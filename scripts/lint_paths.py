"""Standards check 9: no home directory in the tree (CLAUDE.md, "No personal details in the tree").

The repository is public, and a path under someone's home names them. The check refuses one in any tracked or
untracked text file, and in any file's own path. Homes are told from ordinary directories by their spelling:
- ``Users`` and ``home``, spelled as the operating systems spell them, after any separator, wherever they sit in a
  path: ``/Users/<name>``, ``/home/<name>``, ``C:\\Users\\<name>``, Git Bash's ``/c/Users/<name>``, WSL's
  ``/mnt/c/Users/<name>``, ``/Volumes/<disk>/Users/<name>``, ``file://localhost/Users/<name>``;
- any other case (``/users/<name>``, ``c:\\users\\<name>``) only where a path starts, because inside a path a
  lower-case ``users/`` is a directory like any other (``docs/users/`` in the tree);
- separators single, repeated, escaped (``C:\\\\Users\\\\``, JSON's ``\\/Users\\/``) or URL-encoded (``%2FUsers%2F``,
  ``%5CUsers%5C``);
- the dash-encoded ``-Users-<name>-`` that a session's scratchpad carries
  (``/private/tmp/claude-<uid>/-Users-<name>-<repo>/``), which the first scrub's search for ``/Users/`` missed, where
  an encoded path starts (not after a letter or digit, so "Power-Users-guide" is prose).
A placeholder (``<home>``, ``<scratchpad>``), an elision (``/Users/…``), a variable (``/Users/$USER``) and ``~/``
name nobody and pass, as do the public accounts in ``PUBLIC_ACCOUNTS`` and Godot's paths (``NOT_A_DISK``: ``res://``,
``user://`` and files under ``client/``). Any other directory spelled exactly ``Users`` or ``home`` is refused wherever
it sits, web URLs' included, because it can't be told from a home: name it otherwise.

A finding names the file and line, never the name it matched; a file's path is printed cut where the name starts
(``masked``). CI's logs are public.

It can't see a name outside a path (an ``ls -l`` owner column, an account named in prose), a name starting with a
character a name rarely starts with (``.``, ``@``, ``+``, an emoji), a hostname, a private address, text that isn't
UTF-8, a symlink's target, or a dash-encoded home after an encoded prefix (``-Volumes-Data-Users-<name>-``), and a
file's path holding a home it can't see is printed as it stands on its lines' findings: B45.
"""

from __future__ import annotations

import re

# Separators: slashes or backslashes, single, repeated or JSON-escaped (``\/``), or URL-encoded (%2F, %5C).
_SEP = r"(?:[\\/]|(?i:%2f|%5c))+"
# A name is whatever follows the home's separator, from a character a name can start with (a word character in any
# script, or ``%`` for a URL-encoded one) to the next separator, quote or bracket. Only ``_account`` reads where it
# ends; a finding never prints any of it (``masked``).
_NAME = r"(?P<name>[\w%][^\s\\/<>\"'`|()\[\],;]*)"
_EXACT = rf"{_SEP}(?:Users|home){_SEP}"
_AT_START = rf"(?<![\w.-])(?i:(?:/+|%2f)(?:users|home)|[a-z]:{_SEP}users){_SEP}"
PATH_HOME = re.compile(rf"(?:{_EXACT}|{_AT_START}){_NAME}")
# A home as Claude Code encodes a project directory: its slashes are dashes.
DASH_HOME = re.compile(r"(?<![^\W_])-(?i:users|home)-(?P<name>[\w%][\w.%]*)")
# Godot's res:// and user:// paths are the project's and the player's, on no one's disk: a game's own home/ directory
# is one. A path under client/ is one too, since Godot's res:// is that directory. Only the exact spelling is skipped
# inside them (a dash-encoded scratchpad still counts), and only to the next quote, comma, bracket or space: a JSON
# line goes on past the token. Web URLs aren't skipped: a dev server's or a query's path is on a disk.
NOT_A_DISK = re.compile(r"(?:(?i:\b(?:res|user)://)|(?<![\w./-])client/)[^\s\"'`,;()<>\[\]]*")
# Accounts whose name is public: GitHub's hosted runners (/Users/runner, /home/runner) and macOS's shared folder.
PUBLIC_ACCOUNTS = frozenset({"runner", "Shared"})
ADVICE = "write <home>, <scratchpad> or a path relative to the repository (the repository is public)"


def _account(name: str) -> str:
    """The account a name begins with: up to an encoded separator, without a trailing ``-`` or ``.``, so
    ``runner-<name>`` and a sentence's full stop leave ``runner``."""
    return re.split(r"(?i)%2f|%5c", name)[0].rstrip("-.")


def _private(text: str) -> list[re.Match[str]]:
    """The homes in ``text`` whose account isn't public. A path form inside a Godot path (``NOT_A_DISK``), a file's
    own path under ``client/`` among them, is the project's directory, not a home."""
    godot = [m.span() for m in NOT_A_DISK.finditer(text)]
    paths = [m for m in PATH_HOME.finditer(text) if not any(a <= m.start() < b for a, b in godot)]
    found = [*paths, *DASH_HOME.finditer(text)]
    return [m for m in found if _account(m["name"]) not in PUBLIC_ACCOUNTS]


def masked(text: str) -> str:
    """``text`` cut where its first private name starts and ended ``<name>…``. Where a name ends can't be known
    (combining marks, a space in a Windows profile, a dash-encoded first and last name), so nothing after the start
    is printed: CI's logs are public."""
    starts = [m.start("name") for m in _private(text)]
    return text[: min(starts)] + "<name>…" if starts else text


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
