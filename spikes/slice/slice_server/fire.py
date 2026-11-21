"""The slice's fire: a per-object fuel budget, a surface skin for ignition, and radiative spread (plan §3.3, VS4).

Not fire's model, and nothing cites it as one: fire's truth is ``fire_solid.md`` and the ladder. This module only
decides. ``Fire.step`` returns what should change (an object lit, its power set, an object burnt out) and the
simulation applies each decision through ``simcore.core.applier``, so the world still changes in one place.

- **Fuel.** Each flammable named object holds a fuel mass: its box's volume x density x a fuel fraction (the share
  of the box that is burnable: slats and packing, a gamey per-object number). A burning object releases
  ``burn_rate x area x releasable_energy`` watts, with the burning area shrinking as fuel goes, ``(m / m0)^(2/3)``.
  It burns out at 5% of its fuel, the tile spec's ``t_gone`` rule.
- **Ignition.** A skin node per object, the outer ``skin_depth_m`` of its exposed faces, heated by the radiation it
  absorbs and cooled by convection and its own re-radiation. The object lights when its skin passes the material's
  ignition temperature. The skin is the slice's, not the world's: its energy is not put into cells, the same
  "exported, unreceived" accounting the tile spec gives flame radiation (``tile_and_client.md`` §1.2).
- **Spread.** A burning object radiates as a point source at its centroid, ``q = chi_r P / (4 pi r^2)``, the
  point-source model of fire engineering; a target receives it on its nearest point.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

STEFAN_BOLTZMANN = 5.670374419e-8
KELVIN = 273.15

Point = tuple[float, float, float]
Bounds = tuple[Point, Point]


@dataclass(frozen=True)
class FuelMaterial:
    releasable_energy_j_kg: float
    ignition_c: float
    burn_rate_kg_s_m2: float
    density_kg_m3: float
    volumetric_heat_capacity_j_m3k: float  # density x specific heat, for the skin


@dataclass(frozen=True)
class FireParams:
    radiant_fraction: float
    source_radius_m: float
    burnout_fraction: float
    skin_depth_m: float
    skin_h_w_m2k: float
    emissivity: float
    ambient_c: float


@dataclass
class Fuel:
    """One flammable object's fire state."""

    name: str
    material: FuelMaterial
    centroid: Point
    bounds: Bounds
    area_m2: float
    fuel0_kg: float
    fuel_kg: float
    skin_c: float
    burning: bool = False
    burnt_out: bool = False
    released_j: float = 0.0

    def power_w(self) -> float:
        if not self.burning:
            return 0.0
        area = self.area_m2 * (self.fuel_kg / self.fuel0_kg) ** (2.0 / 3.0)
        return self.material.burn_rate_kg_s_m2 * area * self.material.releasable_energy_j_kg

    def peak_power_w(self) -> float:
        return self.material.burn_rate_kg_s_m2 * self.area_m2 * self.material.releasable_energy_j_kg


@dataclass(frozen=True)
class Decision:
    """What the simulation must do through the applier: ``power_w`` > 0 sets the object's fire, 0 puts it out."""

    region: str
    power_w: float


