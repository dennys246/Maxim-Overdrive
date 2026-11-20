"""Untrusted input by source, fail closed (boundaries §5.2, B-4; step 3b delta round 4).

Three allowlists, each a set of names with a reason, so a new input route is refused until someone names it:

- **External imports per layer** (``ALLOWED``), read from grimp's graph, the graph import-linter checks. grimp
  records an external package at its top level (``numpy.lib.npyio`` is recorded as ``numpy``), so numpy's and scipy's
  IO submodules can't be told apart here; ``scripts/lint_inputs.py`` covers them by name.
- **What non-gate code may import from a gate** (``GATES``): the gate module's ``__all__``. Nothing else, so a gate's
  own imports (``pathlib``, ``yaml``) can't be re-exported through it.
- **The attributes ``maxim_overdrive.data`` may use** (``DATA_ATTRIBUTES``): path arithmetic, so the module that holds
  ``pathlib`` for the game opens nothing; the file gate does.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

PACKAGES = ("simcore", "maxim_overdrive")

# Each layer's allowed external modules, with the reason. The most specific key holds for a module.
_NUMERIC = {
    "__future__": "postponed annotations",
    "collections": "Mapping, Sequence and friends from collections.abc",
    "contextlib": "the write window's context manager",
    "dataclasses": "frozen value types",
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
        "collections": "Mapping",
        "dataclasses": "the rig profile's frozen type",
        "numpy": "display quantization of a frame's arrays",
    },
    "maxim_overdrive": {},
    "maxim_overdrive.data": {
        "__future__": "postponed annotations",
        "re": "the rig-name check",
        "pathlib": "path arithmetic only (DATA_ATTRIBUTES); the file gate opens the files",
    },
}

# Gate modules: code elsewhere imports from these only the names in their __all__.
GATES = ("simcore.adapters.loaders", "maxim_overdrive.data")

# Every attribute maxim_overdrive.data may use: path arithmetic, and the two calls it makes on non-paths.
PATH_ARITHMETIC = {"parent", "parents", "name", "stem", "suffix", "with_suffix", "joinpath", "resolve"}
DATA_CALLS = {
    "compile": "re.compile, the rig-name pattern",
    "fullmatch": "RIG_NAME.fullmatch, the name check",
    "load": "RigProfile.load, which hands the path on",
}
DATA_ATTRIBUTES = PATH_ARITHMETIC | set(DATA_CALLS)

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
    """Names a non-gate module takes from a gate that the gate's ``__all__`` doesn't offer: ``from gate import x``,
    or ``gate.x`` through any import of the gate's module (delta round 4, D4-S2)."""
    if module in GATES:
        return []
    tree = ast.parse(source)
    bound, out = _bindings(tree), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in GATES:
            out |= {
                f"{module} takes {a.name} from {node.module}"
                for a in node.names
                if a.name not in _gate_all(node.module)
            }
        elif isinstance(node, ast.Attribute) and (dotted := _dotted(node, bound)):
            for gate in GATES:
                rest = dotted.removeprefix(gate + ".").split(".")[0] if dotted.startswith(gate + ".") else None
                if rest is not None and rest not in _gate_all(gate):
                    out.add(f"{module} takes {rest} from {gate}")
    return sorted(out)


def data_attribute_violations(source: str) -> list[str]:
    """Attributes maxim_overdrive.data uses beyond its allowlist: any Path method but arithmetic opens something."""
    return sorted(
        {
            f"maxim_overdrive.data uses .{n.attr}"
            for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.Attribute) and n.attr not in DATA_ATTRIBUTES
        }
    )
