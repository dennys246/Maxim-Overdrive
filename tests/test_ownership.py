"""The write window (boundaries §4.1) and the writers it admits (§3, §6.4).

At rest every array the core owns is read-only, and nothing can make it writable; inside the window the writable
arrays are fresh copies, swapped in as read-only owners at exit, so no handle outlives the window. Statically, every
function that writes a cell array, a region table or the heat sources lives in the core, and only the named owners
open the window.
"""

from __future__ import annotations

import ast
import importlib
import tomllib
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from maxim_overdrive import data
from simcore.adapters.sem.bridge import region_parts
from simcore.core.applier import Applier
from simcore.core.grid import WindowClosed
from simcore.core.readonly import frozen
from simcore.core.scene import Box, Scene
from simcore.core.world import HeatSource, World

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LIMITS = data.action_limits()
MATERIALS = data.materials()
SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _world() -> World:
    return World.from_scene(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS)


def _surfaces(w: World) -> Iterator[tuple[str, np.ndarray]]:
    """Every array the core hands outward: the grid's channels, region masks, the material table's lookups."""
    g = w.grid
    for name in ("material", "original_material", "integrity", "temperature"):
        yield name, getattr(g, name)
    for name, region in g.regions.items():
        yield f"regions[{name}].cells", region.cells
    for name in ("rho_cp", "conductivity", "fracture", "degrade_above", "degrade_rate"):
        yield f"materials.{name}", getattr(g.materials, name)


def _unlock_then_write(a: np.ndarray) -> None:
    a.flags.writeable = True
    a.flat[0] = a.flat[0]


def _through_base(a: np.ndarray) -> None:
    base = a.base
    while isinstance(base, np.ndarray) and base.base is not None:
        base.flags.writeable = True  # every link on the way down refuses too
        base = base.base
    assert base is not None
    base[0] = 0  # bytes: immutable


WRITES: dict[str, Callable[[np.ndarray], None]] = {
    "direct": lambda a: a.__setitem__((0,) * a.ndim, a[(0,) * a.ndim]),
    "unlock": _unlock_then_write,
    "base": _through_base,
    "ufunc-out": lambda a: np.multiply(a, 1, out=a, casting="unsafe"),
    "slice-view": lambda a: a.reshape(-1)[:1].__setitem__(0, a.flat[0]),
}


@pytest.mark.parametrize("how", WRITES)
def test_every_outward_array_refuses_every_write_at_rest(how):
    w = _world()
    for name, arr in _surfaces(w):
        with pytest.raises((ValueError, TypeError)):
            WRITES[how](arr)
        assert not arr.flags.writeable, name


@pytest.mark.parametrize(
    "assign",
    [
        lambda w: setattr(w.grid, "temperature", np.zeros(w.grid.shape)),
        lambda w: setattr(w.grid, "material", np.zeros(w.grid.shape, dtype=np.uint8)),
        lambda w: setattr(w.grid, "dx", 0.1),
        lambda w: setattr(w, "grid", None),
        lambda w: setattr(w, "sources", {}),
        lambda w: setattr(w, "limits", None),
        lambda w: setattr(w.grid.materials, "rho_cp", None),
        lambda w: setattr(w.grid.regions["crate"], "cells", None),
    ],
)
def test_attribute_assignment_to_an_owned_surface_raises(assign):
    with pytest.raises(AttributeError):
        assign(_world())


def test_the_region_table_and_the_sources_are_read_only_mappings():
    w = _world()
    with pytest.raises(TypeError):
        w.grid.regions["x"] = w.grid.regions["crate"]  # type: ignore[index]
    with pytest.raises(TypeError):
        w.sources["fire:x"] = HeatSource((1.0, 1.0, 1.0), 0.3, 1.0)  # type: ignore[index]
    with pytest.raises(TypeError):
        w.grid.materials.by_name["x"] = w.grid.materials["wood"]  # type: ignore[index]