@dataclass
class Fire:
    params: FireParams
    fuels: dict[str, Fuel] = field(default_factory=dict)

    def flux_at(self, point: Point, *, exclude: str | None = None) -> float:
        """Radiant flux (W/m^2) at ``point`` from every burning object but ``exclude``."""
        total = 0.0
        for fuel in self.fuels.values():
            if fuel.burning and fuel.name != exclude:
                total += point_flux(self.params.radiant_fraction * fuel.power_w(), fuel.centroid, point)
        return total

    def kindle(self, region: str) -> str | None:
        """Light ``region`` with a pilot flame. Returns why not, or None when it is lit."""
        fuel = self.fuels.get(region)
        if fuel is None:
            return f"the {region} doesn't burn"
        if fuel.burnt_out:
            return f"the {region} has burnt out"
        fuel.burning = True
        return None

    def step(self, dt: float) -> tuple[list[Decision], list[dict[str, object]]]:
        """One tick: heat the skins, light what passes ignition, burn fuel. Returns decisions and events."""
        events: list[dict[str, object]] = []
        fluxes = {name: self._flux_on(fuel) for name, fuel in self.fuels.items() if not fuel.burning}
        for name, flux in fluxes.items():
            fuel = self.fuels[name]
            if fuel.burnt_out:
                continue
            fuel.skin_c += self._skin_rate(fuel, flux) * dt
            if fuel.skin_c >= fuel.material.ignition_c:
                fuel.burning = True
                events.append({"type": "event", "what": "ignited", "region": name, "flux_w_m2": flux})
        decisions = []
        for name, fuel in sorted(self.fuels.items()):
            if not fuel.burning:
                continue
            power = fuel.power_w()
            burned = power / fuel.material.releasable_energy_j_kg * dt
            if fuel.fuel_kg - burned <= self.params.burnout_fraction * fuel.fuel0_kg:
                fuel.burning, fuel.burnt_out = False, True
                decisions.append(Decision(name, 0.0))
                events.append({"type": "event", "what": "burnt_out", "region": name})
                continue
            fuel.fuel_kg -= burned
            fuel.released_j += power * dt
            decisions.append(Decision(name, power))
        return decisions, events

    def _flux_on(self, fuel: Fuel) -> float:
        """The flux on a target's face nearest each source, summed."""
        total = 0.0
        for src in self.fuels.values():
            if src.burning and src.name != fuel.name:
                near = nearest_point(fuel.bounds, src.centroid)
                total += point_flux(self.params.radiant_fraction * src.power_w(), src.centroid, near)
        return total

    def _skin_rate(self, fuel: Fuel, flux: float) -> float:
        """dT/dt of the skin (K/s): absorbed radiation less convection and re-radiation, over the skin's capacity."""
        p = self.params
        t, ta = fuel.skin_c + KELVIN, p.ambient_c + KELVIN
        net = p.emissivity * flux - p.skin_h_w_m2k * (t - ta) - p.emissivity * STEFAN_BOLTZMANN * (t**4 - ta**4)
        return net / (fuel.material.volumetric_heat_capacity_j_m3k * p.skin_depth_m)


def point_flux(radiated_w: float, source: Point, target: Point) -> float:
    """The point-source model: radiated power spread over a sphere through the target, ``P_r / (4 pi r^2)``. Closer
    than 0.3 m (inside a source's own flame) it is capped at that distance's value."""
    r = max(math.dist(source, target), 0.3)
    return radiated_w / (4.0 * math.pi * r * r)


def nearest_point(bounds: Bounds, p: Point) -> Point:
    (x0, y0, z0), (x1, y1, z1) = bounds
    return (min(max(p[0], x0), x1), min(max(p[1], y0), y1), min(max(p[2], z0), z1))


def exposed_area(bounds: Bounds, floor_z: float) -> float:
    """A box's surface area, less its bottom face when it rests on the floor."""
    (x0, y0, z0), (x1, y1, z1) = bounds
    a, b, c = x1 - x0, y1 - y0, z1 - z0
    total = 2 * (a * b + b * c + a * c)
    return total - a * b if math.isclose(z0, floor_z) else total


def fuels_from(
    boxes: Mapping[str, tuple[str, Bounds]],
    fractions: Mapping[str, float],
    materials: Mapping[str, FuelMaterial],
    *,
    floor_z: float,
    ambient_c: float,
) -> dict[str, Fuel]:
    """A ``Fuel`` for every named box whose name has a fuel fraction; its material must be flammable."""
    out: dict[str, Fuel] = {}
    for name, fraction in sorted(fractions.items()):
        if name not in boxes:
            raise ValueError(f"fuel names {name!r}, which the alley doesn't have")
        material_name, bounds = boxes[name]
        if material_name not in materials:
            raise ValueError(f"the {name} is {material_name}, which has no fuel entry (it doesn't burn)")
        material = materials[material_name]
        (x0, y0, z0), (x1, y1, z1) = bounds
        volume = (x1 - x0) * (y1 - y0) * (z1 - z0)
        mass = volume * material.density_kg_m3 * fraction
        centroid = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        out[name] = Fuel(name, material, centroid, bounds, exposed_area(bounds, floor_z), mass, mass, ambient_c)
    return out
