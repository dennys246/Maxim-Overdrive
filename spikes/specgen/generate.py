"""Run one (model, arm) cell of the spec generator spike over a prompt split, against a llama-server endpoint.

Throwaway spike code, never imported by ``src/``. The protocol is the frozen ``arms.yaml``'s; the classification is
``protocol.classify``. Every sample appends one JSON line to ``--out``, after a header line that records what the run
is (plan.md §7). The file is the truth and is never regenerated: a restart skips every (prompt, seed) already in it,
so a run stopped between windows costs nothing (the owner runs R in windows).

The endpoint is given on the command line and never written to any file (its address is private). Run, from the
repository root, on the machine that can reach the server:

    python spikes/specgen/generate.py --endpoint http://<host>:<port> --model S --arm A3 --split dev \
        --machine mac-mini-m4pro --out spikes/specgen/runs/S_A3_dev.jsonl
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import protocol

from simcore.core.digest import digest

HEADER_KEYS_THAT_MUST_MATCH = ("frozen", "src_tree", "model", "arm", "split", "engine", "scene", "offsets_m")


class RunRefused(RuntimeError):
    """The run can't start: it would not be the pre-registered one, or its output file belongs to another run."""


@dataclass(frozen=True)
class Reply:
    """One server reply, or the context-overflow refusal that stands for one."""

    content: str
    finish: str | None
    reasoning_chars: int
    prompt_tokens: int | None
    completion_tokens: int | None
    context_overflow: bool = False


class Server:
    """A llama-server's OpenAI-compatible chat endpoint. The URL is held in memory only."""

    def __init__(self, endpoint: str, timeout_s: float = 1800.0) -> None:
        self._base = endpoint.rstrip("/")
        self._timeout = timeout_s

    def props(self) -> dict[str, Any]:
        with urllib.request.urlopen(self._base + "/props", timeout=self._timeout) as r:
            props: dict[str, Any] = json.loads(r.read())
        return props

    def chat(self, body: Mapping[str, Any]) -> Reply:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._base + "/v1/chat/completions", data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                payload = json.loads(r.read())
        except urllib.error.HTTPError as exc:
            with exc:  # the error's response holds the connection; close it on every path
                text = exc.read().decode("utf-8", "replace")
            if exc.code == 400 and "context" in text.lower():  # arms.yaml::protocol.context_overflow
                return Reply("", None, 0, None, None, context_overflow=True)
            raise
        choice = payload["choices"][0]
        message = choice.get("message", {})
        usage = payload.get("usage") or {}
        return Reply(
            message.get("content") or "",
            choice.get("finish_reason"),
            len(message.get("reasoning_content") or ""),
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )


def compact(value: object) -> str:
    """arms.yaml::protocol.example_serialisation: compact JSON, ASCII only, keys in file order."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def base_messages(arms: Mapping[str, Any], arm: str, prompt_text: str) -> list[dict[str, str]]:
    """The system text, then (A2, A3) the four examples as user/assistant turns, then the prompt."""
    messages = [{"role": "system", "content": arms["instructions"]}]
    if arms["arms"][arm]["examples"]:
        for ex in arms["examples"]:
            messages.append({"role": "user", "content": arms["user_template"].format(prompt=ex["prompt"])})
            messages.append({"role": "assistant", "content": compact(ex["reply"])})
    messages.append({"role": "user", "content": arms["user_template"].format(prompt=prompt_text)})
    return messages


def sampling(arms: Mapping[str, Any]) -> dict[str, Any]:
    s = arms["sampling"]
    return {k: s[k] for k in ("temperature", "top_k", "top_p", "min_p", "repeat_penalty")}


def request_body(arms: Mapping[str, Any], arm: str, messages: list[dict[str, str]], seed: int) -> dict[str, Any]:
    body: dict[str, Any] = {"messages": messages, "seed": seed, "max_tokens": arms["sampling"]["max_output_tokens"]}
    body.update(sampling(arms))
    if arms["sampling"]["thinking"] is False:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    if arms["arms"][arm]["grammar"]:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "spec", "schema": arms["schema"]}}
    return body


def grammar_hash(arms: Mapping[str, Any], arm: str) -> str | None:
    return digest(arms["schema"]) if arms["arms"][arm]["grammar"] else None


def run_attempt(
    server: Server, arms: Mapping[str, Any], arm: str, messages: list[dict[str, str]], *, attempt: int, seed: int
) -> dict[str, Any]:
    """One request, classified in arms.yaml's order. Wall time is recorded for M9 only; nothing scored reads it."""
    started = time.monotonic()
    reply = server.chat(request_body(arms, arm, messages, protocol.retry_seed(attempt, seed)))
    wall_s = time.monotonic() - started
    finish = "length" if reply.context_overflow else reply.finish  # an overflow is also the class truncated
    verdict, _ = protocol.classify(reply.content, finish, arm, arms)
    return {
        "attempt": attempt,
        "seed": protocol.retry_seed(attempt, seed),
        "raw": reply.content,
        "finish": reply.finish,
        "context_overflow": reply.context_overflow,
        "reasoning_chars": reply.reasoning_chars,
        "prompt_tokens": reply.prompt_tokens,
        "completion_tokens": reply.completion_tokens,
        "wall_s": round(wall_s, 3),
        **{k: v for k, v in asdict(verdict).items()},
        "m1_pass": verdict.m1_pass,
        "fed_back": None,
    }


