"""The vertical slice's server (docs/plans/vertical_slice.md): a throwaway prototype lane, not the engine.

It imports ``simcore`` read-only and changes the world only through ``simcore.core.applier``. Nothing here is the
real step 5b (bodies), 7 (protocol) or 8 (tile); each piece is deleted or rebuilt through its step at the end.
"""

WIRE_VERSION = "slice-0"
