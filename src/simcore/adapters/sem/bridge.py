"""SEM for the environment: a wall, a door or a crate is an SEM Entity, the gate in front of the intent applier.

The environment is not embodied (it has no drives, pain or learning), but it speaks the same Sensor / Modulator
vocabulary as a body, so a Maxim agent perceives and acts on a wall exactly as it does on its own arm:

    instruments integrity (mean over the region's cells), temperature_max, temperature_mean, breached
    modulators  structure.strike(energy_j, sigma_m, point_m), structure.ignite(power_w, radius_m),
                structure.extinguish()

This module is the membrane's gate half (boundaries §2.2, §6.4). It reads the world only through published frames
(``simcore.core.frames``, B-13) and changes it only through the applier (``simcore.core.applier``); the import
contracts in ``pyproject.toml`` hold it to that. With pymaxim installed, ``to_maxim_entity`` returns a real
``maxim.embodiment.sem.Entity``, and Maxim's own tool generation, gating and prompt formatting work on it unchanged.
Without pymaxim, the same classes run on local stand-ins with the same fields.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from simcore.core.applier import Applier, Outcome
from simcore.core.checks import entity_key, shown
from simcore.core.frames import QUANTITIES, FrameSource
from simcore.core.intents import AFFORDANCE_OF, ActionRefused, parse_action
from simcore.core.refusals import RefusalCode, Refused, agent_text

if TYPE_CHECKING:
    # Type-check against Maxim's own classes; tests/test_sem_compat.py holds the _compat mirror to the same fields.
    from maxim.embodiment.sem import AffordanceSchema, Entity, ModulatorResult, SensorReading

    HAVE_MAXIM: bool
else:
    try:  # Maxim's frozen SEM types, when available.
        from maxim.embodiment.sem import AffordanceSchema, Entity, ModulatorResult, SensorReading

        HAVE_MAXIM = True
    except ImportError:  # exercised by tests/test_sem_compat.py, which blocks the maxim import
        from simcore.adapters.sem._compat import AffordanceSchema, ModulatorResult, SensorReading

        Entity = None
        HAVE_MAXIM = False


# Where an Entity came from, as a fixed vocabulary value on the wire, never a module path (boundaries §11.2, W10).
ENTITY_SOURCE = "overdrive_world"


class RegionInstrument:
    """A lab and test instrument: one quantity over one region, read from the latest published frame.

    It is not a percept. An NPC senses through physical channels at its own position and receptor (boundaries §4.4,
    B-13), which arrive with the first NPC body; reading a whole region's mean from anywhere is an ANALOG divergence
    from that, kept for tests and the lab, never an NPC's input. It holds a frame feed, never the world.
    """

    def __init__(self, frames: FrameSource, region: str, quantity: str) -> None:
        if not isinstance(quantity, str) or quantity not in QUANTITIES:
            raise Refused(f"unknown region quantity {shown(quantity)}", code=RefusalCode.UNKNOWN_KIND)
        if not isinstance(region, str) or region not in frames.latest.region_names:
            raise Refused(f"no region {shown(region)} in this world", code=RefusalCode.NO_REGION)
        self._frames, self._region, self._quantity = frames, region, quantity

    @property
    def name(self) -> str:
        return self._quantity

    @property
    def unit(self) -> str:
        return QUANTITIES[self._quantity]

    @property
    def reading_schema(self) -> dict[str, Any]:
        if self._quantity in ("integrity", "breached"):
            return {"type": "float", "range": [0.0, 1.0]}
        return {"type": "float", "range": [-273.0, 6000.0]}

    def value(self) -> float:
        return self._frames.latest.reading(self._region, self._quantity)

    def read(self) -> SensorReading:
        frame = self._frames.latest
        # No cell size: the grid spacing is the simulation's, not something an observer can sense (BF-N4, §4.4).
        return SensorReading(
            sensor_name=self.name,
            entity_name=self._region,
            value=frame.reading(self._region, self._quantity),
            unit=self.unit,
            timestamp=frame.time_s,
            extra={},
        )


# Keys Maxim adds to a call itself (simcore.core.intents.CALL_KEYS). Maxim's orchestrator-actor tool
# (maxim/simulation/tools.py, OrchestratorActorTool) passes target=<Entity>: what the actor acts ON (it defaults to the
# player). A region's structure is only ever acted on directly, so a target is accepted only when it is absent or is
# this region; any other target is refused, never dropped, because dropping it would strike the crate when the call
# meant the wall.


# What a refused target means, stated where the agent reads the affordance (step 3b(b) review, Bio-faithful S1).
_TARGET_RULE = "The target, if given, is this structure itself, by its name; never the caller or another thing."


class StructureModulator:
    """What can be done *to* a region: the gate in front of the applier. Time passes only in ``World.advance``.

    This is a trust boundary: an NPC's tool call, an LLM's output and a client's intent will all arrive here.
    ``execute`` parses (stage 1), judges the call's target, then hands the typed action to the applier (stage 2); a
    refusal at any stage is a failed result and changes nothing.
    """

    name = "structure"

    def __init__(self, applier: Applier, frames: FrameSource, region: str) -> None:
        frame = frames.latest
        if not isinstance(region, str) or region not in frame.region_names:
            raise Refused(f"no region {shown(region)} in this world", code=RefusalCode.NO_REGION)
        if not frame.is_solid(region):
            raise Refused(f"region {shown(region)} is air: there is no structure to act on", code=RefusalCode.NOT_SOLID)
        self._applier, self._region = applier, region

    @property
    def affordances(self) -> dict[str, AffordanceSchema]:
        lim = self._applier.limits
        return {
            "strike": AffordanceSchema(
                params={"energy_j": float, "sigma_m": (float, lim.default_sigma_m), "point_m": (list, None)},
                description=(
                    "Deliver mechanical energy to this structure (a blow, a bullet, a blast): energy_j up to "
                    f"{lim.max_energy_j:g} J, spread over sigma_m from {lim.min_sigma_m:g} to {lim.max_sigma_m:g} m, "
                    f"at point_m on the structure (its middle if omitted). {_TARGET_RULE}"
                ),
            ),
            "ignite": AffordanceSchema(
                params={"power_w": float, "radius_m": (float, lim.default_radius_m)},
                description=(
                    "Start a fire at this structure's surface; it burns until extinguished. power_w up to "
                    f"{lim.max_power_w:g} W, radius_m from {lim.min_radius_m:g} to {lim.max_radius_m:g} m. "
                    f"{_TARGET_RULE}"
                ),
            ),
            "extinguish": AffordanceSchema(description=f"Put out a fire started on this structure. {_TARGET_RULE}"),
        }

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
        """Parse, judge the target, then apply. A refused result carries no params, so it never echoes a non-finite
        value back."""
        # The affordance is echoed only when it is one of ours: a made-up one is "unknown", never its own text.
        label = affordance if isinstance(affordance, str) and affordance in AFFORDANCE_OF.values() else "unknown"
        try:
            action = parse_action(affordance, params, self._applier.limits)
        except ActionRefused as exc:  # the agent is told the code, never the words (boundaries §5.4)
            return self._result(label, {}, False, exc.agent_text)
        target = params.get("target") if isinstance(params, Mapping) else None
        # Told apart for the agent, in the closed vocabulary with no name echoed: another thing of this name (an item,
        # an NPC called "crate") is a namesake, and "name the crate" would loop it; anything else is the wrong target.
        if self._is_namesake(target):
            return self._result(label, {}, False, RefusalCode.NAMESAKE.value)
        if target is not None and not self._is_this_region(target):
            # The key names the fix, which the affordance's description states (_TARGET_RULE). On Maxim's
            # orchestrator path, OrchestratorActorTool defaults target to the agent under test's body (an Entity);
            # a structure declares no direction for it (OD-C3, OD-A16). On an NPC's per-entity tool, target is
            # undefaulted, so this arises only when the model adds one (step 3b(b) review, Bio S1; delta D4).
            return self._result(label, {}, False, agent_text(RefusalCode.WRONG_TARGET, "target"))
        # TEMPORARY(phase1/agents): execute applies synchronously and logs nothing (boundaries §6.4). In phase1/agents
        # it only parses, checks the bound actor and appends the intent to the stepping agent's outbox, returning a
        # pending, neutral result; the host's step applies it.
        return self._from(self._applier.apply(self._region, action))

    def _from(self, outcome: Outcome) -> ModulatorResult:
        return self._result(
            outcome.affordance, dict(outcome.params), outcome.success, outcome.agent_text, **outcome.metadata
        )

    def _is_namesake(self, target: object) -> bool:
        """A Maxim Entity that shares this region's name but isn't it (an item or an NPC called "crate")."""
        if not (HAVE_MAXIM and isinstance(target, Entity)) or self._is_this_region(target):
            return False
        return type(target.name) is str and entity_key(target.name) == entity_key(self._region)

    def _is_this_region(self, target: object) -> bool:
        """Whether a call's target is this region.

        A Maxim Entity is this region only if it carries this very modulator: names are unique among regions, but an
        item or an NPC elsewhere could share one. A string names this region when it resolves to it under Maxim's own
        name rule (``checks.entity_key``), under which region names are unique.
        """
        if HAVE_MAXIM and isinstance(target, Entity):
            return target.modulators.get("structure") is self
        return type(target) is str and entity_key(target) == entity_key(self._region)


def region_parts(
    applier: Applier, frames: FrameSource, region: str
) -> tuple[dict[str, RegionInstrument], dict[str, StructureModulator]]:
    """One region's instruments and modulators, built from the two capabilities the membrane is given: an applier to
    change the world and a frame view to read it. It never receives the world (step 3b review, Architecture S1)."""
    sensors = {q: RegionInstrument(frames, region, q) for q in QUANTITIES}
    # An air region (a room, a doorway) is sensed, but it has no structure: nothing to strike or set alight.
    solid = frames.latest.is_solid(region)
    modulators = {"structure": StructureModulator(applier, frames, region)} if solid else {}
    return sensors, modulators


def to_maxim_entity(applier: Applier, frames: FrameSource, region: str, entity_type: str = "structure") -> Entity:
    """A real Maxim Entity for one region, from the membrane's two capabilities. Requires pymaxim."""
    if not HAVE_MAXIM:
        raise RuntimeError("pymaxim is not installed: pip install 'maxim-overdrive[maxim]'")
    sensors, modulators = region_parts(applier, frames, region)
    return Entity(
        region,
        entity_type,
        sensors=sensors,  # type: ignore[arg-type]
        modulators=modulators,  # type: ignore[arg-type]
        metadata={"source": ENTITY_SOURCE},  # no cell size: it is the simulation's, not the world's (BF-N4)
    )
