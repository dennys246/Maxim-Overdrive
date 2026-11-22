"""Who may write, inside the write window (`docs/design/sim_core.md` §5.1, §6).

The cells' owner (`simcore.core.grid.CellStore`) decides which arrays exist and when the window is open; this decides
who writes inside it. A window is opened as a writer, and each law narrows to its own name with ``as_writer``: a field's
array is writable only for a writer the field registry (`simcore.core.fields`) declares for it, and a read-only view
for anyone else, so an undeclared write raises instead of landing.

It also counts world-edit batches. Paint, region naming and destruction mark the batch edited; the batch closes when
its ``as_writer`` block (or, for a write made straight in the window, the window) closes, and an edited batch bumps
``topology_version`` once (§5.1: "bumped once per changing batch").
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from simcore.core.fields import WRITERS, writers_of


class WindowClosed(RuntimeError):
    """A write was attempted outside the write window: a programming error, never untrusted input."""


class UndeclaredWriter(RuntimeError):
    """A write to a field by a writer the field registry doesn't declare for it (sim_core.md §5.1, §6): a programming
    error, never untrusted input."""


def _known(name: str) -> str:
    if name not in WRITERS:
        raise UndeclaredWriter(f"{name!r} is not a writer the field registry knows (sim_core.md §6)")
    return name


class WriterGate:
    """The window's writer and its topology version. A base of the cells' owner, which sets ``_open``."""

    def __init__(self) -> None:
        self._open = False
        self._writer: str | None = None  # who writes now, inside the window
        self._topology_version = 0
        self._edited = False  # the open batch has painted, named or destroyed something

    @property
    def writer(self) -> str | None:
        """Who writes now: the window's writer, narrowed by ``as_writer`` (None at rest)."""
        return self._writer

    @property
    def topology_version(self) -> int:
        """How many world-edit batches have changed the cells or the region table (sim_core.md §5.1, §7)."""
        return self._topology_version

    @contextmanager
    def as_writer(self, name: str) -> Iterator[None]:
        """Write as ``name`` for the length of the block, inside the window: each law narrows to its own name, so it
        can write only the fields the registry declares it a writer of. The block is one batch for the version."""
        self._require_window(f"writing as {name!r}")
        before, self._writer = self._writer, _known(name)
        try:
            yield
            self._close_batch()
        finally:
            self._writer = before

    def _require_window(self, what: str) -> None:
        if not self._open:
            raise WindowClosed(f"{what} changes only inside the write window (boundaries §4.1)")

    def _may_write(self, field: str) -> bool:
        return self._writer is not None and self._writer in writers_of(field)

    def _require_writer(self, field: str) -> None:
        if not self._may_write(field):
            raise UndeclaredWriter(f"{self._writer!r} is not a declared writer of {field!r} (sim_core.md §6)")

    def _mark_edited(self) -> None:
        self._edited = True

    def _close_batch(self) -> None:
        if self._edited:  # a batch that changed nothing (a destruction of air) doesn't move the version
            self._topology_version += 1
            self._edited = False

    def _begin(self, writer: str | None) -> int:
        """The window opens as ``writer``; returns the version to restore if it rolls back."""
        self._writer = None if writer is None else _known(writer)
        return self._topology_version

    def _end(self, rollback_to: int | None) -> None:
        """The window closes: committed (``None``), or rolled back to the version it opened at."""
        if rollback_to is None:
            self._close_batch()
        else:
            self._topology_version = rollback_to
        self._writer, self._edited = None, False
