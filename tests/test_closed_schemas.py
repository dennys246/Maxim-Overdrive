"""Red gates: every loader refuses a key it doesn't know (backlog B12).

Today each one ignores unknown keys, so a misspelt key vanishes silently: a material with ``degrade_above:`` for
``degrade_above_c`` never degrades. Each gate is strict and fails only because nothing was raised, so a fix that raises
the wrong type stays red. When closed schemas land, these flip and the markers come off.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from maxim_overdrive.config import MaterialTable, RigProfile, data_dir
from maxim_overdrive.imagination.spec import SpecRejected, place
from maxim_overdrive.world.scene import Scene

OPEN_SCHEMA = pytest.mark.xfail(
    strict=True, raises=pytest.fail.Exception, reason="B12: loaders ignore unknown keys (closed schemas not built)"
)
BOX = {"kind": "box", "min_m": [0, 0, 0], "max_m": [0.6, 0.6, 0.6], "material": "wood"}


@OPEN_SCHEMA
@pytest.mark.parametrize("where", ["top", "material"])
def test_the_material_table_refuses_an_unknown_key(tmp_path: Path, where: str) -> None:
    raw = yaml.safe_load((data_dir() / "materials" / "core.yaml").read_text())
    if where == "top":
        raw["materails"] = {}
    else:
        raw["materials"]["wood"]["degrade_above"] = 250.0  # a misspelt degrade_above_c
    path = tmp_path / "m.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="unknown"):
        MaterialTable.load(path)


@OPEN_SCHEMA
def test_a_rig_profile_refuses_an_unknown_key(tmp_path: Path) -> None:
    raw = yaml.safe_load((data_dir() / "rigs" / "rig.yaml").read_text())
    raw["cell_size"] = 0.5  # a misspelt cell_size_m
    path = tmp_path / "r.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="unknown"):
        RigProfile.load(path)


@OPEN_SCHEMA
@pytest.mark.parametrize(
    "scene",
    [
        {"extent_m": [1, 1, 1], "primitives": [BOX], "ambient": 30.0},  # a misspelt ambient_c
        {"extent_m": [1, 1, 1], "primitives": [{**BOX, "colour": "red"}]},
    ],
)
def test_a_scene_refuses_an_unknown_key(scene: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="unknown"):
        Scene.from_dict(scene)


@OPEN_SCHEMA
def test_an_imagined_object_refuses_an_unknown_key(rig: RigProfile, materials: MaterialTable) -> None:
    grid = Scene((3.0, 3.0, 2.0), ()).build(rig, materials)
    with pytest.raises(SpecRejected, match="unknown"):
        place(grid, {"name": "crate", "primitives": [BOX], "licence": "cc-by"}, (1.0, 1.0, 0.0))
