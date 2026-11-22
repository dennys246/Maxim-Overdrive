"""Standards check 7: one owner per contract (CLAUDE.md, "One owner per contract"; B36).

A contract that other modules depend on is stated in one section of one design document, its owner; every other
document links to it. ``docs/design/contracts.md`` registers each checked contract as a table row:

    | `<name>` | `<path under docs/>` §<number> | vocabulary or signature |

and its owner section carries ``<!-- contract: <name> -->`` on the line before the defining block (a table, a list or
a paragraph). Where the block's shape doesn't isolate the members (a list inside a sentence), the marker names them:
``<!-- contract: <name>: a b c -->``, and each named member must appear in the block as a code span, so the marker
can't drift from the text. A marker lists the members that identify its vocabulary and may leave out a word other
vocabularies share (the codec's `step` is also `AgentPort`'s); a signature's marker names the one span. The check is
mechanical and has a known limit: it sees code spans, not prose, and a member the text gains but the marker doesn't
name goes unseen.

- A *vocabulary* contract's members are the code spans of its defining block: a table's first column, a list item's
  head (before its first ``:``), or every span of a paragraph. Any other block in scope that holds at least
  ``min(3, n)`` distinct members restates it. Fewer is a reference: naming one ``thought_failed`` reason passes.
- A *signature* contract's member is the first code span of its block (an ordering key, say); that span appearing
  anywhere else in scope restates it.
- Every row has exactly one marker, inside the section it names; every marker has a row; a vocabulary has at least
  three members.
- No design document holds a fold table or a decision table: those are records (``docs/design/reviews/``,
  ``docs/design/decisions/``).

Scope: ``docs/design/*.md``, ``docs/plans/*.md``, ``docs/roadmap.md`` and ``docs/architecture.md``. Records
(``reviews/``, ``decisions/``, ``research/``) sit in subdirectories and are out of scope, and so is a design marked
superseded (a line starting ``> **Superseded``), which is history.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

REGISTRY = "docs/design/contracts.md"
KINDS = {"vocabulary", "signature"}
MARKER = re.compile(r"^<!-- contract: ([a-z0-9_.-]+)(?:: ([^>]*?))? -->\s*$")
SUPERSEDED = re.compile(r"^> \*\*Superseded", re.M)
SCOPE = re.compile(r"^docs/(design|plans)/[^/]+\.md$|^docs/(roadmap|architecture)\.md$")
DESIGN = re.compile(r"^docs/design/[^/]+\.md$")
SPAN = re.compile(r"`([^`\n]+)`")
HEADING = re.compile(r"^(#{1,6}) (.*)$")
ITEM = re.compile(r"^(?:[-*]|\d+\.) ")
ROW = re.compile(r"^\| `([a-z0-9_.-]+)` \| `([^`]+)` §(\d+(?:\.\d+)*) \| (\w+) \| (\d+) \|\s*$")
FOLD = re.compile(r"^#{1,6} Fold table", re.M)


@dataclass(frozen=True)
class Contract:
    name: str
    path: str  # repository-relative
    section: str  # "6.6"
    kind: str
    threshold: int  # how many members one block must hold to restate it


@dataclass(frozen=True)
class Block:
    start: int  # 0-based line index of the first line
    lines: tuple[str, ...]


def blocks(text: str) -> list[Block]:
    """Runs of non-blank lines, split at each top-level list item; a heading or a marker is a block of its own, and a
    fenced code block is one block. A table is one block, so a vocabulary spread over its rows is a restatement."""
    out: list[Block] = []
    cur: list[str] = []
    start = 0
    fenced = False
    for i, line in enumerate(text.split("\n")):
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and (not line.strip() or HEADING.match(line) or MARKER.match(line)):
            if cur:
                out.append(Block(start, tuple(cur)))
            cur = []
            if line.strip():  # a heading or a marker stands alone
                out.append(Block(i, (line,)))
            continue
        if not fenced and cur and ITEM.match(line) and ITEM.match(cur[0]):
            out.append(Block(start, tuple(cur)))  # each top-level list item is a block of its own
            cur = []
        if not cur:
            start = i
        cur.append(line)
    if cur:
        out.append(Block(start, tuple(cur)))
    return out


def members(block: Block, kind: str) -> list[str]:
    """The code spans that define a contract, in order, without repeats."""
    lines = block.lines
    if kind == "signature":
        spans = SPAN.findall("\n".join(lines))
        return spans[:1]
    if lines[0].startswith("|"):
        rows = [ln for ln in lines if not re.fullmatch(r"\|[\s:|-]*\|", ln.strip())][1:]  # skip the header
        found = [s for ln in rows for s in SPAN.findall(ln.strip().strip("|").split("|")[0])]
    elif re.match(r"^\s*(?:[-*]|\d+\.) ", lines[0]):
        items = [ln for ln in lines if re.match(r"^\s*(?:[-*]|\d+\.) ", ln)]
        found = [s for ln in items for s in SPAN.findall(ln.split(":", 1)[0])]
    else:
        found = SPAN.findall("\n".join(lines))
    return list(dict.fromkeys(found))


def registry(files: dict[str, str]) -> tuple[list[Contract], list[str]]:
    text = files.get(REGISTRY)
    if text is None:
        return [], [f"{REGISTRY} is missing: B36's contracts have no registry"]
    out: list[Contract] = []
    problems: list[str] = []
    for n, line in enumerate(text.split("\n"), 1):
        if not line.startswith("| `"):
            continue
        m = ROW.match(line)
        if m is None:
            problems.append(f"{REGISTRY}:{n}: a row must read | `name` | `path` §N | kind | restates at |")
            continue
        name, path, section, kind, at = m.groups()
        if kind not in KINDS:
            problems.append(f"{REGISTRY}:{n}: {name}'s kind is {kind!r}; it must be one of {sorted(KINDS)}")
            continue
        if any(c.name == name for c in out):
            problems.append(f"{REGISTRY}:{n}: {name} is registered twice")
            continue
        out.append(Contract(name, f"docs/{path}", section, kind, int(at)))
    return out, problems


def section_span(text: str, number: str) -> tuple[int, int] | None:
    """The 0-based line range of the section numbered ``number``, up to the next heading of its level or higher."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if m and re.match(rf"{re.escape(number)}[. ]", m.group(2)):
            level = len(m.group(1))
            for j in range(i + 1, len(lines)):
                h = HEADING.match(lines[j])
                if h and len(h.group(1)) <= level:
                    return i, j
            return i, len(lines)
    return None


