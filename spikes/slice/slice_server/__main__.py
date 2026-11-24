"""Run the slice: ``python -m slice_server`` serves; ``python -m slice_server replay <log>`` checks a session.

Run from ``spikes/slice`` with the worktree's venv: ``cd spikes/slice && ../../.venv/bin/python -m slice_server``.
"""

from __future__ import annotations

import argparse
import json
import secrets
import signal
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from slice_server import config, intents
from slice_server.metrics import LogRefused, log_meta, read_log, report, session_metrics
from slice_server.server import Server, write_run_file
from slice_server.sim import Sim, replay
from slice_server.voice import Voice, ollama

HERE = Path(__file__).resolve().parents[1]


def _new_log(sessions: Path) -> Path:
    """A session log that never overwrites another: the time, then a counter if two launches share a second."""
    sessions.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    for n in range(1000):
        path = sessions / (f"{stamp}.jsonl" if n == 0 else f"{stamp}-{n}.jsonl")
        try:
            path.touch(exist_ok=False)
        except FileExistsError:
            continue
        return path
    raise RuntimeError(f"no free session log name for {stamp} in {sessions}")


def serve(dx_m: float, port: int, *, llm: bool, root: Path = HERE, ticks: int | None = None) -> None:
    """Serve until Ctrl-C (or for ``ticks`` ticks), writing the run file and the session log under ``root``."""
    log_path = _new_log(root / "sessions")
    token = secrets.token_hex(16)
    with log_path.open("w") as log:
        meta = json.dumps(log_meta(dx_m, data=config.raw()))
        log.write(meta + "\n")
        # The session runs on the logged data as a replay reads it (through JSON), so the two parse the same values.
        cfg = config.parse(json.loads(meta)["meta"]["data"])
        # Engine choice: the voice talks to Ollama on 127.0.0.1 with stdlib urllib, so the slice adds no dependency.
        voice = Voice(cfg.npc.voice, cfg.npc.canned, ollama(cfg.npc.voice) if llm else None)
        server = Server(Sim(cfg, dx_m=dx_m), token=token, log=log, port=port, voice=voice)
        write_run_file(root / "run" / "session.json", server.port, token)
        print(f"slice: 127.0.0.1:{server.port}, logging to {log_path}", flush=True)
        # Ctrl-C and SIGTERM only ask: KeyboardInterrupt would land mid-tick, half an advance into the final digest,
        # and that session would fail replay (it did, once, on a loaded machine).
        previous = {sig: signal.signal(sig, lambda *_: server.stop()) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            server.run(ticks)
        except BaseException:
            server.close(clean=False)  # the log says where it crashed and keeps that tick for replay
            raise
        else:
            server.close()
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            print("slice: stopped", flush=True)


def ticks_of(log_path: Path) -> tuple[float, list[list[intents.Intent]], str | None]:
    """A session log's grid spacing, its intents per tick, and the digest it ended with, if it ended cleanly. A crashed
    session's ticks run through the tick that crashed, so a replay reaches the crash; one cut off with no marker runs
    to its last logged intent. (``metrics.read_log`` is the one reader of the log's format.)"""
    parts = read_log(log_path)
    return parts.dx_m, parts.ticks, parts.digest


def check_replay(log_path: Path) -> bool:
    parts = read_log(log_path)
    got, recorded, ticks = replay(parts.cfg, parts.ticks, dx_m=parts.dx_m), parts.digest, parts.ticks
    print(f"replayed {len(ticks)} ticks: {got}")
    if recorded is None:
        print("the session didn't end cleanly, so there is no digest to compare")
        return False
    print("MATCH" if got == recorded else f"MISMATCH: recorded {recorded}")
    return got == recorded


def _check(args: argparse.Namespace) -> int:
    if args.cmd == "replay":
        return 0 if check_replay(args.log) else 1
    m = session_metrics(args.log)
    print(json.dumps(m, indent=2) if args.json else report(m))
    return 0 if m["replay_matches"] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slice_server")
    sub = parser.add_subparsers(dest="cmd")
    run = sub.add_parser("serve")
    run.add_argument("--dx", type=float, default=0.2)
    run.add_argument("--port", type=int, default=0)
    run.add_argument("--no-llm", action="store_true", help="canned vendor lines only (the cut list's first cut)")
    check = sub.add_parser("replay")
    check.add_argument("log", type=Path)
    numbers = sub.add_parser("metrics", help="a playtest session's numbers, by replaying its log")
    numbers.add_argument("log", type=Path)
    numbers.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd in ("replay", "metrics"):
        try:
            return _check(args)
        except LogRefused as exc:  # a log this slice can't read: say which and why, as the command's result
            print(f"slice_server {args.cmd}: {exc}", file=sys.stderr)
            return 2
    serve(getattr(args, "dx", 0.2), getattr(args, "port", 0), llm=not getattr(args, "no_llm", False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
