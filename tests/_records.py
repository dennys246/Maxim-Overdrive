"""The records tooling for tests: its modules loaded by file, siblings first, and builders of fixture records.

The scripts import their siblings by bare name (``from records import ...``), as ``scripts/lint_standards.py``'s do, so
each is loaded into ``sys.modules`` under that name before anything that imports it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[1]
ORDER = (
    "records",
    "records_index",
    "lint_ids",
    "lint_repo",
    "records_git",
    "lint_records",
    "records_decisions",
    "records_decisions_build",
    "records_migrate",
    "records_renumber",
    "records_tree",
    "records_branch",
    "records_cli",
)


def _load(name: str) -> ModuleType:
    if name in sys.modules and getattr(sys.modules[name], "__file__", "") == str(ROOT / "scripts" / f"{name}.py"):
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = {name: _load(name) for name in ORDER}
records, index, lint_ids, _repo, rgit, lint, decisions, build, migrate, renumber, rtree, branch, cli = (
    M[n] for n in ORDER
)

HEADERS = {
    "docs/lessons/_header.md": "# Lessons\n\nThe head.\n\n",
    "docs/known_gaps/_header.md": "# Known gaps\n\nThe head.\n\n",
    "docs/standards_backlog/_header.md": "# Backlog\n\nThe head.\n\n",
    "docs/design/decisions/alpha/_header.md": "# Decisions of `alpha.md`\n\n",
    "docs/design/decisions/beta/_header.md": "# Decisions of `beta.md`\n\n",
}


def front(**fields: object) -> str:
    return (
        "---\n" + yaml.safe_dump({"version": 1, **fields}, sort_keys=False, allow_unicode=True, width=10**6) + "---\n"
    )


Amended = tuple[dict[str, str], ...]


def lesson(n: int, slug: str, *, body: str = "Text.\n", amended: Amended = (), **over: object) -> tuple[str, str]:
    fields = {"id": n, "slug": slug, "title": slug.replace("-", " ").capitalize(), "date": "2026-11-20",
              "section": "World and physics", "amended": list(amended), **over}  # fmt: skip
    return f"docs/lessons/{n}-{slug}.md", front(**fields) + body


RULING = "**A ruling.** Its text.\n"


def decision(ident: str, slug: str, *, log: str = "alpha", body: str = RULING, **over: object) -> tuple[str, str]:
    fields = {"id": ident, "slug": slug, "title": "A ruling.", "date": "2026-11-20", "who": "owner",
              "owner_section": "§1", **over}  # fmt: skip
    name = f"{slug}.md" if ident == slug else f"{ident}-{slug}.md"
    return f"docs/design/decisions/{log}/{name}", front(**fields) + body


def gap(slug: str, *, body: str = "**A gap.** It is measured; step 8 closes it.\n", **over: object) -> tuple[str, str]:
    fields: dict[str, object] = {"id": slug, "slug": slug, "title": "A gap", "date": "2026-11-20", "kind": "physics"}
    fields |= {"gate": "none: untested", "closes_at": "step 8", **over}
    return f"docs/known_gaps/{slug}.md", front(**fields) + body


def backlog_row(n: int, slug: str, *, body: str = "The check.\n", **over: object) -> tuple[str, str]:
    fields = {"id": f"B{n}", "slug": slug, "title": "A rule", "date": "2026-11-20", "rule": "A rule",
              "lands_with": "open", "status": "open", **over}  # fmt: skip
    return f"docs/standards_backlog/B{n}-{slug}.md", front(**fields) + body


def tree(*items: tuple[str, str], generated: bool = True) -> dict[str, str]:
    """Headers, the given records, and (by default) every generated file regenerated from them."""
    files = {**HEADERS, **dict(items)}
    if generated:
        recs, problems = records.load_records(files)
        assert problems == []
        out, missing = index.generate(recs, index.headers_of(files))
        assert missing == []
        files |= out
    return files
