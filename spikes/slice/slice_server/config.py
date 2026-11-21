"""The slice's tunables, read from ``spikes/slice/data/`` and checked: unknown keys, missing keys and non-finite or
non-positive numbers are refused by name, so a typo in a tuning file is an error, not a silent default."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from slice_server import WIRE_VERSION
from slice_server.fire import FireParams
from slice_server.heat_debt import HeatParams

DATA = Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True)
class BodyParams:
    mass_kg: float
    radius_m: float
    height_m: float
    walk_speed_m_s: float
    overdrive_speed_m_s: float
    response_s: float
    max_speed_m_s: float
    substeps: int
    step_clearance_m: float


@dataclass(frozen=True)
class KindleParams:
    reach_m: float


@dataclass(frozen=True)
class FuelEntry:
    """A flammable material's fire numbers; its density and heat capacity come from the world's material table."""

    releasable_energy_j_kg: float
    ignition_c: float
    burn_rate_kg_s_m2: float


@dataclass(frozen=True)
class FuelConfig:
    materials: Mapping[str, FuelEntry]
    objects: Mapping[str, float]  # named object -> the burnable share of its box
    fire: FireParams


@dataclass(frozen=True)
class SliceConfig:
    body: BodyParams
    kindle: KindleParams
    heat: HeatParams
    fuel: FuelConfig


def _positive(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{where}: must be a finite positive number, got {value!r}")
    return float(value)


def _mapping(value: object, where: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{where}: must be a mapping")
    return value


def _section(raw: Mapping[str, object], name: str, keys: tuple[str, ...]) -> dict[str, float]:
    section = _mapping(raw.get(name), name)
    if set(section) != set(keys):
        missing, extra = sorted(set(keys) - set(section)), sorted(set(section) - set(keys))
        raise ValueError(f"{name}: missing {missing}, unknown {extra}")
    return {key: _positive(section[key], f"{name}.{key}") for key in keys}


def _top(raw: object, keys: set[str], what: str) -> Mapping[str, object]:
    top = _mapping(raw, f"the {what} file")
    if top.get("version") != WIRE_VERSION:
        raise ValueError(f"version must be {WIRE_VERSION!r}, got {top.get('version')!r}")
    if set(top) != keys:
        raise ValueError(f"top-level keys must be {sorted(keys)}, got {sorted(top)}")
    return top


def _fields(cls: type) -> tuple[str, ...]:
    return tuple(cls.__dataclass_fields__)  # type: ignore[attr-defined]


def parse_body(raw: object) -> tuple[BodyParams, KindleParams, HeatParams]:
    top = _top(raw, {"version", "body", "kindle", "heat"}, "body")
    body = _section(top, "body", _fields(BodyParams))
    if not body["substeps"].is_integer():
        raise ValueError(f"body.substeps: must be a whole number, got {body['substeps']!r}")
    substeps = int(body.pop("substeps"))
    kindle = _section(top, "kindle", _fields(KindleParams))
    heat = _section(top, "heat", _fields(HeatParams))
    if not heat["warn_c"] < heat["trip_c"]:
        raise ValueError("heat: warn_c must be below trip_c")
    return BodyParams(**body, substeps=substeps), KindleParams(**kindle), HeatParams(**heat)


def parse_fuel(raw: object, *, ambient_c: float) -> FuelConfig:
    top = _top(raw, {"version", "materials", "objects", "fire"}, "fuel")
    entries = _mapping(top["materials"], "materials")
    materials = {name: FuelEntry(**_section(entries, str(name), _fields(FuelEntry))) for name in entries}
    objects = {str(name): _positive(v, f"objects.{name}") for name, v in _mapping(top["objects"], "objects").items()}
    for name, fraction in objects.items():
        if fraction > 1:
            raise ValueError(f"objects.{name}: a burnable share is at most 1, got {fraction}")
    fire = _section(top, "fire", tuple(k for k in _fields(FireParams) if k != "ambient_c"))
    return FuelConfig(materials, objects, FireParams(**fire, ambient_c=ambient_c))


def load(data: Path = DATA, *, ambient_c: float = 20.0) -> SliceConfig:
    body, kindle, heat = parse_body(yaml.safe_load((data / "body.yaml").read_text()))
    fuel = parse_fuel(yaml.safe_load((data / "fuel.yaml").read_text()), ambient_c=ambient_c)
    return SliceConfig(body, kindle, heat, fuel)
