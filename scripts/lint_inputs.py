"""Standards check 5: untrusted input is guarded at its sources (boundaries §5.2, B-4).

One algorithm. Every name, attribute, subscript and call in a file is canonicalized to a dotted name, and every
dotted prefix of it is matched against two tables. No node is skipped, so a name can't hide inside a longer chain
(``os.environ.get`` matches ``os.environ``) and a call can't hide behind the attribute read from its result
(``open(p).read()`` matches ``builtins.open``).

Canonicalizing resolves:
- import aliases: ``import yaml as y``, ``from os import environ``, ``from importlib import import_module as im``; and
  ``np`` is numpy;
- builtins by any name: ``eval``, ``__builtins__.eval``, ``__builtins__['eval']``, ``vars(builtins)['eval']``,
  ``builtins.__dict__['eval']``, ``builtins.__dict__.get('eval')`` and ``globals()['__builtins__']`` are all
  ``builtins.eval``;
- modules by name: ``sys.modules['pickle']``, ``importlib.import_module('pickle')``, ``__import__('pickle')`` and
  ``importlib.__import__('pickle')`` are ``pickle``; ``getattr(x, 'name')`` is ``x.name``;
- a literal key or ``.get`` of a literal: ``os.environ['X']`` and ``os.environ.get('X')`` are ``os.environ.X``.

The rules:
- **Unsafe decoders, everywhere** (``src/``, ``scripts/``, ``tests/``): a name with a prefix in ``UNSAFE``;
  ``yaml.load`` without a ``SafeLoader`` (or a subclass defined beside it); an ``allow_pickle`` (by keyword, or
  third by position to ``numpy.load``) that is not a literal ``False``; ``numpy.load`` given ``**`` arguments; and
  ``getattr`` with a computed name on a module in ``GETATTR_UNSAFE_ROOTS``.
- **Input primitives, in ``src/`` outside ``INPUT_GATES``:** a name with a prefix in ``INPUT``; a call of a method in
  ``READ_METHODS`` on anything; and, in ``src/simcore/``, a name with a prefix in ``DYNAMIC`` or ``getattr`` with a
  computed name.

What it can't see: a value passed through a variable (other than an import alias), a container other than a literal
subscript, or a function's result (``f = pick(yaml)``); a computed name outside ``src/simcore/``; a yaml constructor
registered without naming ``yaml.constructor``; and code built at run time. It guards mistakes, not adversaries.
``tests/test_lint_inputs_corpus.py`` holds every spelling any review reported, each with its verdict.
"""

from __future__ import annotations

import ast

# The modules that may read input, each with what it reads. A new gate joins this list and the gate registry
# (lint_gates.py) in the change that makes it.
INPUT_GATES = {"src/simcore/adapters/loaders.py": "the file gates: strict YAML from an explicit path"}

UNSAFE = {
    "pickle", "_pickle", "marshal", "shelve", "dill", "cloudpickle", "multiprocessing.reduction",
    "yaml.unsafe_load", "yaml.unsafe_load_all", "yaml.full_load", "yaml.full_load_all", "yaml.Loader",
    "yaml.UnsafeLoader", "yaml.FullLoader", "yaml.CLoader", "yaml.CUnsafeLoader", "yaml.CFullLoader",
    "yaml.constructor", "builtins.eval", "builtins.exec",
}  # fmt: skip
INPUT = {
    "builtins.open", "builtins.input", "io.open", "codecs.open", "json", "yaml", "tomllib", "plistlib",
    "configparser", "fileinput", "numpy.load", "numpy.loadtxt", "numpy.genfromtxt", "numpy.fromfile",
    "os.environ", "os.environb", "os.getenv", "os.getenvb", "sys.argv", "sys.stdin", "environ", "getenv",
}  # fmt: skip
DYNAMIC = {"importlib", "builtins.__import__"}  # in src/simcore: an import by computed name can reach any input
READ_METHODS = {"read_text", "read_bytes", "open", "recv", "recv_into", "recvfrom"}  # Path, sockets, websockets
SAFE_LOADERS = {"SafeLoader", "CSafeLoader"}
GETATTR_UNSAFE_ROOTS = {"yaml", "builtins", "importlib", "pickle", "_pickle", "marshal", "shelve"}
IMPORTERS = {"importlib.import_module", "builtins.__import__", "importlib.__import__"}
NAMESPACES = {"builtins.vars", "builtins.globals", "builtins.locals"}  # vars(x) is x's names; globals() the module's
BUILTINS = {"open", "input", "eval", "exec", "__import__", "getattr", "vars", "globals", "locals", "compile"}


