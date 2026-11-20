"""Standards check 4: the coverage floor only ratchets (CLAUDE.md, "Coverage only ratchets up").

``fail_under`` may not drop below the base branch's.
"""

from __future__ import annotations

import tomllib


def fail_under(pyproject: str) -> float | None:
    value = tomllib.loads(pyproject).get("tool", {}).get("coverage", {}).get("report", {}).get("fail_under")
    return None if value is None else float(value)


def check_coverage_ratchet(current: str, base: str | None) -> list[str]:
    now = fail_under(current)
    if now is None:
        return ["pyproject.toml: [tool.coverage.report] fail_under is missing"]
    before = fail_under(base) if base is not None else None
    if before is not None and now < before:
        return [f"pyproject.toml: coverage fail_under fell from {before:g} to {now:g}; the floor only ratchets up"]
    return []
