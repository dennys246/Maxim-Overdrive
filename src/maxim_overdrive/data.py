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


def data_dir(here: Path | None = None) -> Path:
    """Bundled data: inside the wheel when installed, the repo's ``data/`` in a checkout. Neither is a FileNotFoundError
    that names both, never a path that silently doesn't exist (boundaries §11.2, W5). ``here`` is this package's
    directory; a test passes another."""
    here = Path(__file__).resolve().parent if here is None else here
    for candidate in (here / "_data", here.parents[1] / "data"):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        f"no game data: neither {here / '_data'} (installed) nor {here.parents[1] / 'data'} (checkout)"
    )


def materials() -> MaterialTable:
    """The game's material table (``data/materials/core.yaml``)."""
    return load_materials(data_dir() / "materials" / "core.yaml")


def action_limits() -> ActionLimits:
    """The game's action limits (``data/world/actions.yaml``)."""
    return load_action_limits(data_dir() / "world" / "actions.yaml")


def rig_profile(name: str) -> RigProfile:
    """A shipped rendering tier by name (``data/rigs/<name>.yaml``)."""
    return RigProfile.load(data_dir() / "rigs" / f"{name}.yaml")
