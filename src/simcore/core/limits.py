"""Action limits: how much one action may ask of the world. The type only; ``simcore.adapters.loaders`` reads it."""

from __future__ import annotations

from dataclasses import dataclass

from simcore.core.checks import finite_real


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
        for name, value in vars(self).items():
            number = finite_real(value, f"action limit {name}")
            if number <= 0:
                raise ValueError(f"action limit {name} must be positive, got {value!r}")
            object.__setattr__(self, name, number)
        if not self.min_radius_m <= self.default_radius_m <= self.max_radius_m:
            raise ValueError("ignite's default_radius_m must lie between its minimum and maximum")
        if not self.min_sigma_m <= self.default_sigma_m <= self.max_sigma_m:
            raise ValueError("strike's default_sigma_m must lie between its minimum and maximum")
