"""Rendering tiers: how much of the world a machine's client draws, and at what detail (world_model D20).

A tier never reaches the physics. Every machine simulates one truth, at one grid spacing, so nothing here decides a
cell size or a step count: the core is forbidden from importing this module (``pyproject.toml``, import-linter).
Rig format v0 carried physics (``cell_size_m``, ``min_substeps_per_turn``) and is refused by version, not migrated:
under D20 it is a dead format. v1 holds a name only; the first detail setting arrives with the client code that reads
it, as v2.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from simcore.adapters.loaders import FilePath, read_yaml
from simcore.core.checks import format_version, known_keys, shown

RIG_PROFILE_VERSION = 1
RIG_KEYS = frozenset({"version", "name"})
_V0_MOVED = (
    "rig format v0 carried physics (cell_size_m, min_substeps_per_turn), which left the rig (world_model D20): the "
    "grid spacing is now World.from_scene's dx_m, and the substep floor follows from it"
)


@dataclass(frozen=True)
class RigProfile:
    """A rendering tier, by name. It carries no physics, and no setting yet that a client reads."""

    name: str

    def __post_init__(self) -> None:
        # Validating constructor (boundaries §5.1): holding a RigProfile is proof its name is usable.
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(f"a rig profile needs a name, got {shown(self.name)}")

    @classmethod
    def load(cls, path: FilePath) -> RigProfile:
        """The rig profile in the file at ``path``. The gate (``loaders.read_yaml``) reads it; this only decodes."""
        what = f"rig profile {path}"
        raw = read_yaml(path)
        if isinstance(raw, Mapping) and type(raw.get("version")) is int and raw["version"] == 0:
            raise ValueError(f"{what} version must be {RIG_PROFILE_VERSION}, got 0: {_V0_MOVED}")
        raw = known_keys(format_version(raw, RIG_PROFILE_VERSION, what), what, required=RIG_KEYS)
        try:
            return cls(name=raw["name"])  # type: ignore[arg-type]  # the constructor checks it
        except ValueError as exc:
            raise ValueError(f"{what}: {exc}") from None
