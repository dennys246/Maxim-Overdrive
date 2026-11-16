"""SEM for the environment: a wall, a door or a crate is an SEM Entity whose sensors read its cells.

The environment is not embodied (it has no drives, pain or learning), but it speaks the same Sensor / Modulator
vocabulary as a body, so a Maxim agent perceives and acts on a wall exactly as it does on its own arm:

    sensors     integrity (mean over the region's cells), temperature_max, temperature_mean, breached
    modulators  structure.strike(energy_j, sigma_m, point_m), structure.ignite(power_w, radius_m),
                structure.extinguish()

Sensors are reductions over cells, so a region reads the same at every rig; the cells underneath are as fine as the
rig allows. With pymaxim installed, ``to_maxim_entity`` returns a real ``maxim.embodiment.sem.Entity``, and Maxim's
own tool generation, gating and prompt formatting work on it unchanged. Without pymaxim, the same classes run on
local stand-ins with the same fields.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np

from maxim_overdrive.config import ActionLimits
from maxim_overdrive.world import damage
from maxim_overdrive.world.checks import finite_real, finite_vector
from maxim_overdrive.world.world import HeatSource, World

if TYPE_CHECKING:
    # Type-check against Maxim's own classes; tests/test_sem_compat.py holds the _compat mirror to the same fields.
    from maxim.embodiment.sem import AffordanceSchema, Entity, ModulatorResult, SensorReading

    HAVE_MAXIM: bool
else:
    try:  # Maxim's frozen SEM types, when available.
        from maxim.embodiment.sem import AffordanceSchema, Entity, ModulatorResult, SensorReading

        HAVE_MAXIM = True
    except ImportError:  # exercised by tests/test_sem_compat.py, which blocks the maxim import
        from maxim_overdrive.sem_env._compat import AffordanceSchema, ModulatorResult, SensorReading

        Entity = None
        HAVE_MAXIM = False


class RegionSensor:
    _UNITS: ClassVar[dict[str, str]] = {
        "integrity": "ratio",
        "temperature_max": "celsius",
        "temperature_mean": "celsius",
        "breached": "bool",
    }

    def __init__(self, world: World, region: str, quantity: str) -> None:
        if quantity not in self._UNITS:
            raise ValueError(f"unknown region quantity {quantity!r}")
        if region not in world.grid.regions:
            raise KeyError(f"no region {region!r} in this world")
        self._world, self._region, self._quantity = world, region, quantity

    @property
    def name(self) -> str:
        return self._quantity

    @property
    def unit(self) -> str:
        return self._UNITS[self._quantity]

    @property
    def reading_schema(self) -> dict[str, Any]:
        if self._quantity == "integrity":
            return {"type": "float", "range": [0.0, 1.0]}
        if self._quantity == "breached":
            return {"type": "float", "range": [0.0, 1.0]}
        return {"type": "float", "range": [-273.0, 6000.0]}

    def value(self) -> float:
        g = self._world.grid
        if self._quantity == "integrity":
            return damage.region_integrity(g, self._region)
        if self._quantity == "breached":
            return 1.0 if damage.region_breached(g, self._region) else 0.0
        mask = g.regions[self._region]
        temps = g.temperature[mask]
        if temps.size == 0:
            return float("nan")
        return float(np.max(temps) if self._quantity == "temperature_max" else np.mean(temps))

    def read(self) -> SensorReading:
        return SensorReading(
            sensor_name=self.name,
            entity_name=self._region,
            value=self.value(),
            unit=self.unit,
            timestamp=self._world.grid.time_s,
            extra={"cell_size_m": self._world.grid.dx},
        )


class ActionRefused(ValueError):
    """An action's parameters broke a rule; the message names the parameter. Nothing in the world has changed."""


@dataclass(frozen=True)
class Strike:
    energy_j: float
    sigma_m: float
    point_m: tuple[float, float, float] | None  # None: the region's centroid, found when the action applies


@dataclass(frozen=True)
class Ignite:
    power_w: float
    radius_m: float


@dataclass(frozen=True)
class Extinguish:
    pass


Action = Strike | Ignite | Extinguish

_ALLOWED_PARAMS: dict[str, frozenset[str]] = {
    "strike": frozenset({"energy_j", "sigma_m", "point_m"}),
    "ignite": frozenset({"power_w", "radius_m"}),
    "extinguish": frozenset(),
}


def _number(params: Mapping[str, Any], name: str, lo: float, hi: float, default: float | None = None) -> float:
    """One parameter as a finite float in [lo, hi], or ActionRefused naming it."""
    if name not in params:
        if default is None:
            raise ActionRefused(f"{name} is required")
        return default
    value = params[name]
    try:
        f: float | None = finite_real(value, name)
    except ValueError:
        f = None
    if f is None or not lo <= f <= hi:
        raise ActionRefused(f"{name} must be a finite number in [{lo:g}, {hi:g}], got {value!r}")
    return f


