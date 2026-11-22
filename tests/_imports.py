"""Untrusted input by source, fail closed (boundaries §5.2, B-4; step 3b delta rounds 4 to 6).

Five allowlists, each a set of names with a reason, so a new input route is refused until someone names it:

- **External imports per layer** (``ALLOWED``), read from grimp's graph, the graph import-linter checks.
- **Every external name per layer** (``EXTERNAL_NAMES``): grimp records ``numpy.lib.npyio`` as ``numpy``, and an
  allowed module carries others with it (``reprlib.builtins``, ``dataclasses.sys``), so this names exactly which
  dotted names each layer reaches. Methods on values are a stated blind spot.
- **What one internal module may take from another:** a name it defines or lists in ``__all__``, never one it only
  imported (``internal_reexports``); and from a gate (``GATES``), only its ``__all__``.
- **The attributes a path-holding module may use** (``PATH_HOLDERS``): path arithmetic, so the modules that hold a
  path open nothing; the file gate does.

Every route counts: ``from m import n``, an attribute chain through any import of ``m``, and ``getattr(m, 'n')``
with a literal name.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import subprocess
import sys
import types
from pathlib import Path

PACKAGES = ("simcore", "maxim_overdrive")

# Each layer's allowed external modules, with the reason. The most specific key holds for a module.
_NUMERIC = {
    "__future__": "postponed annotations",
    "collections": "Mapping, Sequence and friends from collections.abc",
    "contextlib": "the write window's context manager",
    "dataclasses": "frozen value types",
    "enum": "StrEnum, the closed vocabularies: refusal codes and law cadences",
    "unicodedata": "a name's NFKC form and its letters' Unicode names (schema.Text); pure, no IO",
    "idna": "IDNA2008's code-point tables and contextual rules for a name's characters (schema.Text); pure, no IO",
    "hashlib": "sha256 for versioned content digests (simcore.core.digest); not the builtin hash()",
    "re": "the shape of a stored digest",
    "math": "scalar maths",
    "numbers": "Real and Integral, to refuse bools and strings posing as numbers",
    "reprlib": "the bounded echo",
    "types": "MappingProxyType, read-only mappings",
    "typing": "types only",
    "numpy": "the cells; its IO is refused by name in scripts/lint_inputs.py",
    "scipy": "special.ndtr and ndimage.label in the laws; scipy.io is refused by name in scripts/lint_inputs.py",
}
ALLOWED: dict[str, dict[str, str]] = {
    "simcore": {},
    "simcore.core": _NUMERIC,
    "simcore.adapters": {},
    "simcore.adapters.loaders": {
        "__future__": "postponed annotations",
        "collections": "Counter, to find a repeated key; Mapping and Sequence",
        "typing": "types only",
        "pathlib": "the file gate: it reads files from an explicit path",
        "yaml": "the file gate: strict YAML through a SafeLoader subclass",
        "re": "the bare-name check a DataPath joins with",
        "os": "the file gate opens a file once, non-blocking, and stats the descriptor (os.open, os.fstat)",
        "stat": "S_ISREG on the open descriptor: a data file is a regular file",
        "weakref": "WeakKeyDictionary: a DataPath's real path, held by the gate and never by the handle",
    },
    "simcore.adapters.sem": {
        "__future__": "postponed annotations",
        "collections": "Mapping",
        "dataclasses": "the mirror of Maxim's frozen types",
        "typing": "types only",
        "maxim": "the SEM membrane, the only engine code that imports maxim",
    },
    "simcore.protocol": {
        "__future__": "postponed annotations",
        "collections": "Mapping and Sequence",
        "dataclasses": "the rig profile's and the wire's frozen types",
        "math": "a grid's cell count (prod)",
        "numpy": "display quantization of a frame's arrays; a frame's arrays as bytes and back",
        "types": "MappingProxyType, read-only mappings",
    },
    # the wire's one JSON parser (boundaries §9.1): no other protocol module may import json
    "simcore.protocol.strict_json": {
        "__future__": "postponed annotations",
        "collections": "Sequence",
        "json": "the strict decoder's parser, with every hook set, and the encoder",
        "math": "isfinite, to refuse 1e400",
    },
    "simcore.verify": {
        "__future__": "postponed annotations",
        "collections": "Callable, Hashable and Sequence from collections.abc",
        "dataclasses": "the harness's frozen result types",
        "itertools": "pairwise, to check control values ascend",
        "math": "logarithms and finiteness for observed orders",
    },
    "maxim_overdrive": {},
    "maxim_overdrive.data": {
        "__future__": "postponed annotations",
        "re": "the rig-name check",
        "pathlib": "path arithmetic only (PATH_HOLDERS); the file gate opens the files",
    },
}

# Every external name each layer may reach, by its full dotted name (delta rounds 5 and 6, D5-S1, D6-S1). grimp
# records a module only at its top level, and an allowed module carries others with it (reprlib.builtins,
# contextlib.os, dataclasses.sys, numpy.lib.npyio), so the import list alone can't say what a layer reaches; this can.
# Counted from `from x import y` and from pure attribute chains, through aliases. A method on a value (an array, a
# path) is a stated blind spot. Anything not named here is refused; a test holds each set to exactly today's use.
# the core's types, scalar maths and arrays, and two scipy laws
_NAMES_CORE = frozenset({
    "__future__.annotations", "collections.abc.Callable", "collections.abc.Collection", "collections.abc.Iterable",
    "collections.abc.Iterator", "collections.abc.Mapping", "collections.abc.Sequence", "contextlib.contextmanager",
    "dataclasses.asdict", "dataclasses.dataclass", "dataclasses.field", "enum.StrEnum", "hashlib.sha256", "math.ceil",
    "math.inf", "math.isfinite", "math.log", "math.nan", "math.pi", "math.prod", "math.sqrt", "numbers.Integral",
    "numbers.Real", "numpy.all", "numpy.arange", "numpy.argmin", "numpy.argwhere", "numpy.array", "numpy.asarray",
    "numpy.bool_", "numpy.diff", "numpy.errstate", "numpy.flatnonzero", "numpy.float32", "numpy.float64",
    "numpy.floating", "numpy.floor", "numpy.frombuffer", "numpy.full", "numpy.generic", "numpy.inf", "numpy.integer",
    "numpy.intersect1d", "numpy.logical_and", "numpy.max", "numpy.mean", "numpy.take", "numpy.typing.NDArray",
    "numpy.uint8", "numpy.where", "numpy.zeros", "re.compile", "reprlib.Repr", "scipy.ndimage", "scipy.ndimage.label",
    "scipy.special.ndtr", "types.MappingProxyType", "typing.Any", "typing.Literal", "typing.Protocol",
    "typing.SupportsFloat", "idna.IDNAError", "idna.check_label", "unicodedata.category", "unicodedata.digit",
    "unicodedata.name", "unicodedata.normalize",
})  # fmt: skip

# the file gate: paths, and strict YAML through a SafeLoader subclass
_NAMES_LOADERS = frozenset({
    "__future__.annotations", "collections.Counter", "collections.abc.Sequence", "os.O_NOCTTY", "os.O_NONBLOCK",
    "os.O_RDONLY", "os.close", "os.fdopen", "os.fstat", "os.open", "pathlib.Path", "re.compile", "stat.S_ISREG",
    "weakref.WeakKeyDictionary", "typing.Any", "yaml.MappingNode", "yaml.SafeLoader", "yaml.YAMLError", "yaml.load",
    "yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG",
})  # fmt: skip

# the membrane: Maxim's frozen SEM types, and their mirror
_NAMES_SEM = frozenset({
    "__future__.annotations", "collections.abc.Mapping", "dataclasses.dataclass", "dataclasses.field",
    "maxim.embodiment.sem.AffordanceSchema", "maxim.embodiment.sem.Entity", "maxim.embodiment.sem.ModulatorResult",
    "maxim.embodiment.sem.SensorReading", "typing.Any", "typing.TYPE_CHECKING",
})  # fmt: skip

# display quantization and the rig profile's type
_NAMES_PROTOCOL = frozenset({
    "__future__.annotations", "collections.abc.Mapping", "collections.abc.Sequence", "dataclasses.dataclass",
    "math.prod", "numpy.ascontiguousarray", "numpy.clip", "numpy.dtype", "numpy.float16", "numpy.frombuffer",
    "numpy.generic", "numpy.round", "numpy.typing.NDArray", "numpy.uint8", "types.MappingProxyType",
})  # fmt: skip

# the wire's strict JSON: its parser with every hook set, and finiteness
_NAMES_STRICT_JSON = frozenset({
    "__future__.annotations", "collections.abc.Sequence", "json.JSONDecodeError", "json.dumps", "json.loads",
    "math.isfinite",
})  # fmt: skip

# the harness: frozen results, observed orders by logarithm
_NAMES_VERIFY = frozenset({
    "__future__.annotations", "collections.abc.Callable", "collections.abc.Hashable", "collections.abc.Sequence",
    "dataclasses.dataclass", "itertools.pairwise", "math.inf", "math.isfinite", "math.log", "math.nan",
})  # fmt: skip

# path arithmetic and the rig-name check
_NAMES_DATA = frozenset({
    "__future__.annotations", "pathlib.Path", "re.compile",
})  # fmt: skip
EXTERNAL_NAMES: dict[str, frozenset[str]] = {
    "simcore.core": _NAMES_CORE,
    "simcore.adapters.loaders": _NAMES_LOADERS,
    "simcore.adapters.sem": _NAMES_SEM,
    "simcore.protocol": _NAMES_PROTOCOL,
    "simcore.protocol.strict_json": _NAMES_STRICT_JSON,
    "simcore.verify": _NAMES_VERIFY,
    "maxim_overdrive.data": _NAMES_DATA,
}


def external_names(source: str) -> set[str]:
    """The external names a module reaches: imported (``from scipy.special import ndtr``) or used as a pure attribute
    chain (``reprlib.builtins.open``), resolved through its import aliases. Internal (simcore) names are not counted
    here; ``internal_reexports`` holds those."""
    tree = ast.parse(source)
    bound = {"np": "numpy", **_bindings(tree)}  # np is numpy even unimported, as the lint reads it
    inner = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    out = {
        f"{node.module}.{a.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 and not _internal(node.module)
        for a in node.names
    }
    for node in ast.walk(tree):
        if id(node) in inner or not isinstance(node, ast.Attribute | ast.Name):
            continue
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            continue
        dotted = _dotted(node, bound)
        if dotted and not _internal(dotted):
            out.add(dotted)
    return out


def external_name_violations(module: str, source: str) -> list[str]:
    allowed = EXTERNAL_NAMES.get(_layer(module), frozenset())
    return [
        f"{module} reaches {n}, which {_layer(module)}'s name list doesn't name"
        for n in sorted(external_names(source) - allowed)
    ]


# Gate modules: code elsewhere imports from these only the names in their __all__.
GATES = ("simcore.adapters.loaders", "maxim_overdrive.data")

# The modules that hold a path for the game, and every attribute each may use (delta rounds 4 and 5): path
# arithmetic, and the few calls each makes on values that aren't paths. Any other method on a path could open it.
# resolve is not here: it reads the filesystem (realpath), so the file gate does it (loaders.existing_directory).
PATH_ARITHMETIC = {"parent", "parents", "name", "stem", "suffix", "with_suffix", "joinpath"}
PATH_HOLDERS: dict[str, dict[str, str]] = {
    "maxim_overdrive.data": {
        "BAD_NAME": "RefusalCode.BAD_NAME, the rig-name refusal's code",
        "compile": "re.compile, the rig-name pattern",
        "fullmatch": "RIG_NAME.fullmatch, the name check",
        "load": "RigProfile.load, which hands the path on",
    },
    "simcore.protocol.tiers": {
        "check": "RIG_PROFILE.schema.check, the constructor's field rules",
        "from_document": "RigProfile.from_document, which builds from a read document",
        "name": "the profile's own name field",
        "read": "RIG_PROFILE.read, the format's reader of the parsed document (no file: read_yaml opened it)",
        "schema": "RIG_PROFILE.schema",
    },
}


_GRAPH = """
import grimp, json, sys
pkgs = sys.argv[1:]
g = grimp.build_graph(*pkgs, include_external_packages=True, cache_dir=None)
internal = {m for m in g.modules if m.split(".")[0] in pkgs}
print(json.dumps({m: sorted(g.find_modules_directly_imported_by(m) - internal) for m in sorted(internal)}))
"""


def external_imports(tree: Path) -> dict[str, list[str]]:
    """Each module of the packages under ``tree/src`` -> the external modules it imports directly, from grimp."""
    env = {**os.environ, "PYTHONPATH": str(tree / "src")}
    run = subprocess.run(
        [sys.executable, "-c", _GRAPH, *PACKAGES], cwd=tree, env=env, capture_output=True, text=True, check=True
    )
    graph: dict[str, list[str]] = json.loads(run.stdout)
    return graph


def _layer(module: str) -> str:
    parts = module.split(".")
    return next(".".join(parts[:i]) for i in range(len(parts), 0, -1) if ".".join(parts[:i]) in ALLOWED)


def allowlist_violations(imports: dict[str, list[str]]) -> list[str]:
    return [
        f"{module} imports {ext}, which {_layer(module)}'s allowlist doesn't name"
        for module, externals in imports.items()
        for ext in externals
        if ext not in ALLOWED[_layer(module)]
    ]


def _gate_all(module: str) -> set[str]:
    return set(importlib.import_module(module).__all__)


def _bindings(tree: ast.Module) -> dict[str, str]:
    """Local name -> the module path it stands for: ``import a.b as c`` gives c -> a.b, ``import a.b`` gives a -> a,
    ``from a import b`` gives b -> a.b."""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {
                (a.asname or a.name.split(".")[0]): (a.name if a.asname else a.name.split(".")[0]) for a in node.names
            }
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out |= {(a.asname or a.name): f"{node.module}.{a.name}" for a in node.names}
    return out


def _dotted(node: ast.AST, bound: dict[str, str]) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name) and node.id in bound:
        return ".".join([bound[node.id], *reversed(parts)])
    return None


def gate_reexports(module: str, source: str) -> list[str]:
    """Names a non-gate module takes from a gate that the gate's ``__all__`` doesn't offer, by any route
    ``internal_reexports`` follows: ``from gate import x``, ``gate.x``, ``getattr(gate, 'x')`` (delta rounds 4, 5)."""
    if module in GATES:
        return []
    tree = ast.parse(source)
    return sorted(
        {
            f"{module} takes {names[0]} from {start}"
            for start, names, _ in _routes(tree, _bindings(tree))
            for gate in GATES
            if start == gate and names[0] not in _gate_all(gate)
        }
    )


def _defined(module: str) -> set[str]:
    """Names a module defines itself (``def``, ``class``, assignment, at its top level or inside a top-level ``if`` or
    ``try``), plus its ``__all__``: what may be imported from it."""
    mod = importlib.import_module(module)
    tree = ast.parse(Path(mod.__file__ or "").read_text())
    out = set(getattr(mod, "__all__", ()))
    stack: list[ast.stmt] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            out.add(node.name)
        elif isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            out |= {n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)}
        elif isinstance(node, ast.TypeAlias):
            out.add(node.name.id)
        elif isinstance(node, ast.If | ast.Try):
            stack += [
                *node.body,
                *node.orelse,
                *getattr(node, "finalbody", []),
                *(h for x in getattr(node, "handlers", []) for h in x.body),
            ]
    return out


def _internal(name: str) -> bool:
    return name.split(".", maxsplit=1)[0] in PACKAGES


def _hop(module: str, name: str) -> str | None:
    """``module.name``: the submodule it names, or None when ``module`` defines it; KeyError when it is neither."""
    obj = getattr(importlib.import_module(module), name, None)
    if isinstance(obj, types.ModuleType) and obj.__name__ == f"{module}.{name}":  # its own submodule, not numpy
        return f"{module}.{name}"
    if name in _defined(module):
        return None
    raise KeyError(name)


def _routes(tree: ast.Module, bound: dict[str, str]) -> list[tuple[str, list[str], int]]:
    """Every (internal module, names taken from it in turn, line): ``from m import n``, the longest module prefix of an
    attribute chain, and ``getattr(module, 'n')`` with a literal name."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and _internal(node.module) and node.level == 0:
            out += [(node.module, [a.name], node.lineno) for a in node.names]
        elif isinstance(node, ast.Attribute) and (dotted := _dotted(node, bound)):
            parts = dotted.split(".")
            prefix = next((i for i in range(len(parts) - 1, 0, -1) if _is_internal_module(".".join(parts[:i]))), None)
            if prefix is not None:
                out.append((".".join(parts[:prefix]), parts[prefix:], node.lineno))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr":
            target = _dotted(node.args[0], bound) if node.args else None
            literal = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else None
            if target and _is_internal_module(target) and isinstance(literal, str):
                out.append((target, [literal], node.lineno))
    return out


