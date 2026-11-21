import ast
import time
from pathlib import Path

import pytest
from slice_server import config
from slice_server.voice import Voice, VoiceFailed, cap, ollama

NPC = config.load().npc
SLICE = Path(__file__).resolve().parents[1] / "slice_server"


def _wait(voice: Voice, n: int = 1) -> list:
    lines: list = []
    deadline = time.monotonic() + 10  # a bound on a worker thread, not a sleep: it returns as soon as lines arrive
    while len(lines) < n and time.monotonic() < deadline:
        lines += voice.ready()
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
