import dataclasses
import math

import pytest
from slice_server import config
from slice_server.fire import (
    Fire,
    FireParams,
    Fuel,
    FuelMaterial,
    exposed_area,
    fuels_from,
    nearest_point,
    point_flux,
)

WOOD = FuelMaterial(12.4e6, 300.0, 0.016, 600.0, 600.0 * 1700.0)
PARAMS = config.load().fuel.fire
BOX = ((6.0, 2.6, 0.4), (6.6, 3.2, 1.0))


def _fuel(name: str = "crate", fraction: float = 0.025, bounds=BOX) -> Fuel:
    return fuels_from({name: ("wood", bounds)}, {name: fraction}, {"wood": WOOD}, floor_z=0.4, ambient_c=20.0)[name]


def test_the_point_source_law_and_its_near_field_cap() -> None:
    assert point_flux(4 * math.pi, (0, 0, 0), (2, 0, 0)) == pytest.approx(0.25)  # P / (4 pi r^2)
    assert point_flux(4 * math.pi, (0, 0, 0), (0.1, 0, 0)) == point_flux(4 * math.pi, (0, 0, 0), (0.3, 0, 0))


def test_geometry_helpers() -> None:
    assert exposed_area(BOX, 0.4) == pytest.approx(5 * 0.36)  # five faces: the bottom sits on the floor
    assert exposed_area(((0, 0, 1), (1, 1, 2)), 0.4) == pytest.approx(6.0)
    assert nearest_point(BOX, (7.0, 2.9, 0.7)) == (6.6, 2.9, 0.7)


def test_a_burn_releases_exactly_the_fuel_it_burns_times_the_releasable_energy() -> None:
    fire = Fire(PARAMS, {"crate": _fuel()})
    assert fire.kindle("crate") is None
    for _ in range(500):
        fire.step(0.1)
    fuel = fire.fuels["crate"]
    burned = fuel.fuel0_kg - fuel.fuel_kg
    assert burned > 0
    assert fuel.released_j == pytest.approx(burned * WOOD.releasable_energy_j_kg, rel=1e-9)


def test_the_burnout_time_follows_the_shrinking_area_closed_form() -> None:
    # dm/dt = -k m0^(1/3) m^(2/3) with k = rate x area / m0^(2/3)... integrated: t = 3 m0 / (rate A) (1 - f^(1/3)).
    fuel = _fuel()
    fire = Fire(PARAMS, {"crate": fuel})
    fire.kindle("crate")
    t, dt = 0.0, 0.1
    while not fuel.burnt_out:
        fire.step(dt)
        t += dt
    want = 3 * fuel.fuel0_kg / (WOOD.burn_rate_kg_s_m2 * fuel.area_m2) * (1 - PARAMS.burnout_fraction ** (1 / 3))
    assert t == pytest.approx(want, rel=0.01)  # explicit Euler's first-order error over ~2,000 steps
    decisions, _ = fire.step(dt)
    assert decisions == []  # out means out: no more power, no relighting
    assert fire.kindle("crate") == "the crate has burnt out"


def test_burnout_returns_a_zero_power_decision_once() -> None:
    fire = Fire(PARAMS, {"crate": _fuel(fraction=0.0005)})
    fire.kindle("crate")
    decisions = []
    for _ in range(400):
        decisions += fire.step(0.1)[0]
    assert decisions[-1].out, "the last decision puts the fire out"
    assert sum(d.out for d in decisions) == 1
    assert decisions[0].power_w == 0.0, "a fire that has just lit has not grown yet, and is not out"


def _heated_skin(flux: float, seconds: float) -> Fuel:
    target = _fuel("pallet", bounds=((7.0, 2.6, 0.4), (7.6, 3.2, 1.0)))
    fire = Fire(PARAMS, {"pallet": target})
    for _ in range(int(seconds / 0.1)):
        target.skin_c += fire._skin_rate(target, flux) * 0.1
    return target


def test_a_skin_settles_where_absorbed_radiation_balances_its_losses() -> None:
    skin = _heated_skin(5000.0, 3600.0)
    t, ta = skin.skin_c + 273.15, 293.15
    lost = PARAMS.skin_h_w_m2k * (t - ta) + PARAMS.emissivity * 5.670374419e-8 * (t**4 - ta**4)
    assert lost == pytest.approx(PARAMS.emissivity * 5000.0, rel=1e-6)


def test_wood_lights_above_its_critical_flux_and_not_below() -> None:
    # Wood's critical flux for piloted ignition is about 12 kW/m^2: the skin model must put it between 5 and 17.
    assert _heated_skin(5000.0, 1800.0).skin_c < 300.0
    assert _heated_skin(17000.0, 120.0).skin_c >= 300.0


def test_a_fire_lights_a_neighbour_by_radiation() -> None:
    crate = _fuel()
    pallet = _fuel("pallet", fraction=0.03, bounds=((7.0, 2.6, 0.4), (7.6, 3.2, 1.0)))
    fire = Fire(PARAMS, {"crate": crate, "pallet": pallet})
    fire.kindle("crate")
    seconds = 0.0
    while not pallet.burning and seconds < 120:
        fire.step(0.1)
        seconds += 0.1
    assert pallet.burning, "the pallet should light within two minutes"
    assert seconds > 5, "not at once: its skin has to heat first"


def test_only_fuel_kindles() -> None:
    fire = Fire(PARAMS, {"crate": _fuel()})
    assert fire.kindle("wall_north") == "the wall_north doesn't burn"


def test_fuels_from_refuses_unknown_names_and_non_fuel_materials() -> None:
    with pytest.raises(ValueError, match="doesn't have"):
        fuels_from({}, {"ghost": 0.1}, {"wood": WOOD}, floor_z=0.4, ambient_c=20.0)
    with pytest.raises(ValueError, match="doesn't burn"):
        fuels_from({"wall": ("concrete", BOX)}, {"wall": 0.1}, {"wood": WOOD}, floor_z=0.4, ambient_c=20.0)


def test_fire_params_come_from_the_fuel_file() -> None:
    assert isinstance(PARAMS, FireParams)
    assert dataclasses.asdict(PARAMS)["ambient_c"] == 20.0


def test_a_fire_grows_as_t_squared_to_its_fuel_limited_power() -> None:
    fuel = _fuel()
    fuel.growth_s = 90.0
    fire = Fire(PARAMS, {"crate": fuel})
    fire.kindle("crate")
    full = fuel.peak_power_w()
    for _ in range(450):  # 45 s: half the growth time
        fire.step(0.1)
    shrink = (fuel.fuel_kg / fuel.fuel0_kg) ** (2 / 3)
    assert fuel.power_w() == pytest.approx(full * shrink * 0.25, rel=1e-6)
    for _ in range(600):  # past the growth time: fuel-limited
        fire.step(0.1)
    assert fuel.power_w() == pytest.approx(full * (fuel.fuel_kg / fuel.fuel0_kg) ** (2 / 3), rel=1e-12)
