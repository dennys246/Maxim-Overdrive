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
from simcore.core.intents import Extinguish, Ignite, Strike
from simcore.core.readonly import frozen
from simcore.core.scene import Box, Scene, constructing
from simcore.core.world import HeatSource, World
from simcore.core.writers import WindowClosed
from tests._cells import as_law, name_region, paint
from tests._sim import SteppingPort, make, record, ticks, world_of

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LIMITS = data.action_limits()
MATERIALS = data.materials()
SCENE = Scene(
    (3.0, 3.0, 2.0),
    (Box((1.2, 1.2, 0), (1.8, 1.8, 0.6), "wood", "crate"), Box((0, 0, 0), (0.6, 3.0, 2.0), "concrete", "wall")),
)


def _sim():
    return make(SCENE, MATERIALS, dx_m=0.2, limits=LIMITS)


def _world() -> World:
    return world_of(_sim())


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
    sim = _sim()
    g = world_of(sim).grid
    with constructing(g):
        handle = g.temperature
        view = g.temperature[1:3]
        view.flags.writeable = True
        assert handle.flags.writeable
    frame = sim.frames.latest
    before = g.temperature.copy()
    handle[:] = 999.0  # the old handles are still writable, but nothing reads them any more
    view[:] = 999.0
    assert np.array_equal(g.temperature, before)
    assert frame.reading("crate", "temperature_max") == pytest.approx(20.0)


def test_one_window_at_a_time_and_none_at_rest():
    g = _world().grid
    with g.writing(writer=None), pytest.raises(WindowClosed, match="one owner at a time"), g.writing(writer=None):
        pass  # pragma: no cover - the nested window is refused before its body runs
    with pytest.raises(WindowClosed, match="only inside the write window"):
        name_region(g, "x", g.regions["crate"].cells, g.regions["crate"].footprint, solid=True)


def _write_everything_then_fail(w: World) -> None:
    g = w.grid
    with w.writing(cells=True) as sources:  # each write as its owner does it: heat's as heat, the paint by Topology
        as_law(g, lambda grid: grid.temperature.fill(500.0))
        paint(g, g.regions["crate"].cells, "air")
        sources["fire:crate"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1.0)
        raise RuntimeError("midway")


def test_a_window_that_raises_changes_nothing():
    sim = _sim()
    w = world_of(sim)
    g = w.grid
    before = (g.temperature.copy(), dict(g.regions), dict(w.sources), sim.frames.latest)
    with pytest.raises(RuntimeError, match="midway"):
        _write_everything_then_fail(w)
    assert np.array_equal(g.temperature, before[0])
    assert _same_regions(g.regions, before[1])
    assert dict(w.sources) == before[2]
    assert sim.frames.latest is before[3]
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
    sim = _sim()
    w = world_of(sim)
    assert sim.step([record(Ignite(1000.0, 0.3), "crate", tick=1)]).outcomes[0].success
    with pytest.raises(TypeError):
        w.sources["fire:x"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1e6)  # type: ignore[index]
    with w.writing(cells=False) as kept:
        pass
    kept["fire:x"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1e6)
    assert set(w.sources) == {"fire:crate"}
    ticks(sim, 4)  # through a physics tick
    assert "fire:x" not in w.sources


def _heat_and_light(w: World) -> None:
    with w.writing(cells=True) as sources:
        as_law(w.grid, lambda grid: grid.temperature.fill(99.0))
        sources["fire:x"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1.0)


def test_a_failure_while_the_window_closes_rolls_it_back_and_leaves_the_owners_read_only(monkeypatch):
    # Step 3b review, Architecture S2: the freeze at exit sat outside the rollback, so a MemoryError there left the
    # window's writable copies as the world's arrays, committed and unpublished.
    sim = _sim()
    w = world_of(sim)
    g = w.grid
    before = (g.temperature.copy(), sim.frames.latest, dict(w.sources))
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
    assert (sim.frames.latest, dict(w.sources)) == before[1:]


def test_a_region_table_taken_before_a_failed_window_still_shows_the_table_before_it():
    w = _world()
    g = w.grid
    held = g.regions
    cells = held["crate"].cells.copy()
    with pytest.raises(RuntimeError, match="midway"):
        _write_everything_then_fail(w)
    assert np.array_equal(held["crate"].cells, cells)


