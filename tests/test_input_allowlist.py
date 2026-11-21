"""Only the file gates read input, fail closed (boundaries §5.2, B-4; step 3b delta round 4).

The rule is three allowlists (``tests/_imports.py``): each layer's external imports, what non-gate code may take
from a gate, and the attributes the game's data locator may use. A route nobody named is refused. Each test plants
what a review found getting past the earlier denylist and watches it go red.
"""

from __future__ import annotations

import shutil
from collections import defaultdict
from pathlib import Path

import pytest

from tests import _imports

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def real_imports() -> dict[str, list[str]]:
    return _imports.external_imports(ROOT)


def test_every_layer_imports_only_the_externals_its_allowlist_names(real_imports):
    assert _imports.allowlist_violations(real_imports) == []


def test_each_allowlist_names_exactly_what_its_layer_imports_today(real_imports):
    used: dict[str, set[str]] = defaultdict(set)
    for module, externals in real_imports.items():
        used[_imports._layer(module)] |= set(externals)
    assert {layer: set(allowed) for layer, allowed in _imports.ALLOWED.items()} == {
        layer: used[layer] for layer in _imports.ALLOWED
    }


# One plant per route; delta round 4 (D4-S1) found the first group past the denylist contract.
PLANTS = {
    "io_c": "import _io\nt = _io.open(p).read()",
    "xml": "import xml.etree.ElementTree as ET\nt = ET.parse(p)",
    "inspect": "import inspect\nt = inspect.getsource(f)",
    "genericpath": "import genericpath\nok = genericpath.exists(p)",
    "wave": "import wave\nw = wave.open(p)",
    "logging_config": "import logging.config\nlogging.config.fileConfig(p)",
    "zipimport": "import zipimport",
    "posixpath": "import posixpath\nh = posixpath.expanduser('~')",
    "platform": "import platform\nn = platform.node()",
    "getpass": "import getpass\nu = getpass.getuser()",
    "pwd": "import pwd",
    "locale": "import locale",
    "sysconfig": "import sysconfig",
    "site": "import site",
    "netrc": "import netrc",
    "socket_c": "import _socket",
    "posixsubprocess": "import _posixsubprocess",
    "futures": "from concurrent.futures import ProcessPoolExecutor",
    "signal": "import signal",
    "fcntl": "import fcntl",
    "scipy_io": "from scipy.io import loadmat\nm = loadmat(p)",  # scipy is a package the protocol doesn't hold
    # the families the earlier contract named, so the allowlist is shown to cover them too
    "os": "import os\nv = os.environ.get('X')",
    "pathlib": "from pathlib import Path\nt = Path(p).read_text()",  # delta round 4, S-d: tiers' route
    "urllib": "from urllib.request import urlopen",
    "subprocess": "import subprocess",
    "importlib": "import importlib",
    "json": "import json",
    "pickle": "import pickle",
}


@pytest.fixture(scope="module")
def planted_imports(tmp_path_factory) -> dict[str, list[str]]:
    tree = tmp_path_factory.mktemp("plants")
    shutil.copytree(ROOT / "src", tree / "src", ignore=shutil.ignore_patterns("__pycache__"))
    for name, source in PLANTS.items():
        (tree / "src" / "simcore" / "protocol" / f"_plant_{name}.py").write_text(source + "\n")
    (tree / "src" / "simcore" / "core" / "_plant_core_os.py").write_text("import os\n")
    (tree / "src" / "simcore" / "adapters" / "loaders.py").write_text(
        (ROOT / "src" / "simcore" / "adapters" / "loaders.py").read_text() + "\nimport importlib\n"
    )  # a gate gets only what its allowlist names
    return _imports.external_imports(tree)


@pytest.mark.parametrize("name", [*PLANTS, "core_os"])
def test_a_planted_input_route_is_refused_by_the_allowlist(planted_imports, name):
    module = f"simcore.protocol._plant_{name}" if name != "core_os" else "simcore.core._plant_core_os"
    assert any(v.startswith(f"{module} imports") for v in _imports.allowlist_violations(planted_imports)), name


def test_a_gate_gets_no_import_its_allowlist_doesnt_name(planted_imports):
    assert "simcore.adapters.loaders imports importlib, which simcore.adapters.loaders's allowlist doesn't name" in (
        _imports.allowlist_violations(planted_imports)
    )


# -- what code outside the gates may take from a gate (delta round 4, D4-S2) ------------------------------------------


def _src_modules():
    for path in sorted((ROOT / "src").rglob("*.py")):
        rel = path.relative_to(ROOT / "src").with_suffix("")
        yield ".".join(rel.parts).removesuffix(".__init__"), path


def test_code_outside_the_gates_takes_only_their_api():
    found = [hit for module, path in _src_modules() for hit in _imports.gate_reexports(module, path.read_text())]
    assert found == []


@pytest.mark.parametrize(
    "line",
    [
        "from simcore.adapters.loaders import Path\nt = Path(p).read_text()",
        "from simcore.adapters.loaders import yaml\nd = yaml.safe_load(s)",
        "from simcore.adapters import loaders\nd = loaders.yaml.safe_load(s)",
        "import simcore.adapters.loaders as L\nP = L.Path",
        "from maxim_overdrive.data import Path",
        "from maxim_overdrive import data\nr = data.RIG_NAME",
        "import simcore.adapters.loaders as L\nP = getattr(L, '_StrictLoader')",  # defined, but not the gate's API
    ],
)
def test_a_name_taken_from_a_gate_beyond_its_all_is_refused(line):
    assert _imports.gate_reexports("simcore.protocol.encoding", line + "\n"), line


