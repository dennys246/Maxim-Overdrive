"""The settings CLAUDE.md's standards rely on are in force, not merely mentioned in pyproject.toml."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

from tests._gitutil import git

ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict[str, Any]:
    tool: dict[str, Any] = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]
    return tool


def test_the_no_silent_swallow_rules_are_selected_and_not_ignored():
    lint = _config()["ruff"]["lint"]
    selected, ignored = set(lint["select"]), set(lint.get("ignore", []))
    assert {"BLE", "S110"} <= selected
    assert not {"BLE", "BLE001", "S110"} & ignored
    for pattern, rules in lint.get("per-file-ignores", {}).items():
        assert pattern.startswith("tests/") or not {"BLE", "BLE001", "S110"} & set(rules), pattern


PRIVATE_REACH = """from simcore.core import grid, topology, writers

writers._claimed["topology"]
topology._TOPOLOGY
grid._channels["material"][0] = 0
"""


@pytest.mark.parametrize(("path", "hits"), [("src/simcore/core/x.py", 3), ("scripts/x.py", 3), ("tests/x.py", 0)])
def test_code_outside_the_tests_reaches_no_private_name(path, hits):
    """PR 2 delta D4: a private name reached from another module (a token, Topology's own, a store's arrays) is a
    lint error in src and scripts; tests reach them to plant and probe. Proven by dropping SLF001: the rows go 0."""
    out = _ruff("check", "--output-format", "json", "--stdin-filename", path, "-", stdin=PRIVATE_REACH)
    assert sum(f["code"] == "SLF001" for f in json.loads(out.stdout)) == hits


def test_red_gates_are_strict_and_warnings_are_errors():
    pytest_cfg = _config()["pytest"]["ini_options"]
    assert pytest_cfg["xfail_strict"] is True
    assert pytest_cfg["filterwarnings"] == ["error"]
    assert "--strict-markers" in pytest_cfg["addopts"]


def test_coverage_measures_branches_over_src_and_scripts():
    coverage = _config()["coverage"]
    assert coverage["run"]["branch"] is True
    assert set(coverage["run"]["source"]) == {"src", "scripts"}  # by directory: a new package is measured unasked
    assert "omit" not in coverage["run"]  # an omitted file is uncovered code that nobody sees


def test_the_gate_runs_every_tests_directory_in_the_tree():
    # The slice's tests sat outside testpaths, so step 5a's PR 4a broke 41 of them and the gate stayed green. Every
    # directory of tests the tree holds is in testpaths, so a spike that tracks main is held to it.
    testpaths = set(_config()["pytest"]["ini_options"]["testpaths"])
    skipped = {".venv", ".worktrees", "node_modules"}  # other checkouts and installed packages, not this tree's
    found = {
        rel.as_posix()
        for p in ROOT.glob("**/tests")
        if p.is_dir() and any(p.glob("test_*.py")) and not skipped & set((rel := p.relative_to(ROOT)).parts)
    }
    assert found - {"client/tests"} == testpaths  # the Godot client's tests run in godot_check, not pytest


def test_mypy_is_strict():
    mypy = _config()["mypy"]
    assert mypy["strict"] is True
    assert set(mypy["files"]) == {"src", "tests", "scripts"}
    relaxed = [o for o in mypy.get("overrides", []) if "disallow_untyped_defs" in o]
    assert all(o["module"] == ["tests.*"] for o in relaxed)  # only test signatures may go unannotated


# Canaries one step past each cap, and one at the complexity cap that must stay quiet. Asking ruff itself, rather than
# reading pyproject.toml for keys that relax a rule, closes every way to relax one, including keys ruff adds later.
CANARY = (
    "def at_cap(x):\n" + "".join(f"    if x == {i}:\n        x += 1\n" for i in range(9)) + "    return x\n\n\n"
    "def complex_(x):\n" + "".join(f"    if x == {i}:\n        x += 1\n" for i in range(10)) + "    return x\n\n\n"
    "def returns(x):\n" + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(6)) + "    return x\n\n\n"
    "def branches(x):\n" + "".join(f"    if x == {i}:\n        x += 1\n" for i in range(13)) + "    return x\n\n\n"
    "def statements(x):\n" + "".join(f"    x += {i}\n" for i in range(51)) + "    return x\n"
)
EXPECTED = {
    "complex_": {"C901"},
    "returns": {"PLR0911"},
    "branches": {"C901", "PLR0912"},
    "statements": {"PLR0915"},
}


def _ruff(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "ruff", *args]
    env = dict(os.environ)  # ruff reads only the tree; it needs no isolation from this session
    return subprocess.run(cmd, cwd=ROOT, env=env, input=stdin, capture_output=True, text=True, check=False)


def _capped_hits(path: str) -> dict[str, set[str]]:
    """The complexity codes ruff reports on the canary, as if it were the file at ``path``, by canary function."""
    out = _ruff("check", "--force-exclude", "--output-format", "json", "--stdin-filename", path, "-", stdin=CANARY)
    starts = {ln.split("(")[0][4:]: i for i, ln in enumerate(CANARY.splitlines(), 1) if ln.startswith("def ")}
    by_line = {line: name for name, line in starts.items()}
    hits: dict[str, set[str]] = {name: set() for name in starts}
    for d in json.loads(out.stdout or "[]"):
        if d["code"] in {"C901", "PLR0911", "PLR0912", "PLR0915"} and d["location"]["row"] in by_line:
            hits[by_line[d["location"]["row"]]].add(d["code"])
    return hits


@pytest.mark.parametrize("path", ["src/simcore/core/canary.py", "src/maxim_overdrive/canary.py", "scripts/canary.py"])
def test_ruff_enforces_each_complexity_cap_at_its_threshold(path):
    hits = _capped_hits(path)
    assert hits.pop("at_cap") == set()  # complexity 10 is allowed: the cap is 10, not lower
    assert hits == EXPECTED


def test_tests_waive_only_the_statement_count():
    hits = _capped_hits("tests/test_canary.py")
    assert hits.pop("at_cap") == set()
    assert hits == {**EXPECTED, "statements": set()}


def test_ruff_lints_every_tracked_python_file():
    """An exclude anywhere (a key, a glob, an extended config) shows up as a tracked file ruff doesn't see."""
    shown = _ruff("check", "--show-files", "src", "tests", "scripts")
    assert shown.returncode == 0, shown.stderr
    seen = {str(Path(p).resolve().relative_to(ROOT)) for p in shown.stdout.split() if p.endswith(".py")}
    listed = git(ROOT, "ls-files", "src", "tests", "scripts")
    tracked = {f for f in listed.stdout.splitlines() if f.endswith(".py")}
    assert tracked - seen == set()


