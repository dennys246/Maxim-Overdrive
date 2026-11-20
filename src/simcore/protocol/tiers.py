"""Rendering tiers: how much of the world a machine's client draws, and at what detail (world_model D20).

A tier never reaches the physics. Every machine simulates one truth, at one grid spacing, so nothing here decides a
cell size or a step count: the core is forbidden from importing this module (``pyproject.toml``, import-linter).
Rig format v0 carried physics (``cell_size_m``, ``min_substeps_per_turn``) and is refused by version, not migrated:
under D20 it is a dead format.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from simcore.adapters.loaders import read_yaml
from simcore.core.checks import finite_real, format_version, known_keys

RIG_PROFILE_VERSION = 1
RIG_KEYS = frozenset({"version", "name", "detail_radius_m"})


@dataclass(frozen=True)
class RigProfile:
    """A rendering tier: a name and how far from the camera the client draws at full detail.

    ``detail_radius_m`` is reserved: no client reads it yet. It replaces v0's ``full_res_radius_m``, which proposed
    running far cells coarser; under D21 resolution follows the world, never the machine.
    """

    name: str
    detail_radius_m: float

    @classmethod
    def load(cls, path: str | Path) -> RigProfile:
        path = Path(path)
        what = f"rig profile {path}"
        raw = known_keys(format_version(read_yaml(path), RIG_PROFILE_VERSION, what), what, required=RIG_KEYS)
        if not isinstance(raw["name"], str):
            raise ValueError(f"rig profile {path}: name must be a string, got {raw['name']!r}")
        return cls(name=raw["name"], detail_radius_m=finite_real(raw["detail_radius_m"], "detail_radius_m"))
