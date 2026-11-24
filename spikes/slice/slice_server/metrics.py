"""A playtest session's numbers, for the verdict note (plan §7; the playtest kit's "Numbers from each session").

Two sources, so nothing is stored twice:

- **Replayed:** the log keeps every intent and the simulation is deterministic, so a replay reproduces the session
  tick by tick. An ``Observer`` watches it: Overdrive seconds, trips, time in the puddle, fires lit and spread, the
  vendor's states, strikes.
- **Read from the log:** what the server recorded beside the intents: the vendor's lines (source, latency, queue
  time) and the tick stats (CPU, overruns).

The replay is trusted only if it ends on the digest the server recorded; ``replay_matches`` says whether it did, and
the report says it loudly when it didn't (a replay that diverged describes some other session).
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from slice_server import LOG_VERSION, alley, config
from slice_server.intents import Intent, parse
from slice_server.sim import Sim

TICK_S = 0.1


@dataclass
class Observer:
    """Counts what happens as a replay runs, one tick at a time."""

    ticks: int = 0
    overdrive_ticks: int = 0
    tripped_ticks: int = 0
    trips: int = 0
    puddle_ticks: int = 0
    puddle_entries: list[float] = field(default_factory=list)  # coolant fraction on each entry
    kindles_ok: int = 0
    kindles_refused: int = 0
    spreads: int = 0
    burnouts: int = 0
    douses: int = 0
    vendor_states: dict[str, int] = field(default_factory=dict)  # state -> times entered
    strikes: int = 0
    overdrive_strikes: int = 0
    _was_tripped: bool = False
    _was_in_puddle: bool = False

    def before(self, sim: Sim) -> None:
        """Read the state the tick starts from: entries into the puddle and trips are judged on it."""
        in_puddle = alley.in_puddle(sim.body.x, sim.body.y)
        if in_puddle and not self._was_in_puddle:
            self.puddle_entries.append(sim.heat.coolant_kg / sim.config.heat.coolant_kg)
        self._was_in_puddle = in_puddle

    def after(self, sim: Sim, events: Sequence[dict[str, object]]) -> None:
        self.ticks += 1
        self.overdrive_ticks += sim.overdrive_on()
        self.tripped_ticks += sim.heat.tripped
        if sim.heat.tripped and not self._was_tripped:
            self.trips += 1
        self._was_tripped = sim.heat.tripped
        self.puddle_ticks += alley.in_puddle(sim.body.x, sim.body.y)
        for event in events:
            self._count(event)

    def _count(self, event: dict[str, object]) -> None:
        what = event["what"]
        if what == "kindle":
            if event["ok"]:
                self.kindles_ok += 1
            else:
                self.kindles_refused += 1
        elif what == "ignited":
            self.spreads += 1
        elif what == "burnt_out":
            self.burnouts += 1
        elif what == "doused":
            self.douses += 1
        elif what == "npc":
            state = str(event["state"])
            self.vendor_states[state] = self.vendor_states.get(state, 0) + 1
        elif what == "strike" and event["ok"]:
            self.strikes += 1
            self.overdrive_strikes += bool(event["overdrive"])


def observe(ticks: Sequence[Sequence[Intent]], *, dx_m: float = 0.2) -> tuple[Observer, Sim]:
    """Replay ``ticks`` (one sequence of intents per tick) and watch it."""
    sim, seen = Sim(config.load(), dx_m=dx_m), Observer()
    for intents in ticks:
        seen.before(sim)
        seen.after(sim, sim.step(list(intents)))
    return seen, sim


@dataclass(frozen=True)
class LogParts:
    dx_m: float
    ticks: list[list[Intent]]
    digest: str | None  # the clean end's, or None
    crashed: bool
    lines: list[dict[str, object]]
    stats: list[dict[str, float]]


def read_log(path: Path) -> LogParts:
    records = [json.loads(line) for line in path.read_text().splitlines()]
    version = records[0]["meta"].get("log") if records and isinstance(records[0].get("meta"), dict) else None
    if version != LOG_VERSION:
        raise ValueError(
            f"{path.name} is a {version or 'pre-version'} log; this slice reads {LOG_VERSION} only (a log replays only"
            " on the engine it was recorded on)"
        )
    dx_m = float(records[0]["meta"]["dx_m"])
    by_tick: dict[int, list[Intent]] = {}
    end = crashed = None
    lines, stats = [], []
    for r in records[1:]:
        if "intents" in r:
            by_tick[int(r["tick"])] = [parse(raw) for raw in r["intents"]]
        lines += [r["line"]] if "line" in r else []
        stats += [r["stats"]] if "stats" in r else []
        end = r.get("end", end)
        crashed = r.get("crashed", crashed)
    if end is not None:
        last = int(end["tick"])
    else:
        last = (int(crashed["tick"]) if crashed is not None else max(by_tick, default=-1)) + 1
    ticks = [by_tick.get(t, []) for t in range(last)]
    return LogParts(dx_m, ticks, None if end is None else str(end["digest"]), crashed is not None, lines, stats)


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, round(0.95 * len(ordered)) - 1)]


def line_numbers(lines: list[dict[str, object]]) -> dict[str, object]:
    latency = [float(line["latency_s"]) for line in lines]  # type: ignore[arg-type]
    queued = [float(line.get("queued_s", 0.0)) for line in lines]  # type: ignore[arg-type]
    canned = [line for line in lines if line["source"] == "canned"]
    return {
        "lines": len(lines),
        "from_model": len(lines) - len(canned),
        "canned": len(canned),
        "canned_reasons": sorted({str(line["why_canned"]) for line in canned}),
        "latency_p95_s": _p95(latency),
        "latency_median_s": statistics.median(latency) if latency else None,
        "queued_p95_s": _p95(queued),
    }


def stat_numbers(stats: list[dict[str, float]]) -> dict[str, object]:
    if not stats:
        return {"windows": 0}
    ticks = sum(s["ticks"] for s in stats)
    return {
        "windows": len(stats),
        "overruns": sum(s["overruns"] for s in stats),
        "overruns_per_50_ticks": sum(s["overruns"] for s in stats) / ticks * 50,
        "tick_cpu_ms_mean": sum(s["tick_cpu_ms_mean"] * s["ticks"] for s in stats) / ticks,
        "tick_cpu_ms_max": max(s["tick_cpu_ms_max"] for s in stats),
        "state_kb_mean": sum(s["state_kb_mean"] * s["ticks"] for s in stats) / ticks,
    }


def session_metrics(path: Path) -> dict[str, object]:
    """Every number the playtest kit asks of a session, with whether the replay can be trusted."""
    parts = read_log(path)
    seen, sim = observe(parts.ticks, dx_m=parts.dx_m)
    minutes = seen.ticks * TICK_S / 60
    counts = {k: v for k, v in asdict(seen).items() if not k.startswith("_")}
    return {
        "log": str(path),
        "replay_matches": parts.digest is not None and sim.digest() == parts.digest,
        "ended": "crashed" if parts.crashed else ("cleanly" if parts.digest is not None else "cut off"),
        "play_minutes": minutes,
        "overdrive_s_per_min": seen.overdrive_ticks * TICK_S / minutes if minutes else 0.0,
        "tripped_s": seen.tripped_ticks * TICK_S,
        "puddle_s": seen.puddle_ticks * TICK_S,
        "replayed": counts,
        "voice": line_numbers(parts.lines),
        "budget": stat_numbers(parts.stats),
    }


def report(m: dict[str, object]) -> str:
    """The numbers as a short text block for the verdict note's working."""
    r = m["replayed"]
    v, b = m["voice"], m["budget"]
    if not (isinstance(r, dict) and isinstance(v, dict) and isinstance(b, dict)):
        raise TypeError("report() takes what session_metrics() returns")
    trust = "replay MATCHES the recorded end" if m["replay_matches"] else (
        f"WARNING: replay does NOT match (the session {m['ended']}); the replayed numbers describe some other run"
    )  # fmt: skip
    out = [
        f"{m['log']}: {trust}",
        f"play: {m['play_minutes']:.1f} min",
        f"Overdrive: {m['overdrive_s_per_min']:.1f} s per minute; trips {r['trips']}, {m['tripped_s']:.0f} s tripped",
        f"puddle: {m['puddle_s']:.0f} s, entered {len(r['puddle_entries'])} times "
        f"(coolant on entry: {', '.join(f'{c:.0%}' for c in r['puddle_entries']) or 'never'})",
        f"fire: {r['kindles_ok']} lit by F ({r['kindles_refused']} refused), {r['spreads']} spread, "
        f"{r['burnouts']} burnt out, {r['douses']} doused",
        f"vendor: {r['vendor_states'] or 'never left idle'}",
        f"strikes: {r['strikes']} ({r['overdrive_strikes']} in Overdrive)",
        f"voice: {v['from_model']} model, {v['canned']} canned {v['canned_reasons'] or ''}; "
        f"latency p95 {v['latency_p95_s']} s, queue p95 {v['queued_p95_s']} s",
        f"budget: {b}",
    ]
    return "\n".join(out)