def loop_ends(attempt: Mapping[str, Any], arms: Mapping[str, Any]) -> bool:
    """A3 ends at the first attempt passing M1, at a truncated reply, at a too_small refusal (never fed back), or at a
    parse failure, for which arms.yaml defines no feedback (an ambiguity, reported with the spike's code)."""
    never = set(arms["protocol"]["a3_never_fed_back"])
    return (
        bool(attempt["m1_pass"])
        or attempt["klass"] in (protocol.TRUNCATED, protocol.PARSE_FAILURE)
        or (attempt["code"] in never)
    )


def run_sample(
    server: Server, arms: Mapping[str, Any], arm: str, prompt: Mapping[str, Any], seed: int
) -> list[dict[str, Any]]:
    """One sample: one attempt, or A3's conversation of up to 1 + retries attempts, the last of which is scored."""
    messages = base_messages(arms, arm, prompt["text"])
    retries = int(arms["arms"][arm]["retries"])
    attempts: list[dict[str, Any]] = []
    for attempt in range(retries + 1):
        result = run_attempt(server, arms, arm, messages, attempt=attempt, seed=seed)
        attempts.append(result)
        if attempt == retries or loop_ends(result, arms):
            break
        feedback = arms["feedback_template"].format(agent_text=result["agent_text"])
        result["fed_back"] = feedback
        messages = [*messages, {"role": "assistant", "content": result["raw"]}, {"role": "user", "content": feedback}]
    return attempts


def _git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(protocol.ROOT), *args], check=True, capture_output=True, text=True)
    return out.stdout.strip()


def _lockfile() -> dict[str, str]:
    name = f"py{sys.version_info.major}.{sys.version_info.minor}.txt"
    return {"name": name, "sha256": protocol.sha256_file(protocol.ROOT / "constraints" / name)}


def _engine_build(arms: Mapping[str, Any]) -> str:
    """The `/props` build_info arms.yaml freezes: 'b10621-c1d0e7a00' from 'build 10621 (c1d0e7a00)' (errata E9)."""
    _, number, commit = str(arms["engine"]["llama_cpp"]).split()
    return f"b{number}-{commit.strip('()')}"


def check_server(props: Mapping[str, Any], arms: Mapping[str, Any], model: str) -> str:
    """The server's build and model must be the frozen ones; returns its build_info."""
    build = str(props.get("build_info", ""))
    if build != _engine_build(arms):
        raise RunRefused(f"the server is build {build!r}, arms.yaml freezes {arms['engine']['llama_cpp']!r}")
    wanted = arms["engine"]["models"][model]["file"]
    if not str(props.get("model_path", "")).endswith(wanted):
        raise RunRefused(f"the server serves {props.get('model_path')!r}, model {model} is {wanted!r}")
    return build


