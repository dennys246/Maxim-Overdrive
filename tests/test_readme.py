"""The README's quick start runs as written (PR 4a review, Architecture S4: it called an API PR 4a retired, and no
test ran it). It runs in its own interpreter, as a reader would paste it."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import ALL_TIERS

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


@pytest.mark.slow
@pytest.mark.skipif(not ALL_TIERS, reason="slow: 6000 ticks in a fresh interpreter; set MAXIM_OVERDRIVE_ALL_TIERS=1")
def test_the_readmes_python_example_runs_and_prints_a_reading(tmp_path):
    blocks = re.findall(r"```python\n(.*?)```", README.read_text(), re.S)
    assert len(blocks) == 1, "the README has one Python example; this test runs it"
    example = tmp_path / "readme_example.py"
    example.write_text(blocks[0])
    env = {**os.environ, "PYTHONPATH": f"{ROOT / 'src'}{os.pathsep}{ROOT}"}
    out = subprocess.run(
        [sys.executable, str(example)], cwd=tmp_path, env=env, capture_output=True, text=True, check=True
    )
    assert 0.0 <= float(out.stdout.strip()) < 1.0  # the crate burned some way, and the reading is a ratio