def internal_reexports(module: str, source: str) -> list[str]:
    """A name taken from an internal module that it neither defines nor lists in ``__all__``: something it imported
    itself, re-exported (delta round 5, D5-S2: ``from simcore.core.grid import np`` gave the membrane numpy)."""
    tree = ast.parse(source)
    out = set()
    for start, names, line in _routes(tree, _bindings(tree)):
        current: str | None = start
        for name in names:
            if current is None:
                break
            try:
                current = _hop(current, name)
            except KeyError:
                out.add(f"{module}:{line}: takes {name} from {current}, which only imports it")
                break
    return sorted(out)


def _is_internal_module(name: str) -> bool:
    return _internal(name) and _is_module(name)


def _is_module(name: str) -> bool:
    try:
        importlib.import_module(name)
    except ImportError:
        return False
    return True


def path_holder_violations(module: str, source: str) -> list[str]:
    """Attributes a path-holding module uses beyond its allowlist, by attribute or by ``getattr`` with a literal
    name: any path method but arithmetic could open the path it holds (delta round 5, Executor N-g)."""
    allowed = PATH_ARITHMETIC | set(PATH_HOLDERS[module])
    tree = ast.parse(source)
    used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    used |= {
        n.args[1].value
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "getattr"
        and len(n.args) > 1
        and isinstance(n.args[1], ast.Constant)
        and isinstance(n.args[1].value, str)
    }
    return sorted(f"{module} uses .{a}" for a in used - allowed)