def test_a_window_that_changes_only_the_sources_copies_no_cells_but_still_publishes_a_frame():
    # Step 3b review, Architecture S5: ignite and extinguish copied every channel twice for a change no frame carries.
    # Delta review, Architecture D2: they still publish, so every application has its after-frame (lesson 23: Maxim's
    # sensors read back right after execute). A frame holds the immutable owners, so republishing copies nothing.
    sim = _sim()
    w = world_of(sim)
    owners = w.grid.temperature
    first = sim.frames.latest
    _, crate = region_parts(SteppingPort(sim), sim.frames, "crate")
    assert crate["structure"].execute("ignite", {"power_w": 1000.0}).success  # ticks 1 and 2: neither is physics
    assert crate["structure"].execute("extinguish", {}).success
    assert w.grid.temperature is owners
    assert sim.frames.latest.sequence == first.sequence + 2
    assert sim.frames.latest.cells.temperature is first.cells.temperature


def test_the_grid_window_and_the_sources_window_share_one_owner():
    # Delta review, Executor S-a and Architecture D5: the two locks were independent, so a sources window opened
    # inside a grid window kept its fire when the grid window raised and rolled back.
    w = _world()
    with pytest.raises(WindowClosed, match="one owner at a time"):
        _ignite_inside_a_failing_grid_window(w)
    assert dict(w.sources) == {}
    assert w.grid.temperature.max() == 20.0  # the grid window rolled back too
    with w.writing(cells=False), pytest.raises(WindowClosed, match="one owner at a time"), w.grid.writing(writer=None):
        pass  # pragma: no cover - the nested window is refused before its body runs


def _ignite_inside_a_failing_grid_window(w: World) -> None:
    with constructing(w.grid):
        w.grid.temperature[:] = 500.0
        with w.writing(cells=False) as sources:  # a second owner: refused, so the grid window raises
            sources["fire:crate"] = HeatSource((1.5, 1.5, 0.3), 0.3, 1000.0)  # pragma: no cover - refused first
        raise AssertionError("the nested window was not refused")  # pragma: no cover - reached only if the guard fails


def test_a_paint_far_from_every_region_copies_no_region_mask():
    # Delta review, Executor N-b: the copy-only-what-a-paint-takes speedup (Trust S5) has a guard of its own.
    g = _world().grid
    far = np.zeros(g.shape, dtype=np.bool_)
    far[-1, -1, -1] = True
    with constructing(g):
        paint(g, far, "steel")
        assert g._masks == {}


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
                # A parameter named sources is the open window's table, handed down (PR 4a: the applier's).
                params = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
                scan.aliases |= {a.arg for a in params if a.arg == "sources"}
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
    "simcore/core/damage/loads.py::LoadsLaw.step",
    "simcore/core/damage/thermal.py::ThermalLaw.step",
    "simcore/core/heat.py::substep",
    "simcore/core/grid.py::MaterialGrid._set_cells",  # paint's and destroy's in-place edits
    "simcore/core/grid.py::MaterialGrid.name_region",
    "simcore/core/grid.py::CellStore._open_window",
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
        "def f(sources):\n    sources['fire:x'] = 1\n",  # the window's table, handed down (PR 4a)
        "class C:\n    def f(self, region, *, sources):\n        del sources['fire:x']\n",
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

