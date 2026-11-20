"""This game's shipped data: where it lives, and the tables the game runs with.

The engine has no default path into anyone's data (boundaries §3); the game says where its files are and passes the
loaded tables to the engine as required parameters.
"""

from __future__ import annotations

from pathlib import Path

from simcore.adapters.loaders import load_action_limits, load_materials
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.protocol.tiers import RigProfile


def data_dir() -> Path:
    """Bundled data: inside the wheel when installed, the repo's ``data/`` in a checkout."""
    here = Path(__file__).resolve().parent
    installed = here / "_data"
    return installed if installed.is_dir() else here.parents[1] / "data"


def materials() -> MaterialTable:
    """The game's material table (``data/materials/core.yaml``)."""
    return load_materials(data_dir() / "materials" / "core.yaml")


def action_limits() -> ActionLimits:
    """The game's action limits (``data/world/actions.yaml``)."""
    return load_action_limits(data_dir() / "world" / "actions.yaml")


def rig_profile(name: str) -> RigProfile:
    """A shipped rendering tier by name (``data/rigs/<name>.yaml``)."""
    return RigProfile.load(data_dir() / "rigs" / f"{name}.yaml")