def test_no_nested_ruff_config_can_override_the_root_one():
    tracked = git(ROOT, "ls-files").stdout
    assert not [f for f in tracked.splitlines() if Path(f).name in {"ruff.toml", ".ruff.toml"}]
    assert [f for f in tracked.splitlines() if Path(f).name == "pyproject.toml"] == ["pyproject.toml"]


# -- import contracts (boundaries O24, §8.1, §10) ----------------------------------------------------------------------


def _src_packages() -> set[str]:
    return {p.parent.name for p in (ROOT / "src").glob("*/__init__.py")}


def _contracts() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in _config()["importlinter"]["contracts"]}


def test_every_package_under_src_is_a_root_of_the_import_graph():
    # grimp builds no graph for a root that isn't listed, so an unlisted package importing maxim would pass every
    # contract (foundations X-12, verified).
    assert set(_config()["importlinter"]["root_packages"]) == _src_packages()
    assert {"simcore", "maxim_overdrive"} <= _src_packages()


def test_the_import_graph_is_built_from_this_worktrees_src():
    # A shared venv's editable install could point the graph at another checkout's code (boundaries §10, W3).
    import grimp  # noqa: PLC0415 - only this test needs it

    graph = grimp.build_graph(*sorted(_src_packages()), cache_dir=None)
    for package in _src_packages():
        module = sys.modules.get(package) or __import__(package)
        assert Path(module.__file__ or "").resolve().is_relative_to(ROOT / "src"), package
        assert package in graph.modules


