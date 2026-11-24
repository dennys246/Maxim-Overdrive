"""Where the tree's tests live: pyproject's ``testpaths``, the one list the gate runs, read by every scan of tests.

A tests directory outside ``tests/`` belongs to a spike (``spikes/slice/tests``); the spike's own code, its parent
directory, is held to the same scans as the tests that drive it, so a lane that joins the gate joins its guards too.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gate_testpaths() -> tuple[str, ...]:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return tuple(config["tool"]["pytest"]["ini_options"]["testpaths"])


def spike_roots() -> tuple[str, ...]:
    """The spikes whose tests the gate runs: each extra testpath's parent (``spikes/slice``)."""
    return tuple(Path(p).parent.as_posix() for p in gate_testpaths() if p != "tests")