def in_scope(files: dict[str, str]) -> dict[str, str]:
    return {
        rel: text for rel, text in files.items() if SCOPE.match(rel) and rel != REGISTRY and not SUPERSEDED.search(text)
    }


def markers(files: dict[str, str]) -> dict[str, list[tuple[str, int, tuple[str, ...]]]]:
    """Each marker name, with every (file, 0-based line, named members) that carries it, across the docs tree."""
    found: dict[str, list[tuple[str, int, tuple[str, ...]]]] = {}
    for rel, text in sorted(files.items()):
        if not rel.startswith("docs/") or not rel.endswith(".md"):
            continue
        for i, line in enumerate(text.split("\n")):
            m = MARKER.match(line)
            if m:
                found.setdefault(m.group(1), []).append((rel, i, tuple((m.group(2) or "").split())))
    return found


def owner_block(
    files: dict[str, str], c: Contract, where: list[tuple[str, int, tuple[str, ...]]]
) -> tuple[Block | None, list[str]]:
    """The defining block of a registered contract, or the problems that stop the check from finding it."""
    if len(where) != 1:
        places = ", ".join(f"{r}:{i + 1}" for r, i, _ in where) or "nowhere"
        return None, [f"{c.name}: needs exactly one `<!-- contract: {c.name} -->` marker, found at {places}"]
    rel, line, _ = where[0]
    text = files.get(c.path)
    span = None if text is None else section_span(text, c.section)
    if rel != c.path or span is None or not span[0] < line < span[1]:
        return None, [f"{c.name}: its marker ({rel}:{line + 1}) is not inside {c.path} §{c.section}"]
    after = [b for b in blocks(files[rel]) if b.start > line]
    if not after or HEADING.match(after[0].lines[0]) or MARKER.match(after[0].lines[0]):
        return None, [f"{c.name}: no defining block follows its marker ({rel}:{line + 1})"]
    return list_run(after), []


