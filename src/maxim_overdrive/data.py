"""This game's shipped data: where it lives, and the tables the game runs with.

The engine has no default path into anyone's data (boundaries §3); the game says where its files are and passes the
loaded tables to the engine as required parameters.
"""

from __future__ import annotations

import re
from pathlib import Path

from simcore.adapters.loaders import existing_directory, load_action_limits, load_materials
from simcore.core.checks import shown
from simcore.core.limits import ActionLimits
from simcore.core.materials import MaterialTable
from simcore.protocol.tiers import RigProfile

__all__ = ["action_limits", "data_dir", "materials", "rig_profile"]

# This module does path arithmetic only; the file gate (simcore.adapters.loaders) touches the filesystem.
# tests/test_input_allowlist.py holds its Path attributes to PATH_ARITHMETIC (delta round 4, S-d).
RIG_NAME = re.compile(r"[A-Za-z0-9_-]+")


def data_dir(here: Path | None = None) -> Path:
    """Bundled data: inside the wheel when installed, the repo's ``data/`` in a checkout. Neither is a FileNotFoundError
    that names both, never a path that silently doesn't exist (boundaries §11.2, W5). ``here`` is this package's
    directory; a test passes another."""
    here = Path(__file__).resolve().parent if here is None else here
    return existing_directory([here / "_data", here.parents[1] / "data"], "no game data (installed, then checkout)")


def materials() -> MaterialTable:
    """The game's material table (``data/materials/core.yaml``)."""
    return load_materials(data_dir() / "materials" / "core.yaml")


def action_limits() -> ActionLimits:
    """The game's action limits (``data/world/actions.yaml``)."""
    return load_action_limits(data_dir() / "world" / "actions.yaml")


def rig_profile(name: str) -> RigProfile:
    """A shipped rendering tier by name (``data/rigs/<name>.yaml``). The name is a bare name: no separator, no ``..``
    and no absolute path, so it can't reach a file outside ``data/rigs/`` (delta round 4, D4-N2)."""
    if not isinstance(name, str) or not RIG_NAME.fullmatch(name):
        raise ValueError(f"a rig name is letters, digits, '_' and '-' only, got {shown(name)}")
    return RigProfile.load(data_dir() / "rigs" / f"{name}.yaml")