def test_a_handle_or_view_unlocked_inside_a_window_and_written_after_it_closes_changes_nothing():
    # The scenario that broke a flag-based window (foundations DR-B4): a view that re-enables itself inside the
    # window stays writable after it, so a guard proven only with the window closed would pass while failing.
    w = _world()
    g = w.grid
    with g.writing():
        handle = g.temperature
        view = g.temperature[1:3]
        view.flags.writeable = True
        assert handle.flags.writeable
    frame = w.frames.latest
    before = g.temperature.copy()
    handle[:] = 999.0  # the old handles are still writable, but nothing reads them any more
    view[:] = 999.0
    assert np.array_equal(g.temperature, before)
    assert frame.reading("crate", "temperature_max") == pytest.approx(20.0)


def test_one_window_at_a_time_and_none_at_rest():
    g = _world().grid
    with g.writing(), pytest.raises(WindowClosed, match="one owner at a time"), g.writing():
        pass  # pragma: no cover - the nested window is refused before its body runs
    with pytest.raises(WindowClosed, match="only inside the write window"):
        g.time_s = 5.0
    with pytest.raises(WindowClosed, match="only inside the write window"):
        g.name_region("x", g.regions["crate"].cells, g.regions["crate"].footprint, solid=True)


def _write_everything_then_fail(w: World) -> None:
    g = w.grid
    with w.writing() as sources:
        g.temperature[:] = 500.0
        g.paint(g.regions["crate"].cells, "air")
        g.time_s = 60.0
        sources["fire:crate"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1.0)
        raise RuntimeError("midway")


def test_a_window_that_raises_changes_nothing():
    w = _world()
    g = w.grid
    before = (g.temperature.copy(), dict(g.regions), g.time_s, dict(w.sources), w.frames.latest)
    with pytest.raises(RuntimeError, match="midway"):
        _write_everything_then_fail(w)
    assert np.array_equal(g.temperature, before[0])
    assert _same_regions(g.regions, before[1])
    assert (g.time_s, dict(w.sources)) == before[2:4]
    assert w.frames.latest is before[4]
    assert not g.temperature.flags.writeable  # and the owners are read-only again


def _same_regions(a, b) -> bool:
    """Region tables equal by value: names, footprints, solidity and every mask's cells."""
    return list(a) == list(b) and all(
        a[n].footprint == b[n].footprint and a[n].solid == b[n].solid and np.array_equal(a[n].cells, b[n].cells)
        for n in a
    )


def test_the_sources_stay_read_only_after_an_ignite_and_a_dict_kept_past_its_window_changes_nothing():
    # Step 3b review, Executor S1: the window committed the very dict its caller held, so a write after the window
    # closed lit a fire no applier had lit, with no frame published.
    w = _world()
    _, crate = region_parts(Applier(w), w.frames, "crate")
    assert crate["structure"].execute("ignite", {"power_w": 1000.0}).success
    with pytest.raises(TypeError):
        w.sources["fire:x"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1e6)  # type: ignore[index]
    with w.writing() as kept:
        pass
    kept["fire:x"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1e6)
    assert set(w.sources) == {"fire:crate"}
    w.advance()
    assert "fire:x" not in w.sources


def _heat_and_light(w: World) -> None:
    with w.writing() as sources:
        w.grid.temperature[:] = 99.0
        sources["fire:x"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1.0)


def test_a_failure_while_the_window_closes_rolls_it_back_and_leaves_the_owners_read_only(monkeypatch):
    # Step 3b review, Architecture S2: the freeze at exit sat outside the rollback, so a MemoryError there left the
    # window's writable copies as the world's arrays, committed and unpublished.
    w = _world()
    g = w.grid
    before = (g.temperature.copy(), w.frames.latest, dict(w.sources))
    real, calls = frozen, []

    def fails_second(arr):
        calls.append(1)
        if len(calls) == 2:
            raise MemoryError("planted")
        return real(arr)

    monkeypatch.setattr("simcore.core.grid.frozen", fails_second)  # the one test that breaks the window's freeze
    with pytest.raises(MemoryError, match="planted"):
        _heat_and_light(w)
    monkeypatch.setattr("simcore.core.grid.frozen", real)
    assert not g.temperature.flags.writeable
    with pytest.raises(ValueError, match="read-only"):
        g.temperature[0, 0, 0] = 5.0
    assert np.array_equal(g.temperature, before[0])
    assert (w.frames.latest, dict(w.sources)) == before[1:]


