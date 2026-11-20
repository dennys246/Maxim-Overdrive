"""Standards check 4, size tripwires and their ratchet: separation of concerns (CLAUDE.md, "Size tripwires").

In ``src/`` and ``scripts/``, no function body, module or class may outgrow the limits in
``[tool.maxim_overdrive.size_limits]``, and no ``noqa`` may silence the complexity rules. A function that doesn't fit
is split by responsibility; the limit is a tripwire for a god function, not a target. The limits only tighten: none
may rise above the base branch's.
"""

from __future__ import annotations

import ast
import re
import tomllib
from dataclasses import dataclass

# A noqa that silences a complexity rule, a blanket noqa (which silences every rule), or a file-wide exemption in
# ruff's or flake8's spelling (ruff honours both). The scan is by line, so a string that spells one is flagged too.
COMPLEXITY_NOQA = re.compile(
    r"#\s*noqa:[^#\n]*\b(?:C90\d?|PLR091[1-5])\b|#\s*noqa(?!\s*:)|#\s*(?:ruff|flake8)\s*:\s*noqa", re.IGNORECASE
)
SIZE_SCOPE = ("src/", "scripts/")


@dataclass(frozen=True)
class SizeLimits:
    function_lines: int
    module_lines: int
    public_methods: int


def size_limits(pyproject: str) -> tuple[SizeLimits | None, list[str]]:
    table = tomllib.loads(pyproject).get("tool", {}).get("maxim_overdrive", {}).get("size_limits")
    names = ("function_lines", "module_lines", "public_methods")
    if not isinstance(table, dict) or set(table) != set(names):
        return None, [f"pyproject.toml: [tool.maxim_overdrive.size_limits] must set exactly {', '.join(names)}"]
    if not all(type(table[n]) is int and table[n] > 0 for n in names):
        return None, ["pyproject.toml: every size limit must be a positive integer"]
    return SizeLimits(**{n: table[n] for n in names}), []


def check_size_ratchet(current: SizeLimits, base: str | None) -> list[str]:
    """The size limits only tighten: no limit may rise above the base branch's."""
    before, _ = size_limits(base) if base is not None else (None, [])
    if before is None:
        return []
    return [
        f"pyproject.toml: size limit {name} rose from {getattr(before, name)} to {getattr(current, name)}; "
        "limits only tighten"
        for name in ("function_lines", "module_lines", "public_methods")
        if getattr(current, name) > getattr(before, name)
    ]


def _body_lines(fn: ast.FunctionDef | ast.AsyncFunctionDef, lines: list[str]) -> int:
    """Lines of code in the body: the docstring, blank lines and comment-only lines don't count, so the limit never
    pushes anyone to delete an explanation. Approximate by design: a line inside a multi-line string that starts with
    ``#`` is skipped too."""
    first = fn.body[0]
    docstring = (
        isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
    )
    body = fn.body[1:] if docstring else fn.body
    if not body:
        return 0
    end = fn.end_lineno if fn.end_lineno is not None else body[-1].lineno
    return sum(1 for ln in lines[body[0].lineno - 1 : end] if ln.strip() and not ln.lstrip().startswith("#"))


def _tree_problems(rel: str, tree: ast.Module, lines: list[str], limits: SizeLimits) -> list[str]:
    """Function bodies and public methods. A class's public methods are the ``def``s in its own body, properties and
    each ``@overload`` stub included: they are all surface a caller can reach."""
    problems = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and (n := _body_lines(node, lines)) > limits.function_lines
        ):
            problems.append(
                f"{rel}:{node.lineno}: {node.name} has a {n}-line body (limit {limits.function_lines}); "
                "split it by responsibility"
            )
        if isinstance(node, ast.ClassDef):
            public = [
                m
                for m in node.body
                if isinstance(m, ast.FunctionDef | ast.AsyncFunctionDef) and not m.name.startswith("_")
            ]
            if len(public) > limits.public_methods:
                problems.append(
                    f"{rel}:{node.lineno}: class {node.name} has {len(public)} public methods "
                    f"(limit {limits.public_methods}); it is doing more than one job"
                )
    return problems


def check_sizes(files: dict[str, str], limits: SizeLimits) -> list[str]:
    """God-function tripwires over the code coverage measures (``src/`` and ``scripts/``)."""
    problems = []
    for rel, text in sorted(files.items()):
        if not (rel.endswith(".py") and rel.startswith(SIZE_SCOPE)):
            continue
        lines = text.splitlines()
        if len(lines) > limits.module_lines:
            problems.append(f"{rel}: {len(lines)} lines (limit {limits.module_lines}); split the module by concern")
        problems += [
            f"{rel}:{i}: a noqa may not silence the complexity rules; split the code instead"
            for i, ln in enumerate(lines, 1)
            if COMPLEXITY_NOQA.search(ln)
        ]
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:  # reported as a finding: an unparseable file must not pass the size check unread
            problems.append(f"{rel}:{exc.lineno}: does not parse, so its sizes can't be checked: {exc.msg}")
            continue
        problems += _tree_problems(rel, tree, lines, limits)
    return problems
