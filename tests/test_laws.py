"""The law tuple, its orchestrator and Topology (sim_core.md §5, §5.1; step 5a's PR 2).

Bit-identity: the tuple must give exactly what heat with damage as its ``on_substep`` callback gave, so this file keeps
a reference copy of that path (``_reference_advance``, ``_reference_strike``: the pre-tuple code, its arithmetic
untouched, writing as construction) and compares every byte of state. The reference shares `heat.substep`, `destroy`
(through Topology) and the window with the code under test, so it checks the orchestration, not that arithmetic (Exec
NIT 6). The pre-change digests were also compared by hand on this machine (the commit message); a golden digest
isn't committed, because only the outcome class is promised across machines.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pytest
from scipy.special import ndtr

from simcore.core import damage, heat, physics, scene, topology
from simcore.core.applier import Applier
from simcore.core.exposure import Exposure, standing
from simcore.core.grid import MaterialGrid
from simcore.core.intents import Ignite, Strike
from simcore.core.law import Cadence, Changes, LawInputs, Load, LoadEffect
from simcore.core.materials import AIR_ID
from simcore.core.scene import Box, constructing, footprint_of
from simcore.core.world import World
from simcore.core.writers import UndeclaredRead, UndeclaredWriter, WindowClosed, WriterToken, claim
from tests._cells import destroy, paint
from tests.conftest import FAST_SPACINGS
from tests.test_determinism import FIRE_W, LIMITS, MATERIALS, SCENE, TURNS

fast_spacings = pytest.mark.parametrize("dx_m", FAST_SPACINGS)
CUBE = Box((0, 0, 0), (1, 1, 1), "concrete")


def _state(w: World) -> str:
    """Every byte the next turn depends on, as test_determinism.digest hashes it, without the turn counter."""
    h, g = hashlib.sha256(), w.grid
    for arr in (g.material, g.original_material, g.integrity, g.temperature):
        h.update(arr.tobytes())
    for name, region in g.regions.items():
        h.update(name.encode() + region.cells.tobytes() + f"{region.footprint}{region.solid}".encode())
    for name, src in w.sources.items():
        h.update(f"{name}{src.point_m}{src.radius_m}{src.power_w}".encode())
    h.update(repr(g.time_s).encode())
    return h.hexdigest()


def _reference_thermal_degrade(grid: MaterialGrid, dt: float) -> int:
    above = grid.materials.degrade_above[grid.material]
    excess = grid.temperature - above
    hot = grid.solid & (excess > 0)
    if not hot.any():
        return 0
    rate = grid.materials.degrade_rate[grid.material]
    grid.integrity[hot] -= (rate[hot] * dt * excess[hot] / 100.0).astype(grid.integrity.dtype)
    return destroy(grid, hot & (grid.integrity <= 0.0))


# The substep floor PR 3 removed (sim_core.md §8, §12): heat.min_substeps(dx) = ceil(0.16 / dx^2), at least 1, the
# retired rigs' 4, 16 and 64 at 0.2, 0.1 and 0.05 m. Kept here only as the reference the break is measured against.
def _retired_floor(dx_m: float) -> int:
    return max(1, math.ceil(0.16 / dx_m**2))


def _reference_advance(w: World, seconds: float) -> int:
    """The pre-tuple, pre-PR-3 World.advance: heat.step with damage.thermal_degrade as its on_substep callback, under
    the retired substep floor, its replan measured from a running float sum."""
    g = w.grid
    with constructing(g):  # the reference writes as construction, through Topology's edits
        n = max(_retired_floor(g.dx), math.ceil(seconds / heat.stable_dt(g)))
        dt = seconds / n
        planned, taken, elapsed, changed = n, 0, 0.0, False
        power_w = w._power_field(Exposure(standing(w.sources, 1), 1))
        while taken < planned:
            if changed:
                power_w = w._power_field(Exposure(standing(w.sources, 1), 1))
                bound = heat.stable_dt(g)
                if bound < dt:
                    remaining = seconds - elapsed
                    more = math.ceil(remaining / bound)
                    dt = remaining / more
                    planned = taken + more
            dt = min(dt, seconds - elapsed)
            heat.substep(g, dt, power_w)
            changed = bool(_reference_thermal_degrade(g, dt))
            elapsed += dt
            taken += 1
        g.time_us += round(seconds * 1_000_000)
    return taken


def _reference_strike(w: World, point, energy_j: float, sigma_m: float) -> tuple[int, float, float]:
    """The pre-tuple damage.strike: integrity, then the grid's own destroy, inside the world's window."""
    g = w.grid
    with constructing(g):  # the reference writes as construction, through Topology's edits
        edges = [np.arange(g.shape[a] + 1) * g.dx for a in range(3)]
        fx, fy, fz = (np.diff(ndtr((edges[a] - point[a]) / sigma_m)) for a in range(3))
        cell_energy = energy_j * fx[:, None, None] * fy[None, :, None] * fz[None, None, :]
        density = cell_energy / g.cell_volume_m3
        solid = g.solid
        fracture = g.materials.fracture[g.material]
        with np.errstate(divide="ignore", invalid="ignore"):
            loss = np.where(solid & (fracture > 0), density / fracture, 0.0)
        integrity = g.integrity
        integrity -= loss.astype(integrity.dtype)
        n = destroy(g, solid & (g.integrity <= 0.0))
        return n, n * g.cell_volume_m3, float(cell_energy[solid].sum())


@fast_spacings
def test_the_digest_break_is_exactly_the_floor_the_law_tuple_otherwise_matches_its_callback_reference(dx_m):
    """Fire on the crate and a strike on the wall, through the tuple and through the pre-tuple, pre-PR-3 reference:
    given the retired floor's count as substep_refine, every byte agrees, every turn, and the scenario really destroys
    cells both ways (so both paths ran). On shipped data stability asks for one substep per turn (sim_core.md §8), so
    the floor's count times one is the floor's count: PR 3's digest break (§12) is the floor and nothing else.
    test_the_break_is_real shows the shipped refine of 1 does differ."""
    worlds = [World.from_scene(SCENE, MATERIALS, dx_m=dx_m, limits=LIMITS) for _ in range(2)]
    for w in worlds:
        assert Applier(w).apply("crate", Ignite(power_w=FIRE_W, radius_m=0.3)).success
    tuple_world, reference = worlds
    point = reference.grid.regions["wall"].footprint.centroid_m
    outcome = Applier(tuple_world).apply("wall", Strike(energy_j=2.0e7, sigma_m=0.2, point_m=None))
    expected = _reference_strike(reference, point, 2.0e7, 0.2)
    assert (outcome.metadata["destroyed_volume_m3"], outcome.metadata["absorbed_j"]) == expected[1:]
    assert expected[0] > 0
    assert _state(tuple_world) == _state(reference)
    for _ in range(TURNS):
        refine = _retired_floor(dx_m)
        assert tuple_world.advance(refine=refine) == _reference_advance(reference, tuple_world.turn_seconds)
        assert _state(tuple_world) == _state(reference)
    assert (tuple_world.grid.original_material != AIR_ID).sum() > tuple_world.grid.solid.sum() + expected[0]


@fast_spacings
def test_the_break_is_real(dx_m):
    """The other half of the recorded break (sim_core.md §12): at the shipped refine of 1, a 6 s turn takes the one
    substep stability asks for, not the floor's 4 or 16, and the state leaves the floor's reference."""
    worlds = [World.from_scene(SCENE, MATERIALS, dx_m=dx_m, limits=LIMITS) for _ in range(2)]
    for w in worlds:
        assert Applier(w).apply("crate", Ignite(power_w=FIRE_W, radius_m=0.3)).success
    shipped, reference = worlds
    assert shipped.advance() == 1
    assert _reference_advance(reference, shipped.turn_seconds) == _retired_floor(dx_m)
    assert _state(shipped) != _state(reference)


def test_the_tuple_is_loads_heat_then_thermal_damage_at_their_cadences():
    assert [(law.name, law.cadence) for law in physics.DEFAULT_LAWS] == [
        ("damage.loads", Cadence.PER_RECORD),
        ("heat", Cadence.PER_SUBSTEP),
        ("damage.thermal", Cadence.PER_SUBSTEP),
    ]
    physics.check_laws(physics.DEFAULT_LAWS)
    assert damage.LOADS.stable_dt(_grid()) == damage.THERMAL.stable_dt(_grid()) == math.inf


@dataclass(frozen=True)
class _Law:
    name: str = "test.law"
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()

    def stable_dt(self, grid: MaterialGrid) -> float:
        return math.inf

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs) -> Changes:
        return Changes()


@pytest.mark.parametrize(
    ("laws", "match"),
    [
        ((heat.HEAT, heat.HEAT), "names each law once"),
        ((_Law(writes=("integrity",)),), r"writes \['integrity'\], but the field registry declares \[\]"),
        ((_Law(name="heat", writes=("integrity",)),), r"declares \['temperature'\]"),
        ((_Law(name="heat"),), r"writes \[\], but the field registry declares \['temperature'\]"),
        ((_Law(cadence=Cadence.PER_TICK),), "a cadence nothing runs yet"),
        ((_Law(cadence=Cadence.PER_PHYSICS_STEP),), "a cadence nothing runs yet"),
    ],
)
def test_a_law_tuple_the_registry_disagrees_with_is_refused(laws, match):
    with pytest.raises(ValueError, match=match):
        physics.check_laws(laws)
    g = _grid()
    with g.writing(writer=None), pytest.raises(ValueError, match=match):
        physics.run_physics(g, 1.0, refine=1, power=lambda: None, laws=laws)


def _grid(dx_m: float = 0.2) -> MaterialGrid:
    g = MaterialGrid.empty((1.0, 1.0, 1.0), MATERIALS, dx_m=dx_m)
    with constructing(g):
        paint(g, np.ones(g.shape, dtype=bool), "concrete")
    return g


def test_physics_over_no_time_runs_no_substep_and_moves_no_clock():
    g = _grid()
    with g.writing(writer=None):
        assert physics.run_physics(g, 0.0, refine=4, power=lambda: None) == 0
        assert physics.run_physics(g, -1.0, refine=4, power=lambda: None) == 0
    assert g.time_s == 0.0


# -- the write window: writers are tokens, and each law reads and writes only what it declares (B43) ---------------


@dataclass(frozen=True)
class _Plant:
    """A planted law: ``body`` runs as its step, under whatever name, reads and writes it declares."""

    body: Callable[[MaterialGrid], object]
    name: str = "heat"
    version: int = 1
    cadence: Cadence = Cadence.PER_SUBSTEP
    reads: tuple[str, ...] = ("material", "temperature")
    writes: tuple[str, ...] = ("temperature",)

    def stable_dt(self, grid: MaterialGrid) -> float:
        return math.inf

    def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs) -> Changes:
        self.body(grid)
        return Changes()


def _run(g: MaterialGrid, body: Callable[[MaterialGrid], object], **declared: object) -> None:
    with g.writing(writer=None):
        physics._run_as(g, _Plant(body, **declared), 1.0, LawInputs())  # type: ignore[arg-type]


def _set(arr: np.ndarray, value: float) -> None:
    arr[0, 0, 0] = value


@pytest.mark.parametrize(
    ("body", "raises", "match"),
    [
        (lambda g: _set(g.integrity, 0.5), UndeclaredRead, "'heat' doesn't declare 'integrity'"),
        (lambda g: g.regions, UndeclaredRead, "'regions'"),
        (lambda g: _set(g.material, 0), ValueError, "read-only"),  # Topology's field: never writable by subscript
        (lambda g: g.destroy(np.ones(g.shape, dtype=bool)), UndeclaredWriter, "only Topology applies it"),
        (lambda g: g.paint(np.ones(g.shape, dtype=bool), "wood"), UndeclaredWriter, "only Topology applies it"),
        (lambda g: setattr(g, "time_us", 5), UndeclaredWriter, "time moves in the orchestrator"),
        (lambda g: setattr(g.material.flags, "writeable", True), ValueError, "WRITEABLE"),  # SF2: can't unlock
        # G3: a law edits the world itself, holding Topology's token; G4: it narrows to another writer. Neither nests.
        (lambda g: topology.apply(g, [topology.Destroy(np.ones(g.shape, dtype=bool))]), UndeclaredWriter, "nests"),
        (lambda g: g.as_writer(physics._TOKENS["damage.thermal"]).__enter__(), UndeclaredWriter, "nests"),
    ],
    ids=["read", "regions", "material", "destroy", "paint", "clock", "unlock", "g3-topology", "g4-other-law"],
)
def test_a_law_reads_and_writes_only_what_it_declares(body, raises, match):
    """Heat writes temperature; anything else it reaches for raises, and changes nothing. Proven by deleting each
    check (``Gate.require_read``, ``_EDITED_ONLY``, ``require_editor``, the read-only buffer, ``narrow``'s nesting
    refusal): each row goes green without its check."""
    g = _grid()
    before = g.integrity.copy(), g.material.copy(), g.topology_version
    with pytest.raises(raises, match=match):
        _run(g, body, reads=("material", "temperature"))
    assert np.array_equal(g.integrity, before[0])
    assert np.array_equal(g.material, before[1])
    assert g.topology_version == before[2]


def test_a_law_writes_its_own_field_and_a_read_only_one_raises():
    g = _grid()
    _run(g, lambda grid: _set(grid.temperature, 30.0))
    assert g.temperature[0, 0, 0] == 30.0
    with pytest.raises(ValueError, match="read-only"):
        _run(g, lambda grid: _set(grid.integrity, 0.5), reads=("integrity",))
    assert g.integrity[0, 0, 0] == 1.0


def test_a_handle_kept_past_its_block_writes_nowhere_the_world_reads():
    """SF2's plant: heat keeps its temperature array, then writes it after its block, and inside thermal's block.
    Neither write lands. Proven by deleting the revocation in ``as_writer``: both land (999.0, then 777.0)."""
    g = _grid()
    kept: list[np.ndarray] = []
    with g.writing(writer=None):
        physics._run_as(g, _Plant(lambda grid: kept.append(grid.temperature)), 1.0, LawInputs())
        _set(kept[0], 999.0)
        physics._run_as(g, _Plant(lambda grid: _set(kept[0], 777.0), name="damage.thermal", writes=("integrity",)),
                        1.0, LawInputs())  # fmt: skip
        assert g.temperature[0, 0, 0] == 20.0
    assert g.temperature[0, 0, 0] == 20.0


def _writable_bases(arr: object) -> list[object]:
    """Every object reachable from ``arr`` through ``.base`` and ``.obj`` that a law could write through."""
    found: list[object] = []
    seen: set[int] = set()
    while arr is not None and id(arr) not in seen:
        seen.add(id(arr))
        if isinstance(arr, np.ndarray):
            try:
                arr.setflags(write=True)
                found.append(arr)
            except ValueError:
                pass  # can't be unlocked: what the test wants
        elif isinstance(arr, memoryview) and not arr.readonly:
            found.append(arr)
        arr = getattr(arr, "base", None) if isinstance(arr, np.ndarray) else getattr(arr, "obj", None)
    return found


@pytest.mark.parametrize("field", ["material", "original_material", "integrity", "temperature"])
def test_a_read_only_view_reaches_no_writable_memory(field):
    """PR 2 delta D2, plant P1: ``grid.material.base.obj[0, 0, 0] = 0`` wrote the world through the old memoryview
    view. A reader's view is a frozen copy now, whose chain ends in immutable bytes. Proven by restoring the
    memoryview view: every row finds a writable base."""
    g = _grid()
    seen: list[list[object]] = []
    reader = ("damage.thermal", ("integrity",)) if field == "temperature" else ("heat", ("temperature",))
    plant = _Plant(lambda grid: seen.append(_writable_bases(getattr(grid, field))), name=reader[0], reads=(field,),
                   writes=reader[1])  # fmt: skip
    with g.writing(writer=None):
        physics._run_as(g, plant, 1.0, LawInputs())  # a law that doesn't write ``field`` reads it
        seen.append(_writable_bases(getattr(g, field)))  # the orchestrator's own window reads too
    assert seen == [[], []]


def test_a_read_only_view_follows_every_change_to_its_field():
    """The read-only copies are cached per field, so each change must drop its field's copy: a writer's block
    (revocation), and Topology's paint and destroy. Proven by deleting each ``_views.pop``: its read goes stale."""
    g = _grid()
    one = np.zeros(g.shape, dtype=bool)
    one[0, 0, 0] = True
    seen: list[float] = []
    with g.writing(writer=None):
        seen += [float(g.temperature[0, 0, 0]), float(g.material[0, 0, 0])]  # cache both
        physics._run_as(g, _Plant(lambda grid: _set(grid.temperature, 30.0)), 1.0, LawInputs())
        seen.append(float(g.temperature[0, 0, 0]))
        destroy(g, one)
        seen.append(float(g.material[0, 0, 0]))
        paint(g, one, "wood")
        seen.append(float(g.material[0, 0, 0]))
    assert seen == [20.0, MATERIALS["concrete"].id, 30.0, AIR_ID, MATERIALS["wood"].id]


