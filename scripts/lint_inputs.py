"""Standards check 5: what an import can't show about untrusted input (boundaries §5.2, B-4).

The load-bearing rule for modules is a set of allowlists, fail closed (``tests/_imports.py``): each layer's external
imports and numpy and scipy names, what one module may take from another, and what a path holder may do with its
path. This lint covers what those can't show, in closed lists:

- **The builtins:** ``open``, ``input`` and ``__import__`` in ``src/``; ``eval``, ``exec`` and ``compile`` in every
  file. They count by any spelling (``builtins.open``, ``__builtins__.eval``, ``__builtins__['eval']``,
  ``vars(builtins)['exec']``, ``globals()['__builtins__']``), and a bare name counts only when the module doesn't bind
  it itself (a parameter, an assignment, a loop or ``with`` target, an import, a ``def`` or ``class``).
- **A module's own loader** in ``src/``: ``__loader__`` and ``__spec__`` (``__loader__.get_data(p)`` reads any file
  with no import); and, in all of ``src/``, ``getattr`` other than a plain call with a literal name, and any call of
  ``vars``, ``globals`` or ``locals``. numpy's and scipy's IO is held by
  ``tests/_imports.py::EXTERNAL_NAMES``, an allowlist of the external names each layer uses.
- **Decoders and code runners in every file**, since the allowlists can't reach ``scripts/`` or ``tests/``: importing or
  naming ``pickle``, ``_pickle``, ``marshal``, ``shelve``, ``dill``, ``cloudpickle``, ``jsonpickle``,
  ``multiprocessing.reduction``, ``numpy.ctypeslib``, ``runpy``, ``code`` or ``ctypes`` (by import,
  ``importlib.import_module``, ``__import__`` or ``sys.modules`` with a literal name); yaml's unsafe loaders and
  ``yaml.constructor``; ``yaml.load`` without a ``SafeLoader`` (or a subclass defined beside it); an ``allow_pickle``
  that is not a literal ``False`` (by keyword, or by position to ``numpy.load``, ``lib.npyio.load``, ``NpzFile`` and
  ``read_array``); and ``*`` or ``**`` arguments to any of them.

- **Routes through a value** in ``src/`` (B29; step 3b delta round 7): the attributes that reach a namespace
  (``__globals__``, ``__dict__``, ``__self__``, frame attributes and the rest of ``NAMESPACE_ATTRIBUTES``) on any
  value, by attribute, by ``getattr`` with a literal name or by ``__getattribute__``, and a format field naming one
  in a str or bytes constant (``'{0.__globals__[os]}'``); and, outside the input gates, a filesystem or receive
  method on any value (``read_text``, ``readline``, ``recv`` and the rest of ``FS_METHODS``), since a path or a stream
  handed in is still input. Names this game also uses for its own things (``open``, ``read``, ``walk``, ``resolve``)
  are left out; the guard there is the capability: ``maxim_overdrive.data.data_dir`` hands out a ``DataPath``, which
  has none of them.

What it can't see: a value passed through a variable, a container or a function (``f = pick(yaml)``,
``operator.attrgetter('unsafe_load')(yaml)``, ``functools.partial(np.load, ...)`` outside ``src/``), a method named
at run time, and ``from x import *`` (ruff's F403 refuses that). It guards mistakes, not adversaries.
``tests/test_lint_inputs_corpus.py`` judges every reported spelling by this lint and the contract together.
"""

from __future__ import annotations

import ast
import re

# The modules that may read input, each with what it reads. A new gate joins this list, the contract's ignore list
# and the gate registry (lint_gates.py) in the change that makes it.
INPUT_GATES = {"src/simcore/adapters/loaders.py": "the file gates: strict YAML from an explicit path"}