def test_the_layers_contract_orders_game_host_verify_protocol_adapters_core():
    # host | verify: two siblings in one layer (boundaries §2.2, layer 8), independent, so neither imports the other.
    layers = _contracts()["layers"]
    assert layers["type"] == "layers"
    assert layers["layers"] == [
        "maxim_overdrive", "simcore.host | simcore.verify", "simcore.protocol", "simcore.adapters", "simcore.core"
    ]  # fmt: skip


def test_the_verification_harness_imports_nothing_from_the_engine():
    # Its layer sits above the protocol, so the layers contract alone would let it reach a World (verify_harness §2).
    contract = _contracts()["verify-measures-only"]
    assert (contract["type"], contract["source_modules"]) == ("forbidden", ["simcore.verify"])
    engine = {"simcore.core", "simcore.adapters", "simcore.protocol", "simcore.host"}
    assert set(contract["forbidden_modules"]) == engine | {"maxim"}
    shipped = _contracts()["verify-ships-nowhere"]
    assert (shipped["type"], shipped["source_modules"], shipped["forbidden_modules"]) == (
        "forbidden", ["maxim_overdrive"], ["simcore.verify"]
    )  # fmt: skip


def test_the_sealed_core_contract_bans_exactly_the_shared_list():
    # One banned list (boundaries §3): the import contract and the core's AST scan read the same constant.
    from tests.test_determinism import BANNED_MODULES, SEALED_CORE_BANNED  # noqa: PLC0415

    core = _contracts()["sealed-core"]
    assert (core["type"], core["source_modules"]) == ("forbidden", ["simcore.core"])
    assert len(core["forbidden_modules"]) == len(set(core["forbidden_modules"]))
    assert set(core["forbidden_modules"]) == SEALED_CORE_BANNED
    assert set(BANNED_MODULES) < SEALED_CORE_BANNED
    assert _config()["importlinter"]["include_external_packages"] is True  # without it, stdlib bans are vacuous


def test_the_shipped_packages_may_not_import_test_tooling():
    tests_out = _contracts()["tests-out"]
    assert (tests_out["type"], set(tests_out["source_modules"])) == ("forbidden", _src_packages())
    assert set(tests_out["forbidden_modules"]) == {"pytest", "_pytest", "hypothesis", "tests"}


def test_the_engine_may_not_import_the_game():
    # The layers contract sees only modules inside a layer; this one covers simcore's root and any new child.
    contract = _contracts()["engine-not-game"]
    assert (contract["type"], contract["source_modules"]) == ("forbidden", ["simcore"])
    assert contract["forbidden_modules"] == ["maxim_overdrive"]


# Direct children of simcore that sit outside the layers, each with its reason. None: a new child joins a layer or
# this list in the change that makes it.
OUTSIDE_LAYERS: dict[str, str] = {}


def test_every_child_of_the_engine_is_in_a_layer():
    layered = {m.strip() for layer in _contracts()["layers"]["layers"] for m in layer.split("|")}
    children = {f"simcore.{p.stem}" for p in (ROOT / "src" / "simcore").iterdir() if p.suffix == ".py" or p.is_dir()}
    children -= {"simcore.__init__", "simcore.__pycache__"}
    assert children - layered == set(OUTSIDE_LAYERS)


def test_the_game_package_holds_only_its_data_until_the_lab():
    # boundaries §2.1 creates the game package with the first game content (phase1/lab); it exists earlier to hold
    # where the data lives (the deviation is recorded in boundaries §10, "As built in 3a"). Until the lab, nothing
    # else may collect in it.
    game = ROOT / "src" / "maxim_overdrive"
    assert {p.name for p in game.iterdir() if p.name != "__pycache__"} == {"__init__.py", "data.py"}


def test_only_the_sem_membrane_may_import_maxim():
    protected = _contracts()["maxim-through-adapters"]
    assert (protected["type"], protected["protected_modules"]) == ("protected", ["maxim"])
    assert protected["allowed_importers"] == ["simcore.adapters.sem"]


def test_the_gate_runs_the_import_contracts_on_this_worktrees_src_without_a_cache():
    gate = (ROOT / "scripts" / "prepush.sh").read_text()
    assert 'PYTHONPATH="$PWD/src" "$PY" -c \'from importlinter.cli import lint_imports_command' in gate
    assert "--no-cache" in gate
    assert "\nlint_imports\n" in gate  # defined and called