def test_a_law_leaves_no_close_listener_behind():
    """PR 2 delta N3: a listener registered from inside a window ran after every later window. Proven by deleting
    the refusal in ``on_close``: the listener is registered and runs."""
    g = _grid()
    ran: list[int] = []
    with g.writing(writer=None), pytest.raises(WindowClosed, match="one owner"):
        physics._run_as(g, _Plant(lambda grid: grid.on_close(lambda: ran.append(1))), 1.0, LawInputs())
    with g.writing(writer=None):
        pass
    assert ran == []


def test_a_law_named_like_a_registered_one_gets_no_token():
    """PR 2 delta SF-1 and D1, plant P2: an object named "damage.thermal" that isn't the registered law writes nothing
    through ``run_law``, so a small adapter can't impersonate a law. Proven by restoring the name lookup: it writes."""
    g = _grid()
    impostor = _Plant(
        lambda grid: _set(grid.integrity, 0.5), name="damage.thermal", reads=("integrity",), writes=("integrity",)
    )
    with g.writing(writer=None), pytest.raises(ValueError, match="read-only"):
        physics.run_law(g, impostor, 1.0, LawInputs())
    assert g.integrity[0, 0, 0] == 1.0


def test_a_law_must_declare_what_it_reads():
    g = _grid()
    with g.writing(writer=None), pytest.raises(ValueError, match="declares no reads"):
        physics.run_law(g, _Plant(lambda grid: None, reads=None), 1.0, LawInputs())  # type: ignore[arg-type]


