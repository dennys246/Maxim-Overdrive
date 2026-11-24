"""The playtest numbers: replayed counts, log-read counts, and the trust check."""

import json
from pathlib import Path

import pytest
from slice_server import config
from slice_server.__main__ import main, serve
from slice_server.body import Command
from slice_server.intents import Kindle, Move
from slice_server.metrics import (
    LogRefused,
    Observer,
    line_numbers,
    log_meta,
    observe,
    report,
    session_metrics,
    stat_numbers,
)
from slice_server.sim import Sim

EAST = Move(Command(1.0, 0.0, 1.0))
STOP = Move(Command())


def test_a_demo_shaped_session_counts_the_kindle_and_the_vendors_douse() -> None:
    # The demo's path: walk east 38 ticks, kindle at tick 34, then watch.
    ticks = (
        [[EAST]] + [[] for _ in range(33)] + [[Kindle()]] + [[] for _ in range(3)] + [[STOP]] + [[] for _ in range(150)]
    )
    seen, _ = observe(ticks)
    assert seen.kindles_ok == 1
    assert seen.douses == 1
    assert seen.vendor_states.get("douse") == 1
    assert seen.vendor_states.get("doused") == 1
    assert seen.ticks == len(ticks)


def test_overdrive_seconds_count_only_while_moving_in_overdrive() -> None:
    run = Move(Command(1.0, 0.0, 1.0, overdrive=True))
    held_still = Move(Command(0.0, 0.0, 0.0, overdrive=True))
    seen, _ = observe([[run]] + [[] for _ in range(19)] + [[held_still]] + [[] for _ in range(9)])
    assert seen.overdrive_ticks == 20


def test_walking_into_the_puddle_counts_an_entry_with_the_coolant_left() -> None:
    to_puddle = Move(Command(0.95, -0.31, 1.0))  # from the spawn toward (3.7, 1.0)
    seen, sim = observe([[to_puddle]] + [[] for _ in range(24)] + [[STOP]] + [[] for _ in range(20)])
    assert seen.puddle_ticks > 0, f"ended at ({sim.body.x:.2f}, {sim.body.y:.2f})"
    assert seen.puddle_entries == [pytest.approx(1.0)]


def test_trips_count_each_new_trip_once() -> None:
    sim, seen = Sim(config.load()), Observer()
    for tripped in [0, 5, 5, 0, 0, 5, 0]:
        sim.heat.tripped_s = float(tripped)
        seen.after(sim, [])
    assert seen.trips == 2
    assert seen.tripped_ticks == 3


def test_events_are_counted_by_kind() -> None:
    seen = Observer()
    for event in [
        {"what": "kindle", "ok": False},
        {"what": "ignited"},
        {"what": "burnt_out"},
        {"what": "strike", "ok": True, "overdrive": True},
        {"what": "strike", "ok": True, "overdrive": False},
        {"what": "strike", "ok": False},
    ]:
        seen._count(event)
    assert (seen.kindles_refused, seen.spreads, seen.burnouts) == (1, 1, 1)
    assert (seen.strikes, seen.overdrive_strikes) == (2, 1)


def test_voice_and_budget_numbers_from_the_log() -> None:
    lines = [
        {"source": "llm", "latency_s": 0.2, "queued_s": 0.0, "why_canned": None},
        {"source": "llm", "latency_s": 1.0, "queued_s": 0.8, "why_canned": None},
        {"source": "canned", "latency_s": 2.5, "queued_s": 0.0, "why_canned": "TimeoutError: timed out"},
    ]
    v = line_numbers(lines)
    assert (v["lines"], v["from_model"], v["canned"]) == (3, 2, 1)
    assert v["canned_reasons"] == ["TimeoutError: timed out"]
    assert v["latency_p95_s"] == 2.5
    stats = [
        {"ticks": 50, "overruns": 5, "tick_cpu_ms_mean": 10.0, "tick_cpu_ms_max": 20.0, "state_kb_mean": 1.0},
        {"ticks": 50, "overruns": 0, "tick_cpu_ms_mean": 20.0, "tick_cpu_ms_max": 30.0, "state_kb_mean": 2.0},
    ]
    b = stat_numbers(stats)
    assert b["overruns_per_50_ticks"] == 2.5
    assert b["tick_cpu_ms_mean"] == 15.0
    assert b["tick_cpu_ms_max"] == 30.0


@pytest.mark.parametrize(
    ("meta", "said"),
    [
        ({"dx_m": 0.2, "tick_s": 0.1}, "pre-version log"),  # every log recorded before the port onto Simulation
        ({"log": "slice-log-0", "dx_m": 0.2, "tick_s": 0.1}, "slice-log-0 log"),
        ({**log_meta(0.2, data=config.raw())["meta"], "engine": {"tick_us": 100000, "physics_every": 5}}, "cadence"),
    ],
)
def test_a_log_from_another_engine_is_refused_by_name(tmp_path: Path, capsys, meta: dict, said: str) -> None:
    # A log replays only on the engine it was recorded on: one from before the port would diverge in its last bits
    # and be reported as "does NOT match", which hides why. It is refused instead, saying which log it is.
    log = tmp_path / "old.jsonl"
    log.write_text(json.dumps({"meta": meta}) + "\n" + json.dumps({"end": {"tick": 0, "digest": "0" * 64}}) + "\n")
    with pytest.raises(LogRefused, match=said):
        session_metrics(log)
    for command in ("metrics", "replay"):
        assert main([command, str(log)]) == 2
        assert said in capsys.readouterr().err


