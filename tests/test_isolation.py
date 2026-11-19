"""Nothing a session runs may collide with another session's work (CLAUDE.md, "Assume other agents are working").

Several agents run the gate at once, each in its own worktree. A fixed temp path, a write to the home directory, a
test server on a fixed port, or a test's git call that inherits another repository's ``GIT_DIR`` is shared between
them, so two runs race or one changes the other's files. This scan holds `src/`, `scripts/` and `tests/` to paths
inside the worktree or pytest's `tmp_path`, test servers to port 0, and tests' git calls to tests/_gitutil.py.

It reads Python only, and resolves literals and module-level name constants, not computed values. A line that must
name a shared path as data (a validator's refusal test, say) carries ``# shared-path-ok: <why>``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCANNED = ("src", "scripts", "tests")
SELF = Path(__file__).resolve()
GIT_HELPER = "tests/_gitutil.py"

SHARED_DIRS = ("/tmp", "/private/tmp", "/var/tmp", "/var/folders", "/dev/shm")
SHARED_ENV = {"HOME", "TMPDIR", "TMP", "TEMP", "USERPROFILE"}
TEMP_CALLS_DIR_AT = {"mkdtemp": 2, "mkstemp": 2, "TemporaryDirectory": 2}  # positional index of dir=
TEMP_CALLS_KEYWORD_ONLY = {"NamedTemporaryFile", "TemporaryFile", "SpooledTemporaryFile"}
SERVER_CALLS_PORT_AT = {"serve": 2, "start_server": 2, "create_server": 2, "connect": None}  # positional index of port
PORT_IN_URL = re.compile(r"^\w+://[^/\s]*:(\d+)")
EXEMPT = re.compile(r"#\s*shared-path-ok:\s*\S.{8,}")
SUBPROCESS_CALLS = {"run", "call", "check_call", "check_output", "Popen"}


def _shared_path(value: str) -> bool:
    return (
        value in ("~",) or value.startswith("~/") or any(value == d or value.startswith(d + "/") for d in SHARED_DIRS)
    )


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _receiver(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Attribute):
        v = node.func.value
        return v.id if isinstance(v, ast.Name) else v.attr if isinstance(v, ast.Attribute) else None
    return None


class _Module:
    """One file's module-level integer and string constants, so ``PORT = 8765; serve(port=PORT)`` is still seen."""

    def __init__(self, tree: ast.Module) -> None:
        self.constants: dict[str, object] = {}
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        self.constants[target.id] = stmt.value.value

    def value(self, node: ast.AST | None) -> object:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.constants.get(node.id)
        return None


def _fixed_port(node: ast.Call, mod: _Module) -> bool:
    """A test server or client on a nonzero port: by keyword, by position, or in a ``.bind((host, port))`` tuple."""
    if any(kw.arg == "port" and _nonzero(mod.value(kw.value)) for kw in node.keywords):
        return True
    name = _call_name(node)
    at = SERVER_CALLS_PORT_AT.get(name or "")
    if at is not None and len(node.args) > at and _nonzero(mod.value(node.args[at])):
        return True
    if name == "bind" and node.args and isinstance(node.args[0], ast.Tuple) and len(node.args[0].elts) >= 2:
        return _nonzero(mod.value(node.args[0].elts[1]))
    return False


