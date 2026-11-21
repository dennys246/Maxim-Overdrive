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


# -- process spawning (S2W-S3, S2D-S1) ------------------------------------------------------------------------------
# A spawned tool inherits this session's environment unless told otherwise, and Godot writes editor settings, caches
# and logs under HOME. So in tests/ and scripts/ a process may be started only at the sites below, each named with the
# environment it must be given; any other spawn, in any spelling, is a finding.
#   "godot": the env must be a godot_env(...) call, which moves HOME and the XDG directories into the work directory.
#   "given": an env= must be written (a deliberate choice, reviewed when the site was added).
ALLOWED_SPAWNS = {
    ("scripts/godot_check.py", "run_godot"): "godot",  # the one way Godot runs
    ("scripts/lint_repo.py", "tracked_text_files"): "given",  # git, on the repository the gate runs in
    ("scripts/lint_repo.py", "base_pyproject"): "given",  # git, the same
    ("tests/_gitutil.py", "git"): "given",  # git with every GIT_* dropped and no global config
    ("tests/test_prepush.py", "_gate"): "given",  # the gate, copied into a tmp repository
    ("tests/test_tooling_config.py", "_ruff"): "given",  # ruff, reading the tree
    ("tests/test_tooling_config.py", "_lint_imports"): "given",  # import-linter, on a tmp copy of src/
    ("tests/test_determinism.py", "test_runs_in_processes_with_different_hash_seeds_agree"): "given",  # Python
    ("tests/test_constructors.py", "test_a_set_echoes_in_the_same_order_under_every_hash_seed"): "given",  # Python
    ("tests/_imports.py", "external_imports"): "given",  # grimp's graph of a tree's src/, in its own interpreter
    ("tests/test_client_project.py", "_detected"): "given",  # ci/install_godot.sh --platform, PATH only
}
SPAWN_MODULES = {
    "subprocess": {"run", "call", "check_call", "check_output", "Popen", "getoutput", "getstatusoutput"},
    "os": {"system", "popen", "posix_spawn", "posix_spawnp", "fork", "forkpty"},
    "asyncio": {"create_subprocess_exec", "create_subprocess_shell"},
    "pty": {"spawn"},
}


def _aliases(tree: ast.Module) -> dict[str, str]:
    """Local name -> what it is: ``import subprocess as sp`` gives sp -> subprocess, ``from os import system as s``
    gives s -> os.system."""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {
                (a.asname or a.name.split(".")[0]): (a.name if a.asname else a.name.split(".")[0]) for a in node.names
            }
        elif isinstance(node, ast.ImportFrom) and node.module:
            out |= {(a.asname or a.name): f"{node.module}.{a.name}" for a in node.names}
    return out


def _spawned(node: ast.Call, aliases: dict[str, str]) -> str | None:
    """``subprocess.run``, ``os.execv`` … when the call starts a process, through any alias; else None."""
    func, dotted = node.func, None
    if isinstance(func, ast.Name):
        dotted = aliases.get(func.id)
    elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in aliases:
        dotted = f"{aliases[func.value.id]}.{func.attr}"
    if dotted is None or "." not in dotted:
        return None
    module, name = dotted.rsplit(".", 1)
    starts = name in SPAWN_MODULES.get(module, set()) or (module == "os" and name.startswith(("exec", "spawn")))
    return dotted if starts else None


def _enclosing_functions(tree: ast.Module) -> dict[int, str]:
    """id(node) -> the innermost function defining it (ast.walk visits outer functions first)."""
    out: dict[int, str] = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out |= {id(n): fn.name for n in ast.walk(fn)}
    return out


def _env_problem(node: ast.Call, kind: str) -> str | None:
    env = next((kw.value for kw in node.keywords if kw.arg == "env"), None)
    if env is None:
        return "without env=; say which environment it gets"
    is_godot_env = isinstance(env, ast.Call) and _call_name(env) == "godot_env"
    if kind == "godot" and not is_godot_env:
        return "Godot must get env=godot_env(home), so HOME and the XDG directories move into the work directory"
    return None


def spawn_findings(rel: str, tree: ast.Module) -> list[str]:
    if not rel.startswith(("tests/", "scripts/")):
        return []
    aliases, owner, out = _aliases(tree), _enclosing_functions(tree), []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or (what := _spawned(node, aliases)) is None:
            continue
        where, kind = f"{rel}:{node.lineno}", ALLOWED_SPAWNS.get((rel, owner.get(id(node), "")))
        if kind is None:
            out.append(f"{where}: {what} starts a process outside ALLOWED_SPAWNS; Godot goes through run_godot")
        elif (problem := _env_problem(node, kind)) is not None:
            out.append(f"{where}: {what} {problem}")
    return out


