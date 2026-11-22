"""Action limits: how much one action may ask of the world. The type and its format; ``simcore.adapters.loaders``
reads the file."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType

from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import Field, Format, Nested, Real, Schema

_POSITIVE = Real(lo=0.0, lo_open=True)
# The file groups the limits by the action they bound; ActionLimits holds them flat.
SECTIONS: Mapping[str, Schema] = MappingProxyType({
    "ignite": Schema(
        tuple(Field(n, _POSITIVE) for n in ("max_power_w", "min_radius_m", "max_radius_m", "default_radius_m"))
    ),
    "strike": Schema(
        tuple(Field(n, _POSITIVE) for n in ("max_energy_j", "min_sigma_m", "max_sigma_m", "default_sigma_m"))
    ),
})  # fmt: skip
_FLAT = Schema(tuple(f for section in SECTIONS.values() for f in section.fields))
ACTION_LIMITS = Format("action limits", 0, Schema(tuple(Field(n, Nested(s)) for n, s in SECTIONS.items())))


@dataclass(frozen=True)
class ActionLimits:
    """How much one SEM action may ask of the world (``data/world/actions.yaml``).

    These are physics-safety ceilings, not what a body can do: an NPC's capability will come from its body and its
    energy (Phase 4 and 5). They are world config, not server config, because the simulation enforces them and a
    replay needs the same values, which makes them engine mechanism (boundaries §8.2). The minimum radius and width
    are at least the coarsest verification grid's cell (0.2 m), so no action lands in a single cell at one spacing and
    spreads at another. They don't make fires or near-threshold strikes agree across spacings: both diverge today
    (docs/architecture.md, Known gaps, each held by a strict red gate).
    """

    max_power_w: float
    min_radius_m: float
    max_radius_m: float
    default_radius_m: float
    max_energy_j: float
    min_sigma_m: float
    max_sigma_m: float
    default_sigma_m: float

    def __post_init__(self) -> None:
        for name, value in _FLAT.check(asdict(self), "action limit").items():
            object.__setattr__(self, name, value)
        if not self.min_radius_m <= self.default_radius_m <= self.max_radius_m:
            raise Refused(
                "ignite's default_radius_m must lie between its minimum and maximum",
                code=RefusalCode.OUT_OF_RANGE,
                field="default_radius_m",
            )
        if not self.min_sigma_m <= self.default_sigma_m <= self.max_sigma_m:
            raise Refused(
                "strike's default_sigma_m must lie between its minimum and maximum",
                code=RefusalCode.OUT_OF_RANGE,
                field="default_sigma_m",
            )

    @classmethod
    def from_document(cls, doc: Mapping[str, object]) -> ActionLimits:
        """The limits from a document ``ACTION_LIMITS`` has read, its sections flattened."""
        flat: dict[str, float] = {}
        for section in SECTIONS:
            flat.update(doc[section])  # type: ignore[call-overload]  # each section is a Nested read
        return cls(**flat)
