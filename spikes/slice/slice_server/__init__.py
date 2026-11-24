"""The vertical slice's server (docs/plans/vertical_slice.md): a throwaway prototype lane, not the engine.

It imports ``simcore`` read-only and changes the world only through records it hands ``Simulation.step``, which applies
them through ``simcore.core.applier``. Nothing here is the
real step 5b (bodies), 7 (protocol) or 8 (tile); each piece is deleted or rebuilt through its step at the end.
"""

WIRE_VERSION = "slice-0"
# The session log's layout (metrics.py reads and writes its header). 1 is the first on step 5a's Simulation; the logs
# before it carry no version and are refused. The header also names the engine's tick and physics cadence, refused
# when they differ; a change to the engine's arithmetic shows as a replay that doesn't match, which the committed log
# in tests/fixtures/ turns red in the gate.
LOG_VERSION = "slice-log-1"
