"""The regression corpus for scripts/lint_inputs.py: every spelling any review reported, with its verdict.

Each rewrite of the lint once silently dropped spellings an earlier round had probed (``os.environ.get`` was caught at
3a0d482 and lost at 8c1de1e), because the probes were never pinned. Here they are pinned, each with the round that
reported it, plus clean spellings that must not be flagged. A spelling a review finds is added here, never only to
the lint. Since delta round 3 each row is judged by the import contracts and the lint together: the contract is
the rule for modules (``input-primitives``), the lint covers the builtins and numpy's IO.
``docs/design/reviews/step3b/fold.md`` records how each revision of the lint scored on this corpus.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from tests.test_lint_standards import _load

inputs = _load("lint_inputs")
ROOT = Path(__file__).resolve().parents[1]

SRC = "src/simcore/protocol/x.py"  # in the engine, outside the gates; planted rows go beside it
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
    # -- input: clean, must not be flagged ----------------------------------------------------------------------------
    ("input", "src/simcore/adapters/loaders.py", "t = path.read_text()", False, "build: the gate itself"),
    ("input", "scripts/x.py", "t = path.read_text()", False, "build: outside src"),
    ("input", SRC, "t = grid.temperature.copy()\nn = self.load", False, "build"),
    ("input", SRC, "v = getattr(obj, 'name', None)", False, "round 1"),
    ("input", SRC, "v = params.get('energy_j')", False, "fold 3"),
    ("input", SRC, "e = self.environ\nr = record.argv", False, "fold 3"),
    ("input", SRC, "import re\np = re.compile('x')", False, "fold 3"),
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
    ("input", "v = getattr(obj, name)", "round 1", "a computed attribute reads no input; importlib is forbidden"),
    (
        "input",
        "async def f(r):\n    return await r.readline()",
        "delta 3",
        "an asyncio stream handed in; asyncio is forbidden",
    ),
    ("unsafe", "import yaml\nf = getattr(yaml, name)", "round 1", "a computed name, a value; in src yaml is forbidden"),
    ("unsafe", "from numpy import *\na = load(f, None, True)", "delta 3", "a star import; ruff's F403 refuses it"),
    ("unsafe", "import operator, yaml\nf = operator.attrgetter('unsafe_load')(yaml)", "delta 3", "a name as a value"),
]


GATES = {"src/simcore/adapters/loaders.py"}


def _planted(rule: str, rel: str) -> bool:
    return rule == "input" and rel.startswith("src/") and rel not in GATES


@pytest.fixture(scope="module")
def contract_hits(tmp_path_factory) -> set[str]:
    """Plant every input row as its own module in a copy of src/ and run the gate's import contracts once; the rows
    whose module breaks a contract, as their planted module names."""
    from tests.test_tooling_config import _lint_imports  # noqa: PLC0415 - the gate's own command

    tree = tmp_path_factory.mktemp("corpus")
    shutil.copytree(ROOT / "src", tree / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "pyproject.toml", tree)
    rows = [(c[0], c[1], c[2]) for c in CASES] + [(n[0], SRC, n[1]) for n in NOT_COVERED]
    for i, (rule, rel, source) in enumerate(rows):
        if _planted(rule, rel):
            (tree / "src" / "simcore" / "protocol" / f"_corpus_{i}.py").write_text(source + "\n")
    out = _lint_imports(tree).stdout
    return set(re.findall(r"simcore\.protocol\.(_corpus_\d+) ->", out))


def _flagged(rule: str, rel: str, source: str, index: int, hits: set[str]) -> bool:
    """The joint verdict: the import contracts (for a planted input row) or the lint."""
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
    assert {"build", "round 1", "delta 1", "delta 2", "delta 3"} <= origins
    assert {c[3] for c in CASES if c[0] == "input"} == {True, False}
    assert {c[3] for c in CASES if c[0] == "unsafe"} == {True, False}
