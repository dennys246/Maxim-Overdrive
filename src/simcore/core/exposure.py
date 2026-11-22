"""`source_exposure` (`docs/design/sim_core.md` §3, the energy rule's owner): which value of each heat source stood at
the end of each tick, and the shares a physics step reads. Each live value carries the tick it took effect; each value
that ended inside the step is a closed segment, a `Share` of the ticks it stood. The physics step reads the step's
shares and clears the segments. Ticks are counted as integers. Not a law: the sources' bookkeeping, which heat's
deposit (`simcore.core.deposit`) reads.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

Point = tuple[float, float, float]


class Source(Protocol):
    """What the deposit reads of a heat source (``simcore.core.world.HeatSource``)."""

    @property
    def point_m(self) -> Point: ...

    @property
    def radius_m(self) -> float: ...

    @property
    def power_w(self) -> float: ...


@dataclass(frozen=True)
class Share:
    """One source value's part of a physics step (sim_core.md §3): its key, the value, and the whole ticks of the step
    it stood at the end of. A closed segment of ``source_exposure`` is one of these."""

    key: str
    source: Source
    ticks: int


@dataclass(frozen=True)
class Exposure:
    """A physics step's shares, sorted by key and then tick, and the step's length in ticks."""

    shares: tuple[Share, ...]
    of_ticks: int


def standing(sources: Mapping[str, Source], ticks: int) -> tuple[Share, ...]:
    """Each source standing for all ``ticks`` of a step, in key order: a step no source changed during."""
    return tuple(Share(key, sources[key], ticks) for key in sorted(sources))


class SourceExposure:
    """The live values, each with the tick it took effect, and the closed segments of the current physics step."""

    def __init__(self, sources: Mapping[str, Source], *, tick: int) -> None:
        """``sources`` stand from ``tick``, the first tick of the first physics step (construction's are tick 0's,
        and stand from tick 1)."""
        self._start = tick  # the first tick of the current physics step
        self._live: dict[str, tuple[Source, int]] = {key: (sources[key], tick) for key in sorted(sources)}
        self._closed: list[Share] = []  # in the order the values ended, so per key in tick order

    @property
    def closed(self) -> tuple[Share, ...]:
        """The values that ended inside the current step, sorted by key and then tick (§9 member 3)."""
        return tuple(sorted(self._closed, key=lambda s: s.key))  # stable: each key's segments stay in tick order

    def end_tick(self, tick: int, sources: Mapping[str, Source]) -> None:
        """Record the sources standing at the end of ``tick``, after its records applied. A value doused or replaced
        at ``tick`` stood at the end of the ticks before it, back to the step's start, and becomes a closed segment;
        an equal value set again (a douse and a re-ignite alike in one tick) didn't change, so it stays live."""
        for key, (value, since) in list(self._live.items()):
            if sources.get(key) != value:
                del self._live[key]
                ticks = tick - max(since, self._start)
                if ticks > 0:  # replaced at the step's first tick: it stood at the end of none of this step's ticks
                    self._closed.append(Share(key, value, ticks))
        for key in sorted(sources):
            if key not in self._live:
                self._live[key] = (sources[key], tick)

    def step(self, tick: int) -> Exposure:
        """The physics step ending at ``tick`` (after `end_tick` for it): every value's share of its ticks, sorted by
        key and then tick. Clears the closed segments; the live values stand on into the next step."""
        of_ticks = tick - self._start + 1
        live = [Share(key, value, tick - max(since, self._start) + 1) for key, (value, since) in self._live.items()]
        shares = tuple(sorted([*self._closed, *live], key=lambda s: s.key))  # stable: closed before live, per key
        self._closed, self._start = [], tick + 1
        return Exposure(shares, of_ticks)
