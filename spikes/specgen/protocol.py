"""The spec generator spike's shared protocol (plan.md, the pre-registration; arms.yaml).

Throwaway spike code, never imported by ``src/``. generate.py and score.py both classify a reply here, so the loop's
decisions and the scorer's metrics read one definition: truncation first, then the parse, then the scorer's bounds
check, then ``place`` in a fresh empty scene (``arms.yaml::protocol``).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from maxim_overdrive.data import materials
from simcore.core.grid import MaterialGrid
from simcore.core.imagination import SpecRejected, place
from simcore.core.refusals import RefusalCode, Refused, agent_text
from simcore.core.scene import Primitive, Scene, primitives_from_data

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ("arms.yaml", "prompts_source.yaml", "split.py", "prompts_dev.yaml", "prompts_heldout.yaml")
SPLITS = {"dev": "prompts_dev.yaml", "heldout": "prompts_heldout.yaml"}
SCENE_EXTENT_M = (4.0, 4.0, 4.0)  # plan §5: an empty 4 x 4 x 4 m air scene
OFFSET_M = (0.503, 0.503, 0.003)  # plan §5: the scene offset
TRUTH_DX_M = 0.1  # plan §5: the truth grid
RETRY_SEED = "100 * attempt + seed"

# The classes an attempt can end in (plan §5 M1): accepted and refused come from place; the rest are the scorer's.
ACCEPTED, REFUSED, OUTSIDE, TRUNCATED, PARSE_FAILURE = (
    "accepted",
    "refused",
    "outside_world",
    "truncated",
    "parse_failure",
)


class FrozenMismatch(ValueError):
    """A frozen input differs from freeze.sha256: the run would not be the pre-registered one."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(base: Path = HERE) -> tuple[dict[str, str], dict[str, str]]:
    """freeze.sha256 as (file hashes by name, weights hashes by model id)."""
    files: dict[str, str] = {}
    weights: dict[str, str] = {}
    for line in (base / "freeze.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, name = line.split(maxsplit=1)
        if name.startswith("weights:"):
            weights[name.split(":")[1]] = digest
        else:
            files[name] = digest
    return files, weights


def check_frozen(base: Path = HERE) -> dict[str, str]:
    """The five frozen files' hashes, or FrozenMismatch naming every file that differs from the manifest."""
    files, _ = read_manifest(base)
    if set(files) != set(FROZEN):
        raise FrozenMismatch(f"freeze.sha256 lists {sorted(files)}, expected {sorted(FROZEN)}")
    wrong = [name for name in FROZEN if sha256_file(base / name) != files[name]]
    if wrong:
        raise FrozenMismatch(f"frozen files differ from freeze.sha256: {wrong}")
    return files


def load_arms(base: Path = HERE) -> dict[str, Any]:
    arms: dict[str, Any] = yaml.safe_load((base / "arms.yaml").read_text(encoding="utf-8"))
    if arms["sampling"]["retry_seed"] != RETRY_SEED:
        raise FrozenMismatch(
            f"arms.yaml's retry_seed is {arms['sampling']['retry_seed']!r}, this code implements {RETRY_SEED!r}"
        )
    return arms


def load_prompts(split: str, base: Path = HERE) -> list[dict[str, Any]]:
    doc = yaml.safe_load((base / SPLITS[split]).read_text(encoding="utf-8"))
    prompts: list[dict[str, Any]] = doc["prompts"]
    return prompts


def retry_seed(attempt: int, seed: int) -> int:
    """arms.yaml's retry_seed: attempt 0 uses the base seed; retry k uses 100 * k + seed."""
    return seed if attempt == 0 else 100 * attempt + seed


_FENCE = re.compile(r"```[A-Za-z0-9_-]*")


def parse_reply(text: str, arm: str) -> dict[str, Any] | None:
    """arms.yaml::protocol: A0's reply is the first complete JSON object after code fences are removed, tried with
    raw_decode at each '{' in order; A1-A3 decode under the grammar, so the whole reply is the object."""
    if arm != "A0":
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return None
        return obj if isinstance(obj, dict) else None
    cleaned = _FENCE.sub("", text)
    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(cleaned, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _whole_cm(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return (
        isinstance(value, list) and bool(value) and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    )


def _to_m(value: int | list[int]) -> float | list[float]:
    return value / 100 if isinstance(value, int) else [v / 100 for v in value]  # exact division, never v * 0.01


def convert(reply: Mapping[str, Any], arms: Mapping[str, Any]) -> dict[str, Any]:
    """The spec place reads: `intent` dropped, whole-centimetre keys renamed to metres by v / 100. Anything else (keys
    in metres, float centimetres) is passed as written, for place to judge (arms.yaml::protocol)."""
    keys = arms["protocol"]["keys_to_m"]
    dropped = set(arms["protocol"]["drop_before_place"])
    spec = {k: v for k, v in reply.items() if k not in dropped}
    listed = spec.get("primitives")
    if isinstance(listed, list):
        spec["primitives"] = [_convert_primitive(p, keys) if isinstance(p, dict) else p for p in listed]
    return spec


def _convert_primitive(p: Mapping[str, Any], keys: Mapping[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in p.items():
        if k in keys and _whole_cm(v):
            out[keys[k]] = _to_m(v)
        else:
            out[k] = v
    return out


def authored(spec: Mapping[str, Any]) -> tuple[Primitive, ...] | None:
    """The spec's primitives as simcore builds them, in the spec's own frame, or None if any is malformed."""
    try:
        return primitives_from_data(spec.get("primitives", []))
    except Refused:
        return None


def outside_world(spec: Mapping[str, Any], offset: Sequence[float] = OFFSET_M) -> bool:
    """The scorer's bounds check (place doesn't check bounds: a Known gap). A spec whose primitives don't build is
    left for place to refuse."""
    prims = authored(spec)
    if not prims:
        return False
    for p in prims:
        lo, hi = p.bounds_m
        for axis in range(3):
            if lo[axis] + offset[axis] < 0.0 or hi[axis] + offset[axis] > SCENE_EXTENT_M[axis]:
                return True
    return False


def empty_grid(dx_m: float = TRUTH_DX_M) -> MaterialGrid:
    return Scene(SCENE_EXTENT_M).build(materials(), dx_m=dx_m)


@dataclass(frozen=True)
class Verdict:
    """How one attempt ended: its class, and for a refusal its code, field and the agent_text A3 feeds back."""

    klass: str
    code: str | None = None
    field: str | None = None
    agent_text: str | None = None
    mass_kg: float | None = None

    @property
    def m1_pass(self) -> bool:
        """Plan §5 M1: accepted, or refused only as too_small (place raises it after every other check)."""
        return self.klass == ACCEPTED or (self.klass == REFUSED and self.code == RefusalCode.TOO_SMALL.value)


def place_verdict(spec: Mapping[str, Any], offset: Sequence[float] = OFFSET_M, dx_m: float = TRUTH_DX_M) -> Verdict:
    """place in a fresh empty scene. Only SpecRejected is a verdict; anything else is a bug and propagates."""
    try:
        mass = place(empty_grid(dx_m), dict(spec), tuple(offset))
    except SpecRejected as exc:
        code = exc.code.value
        return Verdict(REFUSED, code, exc.field, exc.agent_text)
    return Verdict(ACCEPTED, mass_kg=mass)


def classify(
    content: str, finish: str | None, arm: str, arms: Mapping[str, Any]
) -> tuple[Verdict, dict[str, Any] | None]:
    """arms.yaml's check order: truncation, the parse, the scorer's bounds check, then place."""
    if finish == "length":
        return Verdict(TRUNCATED), None
    reply = parse_reply(content, arm)
    if reply is None:
        return Verdict(PARSE_FAILURE), None
    spec = convert(reply, arms)
    if outside_world(spec):
        code = RefusalCode(arms["protocol"]["a3_scorer_refusals"]["outside_world"])
        return Verdict(OUTSIDE, code.value, None, agent_text(code)), spec
    return place_verdict(spec), spec
