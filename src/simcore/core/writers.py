"""Who may read and write the cells now, inside the write window (`docs/design/sim_core.md` §5, §5.1, §6).

A writer is a capability, not a name. ``claim`` grants each writer's ``WriterToken`` once, at its owner's import:
Topology's in `simcore.core.topology`, construction's in `simcore.core.scene`, and every law's in the orchestrator,
`simcore.core.physics`, which narrows to a law's token around that law's step. A second claim raises, so whoever else
claims a writer makes its owner's import fail loudly, and `tests/test_ownership.py`'s token scan holds the claims, the
tokens and the narrowing to those three modules. (The core imports no `sys`, so a claim can't check its caller.)

``Gate`` is the window's access rule, composed by the cells' owner (`simcore.core.grid.CellStore`), which owns the
arrays and the window: who opened the window, who it is narrowed to, and so which fields may be read and written now.
Construction's token only opens a window; inside any window, the code holding Topology's or a law's token narrows to
it for a block, one at a time, and no narrowing nests another. A world edit is made only inside Topology's block
(`simcore.core.topology.apply`), so Topology, not construction or a law, applies every one.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from simcore.core.fields import CONSTRUCTION, FIELDS, TOPOLOGY, WRITERS, writers_of


class WindowClosed(RuntimeError):
    """A write was attempted outside the write window: a programming error, never untrusted input."""


class UndeclaredWriter(RuntimeError):
    """A write to a field by a writer the field registry doesn't declare for it, or by code holding no writer's token
    (sim_core.md §5.1, §6): a programming error, never untrusted input."""


class UndeclaredRead(RuntimeError):
    """A law read a field it doesn't declare in ``reads`` (sim_core.md §5): a programming error."""


_GRANT = object()  # only this module can make a token
_claimed: dict[str, WriterToken] = {}


class WriterToken:
    """One writer's capability. Made only by ``claim``; the gate accepts only a token ``claim`` granted."""

    __slots__ = ("_name",)

    def __init__(self, name: str, grant: object) -> None:
        if grant is not _GRANT:
            raise UndeclaredWriter(f"a writer's token is granted by writers.claim, not made ({name!r})")
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"WriterToken({self._name!r})"


def claim(name: str) -> WriterToken:
    """Grant ``name``'s token, once: its owner claims it at import, and any later claim is refused."""
    if name not in WRITERS:
        raise UndeclaredWriter(f"{name!r} is not a writer the field registry knows (sim_core.md §6)")
    if name in _claimed:
        raise UndeclaredWriter(f"{name!r}'s token was granted already: a writer has one holder")
    _claimed[name] = token = WriterToken(name, _GRANT)
    return token


def _granted(token: object) -> WriterToken:
    if not isinstance(token, WriterToken) or _claimed.get(token.name) is not token:
        raise UndeclaredWriter(f"{token!r} is not a writer's token that writers.claim granted")
    return token


class Gate:
    """Who opened the window and who it is narrowed to, and so what may be read and written now."""

    def __init__(self) -> None:
        self._window: WriterToken | None = None  # the window's opener: construction, or None for an orchestrator
        self._narrowed: tuple[WriterToken | None, frozenset[str] | None] | None = None  # (writer, reads) in a block
        self._ran = False  # an orchestrator's window has opened: construction is over

    @property
    def writer(self) -> str | None:
        """Who writes now: the narrowed writer's name, else the window's (None for nobody, and at rest)."""
        token = self._narrowed[0] if self._narrowed is not None else self._window
        return None if token is None else token.name

    @property
    def narrowed(self) -> bool:
        return self._narrowed is not None

    def open(self, writer: WriterToken | None) -> None:
        """Construction authors a grid before anything runs on it; every later window is an orchestrator's."""
        if writer is None:
            self._ran = True
        elif _granted(writer).name != CONSTRUCTION:
            raise UndeclaredWriter(f"a window is opened by construction or by an orchestrator, not {writer.name!r}")
        elif self._ran:
            raise UndeclaredWriter("construction authors a grid before anything runs on it, never after")
        self._window, self._narrowed = writer, None

    def close(self) -> None:
        self._window, self._narrowed = None, None

    @contextmanager
    def narrow(self, writer: WriterToken | None, reads: tuple[str, ...] | None) -> Iterator[None]:
        """Narrow the open window to ``writer`` (None: a law that writes nothing) for the block, reading only
        ``reads`` and the writer's fields (None: any field, Topology's case)."""
        if self._narrowed is not None:
            raise UndeclaredWriter("the window is narrowed already: one writer at a time, and no writer nests another")
        if writer is not None and _granted(writer).name == CONSTRUCTION:
            raise UndeclaredWriter("construction opens a window of its own; it never narrows one (sim_core.md §6)")
        allowed = None if reads is None else frozenset(reads) | frozenset(_writes(writer))
        self._narrowed = (writer, allowed)
        try:
            yield
        finally:
            self._narrowed = None

    def may_write(self, field: str) -> bool:
        name = self.writer
        return name is not None and name in writers_of(field)

    def require_writer(self, field: str) -> None:
        if not self.may_write(field):
            raise UndeclaredWriter(f"{self.writer!r} is not a declared writer of {field!r} (sim_core.md §6)")

    def require_read(self, field: str) -> None:
        if self._narrowed is not None and self._narrowed[1] is not None and field not in self._narrowed[1]:
            raise UndeclaredRead(f"{self.writer!r} doesn't declare {field!r} in its reads (sim_core.md §5)")

    def require_editor(self, what: str) -> None:
        """World edits are Topology's, inside its ``apply``, whoever asked for them (construction included)."""
        writer = self._narrowed[0] if self._narrowed is not None else None
        if writer is None or writer.name != TOPOLOGY:
            raise UndeclaredWriter(f"{what} is a world edit: only Topology applies it (sim_core.md §5.1)")


def _writes(writer: WriterToken | None) -> tuple[str, ...]:
    return () if writer is None else tuple(f.name for f in FIELDS if writer.name in f.writers)
