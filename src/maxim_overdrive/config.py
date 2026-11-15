"""Rig profiles and the material table: the two inputs every world is built from."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml


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
            cell_size_m=float(raw["cell_size_m"]),
            min_substeps_per_turn=int(raw["min_substeps_per_turn"]),
            full_res_radius_m=float(raw["full_res_radius_m"]),
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
                id=int(v["id"]),
                density_kg_m3=float(v["density_kg_m3"]),
                specific_heat_j_kgk=float(v["specific_heat_j_kgk"]),
                conductivity_w_mk=float(v["conductivity_w_mk"]),
                fracture_energy_j_m3=float(v["fracture_energy_j_m3"]),
                degrade_above_c=None if v.get("degrade_above_c") is None else float(v["degrade_above_c"]),
                degrade_rate_per_s_per_100c=float(v.get("degrade_rate_per_s_per_100c", 0.0)),
                color_rgb=tuple(int(c) for c in v["color_rgb"]),  # type: ignore[arg-type]
            )
        return cls(mats)
