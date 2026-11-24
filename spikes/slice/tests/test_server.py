"""The server end to end on a real localhost socket (port 0): handshake, refusals, states, and replay of its log."""

import contextlib
import io
import json
import select
import socket
import stat
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from slice_server import LOG_VERSION, WIRE_VERSION, config
from slice_server.__main__ import check_replay, main, serve, ticks_of
from slice_server.intents import parse as parse_intent
from slice_server.server import Client, Server
from slice_server.sim import Sim
from slice_server.voice import Voice
from slice_server.wire import FrameReader, encode

TOKEN = "t" * 32
META = json.dumps({"meta": {"log": LOG_VERSION, "dx_m": 0.2, "tick_s": 0.1}}) + "\n"


@contextmanager
def serving(ticks: int) -> Iterator[tuple[Server, io.StringIO]]:
    log = io.StringIO()
    log.write(META)
    server = Server(Sim(config.load()), token=TOKEN, log=log)
    thread = threading.Thread(target=server.run, args=(ticks,))
    thread.start()
    try:
        yield server, log
    finally:
        thread.join(timeout=30)
        server.close()
    assert not thread.is_alive()


def _messages(sock: socket.socket, until: int) -> list[dict]:
    """Read frames until ``until`` have arrived or the server closes."""
    reader, got = FrameReader(), []
    sock.settimeout(10)
    while len(got) < until:
        data = sock.recv(65536)
        if not data:
            break
        got += list(reader.feed(data))
    return got


def _hello(token: str = TOKEN) -> bytes:
    return encode({"type": "hello", "version": WIRE_VERSION, "token": token})


def test_a_session_handshakes_receives_states_and_replays(tmp_path: Path) -> None:
    with serving(ticks=12) as (server, log), socket.create_connection(("127.0.0.1", server.port)) as sock:
        sock.sendall(_hello())
        sock.sendall(encode({"type": "move", "dir": [1, 0], "effort": 1, "overdrive": False}))
        sock.sendall(encode({"type": "move", "dir": "east"}))
        got = _messages(sock, until=6)
    assert got[0]["type"] == "welcome"
    assert got[0]["shape"] == [60, 20, 24]
    assert any(m["type"] == "error" and m["code"] == "bad_intent" for m in got), "a bad intent gets a reply"
    assert any(m["type"] == "state" for m in got), "and the connection stays up"
    path = tmp_path / "session.jsonl"
    path.write_text(log.getvalue())
    assert check_replay(path)


@pytest.mark.parametrize(
    ("first", "code"),
    [
        (_hello("wrong"), "bad_hello"),
        (encode({"type": "move", "dir": [1, 0], "effort": 1, "overdrive": False}), "bad_hello"),
        (b"POST / HTTP/1.1\r\nOrigin: http://evil.example\r\n\r\n", "http_refused"),
    ],
)
def test_a_bad_first_frame_is_refused_and_closed(first: bytes, code: str) -> None:
    with serving(ticks=5) as (server, _), socket.create_connection(("127.0.0.1", server.port)) as sock:
        sock.sendall(first)
        got = _messages(sock, until=99)  # reads to the close
    assert [m["code"] for m in got] == [code]


def test_it_binds_only_to_localhost() -> None:
    with serving(ticks=1) as (server, _):
        assert server._listener.getsockname()[0] == "127.0.0.1"


def test_a_client_that_has_not_said_hello_is_sent_nothing() -> None:
    # Ticks run while this client stays silent; the server must not stream the world to an unauthenticated peer.
    with serving(ticks=3) as (server, _), socket.create_connection(("127.0.0.1", server.port)) as sock:
        reader, got = FrameReader(), []
        sock.settimeout(0.6)  # three 0.1 s ticks pass inside this wait
        with contextlib.suppress(TimeoutError):  # the expected end: nothing arrives before the wait runs out
            while data := sock.recv(65536):
                got += list(reader.feed(data))
    assert got == []


def test_stop_ends_the_loop_between_ticks_so_the_last_digest_replays(tmp_path: Path) -> None:
    # A Ctrl-C used to raise KeyboardInterrupt mid-tick, leaving half an advance in the final digest (a real session
    # failed replay that way). stop() only asks; the loop finishes its tick and returns.
    log = io.StringIO()
    log.write(META)
    server = Server(Sim(config.load()), token=TOKEN, log=log)
    thread = threading.Thread(target=server.run, daemon=True)  # no tick limit: only stop() ends it; daemon so a
    # missing stop fails the test instead of hanging pytest
    thread.start()
    with socket.create_connection(("127.0.0.1", server.port)) as sock:
        sock.sendall(_hello())
        sock.sendall(encode({"type": "move", "dir": [1, 0], "effort": 1, "overdrive": False}))
        _messages(sock, until=4)
        server.stop()
        thread.join(timeout=30)
    assert not thread.is_alive()
    server.close()
    path = tmp_path / "session.jsonl"
    path.write_text(log.getvalue())
    assert check_replay(path)


