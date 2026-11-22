"""Damage (sim_core.md §5.1): two laws, ``damage.loads`` (`loads`) per record and ``damage.thermal`` (`thermal`) per
substep, and the load resolvers ``damage.loads`` applies, one module per load kind (`strike`). Neither law destroys a
cell itself: each asks Topology to. The two laws are separate modules so the `laws-independent` import contract holds
them apart; what they share would live in a module that is not a law.
"""

from __future__ import annotations

from simcore.core.damage.loads import LOADS, LoadsLaw
from simcore.core.damage.strike import analytic_crater_radius_m
from simcore.core.damage.thermal import THERMAL, ThermalLaw

__all__ = ["LOADS", "THERMAL", "LoadsLaw", "ThermalLaw", "analytic_crater_radius_m"]
