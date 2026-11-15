import os

import pytest

from maxim_overdrive.config import MaterialTable, RigProfile

# The 'max' rig takes about a minute per fire scenario. Run it with MAXIM_OVERDRIVE_ALL_TIERS=1.
FAST_TIERS = ["laptop", "rig"]
ALL_TIERS = FAST_TIERS + (["max"] if os.environ.get("MAXIM_OVERDRIVE_ALL_TIERS") else [])


@pytest.fixture(scope="session")
def materials():
    return MaterialTable.load()


@pytest.fixture(params=ALL_TIERS)
def rig(request):
    return RigProfile.load(request.param)


@pytest.fixture
def rigs():
    return [RigProfile.load(t) for t in ALL_TIERS]