def _gate_lint_imports_command() -> list[str]:
    """The arguments after ``"$PY"`` in scripts/prepush.sh's lint_imports function, as the gate runs them."""
    gate = (ROOT / "scripts" / "prepush.sh").read_text()
    body = re.search(r"^lint_imports\(\) \{\n(.*?)\n\}", gate, re.M | re.S)
    assert body is not None, "prepush.sh defines no lint_imports function"
    words = shlex.split(body.group(1).strip())
    assert words[:2] == ["PYTHONPATH=$PWD/src", "$PY"], words  # this worktree's src/, the gate's own Python
    return words[2:]


def _lint_imports(tree: Path) -> subprocess.CompletedProcess[str]:
    """The gate's own import-contract command, read from scripts/prepush.sh, run on a copy of the tree."""
    env = {**os.environ, "PYTHONPATH": str(tree / "src")}
    cmd = [sys.executable, *_gate_lint_imports_command()]
    return subprocess.run(cmd, cwd=tree, env=env, capture_output=True, text=True, check=False)


# One planted import per contract that step 3b added, plus 3a's: each must turn the gate's own command red.
PLANTED = [
    ("simcore/host.py", "from maxim_overdrive import data", "the engine never imports the game"),
    ("simcore/protocol/encoding.py", "from simcore.core import grid", "adapters, protocol and host reach no cells"),
    ("simcore/adapters/sem/bridge.py", "from simcore.core import materials", "the SEM membrane reads frames"),
    ("simcore/verify/runs.py", "from simcore.core import grid", "the verification harness imports nothing"),
    ("maxim_overdrive/data.py", "from simcore import verify", "the game never imports the verification harness"),
]


@pytest.mark.parametrize(("module", "line", "contract"), PLANTED, ids=[p[0] for p in PLANTED])
def test_a_planted_violation_fails_the_gates_import_command(tmp_path, module, line, contract):
    shutil.copytree(ROOT / "src", tmp_path / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "pyproject.toml", tmp_path)
    assert _lint_imports(tmp_path).returncode == 0
    target = tmp_path / "src" / module
    target.write_text((target.read_text() if target.exists() else "") + line + "\n")
    broken = _lint_imports(tmp_path)
    assert broken.returncode == 1, broken.stdout
    assert contract in broken.stdout


def _core_modules() -> set[str]:
    """The core's modules and packages (a package, such as damage, is classified whole)."""
    core = ROOT / "src" / "simcore" / "core"
    modules = {f"simcore.core.{p.stem}" for p in core.glob("*.py") if p.stem != "__init__"}
    return modules | {f"simcore.core.{p.parent.name}" for p in core.glob("*/__init__.py")}


# The core's public surface to the adapters and the protocol (boundaries §2.2, the skip-layer rule): the simulation
# (world, applier, frames), the intents (intents, limits), the material types and the checks. A new core module joins
# this set or the contract's forbidden list in the change that makes it.
CORE_PUBLIC_SURFACE = {
    "simcore.core.world",
    "simcore.core.simulation",  # step 5a: the world's one owner of time
    "simcore.core.applier",
    "simcore.core.frames",
    "simcore.core.intents",
    "simcore.core.limits",
    "simcore.core.materials",
    "simcore.core.checks",
    "simcore.core.refusals",  # the closed vocabulary every refusal answers in
    "simcore.core.schema",  # the format declarations and their one reader, which the file gates and tiers apply
    "simcore.core.converters",  # the converters beyond schema's numbers and names: the wire's vectors, words, tokens
    "simcore.core.text",  # which characters text may hold: names, and guest text (player_text)
    "simcore.core.digest",  # versioned content digests, which step 5a's log header records
    "simcore.core.fields",  # the field registry, which the membrane, the snapshot and the digest read (sim_core.md §6)
    "simcore.core.work",  # the work counters every TickReport carries (sim_core.md §10)
}
# What the membrane may import from the core (B-13): frames to read, the intents to parse, and the applier's Outcome its
# port returns. Not the world or the simulation: it is handed a port and a frame view instead (sim_core.md §13).
MEMBRANE_SURFACE = CORE_PUBLIC_SURFACE - {
    "simcore.core.converters",
    "simcore.core.text",
    "simcore.core.materials",
    "simcore.core.world",
    "simcore.core.simulation",
    "simcore.core.schema",
    "simcore.core.digest",
    "simcore.core.work",  # a TickReport is never a stimulus (sim_core.md §4)
}