def list_run(after: list[Block]) -> Block:
    """The first block, extended over the list items that follow it without a break: a list defines as a whole."""
    lines = list(after[0].lines)
    for b in after[1:]:
        if not ITEM.match(lines[0]) or not ITEM.match(b.lines[0]) or b.start != after[0].start + len(lines):
            break
        lines += b.lines
    return Block(after[0].start, tuple(lines))


def restatements(scope: dict[str, str], c: Contract, defined: list[str], owners: set[tuple[str, int]]) -> list[str]:
    """Blocks outside every owner block that hold enough of ``c``'s members to restate it. An owner block defines its
    own contract and may name another's members (``kind_rank`` names the kinds it ranks)."""
    need = 1 if c.kind == "signature" else min(c.threshold, len(defined))
    out = []
    for rel, text in sorted(scope.items()):
        for b in blocks(text):
            if (rel, b.start) in owners:
                continue
            spans = set(SPAN.findall("\n".join(b.lines)))
            hit = [m for m in defined if m in spans]
            if len(hit) >= need:
                shown = ", ".join(f"`{m}`" for m in hit[:4])
                out.append(f"{rel}:{b.start + 1}: restates {c.name} ({shown}); link to {c.path} §{c.section} instead")
    return out


def structural(files: dict[str, str]) -> list[str]:
    """No fold table and no decision table inside a design document."""
    out = []
    for rel, text in sorted(files.items()):
        if not DESIGN.match(rel) or rel == REGISTRY:
            continue
        for m in FOLD.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            out.append(f"{rel}:{line}: a fold table belongs in docs/design/reviews/, not in a design")
        for b in blocks(text):
            head = b.lines[0]
            cells = [x.strip() for x in head.strip().strip("|").split("|")] if head.startswith("|") else []
            if len(cells) > 1 and re.match(r"(Decision|Ruling)\b", cells[1]):
                out.append(f"{rel}:{b.start + 1}: a decision table belongs in docs/design/decisions/")
    return out


def resolve(
    files: dict[str, str], contracts: list[Contract], found: dict[str, list[tuple[str, int, tuple[str, ...]]]]
) -> tuple[list[tuple[Contract, Block, list[str]]], list[str]]:
    """Each registered contract with its owner block and members, or the problems that keep it from being checked."""
    resolved: list[tuple[Contract, Block, list[str]]] = []
    problems: list[str] = []
    for c in contracts:
        block, missing = owner_block(files, c, found.get(c.name, []))
        problems += missing
        if block is None:
            continue
        named = found[c.name][0][2]
        if c.kind == "signature" and named:
            named = (" ".join(named),)  # a signature is one span, spaces and all
        absent = [m for m in named if m not in SPAN.findall("\n".join(block.lines))]
        defined = list(named) or members(block, c.kind)
        if absent:
            problems.append(f"{c.name}: its marker names {absent}, which its block doesn't hold as code spans")
        elif c.kind == "vocabulary" and len(defined) < 3:
            problems.append(f"{c.name}: a vocabulary needs at least 3 members to check, found {defined}")
        elif not defined:
            problems.append(f"{c.name}: its defining block holds no code span")
        else:
            resolved.append((c, block, defined))
    return resolved, problems


def check_contracts(files: dict[str, str]) -> list[str]:
    contracts, problems = registry(files)
    found = markers(files)
    registered = {c.name for c in contracts}
    problems += [
        f"{r}:{i + 1}: marker {n} has no row in {REGISTRY}"
        for n, w in found.items()
        if n not in registered
        for r, i, _ in w
    ]
    resolved, unresolved = resolve(files, contracts, found)
    owners = {(c.path, b.start + k) for c, b, _ in resolved for k in range(len(b.lines))}
    scope = in_scope(files)
    for c, _, defined in resolved:
        problems += restatements(scope, c, defined, owners)
    return problems + unresolved + structural(files)
