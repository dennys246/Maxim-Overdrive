"""The physics step: a fixed ordered tuple of laws, substeps from the minimum stable_dt, Lie or Strang splitting.

One physics step covers 5 ticks (0.5 s, T3). Its substep count is fixed at the step's start:
    n = refine * max(1, ceil(0.5 / min_law stable_dt(state)))
so the substep dt = 0.5 / n is an exact rational of the physics step and time is counted in integers (no float
``elapsed += dt`` accumulation, which heat.py has). ``refine`` = 10 gives 3c's reference.

Lie:    L1(dt) L2(dt) ... Lk(dt)
Strang: L1(dt/2) ... L(k-1)(dt/2) Lk(dt) L(k-1)(dt/2) ... L1(dt/2)
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from laws import Ledger
from model import PHYSICS_TICKS, PILOT_START_TICK, PILOT_TICKS, STABILITY_SAFETY, TICK_S, C, State

PHYSICS_S = PHYSICS_TICKS * TICK_S


def pilot_overlap(tick_end: int) -> int:
    """tile §3.2: the physics step at tick t covers (t-5, t]; how many of its ticks the pilot [start, stop) covers."""
    start, stop = PILOT_START_TICK, PILOT_START_TICK + PILOT_TICKS
    return max(0, min(tick_end + 1, stop) - max(tick_end - PHYSICS_TICKS + 1, start))


def min_stable_dt(laws: Sequence, s: State) -> tuple[float, str]:
    best, who = math.inf, ""
    for law in laws:
        d = law.stable_dt(s)
        if d < best:
            best, who = d, law.name
    return best, who


class Stats:
    def __init__(self) -> None:
        self.substeps_hist: dict[int, int] = {}
        self.limiter: dict[str, int] = {}
        self.audit_violations = 0  # substeps whose dt exceeded the un-safetied bound of the state they started from
        self.worst_audit_ratio = 0.0


def physics_step(
    laws: Sequence, s: State, ledger: Ledger, *, scheme: str, refine: int, stats: Stats, audit: bool
) -> None:
    s.tick += PHYSICS_TICKS
    overlap = pilot_overlap(s.tick)
    s.pilot_w = C("pilot_power") * TICK_S * overlap / PHYSICS_S  # P x 0.1 s per tick, as a mean power over the step
    s.pilot_ticks += overlap
    dt_bound, who = min_stable_dt(laws, s)
    n = refine * max(1, math.ceil(PHYSICS_S / dt_bound))
    dt = PHYSICS_S / n
    stats.substeps_hist[n] = stats.substeps_hist.get(n, 0) + 1
    stats.limiter[who] = stats.limiter.get(who, 0) + 1
    for i in range(n):
        if audit and i > 0:
            bound, _ = min_stable_dt(laws, s)
            ratio = dt / (bound / STABILITY_SAFETY)
            stats.worst_audit_ratio = max(stats.worst_audit_ratio, ratio)
            if ratio > 1.0:
                stats.audit_violations += 1
        _substep(laws, s, dt, ledger, scheme)


def _substep(laws: Sequence, s: State, dt: float, ledger: Ledger, scheme: str) -> None:
    if scheme == "lie":
        for law in laws:
            law.step(s, dt, ledger)
    elif scheme == "strang":
        half = 0.5 * dt
        for law in laws[:-1]:
            law.step(s, half, ledger)
        laws[-1].step(s, dt, ledger)
        for law in reversed(laws[:-1]):
            law.step(s, half, ledger)
    else:
        raise ValueError(scheme)


def check_bounds(s: State, lo: float, hi: float) -> list[str]:
    bad = []
    for name, a in (("T", s.T), ("Ts", s.Ts), ("mw", s.mw), ("mc", s.mc)):
        if not np.all(np.isfinite(a)):
            bad.append(f"{name} non-finite")
    if np.min(s.T) < lo or np.max(s.T) > hi:
        bad.append(f"T out of [{lo},{hi}]: {np.min(s.T):.3f}..{np.max(s.T):.3f}")
    if np.min(s.Ts) < lo or np.max(s.Ts) > hi:
        bad.append(f"Ts out of [{lo},{hi}]: {np.min(s.Ts):.3f}..{np.max(s.Ts):.3f}")
    if np.min(s.mw) < 0 or np.min(s.mc) < 0:
        bad.append("negative mass")
    return bad
