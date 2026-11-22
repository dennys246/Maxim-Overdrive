"""Sessions and who may change time (boundaries §5.3; realtime_lanes_coop §5, TB-16, TB-17).

A session is one live connection that has said ``hello`` with a token. Sessions are capped, one per token, and
numbered in the order they open, never reused within a launch. ``TimeAuthority`` decides a ``time`` request from a
frozen view of the sessions, never the live table; ``HostOnly`` grants the host and refuses every guest with a
reason, and never answers "pending", which is reserved for a future vote (TB-17).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from simcore.core.refusals import RefusalCode, Refused
from simcore.host.tokens import Role, Tokens

__all__ = ["Decision", "HostOnly", "Session", "SessionView", "Sessions", "TimeAuthority"]


@dataclass(frozen=True)
class Session:
    session_id: int
    role: Role
    token_index: int


@dataclass(frozen=True)
class SessionView:
    """The sessions as of one moment: what an authority decides from."""

    sessions: tuple[Session, ...]

    def role_of(self, session_id: int) -> Role | None:
        return next((s.role for s in self.sessions if s.session_id == session_id), None)


@dataclass(frozen=True)
class Decision:
    granted: bool
    reason: RefusalCode | None  # None when granted


class TimeAuthority(Protocol):
    def decide(self, view: SessionView, session_id: int) -> Decision: ...


class HostOnly:
    """Time is the host's: granted for the host's session, refused for any other, never pending."""

    def decide(self, view: SessionView, session_id: int) -> Decision:
        if view.role_of(session_id) is Role.HOST:
            return Decision(True, None)
        return Decision(False, RefusalCode.HOST_ONLY)


class Sessions:
    """The live sessions of one launch: opened by a valid hello, closed when the connection ends."""

    def __init__(self, tokens: Tokens, *, cap: int) -> None:
        self._tokens = tokens
        self._cap = cap
        self._live: dict[int, Session] = {}
        self._next_id = 1

    def open(self, token: str) -> Session:
        """A new session for ``token``, or a Refused: an unknown token, a token already live, or the cap reached."""
        index = self._tokens.match(token)
        if index is None:
            raise Refused("hello: no such token", code=RefusalCode.BAD_TOKEN)
        if any(s.token_index == index for s in self._live.values()):
            raise Refused("hello: that token's session is live", code=RefusalCode.TOKEN_IN_USE)
        if len(self._live) >= self._cap:
            raise Refused(f"hello: the server holds {self._cap} sessions", code=RefusalCode.BUSY)
        session = Session(self._next_id, Tokens.role(index), index)
        self._next_id += 1
        self._live[session.session_id] = session
        return session

    def close(self, session: Session) -> None:
        self._live.pop(session.session_id, None)

    def view(self) -> SessionView:
        return SessionView(tuple(self._live[k] for k in sorted(self._live)))
