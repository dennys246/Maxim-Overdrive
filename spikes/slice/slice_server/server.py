"""The slice's server loop: one client, a fixed 0.1 s tick paced to the wall clock, a session log.

The wall clock only decides when the next tick runs; ``Sim.step`` always advances exactly one tick of simulated
time. If a tick runs late by more than a whole tick, the server resets its deadline instead of running ticks back to
back to catch up: the world slows (time dilation) rather than skipping or bunching physics, and the overrun is
counted. Sockets are non-blocking under one ``selectors`` loop, so a slow client never stalls the tick.

Security (CLAUDE.md, Game engineering): binds 127.0.0.1 only; the first frame must be ``hello`` with the per-launch
token (compared in constant time); HTTP is refused at the first bytes (``wire``); a second client is refused.
"""

from __future__ import annotations

import hmac
import json
import selectors
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from maxim_overdrive import data
from slice_server import WIRE_VERSION
from slice_server.intents import Intent, parse
from slice_server.sim import Sim
from slice_server.wire import FrameReader, WireRefused, encode

MAX_OUTBOX = 8 << 20  # a client this far behind isn't reading; drop it rather than buffer without bound
STATS_EVERY = 50  # ticks between printed and logged stats


@dataclass
class Client:
    sock: socket.socket
    reader: FrameReader = field(default_factory=FrameReader)
    outbox: bytearray = field(default_factory=bytearray)
    authed: bool = False


@dataclass
class Meter:
    """Tick CPU and snapshot cost over a window of ticks: what B5's budgets will be set from (plan §3.1)."""

    ticks: int = 0
    tick_cpu_s: float = 0.0
    tick_cpu_max_s: float = 0.0
    encode_cpu_s: float = 0.0
    state_bytes: int = 0
    overruns: int = 0

    def add(self, tick_cpu: float, encode_cpu: float, nbytes: int) -> None:
        self.ticks += 1
        self.tick_cpu_s += tick_cpu
        self.tick_cpu_max_s = max(self.tick_cpu_max_s, tick_cpu)
        self.encode_cpu_s += encode_cpu
        self.state_bytes += nbytes

    def report(self) -> dict[str, float]:
        n = max(self.ticks, 1)
        return {
            "ticks": self.ticks,
            "tick_cpu_ms_mean": 1e3 * self.tick_cpu_s / n,
            "tick_cpu_ms_max": 1e3 * self.tick_cpu_max_s,
            "encode_cpu_ms_mean": 1e3 * self.encode_cpu_s / n,
            "state_kb_mean": self.state_bytes / n / 1024,
            "overruns": self.overruns,
        }


