"""Standards check 7: one owner per contract (CLAUDE.md, "One owner per contract"; B36).

A contract that other modules depend on is stated in one section of one design document, its owner; every other
document links to it. ``docs/design/contracts.md`` registers each checked contract as a table row:

    | `<name>` | `<path under docs/>` §<number> | vocabulary or signature | <restates at> |

and the owner section carries ``<!-- contract: <name>: <members> | not: <spans> -->`` on the line before the block
that defines it: one list item (with its nested lines), a table or a paragraph. A list owner is its first item, so a
vocabulary written one member per bullet is owned as a table or as one item that lists it.

- **The marker is tied to its text both ways.** Each member it names is a code span in the block; and every code span
  in the block's member positions (a table's first column, any span of an item or paragraph) is either named or
  listed after ``not:``. A member the text gains without the marker fails, and an exclusion is said aloud; a stale
  exclusion, a span both named and excluded, or anything but ``not:`` after the bar fails too.
- **A restatement** is any block in scope (a paragraph, a table, or a run of list items, so a copy one member per
  bullet counts) that holds the row's *restates at* count of members outside the contract's own owner lines. A
  signature's one span (an ordering key) restates wherever it appears.
- Every row has exactly one marker, inside the section it names; every marker has a row; a vocabulary names at least
  three members.
- No design document holds a fold table, a decision table, or a list of rulings (``- **D20.``, ``**Ruled …:**``):
  those are records (``docs/design/reviews/``, ``docs/design/decisions/``).

Scope: ``docs/design/*.md``, ``docs/plans/*.md``, ``docs/roadmap.md`` and ``docs/architecture.md``. Records
(``reviews/``, ``decisions/``, ``research/``) sit in subdirectories and are out of scope, and so is a design whose
header (the text before its first section) carries a ``> **Superseded`` banner. Markers in fenced code are quotation.
The check sees code spans, not prose: a rule restated in words, a copy below a row's count, and an unregistered
contract stay with review (B36).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

REGISTRY = "docs/design/contracts.md"
KINDS = {"vocabulary", "signature"}
MARKER = re.compile(r"^<!-- contract: ([a-z0-9_.-]+)(?:: ([^>]*?))? -->\s*$")
SUPERSEDED = re.compile(r"^> \*\*Superseded(?! in part)", re.M)  # a partial supersession leaves the design live
SCOPE = re.compile(r"^docs/(design|plans)/[^/]+\.md$|^docs/(roadmap|architecture)\.md$")
DESIGN = re.compile(r"^docs/design/[^/]+\.md$")
SPAN = re.compile(r"`([^`\n]+)`")
HEADING = re.compile(r"^(#{1,6}) (.*)$")
ITEM = re.compile(r"^(?:[-*]|\d+\.) ")
LEAD = re.compile(r"^(?:[-*]|\d+\.) (?:\*\*)?`([^`\n]+)`")  # an item that starts with a code span
ROW = re.compile(r"^\| `([a-z0-9_.-]+)` \| `([^`]+)` §(\d+(?:\.\d+)*) \| (\w+) \| (\d+) \|\s*$")
FOLD = re.compile(r"^#{1,6} Fold table", re.M)
RULING = re.compile(
    r"^(?:(?:[-*]|\d+\.) )?\*\*(?:(?:O|OA|D|T|VS)\d+[a-z]?[.:*]|Ruled\b)", re.M
)  # "- **D20.", "**D20.", "1. **O3.", "**Ruled 2026-…:**", "- **Ruled …"


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
    """Runs of non-blank lines; a heading or a marker is a block of its own, and a fenced code block is one block. A
    table or a run of list items is one block, so a vocabulary spread over its rows or bullets is a restatement."""
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
        if not cur:
            start = i
        cur.append(line)
    if cur:
        out.append(Block(start, tuple(cur)))
    return out


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
        if int(at) < 1:
            problems.append(f"{REGISTRY}:{n}: {name}'s restates at is {at}; it must be at least 1")
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
        if m and re.match(rf"{re.escape(number)}\.?\s", m.group(2)):
            level = len(m.group(1))
            for j in range(i + 1, len(lines)):
                h = HEADING.match(lines[j])
                if h and len(h.group(1)) <= level:
                    return i, j
            return i, len(lines)
    return None


def header(text: str) -> str:
    """A document's lead, before its first section: where a superseded banner says the whole document is history."""
    m = re.search(r"^## ", text, re.M)
    return text[: m.start()] if m else "\n\n".join(text.split("\n\n")[:3])  # no sections: its lead paragraphs


