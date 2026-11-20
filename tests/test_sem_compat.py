"""The pymaxim-free stand-ins match Maxim's frozen SEM types, and the bridge works on them.

CLAUDE.md promises `simcore/adapters/sem/_compat.py` mirrors Maxim "field for field". Until this test existed the
promise was held by attention, and AffordanceSchema had drifted to two of Maxim's eight fields.
"""

from __future__ import annotations

import dataclasses
import importlib
import sys
import typing
from collections.abc import Iterator
from types import ModuleType

import pytest

from maxim_overdrive import data
from simcore.adapters.sem import _compat, bridge
from simcore.core.scene import Box, Scene
from simcore.core.world import World

LIMITS = data.action_limits()

MIRRORED = ["SensorReading", "ModulatorResult", "AffordanceSchema"]


def _shape(cls: type) -> list[tuple[str, object, object, object, object]]:
    hints = typing.get_type_hints(cls)
    out: list[tuple[str, object, object, object, object]] = []
    for f in dataclasses.fields(cls):
        default = f.default if f.default is not dataclasses.MISSING else "<required>"
        factory = f.default_factory() if f.default_factory is not dataclasses.MISSING else "<no factory>"
        out.append((f.name, hints[f.name], default, factory, (f.hash, f.compare, f.init, f.kw_only)))
    return out


@pytest.mark.parametrize("name", MIRRORED)
def test_compat_mirrors_maxim_field_for_field(name: str) -> None:
    sem = pytest.importorskip("maxim.embodiment.sem")
    theirs, ours = getattr(sem, name), getattr(_compat, name)
    assert _shape(ours) == _shape(theirs)
    assert ours.__dataclass_params__.__repr__() == theirs.__dataclass_params__.__repr__()  # frozen, eq, order, ...
    assert getattr(ours, "__slots__", None) == getattr(theirs, "__slots__", None)


class _BlockMaxim:
    """A meta-path finder that makes `import maxim...` fail, as on a machine without pymaxim."""

    def find_spec(self, fullname: str, path: object, target: ModuleType | None = None) -> None:
        if fullname == "maxim" or fullname.startswith("maxim."):
            raise ImportError(f"blocked for test: {fullname}")


@pytest.fixture
def bridge_without_maxim() -> Iterator[ModuleType]:
    saved = {k: v for k, v in sys.modules.items() if k == "maxim" or k.startswith("maxim.")}
    for k in saved:
        del sys.modules[k]
    blocker = _BlockMaxim()
    sys.meta_path.insert(0, blocker)
    try:
        yield importlib.reload(bridge)
    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(saved)
        importlib.reload(bridge)


def test_the_bridge_runs_on_the_stand_ins_without_pymaxim(bridge_without_maxim: ModuleType, dx_m, materials) -> None:
    b = bridge_without_maxim
    assert b.HAVE_MAXIM is False
    w = World.from_scene(
        Scene((2.0, 2.0, 2.0), (Box((0.8, 0, 0), (1.2, 2, 2), "concrete", "wall"),)),
        materials,
        dx_m=dx_m,
        limits=LIMITS,
    )
    sensors, mods = b.region_parts(w, "wall")
    reading = sensors["integrity"].read()
    assert type(reading) is _compat.SensorReading
    assert reading.value == pytest.approx(1.0)
    result = mods["structure"].execute("ignite", {"power_w": 1000.0})
    assert type(result) is _compat.ModulatorResult
    assert result.success
    assert all(type(a) is _compat.AffordanceSchema for a in mods["structure"].affordances.values())
    with pytest.raises(RuntimeError, match="pymaxim is not installed"):
        b.to_maxim_entity(w, "wall")