def test_every_gate_declares_its_api():
    for gate in _imports.GATES:
        assert _imports._gate_all(gate), gate


# -- the modules that hold a path do path arithmetic only (delta rounds 4 and 5: Executor S-d, N-g) --------------------

HOLDERS = {
    "maxim_overdrive.data": ROOT / "src" / "maxim_overdrive" / "data.py",
    "simcore.protocol.tiers": ROOT / "src" / "simcore" / "protocol" / "tiers.py",
}


@pytest.mark.parametrize("module", HOLDERS)
def test_a_path_holder_uses_only_path_arithmetic_and_what_it_names(module):
    assert _imports.path_holder_violations(module, HOLDERS[module].read_text()) == []


@pytest.mark.parametrize("module", HOLDERS)
@pytest.mark.parametrize(
    "line",
    [
        "t = Path(p).read_text()",
        "ok = Path(p).is_dir()",
        "for f in Path(p).iterdir():\n    pass",
        "h = Path(p).open()",
        "Path(p).write_text('x')",
        "q = Path(p).resolve()",  # realpath reads the filesystem: the gate does it
        "def f(path):\n    return path.read_text()",  # a path handed in (N-g)
        "t = getattr(Path(p), 'read_text')()",  # by literal name (N-g)
    ],
)
def test_a_path_method_that_touches_the_filesystem_is_refused_in_a_path_holder(module, line):
    source = HOLDERS[module].read_text() + "\n" + line + "\n"
    assert _imports.path_holder_violations(module, source), line


# -- every external name, by its dotted name (delta rounds 5 and 6, D5-S1, D6-S1) ------------------------------


def test_each_layer_reaches_only_the_external_names_it_lists():
    found = [v for module, path in _src_modules() for v in _imports.external_name_violations(module, path.read_text())]
    assert found == []


def test_each_name_list_names_exactly_what_its_layer_uses_today():
    used: dict[str, set[str]] = defaultdict(set)
    for module, path in _src_modules():
        used[_imports._layer(module)] |= _imports.external_names(path.read_text())
    assert {layer: set(names) for layer, names in _imports.EXTERNAL_NAMES.items()} == {
        layer: used[layer] for layer in _imports.EXTERNAL_NAMES
    }


@pytest.mark.parametrize(
    "line",
    [
        "a = np.lib._npyio_impl.load(p)",
        "a = np.lib._format_impl.read_array(f)",
        "a = np.rec.fromfile(p)",
        "lib = np.ctypeslib.load_library('x', '.')",
        "import scipy.sparse\nm = scipy.sparse.load_npz(p)",
        "a = np.load(p)",
        "from numpy.lib.npyio import load",
        "f = np\na = f.load(p)",  # numpy as a value is itself a name the core doesn't list
    ],
)
def test_a_numpy_or_scipy_name_no_layer_lists_is_refused(line):
    source = "import numpy as np\n" + line + "\n"
    assert _imports.external_name_violations("simcore.core.x", source), line


# -- what one internal module may take from another (delta round 5, D5-S2) ---------------------------------------


def test_no_module_takes_a_name_another_only_imported():
    found = [v for module, path in _src_modules() for v in _imports.internal_reexports(module, path.read_text())]
    assert found == []


@pytest.mark.parametrize(
    "line",
    [
        "from simcore.core.grid import np",
        "from simcore.core.grid import np as n\na = n.load(p)",
        "import simcore.core.grid as g\na = g.np.load(p)",
        "from simcore.core import grid\na = grid.np",
        "import simcore\na = simcore.core.grid.np",
        "import simcore.adapters.loaders as L\nP = getattr(L, 'Path')",  # by literal name (N-g)
    ],
)
def test_a_name_taken_through_another_internal_module_is_refused(line):
    assert _imports.internal_reexports("simcore.adapters.sem.x", line + "\n"), line


def test_a_name_a_module_defines_or_a_submodule_may_be_taken():
    clean = "from simcore.core.grid import MaterialGrid\nfrom simcore.core import grid\nx = grid.MaterialGrid.empty\n"
    assert _imports.internal_reexports("simcore.adapters.sem.x", clean) == []


@pytest.mark.parametrize(
    "line",
    [  # delta round 6, Trust D6-S1: allowed stdlib modules carry others with them
        "import reprlib\nt = reprlib.builtins.open(p).read()",
        "import contextlib\ne = contextlib.os.environ.get('X')",
        "import dataclasses\nb = dataclasses.sys.modules['pickle'].loads(raw)",
        "from dataclasses import sys\ne = sys.modules['os'].environ",
        "import typing\na = typing.sys.argv",
        "import collections\nm = collections._sys.modules['os']",
        "import math as m\nf = m.__loader__",
    ],
)
def test_a_module_reached_through_an_allowed_one_is_refused(line):
    assert _imports.external_name_violations("simcore.core.x", line + "\n"), line


def test_the_names_the_core_uses_today_are_allowed():
    clean = "import math\nfrom dataclasses import dataclass\nfrom typing import Protocol\nr = math.sqrt(2.0)\n"
    assert _imports.external_name_violations("simcore.core.x", clean) == []
