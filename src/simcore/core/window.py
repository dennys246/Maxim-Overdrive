"""The write window's lifecycle (boundaries §4.1): one owner at a time, a window that commits whole or rolls back
whole, and listeners told after each commit.

What a window holds, and who may write inside it, are its owner's (`simcore.core.grid.CellStore` and its gate,
`simcore.core.writers.Gate`); this is only the protocol every window follows, so it lives once.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from simcore.core.writers import WindowClosed, WriterToken


class WindowOwner[Saved]:
    """A base for whatever owns a write window. Subclasses say how a window opens, commits and rolls back; ``Saved``
    is what a rollback restores."""

    def __init__(self) -> None:
        self._open = False
        self._held = False  # the world's sources-only window: the same one owner as the cells' window
        self._on_close: list[Callable[[], None]] = []

    @property
    def is_writing(self) -> bool:
        """Whether the write window is open now."""
        return self._open

    def on_close(self, callback: Callable[[], None]) -> None:
        """Call ``callback`` after each window that closes without raising, whether or not it changed anything (the
        world publishes a frame there). Registered at rest only, by the window's owner, so code running inside a
        window (a law's step) can't leave a listener behind (PR 2 delta N3)."""
        self._refuse_a_second_owner()
        self._on_close.append(callback)

    def _refuse_a_second_owner(self) -> None:
        if self._open or self._held:
            raise WindowClosed("the write window is already open: it has one owner at a time")

    @contextmanager
    def holding(self) -> Iterator[None]:
        """The window's ownership without its contents: held by the world's sources-only window, so neither window
        opens while the other is open (step 3b delta review, Executor S-a). Copies nothing, publishes nothing."""
        self._refuse_a_second_owner()
        self._held = True
        try:
            yield
        finally:
            self._held = False

    @contextmanager
    def writing(self, *, writer: WriterToken | None) -> Iterator[None]:
        """The write window, opened by construction's token or by an orchestrator (None). One owner at a time: a
        window opened inside another, or inside ``holding``, is refused. Everything new is built before anything is
        committed, so a window that raises, in its body or while it closes, is rolled back whole."""
        self._refuse_a_second_owner()
        saved = self._open_window(writer)
        self._open = True
        try:
            yield
            commit = self._prepare_commit()
        except BaseException:
            self._roll_back(saved)
            raise
        else:
            commit()
        finally:
            self._open = False
            self._close_window()
        for callback in self._on_close:
            callback()

    def _open_window(self, writer: WriterToken | None) -> Saved:
        """Open for ``writer``; return what a rollback restores."""
        raise NotImplementedError  # pragma: no cover - abstract: the cell store implements it (no abc in the core)

    def _prepare_commit(self) -> Callable[[], None]:
        """Build everything the commit installs (it may raise: nothing is committed yet); return the install step."""
        raise NotImplementedError  # pragma: no cover - abstract: the cell store implements it (no abc in the core)

    def _roll_back(self, saved: Saved) -> None:
        """Restore what ``_open_window`` saved."""
        raise NotImplementedError  # pragma: no cover - abstract: the cell store implements it (no abc in the core)

    def _close_window(self) -> None:
        """Release whatever only an open window holds, committed or not."""
        raise NotImplementedError  # pragma: no cover - abstract: the cell store implements it (no abc in the core)
