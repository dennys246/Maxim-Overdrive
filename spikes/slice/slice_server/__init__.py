"""The vertical slice's server (docs/plans/vertical_slice.md): a throwaway prototype lane, not the engine.

It imports ``simcore`` read-only and changes the world only through records it hands ``Simulation.step``, which applies
them through ``simcore.core.applier``. Nothing here is the
real step 5b (bodies), 7 (protocol) or 8 (tile); each piece is deleted or rebuilt through its step at the end.
"""

WIRE_VERSION = "slice-0"
# The session log's format. A log replays only on the engine it was recorded on, so the version moves with the engine
# as well as the layout: 1 is the first on step 5a's Simulation. The logs before it carry no version and are refused.
LOG_VERSION = "slice-log-1"