def test_a_change_of_the_vendors_state_sends_a_line_and_logs_it(tmp_path: Path) -> None:
    cfg = config.load()
    log = io.StringIO()
    log.write(META)
    sim = Sim(cfg)
    server = Server(sim, token=TOKEN, log=log, voice=Voice(cfg.npc.voice, cfg.npc.canned, None))
    thread = threading.Thread(target=server.run, args=(30,), daemon=True)
    thread.start()
    got: list[dict] = []
    try:
        with socket.create_connection(("127.0.0.1", server.port)) as sock:
            sock.sendall(_hello())
            sock.sendall(encode({"type": "say", "text": "two bowls, please"}))
            reader = FrameReader()
            sock.settimeout(10)
            while not any(m["type"] == "npc_line" for m in got):  # until the line arrives, not until a close
                data = sock.recv(65536)
                if not data:
                    break
                got += list(reader.feed(data))
                if sim.vendor_state == "idle" and any(m["type"] == "welcome" for m in got):
                    # Once this client is in, stage a change: the vendor's next tick, back to idle, is a new state.
                    sim.vendor_state = "warn"
    finally:
        thread.join(timeout=30)
        server.close()
    lines = [m for m in got if m["type"] == "npc_line"]
    assert lines, "a line reached the client"
    assert lines[0]["source"] == "canned"
    assert lines[0]["text"] in cfg.npc.canned[lines[0]["state"]]
    assert '"line":' in log.getvalue(), "and the session log"
    path = tmp_path / "session.jsonl"
    path.write_text(log.getvalue())
    assert check_replay(path), "a session with words and lines in it still replays"


def test_the_server_runs_past_its_stats_report() -> None:
    # A stray line in _report once broke every session at tick 50, after every other test had stopped short of it.
    cfg = config.load()
    server = Server(Sim(cfg), token=TOKEN, log=io.StringIO(), voice=Voice(cfg.npc.voice, cfg.npc.canned, None))
    try:
        server.run(ticks=55)
    finally:
        server.close()
    assert server.sim.tick == 55


# --- review round (2026-11-21): reproductions written red-first --------------------------------------------------


def test_a_client_that_drops_mid_batch_does_not_crash_the_server() -> None:
    # Executor S2: the error reply's send failed and dropped the client, then the next frame in the same batch
    # asserted a client existed.
    server = Server(Sim(config.load()), token=TOKEN, log=io.StringIO())
    a, b = socket.socketpair()
    a.setblocking(False)
    server._client = Client(a)
    server._client.authed = True
    server._sel.register(a, 1)
    b.sendall(encode({"type": "bogus"}) + encode({"type": "bogus"}))
    b.close()  # the peer is gone, so the first error reply's send fails
    select.select([a], [], [], 5)
    server._read()  # must not raise
    assert server._client is None
    server.close()


def test_a_crash_mid_tick_leaves_a_log_that_replays_to_the_crash(tmp_path: Path) -> None:
    # Executor S1, second consequence: a crash logged an "end" digest of a half-applied tick, and replay dropped
    # the intents that caused it.

    log = io.StringIO()
    log.write(META)
    sim = Sim(config.load())
    server = Server(sim, token=TOKEN, log=log)
    real_step = sim.step

    def failing_step(intents):  # the third tick fails
        if sim.tick == 2:
            raise RuntimeError("boom")
        return real_step(intents)

    sim.step = failing_step  # type: ignore[method-assign]
    kindle = (parse_intent({"type": "kindle"}), {"type": "kindle"})
    server._pending.append(kindle)
    server._tick()  # tick 0, with an intent
    server._tick()  # tick 1
    server._pending.append(kindle)
    with pytest.raises(RuntimeError, match="boom"):
        server._tick()  # tick 2: its intent is logged, then the step fails
    server.close(clean=False)
    path = tmp_path / "s.jsonl"
    path.write_text(log.getvalue())
    assert '"end"' not in log.getvalue()
    assert '"crashed"' in log.getvalue()
    _, ticks, digest = ticks_of(path)
    assert digest is None
    assert len(ticks) == 3, "the crashing tick's intents are kept, so replay reaches the crash"


def test_lines_reach_only_an_authenticated_client() -> None:
    # Executor S7: the hello gate on vendor lines was held by the code alone.
    cfg = config.load()
    voice = Voice(cfg.npc.voice, cfg.npc.canned, None)
    sim = Sim(cfg)
    server = Server(sim, token=TOKEN, log=io.StringIO(), voice=voice)
    thread = threading.Thread(target=server.run, args=(6,), daemon=True)
    with socket.create_connection(("127.0.0.1", server.port)) as sock:
        thread.start()
        sim.vendor_state = "warn"  # a change of state on the first tick, so a line is produced
        reader, got = FrameReader(), []
        sock.settimeout(1.0)
        with contextlib.suppress(TimeoutError):
            while data := sock.recv(65536):
                got += list(reader.feed(data))
    thread.join(timeout=30)
    server.close()
    assert got == [], "no hello, so no line and no state"


def test_serve_writes_the_run_file_the_log_and_an_end_that_replays(tmp_path: Path) -> None:
    # Executor S8: the shipped entry point never ran under a test.

    serve(0.2, 0, llm=False, root=tmp_path, ticks=3)
    run = tmp_path / "run" / "session.json"
    assert stat.S_IMODE(run.stat().st_mode) == 0o600
    (log_path,) = (tmp_path / "sessions").iterdir()
    lines = log_path.read_text().splitlines()
    assert '"meta"' in lines[0]
    assert '"end"' in lines[-1]
    assert main(["replay", str(log_path)]) == 0
    serve(0.2, 0, llm=False, root=tmp_path, ticks=1)
    assert len(list((tmp_path / "sessions").iterdir())) == 2, "a second launch never overwrites the first log"


def test_a_silent_connection_is_dropped_after_the_hello_deadline() -> None:
    # Executor N4 / Architecture N2: a local process that never says hello held the only client slot.
    server = Server(Sim(config.load()), token=TOKEN, log=io.StringIO(), hello_s=0.3)
    thread = threading.Thread(target=server.run, args=(10,), daemon=True)
    with socket.create_connection(("127.0.0.1", server.port)) as sock:
        thread.start()
        sock.settimeout(5)
        got = _messages(sock, until=99)  # reads until the server closes it
    thread.join(timeout=30)
    server.close()
    assert [m["code"] for m in got] == ["hello_timeout"]
