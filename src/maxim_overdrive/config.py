"""Rig profiles, the material table and action limits: the data every world and every action is checked against."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from maxim_overdrive.checks import finite_real, known_keys, whole_number


def data_dir() -> Path:
    """Bundled data: inside the wheel when installed, the repo's ``data/`` in a checkout."""
    here = Path(__file__).resolve().parent
    installed = here / "_data"
    return installed if installed.is_dir() else here.parents[1] / "data"


@dataclass(frozen=True)
class RigProfile:
    """How much resolution this machine can afford.

    A profile may change precision only. The same scene at two profiles must agree on every gameplay outcome
    (did the wall breach, did the room get hot enough to burn); tests/test_cross_tier.py enforces it.
    """

    name: str
    cell_size_m: float
    min_substeps_per_turn: int
    full_res_radius_m: float

    def __post_init__(self) -> None:
        if not self.cell_size_m > 0:
            raise ValueError(f"cell_size_m must be positive, got {self.cell_size_m}")
        if self.min_substeps_per_turn < 1:
            raise ValueError("min_substeps_per_turn must be at least 1")

    @classmethod
    def load(cls, name_or_path: str | Path) -> RigProfile:
        path = Path(name_or_path)
        if not path.suffix:
            path = data_dir() / "rigs" / f"{name_or_path}.yaml"
        raw = known_keys(read_yaml(path), f"rig profile {path}", required=RIG_KEYS)
        if not isinstance(raw["name"], str):
            raise ValueError(f"rig profile {path}: name must be a string, got {raw['name']!r}")
        return cls(
            name=raw["name"],
            cell_size_m=finite_real(raw["cell_size_m"], "cell_size_m"),
            min_substeps_per_turn=whole_number(raw["min_substeps_per_turn"], "min_substeps_per_turn"),
            full_res_radius_m=finite_real(raw["full_res_radius_m"], "full_res_radius_m"),
        )


RIG_KEYS = frozenset({"name", "cell_size_m", "min_substeps_per_turn", "full_res_radius_m"})


@dataclass(frozen=True)
class Material:
    name: str
    id: int
    density_kg_m3: float
    specific_heat_j_kgk: float
    conductivity_w_mk: float
    fracture_energy_j_m3: float
    degrade_above_c: float | None
    degrade_rate_per_s_per_100c: float
    color_rgb: tuple[int, int, int]

    @property
    def diffusivity_m2_s(self) -> float:
        return self.conductivity_w_mk / (self.density_kg_m3 * self.specific_heat_j_kgk)

    @property
    def volumetric_heat_capacity(self) -> float:
        """J / (m^3 K)."""
        return self.density_kg_m3 * self.specific_heat_j_kgk


