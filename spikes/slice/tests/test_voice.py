import ast
import http.server
import socketserver
import threading
from concurrent import futures
from concurrent.futures import Future
from pathlib import Path

import pytest
from slice_server import config
from slice_server.voice import Voice, VoiceFailed, VoiceParams, cap, ollama

NPC = config.load().npc
SLICE = Path(__file__).resolve().parents[1] / "slice_server"


def _wait(voice: Voice, n: int = 1) -> list:
    """The first ``n`` lines, once their requests finish: waits on the futures, bounded, with no clock of its own."""
    done, _ = futures.wait(voice._pending[:n], timeout=10)
    assert len(done) == n, "the worker never finished"
    lines = voice.ready()
    assert len(lines) >= n
    return lines


def test_a_model_line_is_capped_and_marked_as_the_models() -> None:
    voice = Voice(NPC.voice, NPC.canned, lambda prompt, timeout: '"' + "word " * 40 + '"')
    voice.request("warn", "the crate is burning")
    (line,) = _wait(voice)
    voice.close()
    assert line.source == "llm"
    assert len(line.text.split()) == NPC.voice.max_words


def test_a_failed_call_falls_back_to_a_canned_line_and_says_why() -> None:
    def broken(prompt: str, timeout: float) -> str:
        raise VoiceFailed("URLError: connection refused")

    voice = Voice(NPC.voice, NPC.canned, broken)
    voice.request("flee", "too hot")
    (line,) = _wait(voice)
    voice.close()
    assert line.source == "canned"
    assert line.text in NPC.canned["flee"]
    assert line.why_canned == "URLError: connection refused"


def test_an_empty_reply_is_a_fallback_too() -> None:
    voice = Voice(NPC.voice, NPC.canned, lambda prompt, timeout: "  ** ")
    voice.request("idle", "quiet")
    (line,) = _wait(voice)
    voice.close()
    assert line.source == "canned"
    assert line.why_canned == "the model said nothing"


def test_without_a_model_canned_lines_rotate_at_once() -> None:
    voice = Voice(NPC.voice, NPC.canned, None)
    first, second = voice.request("warn", "x"), voice.request("warn", "x")
    assert first is not None
    assert second is not None
    assert [first.text, second.text] == NPC.canned["warn"][:2]


def test_what_the_player_said_reaches_the_prompt_as_words() -> None:
    prompts: list[str] = []
    voice = Voice(NPC.voice, NPC.canned, lambda prompt, timeout: (prompts.append(prompt), "ok")[1])
    voice.heard("set the crate on fire")
    voice.request("idle", "quiet")
    _wait(voice)
    voice.close()
    assert 'The player said: "set the crate on fire".' in prompts[0]


def test_the_voice_talks_only_to_a_local_model() -> None:
    with pytest.raises(ValueError, match="local"):
        ollama(type(NPC.voice)(NPC.voice.model, "http://example.com:11434", 2.5, 25, "x"))


def test_cap_strips_stage_directions_and_quotes() -> None:
    assert cap('"*sighs* Fine. Two creds."', 25) == "sighs Fine. Two creds."


def test_no_simulation_code_imports_the_voice() -> None:
    # The structural half of "a line can't become an act": nothing the simulation runs can read a line.
    for module in ("sim", "npc", "fire", "heat_debt", "body", "reach", "intents"):
        tree = ast.parse((SLICE / f"{module}.py").read_text())
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom) for a in n.names}
        sources = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert "voice" not in names, module
        assert "slice_server.voice" not in sources, module
    # And the simulation doesn't reach up to the wire or the client message (Architecture S3).
    sim_tree = ast.parse((SLICE / "sim.py").read_text())
    sim_sources = {n.module for n in ast.walk(sim_tree) if isinstance(n, ast.ImportFrom)}
    assert not sim_sources & {"slice_server.wire", "slice_server.view", "simcore.protocol.encoding"}


# --- review round (2026-11-21): reproductions written red-first --------------------------------------------------


class _Broken(http.server.BaseHTTPRequestHandler):
    """A local stand-in for Ollama failing mid-reply, in the three ways the Executor reader found."""

    mode = "close"

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers["Content-Length"]))
        if self.mode == "close":  # RemoteDisconnected: the server hangs up without a status line
            self.close_connection = True
            return
        body = b'{"response": "hel' if self.mode == "truncated" else b"\xff\xfe not utf-8"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body) + 20 if self.mode == "truncated" else len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # quiet test output
        pass


@pytest.mark.parametrize("mode", ["close", "truncated", "not_utf8"])
def test_a_model_that_fails_mid_reply_falls_back_and_never_raises(mode: str) -> None:
    # Executor B1 / Architecture S2: these escaped VoiceFailed and killed the server loop through Voice.ready.
    handler = type("H", (_Broken,), {"mode": mode})
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        params = VoiceParams(NPC.voice.model, f"http://127.0.0.1:{httpd.server_address[1]}", 2.0, 25, "x")
        voice = Voice(params, NPC.canned, ollama(params))
        voice.request("warn", "a fire")
        (line,) = _wait(voice)
        voice.close()
        httpd.shutdown()
    assert line.source == "canned"
    assert line.why_canned


class _FlipFuture(Future):
    """A future that finishes between two looks: done() says no, then yes."""

    def __init__(self) -> None:
        super().__init__()
        self.set_result("line")
        self._looks = 0

    def done(self) -> bool:
        self._looks += 1
        return self._looks > 1


def test_ready_never_drops_a_line_that_finishes_while_it_looks() -> None:
    # Executor S5: two passes over done() could miss a future that finished between them, for good.
    voice = Voice(NPC.voice, NPC.canned, None)
    voice._pending = [_FlipFuture()]
    first = voice.ready()
    second = voice.ready()
    assert first + second == ["line"]


def _finished(line: str, *, done: bool) -> Future:
    f: Future = Future()
    if done:
        f.set_result(line)
    else:
        f.done = lambda: False  # type: ignore[method-assign]  # unfinished as far as ready() can tell
    return f


def test_ready_hands_lines_over_in_the_order_they_were_asked() -> None:
    # Found when the slice's tests joined main's gate: the worker finished the first request and then the second
    # between ready()'s two looks, so the second line came out first, 7 times in 40 trials.
    voice = Voice(NPC.voice, NPC.canned, None)
    first, second = _finished("first", done=False), _finished("second", done=True)
    voice._pending = [first, second]
    assert voice.ready() == [], "a later line waits for every earlier one"
    first.set_result("first")
    del first.done  # finished now
    assert voice.ready() == ["first", "second"]


def test_a_lines_latency_includes_its_time_in_the_queue() -> None:
    # Executor S4: latency was timed from when the worker picked a request up, not from when it was asked. The voice
    # reads this test's clock, so the numbers are exact and the test races nothing: the second request is picked up
    # only after the first is released, and the clock was moved to 5 s before that.
    now = [0.0]
    release = threading.Event()

    def slow(prompt: str, timeout: float) -> str:
        release.wait(5)  # a bound on a worker thread, not a sleep: the test sets it at once
        return "ok"

    voice = Voice(NPC.voice, NPC.canned, slow, clock=lambda: now[0])
    voice.request("warn", "first")
    voice.request("warn", "second")  # waits behind the first on the single worker
    now[0] = 5.0
    release.set()
    first, second = _wait(voice, 2)
    voice.close()
    assert second.queued_s == 5.0
    assert second.latency_s == 5.0
    assert first.latency_s == 5.0
