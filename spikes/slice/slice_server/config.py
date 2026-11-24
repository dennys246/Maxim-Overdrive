"""The slice's tunables, read from ``spikes/slice/data/`` and checked: unknown keys, missing keys and non-finite or
non-positive numbers are refused by name, so a typo in a tuning file is an error, not a silent default."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from simcore.adapters.loaders import read_yaml
from simcore.core.checks import shown
from slice_server import WIRE_VERSION
from slice_server.body import BodyParams
from slice_server.fire import FireParams
from slice_server.heat_debt import HeatParams
from slice_server.npc import NpcParams
from slice_server.voice import VoiceParams

DATA = Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True)
class KindleParams:
    reach_m: float


@dataclass(frozen=True)
class StrikeParams:
    reach_m: float
    energy_j: float
    overdrive_energy_j: float
    sigma_m: float
    overdrive_heat_j: float
    recoil_ns: float


@dataclass(frozen=True)
class NpcConfig:
    vendor: NpcParams
    voice: VoiceParams
    canned: Mapping[str, list[str]]  # state -> lines, used when the model can't answer


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
    strike: StrikeParams
    fuel: FuelConfig
    npc: NpcConfig


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


def parse_body(raw: object) -> tuple[BodyParams, KindleParams, HeatParams, StrikeParams]:
    top = _top(raw, {"version", "body", "kindle", "heat", "strike"}, "body")
    body = _section(top, "body", _fields(BodyParams))
    if not body["substeps"].is_integer():
        raise ValueError(f"body.substeps: must be a whole number, got {body['substeps']!r}")
    substeps = int(body.pop("substeps"))
    kindle = _section(top, "kindle", _fields(KindleParams))
    heat = _section(top, "heat", _fields(HeatParams))
    if not heat["warn_c"] < heat["trip_c"]:
        raise ValueError("heat: warn_c must be below trip_c")
    strike = StrikeParams(**_section(top, "strike", _fields(StrikeParams)))
    return BodyParams(**body, substeps=substeps), KindleParams(**kindle), HeatParams(**heat), strike


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


NPC_STATES = ("flee", "douse", "doused", "warn", "comment", "idle")


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: must be non-empty text")
    return value


def parse_npc(raw: object) -> NpcConfig:
    top = _top(raw, {"version", "vendor", "voice", "canned"}, "npc")
    vendor = _section(top, "vendor", _fields(NpcParams))
    if not vendor["charges"].is_integer():
        raise ValueError(f"vendor.charges: must be a whole number, got {vendor['charges']!r}")
    charges = int(vendor.pop("charges"))
    voice = _mapping(top["voice"], "voice")
    if set(voice) != set(_fields(VoiceParams)):
        raise ValueError(f"voice: keys must be {sorted(_fields(VoiceParams))}, got {sorted(voice)}")
    max_words = _positive(voice["max_words"], "voice.max_words")
    if not max_words.is_integer():
        raise ValueError(f"voice.max_words: must be a whole number, got {max_words!r}")
    params = VoiceParams(
        _text(voice["model"], "voice.model"), _text(voice["host"], "voice.host"),
        _positive(voice["timeout_s"], "voice.timeout_s"), int(max_words), _text(voice["persona"], "voice.persona"),
    )  # fmt: skip
    canned = _mapping(top["canned"], "canned")
    if set(canned) != set(NPC_STATES):
        raise ValueError(f"canned: needs lines for exactly {sorted(NPC_STATES)}, got {sorted(canned)}")
    lines = {}
    for state in NPC_STATES:
        listed = canned[state]
        if not isinstance(listed, list) or not listed:
            raise ValueError(f"canned.{state}: must be a non-empty list of lines")
        lines[state] = [_text(line, f"canned.{state}") for line in listed]
    return NpcConfig(NpcParams(**vendor, charges=charges), params, lines)


FILES = ("body", "fuel", "npc")


def raw(data: Path = DATA) -> dict[str, object]:
    """The data files as read, before parsing: what a session log keeps, so a replay runs on the tuning it was played
    on. The repo's strict YAML reader: a repeated key is refused, not silently overridden by the last one."""
    return {name: read_yaml(data / f"{name}.yaml") for name in FILES}


def parse(files: object, *, ambient_c: float = 20.0) -> SliceConfig:
    """``raw``'s mapping, parsed and checked: every file by its parser, each refusal naming what is wrong."""
    if not isinstance(files, dict) or set(files) != set(FILES):
        raise ValueError(f"the slice's data is the files {list(FILES)}, got {shown(files)}")
    body, kindle, heat, strike = parse_body(files["body"])
    fuel = parse_fuel(files["fuel"], ambient_c=ambient_c)
    return SliceConfig(body, kindle, heat, strike, fuel, parse_npc(files["npc"]))


def load(data: Path = DATA, *, ambient_c: float = 20.0) -> SliceConfig:
    return parse(raw(data), ambient_c=ambient_c)