# The window's owners, each with its reason. Since PR 4a the tick's one window is Simulation.step's (sim_core.md §4,
# §13): the apply phase and physics both run inside it. World.writing is the world's window itself (it opens the
# grid's).
WINDOW_OWNERS = {
    "simcore/core/simulation.py::Simulation._run": "the tick's one window: its records, then physics",
    "simcore/core/world.py::World.writing": "the world's window opens the grid's",
    "simcore/core/scene.py::constructing": "construction (Scene.build is its shipped caller)",
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
                if any(_attr(c.func) in ("writing", "holding") for c in calls):  # holding takes the same ownership
                    found.add(f"{rel}::{prefix}{node.name}")

    walk(ast.parse(source).body, "")
    return found


def test_the_opener_scan_counts_holding_as_an_opener():
    # Delta 2, Architecture N-1: holding takes the single ownership, so it is an opener like writing.
    assert window_openers("x.py", "def f(g):\n    with g.holding():\n        pass\n") == {"x.py::f"}


def test_only_the_named_owners_open_the_write_window():
    found = {w for p in sorted(SRC.rglob("*.py")) for w in window_openers(p.relative_to(SRC).as_posix(), p.read_text())}
    assert found == set(WINDOW_OWNERS)


def test_the_shipped_path_publishes_one_frame_per_tick_with_a_record_or_physics():
    # sim_core.md §4 (tile_and_client.md §4's cases): a record's tick publishes, a refusal-only tick too, a physics
    # tick does, and a quiet tick doesn't. Before PR 4a a frame followed each window and a refusal published nothing.
    sim = _sim()
    seen = [sim.frames.latest.sequence]
    assert sim.step([record(Ignite(1000.0, 0.3), "crate", tick=1)]).outcomes[0].success
    seen.append(sim.frames.latest.sequence)
    ticks(sim, 3)  # ticks 2 to 4: quiet
    seen.append(sim.frames.latest.sequence)
    ticks(sim, 1)  # tick 5: physics
    seen.append(sim.frames.latest.sequence)
    assert sim.step([record(Strike(1e5, LIMITS.default_sigma_m, None), "crate", tick=6)]).outcomes[0].success
    seen.append(sim.frames.latest.sequence)
    assert not sim.step([record(Extinguish(), "wall", tick=7)]).outcomes[0].success  # nothing burns on the wall
    seen.append(sim.frames.latest.sequence)
    assert seen == [0, 1, 1, 2, 3, 4]
    assert sim.frames.latest.tick == 7


# -- the membrane and the protocol reach the world only through their capabilities (step 3b review, Arch S1, Exec S2)
#
# The load-bearing guard is capability passing: the membrane is handed an applier and a frame view and holds no World
# or grid, so it has nothing to peek through. The two scans below are tripwires for the common spellings, with stated
# blind spots: they follow import aliases and attribute chains, not values (a local alias, getattr, a default
# argument, sys.modules). They are not to be extended into a reachability analysis.

# Attributes that reach past the public surface: the world's grid, its sources and clock, a window, a frame's cells.
PEEKS = {
    "grid", "sources", "advance", "writing", "holding", "cells", "publish", "_grid", "_sources", "_world", "_feed",
    "__dict__",
}  # fmt: skip
OUTSIDE_CORE = ("simcore/adapters/", "simcore/protocol/")


def peeks(rel: str, source: str) -> list[str]:
    """Attribute reads of world state, and ``vars(...)``, which reaches the same by name (delta review, N-a)."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and node.attr in PEEKS:
            out.append(f"{rel}:{node.lineno}: reaches .{node.attr}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "vars":
            out.append(f"{rel}:{node.lineno}: reaches attributes through vars()")
    return out


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
        "with grid.holding():\n    pass",
        "solid = vars(vars(applier)['_world'])['_grid']",
        "d = applier.__dict__",
    ],
)
def test_the_peek_scan_catches(line):
    assert peeks("x.py", line + "\n"), line


def _contract(contract_id: str) -> dict[str, Any]:
    contracts = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["importlinter"]["contracts"]
    return next(c for c in contracts if c["id"] == contract_id)


def _origin(obj: object) -> str | None:
    return obj.__name__ if isinstance(obj, types.ModuleType) else getattr(obj, "__module__", None)


def _simcore_names(tree: ast.Module) -> dict[str, object]:
    """Local names bound to simcore objects by an import: ``import simcore.core.frames as fr`` binds fr to the module,
    ``from simcore.core import applier`` binds applier, ``import simcore.core.frames`` binds simcore."""
    out: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "simcore" or a.name.startswith("simcore."):
                    module = importlib.import_module(a.name)
                    out[a.asname or "simcore"] = module if a.asname else importlib.import_module("simcore")
        elif isinstance(node, ast.ImportFrom) and (
            node.module == "simcore" or (node.module or "").startswith("simcore.")
        ):
            module = importlib.import_module(node.module or "")
            out |= {(a.asname or a.name): getattr(module, a.name, None) for a in node.names}
    return out


def _chain(node: ast.Attribute) -> tuple[str, list[str]] | None:
    parts = []
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    return (cur.id, parts[::-1]) if isinstance(cur, ast.Name) else None


def reexports(rel: str, source: str, forbidden: set[str]) -> list[str]:
    """A forbidden module reached through an allowed one: ``from simcore.core.<m> import <name>`` where the name is,
    or comes from, a forbidden module, and an attribute chain on an imported simcore object that reaches one
    (``frames.damage.strike``; delta review, Architecture D1)."""
    tree = ast.parse(source)
    names, out = _simcore_names(tree), []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and (node.module or "").startswith("simcore.")
            and node.module not in forbidden
        ):
            module = importlib.import_module(node.module or "")
            for alias in node.names:
                origin = _origin(getattr(module, alias.name, None))
                if origin in forbidden:
                    out.append(f"{rel}:{node.lineno}: {alias.name} from {node.module} is {origin}'s")
        elif isinstance(node, ast.Attribute) and (chain := _chain(node)) and chain[0] in names:
            obj: object = names[chain[0]]
            for part in chain[1]:
                obj = getattr(obj, part, None)
                if _origin(obj) in forbidden:
                    out.append(f"{rel}:{node.lineno}: {chain[0]}.{'.'.join(chain[1])} reaches {_origin(obj)}")
                    break
    return sorted(set(out))


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
        "from simcore.core.simulation import Physics",
        "from simcore.core.frames import reductions, QUANTITIES",
        "import simcore.core.frames as fr\nx = fr.reductions.region_breached",
        "from simcore.core import applier\nx = applier.Load",
        "from simcore.core import frames as f\nx = f.reductions.region_integrity",
        "import simcore.core.simulation\nx = simcore.core.simulation.Physics.run",
        "import simcore\nx = simcore.core.frames.reductions.region_breached",  # delta 2, Architecture D1
        "from simcore import core\nx = core.simulation.Physics",
    ],
)
def test_the_reexport_scan_catches(line):
    forbidden = _forbidden_for("simcore/protocol/encoding.py")
    assert reexports("simcore/protocol/encoding.py", line + "\n", forbidden), line


def test_the_world_window_has_one_owner_at_a_time_too():
    w = _world()
    with w.writing(cells=False), pytest.raises(WindowClosed, match="one owner at a time"), w.writing(cells=False):
        pass  # pragma: no cover - the nested window is refused before its body runs


# B43: inputs never write outcomes. The applier appends a record's inputs (a heat source, a load) and the laws resolve
# them; it writes no cell field and makes no world edit itself. The writer scan above finds every write, so here it
# must find only the two that touch the sources table, and no call may reach a cell writer or Topology.
APPLIER = "simcore/core/applier.py"
OUTCOME_CALLS = {"destroy", "paint", "name_region", "substep", "as_writer"}
OUTCOME_MODULES = {"simcore.core.topology", "simcore.core.damage", "simcore.core.heat", "simcore.core.grid"}


def _under(module: str | None, packages: set[str]) -> bool:
    return module is not None and any(module == p or module.startswith(f"{p}.") for p in packages)


def applier_outcome_writes(source: str) -> list[str]:
    tree = ast.parse(source)
    found = sorted(w for w in writers(APPLIER, source) if not w.endswith(("Applier._ignite", "Applier._extinguish")))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in OUTCOME_CALLS:
            found.append(f"line {node.lineno}: calls {node.func.attr}")
        if isinstance(node, ast.ImportFrom) and node.module == "simcore.core":
            found += [f"imports {a.name}" for a in node.names if f"simcore.core.{a.name}" in OUTCOME_MODULES]
        if isinstance(node, ast.ImportFrom) and _under(node.module, OUTCOME_MODULES - {"simcore.core.grid"}):
            found.append(f"imports from {node.module}")
    return found


def test_the_applier_writes_no_outcome_field():
    assert applier_outcome_writes((SRC / APPLIER).read_text()) == []


@pytest.mark.parametrize(
    "planted",
    [
        "def f(self):\n    self._world.grid.integrity[0] = 0.0\n",
        "def f(self, m):\n    self._world.grid.destroy(m)\n",
        "def f(self, m):\n    self._world.grid.paint(m, 'air')\n",
        "def f(self):\n    with self._world.grid.as_writer('damage.loads'):\n        pass\n",
        "from simcore.core import topology\n",
        "from simcore.core import damage\n",
        "from simcore.core.topology import apply\n",
        "from simcore.core.damage.loads import LOADS\n",
    ],
)
def test_the_applier_scan_catches(planted):
    assert applier_outcome_writes((SRC / APPLIER).read_text() + "\n\n" + planted), planted


# B43: Topology is the one path to the topology fields (sim_core.md §5.1). The window refuses paint, naming and
# destruction outside Topology's block; this scan holds the call sites to Topology's own module (and the grid's paint,
# which names the region it paints), so no requester even spells an edit itself.
WORLD_EDITS = {"destroy", "paint", "name_region"}
WORLD_EDITORS = {"simcore/core/topology.py", "simcore/core/grid.py"}


def world_edit_calls(rel: str, source: str) -> list[str]:
    return [
        f"{rel}:{node.lineno}: {node.func.attr}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in WORLD_EDITS
    ]


def test_only_topology_edits_the_world():
    found = []
    for p in sorted(SRC.rglob("*.py")):
        rel = p.relative_to(SRC).as_posix()
        calls = world_edit_calls(rel, p.read_text())
        assert rel not in {"simcore/core/topology.py"} or calls, "non-vacuity: Topology's own calls must be found"
        if rel not in WORLD_EDITORS:
            found += calls
    assert not found, found


def test_the_world_edit_scan_catches_a_requester_painting_for_itself():
    assert world_edit_calls("x.py", "def f(g, m):\n    g.paint(m, 'air')\n")
    assert world_edit_calls("x.py", "def f(w, m):\n    w.grid.destroy(m)\n")


# B43: a writer is a token its owner holds (``simcore.core.writers.claim``), and the window refuses everyone else at
# runtime. This scan holds the narrowing, the claims, the tokens and construction's window to their owners' modules, so
# a law can't even name another writer (Exec SF1's plants G3 and G4).
NARROWERS = {"simcore/core/physics.py", "simcore/core/topology.py"}
TOKENS = {"_TOKENS": "simcore/core/physics.py", "_TOPOLOGY": "simcore/core/topology.py"} | {
    "_CONSTRUCTION": "simcore/core/scene.py",
    "_run_as": "simcore/core/physics.py",  # runs a body holding a law's token; tests use it, shipped code may not
    "_claimed": "simcore/core/writers.py",  # every granted token (PR 2 delta, N1)
}
OWNED_CALLS = {
    "as_writer": NARROWERS,
    "claim": set(TOKENS.values()),
    "constructing": {"simcore/core/scene.py"},
    "adopt": {"simcore/core/simulation.py"},  # only a simulation adopts cells: a stray adoption orphans them (D4-N4)
}


def _named(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return node.name if isinstance(node, ast.alias) else None


def token_uses(rel: str, source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            name = _named(node.func)
            if name in OWNED_CALLS and rel not in OWNED_CALLS[name]:
                found.append(f"{rel}:{node.lineno}: calls {name}")
        held = _named(node)
        if held in TOKENS and TOKENS[held] != rel:
            found.append(f"{rel}: uses {held}")
    return found


def test_only_each_writers_owner_narrows_claims_or_names_its_token():
    found = []
    for p in sorted(SRC.rglob("*.py")):
        rel = p.relative_to(SRC).as_posix()
        found += token_uses(rel, p.read_text())
    assert not found, found
    assert "as_writer" in (SRC / "simcore/core/topology.py").read_text()  # non-vacuity: the owners do narrow


@pytest.mark.parametrize(
    ("rel", "planted"),
    [
        # G3: thermal damage edits the world itself as Topology. G4: heat writes as construction.
        ("simcore/core/damage/thermal.py", "def f(g, m):\n    with g.as_writer(topology._TOPOLOGY):\n        pass\n"),
        ("simcore/core/heat.py", "def f(g):\n    with g.as_writer('construction'):\n        pass\n"),
        ("simcore/core/heat.py", "from simcore.core.writers import claim\nT = claim('construction')\n"),
        ("simcore/core/applier.py", "from simcore.core.scene import _CONSTRUCTION\n"),
        ("simcore/core/applier.py", "def f(g):\n    with constructing(g):\n        pass\n"),
        ("simcore/core/damage/loads.py", "from simcore.core import physics\nT = physics._TOKENS['heat']\n"),
        ("simcore/core/world.py", "def f(w):\n    w.grid.adopt()\n"),
    ],
    ids=["g3", "g4", "claim", "import-token", "construct", "law-token", "adopt"],
)
def test_the_token_scan_catches(rel, planted):
    assert token_uses(rel, planted), planted