def test_a_region_table_taken_before_a_failed_window_still_shows_the_table_before_it():
    w = _world()
    g = w.grid
    held = g.regions
    cells = held["crate"].cells.copy()
    with pytest.raises(RuntimeError, match="midway"):
        _write_everything_then_fail(w)
    assert np.array_equal(held["crate"].cells, cells)


def test_a_window_that_changes_only_the_sources_copies_no_cells_and_publishes_no_frame():
    # Step 3b review, Architecture S5: ignite and extinguish copied every channel twice for a change no frame carries.
    w = _world()
    owners = w.grid.temperature
    frame = w.frames.latest
    _, crate = region_parts(Applier(w), w.frames, "crate")
    assert crate["structure"].execute("ignite", {"power_w": 1000.0}).success
    assert crate["structure"].execute("extinguish", {}).success
    assert w.grid.temperature is owners
    assert w.frames.latest is frame


# -- the writers (boundaries §3, D-B1) ---------------------------------------------------------------------------------

# Names whose element writes change the world: the grid's channels, region masks and tables, and the heat sources.
OWNED = {"material", "original_material", "integrity", "temperature", "cells", "regions", "sources"}
OWNER_STORES = {"_channels", "_regions", "_sources", "_masks", "_meta"}
CORE = "simcore/core/"


def _attr(node: ast.AST) -> str | None:
    return node.attr if isinstance(node, ast.Attribute) else None


def _root(node: ast.AST) -> ast.AST:
    while isinstance(node, ast.Subscript):
        node = node.value
    return node


def _flat(targets: list[ast.expr]) -> list[ast.expr]:
    out: list[ast.expr] = []
    for t in targets:
        out += _flat(list(t.elts)) if isinstance(t, ast.Tuple | ast.List) else [t]
    return out


class _Writes(ast.NodeVisitor):
    """Whether one function writes something the world owns, directly or through a local alias of it."""

    def __init__(self) -> None:
        self.aliases: set[str] = set()
        self.writes = False

    def _owned(self, node: ast.AST) -> bool:
        node = _root(node)
        return _attr(node) in OWNED | OWNER_STORES or (isinstance(node, ast.Name) and node.id in self.aliases)

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Attribute) and node.value.attr in OWNED:
            self.aliases |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        for t in _flat(node.targets):  # ``self._channels, self._open = ...`` unpacks into each name
            if (isinstance(t, ast.Subscript) and self._owned(t)) or _attr(t) in OWNER_STORES:
                self.writes = True
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.writes |= isinstance(node.target, (ast.Subscript, ast.Attribute, ast.Name)) and self._owned(node.target)
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:
        self.writes |= any(isinstance(t, ast.Subscript) and self._owned(t) for t in node.targets)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:  # ``with world.writing() as sources``: the writable heat sources
            call = item.context_expr
            named = isinstance(item.optional_vars, ast.Name)
            if isinstance(call, ast.Call) and _attr(call.func) == "writing" and named:
                self.aliases.add(item.optional_vars.id)  # type: ignore[union-attr]
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.writes |= any(k.arg == "out" and self._owned(k.value) for k in node.keywords)
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"pop", "update", "clear", "setdefault", "popitem"}:
            self.writes |= self._owned(func.value)
        if isinstance(func, ast.Attribute) and func.attr in {"fill", "put", "itemset", "sort", "resize"}:
            self.writes |= self._owned(func.value)  # in-place array methods
        if _attr(func) == "copyto" or (isinstance(func, ast.Name) and func.id == "copyto"):
            self.writes |= bool(node.args) and self._owned(node.args[0])
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        pass  # a nested function is judged on its own


