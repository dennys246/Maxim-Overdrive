"""Materials: the physical properties every cell is checked against, as types and per-id lookup arrays.

The core reads no files: a ``MaterialTable`` is built by a loader (``simcore.adapters.loaders.load_materials``) and
passed in as a required parameter, so the core has no default path into anyone's data (boundaries §3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


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
