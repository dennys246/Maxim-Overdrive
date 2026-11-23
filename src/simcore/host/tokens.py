"""Per-launch tokens: who may join, and in which role (boundaries §5.3; realtime_lanes_coop §5, TB-4 to TB-6).

Each launch makes one host token and up to ``guests`` guest tokens, fresh from ``secrets``. A token binds its role:
there is no promotion, and a guest's token can never become the host's. The host compares a presented token with
``hmac.compare_digest`` against every token, without stopping at a match, so how long a refusal takes says nothing
about which token was close. A token reaches the client by a 0600 file or the environment, never argv, and never
appears in a log, a repr or an error reply.
"""

from __future__ import annotations

import hmac
import os
import secrets
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from simcore.core.refusals import RefusalCode, Refused

__all__ = ["Role", "Tokens", "write_token_file"]

TOKEN_BYTES = 32  # 43 URL-safe characters, inside the hello schema's 64 (simcore.protocol.messages.TOKEN_CHARS)


class Role(StrEnum):
    HOST = "host"
    GUEST = "guest"


@dataclass(frozen=True)
class Tokens:
    """One launch's tokens: index 0 is the host's. ``repr`` shows how many, never a token."""

    _values: tuple[str, ...] = field(repr=False)

    @classmethod
    def fresh(cls, *, guests: int) -> Tokens:
        if not 0 <= guests <= 8:
            raise Refused(f"a launch has 0 to 8 guest tokens, not {guests}", code=RefusalCode.OUT_OF_RANGE)
        return cls(tuple(secrets.token_urlsafe(TOKEN_BYTES) for _ in range(1 + guests)))

    def __repr__(self) -> str:
        return f"Tokens(host=1, guests={len(self._values) - 1})"

    @property
    def host(self) -> str:
        return self._values[0]

    @property
    def guests(self) -> tuple[str, ...]:
        return self._values[1:]

    def match(self, presented: str) -> int | None:
        """The index of the token ``presented`` is, or None. Every token is compared, whatever matches first."""
        found = None
        for i, value in enumerate(self._values):
            if hmac.compare_digest(presented.encode(), value.encode()):
                found = i
        return found

    @staticmethod
    def role(index: int) -> Role:
        return Role.HOST if index == 0 else Role.GUEST


def write_token_file(path: Path, token: str) -> None:
    """``token`` in a new file at ``path`` that only this user can read (0600), refused if the file exists: a token
    is never written where someone else already chose the file."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(token)
