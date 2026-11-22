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

from simcore.core.checks import finite_real, finite_vector, identity_key, shown, whole_number
from simcore.core.limits import ActionLimits
from simcore.core.refusals import RefusalCode, Refused


class ActionRefused(Refused):
    """An action broke a rule. Its code (and the schema field, when one is at fault) is what an agent is told; the
    message, in words, is for logs and tests. The world is unchanged."""


# Keys a caller adds to a call itself, which parsing passes over: Maxim's orchestrator-actor tool passes
# target=<Entity> (what the actor acts ON). The membrane judges it (simcore.adapters.sem.bridge); parsing only lets it
# through, so it is never mistaken for an unknown parameter.
CALL_KEYS = frozenset({"target"})


def _within(name: str, value: float, lo: float, hi: float) -> None:
    if not lo <= value <= hi:
        message = f"{name} must be between {lo:g} and {hi:g}, got {value:g}"
        raise ActionRefused(message, code=RefusalCode.OUT_OF_RANGE, field=name)


def _typed(action: object, values: Mapping[str, object]) -> None:
    """A hand-built action's numbers become finite floats, or the action is refused: it never reaches the physics."""
    for name, value in values.items():
        try:
            object.__setattr__(action, name, finite_real(value, name))
        except ValueError:
            message = f"{name} must be a finite number, got {shown(value)}"
            raise ActionRefused(message, code=RefusalCode.NOT_FINITE, field=name) from None


@dataclass(frozen=True)
class Strike:
    energy_j: float
    sigma_m: float
    point_m: tuple[float, float, float] | None  # None: the region's centroid, found when the action applies

    def __post_init__(self) -> None:
        _typed(self, {"energy_j": self.energy_j, "sigma_m": self.sigma_m})
        if self.point_m is not None:
            try:
                x, y, z = finite_vector(self.point_m, 3, "point_m")
            except Refused as exc:  # its own code: a NaN is not_finite here as in every reader, a pair is bad_shape
                message = f"point_m must be 3 finite numbers, got {shown(self.point_m)}"
                raise ActionRefused(message, code=exc.code, field="point_m") from None
            object.__setattr__(self, "point_m", (x, y, z))

    def check(self, limits: ActionLimits) -> None:
        _within("energy_j", self.energy_j, 0.0, limits.max_energy_j)
        _within("sigma_m", self.sigma_m, limits.min_sigma_m, limits.max_sigma_m)


@dataclass(frozen=True)
class Ignite:
    power_w: float
    radius_m: float

    def __post_init__(self) -> None:
        _typed(self, {"power_w": self.power_w, "radius_m": self.radius_m})

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
            raise ActionRefused(f"{name} is required", code=RefusalCode.MISSING_FIELD, field=name)
        return default
    try:
        return finite_real(params[name], name)
    except ValueError:  # reported, with the parameter's name, as the refusal
        message = f"{name} must be a finite number, got {shown(params[name])}"
        raise ActionRefused(message, code=RefusalCode.NOT_FINITE, field=name) from None


def parse_action(affordance: object, params: object, limits: ActionLimits) -> Action:
    """Untrusted (affordance, params) as a typed action inside ``limits``, or ActionRefused saying why.

    ``params`` is JSON-shaped: a mapping of names to numbers, lists or None, as an LLM's tool call or a client's
    intent gives it. Numbers must be real numbers; numeric strings such as "1000" are refused, deliberately, so a
    value is never guessed. It reads nothing from the world, so it can run wherever input arrives, before the
    world-dependent checks in ``simcore.core.applier``.
    """
    if not isinstance(params, Mapping):
        raise ActionRefused("params must be a mapping of names to values", code=RefusalCode.BAD_SHAPE)
    allowed = _ALLOWED_PARAMS.get(affordance) if isinstance(affordance, str) else None
    if allowed is None:
        raise ActionRefused(f"unknown affordance {shown(affordance)}", code=RefusalCode.UNKNOWN_KIND)
    unknown = sorted(shown(k) for k in params if k not in allowed and k not in CALL_KEYS)
    if unknown:
        message = f"unknown parameter(s) for {affordance}: {', '.join(unknown[:8])}"
        raise ActionRefused(message, code=RefusalCode.UNKNOWN_FIELD)
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


# -- the log record (boundaries.md §6.2, the record's and the ordering key's owner) ------------------------------------

# A record's kind for each typed action, in the log's v0 vocabulary (sim_core.md's 5a ruling: 5a's logs carry v0).
# `Extinguish` is the action the affordance calls "extinguish"; the log's word is "douse".
RECORD_KIND_OF: Mapping[type, str] = MappingProxyType({Ignite: "ignite", Strike: "strike", Extinguish: "douse"})

# kind_rank, closed: boundaries.md §6.2 owns the values. Only the kinds a record can carry today are listed; a kind
# joins with its payload type (moves at 20 with 5b, controls and host commands with the log), so a new kind can never
# take a rank nobody wrote.
KIND_RANK: Mapping[str, int] = MappingProxyType({"ignite": 30, "strike": 30, "douse": 30})

_U32 = 2**32
_I64 = 2**63


def _bounded(value: object, what: str, below: int, *, minimum: int = 0) -> int:
    n = whole_number(value, what)
    if not minimum <= n < below:
        raise Refused(f"{what} must be from {minimum} to {below - 1}, got {n}", code=RefusalCode.OUT_OF_RANGE)
    return n


@dataclass(frozen=True)
class LogRecord:
    """One input record, with boundaries.md §6.2's field names and its ordering key.

    5a's first PR carries world actions only: ``params`` is the typed action, ``target`` the region it acts on. The
    rest of §6.2's record (schema_version, the observed and issued ticks, the audit payload) and the log's file format
    join in step 5a's PR 4b, as fields with their own payload kinds, so this type widens rather than renames."""

    apply_tick: int
    apply_us: int
    actor_id: int
    seq: int
    kind: str
    target: str
    params: Action

    def __post_init__(self) -> None:
        # Each is stored back as a plain int, so a numpy integer can't reach the key (it must serialise; PR 4b's log).
        object.__setattr__(
            self, "apply_tick", _bounded(self.apply_tick, "apply_tick", _I64, minimum=1)
        )  # tick 0 is construction (sim_core.md §3)
        object.__setattr__(
            self, "apply_us", _bounded(self.apply_us, "apply_us", _I64)
        )  # a step also holds it below its tick's length
        object.__setattr__(
            self, "actor_id", _bounded(self.actor_id, "actor_id", _U32)
        )  # ordering keys are integers (§6.2, D-N2)
        object.__setattr__(self, "seq", _bounded(self.seq, "seq", _U32))
        identity_key(self.target, "target")
        if not isinstance(self.kind, str) or self.kind not in KIND_RANK:
            raise Refused(f"unknown record kind {shown(self.kind)}", code=RefusalCode.UNKNOWN_KIND)
        if RECORD_KIND_OF.get(type(self.params)) != self.kind:
            raise Refused(f"a {self.kind} record's params must be its typed action", code=RefusalCode.BAD_SHAPE)

    @property
    def kind_rank(self) -> int:
        return KIND_RANK[self.kind]

    @property
    def key(self) -> tuple[int, int, int, int, int]:
        """The log's one ordering key (boundaries.md §6.2): (apply_tick, kind_rank, apply_us, actor_id, seq)."""
        return (self.apply_tick, self.kind_rank, self.apply_us, self.actor_id, self.seq)
