"""Where the records tooling reads and writes the working tree: the record directories and today's files."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from records import FAMILIES

ROOTS = tuple(f.root for f in FAMILIES)
TODAY = (
    "docs/lessons_maxim_in_games.md",
    "docs/known_gaps.md",
    "docs/standards_backlog.md",
)


def tree_files(root: Path, prefixes: tuple[str, ...] = ROOTS) -> dict[str, str]:
    """The Markdown files under each prefix on disk (records, headers and today's decision logs), by path."""
    out = {}
    for prefix in prefixes:
        directory = root / prefix
        if directory.is_file():
            out[prefix] = directory.read_text(encoding="utf-8")
        for path in sorted(directory.rglob("*.md")) if directory.is_dir() else ():
            out[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return out


def write(root: Path, writes: Mapping[str, str | None]) -> None:
    for rel, text in sorted(writes.items()):
        path = root / rel
        if text is None:
            path.unlink(missing_ok=True)  # a branch that has not merged main yet never had it
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