def _colour(value: object, what: str) -> tuple[int, int, int]:
    """Three whole numbers, or a ValueError that names the field (a scalar or a string is refused, not iterated)."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 3:
        raise ValueError(f"{what} must be three whole numbers, got {value!r}")
    return (whole_number(value[0], what), whole_number(value[1], what), whole_number(value[2], what))


AIR_ID = 0
# Declared beside the reader, not derived from Material: a field added to the dataclass and forgotten here must not
# become a key the file may carry and the reader ignores. A test holds the two sets to the dataclass.
MATERIAL_REQUIRED = frozenset(
    {"id", "density_kg_m3", "specific_heat_j_kgk", "conductivity_w_mk", "fracture_energy_j_m3", "color_rgb"}
)
MATERIAL_OPTIONAL = frozenset({"degrade_above_c", "degrade_rate_per_s_per_100c"})


class MaterialTable:
    """Materials by name and by id, plus per-id property lookup arrays for vectorized physics."""

    def __init__(self, materials: dict[str, Material]) -> None:
        ids = [m.id for m in materials.values()]
        if len(set(ids)) != len(ids):
            raise ValueError("material ids must be unique")
        if AIR_ID not in ids or materials.get("air") is None or materials["air"].id != AIR_ID:
            raise ValueError("the table must define 'air' with id 0")
        if min(ids) < 0 or max(ids) > 255:  # a negative id would index the property arrays from the end
            raise ValueError("material ids must fit in uint8 (0 to 255)")
        for m in materials.values():
            if len(m.color_rgb) != 3 or not all(0 <= c <= 255 for c in m.color_rgb):
                raise ValueError(f"{m.name}.color_rgb must be three values from 0 to 255, got {m.color_rgb!r}")
        self.by_name = dict(materials)
        self.by_id = {m.id: m for m in materials.values()}
        n = max(ids) + 1
        self.rho_cp = np.ones(n, dtype=np.float64)
        self.conductivity = np.zeros(n, dtype=np.float64)
        self.fracture = np.zeros(n, dtype=np.float64)
        self.degrade_above = np.full(n, np.inf, dtype=np.float64)
        self.degrade_rate = np.zeros(n, dtype=np.float64)
        for m in materials.values():
            self.rho_cp[m.id] = m.volumetric_heat_capacity
            self.conductivity[m.id] = m.conductivity_w_mk
            self.fracture[m.id] = m.fracture_energy_j_m3
            if m.degrade_above_c is not None:
                self.degrade_above[m.id] = m.degrade_above_c
            self.degrade_rate[m.id] = m.degrade_rate_per_s_per_100c

    def __getitem__(self, name: str) -> Material:
        return self.by_name[name]

    def __contains__(self, name: object) -> bool:
        return name in self.by_name

    @classmethod
    def load(cls, path: str | Path | None = None) -> MaterialTable:
        path = Path(path) if path is not None else data_dir() / "materials" / "core.yaml"
        raw = known_keys(read_yaml(path), "material table", required={"materials"})["materials"]
        if not isinstance(raw, Mapping):
            raise ValueError(f"materials must be a mapping, got {type(raw).__name__}")
        mats = {}
        for name, entry in raw.items():
            if not isinstance(name, str):
                raise ValueError(f"material names must be strings, got {name!r}")
            v = known_keys(entry, f"material {name}", required=MATERIAL_REQUIRED, optional=MATERIAL_OPTIONAL)
            mats[name] = Material(
                name=name,
                id=whole_number(v["id"], f"{name}.id"),
                density_kg_m3=finite_real(v["density_kg_m3"], f"{name}.density_kg_m3"),
                specific_heat_j_kgk=finite_real(v["specific_heat_j_kgk"], f"{name}.specific_heat_j_kgk"),
                conductivity_w_mk=finite_real(v["conductivity_w_mk"], f"{name}.conductivity_w_mk"),
                fracture_energy_j_m3=finite_real(v["fracture_energy_j_m3"], f"{name}.fracture_energy_j_m3"),
                degrade_above_c=None
                if v.get("degrade_above_c") is None
                else finite_real(v["degrade_above_c"], f"{name}.degrade_above_c"),
                degrade_rate_per_s_per_100c=finite_real(
                    v.get("degrade_rate_per_s_per_100c", 0.0), f"{name}.degrade_rate_per_s_per_100c"
                ),
                color_rgb=_colour(v["color_rgb"], f"{name}.color_rgb"),
            )
        return cls(mats)


ACTION_LIMITS_VERSION = 0
_LIMIT_FIELDS = {
    "ignite": ("max_power_w", "min_radius_m", "max_radius_m", "default_radius_m"),
    "strike": ("max_energy_j", "min_sigma_m", "max_sigma_m", "default_sigma_m"),
}


class _StrictLoader(yaml.SafeLoader):
    """``yaml.SafeLoader`` that refuses a mapping with a repeated key instead of keeping the last value."""


def _no_duplicate_keys(loader: _StrictLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    # Repeats are judged among the keys written in this mapping; a key that overrides one merged in from <<: is the
    # point of a merge, not a repeat.
    written = [loader.construct_object(k, deep=True) for k, _ in node.value if k.tag != "tag:yaml.org,2002:merge"]
    for key in written:
        if not isinstance(key, (str, int, float, bool)) and key is not None:
            raise ValueError(f"a mapping key must be a plain value, got {type(key).__name__}")
    repeated = sorted({str(k) for k, n in Counter(written).items() if n > 1})
    if repeated:
        raise ValueError(f"repeated key(s) {repeated} in a mapping")
    loader.flatten_mapping(node)  # resolve merge keys (<<:) as SafeLoader does; the written keys come last and win
    return dict(loader.construct_pairs(node, deep=True))


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def read_yaml(path: Path) -> object:
    """A data file parsed strictly: invalid YAML and repeated keys are refused, with the file named.

    Every data loader reads through here, so none of them can keep the last of two values for one key.
    """
    try:
        return yaml.load(path.read_text(), Loader=_StrictLoader)  # a SafeLoader subclass
    except yaml.YAMLError as exc:  # reported, with the file, as the refusal
        raise ValueError(f"{path}: not valid YAML: {exc}") from None
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from None


@dataclass(frozen=True)
class ActionLimits:
    """How much one SEM action may ask of the world (``data/world/actions.yaml``).

    These are physics-safety ceilings, not what a body can do: an NPC's capability will come from its body and its
    energy (Phase 4 and 5). They are world config, not server config, because the simulation enforces them and a
    replay needs the same values. The minimum radius and width are at least the coarsest rig's cell, so no action
    lands in a single cell at one rig and spreads at another. They don't make fires or near-threshold strikes agree
    across rigs: both diverge today (docs/architecture.md, Known gaps, each held by a strict red gate).
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

    @classmethod
    def load(cls, path: str | Path | None = None) -> ActionLimits:
        path = Path(path) if path is not None else data_dir() / "world" / "actions.yaml"
        raw = read_yaml(path)
        version = raw.get("version") if isinstance(raw, dict) else raw
        if type(version) is not int or version != ACTION_LIMITS_VERSION:  # True and 0.0 are not version 0
            raise ValueError(f"{path}: action limits version must be {ACTION_LIMITS_VERSION}, got {version!r}")
        top = known_keys(raw, f"{path}", required={"version", *_LIMIT_FIELDS})
        values: dict[str, Any] = {}
        for section, names in _LIMIT_FIELDS.items():
            values.update(known_keys(top[section], f"{path}: {section}", required=names))
        return cls(**values)
