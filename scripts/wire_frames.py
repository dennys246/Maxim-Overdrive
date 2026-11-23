"""Builders for the wire fixtures' frames (``scripts/wire_fixtures.py`` assembles the sets): v0's cells, and edits to
a frame's header that each break one rule, so a fixture names its defect and nothing else.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

from simcore.protocol.catalogue import V0, Channel
from simcore.protocol.grammar import encode_cells

__all__ = [
    "CELL_UM",
    "EIGHT_F32",
    "ORIGIN_UM",
    "SHAPE",
    "SMOKE",
    "SOOT",
    "ZONES",
    "Header",
    "array_entries",
    "arrays",
    "both",
    "cells",
    "drop_array",
    "edited",
    "extra",
    "raw",
    "repack",
    "set_channel",
    "set_key",
    "split",
    "with_channel",
]

SHAPE = (2, 2, 2)
CELL_UM, ORIGIN_UM = 200_000, (0, 0, 0)

Header = dict[str, Any]  # the encoder's own header, as json.loads reads it back


def arrays(shape: tuple[int, int, int]) -> list[NDArray[np.generic]]:
    n = int(np.prod(shape))
    return [
        (np.arange(n) % 4).astype("<u1").reshape(shape),  # material: air, then three solids
        np.arange(n, dtype="<u2").reshape(shape) * 257 + 1,  # region: 0x0001, 0x0102, ...: the two bytes differ, so
        # a reader that swaps them reads another id (a probe below), which RG8's upload of the low byte first needs
        np.linspace(0, 255, n).astype("<u1").reshape(shape),  # crack
        np.linspace(-40.0, 1200.0, n).astype("<f2").reshape(shape),  # temperature_c
    ]


def cells(tick: int = 5, shape: tuple[int, int, int] = SHAPE, catalogue: Sequence[Channel] = V0) -> bytes:
    """The base frame: v0's channels, under the hash of ``catalogue``, the one its welcome announced."""
    channels = list(zip(V0, arrays(shape), strict=True))
    return encode_cells(
        tick=tick, regions_version=1, cell_size_um=CELL_UM, origin_um=ORIGIN_UM, catalogue=catalogue, channels=channels
    )


def split(frame: bytes) -> tuple[Header, bytes]:
    n = int.from_bytes(frame[:4], "little")
    header: Header = json.loads(frame[4 : 4 + n])
    return header, frame[4 + n :]


def repack(header: Header, payload: list[bytes]) -> bytes:
    """A frame from a header the server's encoder would refuse to write (a float, a missing field): plain JSON."""
    return raw(json.dumps(header, separators=(",", ":"), sort_keys=True), b"".join(payload))


def edited(edit: Callable[[Header], None], frame: bytes | None = None) -> bytes:
    """The base frame with its header changed by ``edit``, the payload as it was."""
    header, payload = split(frame or cells())
    edit(header)
    return repack(header, [payload])


def raw(header_text: str, payload: bytes = b"") -> bytes:
    data = header_text.encode("utf-8", "surrogatepass")
    return len(data).to_bytes(4, "little") + data + payload


def array_entries(header: Header) -> list[dict[str, Any]]:
    arrays: list[dict[str, Any]] = header["arrays"]
    return arrays


def with_channel(channel: Channel, values: bytes, of: str = "cells") -> Callable[[Header], None]:
    """Append an array carrying ``channel``; the frame's catalogue hash stays welcome's (O64)."""

    def edit(header: Header) -> None:
        arrays = array_entries(header)
        offset = sum(int(a["size"]) for a in arrays)
        size = len(values)
        arrays.append({"channel": channel.description(), "of": of, "offset": offset, "size": size,
                       "uncompressed_size": size})  # fmt: skip

    return edit


def extra(channel: Channel, values: bytes, of: str = "cells", grid: Header | None = None) -> bytes:
    header, payload = split(cells())
    if grid is not None:
        header["grids"].append(grid)
    with_channel(channel, values, of)(header)
    return repack(header, [payload, values])


def set_key(key: str, value: object) -> Callable[[Header], None]:
    return lambda h: h.__setitem__(key, value)


def set_channel(i: int, key: str, value: object) -> Callable[[Header], None]:
    def edit(h: Header) -> None:
        array_entries(h)[i]["channel"][key] = value

    return edit


SMOKE = Channel("smoke_kg_m3", "kg_per_m3", "f32", "raw", required=False)  # a unit this build has never heard of
SOOT = Channel("soot", "ratio", "u8", "raw", required=False)  # an optional channel a reader may know and a frame omit
EIGHT_F32 = np.arange(8, dtype="<f4").tobytes()
ZONES = {"name": "zones", "required": False, "shape": [1, 1, 2], "cell_size_um": 400_000, "origin_um": [0, 0, 0]}


def drop_array(frame: bytes, i: int) -> bytes:
    """``frame`` without its array ``i``: later offsets moved down, so only the channel is missing."""
    header, payload = split(frame)
    arrays = array_entries(header)
    dropped = arrays.pop(i)
    start, size = int(dropped["offset"]), int(dropped["size"])
    for a in arrays[i:]:
        a["offset"] = int(a["offset"]) - size
    return repack(header, [payload[:start] + payload[start + size :]])


def both(first: Callable[[Header], None], second: Callable[[Header], None]) -> Callable[[Header], None]:
    def edit(h: Header) -> None:
        first(h)
        second(h)

    return edit
