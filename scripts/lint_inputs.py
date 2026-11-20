"""Standards check 5: untrusted input is guarded at its sources (boundaries §5.2, B-4).

Two rules, read from the syntax tree so spacing, aliases and line breaks can't hide a call:

- **Input primitives by module.** Only a gate module in ``INPUT_GATES`` may read a file, parse YAML or JSON, load a
  numpy file, read the environment or the command line, or receive from a transport. Everywhere else in ``src/`` such
  a call is a finding. ``pyproject.toml``'s ``input-primitives`` import contract holds the imports; this holds the
  calls an import can't show (builtin ``open``, ``Path.read_text``, ``np.load``, ``os.environ``).
- **Unsafe decoders, everywhere** (``src/``, ``scripts/``, ``tests/``): ``pickle``, ``marshal`` and ``shelve``,
  ``yaml.load`` without a ``SafeLoader`` (or a subclass defined beside it), ``yaml``'s unsafe loaders,
  ``np.load(allow_pickle=True)``, and ``eval`` and ``exec``.
"""

from __future__ import annotations

import ast

# The modules that may read input, each with what it reads. A new gate joins this list and the gate registry
# (lint_gates.py) in the change that makes it.
INPUT_GATES = {"src/simcore/adapters/loaders.py": "the file gates: strict YAML from an explicit path"}

READ_CALLS = {"open", "input"}  # builtins that read a file or stdin
READ_METHODS = {"read_text", "read_bytes", "open", "recv", "recv_into", "recvfrom"}  # Path, sockets, websockets
READ_FUNCTIONS = {
    "json.load",
    "json.loads",
    "np.load",
    "numpy.load",
    "np.loadtxt",
    "np.genfromtxt",
    "np.fromfile",
    "os.getenv",
    "os.getenvb",
}
READ_NAMES = {"os.environ", "os.environb", "sys.argv", "sys.stdin", "environ", "getenv"}
UNSAFE_MODULES = {"pickle", "marshal", "shelve", "dill", "cloudpickle"}
UNSAFE_YAML = {"unsafe_load", "unsafe_load_all", "full_load", "full_load_all", "Loader", "UnsafeLoader", "FullLoader"}
SAFE_LOADERS = {"SafeLoader", "CSafeLoader"}


def _dotted(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return ".".join([node.id, *reversed(parts)])
    return None


def _safe_loader_classes(tree: ast.Module) -> set[str]:
    """Classes defined in this module whose bases include a yaml SafeLoader."""
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and any((_dotted(b) or "").split(".")[-1] in SAFE_LOADERS for b in node.bases)
    }


def _yaml_load_is_safe(call: ast.Call, safe: set[str]) -> bool:
    loader = next((k.value for k in call.keywords if k.arg == "Loader"), call.args[1] if len(call.args) > 1 else None)
    name = (_dotted(loader) or "").split(".")[-1] if loader is not None else ""
    return name in SAFE_LOADERS or name in safe


def _unsafe_call(call: ast.Call, safe: set[str]) -> str | None:
    name = _dotted(call.func) or ""
    if name in ("eval", "exec"):
        return f"calls {name}"
    if name in ("yaml.load", "yaml.load_all") and not _yaml_load_is_safe(call, safe):
        return f"calls {name} without a SafeLoader"
    allow = next((k.value for k in call.keywords if k.arg == "allow_pickle"), None)
    if name.split(".")[-1] == "load" and isinstance(allow, ast.Constant) and allow.value is True:
        return f"calls {name}(allow_pickle=True)"
    return None


def unsafe_findings(rel: str, source: str) -> list[str]:
    """Unsafe decoders and code execution, banned in every Python file of the repository."""
    tree = ast.parse(source)
    safe = _safe_loader_classes(tree)
    out = []
    for node in ast.walk(tree):
        hit = None
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            banned = [n for n in names if n.split(".")[0] in UNSAFE_MODULES]
            hit = f"imports {banned[0]}" if banned else None
        elif isinstance(node, ast.Attribute) and _dotted(node) in {f"yaml.{n}" for n in UNSAFE_YAML}:
            hit = f"uses {_dotted(node)}"
        elif isinstance(node, ast.Call):
            hit = _unsafe_call(node, safe)
        if hit:
            out.append(f"{rel}:{getattr(node, 'lineno', 0)}: {hit} (banned everywhere, boundaries §5.2)")
    return out


def _read_hit(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        name = _dotted(node.func) or ""
        if name in READ_CALLS or name in READ_FUNCTIONS or name.startswith("yaml."):
            return f"calls {name}"
        if isinstance(node.func, ast.Attribute) and node.func.attr in READ_METHODS:
            return f"calls .{node.func.attr}()"
    if isinstance(node, ast.Attribute | ast.Name) and _dotted(node) in READ_NAMES:
        return f"reads {_dotted(node)}"
    return None


def input_findings(rel: str, source: str) -> list[str]:
    """Input primitives in a ``src/`` module that is not an input gate."""
    if not rel.startswith("src/") or rel in INPUT_GATES:
        return []
    out = []
    for node in ast.walk(ast.parse(source)):
        hit = _read_hit(node)
        if hit:
            out.append(f"{rel}:{getattr(node, 'lineno', 0)}: {hit}: only an input gate reads input (boundaries §5.2)")
    return out


def check_inputs(files: dict[str, str]) -> list[str]:
    problems = []  # an input gate that does not exist is the gate registry's finding (lint_gates.py)
    for rel, text in sorted(files.items()):
        if rel.endswith(".py"):
            problems += unsafe_findings(rel, text) + input_findings(rel, text)
    return problems
