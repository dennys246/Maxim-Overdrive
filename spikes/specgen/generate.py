"""Run one (model, arm) cell of the spec generator spike over a prompt split, against a llama-server endpoint.

Throwaway spike code, never imported by ``src/``. The protocol is the frozen ``arms.yaml``'s; the classification is
``protocol.classify``. Every sample appends one JSON line to ``--out``, after a header line that records what the run
is (plan.md §7). The file is the truth and is never regenerated: a restart skips every (prompt, seed) already in it,
so a run stopped between windows costs nothing (the owner runs R in windows).

The endpoint is given on the command line and never written to any file (its address is private). Run, from the
repository root, on the machine that can reach the server:

    python spikes/specgen/generate.py --endpoint http://<host>:<port> --model S --arm A3 --split dev \
        --weights-sha256 "$(shasum -a 256 <the gguf> | cut -d' ' -f1)" --machine mini --out runs/S-A3-dev.jsonl

``spikes/specgen/run_window.sh`` runs every cell of one model inside the owner's nightly window.
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

# A resumed run must be this run: the same frozen inputs, code, data, lockfile, server and cell.
HEADER_KEYS_THAT_MUST_MATCH = (
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
OVERFLOW_TYPE = "exceed_context_size_error"  # llama-server's error.type for a request past its context (errata E14)
FROZEN_N_CTX, FROZEN_SLOTS = 16384, 1  # arms.yaml engine.server_flags: -c 16384 --parallel 1 (errata E15)


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
            if exc.code == 400 and _error_type(text) == OVERFLOW_TYPE:  # arms.yaml::protocol.context_overflow
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


def _error_type(text: str) -> str | None:
    """llama-server's ``error.type``, or None when the body isn't its error shape."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return None
    err = body.get("error") if isinstance(body, dict) else None
    kind = err.get("type") if isinstance(err, dict) else None
    return kind if isinstance(kind, str) else None


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


def schema_digest(arms: Mapping[str, Any], arm: str) -> str | None:
    """The digest of the JSON schema a grammar arm sends (llama.cpp compiles the grammar from it), or None."""
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
    """The server must be the frozen one: its build, its model file, and the context and slots arms.yaml's flags set.
    Returns its build_info. The model path is checked, never recorded: it names a private home directory."""
    build = str(props.get("build_info", ""))
    if build != _engine_build(arms):
        raise RunRefused(f"the server is build {build!r}, arms.yaml freezes {arms['engine']['llama_cpp']!r}")
    wanted = arms["engine"]["models"][model]["file"]
    if Path(str(props.get("model_path", ""))).name != wanted:
        raise RunRefused(f"the server serves another model file; model {model} is {wanted!r}")
    settings = props.get("default_generation_settings")
    n_ctx = settings.get("n_ctx") if isinstance(settings, dict) else None
    if n_ctx != FROZEN_N_CTX:
        raise RunRefused(f"the server's context is {n_ctx!r} tokens; arms.yaml's flags set {FROZEN_N_CTX} (-c)")
    if props.get("total_slots") != FROZEN_SLOTS:
        raise RunRefused(f"the server has {props.get('total_slots')!r} slots; arms.yaml's flags set 1 (--parallel)")
    return build


def check_weights(measured: str, model: str) -> str:
    """The SHA-256 measured on the server's machine must be freeze.sha256's; returns it."""
    _, frozen = protocol.read_manifest()
    if measured.strip().lower() != frozen[model]:
        raise RunRefused(f"the measured weights of {model} are {measured!r}; freeze.sha256 has {frozen[model]!r}")
    return frozen[model]


