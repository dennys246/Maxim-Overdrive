"""Standards check 5: untrusted input is guarded at its sources (boundaries §5.2, B-4).

Two rules, read from the syntax tree:

- **Input primitives by module.** Only a gate module in ``INPUT_GATES`` may read a file, parse YAML, JSON, TOML,
  plists or INI files, load a numpy file, read the environment, the command line or stdin, or receive from a
  transport. Elsewhere in ``src/`` such a call is a finding, and in ``src/simcore/`` so is dynamic import
  (``importlib``, ``__import__``) and ``getattr`` with a computed name, which could reach any of them.
  ``pyproject.toml``'s ``input-primitives`` import contract holds the imports too.
- **Unsafe decoders, everywhere** (``src/``, ``scripts/``, ``tests/``): ``pickle``, ``_pickle``, ``marshal``,
  ``shelve``, ``dill`` and ``cloudpickle``; ``yaml.load`` without a ``SafeLoader`` (or a subclass defined beside it);
  ``yaml``'s unsafe loaders and loader classes; any ``allow_pickle`` that is not a literal ``False``, and a
  ``numpy.load`` given ``**`` arguments; ``eval`` and ``exec`` named directly (a call, ``builtins.eval``, an alias
  such as ``e = eval``), and the builtins table read by name (``__builtins__``, ``vars(builtins)``,
  ``builtins.__dict__``); ``getattr`` on ``yaml``, ``pickle``, ``marshal``, ``builtins`` or ``importlib``;
  ``importlib.import_module`` or ``__import__`` of an unsafe module by name; and a yaml constructor registration that
  names ``yaml.constructor``. A call is judged even when its result is used through an attribute
  (``np.load(p, allow_pickle=True).item()``).

What it sees: names as imported, so ``import yaml as y``, ``from yaml import unsafe_load as u`` and
``from os import environ`` resolve to what they are, and ``np`` is numpy. What it doesn't: a value passed through a
variable, a container or a function (``f = yaml.unsafe_load`` is caught because naming it is; ``f = pick(yaml)`` is
not), ``getattr`` with a computed name outside ``src/simcore/``, a Python constructor registered without naming
``yaml.constructor``, and code built at run time. It guards mistakes, not adversaries.
"""

from __future__ import annotations

import ast

# The modules that may read input, each with what it reads. A new gate joins this list and the gate registry
# (lint_gates.py) in the change that makes it.
INPUT_GATES = {"src/simcore/adapters/loaders.py": "the file gates: strict YAML from an explicit path"}

READ_CALLS = {"open", "input", "builtins.open", "builtins.input"}  # builtins that read a file or stdin
READ_METHODS = {"read_text", "read_bytes", "open", "recv", "recv_into", "recvfrom"}  # Path, sockets, websockets
READ_FUNCTIONS = {
    "json.load",
    "json.loads",
    "tomllib.load",
    "tomllib.loads",
    "plistlib.load",
    "plistlib.loads",
    "configparser.ConfigParser",
    "configparser.RawConfigParser",
    "fileinput.input",
    "numpy.load",
    "numpy.loadtxt",
    "numpy.genfromtxt",
    "numpy.fromfile",
    "os.getenv",
    "os.getenvb",
}
READ_NAMES = {"os.environ", "os.environb", "sys.argv", "sys.stdin", "os.getenv", "environ", "getenv"}
UNSAFE_MODULES = {"pickle", "_pickle", "marshal", "shelve", "dill", "cloudpickle"}
UNSAFE_YAML = {
    "unsafe_load", "unsafe_load_all", "full_load", "full_load_all", "Loader", "UnsafeLoader", "FullLoader",
    "CLoader", "CUnsafeLoader", "CFullLoader",
}  # fmt: skip
UNSAFE_NAMES = {f"yaml.{n}" for n in UNSAFE_YAML} | {
    "eval", "exec", "builtins.eval", "builtins.exec", "__builtins__", "builtins.__dict__",
}  # fmt: skip
SAFE_LOADERS = {"SafeLoader", "CSafeLoader"}
GETATTR_UNSAFE_ROOTS = {"yaml", "builtins", "importlib", *UNSAFE_MODULES}
DYNAMIC_IMPORTS = {"importlib.import_module", "__import__", "builtins.__import__"}


