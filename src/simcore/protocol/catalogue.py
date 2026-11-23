"""The channel catalogue: what each array in a frame means, and the closed lists its terms come from
(client_rendering §4.1, §4.2; client_objects §3.1; world_model §8, F1).

A channel's name is an identity: its unit, dtype, encoding, scale and offset are fixed for the life of the format, and
a new meaning gets a new name. ``Channel`` is both the registry's entry and what a frame's header describes. A reader
holds the catalogue its build knows (``V0``) and compares each channel a frame describes against it: a known name must
match it term for term; an unknown name is ignored when the frame marks it optional and refused when it marks it
required (``grammar``).

The vocabularies are this registry's to name (client_objects §3.1 defers them to step 7):

- **dtypes**, each little-endian on the wire: ``u8``, ``u16``, ``u32``, ``f16``, ``f32``. A new one bumps the protocol.
- **encodings:** ``raw`` (the stored value is the value: ids, keys, floats) and ``linear`` (value = stored * scale +
  offset, for integer fractions). A new one bumps the protocol.
- **units:** ``id``, ``celsius``, ``m``, ``ratio``. A unit is part of a channel's identity, so a reader compares it
  for the channels it knows and never judges it for one it ignores (a new optional channel may bring a new unit).

Scale and offset are integer rationals (``[num, den]``), so 975/255 needs no float format (DC-N5). The catalogue hash
is ``digest``'s ``sha256/c14n-1`` over the channels' descriptions in order: a frame states the hash of the channels it
carries, and the decoder holds a frame to the hash ``welcome`` announced.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from simcore.core.digest import digest
from simcore.core.refusals import RefusalCode, Refused

__all__ = [
    "DTYPES",
    "ENCODINGS",
    "UNITS",
    "V0",
    "Channel",
    "catalogue_hash",
    "describe",
    "render",
]

# The wire dtypes and their numpy spelling (little-endian, client_rendering §4.1).
DTYPES: Mapping[str, str] = MappingProxyType({"u8": "<u1", "u16": "<u2", "u32": "<u4", "f16": "<f2", "f32": "<f4"})
ENCODINGS = ("raw", "linear")
UNITS = ("id", "celsius", "m", "ratio")


@dataclass(frozen=True)
class Channel:
    """One channel's identity. ``scale`` and ``offset`` are ``(num, den)``; a ``raw`` channel's are 1/1 and 0/1."""

    name: str
    unit: str
    dtype: str
    encoding: str
    required: bool
    scale: tuple[int, int] = (1, 1)
    offset: tuple[int, int] = (0, 1)

    def __post_init__(self) -> None:
        # Held here for the registry's own channels and for every channel a frame describes, so a malformed one is
        # refused with a code, never built (the header's schema has already held dtype and encoding to their lists).
        if self.encoding == "raw" and (self.scale, self.offset) != ((1, 1), (0, 1)):
            raise Refused(f"channel {self.name}: raw, so scale 1/1 and offset 0/1", code=RefusalCode.BAD_SHAPE)
        if self.scale[1] <= 0 or self.offset[1] <= 0:
            raise Refused(f"channel {self.name}: a rational's denominator is positive", code=RefusalCode.BAD_SHAPE)

    def description(self) -> dict[str, object]:
        """The channel as the wire states it, in ``welcome``'s catalogue and in each frame that carries it."""
        return {
            "name": self.name,
            "unit": self.unit,
            "dtype": self.dtype,
            "encoding": self.encoding,
            "required": self.required,
            "scale": list(self.scale),
            "offset": list(self.offset),
        }


# Protocol v0's cell channels (client_rendering §4.2). Every one is required: a client that can't draw one refuses the
# frame rather than draw the world without it.
V0: tuple[Channel, ...] = (
    Channel("material", "id", "u8", "raw", required=True),
    Channel("region", "id", "u16", "raw", required=True),
    Channel("crack", "ratio", "u8", "linear", required=True, scale=(1, 255)),
    Channel("temperature_c", "celsius", "f16", "raw", required=True),
)


def describe(channels: Sequence[Channel]) -> list[dict[str, object]]:
    return [c.description() for c in channels]


def catalogue_hash(descriptions: Sequence[Mapping[str, object]]) -> str:
    """The versioned digest of channel descriptions, in the order given (``digest``'s c14n-1)."""
    return digest(list(descriptions))


def render() -> str:
    """The catalogue and its vocabularies as Markdown: part of ``docs/generated/protocol.md``."""
    lines = [
        "## Channels (protocol v0)",
        "",
        "| Channel | Unit | dtype | Encoding | Required | Scale | Offset |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in V0:
        scale, offset = f"{c.scale[0]}/{c.scale[1]}", f"{c.offset[0]}/{c.offset[1]}"
        lines.append(f"| `{c.name}` | {c.unit} | {c.dtype} | {c.encoding} | {c.required} | {scale} | {offset} |")
    lines += [
        "",
        f"Catalogue hash: `{catalogue_hash(describe(V0))}`",
        "",
        "- **dtypes** (little-endian): " + ", ".join(f"`{d}`" for d in DTYPES),
        "- **encodings:** " + ", ".join(f"`{e}`" for e in ENCODINGS),
        "- **units:** " + ", ".join(f"`{u}`" for u in UNITS),
    ]
    return "\n".join(lines) + "\n"