def header(
    arms: Mapping[str, Any], *, model: str, arm: str, split: str, runtime: str, machine: str, weights: str
) -> dict[str, Any]:
    """Plan §7's run header. The flags keep arms.yaml's placeholder for the host, so they compare byte for byte.
    ``weights`` is the SHA-256 measured on the server's machine and checked against freeze.sha256."""
    frozen = protocol.check_frozen()
    data = protocol.ROOT / "data"
    half = protocol.TRUTH_DX_M / 2
    return {
        "kind": "header",
        "version": 0,
        "simcore_commit": _git("rev-parse", "HEAD"),
        "src_tree": _git("rev-parse", "HEAD:src"),
        "spike_tree": protocol.spike_tree(),
        "lockfile": _lockfile(),
        "data_sha256": {p: protocol.sha256_file(data / p) for p in ("materials/core.yaml", "world/actions.yaml")},
        "scene": {"extent_m": list(protocol.SCENE_EXTENT_M), "truth_dx_m": protocol.TRUTH_DX_M},
        "offsets_m": [list(protocol.OFFSET_M), [c + half for c in protocol.OFFSET_M]],
        "frozen": frozen,
        "engine": {"llama_cpp": arms["engine"]["llama_cpp"], "server_flags": arms["engine"]["server_flags"]},
        "runtime": runtime,
        "model": {"id": model, **arms["engine"]["models"][model], "weights_sha256": weights, "weights_measured": True},
        "arm": arm,
        "split": split,
        "machine": machine,
    }


def repair_tail(out: Path) -> int:
    """Cut a torn last line, left by a stop mid-write, back to the last newline, so the next record starts on a line
    of its own. Returns the bytes cut. An empty file stays empty and is treated as new."""
    if not out.exists():
        return 0
    data = out.read_bytes()
    keep = data.rfind(b"\n") + 1  # 0 when no line was ever finished
    if keep == len(data):
        return 0
    with out.open("r+b") as f:
        f.truncate(keep)
    return len(data) - keep


def done_samples(out: Path, head: Mapping[str, Any]) -> set[tuple[str, int]]:
    """The (prompt, seed) pairs already in ``out``, after checking its header is this run's."""
    if not out.exists() or out.stat().st_size == 0:
        return set()
    lines = out.read_text(encoding="utf-8").splitlines()
    rows = []
    for number, line in enumerate(lines, start=1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RunRefused(f"{out} has a malformed line {number}: not a run file this code wrote") from exc
    first = rows[0]
    for key in HEADER_KEYS_THAT_MUST_MATCH:
        if first.get(key) != head.get(key):
            raise RunRefused(f"{out} belongs to another run: its {key} differs")
    return {(r["prompt_id"], r["seed"]) for r in rows[1:] if r.get("kind") == "sample"}


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
        "split": head["split"],
        "arm": head["arm"],
        "model": head["model"]["id"],
        "weights_sha256": head["model"]["weights_sha256"],
        "runtime": head["runtime"],
        "machine": head["machine"],
        "sampling": sampling(arms),
        "seed": seed,
        "schema_digest": schema_digest(arms, head["arm"]),
        "attempts": attempts,
    }


def run(server: Server, args: argparse.Namespace) -> int:
    arms = protocol.load_arms()
    seeds = list(arms["sampling"]["seeds"]) if args.seeds is None else args.seeds
    if not set(seeds) <= set(arms["sampling"]["seeds"]):
        raise RunRefused(f"seeds {seeds} are not all among arms.yaml's {arms['sampling']['seeds']}")
    runtime = check_server(server.props(), arms, args.model)
    weights = check_weights(args.weights_sha256, args.model)
    head = header(
        arms, model=args.model, arm=args.arm, split=args.split, runtime=runtime, machine=args.machine, weights=weights
    )
    out = Path(args.out)
    cut = repair_tail(out)
    if cut:
        print(f"generate: cut a torn last line of {cut} bytes from {out}", file=sys.stderr)
    done = done_samples(out, head)
    prompts = _chosen(protocol.load_prompts(args.split), args.prompt_ids)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out.open("a", encoding="utf-8") as f:
        if out.stat().st_size == 0:
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
        "--weights-sha256",
        required=True,
        help="the SHA-256 of the served GGUF, measured on the server's machine (shasum -a 256); checked against"
        " freeze.sha256",
    )
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
