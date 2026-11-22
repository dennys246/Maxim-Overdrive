"""The spec generator spike's own tests: generate.py against a fake llama-server, score.py on hand-made records.

Throwaway spike tests, outside ``tests/`` (the repo's suite never runs them): no model and no network beyond a fake
server bound to 127.0.0.1 on port 0. Run: ``.venv/bin/python -m pytest spikes/specgen/test_spike.py -q``.
"""

from __future__ import annotations

import json
import shutil
import sys
import threading
import urllib.error
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

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


def record(prompt: dict[str, Any], seed: int, content: str, arm: str = "A1") -> dict[str, Any]:
    verdict, _ = protocol.classify(content, "stop", arm, protocol.load_arms())
    attempt = {
        "raw": content,
        "finish": "stop",
        "context_overflow": False,
        "klass": verdict.klass,
        "completion_tokens": 20,
        "wall_s": 1.0,
    }
    return {
        "kind": "sample",
        "prompt_id": prompt["id"],
        "stratum": prompt["stratum"],
        "arm": arm,
        "model": "S",
        "seed": seed,
        "attempts": [attempt],
    }


def test_m1_and_its_prompt_clustered_interval_match_hand_values(tmp_path: Path) -> None:
    p1, p2 = [p for p in protocol.load_prompts("dev") if p["stratum"] == "furniture"][:2]
    rows = [record(p1, 0, GOOD), record(p1, 1, GOOD), record(p2, 0, GOOD), record(p2, 1, HEAVY)]
    path = tmp_path / "r.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    samples_ = score.load([path], protocol.load_arms())
    got = score.m1(samples_, np.random.default_rng(0))
    # Prompt rates 1.0 and 0.5: resampling two prompts gives 1.0, 0.75 or 0.5, each extreme with probability 1/4.
    assert got["rate"]["S/A1"] == {"rate": 0.75, "lo": 0.5, "hi": 1.0, "n": 4, "prompts": 2}
    assert got["classes"]["S/A1"] == {"accepted": 3, "refused:over_budget": 1}
    assert got["recorded_class_disagrees"] == 0


def test_degeneracy_flags_one_part_and_a_floating_part() -> None:
    p = next(p for p in protocol.load_prompts("dev") if p["stratum"] == "furniture" and not p.get("single_ok"))
    arms = protocol.load_arms()
    lone = score.from_record(record(p, 0, GOOD), arms, p)
    assert lone.degenerate == {"a_single": True, "b_one_material": False, "c_floating": False}
    floating = spec("shelf", box([0, 0, 0], [40, 40, 50]), box([0, 0, 60], [40, 40, 70]))
    two = score.from_record(record(p, 0, floating), arms, p)
    assert two.degenerate["c_floating"]


def test_contact_is_exact_at_a_tangent_face() -> None:
    # In floats 0.23 - 0.12 is 0.11000000000000001, past the 0.11 m radius, so a float comparison misses this tangent;
    # in micrometres the cylinder's side touches the box's face (found by searching every whole-cm tangent).
    arms = protocol.load_arms()
    s = protocol.convert(
        json.loads(
            spec(
                "t",
                box([23, 0, 0], [60, 60, 10]),
                {"kind": "cylinder", "center_xy_cm": [12, 12], "radius_cm": 11, "z_cm": [0, 10], "material": "wood"},
            )
        ),
        arms,
    )
    a, b = (geometry.shape(p) for p in protocol.authored(s) or ())
    assert geometry.touches(a, b)


def test_vendi_counts_identical_specs_as_one_and_disjoint_as_two() -> None:
    arms = protocol.load_arms()
    one = protocol.authored(protocol.convert(json.loads(GOOD), arms)) or ()
    far = protocol.authored(protocol.convert(json.loads(spec("f", box([0, 0, 0], [10, 10, 10]))), arms)) or ()
    same = geometry.vendi([geometry.raster(one), geometry.raster(one)])
    assert same == pytest.approx((1.0, 1.0))
    # Moved to the origin, a 10 cm cube sits inside the 40 x 40 x 50 cm crate: IoU 1000 / 80000.
    k = 1000 / 80000
    lam = np.array([1 - k, 1 + k]) / 2
    assert geometry.vendi([geometry.raster(one), geometry.raster(far)]) == pytest.approx(
        (float(np.sum(np.sqrt(lam)) ** 2), float(1 / lam.max()))
    )


def test_a_spec_id_ignores_names() -> None:
    a = json.loads(spec("one", box([0, 0, 0], [40, 40, 50])))
    b = json.loads(spec("two", box([0, 0, 0], [40, 40, 50])))
    b["primitives"][0]["name"] = "lid"
    assert geometry.spec_id(a) == geometry.spec_id(b)
    assert geometry.spec_id(a) != geometry.spec_id(json.loads(HEAVY))


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