class Server:
    def __init__(self, sim: Sim, *, token: str, log: IO[str], port: int = 0) -> None:
        self.sim, self._token, self._log = sim, token, log
        self._listener = socket.create_server(("127.0.0.1", port))
        self._listener.setblocking(False)
        self.port: int = self._listener.getsockname()[1]
        self._sel = selectors.DefaultSelector()
        self._sel.register(self._listener, selectors.EVENT_READ)
        self._client: Client | None = None
        self._pending: list[tuple[Intent, dict[str, object]]] = []
        self.meter = Meter()
        self._stop = threading.Event()

    # The loop ---------------------------------------------------------------------------------------------------

    def run(self, ticks: int | None = None) -> None:
        """Serve until ``stop``, or for ``ticks`` ticks. The stop is checked only between ticks, so a tick always
        runs whole: the state the final digest records is one replay can reach."""
        deadline = time.monotonic()
        while not self._stop.is_set() and (ticks is None or self.sim.tick < ticks):
            for key, events in self._sel.select(max(0.0, deadline - time.monotonic())):
                self._ready(key.fileobj, events)  # type: ignore[arg-type]
            if time.monotonic() >= deadline:
                self._tick()
                deadline += self.sim.tick_s
                if time.monotonic() - deadline > self.sim.tick_s:
                    self.meter.overruns += 1
                    deadline = time.monotonic()

    def stop(self) -> None:
        """Ask the loop to end after its current tick. Safe from a signal handler or another thread."""
        self._stop.set()

    def close(self) -> None:
        self._log_line({"end": {"tick": self.sim.tick, "digest": self.sim.digest()}})
        if self._client is not None:
            self._drop("server closing")
        self._sel.close()
        self._listener.close()

    def _tick(self) -> None:
        pending, self._pending = self._pending, []
        if pending:
            self._log_line({"tick": self.sim.tick, "intents": [raw for _, raw in pending]})
        start = time.thread_time()
        events = self.sim.step([intent for intent, _ in pending])
        tick_cpu = time.thread_time() - start
        start = time.thread_time()
        message = encode(self.sim.state())
        self.meter.add(tick_cpu, time.thread_time() - start, len(message))
        if self._client is not None and self._client.authed:  # the world goes only to a peer that gave the token
            for event in events:
                self._send(encode(event))
            self._send(message)
        if self.sim.tick % STATS_EVERY == 0:
            self._report()

    def _report(self) -> None:
        stats = self.meter.report()
        self._log_line({"stats": stats, "tick": self.sim.tick, "work_j": self.sim.body.work_j})
        print(" ".join(f"{k}={v:.2f}" for k, v in stats.items()), flush=True)
        self.meter = Meter()

    # Sockets ----------------------------------------------------------------------------------------------------

    def _ready(self, sock: socket.socket, events: int) -> None:
        if sock is self._listener:
            self._accept()
            return
        if events & selectors.EVENT_READ:
            self._read()
        if events & selectors.EVENT_WRITE and self._client is not None:
            self._flush()

    def _accept(self) -> None:
        conn, _ = self._listener.accept()
        if self._client is not None:
            conn.close()  # one player in the slice
            return
        conn.setblocking(False)
        self._client = Client(conn)
        self._sel.register(conn, selectors.EVENT_READ)

    def _read(self) -> None:
        assert self._client is not None
        try:
            data_in = self._client.sock.recv(65536)
        except ConnectionError as exc:
            self._drop(f"recv failed: {exc}")
            return
        if not data_in:
            self._drop("client closed")
            return
        try:
            for message in self._client.reader.feed(data_in):
                self._handle(message)
        except WireRefused as exc:
            self._refuse(exc)

    def _handle(self, message: dict[str, object]) -> None:
        assert self._client is not None
        if not self._client.authed:
            self._hello(message)
            return
        try:
            self._pending.append((parse(message), message))
        except WireRefused as exc:  # a malformed intent gets an error reply and changes nothing
            self._send(encode({"type": "error", "code": exc.code, "detail": exc.detail}))

    def _hello(self, message: dict[str, object]) -> None:
        token = message.get("token")
        ok = isinstance(token, str) and hmac.compare_digest(token.encode(), self._token.encode())
        if message.get("type") != "hello" or message.get("version") != WIRE_VERSION or not ok:
            raise WireRefused("bad_hello", f"the first frame must be a {WIRE_VERSION} hello with this launch's token")
        assert self._client is not None
        self._client.authed = True
        self._send(encode(self._welcome()))

    def _welcome(self) -> dict[str, object]:
        f = self.sim.frame
        palette = {str(m.id): list(m.color_rgb) for m in data.materials().by_id.values()}
        return {"type": "welcome", "version": WIRE_VERSION, "shape": list(f.shape), "dx_m": f.dx_m,
                "tick_s": self.sim.tick_s, "palette": palette}  # fmt: skip

    def _refuse(self, exc: WireRefused) -> None:
        self._send(encode({"type": "error", "code": exc.code, "detail": exc.detail}))
        if self._client is not None:  # _send drops a client that isn't reading
            self._flush()
            self._drop(str(exc))

    def _send(self, frame: bytes) -> None:
        if self._client is None:
            return
        self._client.outbox += frame
        if len(self._client.outbox) > MAX_OUTBOX:
            self._drop("client is not reading")
            return
        self._flush()

    def _flush(self) -> None:
        assert self._client is not None
        c = self._client
        try:
            sent = c.sock.send(c.outbox)
        except BlockingIOError:
            sent = 0
        except ConnectionError as exc:
            self._drop(f"send failed: {exc}")
            return
        del c.outbox[:sent]
        self._sel.modify(c.sock, selectors.EVENT_READ | (selectors.EVENT_WRITE if c.outbox else 0))

    def _drop(self, why: str) -> None:
        assert self._client is not None
        print(f"client dropped: {why}", flush=True)
        self._sel.unregister(self._client.sock)
        self._client.sock.close()
        self._client = None

    def _log_line(self, record: dict[str, object]) -> None:
        self._log.write(json.dumps(record, separators=(",", ":")) + "\n")
        self._log.flush()


def write_run_file(path: Path, port: int, token: str) -> None:
    """Where the client finds this launch's port and token: a file only the owner can read, inside the worktree."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text(json.dumps({"port": port, "token": token}))