def parse_action(affordance: object, params: object, limits: ActionLimits) -> Action:
    """Untrusted (affordance, params) as a typed action inside ``limits``, or ActionRefused saying why.

    It reads nothing from the world, so it can run wherever input arrives (the protocol layer, an LLM's tool call)
    before the world-dependent checks that run when the action applies.
    """
    if not isinstance(params, Mapping):
        raise ActionRefused("params must be a mapping of names to values")
    allowed = _ALLOWED_PARAMS.get(affordance) if isinstance(affordance, str) else None
    if allowed is None:
        raise ActionRefused(f"unknown affordance {affordance!r}")
    unknown = sorted(str(k) for k in params if k not in allowed)
    if unknown:
        raise ActionRefused(f"unknown parameter(s) for {affordance}: {', '.join(unknown)}")
    if affordance == "strike":
        point: tuple[float, float, float] | None = None
        if params.get("point_m") is not None:
            try:
                x, y, z = finite_vector(params["point_m"], 3, "point_m")
            except ValueError as exc:
                raise ActionRefused(str(exc)) from None
            point = (x, y, z)
        return Strike(
            _number(params, "energy_j", 0.0, limits.max_energy_j),
            _number(params, "sigma_m", limits.min_sigma_m, limits.max_sigma_m, default=0.15),
            point,
        )
    if affordance == "ignite":
        return Ignite(
            _number(params, "power_w", 0.0, limits.max_power_w),
            _number(params, "radius_m", limits.min_radius_m, limits.max_radius_m, default=0.3),
        )
    return Extinguish()


class StructureModulator:
    """What can be done *to* a region. Actions change cells; time passes only in ``World.advance``.

    This is a trust boundary: an NPC's tool call, an LLM's output and a client's intent all arrive here. Parameters
    are a closed set per affordance, each a finite real number inside ``limits``. A refused action changes nothing.
    """

    name = "structure"

    def __init__(self, world: World, region: str, *, limits: ActionLimits) -> None:
        if region not in world.grid.regions:
            raise KeyError(f"no region {region!r} in this world")
        self._world, self._region, self._limits = world, region, limits

    @property
    def affordances(self) -> dict[str, AffordanceSchema]:
        return {
            "strike": AffordanceSchema(
                params={"energy_j": float, "sigma_m": (float, 0.15), "point_m": (list, None)},
                description="Deliver mechanical energy to this structure (a blow, a bullet, a blast).",
            ),
            "ignite": AffordanceSchema(
                params={"power_w": float, "radius_m": (float, 0.3)},
                description="Start a fire at this structure's surface; it burns until extinguished.",
            ),
            "extinguish": AffordanceSchema(description="Put out a fire started on this structure."),
        }

    def centroid_m(self) -> tuple[float, float, float]:
        idx = np.argwhere(self._world.grid.regions[self._region])
        if idx.size == 0:
            raise ValueError(f"region {self._region!r} has no cells")
        c = (idx.mean(axis=0) + 0.5) * self._world.grid.dx
        return (float(c[0]), float(c[1]), float(c[2]))

    def _result(
        self, affordance: str, params: dict[str, Any], ok: bool, error: str | None = None, **meta: Any
    ) -> ModulatorResult:
        return ModulatorResult(
            success=ok,
            modulator_name=self.name,
            entity_name=self._region,
            affordance=affordance,
            params=dict(params),
            error=error,
            metadata=meta,
        )

    def execute(self, affordance: str, params: dict[str, Any]) -> ModulatorResult:
        """Parse, then apply. A refusal at either stage is a failed result, and the world is unchanged."""
        shown = dict(params) if isinstance(params, Mapping) else {}
        try:
            action = parse_action(affordance, params, self._limits)
        except ActionRefused as exc:
            return self._result(affordance, shown, False, str(exc))
        return self.apply(affordance, shown, action)

    def apply(self, affordance: str, params: dict[str, Any], action: Action) -> ModulatorResult:
        """Apply an already parsed action. Its only refusals depend on the world as it is now."""
        try:
            if isinstance(action, Strike):
                point = action.point_m if action.point_m is not None else self.centroid_m()
                res = damage.strike(self._world.grid, point, action.energy_j, action.sigma_m)
                return self._result(
                    affordance, params, True, destroyed_volume_m3=res.destroyed_volume_m3, absorbed_j=res.absorbed_j
                )
            if isinstance(action, Ignite):
                source = HeatSource(self.centroid_m(), action.radius_m, action.power_w)
                self._world.sources[f"fire:{self._region}"] = source
                return self._result(affordance, params, True)
        except ValueError as exc:  # the region lost every cell, so it has no centroid to act on
            return self._result(affordance, params, False, f"{type(exc).__name__}: {exc}")
        had = self._world.sources.pop(f"fire:{self._region}", None) is not None
        return self._result(affordance, params, had, None if had else "nothing is burning here")


def region_parts(
    world: World, region: str, *, limits: ActionLimits
) -> tuple[dict[str, RegionSensor], dict[str, StructureModulator]]:
    sensors = {q: RegionSensor(world, region, q) for q in RegionSensor._UNITS}
    return sensors, {"structure": StructureModulator(world, region, limits=limits)}


def to_maxim_entity(world: World, region: str, *, limits: ActionLimits, entity_type: str = "structure") -> Entity:
    """A real Maxim Entity for one region. Requires pymaxim."""
    if not HAVE_MAXIM:
        raise RuntimeError("pymaxim is not installed: pip install 'maxim-overdrive[maxim]'")
    sensors, modulators = region_parts(world, region, limits=limits)
    return Entity(
        region,
        entity_type,
        sensors=sensors,  # type: ignore[arg-type]
        modulators=modulators,  # type: ignore[arg-type]
        metadata={"source": "maxim_overdrive.sem_env", "cell_size_m": world.grid.dx},
    )
