"""The cell frame's binary grammar, and its extension rule (client_rendering §4.1; world_v2 §8; world_model §8).

A frame is ``[u32 header length][JSON header][arrays]``, little-endian. The header (``frame_header``) is UTF-8 JSON
read by the strict decoder; the arrays follow it back to back, in the header's order, each the raw little-endian
values of one channel over one grid (z, y, x, x fastest: Godot's axis order, W-F4) or one table's rows.

**The decoder's checks, in order** (a refused frame yields nothing; ``client/addons/engine/net/frame_decoder.gd``
applies the same rules, and the golden fixtures hold the two to one outcome each):

1. the frame's length (at most ``max_bytes``), the header length, and the header as ASCII, strict JSON
   (``bad_shape``, ``bad_json``);
2. ``protocol``, before any other field, so a newer frame is refused for its version (``bad_version``);
3. the header's closed schema: an unknown or missing key, an unknown ``kind``, ``compression``, dtype or encoding
   (``unknown_field``, ``missing_field``, ``unknown_kind``);
4. the catalogue hash, against the one ``welcome`` announced (``bad_version``);
5. the layout: each array's container exists, its size is its count times its dtype's width, and the arrays tile the
   payload exactly (``bad_shape``);
6. the extension rule: an unknown grid, table or channel is ignored when marked optional and refused when marked
   required (``unknown_field``); a known channel must match the reader's description term for term, since a name is
   an identity (``bad_shape``); and every channel the reader requires must be present (``missing_field``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
import numpy.typing as npt

from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import read_version
from simcore.protocol.catalogue import DTYPES, Channel, catalogue_hash, describe
from simcore.protocol.frame_header import Array, Header, read_header
from simcore.protocol.messages import PROTOCOL
from simcore.protocol.strict_json import decode, encode, integers_only

__all__ = ["CELL_GRID", "MAX_HEADER_BYTES", "DecodedFrame", "decode_frame", "encode_cells", "pack"]

CELL_GRID = "cells"  # the one grid v0 knows: the world's cells
MAX_HEADER_BYTES = 64 * 1024
_LENGTH_BYTES = 4


@dataclass(frozen=True)
class DecodedFrame:
    """A frame the reader accepted: its cell channels as read-only ``(nz, ny, nx)`` arrays, and what it ignored."""

    tick: int
    regions_version: int
    shape: tuple[int, int, int]
    cell_size_um: int
    origin_um: tuple[int, int, int]
    channels: Mapping[str, npt.NDArray[np.generic]]
    ignored: tuple[str, ...]  # "grid:<name>", "table:<name>" or "channel:<name>", in header order


def pack(header: Mapping[str, object], payload: Sequence[bytes]) -> bytes:
    """A frame's bytes from its header and its arrays' bytes, as given: the encoder's last step, and how the golden
    fixtures build the malformed frames a decoder must refuse."""
    text = encode(dict(header)).encode("ascii")
    return len(text).to_bytes(_LENGTH_BYTES, "little") + text + b"".join(payload)


def encode_cells(
    *,
    tick: int,
    regions_version: int,
    cell_size_um: int,
    origin_um: tuple[int, int, int],
    catalogue: Sequence[Channel],
    channels: Sequence[tuple[Channel, npt.NDArray[np.generic]]],
) -> bytes:
    """A full frame of cell channels, each an ``(nz, ny, nx)`` array in its channel's dtype. The header carries the
    hash of ``catalogue``, the one ``welcome`` announced, whichever of its channels the frame holds (O64)."""
    shape = channels[0][1].shape
    arrays, offset, payload = [], 0, []
    for channel, values in channels:
        if values.shape != shape or values.dtype != np.dtype(DTYPES[channel.dtype]):
            raise TypeError(f"channel {channel.name}: {values.dtype} {values.shape}, not {channel.dtype} {shape}")
        data = np.ascontiguousarray(values, dtype=DTYPES[channel.dtype]).tobytes()
        entry = {"offset": offset, "size": len(data), "uncompressed_size": len(data)}
        arrays.append({"channel": channel.description(), "of": CELL_GRID, **entry})
        payload.append(data)
        offset += len(data)
    grid = {"name": CELL_GRID, "required": True, "shape": list(shape)}
    header = {
        "protocol": PROTOCOL,
        "kind": "full",
        "tick": tick,
        "shape": list(shape),
        "regions_version": regions_version,
        "catalogue": catalogue_hash(describe(catalogue)),
        "compression": "none",
        "grids": [{**grid, "cell_size_um": cell_size_um, "origin_um": list(origin_um)}],
        "tables": [],
        "arrays": arrays,
    }
    return pack(header, payload)


def _bad_shape(message: str) -> Refused:
    return Refused(f"frame: {message}", code=RefusalCode.BAD_SHAPE)


def _header(data: bytes, max_bytes: int) -> tuple[Header, memoryview]:
    """Checks 1 to 3: the header read to its schema, and the payload after it."""
    if not _LENGTH_BYTES <= len(data) <= max_bytes:
        raise _bad_shape(f"{len(data)} bytes, outside [{_LENGTH_BYTES}, {max_bytes}]")
    length = int.from_bytes(data[:_LENGTH_BYTES], "little")
    if not 0 < length <= min(MAX_HEADER_BYTES, len(data) - _LENGTH_BYTES):
        raise _bad_shape(f"a header length of {length} in a frame of {len(data)} bytes")
    text = data[_LENGTH_BYTES : _LENGTH_BYTES + length]
    if not text.isascii():  # the encoder writes ASCII only, so both readers refuse anything else
        raise Refused("frame: a header byte outside ASCII", code=RefusalCode.BAD_JSON)
    raw = decode(text, max_bytes=MAX_HEADER_BYTES)
    if not isinstance(raw, Mapping):
        raise _bad_shape("the header is not a JSON object")
    version = read_version({"version": raw.get("protocol")}, "frame header protocol")
    if version != PROTOCOL:
        raise Refused(f"frame protocol {version}; this reader knows {PROTOCOL}", code=RefusalCode.BAD_VERSION)
    integers_only(raw, "frame header")
    return read_header(raw), memoryview(data)[_LENGTH_BYTES + length :]


@dataclass(frozen=True)
class _Container:
    count: int  # cells or rows
    known: bool
    required: bool


def _containers(header: Header) -> dict[str, _Container]:
    """Each grid and table by name: its element count, whether this reader knows it, and whether it is required."""
    out = {g.name: _Container(math.prod(g.shape), g.name == CELL_GRID, g.required) for g in header.grids}
    out |= {t.name: _Container(t.rows, False, t.required) for t in header.tables}  # v0 knows no table
    if len(out) != len(header.grids) + len(header.tables):
        raise _bad_shape("two grids or tables share a name")
    cells = [g for g in header.grids if g.name == CELL_GRID]
    if not cells:
        raise Refused(f"frame: no {CELL_GRID} grid", code=RefusalCode.MISSING_FIELD, field=CELL_GRID)
    if cells[0].shape != header.shape:
        raise _bad_shape(f"the {CELL_GRID} grid's shape is not the frame's")
    return out


def _layout(header: Header, containers: Mapping[str, _Container], payload: int) -> None:
    """Check 5: every array lies where the header says, at the size its container and dtype give, back to back."""
    at = 0
    for array in header.arrays:
        name = array.channel.name
        if array.of not in containers:
            raise _bad_shape(f"channel {name} belongs to no grid or table named {array.of}")
        size = containers[array.of].count * np.dtype(DTYPES[array.channel.dtype]).itemsize
        if (array.offset, array.size, array.uncompressed_size) != (at, size, size):
            raise _bad_shape(f"channel {name} is not {size} bytes at offset {at}")
        at += size
    if at != payload:
        raise _bad_shape(f"the arrays hold {at} bytes; the payload is {payload}")


def _unknown_required(what: str, name: str) -> Refused:
    return Refused(f"frame: an unknown required {what} {name}", code=RefusalCode.UNKNOWN_FIELD, field=name)


def _ignored_containers(header: Header, containers: Mapping[str, _Container]) -> list[str]:
    """The grids and tables this reader doesn't know: ignored when optional, refused when required."""
    unknown = [("grid", g.name, g.required) for g in header.grids if not containers[g.name].known]
    unknown += [("table", t.name, t.required) for t in header.tables]  # v0 knows no table
    for what, name, required in unknown:
        if required:
            raise _unknown_required(what, name)
    return [f"{what}:{name}" for what, name, _ in unknown]