def test_the_orchestrators_window_writes_nothing_itself():
    g = _grid()
    with g.writing(writer=None), pytest.raises(ValueError, match="read-only"):
        _set(g.temperature, 40.0)
    with g.writing(writer=None), pytest.raises(UndeclaredWriter, match="only Topology applies it"):
        g.name_region("x", np.ones(g.shape, dtype=bool), footprint_of([CUBE]), solid=True)
    assert g.temperature[0, 0, 0] == 20.0


def test_only_each_writers_owner_holds_its_token():
    """The architecture plant: code outside construction writing as construction inside the world's window. A name
    is no longer a writer, a token can't be made or claimed from here, and construction's own token never narrows."""
    g = _grid()
    for name in ("construction", "topology", "heat"):  # each owner claimed its token at import: a writer has one holder
        with pytest.raises(UndeclaredWriter, match="granted already"):
            claim(name)
    with pytest.raises(UndeclaredWriter, match="not a writer the field registry knows"):
        claim("pyrolysis")
    with pytest.raises(UndeclaredWriter, match=r"granted by writers\.claim"):
        WriterToken("construction", object())
    with g.writing(writer=None), pytest.raises(UndeclaredWriter, match="not a writer's token"), g.as_writer("heat"):  # type: ignore[arg-type]
        pass  # pragma: no cover - refused before the block runs
    with g.writing(writer=None), pytest.raises(UndeclaredWriter, match="never narrows"):
        g.as_writer(scene._CONSTRUCTION).__enter__()
    with pytest.raises(UndeclaredWriter, match="not a writer's token"), g.writing(writer="construction"):  # type: ignore[arg-type]
        pass  # pragma: no cover - refused before the window opens
    with pytest.raises(UndeclaredWriter, match="opened by construction or by an orchestrator"):
        g.writing(writer=topology._TOPOLOGY).__enter__()
    with pytest.raises(WindowClosed, match="only inside the write window"):
        g.as_writer(topology._TOPOLOGY).__enter__()
    assert not g.is_writing