def in_scope(files: dict[str, str]) -> dict[str, str]:
    return {
        rel: text
        for rel, text in files.items()
        if SCOPE.match(rel) and rel != REGISTRY and not SUPERSEDED.search(header(text))
    }


@dataclass(frozen=True)
class Marker:
    rel: str
    line: int  # 0-based
    named: tuple[str, ...]  # the members (a signature names its one span)
    excluded: tuple[str, ...]  # code spans in the marked block that are not members, said aloud
    keyword: str  # what follows the "|": "not:", or "" when there is none


def parse_marker(rel: str, line: int, body: str | None) -> Marker:
    named, bar, rest = (body or "").partition("|")
    keyword = rest.split()[0] if rest.split() else bar
    return Marker(rel, line, items(named), items(rest.strip().removeprefix("not:")), keyword)


def items(text: str) -> tuple[str, ...]:
    """Whitespace-separated words, where a backticked item may hold spaces: ``a `(b, c)` d``."""
    return tuple(span or word for span, word in re.findall(r"`([^`]+)`|(\S+)", text))


def markers(files: dict[str, str]) -> dict[str, list[Marker]]:
    """Each marker name, with every marker that carries it, across the docs tree (fenced code is quotation)."""
    found: dict[str, list[Marker]] = {}
    for rel, text in sorted(files.items()):
        if not rel.startswith("docs/") or not rel.endswith(".md"):
            continue
        fenced = False
        for i, line in enumerate(text.split("\n")):
            fenced = fenced != line.startswith("```")
            m = None if fenced else MARKER.match(line)
            if m:
                found.setdefault(m.group(1), []).append(parse_marker(rel, i, m.group(2)))
    return found


def owner_block(files: dict[str, str], c: Contract, where: list[Marker]) -> tuple[Block | None, list[str]]:
    """The block a contract's one marker marks: the list item, table or paragraph after it."""
    if len(where) != 1:
        places = ", ".join(f"{m.rel}:{m.line + 1}" for m in where) or "nowhere"
        return None, [f"{c.name}: needs exactly one `<!-- contract: {c.name} -->` marker, found at {places}"]
    rel, line = where[0].rel, where[0].line
    text = files.get(c.path)
    span = None if text is None else section_span(text, c.section)
    if rel != c.path or span is None or not span[0] < line < span[1]:
        return None, [f"{c.name}: its marker ({rel}:{line + 1}) is not inside {c.path} §{c.section}"]
    after = [b for b in blocks(files[rel]) if b.start > line]
    if not after or HEADING.match(after[0].lines[0]) or MARKER.match(after[0].lines[0]):
        return None, [f"{c.name}: no defining block follows its marker ({rel}:{line + 1})"]
    return first_item(after[0]), []


def first_item(block: Block) -> Block:
    """A list's first item, with its nested lines; any other block whole."""
    if not ITEM.match(block.lines[0]):
        return block
    end = next((k for k, ln in enumerate(block.lines[1:], 1) if ITEM.match(ln)), len(block.lines))
    return Block(block.start, block.lines[:end])


def member_positions(block: Block) -> list[str]:
    """The code spans that must each be a member or an exclusion: a table's first column, else every span."""
    if not block.lines[0].startswith("|"):
        return SPAN.findall("\n".join(block.lines))
    rows = [ln for ln in block.lines if not re.fullmatch(r"\|[\s:|-]*\|", ln.strip())][1:]  # skip the header
    return [s for ln in rows for s in SPAN.findall(ln.strip().strip("|").split("|")[0])]


def restatements(scope: dict[str, str], c: Contract, defined: list[str], owner: set[tuple[str, int]]) -> list[str]:
    """Blocks that hold the row's count of ``c``'s members outside ``c``'s own owner lines."""
    need = 1 if c.kind == "signature" else min(c.threshold, len(defined))
    out = []
    for rel, text in sorted(scope.items()):
        for b in blocks(text):
            kept = [ln for k, ln in enumerate(b.lines) if (rel, b.start + k) not in owner]
            hit = max((([m for m in defined if m in spans]) for spans in counted_spans(kept)), key=len, default=[])
            if len(hit) >= need:
                shown = ", ".join(f"`{m}`" for m in hit[:4])
                out.append(f"{rel}:{b.start + 1}: restates {c.name} ({shown}); link to {c.path} §{c.section} instead")
    return out