def _process_findings(rel: str, node: ast.Call, where: str) -> list[str]:
    out = []
    if rel.startswith("tests/") and rel != GIT_HELPER and _git_outside_helper(node):
        out.append(f"{where}: a test runs git without tests/_gitutil.py, so it inherits GIT_DIR; use git()")
    return out


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
        out += _process_findings(rel, node, where)
    return out


def findings(rel: str, source: str) -> list[str]:
    tree = ast.parse(source, filename=rel)
    mod, lines = _Module(tree), source.splitlines()
    exempt = {i for i, ln in enumerate(lines, 1) if EXEMPT.search(ln)}
    return [
        f for node in ast.walk(tree) if getattr(node, "lineno", 0) not in exempt for f in _node_findings(rel, node, mod)
    ] + spawn_findings(rel, tree)


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
        'subprocess.run(["git", "init"], cwd=tmp_path, env=e)',
        'subprocess.check_output(["git", "status"], env=e)',
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
        'subprocess.run(["ruff", "check"], env=e)',
    ],
)
def test_the_scan_ignores(source: str) -> None:
    assert findings("tests/test_a.py", source) == []


SPAWN_FORMS = [
    'import subprocess\nsubprocess.run(["x"], env=e)',
    'import subprocess\nsubprocess.run([godot, "--path", p], env=dict(os.environ))',
    'import subprocess as sp\nsp.run(["x"], env=e)',
    'from subprocess import run\nrun(["x"], env=e)',
    'from subprocess import Popen as P\nP(["x"], env=e)',
    "import subprocess\nsubprocess.check_output(cmd, env=e)",
    "import subprocess\nsubprocess.getoutput('x')",
    "import subprocess\nsubprocess.getstatusoutput('x')",
    "import os\nos.system('x')",
    "import os\nos.popen('x')",
    "import os\nos.execv('/bin/x', ['x'])",
    "import os\nos.execvpe('x', ['x'], {})",
    "from os import execl\nexecl('/bin/x', 'x')",
    "import os\nos.spawnv(os.P_WAIT, '/bin/x', ['x'])",
    "import os\nos.posix_spawn('/bin/x', ['x'], {})",
    "import asyncio\nasyncio.create_subprocess_exec('x')",
    "import asyncio\nasyncio.create_subprocess_shell('x')",
    "from asyncio import create_subprocess_exec as cse\ncse('x')",
    "import pty\npty.spawn('x')",
]


@pytest.mark.parametrize("source", SPAWN_FORMS)
def test_the_scan_catches_every_way_to_start_a_process_outside_the_allowlist(source: str) -> None:
    for rel in ("tests/test_a.py", "scripts/a.py"):
        assert any("outside ALLOWED_SPAWNS" in f for f in findings(rel, source)), (rel, source)
    assert findings("src/simcore/a.py", source) == []  # the shipped package is the server's to decide


@pytest.mark.parametrize(
    "env",
    ["", ", env=None", ", env=os.environ", ", env=dict(os.environ)", ", env={**os.environ}", ", env=env"],
)
def test_godot_must_be_given_a_moved_home(env: str) -> None:
    source = f"import subprocess\n\n\ndef run_godot(cmd, env, home):\n    subprocess.run(cmd{env})\n"
    assert findings("scripts/godot_check.py", source), env
    good = "import subprocess\n\n\ndef run_godot(cmd, home):\n    subprocess.run(cmd, env=godot_env(home))\n"
    assert findings("scripts/godot_check.py", good) == []


def test_an_allowed_site_must_still_say_which_environment_it_gets() -> None:
    source = 'import subprocess\n\n\ndef git(cwd):\n    subprocess.run(["git", "status"])\n'
    assert any("without env=" in f for f in findings(GIT_HELPER, source))
    assert findings(GIT_HELPER, source.replace("])", "], env=isolated_env())")) == []


def test_the_allowlist_names_only_sites_that_exist() -> None:
    """A stale entry would let a future function of the same name spawn unreviewed."""
    for rel, function in ALLOWED_SPAWNS:
        tree = ast.parse((ROOT / rel).read_text())
        names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        assert function in names, (rel, function)
