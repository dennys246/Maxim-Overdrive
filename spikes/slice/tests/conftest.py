"""The slice's tests import ``slice_server`` from ``spikes/slice`` (it is not an installed package)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
