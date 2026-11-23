"""Standards check 8: no home directory in the tree (CLAUDE.md, "No personal details in the tree").

The repository is public, and a path under someone's home names them. The check refuses one in any tracked or
untracked text file, and in any file's own path, in these spellings, in any case: ``/Users/<name>``, ``/home/<name>``,
a drive's ``C:\\Users\\<name>`` (or WSL's ``/mnt/c/Users/<name>``) with its separators single, escaped or forward,
the URL-encoded ``%2FUsers%2F<name>``, and the dash-encoded ``-Users-<name>-`` that a session's scratchpad carries
(``/private/tmp/claude-<uid>/-Users-<name>-<repo>/``), which the first scrub's search for ``/Users/`` missed. Each
counts only where a path can start, so ``docs/users/`` (a directory inside a repository) and "Power-Users-guide" pass.
A placeholder (``<home>``, ``<scratchpad>``), an elision (``/Users/…``) and ``~/`` name nobody and pass, as do the
public accounts in ``PUBLIC_ACCOUNTS``.

A finding names the file and line, never the name it matched (a path is printed with it masked): CI's logs are public.

It can't see a name outside a path (an ``ls -l`` owner column, an account named in prose), a hostname, a private
address, or text that isn't UTF-8: B45.
"""

from __future__ import annotations

import re

_SEP = r"(?:\\+|/+|%2f)"
# A home as a path. It starts a path, so ``docs/users/`` (a directory inside one) is not a home; WSL's ``/mnt/c/Users``
# is a drive's, named on its own. The name runs to the next separator, so ``runner-x`` is not ``runner``, and never
# ends in ``-``, so ``runner-<name>`` is a placeholder.
_ROOT = rf"(?<![a-z0-9._-])(?:(?:/+|%2f)(?:users|home)|(?:[a-z]:|/mnt/[a-z]){_SEP}users)"
PATH_HOME = re.compile(
    rf"{_ROOT}{_SEP}(?P<name>[a-z0-9_](?:[a-z0-9._-]*[a-z0-9_])?)",
    re.IGNORECASE,
)
# A home as Claude Code encodes a project directory: its slashes are dashes, so the name ends at the next dash.
DASH_HOME = re.compile(r"(?<![a-z0-9])-(?:users|home)-(?P<name>[a-z0-9_][a-z0-9._]*)", re.IGNORECASE)
# Accounts whose name is public: GitHub's hosted runners (/Users/runner, /home/runner) and macOS's shared folder.
PUBLIC_ACCOUNTS = frozenset({"runner", "Shared"})
ADVICE = "write <home>, <scratchpad> or a path relative to the repository (the repository is public)"


def _private(text: str) -> list[re.Match[str]]:
    """The homes in ``text`` whose account isn't public."""
    found = [*PATH_HOME.finditer(text), *DASH_HOME.finditer(text)]
    return [m for m in found if m["name"] not in PUBLIC_ACCOUNTS]


def masked(text: str) -> str:
    """``text`` with each private account name written ``<name>``, so a finding shows a path without publishing it."""
    for m in sorted(_private(text), key=lambda m: m.start("name"), reverse=True):
        text = text[: m.start("name")] + "<name>" + text[m.end("name") :]
    return text


def check_paths(files: dict[str, str]) -> list[str]:
    """One finding per file path and per line that holds a home directory not in ``PUBLIC_ACCOUNTS``."""
    problems = []
    for rel, text in sorted(files.items()):
        if _private(rel):
            problems.append(f"{masked(rel)}: its path is under someone's home directory; {ADVICE}")
        for number, line in enumerate(text.splitlines(), start=1):
            if _private(line):
                problems.append(f"{rel}:{number}: a path under someone's home directory; {ADVICE}")
    return problems