def header(arms: Mapping[str, Any], *, model: str, arm: str, split: str, runtime: str, machine: str) -> dict[str, Any]:
    """Plan §7's run header. The flags keep arms.yaml's placeholder for the host, so they compare byte for byte."""
    frozen = protocol.check_frozen()
    _, weights = protocol.read_manifest()
    data = protocol.ROOT / "data"
    half = protocol.TRUTH_DX_M / 2
    return {
        "kind": "header",
        "version": 0,
        "simcore_commit": _git("rev-parse", "HEAD"),
        "src_tree": _git("rev-parse", "HEAD:src"),
        "lockfile": _lockfile(),
        "data_sha256": {p: protocol.sha256_file(data / p) for p in ("materials/core.yaml", "world/actions.yaml")},
        "scene": {"extent_m": list(protocol.SCENE_EXTENT_M), "truth_dx_m": protocol.TRUTH_DX_M},
        "offsets_m": [list(protocol.OFFSET_M), [c + half for c in protocol.OFFSET_M]],
        "frozen": frozen,
        "engine": {"llama_cpp": arms["engine"]["llama_cpp"], "server_flags": arms["engine"]["server_flags"]},
        "runtime": runtime,
        "model": {"id": model, **arms["engine"]["models"][model], "weights_sha256": weights[model]},
        "arm": arm,
        "split": split,
        "machine": machine,
    }


def done_samples(out: Path, head: Mapping[str, Any]) -> set[tuple[str, int]]:
    """The (prompt, seed) pairs already in ``out``, after checking its header is this run's."""
    if not out.exists():
        return set()
    lines = out.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    for key in HEADER_KEYS_THAT_MUST_MATCH:
        if first.get(key) != head.get(key):
            raise RunRefused(f"{out} belongs to another run: its {key} differs")
    return {(r["prompt_id"], r["seed"]) for r in map(json.loads, lines[1:]) if r.get("kind") == "sample"}


def sample_record(
    head: Mapping[str, Any],
    arms: Mapping[str, Any],
    prompt: Mapping[str, Any],
    seed: int,
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Plan §7's per-sample record; the last attempt is the one scored."""
    return {
        "kind": "sample",
        "prompt_id": prompt["id"],
        "stratum": prompt["stratum"],
        "arm": head["arm"],
        "model": head["model"]["id"],
        "weights_sha256": head["model"]["weights_sha256"],
        "runtime": head["runtime"],
        "machine": head["machine"],
        "sampling": sampling(arms),
        "seed": seed,
        "grammar_hash": grammar_hash(arms, head["arm"]),
        "attempts": attempts,
    }


def run(server: Server, args: argparse.Namespace) -> int:
    arms = protocol.load_arms()
    seeds = list(arms["sampling"]["seeds"]) if args.seeds is None else args.seeds
    if not set(seeds) <= set(arms["sampling"]["seeds"]):
        raise RunRefused(f"seeds {seeds} are not all among arms.yaml's {arms['sampling']['seeds']}")
    runtime = check_server(server.props(), arms, args.model)
    head = header(arms, model=args.model, arm=args.arm, split=args.split, runtime=runtime, machine=args.machine)
    out = Path(args.out)
    done = done_samples(out, head)
    prompts = _chosen(protocol.load_prompts(args.split), args.prompt_ids)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out.open("a", encoding="utf-8") as f:
        if not done and out.stat().st_size == 0:
            f.write(json.dumps(head) + "\n")
        for prompt in prompts:
            for seed in seeds:
                if (prompt["id"], seed) in done:
                    continue
                attempts = run_sample(server, arms, args.arm, prompt, seed)
                f.write(json.dumps(sample_record(head, arms, prompt, seed, attempts)) + "\n")
                f.flush()
                written += 1
    return written


def _chosen(prompts: Iterable[dict[str, Any]], ids: list[str] | None) -> list[dict[str, Any]]:
    listed = list(prompts)
    if ids is None:
        return listed
    known = {p["id"] for p in listed}
    if not set(ids) <= known:
        raise RunRefused(f"prompt ids {sorted(set(ids) - known)} are not in this split")
    return [p for p in listed if p["id"] in ids]


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--endpoint", required=True, help="the llama-server URL; never written to any file")
    ap.add_argument("--model", required=True, choices=("S", "R"))
    ap.add_argument("--arm", required=True, choices=("A0", "A1", "A2", "A3"))
    ap.add_argument("--split", required=True, choices=tuple(protocol.SPLITS))
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--machine",
        default=f"{platform.system()}-{platform.machine()}",
        help="a label for the machine; never the host name, which is private",
    )
    ap.add_argument("--seeds", type=int, nargs="+", help="a subset of arms.yaml's seeds (default: all)")
    ap.add_argument("--prompt-ids", nargs="+", help="a subset of the split's prompts (default: all)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        written = run(Server(args.endpoint), args)
    except (RunRefused, protocol.FrozenMismatch) as exc:
        print(f"generate: refused: {exc}", file=sys.stderr)
        return 2
    print(f"generate: {written} samples written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
