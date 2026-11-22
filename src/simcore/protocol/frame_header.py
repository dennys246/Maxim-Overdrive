"""A cell frame's JSON header, as a closed schema (client_rendering §4.1; world_v2 §8: frames are self-describing).

The header states the protocol version, the frame's kind, its tick, the cell grid's shape, the grids and tables its
arrays belong to, the regions version, the catalogue hash, the compression and, per array, the channel it carries and
where its bytes lie. Every key is closed: a header key this build doesn't know is ``unknown_field``, so a field is
added with a protocol bump, never slipped in. What the extension rule ignores is named inside the lists (an optional
grid, table or channel), never a top-level key.

A channel's ``unit`` is read as a name here and held to the vocabulary only for a channel the reader knows: an optional
channel with a unit this build has never heard of is ignored with the channel, so it bumps the registry, not the
protocol (§4.1). A dtype, encoding, kind or compression outside the lists is refused wherever it appears.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from simcore.core.converters import Choice, Digest, Flag, Wholes
from simcore.core.schema import Field, Identity, ListOf, Nested, Schema, Whole
from simcore.protocol.catalogue import DTYPES, ENCODINGS, Channel
from simcore.protocol.strict_json import JSON_INT_MAX

__all__ = [
    "COMPRESSIONS", "HEADER", "KINDS", "MAX_ARRAYS", "MAX_EXTENT", "MAX_GRIDS", "MAX_TABLES", "Array", "Grid", "Header",
    "Table", "read_header",
]  # fmt: skip

KINDS = ("full",)  # `delta` is reserved, not built (§4.1): refused as an unknown kind until it is
COMPRESSIONS = ("none",)  # off in v0, the field reserved (realtime_lanes_coop §7)
MAX_GRIDS, MAX_TABLES, MAX_ARRAYS = 8, 16, 64  # counted before any item is read (boundaries §5.4)
MAX_EXTENT = 2**16 - 1  # cells along one axis: a u16 texture dimension

_COUNT = Whole(0, JSON_INT_MAX)
_RATIONAL = Wholes(2, -JSON_INT_MAX, JSON_INT_MAX)

CHANNEL = Schema(
    (
        Field("name", Identity()),
        Field("unit", Identity()),
        Field("dtype", Choice(tuple(DTYPES))),
        Field("encoding", Choice(ENCODINGS)),
        Field("required", Flag()),
        Field("scale", _RATIONAL),
        Field("offset", _RATIONAL),
    )
)
GRID = Schema(
    (
        Field("name", Identity()),
        Field("required", Flag()),
        Field("shape", Wholes(3, 1, MAX_EXTENT)),  # [nz, ny, nx]
        Field("cell_size_um", Whole(1, JSON_INT_MAX)),
        Field("origin_um", Wholes(3, -JSON_INT_MAX, JSON_INT_MAX)),  # [x, y, z] of the grid's corner
    )
)
TABLE = Schema((Field("name", Identity()), Field("required", Flag()), Field("rows", _COUNT)))
ARRAY = Schema(
    (
        Field("channel", Nested(CHANNEL)),
        Field("of", Identity()),  # the grid or table the array belongs to
        Field("offset", _COUNT),  # from the payload's start, after the header
        Field("size", _COUNT),
        Field("uncompressed_size", _COUNT),
    )
)
HEADER = Schema(
    (
        Field("protocol", _COUNT),
        Field("kind", Choice(KINDS)),
        Field("tick", _COUNT),
        Field("shape", Wholes(3, 1, MAX_EXTENT)),  # the cell grid's [nz, ny, nx]
        Field("regions_version", _COUNT),
        Field("catalogue", Digest()),
        Field("compression", Choice(COMPRESSIONS)),
        Field("grids", ListOf(Nested(GRID), MAX_GRIDS)),
        Field("tables", ListOf(Nested(TABLE), MAX_TABLES)),
        Field("arrays", ListOf(Nested(ARRAY), MAX_ARRAYS)),
    ),
    wire=True,
)


@dataclass(frozen=True)
class Grid:
    name: str
    required: bool
    shape: tuple[int, int, int]
    cell_size_um: int
    origin_um: tuple[int, int, int]


@dataclass(frozen=True)
class Table:
    name: str
    required: bool
    rows: int


@dataclass(frozen=True)
class Array:
    channel: Channel
    of: str
    offset: int
    size: int
    uncompressed_size: int


@dataclass(frozen=True)
class Header:
    protocol: int
    kind: str
    tick: int
    shape: tuple[int, int, int]
    regions_version: int
    catalogue: str
    compression: str
    grids: tuple[Grid, ...]
    tables: tuple[Table, ...]
    arrays: tuple[Array, ...]


def _built[T](cls: type[T], values: Mapping[str, object]) -> T:
    return cls(**values)  # each value was converted by its schema field, the field named for the dataclass's own


def read_header(raw: object) -> Header:
    """The header read to its schema and typed, or a Refused. ``protocol`` is the caller's to check first."""
    read = HEADER.read(raw, "frame header")
    arrays = tuple(
        _built(Array, {**a, "channel": _built(Channel, a["channel"])})
        for a in read["arrays"]  # type: ignore[attr-defined]  # ListOf reads a tuple of mappings
    )
    grids = tuple(_built(Grid, g) for g in read["grids"])  # type: ignore[attr-defined]  # ListOf reads a tuple
    tables = tuple(_built(Table, t) for t in read["tables"])  # type: ignore[attr-defined]  # ListOf reads a tuple
    return _built(Header, {**read, "grids": grids, "tables": tables, "arrays": arrays})
