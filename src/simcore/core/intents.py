"""The action vocabulary: typed actions and stage-1 parsing (boundaries §2.2 ``intents``, §5.3).

Stage 1 is typed parsing with no world: shape, finiteness and ceilings, so it can run wherever input arrives (an NPC's
tool call through the SEM membrane today, a client's intent at the protocol layer later). Stage 2, the world check at
apply (the region exists, the point is on it, something is burning), is the applier's (``simcore.core.applier``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from simcore.core.checks import finite_real, finite_vector, shown
from simcore.core.limits import ActionLimits


class ActionRefused(ValueError):
    """An action broke a rule; the message says which, in words fit for whoever asked. The world is unchanged."""


# Keys a caller adds to a call itself, which parsing passes over: Maxim's orchestrator-actor tool passes
# target=<Entity> (what the actor acts ON). The membrane judges it (simcore.adapters.sem.bridge); parsing only lets it
# through, so it is never mistaken for an unknown parameter.
CALL_KEYS = frozenset({"target"})


def _within(name: str, value: float, lo: float, hi: float) -> None:
    if not lo <= value <= hi:
        raise ActionRefused(f"{name} must be between {lo:g} and {hi:g}, got {value:g}")


def _typed(action: object, *names: str) -> None:
    """A hand-built action's numbers become finite floats, or the action is refused: it never reaches the physics."""
    for name in names:
        value = action.__dict__[name]
        try:
            object.__setattr__(action, name, finite_real(value, name))
        except ValueError:
            raise ActionRefused(f"{name} must be a finite number, got {shown(value)}") from None


@dataclass(frozen=True)
class Strike:
    energy_j: float
    sigma_m: float
    point_m: tuple[float, float, float] | None  # None: the region's centroid, found when the action applies

    def __post_init__(self) -> None:
        _typed(self, "energy_j", "sigma_m")
        if self.point_m is not None:
            try:
                x, y, z = finite_vector(self.point_m, 3, "point_m")
            except ValueError:
                raise ActionRefused(f"point_m must be 3 finite numbers, got {shown(self.point_m)}") from None
            object.__setattr__(self, "point_m", (x, y, z))

    def check(self, limits: ActionLimits) -> None:
        _within("energy_j", self.energy_j, 0.0, limits.max_energy_j)
        _within("sigma_m", self.sigma_m, limits.min_sigma_m, limits.max_sigma_m)


@dataclass(frozen=True)
class Ignite:
    power_w: float
    radius_m: float

    def __post_init__(self) -> None:
        _typed(self, "power_w", "radius_m")

    def check(self, limits: ActionLimits) -> None:
        _within("power_w", self.power_w, 0.0, limits.max_power_w)
        _within("radius_m", self.radius_m, limits.min_radius_m, limits.max_radius_m)


@dataclass(frozen=True)
class Extinguish:
    def check(self, limits: ActionLimits) -> None:
        pass


Action = Strike | Ignite | Extinguish

# Each action's affordance name, as Maxim's tool and a client's intent name it.
AFFORDANCE_OF: Mapping[type, str] = MappingProxyType({Strike: "strike", Ignite: "ignite", Extinguish: "extinguish"})

_ALLOWED_PARAMS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "strike": frozenset({"energy_j", "sigma_m", "point_m"}),
        "ignite": frozenset({"power_w", "radius_m"}),
        "extinguish": frozenset(),
    }
)


def _real(params: Mapping[str, Any], name: str, default: float | None = None) -> float:
    if name not in params or params[name] is None:
        if default is None:
            raise ActionRefused(f"{name} is required")
        return default
    try:
        return finite_real(params[name], name)
    except ValueError:  # reported, with the parameter's name, as the refusal
        raise ActionRefused(f"{name} must be a finite number, got {shown(params[name])}") from None


def parse_action(affordance: object, params: object, limits: ActionLimits) -> Action:
    """Untrusted (affordance, params) as a typed action inside ``limits``, or ActionRefused saying why.

    ``params`` is JSON-shaped: a mapping of names to numbers, lists or None, as an LLM's tool call or a client's
    intent gives it. Numbers must be real numbers; numeric strings such as "1000" are refused, deliberately, so a
    value is never guessed. It reads nothing from the world, so it can run wherever input arrives, before the
    world-dependent checks in ``simcore.core.applier``.
    """
    if not isinstance(params, Mapping):
        raise ActionRefused("params must be a mapping of names to values")
    allowed = _ALLOWED_PARAMS.get(affordance) if isinstance(affordance, str) else None
    if allowed is None:
        raise ActionRefused(f"unknown affordance {shown(affordance)}")
    unknown = sorted(shown(k) for k in params if k not in allowed and k not in CALL_KEYS)
    if unknown:
        raise ActionRefused(f"unknown parameter(s) for {affordance}: {', '.join(unknown[:8])}")
    action: Action
    if affordance == "strike":
        action = Strike(
            _real(params, "energy_j"), _real(params, "sigma_m", limits.default_sigma_m), params.get("point_m")
        )
    elif affordance == "ignite":
        action = Ignite(_real(params, "power_w"), _real(params, "radius_m", limits.default_radius_m))
    else:
        action = Extinguish()
    action.check(limits)
    return action