def test_a_real_session_log_replays_and_a_tampered_one_is_flagged(tmp_path: Path) -> None:
    serve(0.2, 0, llm=False, root=tmp_path, ticks=5)
    (log,) = (tmp_path / "sessions").iterdir()
    m = session_metrics(log)
    assert m["replay_matches"] is True
    assert m["ended"] == "cleanly"
    assert main(["metrics", str(log)]) == 0
    lines = log.read_text().splitlines()
    end = json.loads(lines[-1])
    end["end"]["digest"] = "0" * 64  # as if the replay had diverged
    log.write_text("\n".join([*lines[:-1], json.dumps(end)]) + "\n")
    tampered = session_metrics(log)
    assert tampered["replay_matches"] is False
    assert "does NOT match" in report(tampered)
    assert main(["metrics", str(log)]) == 1


# The committed session log (CLAUDE.md: "Old fixtures stay committed"): a short scripted session that walks to the
# crate, lights it, strikes it in Overdrive and watches the vendor douse it. A change to the engine that moves the
# slice's replay turns this red in the gate. If the change is meant, rebuild the log with _build_fixture (from
# spikes/slice: ../../.venv/bin/python -c "import sys; sys.path[:0] = ['.', 'tests']; import test_metrics as t;
# t._build_fixture(t.FIXTURE)") and say so in the commit; a new log layout bumps LOG_VERSION and keeps the old file.
FIXTURE = Path(__file__).parent / "fixtures" / "session_slice-log-1.jsonl"


def _script() -> dict[int, list[dict[str, object]]]:
    def move(x: float, y: float, effort: float, overdrive: bool = False) -> dict[str, object]:
        return {"type": "move", "dir": [x, y], "effort": effort, "overdrive": overdrive}

    return {
        0: [move(1.0, 0.18, 1.0)],
        32: [move(0.0, 0.0, 0.0), {"type": "kindle"}],
        33: [move(0.0, 0.0, 0.0, True), {"type": "strike"}],
        34: [move(0.0, 0.0, 0.0)],
    }


def _build_fixture(path: Path, ticks: int = 200) -> None:
    from slice_server.intents import parse  # noqa: PLC0415 - only the rebuild needs it

    sim, script = Sim(config.load(), dx_m=0.2), _script()
    rows = [log_meta(0.2, data=config.raw())]
    for tick in range(ticks):
        raw = script.get(tick, [])
        rows += [{"tick": tick, "intents": raw}] if raw else []
        sim.step([parse(r) for r in raw])
    rows.append({"end": {"tick": ticks, "digest": sim.digest()}})
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def test_the_committed_session_log_still_replays() -> None:
    m = session_metrics(FIXTURE)
    assert m["replay_matches"] is True, "the engine moved the slice's replay; see FIXTURE's comment"
    r = m["replayed"]
    assert isinstance(r, dict)
    assert (r["kindles_ok"], r["strikes"], r["overdrive_strikes"], r["douses"]) == (1, 1, 1, 1)  # it reaches them


def test_a_replay_runs_on_the_data_the_session_was_played_on(monkeypatch: pytest.MonkeyPatch) -> None:
    # Delta 1: a retune of the YAML would have made every earlier playtest log report "does NOT match". The log keeps
    # its data, and the replay reads that, never the files as they are now.
    def retuned() -> config.SliceConfig:
        raise AssertionError("the replay read today's data files")

    monkeypatch.setattr(config, "load", retuned)
    assert session_metrics(FIXTURE)["replay_matches"] is True


@pytest.mark.parametrize(
    ("damage", "said"),
    [
        (lambda text: text[:400], "isn't a whole record"),  # a server killed mid-write
        (lambda text: text.replace('"dx_m": 0.2', '"dx_m": "x"'), "can't be replayed"),
        (lambda text: text.replace('"mass_kg": 80.0', '"mass_kg": -1.0'), "can't be replayed"),
        (lambda text: text.replace('"type": "kindle"', '"type": "fly"'), "can't be replayed"),
        (lambda text: "[1]\n" + text, "isn't a record"),
    ],
)
def test_a_damaged_log_is_refused_by_name(tmp_path: Path, capsys, damage, said: str) -> None:
    # Delta 1 S2: a truncated log, or one with a bad number, crashed the metrics command with a traceback.
    log = tmp_path / "damaged.jsonl"
    log.write_text(damage(FIXTURE.read_text()))
    assert log.read_text() != FIXTURE.read_text(), "a precondition: the damage applied"
    with pytest.raises(LogRefused, match=said):
        session_metrics(log)
    assert main(["metrics", str(log)]) == 2
    assert said in capsys.readouterr().err
