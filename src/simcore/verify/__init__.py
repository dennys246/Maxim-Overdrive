"""The verification harness (``docs/design/verify_harness.md``): convergence, bands and splitting, in one vocabulary.

The harness measures; it never builds state. A test hands it observables (callables of a ``Run``) and it returns
frozen results. It imports nothing from the engine, so it can't reach a ``World`` (boundaries layer 8).
"""

from simcore.verify.bands import Band, band_gate
from simcore.verify.convergence import Convergence, converges
from simcore.verify.runs import Run, Work
from simcore.verify.splitting import same_class_under_refinement

__all__ = ["Band", "Convergence", "Run", "Work", "band_gate", "converges", "same_class_under_refinement"]
