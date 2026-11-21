"""One discretisation, and the exact work it took."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Run:
    """A discretisation: grid spacing ``dx_m``, physics step ``dt_s`` and the number of steps."""

    dx_m: float
    dt_s: float
    steps: int

    def __post_init__(self) -> None:
        if not (math.isfinite(self.dx_m) and self.dx_m > 0):
            raise ValueError(f"dx_m must be finite and positive, got {self.dx_m!r}")
        if not (math.isfinite(self.dt_s) and self.dt_s > 0):
            raise ValueError(f"dt_s must be finite and positive, got {self.dt_s!r}")
        if isinstance(self.steps, bool) or not isinstance(self.steps, int) or self.steps < 1:
            raise ValueError(f"steps must be a whole number of at least 1, got {self.steps!r}")

    @property
    def seconds(self) -> float:
        """The simulated time this run covers."""
        return self.dt_s * self.steps

    def refined_in_time(self, factor: int) -> Run:
        """The same run with ``factor`` times as many steps, each ``factor`` times shorter."""
        return Run(self.dx_m, self.dt_s / factor, self.steps * factor)


@dataclass(frozen=True)
class Work:
    """Exact, deterministic work counters for one run: never wall time (world_v2's performance counters)."""

    substeps: int
    cell_substeps: int
