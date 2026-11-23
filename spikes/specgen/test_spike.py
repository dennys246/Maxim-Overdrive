"""The spec generator spike's own tests: generate.py against a fake llama-server, score.py on hand-made records.

Throwaway spike tests, outside ``tests/`` (the repo's suite never runs them): no model and no network beyond a fake
server bound to 127.0.0.1 on port 0. Run: ``.venv/bin/python -m pytest spikes/specgen/test_spike.py -q``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import urllib.error
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import burn
import generate
import geometry
import labelling
import protocol
import score


def spec(name: str, *prims: dict[str, Any]) -> str:
    return json.dumps({"intent": "a test object", "name": name, "primitives": list(prims)})


def box(lo: list[int], hi: list[int], material: str = "wood") -> dict[str, Any]:
    return {"kind": "box", "min_cm": lo, "max_cm": hi, "material": material}


GOOD = spec("crate", box([0, 0, 0], [40, 40, 50]))  # 48 kg of wood, whole cells at 0.1 m: accepted
OUTSIDE = spec(  # reaches 450 cm from its origin, past the 4 m world, and weighs 1.7 t: the bounds check comes first
    "disc", {"kind": "cylinder", "center_xy_cm": [300, 300], "radius_cm": 150, "z_cm": [0, 10], "material": "concrete"}
)
HEAVY = spec("block", box([0, 0, 0], [100, 100, 100], "concrete"))  # 2,400 kg: over_budget
THIN = spec("plate", box([0, 0, 0], [100, 100, 1]))  # 1 cm thick at z 0.003-0.013 m: no cell centre, too_small

# What build 10621 reports with arms.yaml's flags (-c 16384 --parallel 1), checked on the mini.
PROPS: dict[str, Any] = {
    "build_info": "b10621-c1d0e7a00",
    "model_path": "/models/Qwen3.5-4B-Q8_0.gguf",
    "default_generation_settings": {"n_ctx": 16384, "params": {}},
    "total_slots": 1,
}
S_WEIGHTS = protocol.read_manifest()[1]["S"]


class Fake:
    """A fake llama-server: ``reply(body)`` returns (status, payload). Every request body is kept."""

    def __init__(
        self, reply: Callable[[dict[str, Any]], tuple[int, dict[str, Any]]], props: dict[str, Any] | None = None
    ) -> None:
        self.reply = reply
        self.props = PROPS if props is None else props
        self.bodies: list[dict[str, Any]] = []

    @contextmanager
    def serve(self) -> Iterator[str]:
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status: int, payload: dict[str, Any]) -> None:
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                self._send(200, fake.props)

            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.bodies.append(body)
                self._send(*fake.reply(body))

            def log_message(self, *args: object) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


def ok(content: str, finish: str = "stop") -> tuple[int, dict[str, Any]]:
    return 200, {
        "choices": [{"message": {"content": content}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }


def by_seed(table: dict[int, tuple[int, dict[str, Any]]]) -> Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]:
    return lambda body: table[body["seed"]]


def run_cell(fake: Fake, out: Path, arm: str, seeds: list[int], prompts: list[str], *, weights: str = S_WEIGHTS) -> int:
    with fake.serve() as url:
        args = generate.parse_args(
            [
                "--endpoint",
                url,
                "--model",
                "S",
                "--arm",
                arm,
                "--split",
                "dev",
                "--out",
                str(out),
                "--machine",
                "test",
                "--weights-sha256",
                weights,
                "--seeds",
                *map(str, seeds),
                "--prompt-ids",
                *prompts,
            ]
        )
        return generate.run(generate.Server(url), args)


@pytest.fixture
def dev_ids() -> list[str]:
    return [p["id"] for p in protocol.load_prompts("dev")]


def samples(out: Path) -> list[dict[str, Any]]:
    return [r for r in map(json.loads, out.read_text().splitlines()) if r["kind"] == "sample"]


def test_a_restart_skips_every_sample_already_written(tmp_path: Path, dev_ids: list[str]) -> None:
    out = tmp_path / "run.jsonl"
    first = Fake(lambda body: ok(GOOD))
    assert run_cell(first, out, "A1", [0, 1], dev_ids[:2]) == 4
    assert len(first.bodies) == 4
    again = Fake(lambda body: ok(GOOD))
    assert run_cell(again, out, "A1", [0, 1], dev_ids[:2]) == 0
    assert again.bodies == []  # nothing was asked again
    lines = out.read_text().splitlines()
    assert json.loads(lines[0])["kind"] == "header"
    assert len(lines) == 5


def test_a_restart_refuses_a_file_from_another_run(tmp_path: Path, dev_ids: list[str]) -> None:
    out = tmp_path / "run.jsonl"
    run_cell(Fake(lambda body: ok(GOOD)), out, "A1", [0], dev_ids[:1])
    with pytest.raises(generate.RunRefused, match="arm"):
        run_cell(Fake(lambda body: ok(GOOD)), out, "A2", [0], dev_ids[:1])


def test_a3_checks_bounds_before_place_feeds_back_codes_and_ends_at_too_small(
    tmp_path: Path, dev_ids: list[str]
) -> None:
    fake = Fake(by_seed({0: ok(OUTSIDE), 100: ok(HEAVY), 200: ok(THIN), 300: ok(GOOD)}))
    run_cell(fake, tmp_path / "a3.jsonl", "A3", [0], dev_ids[:1])
    (rec,) = samples(tmp_path / "a3.jsonl")
    got = [(a["klass"], a["code"], a["seed"]) for a in rec["attempts"]]
    assert got == [
        ("outside_world", "outside_extent", 0),
        ("refused", "over_budget", 100),
        ("refused", "too_small", 200),
    ]
    assert [a["fed_back"] for a in rec["attempts"]] == [
        "The world refused that object: outside_extent. Reply with a corrected object.",
        "The world refused that object: over_budget. Reply with a corrected object.",
        None,  # too_small is a world outcome: never fed back, and it ends the loop
    ]
    second = fake.bodies[1]["messages"]
    assert second[-2] == {"role": "assistant", "content": OUTSIDE}
    assert second[-1]["content"].startswith("The world refused that object: outside_extent")
    assert len(fake.bodies) == 3  # seed 300 was never asked


def test_a3_stops_after_its_third_retry(tmp_path: Path, dev_ids: list[str]) -> None:
    fake = Fake(by_seed({0: ok(HEAVY), 100: ok(HEAVY), 200: ok(HEAVY), 300: ok(HEAVY)}))
    run_cell(fake, tmp_path / "a3.jsonl", "A3", [0], dev_ids[:1])
    (rec,) = samples(tmp_path / "a3.jsonl")
    assert [a["seed"] for a in rec["attempts"]] == [0, 100, 200, 300]
    assert rec["attempts"][-1]["fed_back"] is None


def test_truncation_comes_before_the_parse_and_ends_a3(tmp_path: Path, dev_ids: list[str]) -> None:
    fake = Fake(by_seed({1: ok(GOOD, finish="length")}))
    run_cell(fake, tmp_path / "t.jsonl", "A3", [1], dev_ids[:1])
    (rec,) = samples(tmp_path / "t.jsonl")
    assert [a["klass"] for a in rec["attempts"]] == ["truncated"]  # a complete object, still truncated


def test_a_context_overflow_is_the_class_truncated(tmp_path: Path, dev_ids: list[str]) -> None:
    overflow = (
        400,
        {
            "error": {
                "code": 400,
                "message": "the request exceeds the available context size",
                "type": "exceed_context_size_error",
            }
        },
    )
    fake = Fake(by_seed({2: overflow}))
    run_cell(fake, tmp_path / "o.jsonl", "A3", [2], dev_ids[:1])
    (rec,) = samples(tmp_path / "o.jsonl")
    assert [(a["klass"], a["context_overflow"]) for a in rec["attempts"]] == [("truncated", True)]


def test_the_request_pins_the_frozen_sampler_thinking_and_grammar(tmp_path: Path, dev_ids: list[str]) -> None:
    fake = Fake(lambda body: ok(GOOD))
    run_cell(fake, tmp_path / "s.jsonl", "A2", [3], dev_ids[:1])
    (body,) = fake.bodies
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert (body["temperature"], body["top_k"], body["top_p"], body["min_p"], body["repeat_penalty"]) == (
        0.7,
        0,
        1.0,
        0.0,
        1.0,
    )
    assert body["response_format"]["json_schema"]["schema"] == protocol.load_arms()["schema"]
    assert len(body["messages"]) == 1 + 2 * 4 + 1  # system, four examples as turns, the prompt
    assert body["messages"][2]["content"].startswith('{"intent":')  # compact JSON, keys in file order


def test_the_server_must_be_the_frozen_build_and_model() -> None:
    arms = protocol.load_arms()
    assert generate.check_server(PROPS, arms, "S") == PROPS["build_info"]
    with pytest.raises(generate.RunRefused, match="build"):
        generate.check_server({**PROPS, "build_info": "b9999"}, arms, "S")
    with pytest.raises(generate.RunRefused, match="build"):  # contains the frozen build: a substring test passes it
        generate.check_server({**PROPS, "build_info": "b10621-c1d0e7a00-dirty"}, arms, "S")
    with pytest.raises(generate.RunRefused, match="context"):
        generate.check_server({**PROPS, "default_generation_settings": {"n_ctx": 8192}}, arms, "S")
    with pytest.raises(generate.RunRefused, match="context"):
        generate.check_server({k: v for k, v in PROPS.items() if k != "default_generation_settings"}, arms, "S")
    with pytest.raises(generate.RunRefused, match="slots"):
        generate.check_server({**PROPS, "total_slots": 4}, arms, "S")  # what the server reports without --parallel 1
    with pytest.raises(generate.RunRefused, match="serves"):
        generate.check_server(PROPS, arms, "R")


def test_the_header_refuses_a_tree_whose_frozen_files_differ(tmp_path: Path) -> None:
    copy = tmp_path / "specgen"
    shutil.copytree(protocol.HERE, copy, ignore=shutil.ignore_patterns("__pycache__", "runs"))
    assert protocol.check_frozen(copy) == protocol.read_manifest()[0]
    path = copy / "prompts_dev.yaml"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(protocol.FrozenMismatch, match=r"prompts_dev\.yaml"):
        protocol.check_frozen(copy)


def test_a0_takes_the_first_object_after_fences_and_prose() -> None:
    reply = 'Here it is:\n```json\n{"name": "crate", "primitives": []}\n```\n{"name": "second"}'
    assert protocol.parse_reply(reply, "A0") == {"name": "crate", "primitives": []}
    assert protocol.parse_reply(reply, "A1") is None  # a grammar arm's reply is the object, whole
    assert protocol.parse_reply("no object here", "A0") is None


def test_whole_centimetres_become_metres_by_exact_division() -> None:
    arms = protocol.load_arms()
    out = protocol.convert(json.loads(spec("x", box([0, 0, 0], [35, 7, 300]))), arms)
    (p,) = out["primitives"]
    assert p["max_m"] == [35 / 100, 7 / 100, 300 / 100]  # 35 * 0.01 is 0.35000000000000003
    assert "intent" not in out
    floats = protocol.convert({"primitives": [{"kind": "box", "min_cm": [0.5, 0, 0]}]}, arms)
    assert floats["primitives"][0] == {"kind": "box", "min_cm": [0.5, 0, 0]}  # not whole: passed as written


def test_a_torn_last_line_is_cut_and_the_run_resumes(tmp_path: Path, dev_ids: list[str]) -> None:
    out = tmp_path / "run.jsonl"
    run_cell(Fake(lambda body: ok(GOOD)), out, "A1", [0], dev_ids[:1])
    with out.open("ab") as f:
        f.write(b'{"kind": "sample", "prompt_id": "f0')  # a stop mid-write
    again = Fake(lambda body: ok(GOOD))
    assert run_cell(again, out, "A1", [0, 1], dev_ids[:1]) == 1  # the torn sample is redone with the new one
    rows = [json.loads(line) for line in out.read_text().splitlines()]  # every line whole
    assert [r["kind"] for r in rows] == ["header", "sample", "sample"]


def test_an_empty_or_header_torn_file_starts_a_new_run(tmp_path: Path, dev_ids: list[str]) -> None:
    for content in (b"", b'{"kind": "header", "vers'):
        out = tmp_path / f"run{len(content)}.jsonl"
        out.write_bytes(content)
        assert run_cell(Fake(lambda body: ok(GOOD)), out, "A1", [0], dev_ids[:1]) == 1
        assert [json.loads(line)["kind"] for line in out.read_text().splitlines()] == ["header", "sample"]


def test_a_malformed_middle_line_refuses_the_resume(tmp_path: Path, dev_ids: list[str]) -> None:
    out = tmp_path / "run.jsonl"
    run_cell(Fake(lambda body: ok(GOOD)), out, "A1", [0, 1], dev_ids[:1])
    lines = out.read_text().splitlines()
    out.write_text("\n".join([lines[0], lines[1][:-5], lines[2]]) + "\n")  # line 2 corrupted, not the last
    with pytest.raises(generate.RunRefused, match="malformed line 2"):
        run_cell(Fake(lambda body: ok(GOOD)), out, "A1", [0, 1, 2], dev_ids[:1])


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (400, {"error": {"code": 400, "message": "invalid chat template context", "type": "invalid_request_error"}}),
        (400, {"detail": "context"}),
        (500, {"error": {"code": 500, "message": "context", "type": "exceed_context_size_error"}}),
    ],
)
def test_only_llama_servers_overflow_error_is_the_class_truncated(
    tmp_path: Path, dev_ids: list[str], status: int, payload: dict[str, Any]
) -> None:
    with pytest.raises(urllib.error.HTTPError):
        run_cell(Fake(lambda body: (status, payload)), tmp_path / "e.jsonl", "A3", [0], dev_ids[:1])


def test_the_run_refuses_weights_that_differ_from_the_manifest(tmp_path: Path, dev_ids: list[str]) -> None:
    with pytest.raises(generate.RunRefused, match="weights"):
        run_cell(Fake(lambda body: ok(GOOD)), tmp_path / "w.jsonl", "A1", [0], dev_ids[:1], weights="0" * 64)


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ({"build_info": "b10621-c1d0e7a00-dirty"}, "build"),
        ({"model_path": "/models/Qwen3.5-27B-Q8_0.gguf"}, "model file"),
        ({"default_generation_settings": {"n_ctx": 4096}}, "context"),
        ({"default_generation_settings": {"n_ctx": 32768}}, "context"),  # larger is wrong too: overflow moves
        ({"total_slots": 4}, "slots"),
    ],
)
def test_the_run_refuses_a_server_that_is_not_the_frozen_one(
    tmp_path: Path, dev_ids: list[str], change: dict[str, Any], match: str
) -> None:
    fake = Fake(lambda body: ok(GOOD), props={**PROPS, **change})
    with pytest.raises(generate.RunRefused, match=match):
        run_cell(fake, tmp_path / "p.jsonl", "A1", [0], dev_ids[:1])
    assert fake.bodies == []  # refused before any request


def test_the_run_refuses_a_tree_whose_frozen_files_differ(
    tmp_path: Path, dev_ids: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    copy = tmp_path / "specgen"
    shutil.copytree(protocol.HERE, copy, ignore=shutil.ignore_patterns("__pycache__", "runs"))
    path = copy / "prompts_dev.yaml"
    path.write_text(path.read_text() + "\n")
    monkeypatch.setattr(protocol, "HERE", copy)
    fake = Fake(lambda body: ok(GOOD))
    with pytest.raises(protocol.FrozenMismatch, match=r"prompts_dev\.yaml"):
        run_cell(fake, tmp_path / "f.jsonl", "A1", [0], dev_ids[:1])
    assert fake.bodies == []


# Pinned here, not read from generate.py, so cutting a key from the code turns its case red (code round 1, exec S5).
RESUME_KEYS = (
    "frozen",
    "src_tree",
    "spike_tree",
    "simcore_commit",
    "data_sha256",
    "lockfile",
    "runtime",
    "model",
    "arm",
    "split",
    "engine",
    "scene",
    "offsets_m",
)


@pytest.mark.parametrize("key", RESUME_KEYS)
def test_a_resume_refuses_a_header_that_differs_in_any_key(tmp_path: Path, dev_ids: list[str], key: str) -> None:
    out = tmp_path / "run.jsonl"
    run_cell(Fake(lambda body: ok(GOOD)), out, "A1", [0], dev_ids[:1])
    lines = out.read_text().splitlines()
    head = json.loads(lines[0])
    assert key in head
    head[key] = "something else"
    out.write_text("\n".join([json.dumps(head), *lines[1:]]) + "\n")
    with pytest.raises(generate.RunRefused, match=key):
        run_cell(Fake(lambda body: ok(GOOD)), out, "A1", [0, 1], dev_ids[:1])


def test_the_header_records_measured_weights_and_no_private_path(tmp_path: Path, dev_ids: list[str]) -> None:
    out = tmp_path / "run.jsonl"
    run_cell(Fake(lambda body: ok(GOOD)), out, "A1", [0], dev_ids[:1])
    head = json.loads(out.read_text().splitlines()[0])
    (rec,) = samples(out)
    assert (head["split"], rec["split"]) == ("dev", "dev")  # the scorer reads each sample's split
    assert (head["model"]["weights_sha256"], head["model"]["weights_measured"]) == (S_WEIGHTS, True)
    text = out.read_text()
    assert "/models/" not in text  # the served path names a home directory on the mini
    assert "127.0.0.1" not in text  # nor the endpoint


def test_a3_ends_at_a_parse_failure_without_feedback(tmp_path: Path, dev_ids: list[str]) -> None:
    fake = Fake(lambda body: ok("not an object"))
    run_cell(fake, tmp_path / "pf.jsonl", "A3", [0], dev_ids[:1])
    (rec,) = samples(tmp_path / "pf.jsonl")
    assert [(a["klass"], a["fed_back"]) for a in rec["attempts"]] == [("parse_failure", None)]
    assert len(fake.bodies) == 1


def test_arms_yaml_must_switch_thinking_off(tmp_path: Path) -> None:
    copy = tmp_path / "specgen"
    shutil.copytree(protocol.HERE, copy, ignore=shutil.ignore_patterns("__pycache__", "runs"))
    path = copy / "arms.yaml"
    text = path.read_text()
    assert "  thinking: off\n" in text
    path.write_text(text.replace("  thinking: off\n", "  thinking: true\n"))
    with pytest.raises(protocol.FrozenMismatch, match="thinking"):
        protocol.load_arms(copy)


# --- score.py and geometry.py on hand-made records -------------------------------------------------------------

TWO = spec("stool", box([0, 0, 0], [40, 40, 40]), box([0, 0, 40], [40, 40, 50]))  # two touching parts: not degenerate


def record(prompt: dict[str, Any], seed: int, content: str, arm: str = "A1", model: str = "S") -> dict[str, Any]:
    verdict, _ = protocol.classify(content, "stop", arm, protocol.load_arms())
    attempt = {
        "raw": content,
        "finish": "stop",
        "context_overflow": False,
        "klass": verdict.klass,
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "wall_s": 1.0,
    }
    return {
        "kind": "sample",
        "prompt_id": prompt["id"],
        "stratum": prompt["stratum"],
        "split": "dev",
        "arm": arm,
        "model": model,
        "seed": seed,
        "attempts": [attempt],
    }


def write_run(path: Path, rows: list[dict[str, Any]], *, model: str = "S", arm: str = "A1", split: str = "dev") -> Path:
    head = generate.header(
        protocol.load_arms(),
        model=model,
        arm=arm,
        split=split,
        runtime=PROPS["build_info"],
        machine="test",
        weights=protocol.read_manifest()[1][model],
    )
    path.write_text("".join(json.dumps(r) + "\n" for r in [head, *rows]))
    return path


def furniture(n: int) -> list[dict[str, Any]]:
    """The first ``n`` dev furniture prompts with one expected material, none `single_ok` or `hard`."""
    picked = [
        p
        for p in protocol.load_prompts("dev")
        if p["stratum"] == "furniture" and p["expect"] == ["wood"] and not p.get("single_ok") and not p.get("hard")
    ]
    return picked[:n]


def args_for(path: Path, out: Path, *extra: str) -> Any:
    return score.parse_args(["--split", "dev", "--runs", str(path), "--out", str(out), *extra])


def test_m1_and_its_prompt_clustered_interval_match_hand_values(tmp_path: Path) -> None:
    p1, p2 = furniture(2)
    rows = [record(p1, 0, GOOD), record(p1, 1, GOOD), record(p2, 0, GOOD), record(p2, 1, HEAVY)]
    samples_ = score.load([write_run(tmp_path / "r.jsonl", rows)], protocol.load_arms(), "dev")
    got = score.m1(samples_)
    # Prompt rates 1.0 and 0.5: resampling two prompts gives 1.0, 0.75 or 0.5, each extreme with probability 1/4.
    assert got["rate"]["S/A1"] == {"rate": 0.75, "lo": 0.5, "hi": 1.0, "n": 4, "prompts": 2}
    assert got["classes"]["S/A1"] == {"accepted": 3, "refused:over_budget": 1}
    assert got["recorded_class_disagrees"] == 0


@pytest.mark.parametrize("fault", ["no_header", "other_split", "duplicate", "frozen", "data"])
def test_load_refuses_a_run_it_cannot_trust(tmp_path: Path, fault: str) -> None:
    (p,) = furniture(1)
    rows = [record(p, 0, GOOD)]
    path = write_run(tmp_path / "r.jsonl", rows)
    lines = path.read_text().splitlines()
    head = json.loads(lines[0])
    if fault == "no_header":
        path.write_text("\n".join(lines[1:]) + "\n")
    elif fault == "duplicate":
        path.write_text("\n".join([*lines, lines[1]]) + "\n")
    else:
        key = {"other_split": "split", "frozen": "frozen", "data": "data_sha256"}[fault]
        head[key] = "heldout" if key == "split" else {"x": "y"}
        path.write_text("\n".join([json.dumps(head), *lines[1:]]) + "\n")
    with pytest.raises(score.ScoreRefused):
        score.load([path], protocol.load_arms(), "dev")


def test_an_incomplete_cell_is_refused_unless_watching(tmp_path: Path) -> None:
    (p,) = furniture(1)
    path = write_run(tmp_path / "r.jsonl", [record(p, 0, GOOD)])
    with pytest.raises(score.ScoreRefused, match="missing"):
        score.score(args_for(path, tmp_path / "o.json"))
    watched = score.score(args_for(path, tmp_path / "o.json", "--allow-partial"))
    assert watched["partial"] is True
    assert watched["completeness"]["S/A1"] == {"expected": 150 * 8, "missing": 150 * 8 - 1}


def _paired(table: dict[str, dict[str, list[str]]]) -> tuple[list[Any], labelling.Draws, Any]:
    """Samples for S and R under A3 from ``table[model][prompt] = [content per seed 0-3]``, with "yes" labels for every
    sample passing M1."""
    meta = score.prompt_meta()
    arms = protocol.load_arms()
    samples_, label, sets = [], {}, {}
    for model, prompts in table.items():
        for pid, contents in prompts.items():
            for seed, content in enumerate(contents):
                s = score.from_record(record(meta[pid], seed, content, "A3", model), arms, meta[pid])
                samples_.append(s)
                if s.verdict.m1_pass:
                    label[s.key], sets[s.key] = "yes", "paired"
    pids = tuple(next(iter(table.values())))
    return samples_, labelling.Draws(pids, (), ()), score.Labels(label, sets)


def test_rule_1_when_the_small_models_lower_bound_reaches_p() -> None:
    a, b = (p["id"] for p in furniture(2))
    s, d, lab = _paired({"S": {a: [TWO] * 4, b: [TWO] * 4}, "R": {a: [TWO] * 4, b: [TWO] * 4}})
    assert score.decision(s, d, lab)["rule"] == 1


def test_rule_2_when_the_reference_reaches_p_and_delta_excludes_zero() -> None:
    a, b = (p["id"] for p in furniture(2))
    s, d, lab = _paired({"S": {a: [HEAVY] * 4, b: [HEAVY] * 4}, "R": {a: [TWO] * 4, b: [TWO] * 4}})
    got = score.decision(s, d, lab)
    assert (got["rule"], got["L"]["rate"], got["H"]["rate"], got["delta"]["lo"]) == (2, 0.0, 1.0, 1.0)


def test_rule_3_when_delta_reaches_zero_even_though_h_reaches_p() -> None:
    a, b = (p["id"] for p in furniture(2))
    s, d, lab = _paired({"S": {a: [TWO] * 4, b: [TWO, TWO, HEAVY, HEAVY]}, "R": {a: [TWO] * 4, b: [TWO] * 4}})
    got = score.decision(s, d, lab)
    # L = 0.75 (lo 0.5), H = 1 (lo 1); Δ per resample is 0, 0.25 or 0.5, so its lower bound is 0 and rule 2 fails.
    assert (got["L"]["lo"], got["H"]["lo"], got["delta"]["lo"], got["rule"]) == (0.5, 1.0, 0.0, 3)


@pytest.mark.parametrize("gap", ["sample", "label"])
def test_the_decision_refuses_a_missing_sample_or_label(gap: str) -> None:
    a, b = (p["id"] for p in furniture(2))
    s, d, lab = _paired({"S": {a: [TWO] * 4, b: [TWO] * 4}, "R": {a: [TWO] * 4, b: [TWO] * 4}})
    if gap == "sample":
        s = [x for x in s if x.key != ("R", "A3", b, 3)]
    else:
        lab = score.Labels({k: v for k, v in lab.label.items() if k != ("R", "A3", b, 3)}, lab.sets)
    with pytest.raises(score.ScoreRefused, match="paired set"):
        score.decision(s, d, lab)


def test_an_interval_never_depends_on_what_else_was_scored() -> None:
    a, b = (p["id"] for p in furniture(2))
    s, d, lab = _paired({"S": {a: [TWO, HEAVY] * 2, b: [TWO] * 4}, "R": {a: [TWO] * 4, b: [TWO, HEAVY] * 2}})
    first = score.decision(s, d, lab)
    score.m1(s)  # other statistics drawn first
    score.m2_m4(s)
    assert score.decision(s, d, lab) == first
    # Prompts of differing sizes and rates make the interval's bounds fine-grained, so they move with the stream: a
    # stream shared between statistics would give a second call different bounds.
    by_prompt = {f"p{i}": [1.0] * (i % 5) + [0.0] * (i % 7 + 1) for i in range(23)}
    once = score.cluster_rate(by_prompt, "test.rate")
    score.cluster_rate(by_prompt, "test.other")
    assert score.cluster_rate(by_prompt, "test.rate") == once


def test_paired_delta_matches_hand_values() -> None:
    got = score.paired_delta({"a": [1.0], "b": [1.0]}, {"a": [1.0], "b": [0.0]}, "test")
    # Resamples (a, a), (b, b) and the mixes give Δ of 0, 1 and 0.5, each extreme with probability 1/4.
    assert got == {"delta": 0.5, "lo": 0.0, "hi": 1.0}


def test_m3_reports_voxel_fidelity_and_counts_refusals() -> None:
    (p,) = furniture(1)
    arms = protocol.load_arms()
    whole = score.from_record(record(p, 0, GOOD), arms, p)  # whole cells at both offsets and at 0.2 m
    thin = score.from_record(record(p, 1, THIN), arms, p)  # too_small: passes M1, refused when placed
    got = score.m3([whole, thin])["S/A1"]
    assert got == {
        "ratio_offset": 0.5,
        "ratio_half_cell": 0.5,
        "accepted_at_0.2m": 0.5,
        "refused_at_an_offset": 2,
        "n": 2,
    }


def test_m5_burns_an_accepted_spec_at_turns_of_6_s() -> None:
    arms = protocol.load_arms()
    got = burn.burn(protocol.convert(json.loads(GOOD), arms))
    assert (got["ignited"], got["fire_on_air"]) == (True, False)
    assert sorted(got["integrity"]) == [10, 20, 30]
    assert burn.TURN_S == 6.0


def test_m5_on_simulation_is_bit_for_bit_m5_on_world_advance() -> None:
    # Errata E18: the port to Simulation.step changes no M5 number. The golden is six specs' rows (solid cells in the
    # fire's sphere and integrity, after the ignite and after every 6 s turn), recorded on c6d4f10's engine by
    # m5_golden_recorder.py; it holds a fire on air (legs) and a burnout (block).
    golden = json.loads(burn.GOLDEN.read_text())
    assert burn.check_engine() == "c6d4f10"
    rows = golden["turns"]
    assert rows["legs"][0][0] == 0  # a fire on air
    assert rows["block"][0][0] > 0
    assert rows["block"][-1][0] == 0
    assert any(r[-1][1] not in ("1.0", "0.0") for r in rows.values())  # it burns partway: it tells engines apart


def test_m5_refuses_to_score_on_an_engine_that_moved(tmp_path: Path) -> None:
    golden = json.loads(burn.GOLDEN.read_text())
    golden["turns"]["plank"][-1][1] = repr(0.5)  # as if a physics change had moved the plank's last integrity
    moved = tmp_path / "golden.json"
    moved.write_text(json.dumps(golden))
    with pytest.raises(RuntimeError, match="M5 refuses to score: plank"):
        burn.check_engine(moved)


def test_m5_records_the_engine_it_burned_on() -> None:
    out = burn.m5([])
    head = subprocess.run(
        ["git", "-C", str(protocol.ROOT), "rev-parse", "HEAD:src"], check=True, capture_output=True, text=True
    ).stdout.strip()
    assert out["engine"] == {"matches": "c6d4f10", "src_tree": head}


def test_m5_checks_the_engine_before_it_burns_anything(monkeypatch: pytest.MonkeyPatch) -> None:
    # Delta 8, D8-S1: m5 itself must call the check, and before any burn.
    burned: list[Any] = []

    def moved() -> str:
        raise RuntimeError("M5 refuses to score: planted")

    def burn_one(spec: dict[str, Any]) -> dict[str, Any]:
        burned.append(spec)
        return {"ignited": False, "code": None}

    monkeypatch.setattr(burn, "check_engine", moved)
    monkeypatch.setattr(burn, "burn", burn_one)
    sample = SimpleNamespace(verdict=SimpleNamespace(klass=protocol.ACCEPTED), spec={"name": "x"}, model="S", arm="A1")
    with pytest.raises(RuntimeError, match="planted"):
        burn.m5([sample])
    assert burned == []


def test_m5_refuses_an_uncommitted_src_which_no_tree_names(tmp_path: Path) -> None:
    # Delta 8, D8-S2: HEAD:src names the committed engine, not an edited one.
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "GIT_CONFIG_NOSYSTEM": "1"}

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, env=env)

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "heat.py").write_text("K = 1\n")
    git("init", "-q")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "commit", "-qm", "t")
    assert len(burn.src_tree(tmp_path)) == 40
    (tmp_path / "src" / "heat.py").write_text("K = 2\n")
    with pytest.raises(RuntimeError, match="M5 refuses to score: src has uncommitted changes"):
        burn.src_tree(tmp_path)


def test_m5_burn_returns_a_fire_on_air_and_a_burnout_as_the_golden_rows_say() -> None:
    # Delta 8, D7-N2: burn()'s own returns on the golden's fire on air (legs) and burnout (block).
    golden = json.loads(burn.GOLDEN.read_text())
    arms = protocol.load_arms()
    specs = {raw["name"]: protocol.convert(raw, arms) for raw in golden["specs"]}
    assert burn.burn(specs["legs"]) == {"ignited": True, "fire_on_air": True}
    rows = golden["turns"]["block"]
    gone = next(t for t in range(1, len(rows)) if rows[t][0] == 0)
    want = {t: None if t >= gone else float(rows[t][1]) for t in burn.AT}
    assert burn.burn(specs["block"]) == {
        "ignited": True,
        "fire_on_air": False,
        "solid_gone_turn": gone,
        "integrity": want,
    }


def test_m6_and_m8_rates_come_from_the_labels() -> None:
    (p,) = furniture(1)
    impossible = next(x for x in protocol.load_prompts("dev") if x["stratum"] == "impossible")
    arms = protocol.load_arms()
    rows = [
        score.from_record(record(p, 0, TWO, "A3", "S"), arms, p),
        score.from_record(record(p, 1, TWO, "A3", "S"), arms, p),
        score.from_record(record(impossible, 0, TWO, "A3", "S"), arms, impossible),
    ]
    lab = score.Labels(
        {rows[0].key: "yes", rows[1].key: "no", rows[2].key: "partly"},
        {rows[0].key: "paired", rows[1].key: "paired", rows[2].key: "m8"},
    )
    got = score.m6_m8_labels(rows, lab)
    assert got["m6"]["paired/S/plain"]["counts"] == {"no": 1, "yes": 1}
    assert got["m6"]["paired/S/plain"]["yes_rate"]["rate"] == 0.5
    assert got["m8_closest_fit"]["m8/plain"]["counts"] == {"partly": 1}


def test_m9_counts_prompt_tokens_and_its_ratios() -> None:
    (p,) = furniture(1)
    arms = protocol.load_arms()
    rows = [score.from_record(record(p, 0, GOOD), arms, p), score.from_record(record(p, 1, HEAVY), arms, p)]
    got = score.m9(rows, None)["S/A1"]
    assert (got["prompt_tokens"], got["completion_tokens"]) == (20, 40)
    assert got["per_sample"] == {"tokens": 30.0, "wall_s": 1.0}
    assert got["per_m1_pass"] == {"tokens": 60.0, "wall_s": 2.0}


def test_a_spec_id_ignores_names_and_nothing_else() -> None:
    a = json.loads(spec("one", box([0, 0, 0], [40, 40, 50])))
    b = json.loads(spec("two", box([0, 0, 0], [40, 40, 50])))
    b["primitives"][0]["name"] = "lid"
    assert geometry.spec_id(a) == geometry.spec_id(b)
    other_material = json.loads(spec("one", box([0, 0, 0], [40, 40, 50], "steel")))
    other_corner = json.loads(spec("one", box([0, 0, 0], [40, 40, 51])))
    assert geometry.spec_id(a) != geometry.spec_id(other_material)
    assert geometry.spec_id(a) != geometry.spec_id(other_corner)


def test_the_labelling_sets_are_stratified_and_deterministic() -> None:
    dev = protocol.load_prompts("dev")
    d1 = labelling.draw(np.random.default_rng(0), dev)
    d2 = labelling.draw(np.random.default_rng(0), dev)
    assert d1 == d2
    assert len(d1.paired) == 30
    assert len(d1.trend) == 10
    assert len(d1.m8) == 10
    counts = {s: sum(p["stratum"] == s for p in dev) for s in labelling.POSSIBLE}
    q = labelling.quotas(counts, 30)
    assert sum(q.values()) == 30
    strata = {p["id"]: p["stratum"] for p in dev}
    assert {s: sum(strata[i] == s for i in d1.paired) for s in labelling.POSSIBLE} == q


def test_the_labelling_sheet_is_never_rewritten(tmp_path: Path) -> None:
    draws = labelling.draw(np.random.default_rng(score.SEED), protocol.load_prompts("dev"))
    p = score.prompt_meta()[draws.paired[0]]  # an item the owner labels
    path = write_run(tmp_path / "r.jsonl", [record(p, 0, TWO, "A3")], arm="A3")
    out = tmp_path / "labelling"
    score.score(args_for(path, tmp_path / "o.json", "--allow-partial", "--labelling-dir", str(out)))
    (row,) = map(json.loads, (out / "sheet.jsonl").read_text().splitlines())
    assert sorted(row) == ["id", "label", "prompt"]  # blind: the sheet doesn't say which set, model or arm
    with pytest.raises(FileExistsError):
        score.score(args_for(path, tmp_path / "o.json", "--allow-partial", "--labelling-dir", str(out)))


def test_check_scores_twice_in_separate_processes(tmp_path: Path) -> None:
    (p,) = furniture(1)
    path = write_run(tmp_path / "r.jsonl", [record(p, 0, GOOD)])
    out = tmp_path / "o.json"
    argv = ["--split", "dev", "--runs", str(path), f"--out={out}", "--allow-partial"]
    assert score.main([*argv, "--labelling-dir", str(tmp_path / "lab"), "--check"]) == 0
    assert not (tmp_path / "lab").exists()  # each process drew its own sheet in the temporary directory


# The digest of score()'s whole output on a fixed set of runs. It changes when any statistic, seed, percentile or
# exclusion changes; update it only for a change the errata or a review records.
SCORE_DIGEST = "8357e82517ff72a8bd1694094f8dc83e61bff85723ce8881526a4bfa2ad2f143"


def test_scores_output_is_pinned(tmp_path: Path) -> None:
    prompts = [*furniture(3), next(x for x in protocol.load_prompts("dev") if x["stratum"] == "impossible")]
    contents = [GOOD, TWO, HEAVY, THIN, OUTSIDE]
    rows = [record(p, s, contents[(i + s) % len(contents)]) for i, p in enumerate(prompts) for s in range(8)]
    path = write_run(tmp_path / "r.jsonl", rows)
    got = score.score(args_for(path, tmp_path / "o.json", "--allow-partial", "--m3"))
    digest_ = __import__("hashlib").sha256(json.dumps(got, sort_keys=True).encode()).hexdigest()
    assert digest_ == SCORE_DIGEST


@pytest.mark.parametrize("arm", ["A0", "A1"])
def test_a_reply_that_crashes_the_json_parser_is_a_parse_failure(monkeypatch: pytest.MonkeyPatch, arm: str) -> None:
    # Python 3.12's parser raises RecursionError past about 8,000 nested brackets (measured on the mini); a reply
    # must never crash the run, so the recursion is forced here, the same on every Python.
    def deep(*args: Any, **kwargs: Any) -> Any:
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(json, "loads", deep)
    monkeypatch.setattr(json.JSONDecoder, "raw_decode", deep)
    assert protocol.parse_reply('{"primitives": [[[[]]]]}', arm) is None
