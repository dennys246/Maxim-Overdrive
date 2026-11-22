"""The law tuple, its orchestrator and Topology (sim_core.md §5, §5.1; step 5a's PR 2).

Bit-identity: the tuple must give exactly what heat with damage as its ``on_substep`` callback gave, so this file keeps
a reference copy of that path (``_reference_advance``, ``_reference_strike``: the pre-tuple code, its arithmetic
untouched, writing as construction) and compares every byte of state. The pre-change digests were also compared by
hand on this machine (the commit message); a golden digest isn't committed, because only the outcome class is promised
across machines.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np
import pytest
from scipy.special import ndtr

from simcore.core import damage, heat, physics, topology
from simcore.core.applier import Applier
from simcore.core.fields import CONSTRUCTION
from simcore.core.grid import MaterialGrid
from simcore.core.intents import Ignite, Strike
from simcore.core.law import Cadence, Changes, LawInputs, Load
from simcore.core.materials import AIR_ID
from simcore.core.scene import Box, footprint_of
from simcore.core.world import World
from simcore.core.writers import UndeclaredWriter, WindowClosed
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
    return grid.destroy(hot & (grid.integrity <= 0.0))


def _reference_advance(w: World, seconds: float) -> int:
    """The pre-tuple World.advance: heat.step with damage.thermal_degrade as its on_substep callback."""
    g = w.grid
    with w.writing(), g.as_writer(CONSTRUCTION):
        n = max(heat.min_substeps(g.dx), math.ceil(seconds / heat.stable_dt(g)))
        dt = seconds / n
        planned, taken, elapsed, changed = n, 0, 0.0, False
        power_w = w._power_field()
        while taken < planned:
            if changed:
                power_w = w._power_field()
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
        g.time_s += seconds
    return taken


def _reference_strike(w: World, point, energy_j: float, sigma_m: float) -> tuple[int, float, float]:
    """The pre-tuple damage.strike: integrity, then the grid's own destroy, inside the world's window."""
    g = w.grid
    with w.writing(), g.as_writer(CONSTRUCTION):
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
        n = g.destroy(solid & (g.integrity <= 0.0))
        return n, n * g.cell_volume_m3, float(cell_energy[solid].sum())


@fast_spacings
def test_the_law_tuple_is_bit_identical_to_heat_with_damage_as_its_callback(dx_m):
    """Fire on the crate and a strike on the wall, through the tuple and through the reference: every byte agrees,
    every turn, and the scenario really destroys cells both ways (so both paths ran)."""
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
        assert tuple_world.advance() == _reference_advance(reference, tuple_world.turn_seconds)
        assert _state(tuple_world) == _state(reference)
    assert (tuple_world.grid.original_material != AIR_ID).sum() > tuple_world.grid.solid.sum() + expected[0]


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
        ((_Law(writes=("integrity",)),), "doesn't declare"),
        ((_Law(name="heat", writes=("integrity",)),), "doesn't declare"),
        ((_Law(cadence=Cadence.PER_TICK),), "a cadence nothing runs yet"),
        ((_Law(cadence=Cadence.PER_PHYSICS_STEP),), "a cadence nothing runs yet"),
    ],
)
def test_a_law_tuple_the_registry_disagrees_with_is_refused(laws, match):
    with pytest.raises(ValueError, match=match):
        physics.check_laws(laws)
    g = _grid()
    with g.writing(writer=None), pytest.raises(ValueError, match=match):
        physics.run_physics(g, 1.0, min_substeps=1, power=lambda: None, laws=laws)


def _grid(dx_m: float = 0.2) -> MaterialGrid:
    g = MaterialGrid.empty((1.0, 1.0, 1.0), MATERIALS, dx_m=dx_m)
    with g.writing(writer=CONSTRUCTION):
        g.paint(np.ones(g.shape, dtype=bool), "concrete")
    return g


def test_physics_over_no_time_runs_no_substep_and_moves_no_clock():
    g = _grid()
    with g.writing(writer=None):
        assert physics.run_physics(g, 0.0, min_substeps=4, power=lambda: None) == 0
        assert physics.run_physics(g, -1.0, min_substeps=4, power=lambda: None) == 0
    assert g.time_s == 0.0


# -- the write window refuses an undeclared writer (B43) --------------------------------------------------------


def test_a_law_cannot_write_a_field_the_registry_does_not_declare_for_it():
    """Heat writes temperature only: integrity is a read-only view for it, and it can't paint or destroy. Proven by
    deleting the check: with ``_channel`` returning the array whatever the writer, the first raises go green."""
    g = _grid()
    with g.writing(writer=None):
        with g.as_writer("heat"):
            g.temperature[0, 0, 0] = 30.0  # declared
            with pytest.raises(ValueError, match="read-only"):
                g.integrity[0, 0, 0] = 0.5
            with pytest.raises(UndeclaredWriter, match="'heat' is not a declared writer of 'material'"):
                g.destroy(np.ones(g.shape, dtype=bool))
            with pytest.raises(UndeclaredWriter, match="of 'material'"):
                g.paint(np.ones(g.shape, dtype=bool), "wood")
            inside = g.writer
            assert inside == "heat"
        with pytest.raises(ValueError, match="read-only"):  # the window's own writer None is nobody: laws narrow
            g.temperature[0, 0, 0] = 40.0
        with pytest.raises(UndeclaredWriter, match="of 'regions'"):
            g.name_region("x", np.ones(g.shape, dtype=bool), footprint_of([CUBE]), solid=True)
    assert g.writer is None
    assert g.temperature[0, 0, 0] == 30.0
    assert g.integrity[0, 0, 0] == 1.0


def test_a_writer_the_registry_does_not_know_is_refused():
    g = _grid()
    with pytest.raises(UndeclaredWriter, match="not a writer the field registry knows"), g.writing(writer="admin"):
        pass  # pragma: no cover - refused before the window opens
    assert not g.is_writing
    with (
        g.writing(writer=None),
        pytest.raises(UndeclaredWriter, match="not a writer the field registry knows"),
        g.as_writer("pyrolysis"),
    ):
        pass  # pragma: no cover - refused before the block runs
    with pytest.raises(WindowClosed, match="only inside the write window"), g.as_writer("heat"):
        pass  # pragma: no cover - refused outside the window


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


def test_construction_counts_as_one_batch_whether_or_not_it_goes_through_topology():
    g = MaterialGrid.empty((1.0, 1.0, 1.0), MATERIALS, dx_m=0.2)
    assert g.topology_version == 0
    with g.writing(writer=CONSTRUCTION):  # painted straight in the window: the window is the batch
        g.paint(np.ones(g.shape, dtype=bool), "wood")
        g.paint(np.ones(g.shape, dtype=bool), "steel")
    assert g.topology_version == 1
    with g.writing(writer=CONSTRUCTION):
        g.temperature[:] = 50.0  # not a world edit
    assert g.topology_version == 1
    assert SCENE.build(MATERIALS, dx_m=0.2).topology_version == 1  # Scene.build's one batch of requests


def test_topology_applies_only_as_itself_or_construction():
    g = _grid()
    with g.writing(writer=None), pytest.raises(ValueError, match="as Topology or construction"):
        topology.apply(g, [topology.Destroy(np.ones(g.shape, dtype=bool))], writer="heat")
    assert g.solid.all()


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
    with g.writing(writer=CONSTRUCTION):
        g.temperature[:] = 2000.0  # far past concrete's limit, for one short step
        assert damage.THERMAL.step(g, 1e-3, LawInputs()) == Changes()
        assert g.integrity.max() < 1.0