EVERYWHERE = {
    "pickle", "_pickle", "marshal", "shelve", "dill", "cloudpickle", "jsonpickle", "multiprocessing.reduction",
    "runpy", "code", "ctypes", "yaml.unsafe_load", "yaml.unsafe_load_all", "yaml.full_load", "yaml.full_load_all",
    "yaml.Loader", "yaml.UnsafeLoader", "yaml.FullLoader", "yaml.CLoader", "yaml.CUnsafeLoader", "yaml.CFullLoader",
    "yaml.constructor", "builtins.eval", "builtins.exec", "builtins.compile", "numpy.ctypeslib",
}  # fmt: skip
# numpy's and scipy's IO is not listed here: tests/_imports.py::EXTERNAL_NAMES allows each layer only the external
# names it uses, so every other part of those packages, and of the stdlib, is refused (delta rounds 5 and 6).
IN_SRC = {"builtins.open", "builtins.input", "builtins.__import__", "__loader__", "__spec__"}
# allow_pickle by position, per reader: numpy.load(file, mmap_mode, allow_pickle), read_array(fp, allow_pickle).
PICKLE_POSITION = {
    "numpy.load": 2, "numpy.lib.npyio.load": 2, "numpy.lib.npyio.NpzFile": 2, "numpy.lib.format.read_array": 1,
}  # fmt: skip
SAFE_LOADERS = {"SafeLoader", "CSafeLoader"}
IMPORTERS = {"importlib.import_module", "builtins.__import__", "importlib.__import__"}
NAMESPACES = {"builtins.vars", "builtins.globals", "builtins.locals"}  # vars(x) is x's names; globals() the module's
BUILTINS = {"open", "input", "eval", "exec", "__import__", "compile", "getattr", "vars", "globals", "locals"}
# Attributes that reach a module's namespace from any value (contextmanager(len).__globals__['os']), in src/.
NAMESPACE_ATTRIBUTES = {
    "__globals__", "__dict__", "__builtins__", "__subclasses__", "__code__", "__closure__", "__self__",
    "__getattribute__", "__loader__", "__spec__", "f_globals", "f_builtins", "f_locals", "f_back", "tb_frame",
    "gi_frame", "cr_frame", "ag_frame",
}  # fmt: skip
# A str.format field that reads one of them itself ('{0.__globals__[os]}'.format(f)), or any dunder by attribute or
# by subscript: a format field is code that runs on its arguments. Bytes constants too (b'{0.__globals__}'.decode()).
# Any dunder, and every name in NAMESPACE_ATTRIBUTES ('{0.gi_frame.f_globals[os]}'; delta review, D9).
_NAMESPACE_WORDS = "|".join(sorted(n for n in NAMESPACE_ATTRIBUTES if not n.startswith("__")))
FORMAT_DUNDER = re.compile(rf"\{{[^{{}}]*[.\[]\s*(__|(?:{_NAMESPACE_WORDS})\b)")
# Methods that read or write the filesystem or a stream from a value (a Path or a socket handed in), outside the input
# gates: only names with no other meaning in this game. read, replace, copy, move, open, walk, resolve, exists, stat
# and absolute are also str, dict, Format.read, a door, a body's walk or target resolution (step 3b(b) review,
# Architecture A6), so they are a stated blind spot; the guard for those is the capability: the file gates hand out no
# pathlib.Path at all, only a DataPath, which has none of them (Trust T1-S3, T1-S5; delta review, D1).
FS_METHODS = {
    "read_text", "read_bytes", "write_text", "write_bytes", "iterdir", "glob", "rglob", "is_file", "is_dir",
    "is_symlink", "is_mount", "lstat", "readlink", "mkdir", "rmdir", "unlink", "touch", "rename", "symlink_to",
    "hardlink_to", "chmod", "lchmod", "owner", "samefile", "expanduser", "scandir", "readline", "readlines", "readinto",
    "readexactly", "readuntil", "recv", "recv_into", "recvfrom", "recvfrom_into", "recvmsg", "recv_bytes", "makefile",
}  # fmt: skip


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
            out |= {(a.asname or a.name): f"{node.module}.{a.name}" for a in node.names if a.name != "*"}
    return out


