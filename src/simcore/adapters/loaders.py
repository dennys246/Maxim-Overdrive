"""File gates: the material table and action limits read from YAML, strictly, into the core's types.

The core reads no files (boundaries §3); these loaders are the engine's edge to the file system. Each takes an
explicit path: where a game keeps its data is the game's business (``maxim_overdrive.data``), never the engine's.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from simcore.core.checks import shown
from simcore.core.limits import ACTION_LIMITS, ActionLimits
from simcore.core.materials import MATERIAL_TABLE, MaterialTable
from simcore.core.refusals import RefusalCode, Refused

# Each data format is a simcore.core.schema.Format declared beside its type (MATERIAL_TABLE in materials,
# ACTION_LIMITS in limits, RIG_PROFILE in simcore.protocol.tiers, SCENE in scene), so its version, its keys and its
# rules live in one place; a loader here reads the file strictly and hands the document to that Format, the one reader.
# The gate's API. Code outside the gates imports only these names from here, never a module this file imports
# (pathlib, yaml): tests/test_input_allowlist.py holds every import from a gate to its __all__ (delta round 4, D4-S2).
__all__ = [
    "DataPath",
    "FilePath",
    "existing_directory",
    "load_action_limits",
    "load_materials",
    "read_yaml",
]


class DataPath:
    """A place in a game's bundled data that only these gates open (B29; step 3b delta round 7, D7-N2).

    The game's data locator hands out one of these, never a ``pathlib.Path``: it joins bare names with ``/`` and
    prints itself, and nothing else, so game code can't read a data file past the strict YAML gate. It has no
    ``__fspath__``, so ``open`` and ``Path`` refuse it; a loader here takes it.
    """

    __slots__ = ("_path",)

    def __init__(self, path: Path) -> None:
        self._path = path

    def __truediv__(self, name: object) -> DataPath:
        if not isinstance(name, str) or not _BARE_NAME.fullmatch(name) or name in (".", ".."):
            raise Refused(f"a data path joins bare names only, got {shown(name)}", code=RefusalCode.BAD_NAME)
        return DataPath(self._path / name)

    __hash__ = None  # type: ignore[assignment]  # compared, never hashed: the simulation bans builtin hash()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DataPath) and other._path == self._path

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"DataPath({str(self._path)!r})"


_BARE_NAME = re.compile(r"[A-Za-z0-9_.-]+")
# A path a caller hands a gate: the only file-reading module is this one, so callers name paths without pathlib.
FilePath = str | Path | DataPath


def _path(path: FilePath) -> Path:
    return path._path if isinstance(path, DataPath) else Path(path)


class _StrictLoader(yaml.SafeLoader):
    """``yaml.SafeLoader`` that refuses a mapping with a repeated key instead of keeping the last value."""


def _no_duplicate_keys(loader: _StrictLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    # Repeats are judged among the keys written in this mapping; a key that overrides one merged in from <<: is the
    # point of a merge, not a repeat.
    written = [loader.construct_object(k, deep=True) for k, _ in node.value if k.tag != "tag:yaml.org,2002:merge"]
    for key in written:
        if not isinstance(key, (str, int, float, bool)) and key is not None:
            raise Refused(f"a mapping key must be a plain value, got {type(key).__name__}", code=RefusalCode.BAD_SHAPE)
    repeated = sorted({str(k) for k, n in Counter(written).items() if n > 1})
    if repeated:
        raise Refused(f"repeated key(s) {repeated} in a mapping", code=RefusalCode.DUPLICATE_KEY)
    loader.flatten_mapping(node)  # resolve merge keys (<<:) as SafeLoader does; the written keys come last and win
    return dict(loader.construct_pairs(node, deep=True))


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def existing_directory(base: str | Path, candidates: Sequence[str], what: str) -> DataPath:
    """The first of ``candidates`` (relative to ``base``, ``..`` allowed) that is a directory, as a ``DataPath``, or a
    FileNotFoundError that names them all.

    ``base`` is resolved before any arithmetic, so data beside a package reached through a symlink is found beside
    the real package (delta round 6, Executor N-h). Only a ``DataPath`` leaves: the game's data locator never holds a
    ``pathlib.Path`` it could open past the strict YAML gate (B29; step 3b(b) delta review, D1)."""
    real = Path(base).resolve()  # realpath reads the filesystem, so it happens here, in the gate
    tried = [(real / c).resolve() for c in candidates]
    for candidate in tried:
        if candidate.is_dir():
            return DataPath(candidate)
    raise FileNotFoundError(f"{what}: none of {', '.join(str(c) for c in tried)} is a directory")


MAX_FILE_BYTES = 16 * 2**20  # a data file's budget, checked before it is read (boundaries §5.4); core.yaml is 2 kB


def _text_of(path: FilePath) -> str:
    """The file's text as UTF-8 (never the machine's locale), or a Refused: a data file is a regular file (a FIFO or
    /dev/zero reports 0 bytes and never ends) of at most ``MAX_FILE_BYTES``, counted on the bytes read, so a file that
    grows after it is checked is still bounded (step 3b(b) delta review, D3)."""
    where = _path(path)
    if not where.exists():  # an operator's missing file, which the registry documents (delta round 5, D5-N1)
        raise FileNotFoundError(f"{path}: no such file")
    if not where.is_file():  # follows symlinks: a link to a FIFO or a device is not a regular file either
        raise Refused(f"{path}: not a regular file", code=RefusalCode.BAD_SHAPE)
    with where.open("rb") as handle:
        data = handle.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise Refused(f"{path}: larger than {MAX_FILE_BYTES} bytes, no data file is", code=RefusalCode.OVER_BUDGET)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused(f"{path}: not UTF-8 text", code=RefusalCode.BAD_SHAPE) from None


def read_yaml(path: FilePath) -> object:
    """A data file parsed strictly: invalid YAML and repeated keys are refused, with the file named.

    Every data loader reads through here, so none of them can keep the last of two values for one key. A scalar
    SafeLoader can't build (``2026-02-30``, ``!!int x``, ``!!bool maybe``, a 5,000-digit int) is a refusal too:
    those raise ValueError, KeyError or AttributeError inside PyYAML's constructors (step 3b(b) review, T1-S1, S2).
    The handler wraps the whole load, so a bug in ``_StrictLoader``'s own constructors would read as the file's
    ``bad_shape`` too: narrowing it needs a hook per scalar constructor, which no refusal so far has needed (D-N5).
    """
    text = _text_of(path)
    try:
        return yaml.load(text, Loader=_StrictLoader)  # a SafeLoader subclass
    except yaml.YAMLError as exc:  # reported, with the file, as the refusal
        raise Refused(f"{path}: not valid YAML: {exc}", code=RefusalCode.BAD_SHAPE) from None
    except RecursionError:  # the parser recurses per level; no data file nests this deep
        raise Refused(f"{path}: nested too deeply to be a data file", code=RefusalCode.OVER_BUDGET) from None
    except Refused as exc:
        raise Refused(f"{path}: {exc}", code=exc.code, field=exc.field) from None
    except (ValueError, KeyError, AttributeError, TypeError, OverflowError) as exc:  # a scalar it can't build
        message = f"{path}: a value YAML can't build ({type(exc).__name__}): {shown(str(exc))}"
        raise Refused(message, code=RefusalCode.BAD_SHAPE) from None


def load_materials(path: FilePath) -> MaterialTable:
    """The material table in the file at ``path``, at its format's version, or a ValueError saying why not."""
    return MaterialTable.from_document(MATERIAL_TABLE.read(read_yaml(path), f"material table {path}"))


def load_action_limits(path: FilePath) -> ActionLimits:
    """The action limits in the file at ``path``, at their format's version, or a ValueError saying why not."""
    return ActionLimits.from_document(ACTION_LIMITS.read(read_yaml(path), f"action limits {path}"))
