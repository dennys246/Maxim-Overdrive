"""The playtest numbers: replayed counts, log-read counts, and the trust check."""

import json
from pathlib import Path

import pytest
from slice_server import config
from slice_server.__main__ import main, serve
from slice_server.body import Command
from slice_server.intents import Kindle, Move
from slice_server.metrics import Observer, line_numbers, observe, report, session_metrics, stat_numbers
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
    ],
)
def test_a_log_from_another_engine_is_refused_by_name(tmp_path: Path, capsys, meta: dict, said: str) -> None:
    # A log replays only on the engine it was recorded on: one from before the port would diverge in its last bits
    # and be reported as "does NOT match", which hides why. It is refused instead, saying which log it is.
    log = tmp_path / "old.jsonl"
    log.write_text(json.dumps({"meta": meta}) + "\n" + json.dumps({"end": {"tick": 0, "digest": "0" * 64}}) + "\n")
    with pytest.raises(ValueError, match=said):
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
