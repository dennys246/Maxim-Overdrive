"""The regression corpus for scripts/lint_inputs.py: every spelling any review reported, with its verdict.

Each rewrite of the lint once silently dropped spellings an earlier round had probed (``os.environ.get`` was caught at
3a0d482 and lost at 8c1de1e), because the probes were never pinned. Here they are pinned, each with the round that
reported it, plus clean spellings that must not be flagged. A spelling a review finds is added here, never only to
the lint. Each row is judged by the fail-closed import allowlist (``tests/_imports.py``: each layer's external
imports, a gate's ``__all__``, the data locator's attributes) and the lint together; the allowlist is the rule for
modules, the lint covers the builtins and numpy's and scipy's IO.
``docs/design/reviews/step3b/fold.md`` records how each revision of the lint scored on this corpus.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from tests import _imports
from tests.test_lint_standards import _load

inputs = _load("lint_inputs")
ROOT = Path(__file__).resolve().parents[1]
HOLDER = {
    "src/maxim_overdrive/data.py": "maxim_overdrive.data",
    "src/simcore/protocol/tiers.py": "simcore.protocol.tiers",
}
HOLDER_SOURCE = {rel: (ROOT / rel).read_text() for rel in HOLDER}

SRC = "src/simcore/protocol/x.py"  # in the engine, outside the gates; planted rows go beside it
DATA = "src/maxim_overdrive/data.py"  # a path holder: rows here judge its attributes
TIERS = "src/simcore/protocol/tiers.py"  # the other path holder
ANY = "tests/test_x.py"  # the unsafe rule holds in every file

# (rule, file, source, flagged, where it was reported)
CASES: list[tuple[str, str, str, bool, str]] = [
    # -- input primitives, reported when the lint was built (step 3b) -------------------------------------------------
    ("input", SRC, "import json\nx = json.loads(raw)", True, "build"),
    ("input", SRC, "import json\nx = json.load(f)", True, "build"),
    ("input", SRC, "import yaml\nx = yaml.safe_load(text)", True, "build"),
    ("input", SRC, "f = open('x')", True, "build"),
    ("input", SRC, "a = np.load('z.npy')", True, "build"),
    ("input", SRC, "import numpy\na = numpy.load('z.npy')", True, "build"),
    ("input", SRC, "import os\nv = os.environ['X']", True, "build"),
    ("input", SRC, "import os\nv = os.getenv('X')", True, "build"),
    ("input", SRC, "import sys\na = sys.argv[1]", True, "build"),
    ("input", SRC, "line = input()", True, "build"),
    # -- input primitives, round 1 (Trust S1, Architecture N5) ---------------------------------------------------------
    ("input", SRC, "import numpy as n\na = n.load(p)", True, "round 1"),
    ("input", SRC, "from numpy import load as ld\na = ld(p)", True, "round 1"),
    ("input", SRC, "from os import environ as env\nv = env['X']", True, "round 1"),
    ("input", SRC, "import sys as s\na = s.argv", True, "round 1"),
    ("input", SRC, "import json as j\nx = j.loads(raw)", True, "round 1"),
    ("input", SRC, "import tomllib\nx = tomllib.loads(raw)", True, "round 1"),
    ("input", SRC, "import configparser\nc = configparser.ConfigParser()", True, "round 1"),
    ("input", SRC, "import plistlib\nx = plistlib.loads(raw)", True, "round 1"),
    ("input", SRC, "import fileinput\nfor line in fileinput.input():\n    pass", True, "round 1"),
    ("input", SRC, "import importlib\nm = importlib.import_module(name)", True, "round 1"),
    ("input", SRC, "import importlib\nm = importlib.import_module('json')", True, "round 1"),
    ("input", SRC, "m = __import__(name)", True, "round 1"),
    # -- input primitives, delta 1 (D-B1: a call used through an attribute) ----------------------------------------
    ("input", SRC, "t = open(p).read()", True, "delta 1"),
    ("input", SRC, "from pathlib import Path\nt = Path(p).open().read()", True, "delta 1"),
    ("input", SRC, "a = np.load(p).copy()", True, "delta 1"),
    ("input", SRC, "import json\nv = json.loads(s).get('a')", True, "delta 1"),
    # -- input primitives, delta 2 (D2-B1: a name used through an attribute) ------------------------------------------
    ("input", SRC, "import os\nv = os.environ.get('X')", True, "delta 2"),
    ("input", SRC, "import os\ne = os.environ.copy()", True, "delta 2"),
    ("input", SRC, "from os import environ\nv = environ.get('X')", True, "delta 2"),
    ("input", SRC, "import sys\nt = sys.stdin.read()", True, "delta 2"),
    ("input", SRC, "import sys\nt = sys.stdin.readline()", True, "delta 2"),
    ("input", SRC, "import sys\na = sys.argv.copy()", True, "delta 2"),
    ("input", SRC, "import os\nok = 'X' in os.environ", True, "delta 2"),
    ("input", SRC, "import os\nx = os.environ", True, "delta 2"),
    ("input", SRC, "import builtins\nt = builtins.open(p).read()", True, "delta 2"),
    ("input", SRC, "t = [open(p)][0].read()", True, "delta 2"),
    ("input", SRC, "import io\nt = io.open(p).read()", True, "delta 2"),
    ("input", SRC, "import os\nv = os.getenv('X').strip()", True, "delta 2"),
    # -- input primitives, delta 3 (D3-S1): structural now, held by the contract -----------------------------------
    ("input", SRC, "import os\nb = os.read(fd, 10)", True, "delta 3"),
    ("input", SRC, "import os\nt = os.fdopen(fd).read()", True, "delta 3"),
    ("input", SRC, "import io\nb = io.FileIO(p).readall()", True, "delta 3"),
    ("input", SRC, "m = np.memmap(p)", True, "delta 3"),
    ("input", SRC, "a = np.fromregex(p, 'x', float)", True, "delta 3"),
    ("input", SRC, "import zipfile\nb = zipfile.ZipFile(p).read('x')", True, "delta 3"),
    ("input", SRC, "from urllib.request import urlopen\nb = urlopen(u).read()", True, "delta 3"),
    ("input", SRC, "import sqlite3\nc = sqlite3.connect(p)", True, "delta 3"),
    ("input", SRC, "import mmap\nm = mmap.mmap(fd, 0)", True, "delta 3"),
    ("input", SRC, "import posix\ne = posix.environ", True, "delta 3"),
    ("input", SRC, "import nt\ne = nt.environ", True, "delta 3"),
    ("input", SRC, "import pkgutil\nb = pkgutil.get_data('x', 'a')", True, "delta 3"),
    ("input", SRC, "import asyncio\nr = asyncio.open_connection(h, 80)", True, "delta 3"),
    ("input", SRC, "import tarfile\nt = tarfile.open(p)", True, "delta 3"),
    ("input", SRC, "from importlib import resources\nb = resources.files('x')", True, "delta 3"),
    # -- input: clean, delta 3 (D3-S2): a parameter or local named after a builtin or a module ---------------------
    ("input", SRC, "def f(input):\n    return input.shape", False, "delta 3"),
    ("input", SRC, "def f(*, input=None):\n    return input", False, "delta 3"),
    ("input", SRC, "def f(open: bool):\n    return open", False, "delta 3"),
    ("input", SRC, "json = x.to_dict()", False, "delta 3"),
    ("input", SRC, "yaml = x", False, "delta 3"),
    # -- input, delta 4 (D4-S1): routes past the old denylist, now refused by the allowlist ---------------------------
    ("input", SRC, "import _io\nt = _io.open(p).read()", True, "delta 4"),
    ("input", SRC, "import xml.etree.ElementTree as ET\nt = ET.parse(p)", True, "delta 4"),
    ("input", SRC, "import inspect\nt = inspect.getsource(f)", True, "delta 4"),
    ("input", SRC, "import genericpath\nok = genericpath.exists(p)", True, "delta 4"),
    ("input", SRC, "import wave\nw = wave.open(p)", True, "delta 4"),
    ("input", SRC, "import logging.config\nlogging.config.fileConfig(p)", True, "delta 4"),
    ("input", SRC, "import zipimport", True, "delta 4"),
    ("input", SRC, "import posixpath\nh = posixpath.expanduser('~')", True, "delta 4"),
    ("input", SRC, "import platform\nn = platform.node()", True, "delta 4"),
    ("input", SRC, "import getpass\nu = getpass.getuser()", True, "delta 4"),
    ("input", SRC, "import pwd", True, "delta 4"),
    ("input", SRC, "import locale", True, "delta 4"),
    ("input", SRC, "import sysconfig", True, "delta 4"),
    ("input", SRC, "import site", True, "delta 4"),
    ("input", SRC, "import netrc", True, "delta 4"),
    ("input", SRC, "import _socket", True, "delta 4"),
    ("input", SRC, "import _posixsubprocess", True, "delta 4"),
    ("input", SRC, "from concurrent.futures import ProcessPoolExecutor", True, "delta 4"),
    ("input", SRC, "import signal", True, "delta 4"),
    ("input", SRC, "import fcntl", True, "delta 4"),
    ("input", SRC, "from scipy.io import loadmat\nm = loadmat(p)", True, "delta 4"),
    ("input", SRC, "import scipy.io\nm = scipy.io.loadmat(p)", True, "delta 4"),
    ("input", SRC, "a = np.lib.npyio.load(p)", True, "delta 4"),
    ("input", SRC, "z = np.lib.npyio.NpzFile(f, True)", True, "delta 4"),
    ("input", SRC, "t = np.DataSource().open(u)", True, "delta 4"),
    ("input", SRC, "f = getattr(np, name)\na = f(p)", True, "delta 4"),
    ("input", SRC, "v = getattr(obj, name)", True, "round 1: covered again in fold 5 (a computed getattr in simcore)"),
    # -- input, delta 4 (D4-S2, Executor S-d): through a gate, and through the module that holds pathlib -------------
    ("input", SRC, "from simcore.adapters.loaders import Path\nt = Path(p).read_text()", True, "delta 4"),
    ("input", SRC, "from simcore.adapters.loaders import yaml\nd = yaml.safe_load(s)", True, "delta 4"),
    ("input", SRC, "from simcore.adapters import loaders\nd = loaders.yaml.safe_load(s)", True, "delta 4"),
    (
        "input",
        SRC,
        "from pathlib import Path\ndef sneak(path):\n    return Path(path).read_text()",
        True,
        "delta 4: S-d in tiers",
    ),
    ("input", DATA, "def sneak(path):\n    return Path(path).read_text()", True, "delta 4: S-d in data"),
    ("input", DATA, "ok = Path(p).is_dir()", True, "delta 4"),
    ("input", DATA, "q = Path(p).parent / 'x'", False, "delta 4: path arithmetic"),
    # -- input, delta 5 (D5-S1, D5-S2, Executor N-g): the last denylist corners, now allowlisted ------------------
    ("input", SRC, "a = np.lib._npyio_impl.load(p)", True, "delta 5"),
    ("input", SRC, "a = np.lib._format_impl.read_array(f)", True, "delta 5"),
    ("input", SRC, "a = np.rec.fromfile(p)", True, "delta 5"),
    ("input", SRC, "lib = np.ctypeslib.load_library('x', '.')", True, "delta 5"),
    ("input", SRC, "import scipy.sparse\nm = scipy.sparse.load_npz(p)", True, "delta 5"),
    ("input", SRC, "b = __loader__.get_data(p)", True, "delta 5"),
    ("input", SRC, "b = __spec__.loader.get_data(p)", True, "delta 5"),
    ("input", SRC, "b = globals()['__loader__'].get_data(p)", True, "delta 5"),
    ("input", SRC, "from simcore.core.grid import np", True, "delta 5"),
    ("input", SRC, "from simcore.core.grid import np as n\na = n.load(p)", True, "delta 5"),
    ("input", SRC, "from simcore.core.grid import np\na = np.load(p)", True, "delta 5"),
    ("input", SRC, "import simcore.core.grid as g\na = g.np.load(p)", True, "delta 5"),
    ("input", TIERS, "def f(path):\n    return path.read_text()", True, "delta 5: a path handed in"),
    ("input", TIERS, "import simcore.adapters.loaders as L\nP = getattr(L, 'Path')", True, "delta 5"),
    ("input", DATA, "t = getattr(Path(p), 'read_text')()", True, "delta 5"),
    ("input", DATA, "q = Path(p).resolve()", True, "delta 5: realpath reads the filesystem"),
    ("input", SRC, "from simcore.core.grid import MaterialGrid", False, "delta 5: a name grid defines"),
    # -- input: clean, must not be flagged ----------------------------------------------------------------------------
    ("input", "src/simcore/adapters/loaders.py", "t = path.read_text()", False, "build: the gate itself"),
    ("input", "scripts/x.py", "t = path.read_text()", False, "build: outside src"),
    ("input", SRC, "t = grid.temperature.copy()\nn = self.load", False, "build"),
    ("input", SRC, "v = getattr(obj, 'name', None)", False, "round 1"),
    ("input", SRC, "v = params.get('energy_j')", False, "fold 3"),
    ("input", SRC, "e = self.environ\nr = record.argv", False, "fold 3"),
    ("input", SRC, "p = pattern.compile('x')", False, "fold 3: an attribute named compile is not the builtin"),
    # -- unsafe decoders, reported when the lint was built -------------------------------------------------------------
    ("unsafe", ANY, "import pickle", True, "build"),
    ("unsafe", ANY, "import marshal", True, "build"),
    ("unsafe", ANY, "from shelve import open", True, "build"),
    ("unsafe", ANY, "import cloudpickle as cp", True, "build"),
    ("unsafe", ANY, "import yaml\nx = yaml.load(text)", True, "build"),
    ("unsafe", ANY, "import yaml\nx = yaml.load(text, Loader=yaml.Loader)", True, "build"),
    ("unsafe", ANY, "import yaml\nx = yaml.load(text, Loader=yaml.FullLoader)", True, "build"),
    ("unsafe", ANY, "import yaml\nx = yaml.load_all(text, Loader=MyLoader)", True, "build"),
    ("unsafe", ANY, "import yaml\nx = yaml.unsafe_load(text)", True, "build"),
    ("unsafe", ANY, "import yaml\nx = yaml.full_load(text)", True, "build"),
    ("unsafe", ANY, "a = np.load('z.npy', allow_pickle=True)", True, "build"),
    ("unsafe", ANY, "y = eval('1')", True, "build"),
    ("unsafe", ANY, "exec('x = 1')", True, "build"),
    # -- unsafe decoders, round 1 (Trust S1, Architecture N5) ----------------------------------------------------------
    ("unsafe", ANY, "import yaml as y\nx = y.load(s, Loader=y.Loader)", True, "round 1"),
    ("unsafe", ANY, "from yaml import unsafe_load\nx = unsafe_load(s)", True, "round 1"),
    ("unsafe", ANY, "from yaml import load, Loader\nx = load(s, Loader=Loader)", True, "round 1"),
    ("unsafe", ANY, "import yaml\nf = getattr(yaml, 'unsafe_load')", True, "round 1"),
    ("unsafe", ANY, "import importlib\nm = importlib.import_module('pickle')", True, "round 1"),
    ("unsafe", ANY, "m = __import__('pickle')", True, "round 1"),
    ("unsafe", ANY, "import _pickle", True, "round 1"),
    ("unsafe", ANY, "a = np.load(p, allow_pickle=flag)", True, "round 1"),
    ("unsafe", ANY, "a = np.load(p, **{'allow_pickle': True})", True, "round 1"),
    ("unsafe", ANY, "import numpy as n\na = n.load(p, allow_pickle=True)", True, "round 1"),
    ("unsafe", ANY, "import numpy\na = numpy.lib.format.read_array(f, allow_pickle=True)", True, "round 1"),
    ("unsafe", ANY, "import builtins\nx = builtins.eval(s)", True, "round 1"),
    ("unsafe", ANY, "import builtins\nx = builtins.exec(s)", True, "round 1"),
    ("unsafe", ANY, "e = eval\nx = e(s)", True, "round 1"),
    # -- unsafe decoders, delta 1 (D-B1 and D-N1) ------------------------------------------------------------------
    ("unsafe", ANY, "a = np.load(p, allow_pickle=True).item()", True, "delta 1"),
    ("unsafe", ANY, "import importlib\nb = importlib.import_module('pickle').loads(raw)", True, "delta 1"),
    ("unsafe", ANY, "b = __import__('pickle').loads(raw)", True, "delta 1"),
    ("unsafe", ANY, "a = np.load(p, None, True)", True, "delta 1"),
    ("unsafe", ANY, "f = __builtins__['eval']", True, "delta 1"),
    ("unsafe", ANY, "import builtins\nf = vars(builtins)['exec']", True, "delta 1"),
    ("unsafe", ANY, "import builtins\nf = builtins.__dict__['exec']", True, "delta 1"),
    ("unsafe", ANY, "import yaml\nL = yaml.CUnsafeLoader", True, "delta 1"),
    ("unsafe", ANY, "import yaml\nL = yaml.CFullLoader", True, "delta 1"),
    (
        "unsafe",
        ANY,
        "import yaml\nclass L(yaml.SafeLoader):\n    pass\n"
        "L.add_multi_constructor('tag:yaml.org,2002:python/', yaml.constructor.UnsafeConstructor.x)",
        True,
        "delta 1",
    ),
    # -- unsafe decoders, delta 2 (D2-B1 and D2-N1) ----------------------------------------------------------------
    ("unsafe", ANY, "x = __builtins__.eval(s)", True, "delta 2"),
    ("unsafe", ANY, "m = __builtins__.__import__('pickle')", True, "delta 2"),
    ("unsafe", ANY, "import builtins\nx = builtins.__dict__.get('eval')(s)", True, "delta 2"),
    ("unsafe", ANY, "import yaml\nyaml.Loader.add_constructor('!x', f)", True, "delta 2"),
    ("unsafe", ANY, "import importlib\nm = importlib.__import__('pickle')", True, "delta 2"),
    ("unsafe", ANY, "import sys\nm = sys.modules['pickle']", True, "delta 2"),
    ("unsafe", ANY, "import sys\nx = sys.modules['builtins'].eval(s)", True, "delta 2"),
    ("unsafe", ANY, "x = globals()['__builtins__']['eval'](s)", True, "delta 2"),
    ("unsafe", ANY, "import multiprocessing\nx = multiprocessing.reduction.ForkingPickler.loads(b)", True, "delta 2"),
    ("unsafe", ANY, "a = np.load(p, allow_pickle=True)[()]", True, "delta 2"),
    ("unsafe", ANY, "import pickle\nx = pickle.Unpickler(f).load()", True, "delta 2"),
    ("unsafe", ANY, "b = [__import__('pickle')][0].loads(raw)", True, "delta 2"),
    ("unsafe", ANY, "from importlib import import_module as im\nb = im('pickle').loads(raw)", True, "delta 2"),
    ("unsafe", ANY, "import builtins\nb = builtins.__import__('pickle').loads(raw)", True, "delta 2"),
    ("unsafe", ANY, "import importlib\nf = getattr(importlib.import_module('pickle'), 'loads')", True, "delta 2"),
    ("unsafe", ANY, "import marshal\nx = marshal.loads(b).keys()", True, "delta 2"),
    ("unsafe", ANY, "import shelve\nx = shelve.open(p).keys()", True, "delta 2"),
    ("unsafe", ANY, "import yaml\nx = yaml.unsafe_load(s).keys()", True, "delta 2"),
    ("unsafe", ANY, "import yaml\nx = yaml.load(s).keys()", True, "delta 2"),
    ("unsafe", ANY, "from yaml import load\nx = load(s).get('a')", True, "delta 2"),
    # -- unsafe, delta 3 (D3-N1) --------------------------------------------------------------------------------------
    ("unsafe", ANY, "a = np.load(f, *a)", True, "delta 3"),
    ("unsafe", ANY, "a = np.lib.format.read_array(f, True)", True, "delta 3"),
    ("unsafe", ANY, "import runpy\nrunpy.run_path(p)", True, "delta 3"),
    ("unsafe", ANY, "import code\ncode.InteractiveInterpreter().runsource(s)", True, "delta 3"),
    ("unsafe", ANY, "import types\nf = types.FunctionType(compile(s, 'x', 'exec'), {})", True, "delta 3"),
    ("unsafe", ANY, "import ctypes\nctypes.pythonapi.PyRun_SimpleString(b'x')", True, "delta 3"),
    ("unsafe", ANY, "import jsonpickle\nx = jsonpickle.decode(s)", True, "delta 3"),
    ("unsafe", ANY, "eval = model.evaluate()", False, "delta 3: a local named eval"),
    # -- unsafe, delta 4 (D4-N1): allow_pickle by position to the other readers ------------------------------------
    ("unsafe", ANY, "a = np.lib.npyio.load(f, None, True)", True, "delta 4"),
    ("unsafe", ANY, "z = np.lib.npyio.NpzFile(f, False, True)", True, "delta 4"),
    # -- unsafe: clean, must not be flagged ---------------------------------------------------------------------------
    ("unsafe", ANY, "import yaml\nx = yaml.load(text, Loader=yaml.SafeLoader)", False, "build"),
    ("unsafe", ANY, "import yaml\nx = yaml.load(text, yaml.CSafeLoader)", False, "build"),
    ("unsafe", ANY, "import yaml\nclass L(yaml.SafeLoader):\n    pass\nx = yaml.load(text, Loader=L)", False, "build"),
    ("unsafe", ANY, "import yaml\nx = yaml.safe_load(text)", False, "build"),
    ("unsafe", ANY, "a = np.load('z.npy')", False, "build"),
    ("unsafe", ANY, "a = np.load('z.npy', allow_pickle=False)", False, "build"),
    ("unsafe", ANY, "s = 'eval(x) and pickle are banned'", False, "build"),
    ("unsafe", ANY, "x = model.eval()", False, "build"),
    ("unsafe", ANY, "import yaml as y\nx = y.load(s, Loader=y.SafeLoader)", False, "round 1"),
    ("unsafe", ANY, "import importlib\nm = importlib.import_module(node.module)", False, "fold 3: a test helper"),
    ("unsafe", ANY, "import builtins\nf = builtins.len", False, "fold 3"),
    ("unsafe", ANY, "f = getattr(obj, name)", False, "fold 3: a computed name on an ordinary object"),
    ("unsafe", ANY, "import sys\nm = sys.modules['json']", False, "fold 3"),
]

# Spellings the design deliberately doesn't cover, each with the reason. The joint judge must not flag them; if one
# becomes covered, move it into CASES.
NOT_COVERED: list[tuple[str, str, str, str]] = [
    (
        "input",
        "t = Path(p).read_text()",
        "build",
        "Path unbound: only an import brings it in, which the contract forbids",
    ),
    ("input", "b = path.read_bytes()", "build", "a method on an object handed in; values aren't followed"),
    ("input", "m = sock.recv(1024)", "build", "a method on an object handed in; values aren't followed"),
    ("input", "h = path.open()", "build", "a method on an object handed in; values aren't followed"),
    ("input", "v = getenv('X')", "build", "getenv unbound is a NameError; importing it is a contract finding"),
    (
        "input",
        "async def f(r):\n    return await r.readline()",
        "delta 3",
        "an asyncio stream handed in; asyncio is forbidden",
    ),
    ("unsafe", "import yaml\nf = getattr(yaml, name)", "round 1", "a computed name, a value; in src yaml is forbidden"),
    ("unsafe", "from numpy import *\na = load(f, None, True)", "delta 3", "a star import; ruff's F403 refuses it"),
    ("unsafe", "import operator, yaml\nf = operator.attrgetter('unsafe_load')(yaml)", "delta 3", "a name as a value"),
    (
        "unsafe",
        "import functools\nf = functools.partial(np.load, mmap_mode=None)\na = f(p, None, True)",
        "delta 4",
        "a function passed as a value; in src naming np.load is already refused",
    ),
]


GATES = {"src/simcore/adapters/loaders.py"}


def _planted(rule: str, rel: str) -> bool:
    return rule == "input" and rel.startswith("src/") and rel not in GATES


@pytest.fixture(scope="module")
def contract_hits(tmp_path_factory) -> set[str]:
    """Plant every input row as its own module in a copy of src/, build the import graph once, and return the rows
    the import allowlist or a gate's ``__all__`` refuses, as their planted module names."""
    tree = tmp_path_factory.mktemp("corpus")
    shutil.copytree(ROOT / "src", tree / "src", ignore=shutil.ignore_patterns("__pycache__"))
    rows = [(c[0], c[1], c[2]) for c in CASES] + [(n[0], SRC, n[1]) for n in NOT_COVERED]
    hits = set()
    for i, (rule, rel, source) in enumerate(rows):
        if _planted(rule, rel) and rel not in HOLDER:
            (tree / "src" / "simcore" / "protocol" / f"_corpus_{i}.py").write_text(source + "\n")
            name = f"simcore.protocol._corpus_{i}"
            checks = (_imports.gate_reexports, _imports.internal_reexports, _imports.numeric_violations)
            if any(check(name, source + "\n") for check in checks):
                hits.add(f"_corpus_{i}")
        elif _planted(rule, rel) and _imports.path_holder_violations(HOLDER[rel], HOLDER_SOURCE[rel] + "\n" + source):
            hits.add(f"_corpus_{i}")
    violations = _imports.allowlist_violations(_imports.external_imports(tree))
    return hits | set(re.findall(r"simcore\.protocol\.(_corpus_\d+) imports", "\n".join(violations)))


