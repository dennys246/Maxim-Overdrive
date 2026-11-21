"""Fetch the pinned MaCFP files into the git-ignored cache, verified against the pinned commit's tree.

The tree comes from `gh api` at the pinned commit; each file comes from its raw URL at that commit, and its git blob
SHA-1 must equal the tree's, so a file in the cache is byte for byte the pinned one. Downloads are untrusted data:
only `.csv`, `.CSV` and `.md` files are fetched, they are written under `cache/` by their repository path (which
must stay inside it), and nothing here executes them.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

import pins

CACHE = Path(__file__).resolve().parent / "cache"
COMMIT_FILE = CACHE / "commit.json"
TREE_FILE = CACHE / "tree.json"
ALLOWED_SUFFIXES = (".csv", ".md")


def git_blob_sha1(data: bytes) -> str:
    """Git's object id for a blob: SHA-1 over "blob <size>\\0" and the bytes."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def gh_api(endpoint: str, dest: Path) -> dict[str, object]:
    """A GitHub API response as JSON, fetched once with `gh api` and then read from the cache."""
    if not dest.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        out = subprocess.run(["gh", "api", endpoint], check=True, capture_output=True).stdout
        dest.write_bytes(out)
    loaded: dict[str, object] = json.loads(dest.read_text(encoding="utf-8"))
    return loaded


def load_tree() -> dict[str, dict[str, object]]:
    """The pinned commit's recursive tree, blobs only, keyed by path.

    The commit object names its tree's SHA; the tree is then fetched by that SHA and must echo it, so the listing
    is the commit's own (a tree requested by commit SHA would echo whatever SHA it was asked for).
    """
    commit = gh_api(f"repos/{pins.REPO}/git/commits/{pins.COMMIT}", COMMIT_FILE)
    tree_obj = commit.get("tree")
    tree_sha = tree_obj.get("sha") if isinstance(tree_obj, dict) else None
    if commit.get("sha") != pins.COMMIT or not isinstance(tree_sha, str):
        raise RuntimeError(f"commit.json is not commit {pins.COMMIT}")
    tree = gh_api(f"repos/{pins.REPO}/git/trees/{tree_sha}?recursive=1", TREE_FILE)
    if tree.get("sha") != tree_sha or tree.get("truncated") is not False:
        raise RuntimeError(f"tree.json is not the full tree {tree_sha} of commit {pins.COMMIT}")
    entries = tree["tree"]
    assert isinstance(entries, list)
    return {e["path"]: e for e in entries if e["type"] == "blob"}


def is_wanted(path: str) -> bool:
    """The cone files of §2's P1 and P2 rows, the NIST gasification CSVs (P0) and the named READMEs."""
    name = PurePosixPath(path).name
    if path in pins.READMES:
        return True
    if not name.lower().endswith(".csv"):
        return False
    if path.startswith(pins.PMMA_CONE_DIR):
        return "_Cone_" in name
    if path.startswith(pins.WOOD_CONE_DIR):
        return "_Wood_Cone_" in name
    return path.startswith(pins.GASIF_DIR) and name.startswith("MaCFP-PMMA_Gasification_")


def cache_path(path: str) -> Path:
    """Where a repository path lives in the cache; refuses anything that would leave it."""
    rel = PurePosixPath(path)
    if rel.is_absolute() or ".." in rel.parts or not path.lower().endswith(ALLOWED_SUFFIXES):
        raise ValueError(f"refusing repository path {path!r}")
    return CACHE.joinpath(*rel.parts)


def fetch_one(path: str, want_sha1: str) -> bytes:
    """The file's bytes, from the cache if it verifies, else downloaded at the pinned commit and verified."""
    dest = cache_path(path)
    if dest.exists() and git_blob_sha1(dest.read_bytes()) == want_sha1:
        return dest.read_bytes()
    url = f"https://raw.githubusercontent.com/{pins.REPO}/{pins.COMMIT}/{urllib.parse.quote(path)}"
    with urllib.request.urlopen(url, timeout=60) as resp:  # a fixed https URL at the pinned commit
        data: bytes = resp.read()
    if git_blob_sha1(data) != want_sha1:
        raise RuntimeError(f"{path}: downloaded bytes do not match the pinned tree's blob {want_sha1}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data


def fetch_all() -> dict[str, str]:
    """Fetch every wanted file; returns {repository path: SHA-256} in sorted path order."""
    tree = load_tree()
    wanted = sorted(p for p in tree if is_wanted(p))
    missing = [p for p in pins.READMES if p not in tree]
    if missing:
        raise RuntimeError(f"pinned tree lacks {missing}")
    return {p: hashlib.sha256(fetch_one(p, str(tree[p]["sha"]))).hexdigest() for p in wanted}