def test_a_paint_needs_every_field_it_writes_declared_for_topology(monkeypatch):
    """Arch N2: paint narrows region masks too, so it checks the regions writer, not only material's."""
    from simcore.core import writers  # noqa: PLC0415 - the registry lookup the gate reads

    real = writers.writers_of  # type: ignore[attr-defined]  # the gate's own import, patched below
    monkeypatch.setattr(writers, "writers_of", lambda f: () if f == "regions" else real(f))
    g = MaterialGrid.empty((1.0, 1.0, 1.0), MATERIALS, dx_m=0.2)
    with pytest.raises(UndeclaredWriter, match="'topology' is not a declared writer of 'regions'"), constructing(g):
        paint(g, np.ones(g.shape, dtype=bool), "wood")
    assert repr(topology._TOPOLOGY) == "WriterToken('topology')"


def test_construction_is_over_once_anything_has_run():
    g = _grid()
    with g.writing(writer=None):
        pass
    with pytest.raises(UndeclaredWriter, match="never after"), constructing(g):
        pass  # pragma: no cover - refused before the window opens
    assert not g.is_writing


# -- Topology -------------------------------------------------------------------------------------------------


def test_topology_bumps_the_version_once_per_batch_that_changes_something():
    g = _grid()
    v = g.topology_version
    everything = np.ones(g.shape, dtype=bool)
    half = np.zeros(g.shape, dtype=bool)
    half[: g.shape[0] // 2] = True
    with g.writing(writer=None):
        assert topology.apply(g, [topology.Destroy(half), topology.Destroy(everything)]) == everything.sum()
        assert g.topology_version == v + 1  # two requests, one batch
        assert topology.apply(g, [topology.Destroy(everything)]) == 0  # all air now: nothing changes
        assert topology.apply(g, []) == 0
        assert g.topology_version == v + 1
        topology.apply(g, [topology.Paint(half, "wood")])
    assert g.topology_version == v + 2
    assert (g.material[half] != AIR_ID).all()
    assert (g.material[~half] == AIR_ID).all()


def test_a_batch_moves_the_version_only_if_it_changes_a_value():
    """PR 2 delta SF-2: one definition of a changing batch, a changed cell value or region table, for paint as for
    destroy. Proven by making paint set ``_edited`` unconditionally again: the empty and same-material rows bump."""
    g = MaterialGrid.empty((1.0, 1.0, 1.0), MATERIALS, dx_m=0.2)
    left = np.zeros(g.shape, dtype=bool)
    left[: g.shape[0] // 2] = True
    with constructing(g):
        paint(g, left, "concrete", "slab", footprint=footprint_of([CUBE]))
    versions = [g.topology_version]
    with g.writing(writer=None):
        for request in (
            topology.Paint(np.zeros(g.shape, dtype=bool), "wood"),  # empty: no change
            topology.Paint(~left, "air"),  # air over air at integrity 0: no change
            topology.Paint(left, "concrete"),  # the same material, but it takes the cells from "slab": a change
            topology.Paint(left, "concrete"),  # now nothing at all changes
            topology.NameRegion("void", np.zeros(g.shape, dtype=bool), footprint_of([CUBE]), False),  # a new name
        ):
            topology.apply(g, [request])
            versions.append(g.topology_version)
    assert versions == [1, 1, 1, 2, 2, 3]


def test_a_strike_that_breaks_nothing_leaves_the_version_where_it_was():
    """Wire S1's zero-change case, on the strike path: the version counts batches that changed the world."""
    g = _grid()
    with g.writing(writer=None):
        effect = physics.strike(g, (0.5, 0.5, 0.5), 1.0, 0.2)
    assert effect.destroyed_cells == 0
    assert g.integrity.min() < 1.0  # it landed, and broke nothing
    assert g.topology_version == 1  # _grid's construction batch only


def test_a_window_that_rolls_back_restores_the_topology_version():
    g = _grid()
    v = g.topology_version
    seen: list[int] = []

    def destroy_then_fail() -> None:
        with g.writing(writer=None):
            topology.apply(g, [topology.Destroy(np.ones(g.shape, dtype=bool))])
            seen.append(g.topology_version)
            raise RuntimeError("midway")

    with pytest.raises(RuntimeError, match="midway"):
        destroy_then_fail()
    assert seen == [v + 1]
    assert g.topology_version == v
    assert g.solid.all()


def test_a_batch_that_raises_after_an_edit_counts_it_and_leaks_nothing_into_the_next():
    """Exec NIT 3, Wire N3: a batch caught inside a still-open window changed the cells, so it counts once, and the
    next batch, which changes nothing, doesn't bump for it."""
    g = _grid()
    v = g.topology_version

    def paint_then_refuse():
        yield topology.Paint(np.ones(g.shape, dtype=bool), "wood")
        raise ValueError("refused midway")

    with g.writing(writer=None):
        with pytest.raises(ValueError, match="refused midway"):
            topology.apply(g, paint_then_refuse())
        assert g.topology_version == v + 1
        topology.apply(g, [])
        assert g.topology_version == v + 1


def test_construction_goes_through_topology_one_batch_per_apply():
    g = MaterialGrid.empty((1.0, 1.0, 1.0), MATERIALS, dx_m=0.2)
    assert g.topology_version == 0
    with constructing(g):
        topology.apply(g, [topology.Paint(np.ones(g.shape, dtype=bool), m) for m in ("wood", "steel")])
        with pytest.raises(UndeclaredWriter, match="only Topology applies it"):
            g.paint(np.ones(g.shape, dtype=bool), "wood")  # painted straight in the window: refused
        g.temperature[:] = 50.0  # construction's own field, not a world edit
        with pytest.raises(ValueError, match="read-only"):
            _set(g.material, 0)  # Topology's field: even construction changes it only through Topology
    assert g.topology_version == 1
    assert (g.material == MATERIALS["steel"].id).all()
    assert SCENE.build(MATERIALS, dx_m=0.2).topology_version == 1  # Scene.build's one batch of requests


def test_overlapping_paints_apply_in_emission_order():
    """Wire S2: a request's key is its place in the batch, and that order is load-bearing where paints overlap."""
    cells = []
    for order in (("wood", "steel"), ("steel", "wood")):
        g = MaterialGrid.empty((1.0, 1.0, 1.0), MATERIALS, dx_m=0.2)
        with constructing(g):
            topology.apply(g, [topology.Paint(np.ones(g.shape, dtype=bool), m) for m in order])
        cells.append(g.material.copy())
    assert (cells[0] == MATERIALS["steel"].id).all()
    assert (cells[1] == MATERIALS["wood"].id).all()


def test_a_per_record_law_whose_effects_disagree_with_topology_is_refused():
    """Arch N1: an effect's destroyed count is what Topology destroyed, one fact; a law that misreports it raises."""

    @dataclass(frozen=True)
    class _Liar:
        name: str = "damage.loads"
        version: int = 1
        cadence: Cadence = Cadence.PER_RECORD
        reads: tuple[str, ...] = ("material",)
        writes: tuple[str, ...] = ("integrity",)

        def stable_dt(self, grid: MaterialGrid) -> float:
            return math.inf

        def step(self, grid: MaterialGrid, dt_s: float, inputs: LawInputs) -> Changes:
            return Changes((topology.Destroy(np.ones(grid.shape, dtype=bool)),), (LoadEffect(0, 0.0, 0.0),))

    g = _grid()
    with g.writing(writer=None), pytest.raises(RuntimeError, match="reported 0 destroyed cells"):
        physics.resolve_loads(g, (), laws=(_Liar(),))


# -- damage's laws ----------------------------------------------------------------------------------------------


def test_two_loads_in_one_record_count_each_broken_cell_once():
    """Every load of a record resolves before Topology applies the batch, so a cell two loads break is counted by the
    first, and the record's destroyed volume is the volume that really went."""
    g = _grid()
    load = Load("strike", (0.5, 0.5, 0.5), 5.0e7, 0.2)
    with g.writing(writer=None):
        first, second = physics.resolve_loads(g, (load, load))
    destroyed = int((~g.solid).sum())
    assert first.destroyed_cells > 0
    assert first.destroyed_cells + second.destroyed_cells == destroyed
    assert first.absorbed_j == second.absorbed_j  # both landed on the same solid cells: none was gone yet


def test_damage_resolves_no_load_kind_it_does_not_know():
    g = _grid()
    with g.writing(writer=None), pytest.raises(ValueError, match="no 'bullet' load"):
        physics.resolve_loads(g, (Load("bullet", (0.5, 0.5, 0.5), 1.0, 0.2),))
    assert g.integrity.min() == 1.0


def test_thermal_damage_asks_for_no_destruction_when_nothing_breaks():
    g = _grid()
    with constructing(g):
        g.temperature[:] = 2000.0  # far past concrete's limit, for one short step
    with g.writing(writer=None):
        assert physics.run_law(g, damage.THERMAL, 1e-3, LawInputs()) == (Changes(), 0)
    assert g.integrity.max() < 1.0
