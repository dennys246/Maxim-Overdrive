"""The regression corpus for scripts/lint_inputs.py: every spelling any review reported, with its verdict.

Each rewrite of the lint once silently dropped spellings an earlier round had probed (``os.environ.get`` was caught at
3a0d482 and lost at 8c1de1e), because the probes were never pinned. Here they are pinned, each with the round that
reported it, plus clean spellings that must not be flagged. A spelling a review finds is added here, never only to
the lint. ``docs/design/reviews/step3b/fold.md`` records how each revision of the lint scored on this corpus.
"""

from __future__ import annotations

import pytest

from tests.test_lint_standards import _load

inputs = _load("lint_inputs")

SRC = "src/simcore/core/x.py"  # the input rule's strictest place: the engine, outside the gates
ANY = "tests/test_x.py"  # the unsafe rule holds in every file

# (rule, file, source, flagged, where it was reported)
CASES: list[tuple[str, str, str, bool, str]] = [
    # -- input primitives, reported when the lint was built (step 3b) -------------------------------------------------
    ("input", SRC, "import json\nx = json.loads(raw)", True, "build"),
    ("input", SRC, "import json\nx = json.load(f)", True, "build"),
    ("input", SRC, "import yaml\nx = yaml.safe_load(text)", True, "build"),
    ("input", SRC, "t = Path(p).read_text()", True, "build"),
    ("input", SRC, "b = path.read_bytes()", True, "build"),
    ("input", SRC, "f = open('x')", True, "build"),
    ("input", SRC, "a = np.load('z.npy')", True, "build"),
    ("input", SRC, "import numpy\na = numpy.load('z.npy')", True, "build"),
    ("input", SRC, "import os\nv = os.environ['X']", True, "build"),
    ("input", SRC, "import os\nv = os.getenv('X')", True, "build"),
    ("input", SRC, "v = getenv('X')", True, "build"),
    ("input", SRC, "import sys\na = sys.argv[1]", True, "build"),
    ("input", SRC, "line = input()", True, "build"),
    ("input", SRC, "m = sock.recv(1024)", True, "build"),
    ("input", SRC, "h = path.open()", True, "build"),
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
    ("input", SRC, "v = getattr(obj, name)", True, "round 1"),
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
    ("unsafe", ANY, "import yaml\nf = getattr(yaml, name)", True, "round 1: any getattr on yaml"),
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


def _flagged(rule: str, rel: str, source: str) -> bool:
    check = inputs.input_findings if rule == "input" else inputs.unsafe_findings
    return bool(check(rel, source + "\n"))


@pytest.mark.parametrize(
    ("rule", "rel", "source", "flagged", "origin"), CASES, ids=[f"{c[0]}-{c[4]}-{i}" for i, c in enumerate(CASES)]
)
def test_every_reported_spelling_keeps_its_verdict(rule, rel, source, flagged, origin):
    assert _flagged(rule, rel, source) is flagged, (origin, source)


def test_the_corpus_holds_every_round_and_both_verdicts():
    origins = {c[4].split(":")[0] for c in CASES}
    assert {"build", "round 1", "delta 1", "delta 2"} <= origins
    assert {c[3] for c in CASES if c[0] == "input"} == {True, False}
    assert {c[3] for c in CASES if c[0] == "unsafe"} == {True, False}
