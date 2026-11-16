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

import reprlib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np
import numpy.typing as npt

from maxim_overdrive.checks import finite_real, finite_vector
from maxim_overdrive.config import ActionLimits
from maxim_overdrive.world import damage
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
    """An action broke a rule; the message says which, in words fit for whoever asked. The world is unchanged."""


# Keys Maxim adds to every call on some paths, which name nothing the action needs. Maxim's orchestrator-actor tool
# (maxim/simulation/tools.py, OrchestratorActorTool) always passes target=<Entity>: the entity this modulator
# already belongs to. They are accepted and dropped; any other unknown key is refused.
MAXIM_CALL_KEYS = frozenset({"target"})

_SHOW = reprlib.Repr()
_SHOW.maxstring = _SHOW.maxother = 40


def _shown(value: object) -> str:
    """A bounded repr for an error message, so a huge or hostile value can't flood (or crash) the reply."""
    # Python 3.10's reprlib calls repr() on an int, which raises past 4300 digits; 3.12+ prints a placeholder. The
    # tests' 10**5000 cases go red without this on 3.10, which CI runs.
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 128:
        return f"<an integer of about {int(value.bit_length() * 0.30103)} digits>"
    return _SHOW.repr(value)


def _within(name: str, value: float, lo: float, hi: float) -> None:
    if not lo <= value <= hi:
        raise ActionRefused(f"{name} must be between {lo:g} and {hi:g}, got {value:g}")


@dataclass(frozen=True)
class Strike:
    energy_j: float
    sigma_m: float
    point_m: tuple[float, float, float] | None  # None: the region's centroid, found when the action applies

    def check(self, limits: ActionLimits) -> None:
        _within("energy_j", self.energy_j, 0.0, limits.max_energy_j)
        _within("sigma_m", self.sigma_m, limits.min_sigma_m, limits.max_sigma_m)


@dataclass(frozen=True)
class Ignite:
    power_w: float
    radius_m: float

    def check(self, limits: ActionLimits) -> None:
        _within("power_w", self.power_w, 0.0, limits.max_power_w)
        _within("radius_m", self.radius_m, limits.min_radius_m, limits.max_radius_m)


@dataclass(frozen=True)
class Extinguish:
    def check(self, limits: ActionLimits) -> None:
        pass


Action = Strike | Ignite | Extinguish

_ALLOWED_PARAMS: dict[str, frozenset[str]] = {
    "strike": frozenset({"energy_j", "sigma_m", "point_m"}),
    "ignite": frozenset({"power_w", "radius_m"}),
    "extinguish": frozenset(),
}


def _real(params: Mapping[str, Any], name: str, default: float | None = None) -> float:
    if name not in params or params[name] is None:
        if default is None:
            raise ActionRefused(f"{name} is required")
        return default
    try:
        return finite_real(params[name], name)
    except ValueError:  # reported, with the parameter's name, as the refusal
        raise ActionRefused(f"{name} must be a finite number, got {_shown(params[name])}") from None


def parse_action(affordance: object, params: object, limits: ActionLimits) -> Action:
    """Untrusted (affordance, params) as a typed action inside ``limits``, or ActionRefused saying why.

    ``params`` is JSON-shaped: a mapping of names to numbers, lists or None, as an LLM's tool call or a client's
    intent gives it. Numbers must be real numbers; numeric strings such as "1000" are refused, deliberately, so a
    value is never guessed. It reads nothing from the world, so it can run wherever input arrives, before the
    world-dependent checks in ``StructureModulator.apply``.
    """
    if not isinstance(params, Mapping):
        raise ActionRefused("params must be a mapping of names to values")
    allowed = _ALLOWED_PARAMS.get(affordance) if isinstance(affordance, str) else None
    if allowed is None:
        raise ActionRefused(f"unknown affordance {_shown(affordance)}")
    unknown = sorted(_shown(k) for k in params if k not in allowed and k not in MAXIM_CALL_KEYS)
    if unknown:
        raise ActionRefused(f"unknown parameter(s) for {affordance}: {', '.join(unknown)}")
    action: Action
    if affordance == "strike":
        point: tuple[float, float, float] | None = None
        if params.get("point_m") is not None:
            try:
                x, y, z = finite_vector(params["point_m"], 3, "point_m")
            except ValueError:  # reported as the refusal
                raise ActionRefused(f"point_m must be 3 finite numbers, got {_shown(params['point_m'])}") from None
            point = (x, y, z)
        action = Strike(_real(params, "energy_j"), _real(params, "sigma_m", limits.default_sigma_m), point)
    elif affordance == "ignite":
        action = Ignite(_real(params, "power_w"), _real(params, "radius_m", limits.default_radius_m))
    else:
        action = Extinguish()
    action.check(limits)
    return action


