import os

import pytest

from maxim_overdrive import data

# Physics runs over grid spacings, not rig names: every machine simulates one truth (world_model D20), and the 0.2 m
# and 0.05 m grids are verification grids around it. 0.05 m takes about a minute per fire scenario, so it runs with
# MAXIM_OVERDRIVE_ALL_TIERS=1 (the gate sets it).
FAST_SPACINGS = [0.2, 0.1]
ALL_TIERS = bool(os.environ.get("MAXIM_OVERDRIVE_ALL_TIERS"))
ALL_SPACINGS = FAST_SPACINGS + ([0.05] if ALL_TIERS else [])
COARSEST_M = max(FAST_SPACINGS)
# The fast spacings for a study that takes more than a few seconds at the truth grid since PR 4a moved the scenarios to
# the 0.5 s physics step (twelve steps per old turn): 0.2 m always, 0.1 m as a slow test under the tier variable.
_SLOW = (pytest.mark.slow, pytest.mark.skipif(not ALL_TIERS, reason="slow at 0.1 m; set MAXIM_OVERDRIVE_ALL_TIERS=1"))
TIERED_FAST_SPACINGS = [0.2, pytest.param(0.1, marks=_SLOW)]
TIERED_SPACINGS = TIERED_FAST_SPACINGS + ([0.05] if ALL_TIERS else [])


@pytest.fixture(scope="session")
def materials():
    return data.materials()


@pytest.fixture(params=ALL_SPACINGS)
def dx_m(request):
    return request.param


@pytest.fixture
def spacings():
    return list(ALL_SPACINGS)


@pytest.fixture(scope="session")
def limits():
    return data.action_limits()
