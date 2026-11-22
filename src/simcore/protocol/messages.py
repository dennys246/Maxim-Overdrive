"""Protocol v0's client messages, read at the decode stage and stage 1 (tile §3.3, §3.4; boundaries §5.3, §9.1).

Each message is one JSON object whose ``type`` names it, from the closed set tile §3.3 lists. The read is in two steps,
each with its codes from ``refusals``:

- **decode** (``strict_json``): ``bad_json``; then ``unknown_kind`` for a ``type`` outside the set, and
  ``unknown_field`` for any key the message doesn't take, which refuses every client-sent ``actor``, ``tick``,
  ``role``, ``session``, ``observed_tick``, ``issued_tick``, ``apply_tick`` and ``apply_us`` (boundaries §5.3);
- **stage 1** (types and shapes, the schema's converters): ``not_int`` for ``true``, ``5500.0`` or ``1e3`` where an
  integer is expected, ``bad_shape`` for a vector of the wrong length or a value of the wrong kind, ``missing_field``.

What stage 1 checks against limits from ``data/world/`` (a ceiling, ``dir`` both zero, a point outside the world) is
answered with an ``intent_result``, which joins with step 5a's integer clock; until then these fields are held only to
the JSON integer pin. The two replies the decode stage and stage 1 give are ``error`` messages (``server.error``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from simcore.core.converters import Choice, Opaque, Wholes
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import Field, Real, Schema, Tagged, Whole
from simcore.protocol.strict_json import JSON_INT_MAX, decode

__all__ = [
    "CLIENT_MESSAGES",
    "MAX_MESSAGE_BYTES",
    "PROTOCOL",
    "SEQ_LIMIT",
    "TIME_OPS",
    "TOKEN_CHARS",
    "ClientMessage",
    "Hello",
    "Kindle",
    "Move",
    "MoveTo",
    "Snapshot",
    "Time",
    "read_message",
]

PROTOCOL = 0  # protocol v0: the version hello carries and every frame header states
MAX_MESSAGE_BYTES = (
    64 * 1024
)  # the server's inbound max_size (client_rendering §4.3); past it the transport closes 1009
SEQ_LIMIT = 2**31  # a message's seq is in [0, 2^31) (tile §3.3, W-F5)
TOKEN_CHARS = 64  # a token's text, as the host makes it, is 43 characters; any longer is not one
TIME_OPS = ("pause", "resume", "set_scale")

_INT = Whole(-JSON_INT_MAX, JSON_INT_MAX)  # held to the pin only, until intent_result brings the ceilings
_SEQ = Field("seq", Whole(0, SEQ_LIMIT - 1))
_VERSION = Whole(0, JSON_INT_MAX)  # any version is read as a number first, so a newer one gets bad_version

CLIENT_MESSAGES = Tagged(
    "type",
    "",  # no type is refused as unknown_kind, like a misspelt one
    MappingProxyType(
        {
            "hello": Schema((Field("protocol", _VERSION), Field("token", Opaque(TOKEN_CHARS)))),
            "move": Schema((_SEQ, Field("dir", Wholes(2, -JSON_INT_MAX, JSON_INT_MAX), nullable=True))),
            "move_to": Schema((_SEQ, Field("target_mm", Wholes(2, -JSON_INT_MAX, JSON_INT_MAX)))),
            "kindle": Schema(
                (
                    _SEQ,
                    Field("point_mm", Wholes(3, -JSON_INT_MAX, JSON_INT_MAX)),
                    Field("duration_ticks", _INT),
                ),
                wire=True,
            ),
            "time": Schema(
                (_SEQ, Field("op", Choice(TIME_OPS)), Field("scale", Real(), required=False, nullable=True))
            ),
            "snapshot": Schema((_SEQ,)),
        }
    ),
)


@dataclass(frozen=True)
class Hello:
    protocol: int
    token: str

    def __repr__(self) -> str:  # a token never reaches a log through a repr (boundaries §5.3)
        return f"Hello(protocol={self.protocol}, token=<{len(self.token)} characters>)"


@dataclass(frozen=True)
class Move:
    seq: int
    dir: tuple[int, int] | None  # None stops; a stop is never refused (tile §3.4, WT-S5)


@dataclass(frozen=True)
class MoveTo:
    seq: int
    target_mm: tuple[int, int]


@dataclass(frozen=True)
class Kindle:
    seq: int
    point_mm: tuple[int, int, int]
    duration_ticks: int


@dataclass(frozen=True)
class Time:
    seq: int
    op: str
    scale: float | None  # present for set_scale only


@dataclass(frozen=True)
class Snapshot:
    seq: int


ClientMessage = Hello | Move | MoveTo | Kindle | Time | Snapshot


def read_message(data: str | bytes) -> ClientMessage:
    """One client message, decoded and through stage 1, or a Refused with the code its ``error`` reply carries."""
    raw = decode(data, max_bytes=MAX_MESSAGE_BYTES)
    if not isinstance(raw, Mapping):
        raise Refused(f"a message is a JSON object, got a {type(raw).__name__}", code=RefusalCode.BAD_SHAPE)
    read = CLIENT_MESSAGES.convert(raw, "message")
    return _typed(read)


def _typed(read: Mapping[str, object]) -> ClientMessage:
    values = {k: v for k, v in read.items() if k != "type"}
    kind = read["type"]
    if kind == "time":
        return _time(values)
    builder: type[Hello | Move | MoveTo | Kindle | Snapshot] = {
        "hello": Hello, "move": Move, "move_to": MoveTo, "kindle": Kindle, "snapshot": Snapshot
    }[str(kind)]  # fmt: skip
    return builder(**values)  # type: ignore[arg-type]  # the schema read each field to its declared type


def _time(values: Mapping[str, object]) -> Time:
    """A ``time`` message: ``scale`` comes with ``set_scale`` and with nothing else (tile §3.3)."""
    has_scale = values["scale"] is not None
    if has_scale != (values["op"] == "set_scale"):
        rule = "set_scale needs a scale" if not has_scale else f"{values['op']} takes no scale"
        raise Refused(f"message (time): {rule}", code=RefusalCode.BAD_SHAPE, field="scale")
    return Time(**values)  # type: ignore[arg-type]  # the schema read each field to its declared type