def bound_names(tree: ast.Module) -> set[str]:
    """Names the module binds itself: parameters, assignment, loop, ``with`` and ``except`` targets, ``def`` and
    ``class`` names (imports are aliases, resolved separately)."""
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
            out.add(node.id)
        elif isinstance(node, ast.arg):
            out.add(node.arg)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            out.add(node.name)
        elif isinstance(node, ast.ExceptHandler):
            out |= {node.name} if node.name else set()
    return out


def _literal(node: ast.AST | None) -> object:
    return node.value if isinstance(node, ast.Constant) else ...


class _Names:
    """Canonical dotted names of expressions in one module."""

    def __init__(self, tree: ast.Module) -> None:
        self.table, self.bound = aliases(tree), bound_names(tree)

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

    def name(self, ident: str) -> str | None:
        if ident in self.table:
            return self.table[ident]
        if ident in self.bound:
            return None  # the module's own name: a parameter called input is not the builtin
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


def _hit(name: str | None, table: set[str]) -> str | None:
    if not name:
        return None
    parts = name.split(".")
    return next((p for p in (".".join(parts[: i + 1]) for i in range(len(parts))) if p in table), None)


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
        local = loader.id if isinstance(loader, ast.Name) and loader.id in safe else None  # a class defined here
        last = local or ((names.of(loader) or "").rsplit(".", 1)[-1] if loader is not None else "")
        return None if last in SAFE_LOADERS or last in safe else f"calls {func} without a SafeLoader"
    at = PICKLE_POSITION.get(func)
    positional = call.args[at] if at is not None and len(call.args) > at else None
    allow = next((k.value for k in call.keywords if k.arg == "allow_pickle"), positional)
    if allow is not None and _literal(allow) is not False:
        return f"calls {func} with allow_pickle that is not a literal False"
    starred = any(isinstance(a, ast.Starred) for a in call.args) or any(k.arg is None for k in call.keywords)
    if at is not None and starred:
        return f"calls {func} with * or ** arguments, which can carry allow_pickle"
    return None


