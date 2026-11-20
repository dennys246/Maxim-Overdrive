"""Materials: the physical properties every cell is checked against, as types and per-id lookup arrays.

The core reads no files: a ``MaterialTable`` is built by a loader (``simcore.adapters.loaders.load_materials``) and
passed in as a required parameter, so the core has no default path into anyone's data (boundaries §3).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
import numpy.typing as npt

from simcore.core.checks import finite_real, shown, whole_number
from simcore.core.readonly import frozen

# The physical bounds a material must meet, whoever builds it (boundaries §5.1, TB-B2): heat capacity divides, so a
# zero density or specific heat would make the first heat step divide by zero.
_POSITIVE = ("density_kg_m3", "specific_heat_j_kgk")
_NON_NEGATIVE = ("conductivity_w_mk", "fracture_energy_j_m3", "degrade_rate_per_s_per_100c")


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

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(f"a material needs a name, got {shown(self.name)}")
        number = whole_number(self.id, f"{self.name}.id")
        if not 0 <= number <= 255:  # a negative id would index the property arrays from the end
            raise ValueError(f"{self.name}.id must fit in uint8 (0 to 255), got {number}")
        object.__setattr__(self, "id", number)
        for name in (*_POSITIVE, *_NON_NEGATIVE):
            value = finite_real(self.__dict__[name], f"{self.name}.{name}")
            if value < 0 or (value == 0 and name in _POSITIVE):
                kind = "positive" if name in _POSITIVE else "non-negative"
                raise ValueError(f"{self.name}.{name} must be {kind}, got {value!r}")
            object.__setattr__(self, name, value)
        if self.degrade_above_c is not None:
            above = finite_real(self.degrade_above_c, f"{self.name}.degrade_above_c")
            object.__setattr__(self, "degrade_above_c", above)
        object.__setattr__(self, "color_rgb", _colour(self.color_rgb, f"{self.name}.color_rgb"))

    @property
    def diffusivity_m2_s(self) -> float:
        return self.conductivity_w_mk / (self.density_kg_m3 * self.specific_heat_j_kgk)

    @property
    def volumetric_heat_capacity(self) -> float:
        """J / (m^3 K)."""
        return self.density_kg_m3 * self.specific_heat_j_kgk


def _colour(value: object, what: str) -> tuple[int, int, int]:
    """Three whole numbers from 0 to 255, or a ValueError that names the field."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 3:
        raise ValueError(f"{what} must be three values from 0 to 255, got {shown(value)}")
    rgb = tuple(whole_number(c, what) for c in value)
    if not all(0 <= c <= 255 for c in rgb):
        raise ValueError(f"{what} must be three values from 0 to 255, got {shown(value)}")
    return (rgb[0], rgb[1], rgb[2])


AIR_ID = 0
Lookup = npt.NDArray[np.float64]


def _lookup(fill: float, n: int, values: Mapping[int, float]) -> Lookup:
    arr = np.full(n, fill, dtype=np.float64)
    for i, v in values.items():
        arr[i] = v
    return frozen(arr)


class MaterialTable:
    """Materials by name and by id, plus per-id property lookup arrays for vectorized physics.

    Frozen, deeply (boundaries §5.1): the mappings are read-only views and the arrays are read-only; nothing writes
    them after construction."""

    def __init__(self, materials: Mapping[str, Material]) -> None:
        for key, m in materials.items():
            if not isinstance(m, Material) or m.name != key:
                raise ValueError(f"material {shown(key)} must be a Material of that name")
        ids = [m.id for m in materials.values()]
        if len(set(ids)) != len(ids):
            raise ValueError("material ids must be unique")
        if AIR_ID not in ids or materials.get("air") is None or materials["air"].id != AIR_ID:
            raise ValueError("the table must define 'air' with id 0")
        self._by_name = MappingProxyType(dict(materials))
        self._by_id = MappingProxyType({m.id: m for m in materials.values()})
        n, ms = max(ids) + 1, list(materials.values())
        self._rho_cp = _lookup(1.0, n, {m.id: m.volumetric_heat_capacity for m in ms})
        self._conductivity = _lookup(0.0, n, {m.id: m.conductivity_w_mk for m in ms})
        self._fracture = _lookup(0.0, n, {m.id: m.fracture_energy_j_m3 for m in ms})
        above = {m.id: m.degrade_above_c for m in ms if m.degrade_above_c is not None}
        self._degrade_above = _lookup(np.inf, n, above)
        self._degrade_rate = _lookup(0.0, n, {m.id: m.degrade_rate_per_s_per_100c for m in ms})

    @property
    def by_name(self) -> Mapping[str, Material]:
        return self._by_name

    @property
    def by_id(self) -> Mapping[int, Material]:
        return self._by_id

    @property
    def rho_cp(self) -> Lookup:
        return self._rho_cp

    @property
    def conductivity(self) -> Lookup:
        return self._conductivity

    @property
    def fracture(self) -> Lookup:
        return self._fracture

    @property
    def degrade_above(self) -> Lookup:
        return self._degrade_above

    @property
    def degrade_rate(self) -> Lookup:
        return self._degrade_rate

    def __getitem__(self, name: str) -> Material:
        return self.by_name[name]

    def __contains__(self, name: object) -> bool:
        return name in self.by_name
