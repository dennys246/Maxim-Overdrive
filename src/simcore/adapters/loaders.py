"""File gates: the material table and action limits read from YAML, strictly, into the core's types.

The core reads no files (boundaries §3); these loaders are the engine's edge to the file system. Each takes an
explicit path: where a game keeps its data is the game's business (``maxim_overdrive.data``), never the engine's.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from simcore.core.checks import finite_real, format_version, known_keys, shown, whole_number
from simcore.core.limits import ActionLimits
from simcore.core.materials import Material, MaterialTable

# Each data format has its own version (MATERIAL_TABLE_VERSION, ACTION_LIMITS_VERSION, and the rendering tier's
# RIG_PROFILE_VERSION in simcore.protocol.tiers), checked by checks.format_version before the keys. A change a reader
# of the old version can't read bumps it, and the reader then migrates or loudly refuses the committed v0 files in
# tests/fixtures/formats/ (CLAUDE.md, "Every format is versioned").
# The gate's API. Code outside the gates imports only these names from here, never a module this file imports
# (pathlib, yaml): tests/test_input_allowlist.py holds every import from a gate to its __all__ (delta round 4, D4-S2).
__all__ = [
    "ACTION_LIMITS_VERSION",
    "MATERIAL_OPTIONAL",
    "MATERIAL_REQUIRED",
    "MATERIAL_TABLE_VERSION",
    "FilePath",
    "existing_directory",
    "load_action_limits",
    "load_materials",
    "read_yaml",
]

# A path a caller hands a gate: the only file-reading module is this one, so callers name paths without pathlib.
FilePath = str | Path

MATERIAL_TABLE_VERSION = 0
# Declared beside the reader, not derived from Material: a field added to the dataclass and forgotten here must not
# become a key the file may carry and the reader ignores. A test holds the two sets to the dataclass.
MATERIAL_REQUIRED = frozenset(
    {"id", "density_kg_m3", "specific_heat_j_kgk", "conductivity_w_mk", "fracture_energy_j_m3", "color_rgb"}
)
MATERIAL_OPTIONAL = frozenset({"degrade_above_c", "degrade_rate_per_s_per_100c"})

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


def existing_directory(candidates: Sequence[FilePath], what: str) -> Path:
    """The first of ``candidates`` that is a directory, or a FileNotFoundError that names them all.

    The game's data locator asks this gate, so the game itself only does path arithmetic (delta round 4, S-d)."""
    for candidate in candidates:
        if Path(candidate).is_dir():
            return Path(candidate).resolve()  # realpath reads the filesystem, so it happens here, in the gate
    raise FileNotFoundError(f"{what}: none of {', '.join(str(c) for c in candidates)} is a directory")


def read_yaml(path: FilePath) -> object:
    """A data file parsed strictly: invalid YAML and repeated keys are refused, with the file named.

    Every data loader reads through here, so none of them can keep the last of two values for one key.
    """
    try:
        return yaml.load(Path(path).read_text(), Loader=_StrictLoader)  # a SafeLoader subclass
    except yaml.YAMLError as exc:  # reported, with the file, as the refusal
        raise ValueError(f"{path}: not valid YAML: {exc}") from None
    except RecursionError:  # the parser recurses per level; no data file nests this deep
        raise ValueError(f"{path}: nested too deeply to be a data file") from None
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from None


def _colour(value: object, what: str) -> tuple[int, int, int]:
    """Three whole numbers, or a ValueError that names the field (a scalar or a string is refused, not iterated)."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 3:
        raise ValueError(f"{what} must be three whole numbers, got {shown(value)}")
    return (whole_number(value[0], what), whole_number(value[1], what), whole_number(value[2], what))


def _material(name: object, entry: object) -> Material:
    if not isinstance(name, str):
        raise ValueError(f"material names must be strings, got {shown(name)}")
    v = known_keys(entry, f"material {name}", required=MATERIAL_REQUIRED, optional=MATERIAL_OPTIONAL)
    return Material(
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


def load_materials(path: FilePath) -> MaterialTable:
    """The material table in the file at ``path``, at ``MATERIAL_TABLE_VERSION``, or a ValueError saying why not."""
    path = Path(path)
    what = f"material table {path}"
    table = format_version(read_yaml(path), MATERIAL_TABLE_VERSION, what)
    raw = known_keys(table, what, required={"version", "materials"})["materials"]
    if not isinstance(raw, Mapping):
        raise ValueError(f"materials must be a mapping, got {type(raw).__name__}")
    return MaterialTable({name: _material(name, entry) for name, entry in raw.items()})


def load_action_limits(path: FilePath) -> ActionLimits:
    """The action limits in the file at ``path``, at ``ACTION_LIMITS_VERSION``, or a ValueError saying why not."""
    path = Path(path)
    raw = format_version(read_yaml(path), ACTION_LIMITS_VERSION, f"{path}: action limits")
    top = known_keys(raw, f"{path}", required={"version", *_LIMIT_FIELDS})
    values: dict[str, Any] = {}
    for section, names in _LIMIT_FIELDS.items():
        values.update(known_keys(top[section], f"{path}: {section}", required=names))
    return ActionLimits(**values)
