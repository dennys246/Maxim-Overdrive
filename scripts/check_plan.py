"""Fail if the foundations plan drops a decision, a Phase 3 item or an open question, or outgrows its word budget.

It checks presence, not truth: each id and question must appear in docs/plans/foundations_plan.md, and a reviewer
still checks that the plan states each one correctly. Sources:

- decision ids (``O12``, ``O11a``, ``OA3``) and Phase 3 ids (``OD-A17``) from the design documents and the roadmap,
  world-model decisions (``D26``) from ``world_model.md``, and the tile's decisions (``T1``) from its two documents;
- every open question: the numbered items of ``boundaries.md`` §12, ``world_model.md`` §12, ``npcs_and_sem.md``
  §12.1, ``tile_and_client.md`` §9 and ``client_rendering.md`` §10, and the bullets of the roadmap's "Open
  questions". The plan lists each source's questions under a heading ``### Open: <source>``, numbered from 1, one
  item per question.

Run: ``python scripts/check_plan.py`` (exit 1 on any finding).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = "docs/plans/foundations_plan.md"
WORD_BUDGET = 2500
ID_SOURCES = (
    "docs/design/boundaries.md",
    "docs/design/npcs_and_sem.md",
    "docs/roadmap.md",
    "docs/design/world_model.md",
    "docs/design/tile_and_client.md",
    "docs/design/client_rendering.md",
)
TILE_DOCS = ("docs/design/tile_and_client.md", "docs/design/client_rendering.md")
DECISION = re.compile(r"\b(O\d+[a-z]?|OA\d+)\b")
PHASE3 = re.compile(r"\bOD-[A-Z]+\d+\b")
WORLD_DECISION = re.compile(r"\bD\d+\b")
TILE_DECISION = re.compile(r"\bT\d+\b")


@dataclass(frozen=True)
class QuestionSource:
    """Where a source keeps its open questions, and the heading the plan lists them under."""

    path: str
    heading: str  # the source's section heading, matched at the start of a line
    numbered: bool  # numbered items ("1. ...") or bullets ("- ...")
    label: str  # the plan's heading is "### Open: <label>"


QUESTIONS = (
    QuestionSource("docs/design/boundaries.md", "## 12. Open questions", True, "boundaries §12"),
    QuestionSource("docs/design/world_model.md", "## 12. Open questions", True, "world_model §12"),
    QuestionSource("docs/design/npcs_and_sem.md", "### 12.1", True, "npcs_and_sem §12.1"),
    QuestionSource("docs/design/tile_and_client.md", "## 9. Open questions", True, "tile §9"),
    QuestionSource("docs/design/client_rendering.md", "## 10. Open questions", True, "client §10"),
    QuestionSource("docs/roadmap.md", "## Open questions", False, "roadmap"),
)


def section(text: str, heading: str) -> str | None:
    """The body under the first line that starts with ``heading``, up to the next heading of that level or higher."""
    level = len(heading) - len(heading.lstrip("#"))
    match = re.search(rf"^{re.escape(heading)}.*$", text, re.M)
    if match is None:
        return None
    rest = text[match.end() :]
    end = re.search(rf"^#{{1,{level}}} ", rest, re.M)
    return rest[: end.start()] if end else rest


def count_items(body: str, numbered: bool) -> int:
    pattern = r"^\d+\. " if numbered else r"^- "
    return len(re.findall(pattern, body, re.M))


def missing_ids(plan: str, sources: dict[str, str]) -> list[str]:
    ids = {i for text in sources.values() for i in DECISION.findall(text) + PHASE3.findall(text)}
    ids |= set(WORLD_DECISION.findall(sources["docs/design/world_model.md"]))
    ids |= {i for doc in TILE_DOCS for i in TILE_DECISION.findall(sources[doc])}
    return [f"{i} is in the sources but not in the plan" for i in sorted(ids) if not re.search(rf"\b{i}\b", plan)]


def missing_questions(plan: str, sources: dict[str, str]) -> list[str]:
    out = []
    for q in QUESTIONS:
        body = section(sources[q.path], q.heading)
        if body is None:
            out.append(f"{q.path} has no '{q.heading}' section")
            continue
        want = count_items(body, q.numbered)
        listed = section(plan, f"### Open: {q.label}")
        have = set(re.findall(r"^(\d+)\. ", listed, re.M)) if listed is not None else set()
        out += [f"{q.label} question {n} is not in the plan" for n in range(1, want + 1) if str(n) not in have]
    return out


def over_budget(plan: str) -> list[str]:
    words = len(plan.split())
    return [f"the plan is {words} words; its budget is {WORD_BUDGET}"] if words > WORD_BUDGET else []


def findings(root: Path = ROOT) -> list[str]:
    plan = (root / PLAN).read_text()
    sources = {s: (root / s).read_text() for s in ID_SOURCES}
    return missing_ids(plan, sources) + missing_questions(plan, sources) + over_budget(plan)


def main(root: Path = ROOT) -> int:
    problems = findings(root)
    for p in problems:
        print(f"check_plan: {p}", file=sys.stderr)
    print(f"check_plan: {'FAIL' if problems else 'PASS'} ({len(problems)} finding(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
