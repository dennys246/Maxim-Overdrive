"""The vendor's voice: a local LLM writes its lines, and only its lines (plan §3.5, VS2).

Server side, not simulation: the voice does IO and takes wall-clock time, so it lives beside the tick loop and never
inside ``Sim``. Its output is text for the client and the session log. Nothing reads it back: no simulation code
imports this module, and a line can't become an act (``tests/test_voice.py`` holds both). The player's ``say`` text
goes into the next prompt as words, and can change what the vendor says, never what it does.

A request runs on one worker thread with a timeout, so a slow model never stalls a tick. Any failure (the server is
down, the call times out, the reply is malformed or empty) falls back to a canned line for the state, and the reason
is kept with the line: a fallback is reported, never silent.
"""

from __future__ import annotations

import http.client
import json
import time
import urllib.request
from collections import deque
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

Ask = Callable[[str, float], str]  # (prompt, timeout_s) -> reply text


@dataclass(frozen=True)
class VoiceParams:
    model: str
    host: str
    timeout_s: float
    max_words: int
    persona: str


@dataclass(frozen=True)
class Line:
    text: str
    state: str
    source: str  # "llm" or "canned"
    latency_s: float  # from the request to the line, queue included: what the player waited
    why_canned: str | None = None
    queued_s: float = 0.0  # of which waiting behind earlier requests on the one worker


class VoiceFailed(RuntimeError):
    """The model gave no usable line; the message says why."""


def ollama(params: VoiceParams) -> Ask:
    """A call to a local Ollama server on 127.0.0.1 (the LLM spike's setup): one non-streamed generation."""
    if not params.host.startswith("http://127.0.0.1:"):
        raise ValueError(f"the voice talks only to a local model, got {params.host!r}")

    def ask(prompt: str, timeout_s: float) -> str:
        body = json.dumps({"model": params.model, "prompt": prompt, "stream": False}).encode()
        request = urllib.request.Request(f"{params.host}/api/generate", body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                reply = json.loads(response.read())
        # urllib wraps only errors while sending; reading the reply can fail with any OSError (connection reset,
        # remote disconnected, timeout), an HTTPException (truncated body), or a ValueError (bytes that aren't
        # UTF-8, text that isn't JSON). Each is a failed line, reported, never a crash of the server.
        except (OSError, http.client.HTTPException, ValueError) as exc:
            raise VoiceFailed(f"{type(exc).__name__}: {exc}") from exc
        text = reply.get("response") if isinstance(reply, dict) else None
        if not isinstance(text, str):
            raise VoiceFailed("the reply had no response text")
        return text

    return ask


def cap(text: str, max_words: int) -> str:
    """One line, at most ``max_words`` words, without stage directions in asterisks or quotes around it."""
    words = text.replace("*", " ").strip().strip('"').split()
    return " ".join(words[:max_words])


class Voice:
    def __init__(
        self,
        params: VoiceParams,
        canned: Mapping[str, list[str]],
        ask: Ask | None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """``clock`` times latency and queueing: the wall clock in play, a test's own clock in tests."""
        self._params, self._canned, self._ask, self._clock = params, canned, ask, clock
        self._turn = dict.fromkeys(canned, 0)  # canned lines rotate per state, deterministically
        self._heard: deque[str] = deque(maxlen=3)
        self._pool = ThreadPoolExecutor(max_workers=1) if ask is not None else None
        self._pending: list[Future[Line]] = []

    def heard(self, text: str) -> None:
        """What the player said, for the next prompts."""
        self._heard.append(text)

    def request(self, state: str, facts: str) -> Line | None:
        """Ask for a line for ``state``. With no model it returns the canned line at once; with one, it queues the
        request and its line arrives later from ``ready``."""
        if self._pool is None or self._ask is None:
            return self._fallback(state, 0.0, "no model configured")
        asked = self._clock()
        self._pending.append(self._pool.submit(self._speak, self._ask, state, self._prompt(state, facts), asked))
        return None

    def ready(self) -> list[Line]:
        """The lines whose requests have finished, in the order they were asked: the finished ones at the front of
        the queue, up to the first that hasn't. A later line that finished first waits for the earlier ones (the
        worker can finish two between looks). One look per request, so a request that finishes while this runs is
        kept for the next call, never lost between two looks."""
        ready = 0
        while ready < len(self._pending) and self._pending[ready].done():
            ready += 1
        done, self._pending = self._pending[:ready], self._pending[ready:]
        return [f.result() for f in done]

    def close(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)

    def _prompt(self, state: str, facts: str) -> str:
        heard = " ".join(f'The player said: "{t}".' for t in self._heard)
        return (
            f"{self._params.persona}\nWhat is happening: {facts}. {heard}\n"
            f"Say one short line out loud (at most {self._params.max_words} words), no stage directions."
        )

    def _speak(self, ask: Ask, state: str, prompt: str, asked: float) -> Line:
        queued = self._clock() - asked
        try:
            text = cap(ask(prompt, self._params.timeout_s), self._params.max_words)
        except VoiceFailed as exc:
            return self._fallback(state, self._clock() - asked, str(exc), queued)
        if not text:
            return self._fallback(state, self._clock() - asked, "the model said nothing", queued)
        return Line(text, state, "llm", self._clock() - asked, queued_s=queued)

    def _fallback(self, state: str, latency_s: float, why: str, queued_s: float = 0.0) -> Line:
        lines = self._canned[state]
        text = lines[self._turn[state] % len(lines)]
        self._turn[state] += 1
        return Line(text, state, "canned", latency_s, why, queued_s)


def facts(event: Mapping[str, object]) -> str:
    """What the voice is told about a change of the vendor's state: plain words built from the event's fields."""
    target, core = event.get("target"), event.get("player_core_c")
    words = {
        "flee": "the fire's heat is on you and you are running for the alley's mouth",
        "douse": f"a fire has started on the {target} near your stall and you go to put it out",
        "doused": f"you just put out the fire on the {target}",
        "warn": f"the {target} is burning and you can't put it out",
        "comment": f"the customer's cyberware is overheating, at {core:.0f} C" if isinstance(core, float) else "",
        "idle": "it is quiet and you are back at your stall",
    }
    return words[str(event["state"])]
