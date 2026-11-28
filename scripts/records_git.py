"""What the records tooling reads from git: the base, the lines a branch added, and files at a commit.

The base of every comparison is the merge base with a freshly fetched ``origin/main``, never local ``main``, which
may be days behind (records_layout §5, RL12). A command that rewrites by the branch's own lines refuses to run during
an uncommitted merge, when the working tree holds ``main``'s incoming lines as if they were the branch's.

Every call goes through ``_git`` with the environment its caller hands in: the command line hands in its own (it
reads the repository it is run in), and a test hands in one with every ``GIT_*`` dropped.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _git(
    root: Path, env: Mapping[str, str], args: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, env=dict(env), capture_output=True, text=True, check=check)


@dataclass(frozen=True)
class Hunk:
    """One hunk of a file's diff against the base: the base lines it removed and the new lines it added (1-based)."""

    removed: tuple[str, ...]
    added: tuple[int, ...]


@dataclass(frozen=True)
class Git:
    """The repository at ``root``, run with ``env`` (required: a test must not inherit someone else's ``GIT_DIR``)."""

    root: Path
    env: Mapping[str, str] = field(repr=False)

    def run(self, *args: str, check: bool = True) -> str:
        return _git(self.root, self.env, list(args), check=check).stdout

    def ok(self, *args: str) -> bool:
        return _git(self.root, self.env, list(args), check=False).returncode == 0

    def merging(self) -> bool:
        """True during an uncommitted merge (``MERGE_HEAD`` exists)."""
        return self.ok("rev-parse", "-q", "--verify", "MERGE_HEAD")

    def fetch_base(self, remote: str = "origin", branch: str = "main") -> str:
        """Fetch ``remote/branch`` now and return the merge base of HEAD with it (RL12)."""
        self.run("fetch", "-q", remote, branch)
        return self.run("merge-base", "HEAD", f"{remote}/{branch}").strip()

    def merge_base(self, ref: str, other: str = "HEAD") -> str:
        return self.run("merge-base", other, ref).strip()

    def files_at(self, rev: str, prefixes: tuple[str, ...] = ()) -> dict[str, str]:
        """Every Markdown file at ``rev`` under ``prefixes`` (all when none), by repository path: the records, their
        headers, the generated files and the drafts, which are all the tooling reads. Blobs only, so a submodule's
        entry is never shown, and Markdown only, so nothing binary is decoded."""
        entries = self.run("ls-tree", "-r", "-z", rev, "--", *prefixes).split("\0")
        blobs = [e.split("\t", 1)[1] for e in entries if e.split(" ", 2)[1:2] == ["blob"]]
        return {rel: self.run("show", f"{rev}:{rel}") for rel in blobs if rel.endswith(".md")}

    def hunks(self, base: str, head: str | None = None) -> dict[str, list[Hunk]]:
        """Each changed file's hunks against ``base``: of the working tree (untracked files included, every line
        added), or of commit ``head`` when given. Renames are not followed: a moved line is a removed and an added
        one, so a moved citation counts as the branch's own."""
        # fixed prefixes and unquoted names, whatever the user's config says (diff.noprefix, core.quotePath)
        diff = ["-c", "core.quotePath=false", "diff", "-U0", "--no-renames", "--no-color", "--src-prefix=a/",
                "--dst-prefix=b/", base, *([head] if head else []), "--"]  # fmt: skip
        found: dict[str, list[tuple[list[str], range]]] = {}
        current: str | None = None
        for line in self.run(*diff).split("\n"):
            if line.startswith("diff --git "):
                current = None  # the next file's header lines ("--- a/x") are never content
            elif line.startswith("+++ ") and current is None:
                current = None if line == "+++ /dev/null" else line[6:].removesuffix("\t")
            elif (m := _HUNK.match(line)) and current is not None:
                start, count = int(m.group(3)), 1 if m.group(4) is None else int(m.group(4))
                found.setdefault(current, []).append(([], range(start, start + count)))
            elif line.startswith("-") and current in found:
                found[current][-1][0].append(line[1:])
        out = {rel: [Hunk(tuple(r), tuple(a)) for r, a in hunks] for rel, hunks in found.items()}
        if head is None:
            for rel in filter(None, self.run("ls-files", "-z", "-o", "--exclude-standard").split("\0")):
                try:
                    count = len((self.root / rel).read_text(encoding="utf-8").split("\n"))
                except UnicodeDecodeError:  # binary: no lines to cite in, and no citations to rewrite
                    continue
                out[rel] = [Hunk((), tuple(range(1, count + 1)))]
        return out