def _imported(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    return [f"{node.module}.{a.name}" for a in node.names] if node.module and node.level == 0 else []


def _findings(rel: str, source: str, table: set[str], calls: bool) -> list[str]:
    tree = ast.parse(source)
    names, safe = _Names(tree), _safe_loader_classes(tree)
    out: set[str] = set()
    for node in ast.walk(tree):
        hits: list[str | None] = []
        if isinstance(node, ast.Import | ast.ImportFrom):
            hits = [f"imports {n}" if _hit(n, table) else None for n in _imported(node)]
        elif isinstance(node, ast.Name | ast.Attribute | ast.Subscript | ast.Call):
            hit = _hit(names.of(node), table)
            hits = [f"names {hit}" if hit else None]
            if calls and isinstance(node, ast.Call):
                hits.append(_unsafe_call(node, names, safe))
        out |= {f"{rel}:{getattr(node, 'lineno', 0)}: {h} (boundaries §5.2)" for h in hits if h}
    return sorted(out)


def unsafe_findings(rel: str, source: str) -> list[str]:
    """Decoders, code runners and the code-running builtins, banned in every Python file of the repository."""
    return _findings(rel, source, EVERYWHERE, calls=True)


def _computed_getattr(rel: str, source: str) -> list[str]:
    """``getattr`` used any way but a plain call with a literal name (a computed name, star arguments, the builtin
    taken as a value, ``__builtins__.getattr`` too), and any call of ``vars``, ``globals`` or ``locals``, whose
    result is a namespace (``vars(module)['_private']``), in every ``src/`` module (delta reviews 2 and 3: N3, R3-3,
    R3-4). Further deliberate spellings are out of this branch's scope (owner, 2026-11-21): docs/standards_backlog.md
    B39, triggered when untrusted code (mods) can reach src/."""
    tree = ast.parse(source)
    names = _Names(tree)
    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    out = []
    for node in ast.walk(tree):
        value = isinstance(node, ast.Name | ast.Attribute | ast.Subscript) and id(node) not in called
        if value and names.of(node) == "builtins.getattr":  # g = getattr, g = __builtins__.getattr (round 3, R3-4)
            out.append(f"{rel}:{getattr(node, 'lineno', 0)}: takes getattr as a value (boundaries §5.2)")
        if isinstance(node, ast.Call) and names.of(node.func) in NAMESPACES:  # vars(M)['_REAL'] (round 3, R3-3)
            out.append(f"{rel}:{node.lineno}: reads a namespace through {names.of(node.func)} (boundaries §5.2)")
        if not (isinstance(node, ast.Call) and names.of(node.func) == "builtins.getattr"):
            continue
        if len(node.args) < 2 or not isinstance(_literal(node.args[1]), str):  # star args fail here too
            out.append(f"{rel}:{node.lineno}: calls getattr with a computed name (boundaries §5.2)")
    return out


def _attribute_named(node: ast.AST) -> str | None:
    """The attribute ``node`` reads: ``v.name``, ``getattr(v, 'name')``, ``v.__getattribute__('name')`` and
    ``object.__getattribute__(v, 'name')`` alike (step 3b(b) review, Trust T1-S4)."""
    if isinstance(node, ast.Attribute):
        return node.attr
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    by_getattr = isinstance(func, ast.Name) and func.id == "getattr" and len(node.args) > 1
    by_dunder = isinstance(func, ast.Attribute) and func.attr == "__getattribute__"
    if not (by_getattr or by_dunder):
        return None
    # The name's own argument: getattr(v, NAME, default) and object.__getattribute__(v, NAME) take it second, a bound
    # v.__getattribute__(NAME) first; a string default is not the name (delta review, D-S3).
    owner = func.value if isinstance(func, ast.Attribute) else None
    bound = by_dunder and not (isinstance(owner, ast.Name) and owner.id == "object")
    at = 0 if bound else 1
    arg = node.args[at] if len(node.args) > at else None
    return arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None


def _format_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str | bytes):
        return node.value if isinstance(node.value, str) else node.value.decode("latin-1")
    return None


def _value_routes(rel: str, source: str, gate: bool) -> list[str]:
    """Namespace attributes and dunder format fields on any value; filesystem methods outside a gate (B29)."""
    out = []
    for node in ast.walk(ast.parse(source)):
        name, text, line = _attribute_named(node), _format_text(node), getattr(node, "lineno", 0)
        if name in NAMESPACE_ATTRIBUTES:
            out.append(f"{rel}:{line}: reads {name}, a namespace through a value (B29)")
        elif name in FS_METHODS and not gate:
            out.append(f"{rel}:{line}: calls .{name}, input through a value outside the gates (B29)")
        elif text is not None and FORMAT_DUNDER.search(text):
            out.append(f"{rel}:{line}: a format field names a dunder, a namespace through a value (B29)")
    return sorted(set(out))


def input_findings(rel: str, source: str) -> list[str]:
    """The input builtins and a module's own loader, in a ``src/`` module that is not an input gate; and the routes
    through a value, in every ``src/`` module (filesystem methods outside the gates only)."""
    if not rel.startswith("src/"):
        return []
    routes = _value_routes(rel, source, gate=rel in INPUT_GATES)
    if rel in INPUT_GATES:
        return routes
    computed = _computed_getattr(rel, source)
    return _findings(rel, source, IN_SRC, calls=False) + computed + routes


def check_inputs(files: dict[str, str]) -> list[str]:
    problems = []  # an input gate that does not exist is the gate registry's finding (lint_gates.py)
    for rel, text in sorted(files.items()):
        if rel.endswith(".py"):
            problems += unsafe_findings(rel, text) + input_findings(rel, text)
    return problems
