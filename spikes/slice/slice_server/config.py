"""The slice's tunables, read from ``spikes/slice/data/`` and checked: unknown keys, missing keys and non-finite or
non-positive numbers are refused by name, so a typo in a tuning file is an error, not a silent default."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from slice_server import WIRE_VERSION

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
    power_w: float
    radius_m: float


@dataclass(frozen=True)
class SliceConfig:
    body: BodyParams
    kindle: KindleParams


def _section(raw: Mapping[str, object], name: str, keys: tuple[str, ...]) -> dict[str, float]:
    section = raw.get(name)
    if not isinstance(section, Mapping):
        raise ValueError(f"{name}: must be a mapping")
    if set(section) != set(keys):
        missing, extra = sorted(set(keys) - set(section)), sorted(set(section) - set(keys))
        raise ValueError(f"{name}: missing {missing}, unknown {extra}")
    out: dict[str, float] = {}
    for key in keys:
        value = section[key]
        if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name}.{key}: must be a finite positive number, got {value!r}")
        out[key] = float(value)
    return out


def parse(raw: object) -> SliceConfig:
    if not isinstance(raw, Mapping):
        raise ValueError("the body file must be a mapping")
    if raw.get("version") != WIRE_VERSION:
        raise ValueError(f"version must be {WIRE_VERSION!r}, got {raw.get('version')!r}")
    if set(raw) != {"version", "body", "kindle"}:
        raise ValueError(f"top-level keys must be version, body and kindle, got {sorted(raw)}")
    body = _section(raw, "body", tuple(BodyParams.__dataclass_fields__))
    if not body["substeps"].is_integer():
        raise ValueError(f"body.substeps: must be a whole number, got {body['substeps']!r}")
    substeps = int(body.pop("substeps"))
    kindle = _section(raw, "kindle", tuple(KindleParams.__dataclass_fields__))
    return SliceConfig(BodyParams(**body, substeps=substeps), KindleParams(**kindle))


def load(path: Path = DATA / "body.yaml") -> SliceConfig:
    return parse(yaml.safe_load(path.read_text()))
