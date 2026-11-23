"""Standards check 8: no home directory in the tree (CLAUDE.md, "No personal details in the tree").

The repository is public, and a path under someone's home names them. The check refuses one in any tracked or
untracked text file, and in any file's own path. Homes are told from ordinary directories by their spelling:
- ``Users`` and ``home``, spelled as the operating systems spell them, after any separator, wherever they sit in a
  path: ``/Users/<name>``, ``/home/<name>``, ``C:\\Users\\<name>``, Git Bash's ``/c/Users/<name>``, WSL's
  ``/mnt/c/Users/<name>``, ``/Volumes/<disk>/Users/<name>``, ``file://localhost/Users/<name>``;
- any other case (``/users/<name>``, ``c:\\users\\<name>``) only where a path starts, because inside a path a
  lower-case ``users/`` is a directory like any other (``docs/users/`` in the tree);
- separators single, repeated, escaped (``C:\\\\Users\\\\``) or URL-encoded (``%2FUsers%2F``);
- the dash-encoded ``-Users-<name>-`` that a session's scratchpad carries
  (``/private/tmp/claude-<uid>/-Users-<name>-<repo>/``), which the first scrub's search for ``/Users/`` missed, where
  an encoded path starts (not after a letter or digit, so "Power-Users-guide" is prose).
A placeholder (``<home>``, ``<scratchpad>``), an elision (``/Users/…``) and ``~/`` name nobody and pass, as do the
public accounts in ``PUBLIC_ACCOUNTS``.

A finding names the file and line, never the name it matched (a path is printed with it masked): CI's logs are public.

It can't see a name outside a path (an ``ls -l`` owner column, an account named in prose), a hostname, a private
address, text that isn't UTF-8, a symlink's target, or a dash-encoded home after an encoded prefix
(``-Volumes-Data-Users-<name>-``): B45.
"""

from __future__ import annotations

import re

_SEP = r"(?:\\+|/+|(?i:%2f))"
# A name runs to the next separator, so ``runner-x`` is not ``runner``. It never ends in ``-``, so ``runner-<name>`` is
# a placeholder. ``\w`` is Unicode's: a profile named in any script is a name.
_NAME = r"(?P<name>\w(?:[\w.-]*\w)?)"
_EXACT = rf"{_SEP}(?:Users|home){_SEP}"
_AT_START = rf"(?<![\w.-])(?i:(?:/+|%2f)(?:users|home)|[a-z]:{_SEP}users){_SEP}"
PATH_HOME = re.compile(rf"(?:{_EXACT}|{_AT_START}){_NAME}")
# A home as Claude Code encodes a project directory: its slashes are dashes, so the name ends at the next dash.
DASH_HOME = re.compile(r"(?<![^\W_])-(?i:users|home)-(?P<name>\w[\w.]*)")
# Accounts whose name is public: GitHub's hosted runners (/Users/runner, /home/runner) and macOS's shared folder.
PUBLIC_ACCOUNTS = frozenset({"runner", "Shared"})
ADVICE = "write <home>, <scratchpad> or a path relative to the repository (the repository is public)"


def _private(text: str) -> list[re.Match[str]]:
    """The homes in ``text`` whose account isn't public."""
    found = [*PATH_HOME.finditer(text), *DASH_HOME.finditer(text)]
    return [m for m in found if m["name"] not in PUBLIC_ACCOUNTS]


# The rest of a dash-encoded path component: an encoded name's end can't be told (``-Users-<first>-<last>-<repo>``).
_COMPONENT_REST = re.compile(r"[^/\\\s`'\"]*")


def _span(match: re.Match[str], text: str) -> tuple[int, int]:
    """The characters a match's name may occupy: to the separator for a path, to the component's end for a dash form."""
    if match.re is DASH_HOME:
        rest = _COMPONENT_REST.match(text, match.end("name"))
        return match.start("name"), rest.end() if rest else match.end("name")
    return match.start("name"), match.end("name")


def masked(text: str) -> str:
    """``text`` with each private account name written ``<name>``, so a finding shows a path without publishing it.
    Overlapping spans (a dash form inside a path form's name) merge, so no letter of either leaks."""
    spans: list[list[int]] = []
    for start, end in sorted(_span(m, text) for m in _private(text)):
        if spans and start <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], end)
        else:
            spans.append([start, end])
    for start, end in reversed(spans):
        text = text[:start] + "<name>" + text[end:]
    return text


def check_paths(files: dict[str, str]) -> list[str]:
    """One finding per file path and per line that holds a home directory not in ``PUBLIC_ACCOUNTS``."""
    problems = []
    for rel, text in sorted(files.items()):
        shown = masked(rel)
        if shown != rel:
            problems.append(f"{shown}: its path is under someone's home directory; {ADVICE}")
        for number, line in enumerate(text.splitlines(), start=1):
            if _private(line):
                problems.append(f"{shown}:{number}: a path under someone's home directory; {ADVICE}")
    return problems
