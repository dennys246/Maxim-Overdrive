"""Converters beyond ``schema``'s numbers and names: whole-number vectors, closed words, flags, digests and secrets.

The wire needs them first (``simcore.protocol``: millimetre vectors, a ``time`` message's ``op``, a frame header's
``required`` and catalogue hash, a session token), but none is the wire's: each is a ``schema.Converter`` any
format's ``Field`` may take, with its ``bad`` values for the generated rejection tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from simcore.core.checks import identity_key, shown
from simcore.core.digest import check_digest
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import Bad, Whole, item_count

__all__ = ["OPAQUE_ALPHABET", "Choice", "Digest", "Flag", "Opaque", "Wholes", "WireName"]


@dataclass(frozen=True)
class Wholes:
    """``n`` ints, each within [``lo``, ``hi``]: a wire vector in whole millimetres, or a direction (tile §3.3)."""

    n: int
    lo: int
    hi: int

    def convert(self, value: object, what: str) -> tuple[int, ...]:
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or item_count(value) != self.n:
            raise Refused(f"{what} must be {self.n} whole numbers, got {shown(value)}", code=RefusalCode.BAD_SHAPE)
        return tuple(Whole(self.lo, self.hi).convert(v, what) for v in value)

    @property
    def bad(self) -> Bad:
        edge = [0] * (self.n - 1)
        return (
            ([0] * (self.n + 1), RefusalCode.BAD_SHAPE),
            ("0" * self.n, RefusalCode.BAD_SHAPE),
            ([*edge, True], RefusalCode.NOT_INT),
            ([*edge, 5500.0], RefusalCode.NOT_INT),
            ([*edge, self.hi + 1], RefusalCode.OUT_OF_RANGE),
        )


@dataclass(frozen=True)
class Choice:
    """One of a closed set of words, such as a ``time`` message's ``op``; another is ``unknown_kind``."""

    words: tuple[str, ...]

    def convert(self, value: object, what: str) -> str:
        if type(value) is not str or value not in self.words:
            raise Refused(
                f"{what} must be one of {list(self.words)}, got {shown(value)}", code=RefusalCode.UNKNOWN_KIND
            )
        return value

    @property
    def bad(self) -> Bad:
        return ((7, RefusalCode.UNKNOWN_KIND), ("nothing", RefusalCode.UNKNOWN_KIND), ([], RefusalCode.UNKNOWN_KIND))


@dataclass(frozen=True)
class Flag:
    """A JSON boolean, exactly: not 0, 1 or "true"."""

    def convert(self, value: object, what: str) -> bool:
        if type(value) is not bool:
            raise Refused(f"{what} must be true or false, got {shown(value)}", code=RefusalCode.BAD_SHAPE)
        return value

    @property
    def bad(self) -> Bad:
        return ((1, RefusalCode.BAD_SHAPE), ("true", RefusalCode.BAD_SHAPE), (None, RefusalCode.BAD_SHAPE))


@dataclass(frozen=True)
class Digest:
    """A stored digest in the one scheme this build knows (``digest.check_digest``)."""

    def convert(self, value: object, what: str) -> str:
        return check_digest(value, what)

    @property
    def bad(self) -> Bad:
        other = "sha1/c14n-1:" + "0" * 64
        return (
            (7, RefusalCode.BAD_SHAPE),
            ("sha256/c14n-1:xyz", RefusalCode.BAD_SHAPE),
            (other, RefusalCode.BAD_VERSION),
        )


OPAQUE_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


@dataclass(frozen=True)
class Opaque:
    """A secret a reader compares and never shows, such as a session token (boundaries §5.3): 1 to ``max_chars``
    characters of the URL-safe base64 alphabet. Its refusal names the field and never the value, so a token can't
    reach a reply or a log through an echo."""

    max_chars: int

    def convert(self, value: object, what: str) -> str:
        if type(value) is not str or not 0 < len(value) <= self.max_chars or not set(value) <= OPAQUE_ALPHABET:
            raise Refused(f"{what} must be 1 to {self.max_chars} URL-safe characters", code=RefusalCode.BAD_SHAPE)
        return value

    @property
    def bad(self) -> Bad:
        long = "x" * (self.max_chars + 1)
        return ((7, RefusalCode.BAD_SHAPE), ("", RefusalCode.BAD_SHAPE), (long, RefusalCode.BAD_SHAPE),
                ("a b", RefusalCode.BAD_SHAPE), ("tok\u00e9n", RefusalCode.BAD_SHAPE))  # fmt: skip


@dataclass(frozen=True)
class WireName:
    """A name on the wire (a grid's, a table's, a channel's, a unit): an identity key (``checks.identity_key``) in
    printable ASCII only, so a reader in another language applies the same rule without Unicode tables of its own,
    which differ between versions (client_rendering §4.1, O63)."""

    def convert(self, value: object, what: str) -> str:
        text = identity_key(value, what)
        if not all(" " <= ch <= "~" for ch in text):
            raise Refused(f"{what} must be printable ASCII", code=RefusalCode.BAD_IDENTITY_KEY)
        return text

    @property
    def bad(self) -> Bad:
        return ((7, RefusalCode.BAD_IDENTITY_KEY), ("", RefusalCode.BAD_IDENTITY_KEY),
                ("a:b", RefusalCode.BAD_IDENTITY_KEY), (" a", RefusalCode.BAD_IDENTITY_KEY),
                ("café", RefusalCode.BAD_IDENTITY_KEY), ("x" * 65, RefusalCode.BAD_IDENTITY_KEY))  # fmt: skip