def aliases(tree: ast.Module) -> dict[str, str]:
    """Local name -> what it names: ``import yaml as y`` gives y -> yaml, ``from os import environ`` gives environ
    -> os.environ. ``np`` is numpy and ``__builtins__`` is builtins even unimported."""
    out = {"np": "numpy", "__builtins__": "builtins"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                out[a.asname or root] = a.name if a.asname else root
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out |= {(a.asname or a.name): f"{node.module}.{a.name}" for a in node.names}
    return out


def _literal(node: ast.AST | None) -> object:
    return node.value if isinstance(node, ast.Constant) else ...


class _Names:
    """Canonical dotted names of expressions in one module."""

    def __init__(self, table: dict[str, str]) -> None:
        self.table = table

    def of(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return self.name(node.id)
        if isinstance(node, ast.Attribute):
            base = self.of(node.value)
            if base is None:
                return None
            return base if node.attr == "__dict__" else f"{base}.{node.attr}"
        if isinstance(node, ast.Subscript):
            return self._member(self.of(node.value), node.slice)
        if isinstance(node, ast.Call):
            return self._call(node)
        return None

    def name(self, ident: str) -> str:
        if ident in self.table:
            return self.table[ident]
        return f"builtins.{ident}" if ident in BUILTINS else ident

    def _member(self, base: str | None, key: ast.AST) -> str | None:
        """``base[key]`` or ``base.get(key)``: a module by name from ``sys.modules``, a name from a namespace."""
        if base is None:
            return None
        literal = _literal(key)
        if not isinstance(literal, str):
            return base
        if base == "sys.modules":
            return literal
        if base == "<module>":
            return self.name(literal)
        return f"{base}.{literal}"

    def _call(self, call: ast.Call) -> str | None:
        func = self.of(call.func)
        first = call.args[0] if call.args else None
        if func in IMPORTERS and isinstance(_literal(first), str):
            return str(_literal(first))
        if func in NAMESPACES:
            return self.of(first) if first is not None else "<module>"
        if func == "builtins.getattr" and len(call.args) > 1:
            return self._member(self.of(call.args[0]), call.args[1])
        if isinstance(call.func, ast.Attribute) and call.func.attr == "get" and first is not None:
            return self._member(self.of(call.func.value), first)
        return func


def _prefixes(name: str) -> list[str]:
    parts = name.split(".")
    return [".".join(parts[: i + 1]) for i in range(len(parts))]


def _hit(name: str | None, table: set[str]) -> str | None:
    return next((p for p in _prefixes(name) if p in table), None) if name else None


def _imported(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    return [f"{node.module}.{a.name}" for a in node.names] if node.module and node.level == 0 else []


def _base_name(node: ast.expr) -> str:
    return node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name) else ""


def _safe_loader_classes(tree: ast.Module) -> set[str]:
    """Classes defined in this module whose bases include a yaml SafeLoader."""
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and any(_base_name(b) in SAFE_LOADERS for b in node.bases)
    }


def _unsafe_call(call: ast.Call, names: _Names, safe: set[str]) -> str | None:
    func = names.of(call.func) or ""
    if func in ("yaml.load", "yaml.load_all"):
        positional = call.args[1] if len(call.args) > 1 else None
        loader = next((k.value for k in call.keywords if k.arg == "Loader"), positional)
        last = (names.of(loader) or "").rsplit(".", 1)[-1] if loader is not None else ""
        if last not in SAFE_LOADERS and last not in safe:
            return f"calls {func} without a SafeLoader"
    positional = call.args[2] if func == "numpy.load" and len(call.args) > 2 else None  # load(file, mmap, pickle)
    allow = next((k.value for k in call.keywords if k.arg == "allow_pickle"), positional)
    if allow is not None and _literal(allow) is not False:
        return f"calls {func} with allow_pickle that is not a literal False"
    if func == "numpy.load" and any(k.arg is None for k in call.keywords):
        return "calls numpy.load with ** arguments, which can carry allow_pickle"
    computed = len(call.args) > 1 and not isinstance(_literal(call.args[1]), str)
    if func == "builtins.getattr" and computed and (names.of(call.args[0]) or "").split(".")[0] in GETATTR_UNSAFE_ROOTS:
        return f"calls getattr with a computed name on {names.of(call.args[0])}"
    return None


def unsafe_findings(rel: str, source: str) -> list[str]:
    """Unsafe decoders and code execution, banned in every Python file of the repository."""
    tree = ast.parse(source)
    names, safe = _Names(aliases(tree)), _safe_loader_classes(tree)
    out: set[str] = set()
    for node in ast.walk(tree):
        hits: list[str | None] = []
        if isinstance(node, ast.Import | ast.ImportFrom):
            hits = [f"imports {n}" if _hit(n, UNSAFE) else None for n in _imported(node)]
        elif isinstance(node, ast.Name | ast.Attribute | ast.Subscript | ast.Call):
            hit = _hit(names.of(node), UNSAFE)
            hits = [f"names {hit}" if hit else None]
            if isinstance(node, ast.Call):
                hits.append(_unsafe_call(node, names, safe))
        out |= {f"{rel}:{getattr(node, 'lineno', 0)}: {h} (banned everywhere, boundaries §5.2)" for h in hits if h}
    return sorted(out)


def _read_call(call: ast.Call, names: _Names, engine: bool) -> str | None:
    if isinstance(call.func, ast.Attribute) and call.func.attr in READ_METHODS:
        return f"calls .{call.func.attr}()"
    computed = len(call.args) > 1 and not isinstance(_literal(call.args[1]), str)
    if engine and names.of(call.func) == "builtins.getattr" and computed:
        return "calls getattr with a computed name"
    return None


def _read_hit(node: ast.AST, names: _Names, engine: bool) -> str | None:
    if isinstance(node, ast.Import | ast.ImportFrom):
        banned = [n for n in _imported(node) if _hit(n, INPUT) or (engine and _hit(n, DYNAMIC))]
        return f"imports {banned[0]}" if banned else None
    if not isinstance(node, ast.Name | ast.Attribute | ast.Subscript | ast.Call):
        return None
    name = names.of(node)
    if hit := _hit(name, INPUT):
        return f"reaches {name}, under {hit}"
    if engine and (hit := _hit(name, DYNAMIC)):
        return f"reaches {hit}: a dynamic import can reach any input"
    return _read_call(node, names, engine) if isinstance(node, ast.Call) else None


def input_findings(rel: str, source: str) -> list[str]:
    """Input primitives in a ``src/`` module that is not an input gate."""
    if not rel.startswith("src/") or rel in INPUT_GATES:
        return []
    tree = ast.parse(source)
    names, engine = _Names(aliases(tree)), rel.startswith("src/simcore/")
    out = {
        f"{rel}:{getattr(node, 'lineno', 0)}: {hit}: only an input gate reads input (boundaries §5.2)"
        for node in ast.walk(tree)
        if (hit := _read_hit(node, names, engine))
    }
    return sorted(out)


def check_inputs(files: dict[str, str]) -> list[str]:
    problems = []  # an input gate that does not exist is the gate registry's finding (lint_gates.py)
    for rel, text in sorted(files.items()):
        if rel.endswith(".py"):
            problems += unsafe_findings(rel, text) + input_findings(rel, text)
    return problems
