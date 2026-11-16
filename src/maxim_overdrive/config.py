"""Rig profiles, the material table and action limits: the data every world and every action is checked against."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from maxim_overdrive.checks import finite_real, whole_number


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
        raw = yaml.safe_load(path.read_text())
        return cls(
            name=str(raw["name"]),
            cell_size_m=finite_real(raw["cell_size_m"], "cell_size_m"),
            min_substeps_per_turn=whole_number(raw["min_substeps_per_turn"], "min_substeps_per_turn"),
            full_res_radius_m=finite_real(raw["full_res_radius_m"], "full_res_radius_m"),
        )


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


AIR_ID = 0


class MaterialTable:
    """Materials by name and by id, plus per-id property lookup arrays for vectorized physics."""

    def __init__(self, materials: dict[str, Material]) -> None:
        ids = [m.id for m in materials.values()]
        if len(set(ids)) != len(ids):
            raise ValueError("material ids must be unique")
        if AIR_ID not in ids or materials.get("air") is None or materials["air"].id != AIR_ID:
            raise ValueError("the table must define 'air' with id 0")
        if max(ids) > 255:
            raise ValueError("material ids must fit in uint8")
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
        raw: dict[str, Any] = yaml.safe_load(path.read_text())["materials"]
        mats = {}
        for name, v in raw.items():
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
                color_rgb=tuple(whole_number(c, f"{name}.color_rgb") for c in v["color_rgb"]),  # type: ignore[arg-type]
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
    loader.flatten_mapping(node)  # resolve YAML merge keys (<<:) first, as SafeLoader does
    keys = [loader.construct_object(k, deep=True) for k, _ in node.value]
    for key in keys:
        if not isinstance(key, (str, int, float, bool)) and key is not None:
            raise ValueError(f"a mapping key must be a plain value, got {type(key).__name__}")
    repeated = sorted({str(k) for k in keys if keys.count(k) > 1})
    if repeated:
        raise ValueError(f"repeated key(s) {repeated} in a mapping")
    return dict(loader.construct_pairs(node, deep=True))


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


@dataclass(frozen=True)
class ActionLimits:
    """How much one SEM action may ask of the world (``data/world/actions.yaml``).

    These are physics-safety ceilings, not what a body can do: an NPC's capability will come from its body and its
    energy (Phase 4 and 5). They are world config, not server config, because the simulation enforces them and a
    replay needs the same values. The minimum radius and width are at least the coarsest rig's cell. Within the
    limits, a strike has the same outcome class at every rig (none, small or crater, from its closed-form radius),
    and a fire the same outcome for its first 30 turns; past that the fuel gap makes fires diverge
    (``tests/test_act_validation.py`` holds all three, the last as a strict red gate).
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
        try:
            raw = yaml.load(path.read_text(), Loader=_StrictLoader)  # a SafeLoader subclass
        except yaml.YAMLError as exc:  # reported, with the file, as the refusal
            raise ValueError(f"{path}: not valid YAML: {exc}") from None
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from None
        version = raw.get("version") if isinstance(raw, dict) else raw
        if type(version) is not int or version != ACTION_LIMITS_VERSION:  # True and 0.0 are not version 0
            raise ValueError(f"{path}: action limits version must be {ACTION_LIMITS_VERSION}, got {version!r}")
        assert isinstance(raw, dict)
        if set(raw) != {"version", *_LIMIT_FIELDS}:
            raise ValueError(f"{path}: expected sections {sorted(_LIMIT_FIELDS)}, got {sorted(set(raw) - {'version'})}")
        values: dict[str, Any] = {}
        for section, names in _LIMIT_FIELDS.items():
            block = raw[section]
            if not isinstance(block, dict) or set(block) != set(names):
                raise ValueError(f"{path}: {section} must have exactly {list(names)}, got {block!r}")
            values.update(block)
        return cls(**values)
