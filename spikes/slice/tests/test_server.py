"""The server end to end on a real localhost socket (port 0): handshake, refusals, states, and replay of its log."""

import contextlib
import io
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from slice_server import WIRE_VERSION, config
from slice_server.__main__ import check_replay
from slice_server.server import Server
from slice_server.sim import Sim
from slice_server.voice import Voice
from slice_server.wire import FrameReader, encode

TOKEN = "t" * 32


@contextmanager
def serving(ticks: int) -> Iterator[tuple[Server, io.StringIO]]:
    log = io.StringIO()
    log.write('{"meta":{"dx_m":0.2,"tick_s":0.1}}\n')
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
    log.write('{"meta":{"dx_m":0.2,"tick_s":0.1}}\n')
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
    log.write('{"meta":{"dx_m":0.2,"tick_s":0.1}}\n')
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