def counted_spans(lines: list[str]) -> list[set[str]]:
    """The span sets a restatement is counted over. A paragraph or a table is one set. A list is each item on its own,
    plus the spans its items lead with (`- `a`: …`), so a copy one member per bullet counts and mentions scattered
    through a long list don't add up."""
    if not lines or not ITEM.match(lines[0]):
        return [set(SPAN.findall("\n".join(lines)))]
    items: list[list[str]] = []
    for ln in lines:
        if ITEM.match(ln) or not items:
            items.append([])
        items[-1].append(ln)
    heads = {m.group(1) for it in items if (m := LEAD.match(it[0]))}
    return [heads] + [set(SPAN.findall("\n".join(it))) for it in items]


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
        for m in RULING.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            out.append(f"{rel}:{line}: a list of rulings belongs in docs/design/decisions/")
    return out


def resolve(
    files: dict[str, str], contracts: list[Contract], found: dict[str, list[Marker]]
) -> tuple[list[tuple[Contract, Block, list[str]]], list[str]]:
    """Each registered contract with its owner block and members, or the problems that keep it from being checked."""
    resolved: list[tuple[Contract, Block, list[str]]] = []
    problems: list[str] = []
    for c in contracts:
        block, missing = owner_block(files, c, found.get(c.name, []))
        problems += missing
        if block is None:
            continue
        marker = found[c.name][0]
        defined = [" ".join(marker.named)] if c.kind == "signature" and marker.named else list(marker.named)
        problem = marker_problem(c, block, marker, defined)
        if problem:
            problems.append(problem)
        elif c.kind == "vocabulary" and len(defined) < 3:
            problems.append(f"{c.name}: a vocabulary needs at least 3 members to check, found {defined}")
        else:
            resolved.append((c, block, defined))
    return resolved, problems


def marker_problem(c: Contract, block: Block, marker: Marker, defined: list[str]) -> str | None:
    """Why a marker doesn't match the text it marks, both ways, or None."""
    spans = SPAN.findall("\n".join(block.lines))
    positions = member_positions(block)
    if not defined:
        return f"{c.name}: its marker names no members"
    if marker.keyword == "|":
        return f"{c.name}: its marker has a '|' with nothing after it"
    if marker.keyword not in ("", "not:"):
        return f"{c.name}: its marker reads {marker.keyword!r} after '|'; only 'not:' may follow it"
    checks = [
        ([m for m in defined if m not in spans], "its marker names {}, which its block doesn't hold as code spans"),
        ([m for m in defined if m in marker.excluded], "its marker both names and excludes {}"),
        ([x for x in marker.excluded if x not in positions], "its marker excludes {}, which its block doesn't hold"),
        (
            [] if c.kind == "signature" else unnamed(block, defined, marker.excluded),
            "its block holds {}, which its marker neither names nor excludes",
        ),
    ]
    return next((f"{c.name}: " + text.format(found) for found, text in checks if found), None)


def unnamed(block: Block, defined: list[str], excluded: tuple[str, ...]) -> list[str]:
    """Spans in the block's member positions that the marker doesn't account for: a member the text gained."""
    return list(dict.fromkeys(s for s in member_positions(block) if s not in defined and s not in excluded))


def check_contracts(files: dict[str, str]) -> list[str]:
    contracts, problems = registry(files)
    found = markers(files)
    registered = {c.name for c in contracts}
    problems += [
        f"{r}:{i + 1}: marker {n} has no row in {REGISTRY}"
        for n, w in found.items()
        if n not in registered
        for r, i in [(m.rel, m.line) for m in w]
    ]
    resolved, unresolved = resolve(files, contracts, found)
    scope = in_scope(files)
    for c, b, defined in resolved:
        problems += restatements(scope, c, defined, {(c.path, b.start + k) for k in range(len(b.lines))})
    return problems + unresolved + structural(files)
