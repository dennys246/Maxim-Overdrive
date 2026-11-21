"""Drive the solid: a gasification run (V, P0) or a cone test (P1, P2), recording a series every step.

Cone (§3, fire_solid §4.4): the pilot is present from t = 0 and adds no energy. At the end of each step the part's
mass flux m'' (gas released over the step ÷ dt) is compared with m''_flash (unignited) or m''_ext (flaming); a
change applies from the next step. While flaming, q''_fl is added to the incident flux and convection is off.
Q'' = m''·ΔH_c,eff while flaming (the one part is the whole sample), else 0. Every state change is counted (N3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
import spec
from kernel import Solid
from materials import Build

Array = npt.NDArray[np.float64]
BURNOUT_FRACTION = 1e-6  # CHOICE: a non-charring cone run stops when this fraction of its reactive mass is left


@dataclass(frozen=True)
class Flame:
    q_fl: float  # W/m²
    m_flash: float  # kg/m²s
    m_ext: float | None  # kg/m²s; None = no extinction (PMMA: unset, §4.4)
    dhc: float  # J/kg
    allow_inverted: bool = False  # N4 only: lets m_ext >= m_flash through, to prove the guard

    def __post_init__(self) -> None:
        if self.m_ext is not None and self.m_ext >= self.m_flash and not self.allow_inverted:
            raise ValueError("refused: m''_ext >= m''_flash (fire_solid §4.4 hysteresis)")


@dataclass
class Series:
    t: list[float] = field(default_factory=list)
    mdot: list[float] = field(default_factory=list)  # g/m²s, over the step ending at t
    mass: list[float] = field(default_factory=list)  # g/m² of the sample (first layer) at t
    q: list[float] = field(default_factory=list)  # kW/m²
    t_front: list[float] = field(default_factory=list)  # K, the face
    t_back: list[float] = field(default_factory=list)  # K, the first layer's deepest node
    flaming: list[bool] = field(default_factory=list)
    flashes: int = 0
    extinctions: int = 0
    worst_energy: float = 0.0
    worst_mass: float = 0.0
    lines_needed: dict[str, float] = field(default_factory=dict)
    merges: int = 0
    steps: int = 0
    initial_g: float = 0.0

    def arrays(self) -> dict[str, Array]:
        return {k: np.array(getattr(self, k), dtype=float) for k in ("t", "mdot", "mass", "q", "t_front", "t_back")}


def _record(s: Series, solid: Solid, t: float, mdot: float, q: float, flaming: bool) -> None:
    s.t.append(t)
    s.mdot.append(mdot * 1000.0)
    s.mass.append(solid.layer_mass(0) * 1000.0)
    s.q.append(q)
    s.t_front.append(solid.t_face)
    s.t_back.append(solid.last_node_t(0))
    s.flaming.append(flaming)


def _finish(s: Series, solid: Solid) -> Series:
    L = solid.ledger
    s.worst_energy, s.worst_mass = L.worst_energy, L.worst_mass
    s.lines_needed = dict(L.lines_needed)
    s.merges = solid.merges
    return s


def gasification(build: Build, *, flux: float, h: float, t_amb: float, dt: float, t_end: float) -> Series:
    """Anaerobic gasification: constant incident flux, convection h to gas at ambient, surroundings at ambient."""
    solid = Solid(build.comps, build.reactions, build.layers, t_amb)
    s = Series(initial_g=solid.layer_mass(0) * 1000.0)
    _record(s, solid, 0.0, 0.0, 0.0, False)
    n = round(t_end / dt)
    for i in range(1, n + 1):
        gas = solid.step(dt, flux, h, t_amb, t_amb)
        _record(s, solid, i * dt, gas / dt, 0.0, False)
    s.steps = n
    return _finish(s, solid)


def cone(
    build: Build,
    *,
    flux: float,
    flame: Flame,
    dt: float,
    t_end: float,
    stop_after_burnout: bool,
    t_amb: float = spec.CONE_T_AMB,
    h: float = spec.CONE_H,
    stop_at: float | None = None,
    heater_off_after_flash: float | None = None,
) -> Series:
    """A cone test. Stops at t_end, at `stop_at` seconds after the first flash (if given), or, for a non-charring
    sample, once its reactive mass is gone (nothing further can be released)."""
    solid = Solid(build.comps, build.reactions, build.layers, t_amb)
    s = Series(initial_g=solid.layer_mass(0) * 1000.0)
    _record(s, solid, 0.0, 0.0, 0.0, False)
    flaming = False
    reactive0 = solid.reactive_mass()
    t_flash: float | None = None
    n = round(t_end / dt)
    for i in range(1, n + 1):
        t = i * dt
        heater = flux
        if heater_off_after_flash is not None and t_flash is not None and t > t_flash + heater_off_after_flash:
            heater = 0.0  # ungraded prediction: the heater removed (§5 "also reported")
        incident = heater + (flame.q_fl if flaming else 0.0)
        gas = solid.step(dt, incident, 0.0 if flaming else h, t_amb, t_amb)
        mdot = gas / dt
        if not flaming and mdot >= flame.m_flash:
            flaming = True
            s.flashes += 1
            if t_flash is None:
                t_flash = t
        elif flaming and flame.m_ext is not None and mdot < flame.m_ext:
            flaming = False
            s.extinctions += 1
        _record(s, solid, t, mdot, mdot * flame.dhc / 1000.0 if flaming else 0.0, flaming)
        s.steps = i
        if stop_after_burnout and solid.reactive_mass() <= BURNOUT_FRACTION * reactive0:
            break
        if stop_at is not None and t_flash is not None and t >= t_flash + stop_at:
            break
    return _finish(s, solid)