def writers(rel: str, source: str) -> set[str]:
    """``path::Qualified.name`` of every function in ``source`` that writes what the world owns."""
    found: set[str] = set()

    def walk(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                walk(node.body, f"{prefix}{node.name}.")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scan = _Writes()
                for stmt in node.body:
                    scan.visit(stmt)
                if scan.writes:
                    found.add(f"{rel}::{prefix}{node.name}")
                walk(node.body, f"{prefix}{node.name}.")

    walk(ast.parse(source).body, "")
    return found


def _all_writers() -> set[str]:
    return {w for p in sorted(SRC.rglob("*.py")) for w in writers(p.relative_to(SRC).as_posix(), p.read_text())}


# Non-vacuity: the scan must find the writers known to exist, so a change that blinds it goes red.
KNOWN_WRITERS = {
    "simcore/core/damage.py::strike",
    "simcore/core/damage.py::thermal_degrade",
    "simcore/core/heat.py::substep",
    "simcore/core/grid.py::MaterialGrid.paint",
    "simcore/core/grid.py::MaterialGrid.name_region",
    "simcore/core/grid.py::MaterialGrid.destroy",
    "simcore/core/grid.py::CellStore.writing",
    "simcore/core/grid.py::CellStore._take_cells",
    "simcore/core/world.py::World.writing",
    "simcore/core/applier.py::Applier._ignite",
    "simcore/core/applier.py::Applier._extinguish",
}


def test_every_function_that_writes_the_world_is_in_the_core():
    found = _all_writers()
    assert found >= KNOWN_WRITERS, sorted(KNOWN_WRITERS - found)
    outside = sorted(w for w in found if not w.startswith(CORE))
    assert not outside, f"world writers outside the sealed core: {outside}"


@pytest.mark.parametrize(
    "source",
    [
        "def f(w):\n    w.grid.temperature[0] = 1.0\n",
        "def f(w):\n    t = w.grid.temperature\n    t += 1.0\n",
        "def f(g):\n    np.add(g.integrity, 1, out=g.integrity)\n",
        "def f(w):\n    w.sources.pop('fire:x')\n",
        "def f(w):\n    with w.writing() as s:\n        s['fire:x'] = 1\n",
        "def f(w):\n    with w.writing() as s:\n        del s['fire:x']\n",
        "class C:\n    def f(self):\n        self._sources = {}\n",
        "class C:\n    def f(self):\n        self._channels, self._open = {}, True\n",
        "def f(g):\n    g.regions['x'].cells[:] = False\n",
        "def f(g, x):\n    np.copyto(g.temperature, x)\n",
        "def f(g):\n    g.temperature.fill(0.0)\n",
        "def f(g):\n    g.integrity.put([0], 0.0)\n",
    ],
)
def test_the_writer_scan_catches(source):
    assert writers("x.py", source), source


@pytest.mark.parametrize(
    "source",
    [
        "def f(g):\n    return g.temperature.copy()\n",
        "def f(g):\n    t = g.temperature.copy()\n    t += 1\n    return t\n",
        "def f(g):\n    return g.integrity[g.solid].sum()\n",
        "def f(params):\n    params.pop('x')\n",
    ],
)
def test_the_writer_scan_ignores(source):
    assert writers("x.py", source) == set(), source


# -- who opens the window (boundaries §4.1) ----------------------------------------------------------------------------

# The window's owners, each with its reason. World.advance and the applier carry band-aid markers scheduled for
# phase1/sim-clock: both move into Simulation.step. World.writing is the world's window itself (it opens the grid's).
WINDOW_OWNERS = {
    "simcore/core/world.py::World.advance": "the laws, during advance",
    "simcore/core/world.py::World.writing": "the world's window opens the grid's",
    "simcore/core/applier.py::Applier._strike": "intent application: strike",
    "simcore/core/applier.py::Applier._ignite": "intent application: ignite",
    "simcore/core/applier.py::Applier._extinguish": "intent application: douse",
    "simcore/core/scene.py::Scene.build": "construction",
    "simcore/core/imagination.py::_voxelize": "place, under a phase1/sim-clock marker: imagine has no intent kind yet",
}


def window_openers(rel: str, source: str) -> set[str]:
    found: set[str] = set()

    def walk(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                walk(node.body, f"{prefix}{node.name}.")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = (n for n in ast.walk(node) if isinstance(n, ast.Call))
                if any(_attr(c.func) == "writing" for c in calls):
                    found.add(f"{rel}::{prefix}{node.name}")

    walk(ast.parse(source).body, "")
    return found


def test_only_the_named_owners_open_the_write_window():
    found = {w for p in sorted(SRC.rglob("*.py")) for w in window_openers(p.relative_to(SRC).as_posix(), p.read_text())}
    assert found == set(WINDOW_OWNERS)


def test_the_shipped_path_publishes_a_frame_after_each_application_and_each_advance():
    w = _world()
    _, crate = region_parts(Applier(w), w.frames, "crate")
    seen = [w.frames.latest.sequence]
    assert crate["structure"].execute("ignite", {"power_w": 1000.0}).success
    seen.append(w.frames.latest.sequence)
    w.advance()
    seen.append(w.frames.latest.sequence)
    assert crate["structure"].execute("strike", {"energy_j": 1e5}).success
    seen.append(w.frames.latest.sequence)
    assert not crate["structure"].execute("strike", {"energy_j": -1.0}).success  # a refusal publishes nothing
    seen.append(w.frames.latest.sequence)
    assert seen == [0, 0, 1, 2, 2]  # an ignite changes no cell, so no frame (boundaries §4.2: on change)


# -- the membrane and the protocol reach the world only through their capabilities (step 3b review, Arch S1, Exec S2)

# Attributes that reach past the public surface: the world's grid, its sources and clock, a window, a frame's cells.
PEEKS = {"grid", "sources", "advance", "writing", "cells", "publish", "_grid", "_sources", "_world", "_feed"}
OUTSIDE_CORE = ("simcore/adapters/", "simcore/protocol/")


def peeks(rel: str, source: str) -> list[str]:
    return [
        f"{rel}:{node.lineno}: reaches .{node.attr}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute) and node.attr in PEEKS
    ]


def test_the_adapters_and_the_protocol_reach_no_world_state_by_attribute():
    found = [
        hit
        for p in sorted(SRC.rglob("*.py"))
        if p.relative_to(SRC).as_posix().startswith(OUTSIDE_CORE)
        for hit in peeks(p.relative_to(SRC).as_posix(), p.read_text())
    ]
    assert not found, found


@pytest.mark.parametrize(
    "line",
    [
        "solid = world.grid.regions[region].solid",
        "fires = w.sources",
        "w.advance()",
        "arr = frames.latest.cells.temperature",
        "feed.publish(frame)",
        "applier._world.grid",
    ],
)
def test_the_peek_scan_catches(line):
    assert peeks("x.py", line + "\n"), line


def _contract(contract_id: str) -> dict[str, Any]:
    contracts = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["importlinter"]["contracts"]
    return next(c for c in contracts if c["id"] == contract_id)


def reexports(rel: str, source: str, forbidden: set[str]) -> list[str]:
    """``from simcore.core.<m> import <name>`` where the name is, or comes from, a forbidden module (a re-export)."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.ImportFrom) and (node.module or "").startswith("simcore.")):
            continue
        module = importlib.import_module(node.module or "")
        for alias in node.names:
            obj = getattr(module, alias.name, None)
            origin = obj.__name__ if isinstance(obj, types.ModuleType) else getattr(obj, "__module__", None)
            if origin in forbidden and node.module not in forbidden:
                out.append(f"{rel}:{node.lineno}: {alias.name} from {node.module} is {origin}'s")
    return out


def _forbidden_for(rel: str) -> set[str]:
    out: set[str] = set()
    for cid in ("skip-layer", "membrane-reads-frames"):
        contract = _contract(cid)
        sources = [str(m).replace(".", "/") for m in contract["source_modules"]]
        if any(rel.startswith(s) for s in sources):
            out |= set(contract["forbidden_modules"])
    return out


def test_nothing_outside_the_core_imports_a_forbidden_module_through_an_allowed_one():
    found = []
    for p in sorted(SRC.rglob("*.py")):
        rel = p.relative_to(SRC).as_posix()
        if rel.startswith(OUTSIDE_CORE):
            found += reexports(rel, p.read_text(), _forbidden_for(rel))
    assert not found, found
    assert _forbidden_for("simcore/adapters/sem/bridge.py") >= {"simcore.core.heat", "simcore.core.world"}


@pytest.mark.parametrize(
    "line",
    [
        "from simcore.core.frames import MaterialGrid",
        "from simcore.core.applier import damage",
        "from simcore.core.frames import damage, QUANTITIES",
    ],
)
def test_the_reexport_scan_catches(line):
    forbidden = _forbidden_for("simcore/protocol/encoding.py")
    assert reexports("simcore/protocol/encoding.py", line + "\n", forbidden), line


def test_the_world_window_has_one_owner_at_a_time_too():
    w = _world()
    with w.writing(cells=False), pytest.raises(WindowClosed, match="one owner at a time"), w.writing(cells=False):
        pass  # pragma: no cover - the nested window is refused before its body runs
