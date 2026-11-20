import os

import pytest

from maxim_overdrive import data

# Physics runs over grid spacings, not rig names: every machine simulates one truth (world_model D20), and the 0.2 m
# and 0.05 m grids are verification grids around it. 0.05 m takes about a minute per fire scenario, so it runs with
# MAXIM_OVERDRIVE_ALL_TIERS=1 (the gate sets it).
FAST_SPACINGS = [0.2, 0.1]
ALL_SPACINGS = FAST_SPACINGS + ([0.05] if os.environ.get("MAXIM_OVERDRIVE_ALL_TIERS") else [])
COARSEST_M = max(FAST_SPACINGS)


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
