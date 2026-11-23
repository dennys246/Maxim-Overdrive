"""The server's text replies that need no simulation clock: ``welcome`` and ``error`` (client_rendering §4.1).

``welcome`` carries, in this step, the session, its role, the protocol, the engine ``build``, the cell grid's shape
and the channel catalogue with its hash; the rest of §4.1's row (the actor, the world config, the region map, the
zones, the material table, the recipe and kind vocabularies, ``regions_version``, the time state and
``bindings_digest``) joins as each producer lands. ``error`` carries a refusal code and, when the refusal names one,
the field we wrote: never exception text, which ``shown`` bounds but doesn't scrub, and never a token.
"""

from __future__ import annotations

from collections.abc import Mapping

import simcore
from simcore.core.refusals import RefusalCode
from simcore.protocol.catalogue import V0, catalogue_hash, describe
from simcore.protocol.messages import PROTOCOL
from simcore.protocol.strict_json import encode

__all__ = ["BUILD", "MAX_TEXT_BYTES", "error", "text", "welcome"]

BUILD = f"simcore {simcore.__version__}"  # the engine build a client shows, and may refuse
# The client's cap on a server text message (client_rendering §4.3): a reply past it would end the session there, so
# the server refuses to write one, loudly, and a reply that grows (a welcome's maps, a tick's columns) fails a test.
MAX_TEXT_BYTES = 64 * 1024


def text(message: Mapping[str, object]) -> str:
    """``message`` as the server's JSON text, within the client's cap: a reply too large for it is a programming
    error, never sent."""
    out = encode(dict(message))
    if len(out) > MAX_TEXT_BYTES:
        raise ValueError(f"a {message.get('type')!r} reply of {len(out)} bytes, past the client's {MAX_TEXT_BYTES}")
    return out


def welcome(*, session_id: int, role: str, shape: tuple[int, int, int]) -> dict[str, object]:
    descriptions = describe(V0)
    return {
        "type": "welcome",
        "protocol": PROTOCOL,
        "session": session_id,
        "role": role,
        "build": BUILD,
        "shape": list(shape),
        "catalogue": descriptions,
        "catalogue_hash": catalogue_hash(descriptions),
    }


def error(code: RefusalCode, field: str | None = None) -> dict[str, object]:
    return {"type": "error", "code": code.value, **({} if field is None else {"field": field})}