def _flagged(rule: str, rel: str, source: str, index: int, hits: set[str]) -> bool:
    """The joint verdict: the import allowlist, a gate's __all__ and the data locator's attributes (for a planted
    input row), or the lint."""
    if rule == "unsafe":
        return bool(inputs.unsafe_findings(rel, source + "\n"))
    return f"_corpus_{index}" in hits or bool(inputs.input_findings(rel, source + "\n"))


@pytest.mark.parametrize(
    ("index", "row"), list(enumerate(CASES)), ids=[f"{c[0]}-{c[4]}-{i}" for i, c in enumerate(CASES)]
)
def test_every_reported_spelling_keeps_its_verdict(contract_hits, index, row):
    rule, rel, source, flagged, origin = row
    assert _flagged(rule, rel, source, index, contract_hits) is flagged, (origin, source)


@pytest.mark.parametrize(
    ("index", "row"),
    [(len(CASES) + i, n) for i, n in enumerate(NOT_COVERED)],
    ids=[f"not-covered-{n[2]}-{i}" for i, n in enumerate(NOT_COVERED)],
)
def test_a_spelling_the_design_leaves_out_is_still_left_out(contract_hits, index, row):
    rule, source, origin, reason = row
    rel = SRC if rule == "input" else ANY
    assert not _flagged(rule, rel, source, index, contract_hits), (origin, reason)


def test_the_corpus_holds_every_round_and_both_verdicts():
    origins = {c[4].split(":")[0] for c in CASES}
    assert {"build", "round 1", "delta 1", "delta 2", "delta 3", "delta 4", "delta 5"} <= origins
    assert {c[3] for c in CASES if c[0] == "input"} == {True, False}
    assert {c[3] for c in CASES if c[0] == "unsafe"} == {True, False}