def _extension(
    header: Header, containers: Mapping[str, _Container], known: Sequence[Channel]
) -> tuple[list[Array], list[str]]:
    """Check 6: the arrays this reader takes, and what it ignored, in header order."""
    ignored = _ignored_containers(header, containers)
    by_name = {c.name: c for c in known}
    taken: list[Array] = []
    for array in header.arrays:
        channel = array.channel
        if not containers[array.of].known:
            continue  # it belongs to an ignored grid or table
        if channel.name in by_name:
            if channel != by_name[channel.name]:
                raise _bad_shape(f"channel {channel.name} differs from this reader's: a name is an identity")
            taken.append(array)
        elif channel.required:
            raise _unknown_required("channel", channel.name)
        else:
            ignored.append(f"channel:{channel.name}")
    return taken, ignored


def _channels(taken: Sequence[Array], known: Sequence[Channel]) -> None:
    names = [a.channel.name for a in taken]
    if len(set(names)) != len(names):
        raise _bad_shape("a channel appears twice")
    missing = [c.name for c in known if c.required and c.name not in names]
    if missing:
        raise Refused(f"frame: no {missing[0]} channel", code=RefusalCode.MISSING_FIELD, field=missing[0])


def decode_frame(data: bytes, *, known: Sequence[Channel], catalogue: str, max_bytes: int) -> DecodedFrame:
    """A frame read by this reader's ``known`` channels and held to the ``catalogue`` hash ``welcome`` announced, or
    a Refused with its code. The arrays are read-only views of ``data``."""
    header, payload = _header(data, max_bytes)
    if header.catalogue != catalogue:
        raise Refused("frame: a catalogue hash other than welcome's", code=RefusalCode.BAD_VERSION, field="catalogue")
    containers = _containers(header)
    _layout(header, containers, len(payload))
    taken, ignored = _extension(header, containers, known)
    _channels(taken, known)
    channels = {
        a.channel.name: np.frombuffer(
            payload, dtype=DTYPES[a.channel.dtype], count=math.prod(header.shape), offset=a.offset
        ).reshape(header.shape)
        for a in taken
    }
    cells = next(g for g in header.grids if g.name == CELL_GRID)
    return DecodedFrame(
        tick=header.tick,
        regions_version=header.regions_version,
        shape=header.shape,
        cell_size_um=cells.cell_size_um,
        origin_um=cells.origin_um,
        channels=MappingProxyType(channels),
        ignored=tuple(ignored),
    )
