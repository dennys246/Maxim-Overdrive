"""The sources' deposit (sim_core.md §7): the bounding-box overlap and the caches hold the reference's bits, the
accumulation is in sorted-key order, and a cache holds only what the current sources need."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from simcore.core.deposit import Deposit, bounding_box, sphere_overlap
from simcore.core.exposure import Share, standing
from simcore.core.grid import Field, MaterialGrid
from simcore.core.scene import constructing
from simcore.core.world import HeatSource
from tests._cells import destroy, paint


def _grid(materials, solid=True):
    g = MaterialGrid.empty((1.2, 1.0, 0.8), materials, dx_m=0.2)
    if solid:
        with constructing(g):
            paint(g, np.ones(g.shape, dtype=bool), "wood")
    return g


def _power(deposit: Deposit, sources) -> Field:
    power = deposit.power(standing(sources, 5), 5)  # standing the whole step: the fraction is exactly 1.0
    assert power is not None
    return power


def _reference_overlap(grid, center_m, radius_m, samples=4):
    """PR 2's world.sphere_overlap, frozen (PR 3 review N4): the whole grid, with no box."""
    offs = (np.arange(samples) + 0.5) / samples * grid.dx
    frac = np.zeros(grid.shape, dtype=np.float64)
    base = [np.arange(n) * grid.dx for n in grid.shape]
    cx, cy, cz = center_m
    for ox in offs:
        dx2 = ((base[0] + ox - cx) ** 2)[:, None, None]
        for oy in offs:
            dy2 = ((base[1] + oy - cy) ** 2)[None, :, None]
            for oz in offs:
                dz2 = ((base[2] + oz - cz) ** 2)[None, None, :]
                frac += (dx2 + dy2 + dz2) <= radius_m**2
    return frac / samples**3


def _reference_power(grid, sources):
    """PR 2's World._power_field, frozen: whole-grid overlap, in the order the mapping gives."""
    power = np.zeros(grid.shape, dtype=np.float64)
    for src in sources.values():
        frac = _reference_overlap(grid, src.point_m, src.radius_m)
        on_solid = frac * grid.solid
        weights = on_solid if on_solid.sum() > 0 else frac
        if weights.sum() == 0:
            weights = np.zeros(grid.shape)
            weights[grid.cell_of(src.point_m)] = 1.0
        power += src.power_w * weights / weights.sum()
    return power


coords = st.floats(0.0, 0.79, allow_nan=False)
radii = st.floats(1e-3, 1.5, allow_nan=False)


@settings(max_examples=200, deadline=None)
@given(x=st.floats(0.0, 1.19), y=st.floats(0.0, 0.99), z=coords, r=radii)
def test_the_box_overlap_is_the_whole_grid_overlap_bit_for_bit(materials, x, y, z, r):
    g = _grid(materials)
    box = bounding_box(g, (x, y, z), r)
    whole = sphere_overlap(g, (x, y, z), r)
    inside = np.zeros(g.shape)
    inside[box] = sphere_overlap(g, (x, y, z), r, box)
    assert np.array_equal(inside, whole)
    assert np.array_equal(whole, _reference_overlap(g, (x, y, z), r))  # and the whole grid is PR 2's, bit for bit
    assert whole.sum() == whole[box].sum()  # nothing the box leaves out overlaps the sphere


@pytest.mark.parametrize("solid", [True, False])
@pytest.mark.parametrize("radius_m", [1e-4, 0.15, 0.3, 2.0])
def test_one_or_two_sources_deposit_the_references_bits(materials, solid, radius_m):
    g = _grid(materials, solid)
    sources = {"b": HeatSource((0.5, 0.5, 0.4), radius_m, 300.0), "a": HeatSource((0.61, 0.43, 0.3), 0.2, 7e3)}
    assert np.array_equal(_power(Deposit(g), sources), _reference_power(g, sources))


def test_three_overlapping_sources_accumulate_in_sorted_key_order_whatever_the_insertion_order(materials):
    g = _grid(materials)
    values = [HeatSource((0.5, 0.5, 0.4), 0.3, p) for p in (1e16, 1.0, 1.0)]  # (1e16 + 1) + 1 != 1e16 + (1 + 1)
    forward = dict(zip("abc", values, strict=True))
    backward = dict(reversed(list(forward.items())))
    assert list(backward) == ["c", "b", "a"]
    assert np.array_equal(_power(Deposit(g), forward), _power(Deposit(g), backward))
    assert np.array_equal(_power(Deposit(g), backward), _reference_power(g, forward))  # sorted is a, b, c
    assert not np.array_equal(_reference_power(g, forward), _reference_power(g, backward))  # the order is visible