def _nonzero(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value != 0


def _temp_without_dir(node: ast.Call, name: str) -> bool:
    if name not in TEMP_CALLS_DIR_AT and name not in TEMP_CALLS_KEYWORD_ONLY:
        return False
    keyword = next((kw for kw in node.keywords if kw.arg == "dir"), None)
    if keyword is not None:
        return isinstance(keyword.value, ast.Constant) and keyword.value.value is None
    at = TEMP_CALLS_DIR_AT.get(name)
    return at is None or len(node.args) <= at


def _shared_env(node: ast.AST) -> str | None:
    """``os.environ["HOME"]``, ``os.environ.get("HOME")`` or ``os.getenv("TMPDIR")``."""
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        base = node.value
        if isinstance(base, ast.Attribute) and base.attr == "environ" and node.slice.value in SHARED_ENV:
            return str(node.slice.value)
    if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
        name, recv = _call_name(node), _receiver(node)
        if (name == "getenv" or (name == "get" and recv == "environ")) and node.args[0].value in SHARED_ENV:
            return str(node.args[0].value)
    return None


def _git_outside_helper(node: ast.Call) -> bool:
    if _call_name(node) not in SUBPROCESS_CALLS or _receiver(node) != "subprocess" or not node.args:
        return False
    cmd = node.args[0]
    return (
        isinstance(cmd, ast.List)
        and bool(cmd.elts)
        and isinstance(cmd.elts[0], ast.Constant)
        and cmd.elts[0].value == "git"
    )


def _node_findings(rel: str, node: ast.AST, mod: _Module) -> list[str]:
    where, in_tests = f"{rel}:{getattr(node, 'lineno', 0)}", rel.startswith("tests/")
    out = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if _shared_path(node.value):
            out.append(f"{where}: a path outside the worktree ({node.value!r}); use tmp_path or the worktree")
        m = PORT_IN_URL.match(node.value)
        if in_tests and m and int(m.group(1)) != 0:
            out.append(f"{where}: a URL on a fixed port ({node.value!r}); bind port 0 and use the port it got")
    if (env := _shared_env(node)) is not None:
        out.append(f"{where}: ${env} is a directory every session shares")
    if isinstance(node, ast.Call):
        name = _call_name(node) or ""
        if (name == "home" and _receiver(node) == "Path") or name in {"expanduser", "gettempdir"}:
            out.append(f"{where}: {name}() reaches a directory every session shares")
        if _temp_without_dir(node, name):
            out.append(f"{where}: {name}() without a dir lands in the shared temp directory; use tmp_path")
        if in_tests and _fixed_port(node, mod):
            out.append(f"{where}: a test server on a fixed port collides with other sessions; bind port 0")
        if in_tests and rel != GIT_HELPER and _git_outside_helper(node):
            out.append(f"{where}: a test runs git without tests/_gitutil.py, so it inherits GIT_DIR; use git()")
    return out


def findings(rel: str, source: str) -> list[str]:
    tree = ast.parse(source, filename=rel)
    mod, lines = _Module(tree), source.splitlines()
    exempt = {i for i, ln in enumerate(lines, 1) if EXEMPT.search(ln)}
    return [
        f for node in ast.walk(tree) if getattr(node, "lineno", 0) not in exempt for f in _node_findings(rel, node, mod)
    ]


def scanned() -> list[Path]:
    return sorted(p for d in SCANNED for p in (ROOT / d).rglob("*.py") if p.resolve() != SELF)


def test_nothing_writes_outside_its_worktree_or_binds_a_fixed_port() -> None:
    hits = [f for p in scanned() for f in findings(p.relative_to(ROOT).as_posix(), p.read_text())]
    assert not hits, "\n".join(hits)


@pytest.mark.parametrize(
    "source",
    [
        'p = Path("/tmp/overdrive")',
        'p = "/tmp"',
        'p = "/private/tmp/x"',
        'p = "/var/folders/ab/cd"',
        'p = "/dev/shm/x"',
        'p = "~/.maxim"',
        "p = Path.home() / 'x'",
        "p = pathlib.Path.home()",
        "p = os.path.expanduser('x')",
        "d = tempfile.gettempdir()",
        "d = tempfile.mkdtemp()",
        "d = tempfile.mkdtemp(dir=None)",
        "fd, p = tempfile.mkstemp('', 'x')",
        "with tempfile.TemporaryDirectory() as d: pass",
        "f = tempfile.NamedTemporaryFile()",
        'h = os.environ["HOME"]',
        'h = os.environ.get("TMPDIR")',
        'h = os.getenv("HOME")',
    ],
)
def test_the_scan_catches_shared_paths(source: str) -> None:
    assert findings("src/a.py", source)


@pytest.mark.parametrize(
    "source",
    [
        "serve(handler, '127.0.0.1', port=8765)",
        "websockets.serve(handler, '127.0.0.1', 8765)",
        "asyncio.start_server(handler, host, 8765)",
        "PORT = 8765\nserve(handler, host, port=PORT)",
        "s.bind(('127.0.0.1', 8765))",
        'websockets.connect("ws://127.0.0.1:8765")',
        'url = "http://localhost:8080/x"',
    ],
)
def test_the_scan_catches_a_fixed_port_in_a_test(source: str) -> None:
    assert findings("tests/test_a.py", source)
    assert findings("src/a.py", source) == []  # the shipped server may default to a fixed port; tests may not


@pytest.mark.parametrize(
    "source",
    [
        'subprocess.run(["git", "init"], cwd=tmp_path)',
        'subprocess.check_output(["git", "status"])',
    ],
)
def test_the_scan_catches_a_test_running_git_without_the_helper(source: str) -> None:
    assert findings("tests/test_a.py", source)
    assert findings(GIT_HELPER, source) == []


@pytest.mark.parametrize(
    "source",
    [
        "p = tmp_path / 'x'",
        "d = tempfile.mkdtemp(dir=tmp_path)",
        "fd, p = tempfile.mkstemp('', 'x', tmp_path)",
        "s.bind(('127.0.0.1', 0))",
        "serve(handler, '127.0.0.1', port=0)",
        "websockets.serve(handler, '127.0.0.1', 0)",
        'msg = "temporary files go in tmp_path"',
        'p = ROOT / "data"',
        'p = "/tmpl/x"',
        'spec = "~=1.2"',
        'text = "~~strike~~"',
        "where = npc.home()",
        'assert refuse("/tmp/evil")  # shared-path-ok: the validator under test must refuse this',
        'subprocess.run(["ruff", "check"])',
    ],
)
def test_the_scan_ignores(source: str) -> None:
    assert findings("tests/test_a.py", source) == []
