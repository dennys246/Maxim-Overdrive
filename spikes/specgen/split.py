"""Deal the spec generator spike's prompts into the development and held-out splits (plan §4).

Throwaway spike code, never imported by ``src/``. A seeded generator draws the held-out prompts, so no one chooses
them. ``HELD_OUT`` fixes how many each stratum gives, about a quarter, with the halves broken so the total is 50:
furniture 13 and mixed 12 of 50 each, glass 8 of 30, impossible 7 of 30. The impossible stratum is dealt within each
`breaks` group (``HELD_OUT_BREAKS``), so the held-out split tests every budget.

The source is checked before anything is dealt:
- a loader that refuses duplicate keys (``yaml.safe_load`` keeps the last one silently);
- each prompt's keys against ``KEYS``;
- the plan's stratum sizes;
- unique ids and texts;
- materials from ``MATERIALS``, a copy of ``data/materials/core.yaml``'s solids (an empty ``expect`` is allowed);
- `breaks` values, present on impossible prompts only.

Run: ``python spikes/specgen/split.py`` from the repository root. It rewrites ``prompts_dev.yaml`` and
``prompts_heldout.yaml`` beside this file. The same source gives the same files for one NumPy and one PyYAML
version, which the headers record; NumPy doesn't promise ``Generator.permutation``'s stream across releases.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import yaml

HERE = Path(__file__).parent
SIZES = {"furniture": 50, "barriers": 40, "glass": 30, "mixed": 50, "impossible": 30}
HELD_OUT = {"furniture": 13, "barriers": 10, "glass": 8, "mixed": 12, "impossible": 7}
HELD_OUT_BREAKS = {"extent": 3, "mass": 2, "primitives": 2}
assert sum(HELD_OUT_BREAKS.values()) == HELD_OUT["impossible"]  # a constant check at import
MATERIALS = {"concrete", "steel", "glass", "wood", "drywall"}
KEYS = {"id", "text", "expect", "breaks", "single_ok", "hard"}
HARD = {"shape"}
SEED = 0


class _StrictLoader(yaml.SafeLoader):
    """A safe loader that refuses a mapping with a repeated key."""


def _no_repeats(loader: _StrictLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    keys = [loader.construct_object(k) for k, _ in node.value]
    if not all(isinstance(k, str) for k in keys):
        raise ValueError(f"line {node.start_mark.line + 1}: every key must be a string")
    repeated = {k for k in keys if keys.count(k) > 1}
    if repeated:
        raise ValueError(f"line {node.start_mark.line + 1}: repeated keys {sorted(map(str, repeated))}")
    return loader.construct_mapping(node)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_repeats)


def _check_prompt(stratum: str, p: dict[str, Any]) -> None:
    if not isinstance(p, dict):
        raise ValueError(f"{stratum}: each prompt must be a mapping, not {p!r}")
    pid = p.get("id")
    if not set(p) <= KEYS or not {"id", "text", "expect"} <= set(p):
        raise ValueError(f"{pid}: keys {sorted(map(str, p))} must include id, text and expect, within {sorted(KEYS)}")
    if not isinstance(p["text"], str) or not p["text"].strip():
        raise ValueError(f"{pid}: text must be a non-empty string")
    if not isinstance(p["expect"], list) or not all(isinstance(m, str) and m in MATERIALS for m in p["expect"]):
        raise ValueError(f"{pid}: unknown material in {p['expect']}")
    if (stratum == "impossible") != ("breaks" in p):
        raise ValueError(f"{pid}: `breaks` belongs to the impossible stratum only")
    if "breaks" in p and p["breaks"] not in list(HELD_OUT_BREAKS):
        raise ValueError(f"{pid}: breaks must be one of {sorted(HELD_OUT_BREAKS)}")
    if p.get("single_ok", True) is not True or p.get("hard", "shape") not in list(HARD):
        raise ValueError(f"{pid}: single_ok must be true and hard one of {sorted(HARD)}")


def _checked(source: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(source, dict) or type(source.get("version")) is not int or source["version"] != 0:
        raise ValueError("prompts_source.yaml: a mapping with version 0 (an integer) is required")
    strata = {k: v for k, v in source.items() if k != "version"}
    if {k: len(v) for k, v in strata.items()} != SIZES:
        raise ValueError(f"stratum sizes {[(k, len(v)) for k, v in strata.items()]} differ from the plan's {SIZES}")
    for name, prompts in strata.items():
        for p in prompts:
            _check_prompt(name, p)
    for field in ("id", "text"):
        values = [p[field] for prompts in strata.values() for p in prompts]
        if len(values) != len(set(values)):
            raise ValueError(f"prompt {field}s repeat")
    return strata


def _held_out(rng: np.random.Generator, name: str, prompts: list[dict[str, Any]]) -> set[int]:
    groups = {"all": list(range(len(prompts)))}
    quota = {"all": HELD_OUT[name]}
    if name == "impossible":
        groups = {b: [i for i, p in enumerate(prompts) if p["breaks"] == b] for b in HELD_OUT_BREAKS}
        quota = HELD_OUT_BREAKS
    chosen: set[int] = set()
    for group, members in groups.items():  # a fixed order, so the draws don't depend on the file's order
        chosen |= {members[i] for i in rng.permutation(len(members))[: quota[group]].tolist()}
    return chosen


def _deal(strata: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = np.random.default_rng(SEED)
    dev: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    for name in SIZES:  # a fixed stratum order, so the draws don't depend on the file's key order
        chosen = _held_out(rng, name, strata[name])
        for i, p in enumerate(strata[name]):
            (held if i in chosen else dev).append({"stratum": name, **p})
    return dev, held


def _write(path: Path, split: str, prompts: list[dict[str, Any]]) -> None:
    header = (
        f"# The spec generator spike's {split} split (plan §4), dealt by split.py from prompts_source.yaml with\n"
        f"# numpy.random.default_rng({SEED}), numpy {np.__version__}, PyYAML {yaml.__version__}.\n"
        "# Generated: edit the source and rerun, never this file.\n"
    )
    body = yaml.safe_dump({"version": 0, "split": split, "prompts": prompts}, sort_keys=False, width=120)
    path.write_text(header + body, encoding="utf-8")


def main() -> None:
    source = yaml.load((HERE / "prompts_source.yaml").read_text(encoding="utf-8"), Loader=_StrictLoader)
    dev, held = _deal(_checked(source))
    _write(HERE / "prompts_dev.yaml", "development", dev)
    _write(HERE / "prompts_heldout.yaml", "held-out", held)
    print(f"split: {len(dev)} development, {len(held)} held out")


if __name__ == "__main__":
    main()
