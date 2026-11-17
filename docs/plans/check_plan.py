"""Fail if the foundations plan misses a decision, a Phase 3 item or an open owner question from its sources.

Run: ``python docs/plans/check_plan.py`` from the repository root. It extracts every decision id (``O12``, ``O11a``,
``OA3``) and every Phase 3 id (``OD-A17``, ``OD-HX1``) from the design documents and the roadmap, and every numbered
item of ``npcs_and_sem.md`` §12.1, and checks that each appears in ``docs/plans/foundations_plan.md``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/plans/foundations_plan.md"
SOURCES = ("docs/design/boundaries.md", "docs/design/npcs_and_sem.md", "docs/roadmap.md")
DECISION = re.compile(r"\b(O\d+[a-z]?|OA\d+)\b")
PHASE3 = re.compile(r"\bOD-[A-Z]+\d+\b")


def owner_questions(npcs: str) -> list[str]:
    """The numbers of §12.1's items, e.g. ['1', ..., '7']."""
    section = npcs.split("### 12.1", 1)[1].split("\n### ", 1)[0]
    return re.findall(r"^(\d+)\. \*\*", section, re.M)


def missing(plan: str, sources: dict[str, str]) -> list[str]:
    ids = {i for text in sources.values() for i in DECISION.findall(text) + PHASE3.findall(text)}
    out = [i for i in sorted(ids) if not re.search(rf"\b{re.escape(i)}\b", plan)]
    section = plan.split("### 5.1", 1)[1].split("\n### ", 1)[0] if "### 5.1" in plan else ""
    covered = set(re.findall(r"^(\d+)\. ", section, re.M))
    out += [f"§12.1 item {n}" for n in owner_questions(sources["docs/design/npcs_and_sem.md"]) if n not in covered]
    return out


def main() -> int:
    sources = {s: (ROOT / s).read_text() for s in SOURCES}
    gaps = missing(PLAN.read_text(), sources)
    for g in gaps:
        print(f"check_plan: {g} is in the sources but not in docs/plans/foundations_plan.md", file=sys.stderr)
    print(f"check_plan: {'FAIL' if gaps else 'PASS'} ({len(gaps)} missing)")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
