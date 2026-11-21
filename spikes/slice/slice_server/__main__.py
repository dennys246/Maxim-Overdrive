"""Run the slice: ``python -m slice_server`` serves; ``python -m slice_server replay <log>`` checks a session.

Run from ``spikes/slice`` with the worktree's venv: ``cd spikes/slice && ../../.venv/bin/python -m slice_server``.
"""

from __future__ import annotations

import argparse
import json
import secrets
import signal
import time
from collections.abc import Sequence
from pathlib import Path

from slice_server import config, intents
from slice_server.server import Server, write_run_file
from slice_server.sim import Sim, replay

HERE = Path(__file__).resolve().parents[1]


def serve(dx_m: float, port: int) -> None:
    sessions = HERE / "sessions"
    sessions.mkdir(exist_ok=True)
    log_path = sessions / f"{time.strftime('%Y%m%dT%H%M%S')}.jsonl"
    token = secrets.token_hex(16)
    with log_path.open("w") as log:
        log.write(json.dumps({"meta": {"dx_m": dx_m, "tick_s": 0.1}}) + "\n")
        server = Server(Sim(config.load(), dx_m=dx_m), token=token, log=log, port=port)
        write_run_file(HERE / "run" / "session.json", server.port, token)
        print(f"slice: 127.0.0.1:{server.port}, logging to {log_path}", flush=True)
        # Ctrl-C and SIGTERM only ask: KeyboardInterrupt would land mid-tick, half an advance into the final digest,
        # and that session would fail replay (it did, once, on a loaded machine).
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: server.stop())
        try:
            server.run()
        finally:
            print("slice: stopping", flush=True)
            server.close()


def ticks_of(log_path: Path) -> tuple[float, list[list[intents.Intent]], str | None]:
    """A session log's grid spacing, its intents per tick, and the digest it ended with, if it ended cleanly."""
    lines = [json.loads(line) for line in log_path.read_text().splitlines()]
    dx_m, by_tick, end = float(lines[0]["meta"]["dx_m"]), {}, None
    for line in lines[1:]:
        if "intents" in line:
            by_tick[int(line["tick"])] = [intents.parse(raw) for raw in line["intents"]]
        if "end" in line:
            end = line["end"]
    if end is None:
        return dx_m, [by_tick.get(t, []) for t in range(max(by_tick, default=-1) + 1)], None
    return dx_m, [by_tick.get(t, []) for t in range(int(end["tick"]))], str(end["digest"])


def check_replay(log_path: Path) -> bool:
    dx_m, ticks, recorded = ticks_of(log_path)
    got = replay(config.load(), ticks, dx_m=dx_m)
    print(f"replayed {len(ticks)} ticks: {got}")
    if recorded is None:
        print("the session didn't end cleanly, so there is no digest to compare")
        return False
    print("MATCH" if got == recorded else f"MISMATCH: recorded {recorded}")
    return got == recorded


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slice_server")
    sub = parser.add_subparsers(dest="cmd")
    run = sub.add_parser("serve")
    run.add_argument("--dx", type=float, default=0.2)
    run.add_argument("--port", type=int, default=0)
    check = sub.add_parser("replay")
    check.add_argument("log", type=Path)
    args = parser.parse_args(argv)
    if args.cmd == "replay":
        return 0 if check_replay(args.log) else 1
    serve(getattr(args, "dx", 0.2), getattr(args, "port", 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
