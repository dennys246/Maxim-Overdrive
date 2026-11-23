"""Standards check 8: no home directory in the tree (CLAUDE.md, "No personal details in the tree").

The repository is public, and a path under someone's home names them. The check refuses every spelling of one in any
tracked or untracked text file: ``/Users/<name>``, ``/home/<name>``, ``C:\\Users\\<name>``, and the dash-encoded
``-Users-<name>-`` that a session's scratchpad directory carries (``/private/tmp/claude-<uid>/-Users-<name>-<repo>/``),
which the first scrub's search for ``/Users/`` missed. A placeholder (``<home>``, ``<scratchpad>``), an elision
(``/Users/…``) and ``~/`` name nobody and pass, as do the public accounts in ``PUBLIC_ACCOUNTS``.

A finding names the file and line, never the name it matched: CI's logs are public too.

It can't see a name outside a path (an ``ls -l`` owner column), a hostname or a private address: B44.
"""

from __future__ import annotations

import re

# The home roots, as paths and as Claude Code's dash-encoded project directories.
HOME = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\Users\\|-Users-|-home-)(?P<name>[A-Za-z0-9_][A-Za-z0-9._]*)")
# Accounts whose name is public: GitHub's hosted runners (/Users/runner, /home/runner) and macOS's shared folder.
PUBLIC_ACCOUNTS = frozenset({"runner", "Shared"})


def check_paths(files: dict[str, str]) -> list[str]:
    """One finding per line that holds a home directory not in ``PUBLIC_ACCOUNTS``."""
    problems = []
    for rel, text in sorted(files.items()):
        for number, line in enumerate(text.splitlines(), start=1):
            if any(m["name"] not in PUBLIC_ACCOUNTS for m in HOME.finditer(line)):
                problems.append(
                    f"{rel}:{number}: a path under someone's home directory; write <home>, <scratchpad> or a path "
                    "relative to the repository (the repository is public)"
                )
    return problems