class StructureModulator:
    """What can be done *to* a region. Actions change cells; time passes only in ``World.advance``.

    This is a trust boundary: an NPC's tool call, an LLM's output and a client's intent will all arrive here.
    ``execute`` parses, then applies; a refusal at either stage is a failed result and changes nothing.
    """

    name = "structure"

    def __init__(self, world: World, region: str) -> None:
        if region not in world.grid.regions:
            raise KeyError(f"no region {region!r} in this world")
        self._world, self._region = world, region

    @property
    def affordances(self) -> dict[str, AffordanceSchema]:
        lim = self._world.limits
        return {
            "strike": AffordanceSchema(
                params={"energy_j": float, "sigma_m": (float, lim.default_sigma_m), "point_m": (list, None)},
                description=(
                    "Deliver mechanical energy to this structure (a blow, a bullet, a blast): energy_j up to "
                    f"{lim.max_energy_j:g} J, spread over sigma_m from {lim.min_sigma_m:g} to {lim.max_sigma_m:g} m, "
                    "at point_m on the structure (its middle if omitted)."
                ),
            ),
            "ignite": AffordanceSchema(
                params={"power_w": float, "radius_m": (float, lim.default_radius_m)},
                description=(
                    "Start a fire at this structure's surface; it burns until extinguished. power_w up to "
                    f"{lim.max_power_w:g} W, radius_m from {lim.min_radius_m:g} to {lim.max_radius_m:g} m."
                ),
            ),
            "extinguish": AffordanceSchema(description="Put out a fire started on this structure."),
        }

    def _cells(self) -> npt.NDArray[np.intp]:
        return np.argwhere(self._world.grid.regions[self._region])

    def centroid_m(self) -> tuple[float, float, float]:
        idx = self._cells()
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
            params=params,
            error=error,
            metadata=meta,
        )

    def execute(self, affordance: str, params: dict[str, Any]) -> ModulatorResult:
        """Parse, then apply. A refused result carries no params, so it never echoes a non-finite value back."""
        try:
            action = parse_action(affordance, params, self._world.limits)
        except ActionRefused as exc:
            return self._result(str(affordance), {}, False, str(exc))
        return self.apply(action)

    def apply(self, action: Action) -> ModulatorResult:
        """Apply a typed action: it is re-checked against this world's limits, then against the world as it is now."""
        affordance = _AFFORDANCE_OF[type(action)]
        shown = {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(action).items()}
        try:
            action.check(self._world.limits)
        except ActionRefused as exc:
            return self._result(affordance, shown, False, str(exc))
        cells = self._cells()
        if cells.size == 0:
            return self._result(affordance, shown, False, f"the {self._region} is gone")
        if isinstance(action, Strike):
            point = action.point_m if action.point_m is not None else self.centroid_m()
            dx = self._world.grid.dx
            lo, hi = cells.min(axis=0) * dx - action.sigma_m, (cells.max(axis=0) + 1) * dx + action.sigma_m
            if not all(a <= p <= b for a, p, b in zip(lo, point, hi, strict=True)):
                return self._result(affordance, shown, False, f"point_m is not on the {self._region}")
            res = damage.strike(self._world.grid, point, action.energy_j, action.sigma_m)
            return self._result(
                affordance, shown, True, destroyed_volume_m3=res.destroyed_volume_m3, absorbed_j=res.absorbed_j
            )
        if isinstance(action, Ignite):
            self._world.sources[f"fire:{self._region}"] = HeatSource(self.centroid_m(), action.radius_m, action.power_w)
            return self._result(affordance, shown, True)
        had = self._world.sources.pop(f"fire:{self._region}", None) is not None
        return self._result(affordance, shown, had, None if had else f"nothing is burning on the {self._region}")


_AFFORDANCE_OF: dict[type, str] = {Strike: "strike", Ignite: "ignite", Extinguish: "extinguish"}


def region_parts(world: World, region: str) -> tuple[dict[str, RegionSensor], dict[str, StructureModulator]]:
    sensors = {q: RegionSensor(world, region, q) for q in RegionSensor._UNITS}
    return sensors, {"structure": StructureModulator(world, region)}


def to_maxim_entity(world: World, region: str, entity_type: str = "structure") -> Entity:
    """A real Maxim Entity for one region. Requires pymaxim."""
    if not HAVE_MAXIM:
        raise RuntimeError("pymaxim is not installed: pip install 'maxim-overdrive[maxim]'")
    sensors, modulators = region_parts(world, region)
    return Entity(
        region,
        entity_type,
        sensors=sensors,  # type: ignore[arg-type]
        modulators=modulators,  # type: ignore[arg-type]
        metadata={"source": "maxim_overdrive.sem_env", "cell_size_m": world.grid.dx},
    )
