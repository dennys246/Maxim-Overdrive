"""Materials: the physical properties every cell is checked against, as types and per-id lookup arrays.

The core reads no files: a ``MaterialTable`` is built by a loader (``simcore.adapters.loaders.load_materials``) and
passed in as a required parameter, so the core has no default path into anyone's data (boundaries §3).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any

import numpy as np
import numpy.typing as npt

from simcore.core.checks import shown
from simcore.core.readonly import frozen
from simcore.core.refusals import RefusalCode, Refused
from simcore.core.schema import Field, Format, MapOf, Nested, Real, Rgb, Schema, Text, Whole

# The material's one schema (boundaries §5.1, TB-B2): the file's reader, Material's constructor and the table's lookup
# arrays all read it. Heat capacity divides, so a zero density or specific heat would make the first heat step divide
# by zero; a negative conductivity would run heat uphill. The bounds are validity bounds, not tunables, each past any
# real material on both sides (hydrogen gas 0.084 to osmium 22,590 kg/m³; lead 129 to hydrogen 14,300 J/kg K;
# graphene about 5,000 W/m K), so no product a law forms overflows or underflows: 1e200 times 1e200 made rho_cp
# infinite and the first step NaN (step 3b(b) review, T1-S7), and 1e-3 times 1e-3 with k = 1e4 made the stable step
# 6e-13 s, 10^13 substeps a turn (delta review, D1). The diffusivity bound is the one the substep count reads.
# ``lookup`` is the value an unused id gets in its array.
MATERIAL = Schema(
    (
        Field("id", Whole(0, 255)),  # uint8 cells; a negative id would index the property arrays from the end
        Field("density_kg_m3", Real(lo=0.05, hi=1e5)),
        Field("specific_heat_j_kgk", Real(lo=100.0, hi=1e5)),
        Field("conductivity_w_mk", Real(lo=0.0, hi=1e4), lookup=0.0),
        Field("fracture_energy_j_m3", Real(lo=0.0, hi=1e12), lookup=0.0),
        Field("degrade_above_c", Real(lo=-273.15, hi=1e4), required=False, nullable=True, lookup=np.inf),
        Field("degrade_rate_per_s_per_100c", Real(lo=0.0, hi=1e3), required=False, default=0.0, lookup=0.0),
        Field("color_rgb", Rgb()),
    )
)
# Pyrolytic graphite, the most diffusive real solid, is about 1.2e-3 m²/s; air 2.2e-5. At 1e-2 the 0.05 m grid's
# stable step stays above 0.04 s.
MAX_DIFFUSIVITY_M2_S = 1e-2
MATERIAL_NAME = Text()  # the file's key and Material.name: one rule whoever builds the material
MAX_MATERIALS = 256  # one per uint8 id
MATERIAL_TABLE = Format(
    "material table", 0, Schema((Field("materials", MapOf(MATERIAL_NAME, Nested(MATERIAL), MAX_MATERIALS)),))
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", MATERIAL_NAME.convert(self.name, "a material's name"))
        values = asdict(self)
        for name, value in MATERIAL.check(values, f"material {self.name}").items():
            object.__setattr__(self, name, value)
        if self.diffusivity_m2_s > MAX_DIFFUSIVITY_M2_S:
            message = (
                f"material {self.name}'s diffusivity k/(rho c) must be at most {MAX_DIFFUSIVITY_M2_S:g} m²/s, got "
                f"{self.diffusivity_m2_s:g}: the heat law's stable step shrinks with it"
            )
            raise Refused(message, code=RefusalCode.OUT_OF_RANGE, field="conductivity_w_mk")

    @property
    def diffusivity_m2_s(self) -> float:
        return self.conductivity_w_mk / (self.density_kg_m3 * self.specific_heat_j_kgk)

    @property
    def volumetric_heat_capacity(self) -> float:
        """J / (m^3 K)."""
        return self.density_kg_m3 * self.specific_heat_j_kgk


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
                raise Refused(f"material {shown(key)} must be a Material of that name", code=RefusalCode.BAD_SHAPE)
        ids = [m.id for m in materials.values()]
        if len(set(ids)) != len(ids):
            raise Refused("material ids must be unique", code=RefusalCode.DUPLICATE_KEY, field="id")
        if AIR_ID not in ids or materials.get("air") is None or materials["air"].id != AIR_ID:
            raise Refused("the table must define 'air' with id 0", code=RefusalCode.MISSING_FIELD)
        self._by_name = MappingProxyType(dict(materials))
        self._by_id = MappingProxyType({m.id: m for m in materials.values()})
        n, ms = max(ids) + 1, [asdict(m) for m in materials.values()]
        # One array per field the schema marks with a lookup value, so a new per-id property is declared once.
        self._lookups = MappingProxyType(
            {
                f.name: _lookup(f.lookup, n, {m["id"]: m[f.name] for m in ms if m[f.name] is not None})
                for f in MATERIAL.fields
                if f.lookup is not None
            }
        )
        self._rho_cp = _lookup(1.0, n, {m["id"]: m["density_kg_m3"] * m["specific_heat_j_kgk"] for m in ms})

    @classmethod
    def from_document(cls, doc: Mapping[str, object]) -> MaterialTable:
        """The table from a document ``MATERIAL_TABLE`` has read."""
        entries: Mapping[str, Mapping[str, Any]] = doc["materials"]  # type: ignore[assignment]  # the schema's MapOf
        return cls({name: Material(name=name, **entry) for name, entry in entries.items()})

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
    def lookups(self) -> Mapping[str, Lookup]:
        """Every per-id array the schema declares, by field name."""
        return self._lookups

    @property
    def conductivity(self) -> Lookup:
        return self._lookups["conductivity_w_mk"]

    @property
    def fracture(self) -> Lookup:
        return self._lookups["fracture_energy_j_m3"]

    @property
    def degrade_above(self) -> Lookup:
        return self._lookups["degrade_above_c"]

    @property
    def degrade_rate(self) -> Lookup:
        return self._lookups["degrade_rate_per_s_per_100c"]

    def __getitem__(self, name: str) -> Material:
        return self.by_name[name]

    def __contains__(self, name: object) -> bool:
        return name in self.by_name