def test_the_caches_hold_only_the_current_sources_at_the_current_topology(materials):
    g = _grid(materials)
    deposit = Deposit(g)
    fire = HeatSource((0.5, 0.5, 0.4), 0.3, 1e3)
    deposit.power(standing({"fire": fire}, 1), 1)
    assert set(deposit._overlaps) == {(fire.point_m, 0.3)}
    assert set(deposit._weights) == {(fire.point_m, 0.3, g.topology_version)}
    bigger = HeatSource(fire.point_m, 0.4, 1e3)  # a re-ignite with a new radius under the same id misses the cache
    deposit.power(standing({"fire": bigger}, 1), 1)
    assert set(deposit._overlaps) == {(fire.point_m, 0.4)}
    assert deposit.power((), 1) is None
    assert deposit._overlaps == {}
    assert deposit._weights == {}


def test_a_destroyed_cell_moves_the_weights_and_the_power_stays_the_references(materials):
    g = _grid(materials)
    deposit = Deposit(g)
    fire = {"fire": HeatSource((0.5, 0.5, 0.4), 0.3, 1e3)}
    before = _power(deposit, fire)
    with constructing(g):
        destroy(g, _cell(g, (0.5, 0.5, 0.4)))
    after = _power(deposit, fire)
    assert set(deposit._weights) == {((0.5, 0.5, 0.4), 0.3, g.topology_version)}
    assert not np.array_equal(before, after)
    assert np.array_equal(after, _reference_power(g, fire))


def _cell(g, point):
    mask = np.zeros(g.shape, dtype=bool)
    mask[g.cell_of(point)] = True
    return mask


def test_a_share_delivers_its_fraction_of_the_step(materials):
    """sim_core.md §3: a value that stood k of a step's 5 ticks delivers k/5 of its power over the step, deposited
    where its own point and radius put it; two values under one key (a re-ignite) each at their own power."""
    g = _grid(materials)
    first, second = HeatSource((0.5, 0.5, 0.4), 0.3, 1e3), HeatSource((0.7, 0.5, 0.4), 0.2, 4e3)
    for k in range(1, 6):
        share = Deposit(g).power((Share("fire", first, k),), 5)
        assert share is not None
        assert _power(Deposit(g), {"fire": first}).sum() * k / 5 == pytest.approx(share.sum(), rel=1e-15)
    both = Deposit(g).power((Share("fire", first, 2), Share("fire", second, 3)), 5)
    expected = _reference_power(g, {"a": first}) * 2 / 5 + _reference_power(g, {"b": second}) * 3 / 5
    assert both == pytest.approx(expected, rel=1e-12, abs=1e-9)


class _Raised(Exception):
    pass


def test_a_window_that_rolls_back_leaves_no_entry_a_later_state_could_reuse(materials):
    """sim_core.md §7: a cache's contents are a function of state. A rollback restores ``topology_version``, so an
    entry built inside the rolled-back window would be found again by a different edit that reaches the same version
    (PR 3 review S1, all three lenses: 75 W into a destroyed cell). Edit A, deposit, raise; then edit B: the deposit is
    a fresh one's, bit for bit."""
    g = _grid(materials)
    deposit = Deposit(g)
    fire = {"fire": HeatSource((0.5, 0.5, 0.4), 0.3, 1e3)}
    _power(deposit, fire)
    v0 = g.topology_version

    def edit_a_then_raise() -> None:
        with constructing(g):
            destroy(g, _cell(g, (0.5, 0.5, 0.4)))  # edit A: version v0 + 1
            _power(deposit, fire)  # an entry for A's cells at v0 + 1
            raise _Raised

    with pytest.raises(_Raised):
        edit_a_then_raise()
    assert g.topology_version == v0
    with constructing(g):
        destroy(g, _cell(g, (0.3, 0.5, 0.4)))  # edit B, another cell: version v0 + 1 again
    assert g.topology_version == v0 + 1
    assert np.array_equal(_power(deposit, fire), _power(Deposit(g), fire))
    assert _power(deposit, fire)[g.cell_of((0.3, 0.5, 0.4))] == 0.0  # nothing lands in B's destroyed cell


def test_a_cached_entry_cannot_be_written(materials):
    """PR 3 review N3 (Performance): every later hit shares a cached array, so one in-place write would poison them."""
    g = _grid(materials)
    deposit = Deposit(g)
    _power(deposit, {"fire": HeatSource((0.5, 0.5, 0.4), 0.3, 1e3)})
    ((_, overlap),) = deposit._overlaps.values()
    ((_, weights, _),) = deposit._weights.values()
    for arr in (overlap, weights):
        with pytest.raises(ValueError, match="read-only"):
            np.multiply(arr, 2.0, out=arr)