def _dotted(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return ".".join([node.id, *reversed(parts)])
    return None


def aliases(tree: ast.Module) -> dict[str, str]:
    """Local name -> what it names: ``import yaml as y`` gives y -> yaml, ``from os import environ`` gives environ
    -> os.environ. ``np`` is numpy even unimported, as everywhere in this repository."""
    out = {"np": "numpy"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {
                (a.asname or a.name.split(".")[0]): (a.name if a.asname else a.name.split(".")[0]) for a in node.names
            }
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out |= {(a.asname or a.name): f"{node.module}.{a.name}" for a in node.names}
    return out


def _canonical(node: ast.AST, table: dict[str, str]) -> str:
    dotted = _dotted(node) or ""
    head, _, rest = dotted.partition(".")
    resolved = table.get(head, head)
    return f"{resolved}.{rest}" if rest else resolved


def _inner(tree: ast.Module) -> set[int]:
    """The names and attributes inside a longer attribute chain, judged once at the chain's end. Never a call: a
    call whose result is used through an attribute (``np.load(p).copy()``) is judged itself (delta review, D-B1)."""
    return {
        id(n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute | ast.Name)
    }


def _safe_loader_classes(tree: ast.Module) -> set[str]:
    """Classes defined in this module whose bases include a yaml SafeLoader."""
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and any((_dotted(b) or "").split(".")[-1] in SAFE_LOADERS for b in node.bases)
    }


def _literal(node: ast.AST | None) -> object:
    return node.value if isinstance(node, ast.Constant) else ...


def _unsafe_yaml(call: ast.Call, name: str, table: dict[str, str], safe: set[str]) -> str | None:
    if name in ("yaml.load", "yaml.load_all"):
        positional = call.args[1] if len(call.args) > 1 else None
        loader = next((k.value for k in call.keywords if k.arg == "Loader"), positional)
        last = _canonical(loader, table).split(".")[-1] if loader is not None else ""
        return None if last in SAFE_LOADERS or last in safe else f"calls {name} without a SafeLoader"
    registers = name.rsplit(".", maxsplit=1)[-1] in (
        "add_constructor",
        "add_multi_constructor",
        "add_multi_representer",
    )
    named = (_canonical(a, table) for a in ast.walk(call) if isinstance(a, ast.Attribute))
    if registers and any("yaml.constructor" in n for n in named):
        return f"registers one of yaml's Python constructors through {name}"
    return None


def _unsafe_pickle(call: ast.Call, name: str) -> str | None:
    positional = call.args[2] if name == "numpy.load" and len(call.args) > 2 else None  # load(file, mmap, pickle)
    allow = next((k.value for k in call.keywords if k.arg == "allow_pickle"), positional)
    if allow is not None and _literal(allow) is not False:
        return f"calls {name} with allow_pickle that is not a literal False"
    if name == "numpy.load" and any(k.arg is None for k in call.keywords):
        return "calls numpy.load with ** arguments, which can carry allow_pickle"
    return None


def _unsafe_reach(call: ast.Call, name: str, table: dict[str, str]) -> str | None:
    """Reaching an unsafe module or builtin by name: a dynamic import, ``vars(builtins)``, ``getattr``."""
    target = _literal(call.args[0]) if call.args else None
    if name in DYNAMIC_IMPORTS and isinstance(target, str) and target.split(".")[0] in UNSAFE_MODULES:
        return f"imports {target} by name"
    on = _canonical(call.args[0], table) if call.args else ""
    if name in ("vars", "builtins.vars") and on == "builtins":
        return "reads builtins by name through vars()"
    if name in ("getattr", "builtins.getattr") and on.split(".")[0] in GETATTR_UNSAFE_ROOTS:
        return f"calls getattr on {on}"
    return None


def _unsafe_call(call: ast.Call, table: dict[str, str], safe: set[str]) -> str | None:
    name = _canonical(call.func, table)
    return _unsafe_yaml(call, name, table, safe) or _unsafe_pickle(call, name) or _unsafe_reach(call, name, table)


def _unsafe_node(node: ast.AST, table: dict[str, str], safe: set[str]) -> str | None:
    if isinstance(node, ast.Import | ast.ImportFrom):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
        banned = [n for n in names if n.split(".")[0] in UNSAFE_MODULES]
        return f"imports {banned[0]}" if banned else None
    if isinstance(node, ast.Call):
        return _unsafe_call(node, table, safe)
    if isinstance(node, ast.Attribute | ast.Name) and isinstance(node.ctx, ast.Load):
        name = _canonical(node, table)
        return f"names {name}" if name in UNSAFE_NAMES else None
    return None


def unsafe_findings(rel: str, source: str) -> list[str]:
    """Unsafe decoders and code execution, banned in every Python file of the repository."""
    tree = ast.parse(source)
    table, safe = aliases(tree), _safe_loader_classes(tree)
    inner = _inner(tree)
    out = []
    for node in ast.walk(tree):
        if id(node) in inner:
            continue
        if hit := _unsafe_node(node, table, safe):
            out.append(f"{rel}:{getattr(node, 'lineno', 0)}: {hit} (banned everywhere, boundaries §5.2)")
    return out


def _read_call(call: ast.Call, table: dict[str, str], engine: bool) -> str | None:
    name = _canonical(call.func, table)
    if name in READ_CALLS or name in READ_FUNCTIONS or name.startswith("yaml."):
        return f"calls {name}"
    if isinstance(call.func, ast.Attribute) and call.func.attr in READ_METHODS:
        return f"calls .{call.func.attr}()"
    if engine and name in DYNAMIC_IMPORTS:
        return f"calls {name}: a dynamic import can reach any input"
    computed = len(call.args) > 1 and not isinstance(_literal(call.args[1]), str)
    if engine and name in ("getattr", "builtins.getattr") and computed:
        return "calls getattr with a computed name"
    return None


def _read_hit(node: ast.AST, table: dict[str, str], engine: bool) -> str | None:
    if isinstance(node, ast.Call):
        return _read_call(node, table, engine)
    if isinstance(node, ast.Attribute | ast.Name) and _canonical(node, table) in READ_NAMES:
        return f"reads {_canonical(node, table)}"
    if engine and isinstance(node, ast.Import | ast.ImportFrom):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
        return "imports importlib" if any(n.split(".")[0] == "importlib" for n in names) else None
    return None


def input_findings(rel: str, source: str) -> list[str]:
    """Input primitives in a ``src/`` module that is not an input gate."""
    if not rel.startswith("src/") or rel in INPUT_GATES:
        return []
    tree = ast.parse(source)
    table, engine = aliases(tree), rel.startswith("src/simcore/")
    inner = _inner(tree)
    out = []
    for node in ast.walk(tree):
        if id(node) not in inner and (hit := _read_hit(node, table, engine)):
            out.append(f"{rel}:{getattr(node, 'lineno', 0)}: {hit}: only an input gate reads input (boundaries §5.2)")
    return out


def check_inputs(files: dict[str, str]) -> list[str]:
    problems = []  # an input gate that does not exist is the gate registry's finding (lint_gates.py)
    for rel, text in sorted(files.items()):
        if rel.endswith(".py"):
            problems += unsafe_findings(rel, text) + input_findings(rel, text)
    return problems