def test_the_skip_layer_contract_forbids_every_core_module_outside_the_public_surface():
    contract = _contracts()["skip-layer"]
    sources = ["simcore.adapters", "simcore.protocol", "simcore.host"]
    assert (contract["type"], contract["source_modules"]) == ("forbidden", sources)
    assert _core_modules() >= CORE_PUBLIC_SURFACE
    assert set(contract["forbidden_modules"]) == _core_modules() - CORE_PUBLIC_SURFACE
    assert contract["allow_indirect_imports"] is True  # the public surface reaches the cells; a direct import may not


def test_the_membrane_contract_leaves_it_frames_the_applier_and_the_intents_only():
    contract = _contracts()["membrane-reads-frames"]
    assert (contract["type"], contract["source_modules"]) == ("forbidden", ["simcore.adapters.sem"])
    expected = (_core_modules() - MEMBRANE_SURFACE) | {"simcore.adapters.loaders"}
    assert set(contract["forbidden_modules"]) == expected
    assert contract["allow_indirect_imports"] is True


def test_the_laws_independent_contract_covers_every_law_in_the_tuple():
    # B43: laws couple only through fields. The contract lists each law's module, one module per law (an independence
    # contract works per module, so two laws in one would be held apart by nothing: Arch S5, Exec NIT 4); a law added
    # to the tuple from a new module, or a contract that loses one, goes red here. Proven by planting
    # `from simcore.core.damage.loads import LOADS` in damage/thermal.py: lint-imports went red (commit message).
    from simcore.core import physics  # noqa: PLC0415 - the tuple, read where it is declared

    contract = _contracts()["laws-independent"]
    assert contract["type"] == "independence"
    modules = [type(law).__module__ for law in physics.DEFAULT_LAWS]
    assert len(set(modules)) == len(modules), f"two laws share a module: {modules}"
    assert set(contract["modules"]) == set(modules)
    assert contract.get("allow_indirect_imports", False) is False  # through a third module counts too


def test_the_gate_exports_the_tier_switch_conftest_reads():
    # W6: a rename on one side would silently drop the 0.05 m grid from the gate.
    conftest = (ROOT / "tests" / "conftest.py").read_text()
    names = set(re.findall(r'os\.environ\.get\("(MAXIM_OVERDRIVE_\w+)"\)', conftest))
    assert names == {"MAXIM_OVERDRIVE_ALL_TIERS"}
    gate = (ROOT / "scripts" / "prepush.sh").read_text()
    assert all(f"{name}=1" in gate for name in names)


def test_the_version_has_one_source():
    import simcore  # noqa: PLC0415

    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert "version" not in project
    assert project["dynamic"] == ["version"]
    assert _config()["hatch"]["version"]["path"] == "src/simcore/__init__.py"
    assert simcore.__version__


def test_the_wheel_ships_the_game_data_beside_the_module_that_reads_it():
    from maxim_overdrive import data  # noqa: PLC0415

    hatch = _config()["hatch"]["build"]["targets"]["wheel"]
    assert set(hatch["packages"]) == {f"src/{p}" for p in _src_packages()}
    assert hatch["force-include"] == {"data": f"{data.__name__.rsplit('.', 1)[0]}/_data"}


def test_the_network_lane_contract_keeps_the_server_off_the_world():
    # realtime_lanes_coop §4.1 (step 7 review C3, D-S1): the server never calls into the world; step 5a's hand-off
    # is a bounded queue to the simulation lane
    contract = _contracts()["network-lane-off-the-world"]
    assert (contract["type"], contract["source_modules"]) == ("forbidden", ["simcore.host.server"])
    want = {"simcore.core.world", "simcore.core.simulation", "simcore.core.applier"}
    assert set(contract["forbidden_modules"]) == want
