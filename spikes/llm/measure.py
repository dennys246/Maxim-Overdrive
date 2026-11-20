"""The LLM spike (owner decision O20): how fast does a local model answer an NPC-sized prompt?

Throwaway measurement, outside the replayable core: raw calls to a local Ollama server on 127.0.0.1, no Maxim, no
claim about behaviour. It measures, per model, prompt size and number of NPCs talking at once:

- time to the first token (TTFT): what O11a's conversational timing must hide behind filler and an account;
- time to the full reply, output tokens and decode rate;
- how latency grows when several NPCs ask at once (requests in flight against one model), the measure of how many
  NPCs one local model can serve.

Every run records the machine's load average, because the host is shared with other sessions and latency under
load is not latency on a quiet machine. Results are JSON lines in ``spikes/llm/results/``.

Run: ``python spikes/llm/measure.py --models qwen2.5:3b qwen2.5:7b`` (Ollama must be serving).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

HOST = "http://127.0.0.1:11434"
HERE = Path(__file__).resolve().parent
PERSONA = (
    "You are Vex, a ripperdoc in the city of Maxim Prime. You are tired, precise and a little kind. You speak in short "
    "sentences. You remember the people who come to your clinic."
)
MEMORY = "Earlier today a courier came in with a burnt cyberarm; you fixed it and he paid late."
PLAYER = "Player: The alley's on fire. Did you see who started it?"
INSTRUCTION = "Reply as Vex, in one or two sentences, out loud, with no stage directions."


@dataclass(frozen=True)
class Sample:
    model: str
    context_words: int
    in_flight: int
    ttft_s: float
    total_s: float
    prompt_tokens: int
    output_tokens: int
    decode_tok_s: float
    load_avg_1m: float


def build_prompt(context_words: int) -> str:
    """An NPC turn padded with remembered lines to about ``context_words`` words (about 1.3 tokens each)."""
    lines = [PERSONA]
    while sum(len(line.split()) for line in lines) < context_words:
        lines.append(MEMORY)
    return "\n".join([*lines, PLAYER, INSTRUCTION])


def _request(model: str, prompt: str) -> urllib.request.Request:
    body = {"model": model, "prompt": prompt, "stream": True, "options": {"num_predict": 60, "temperature": 0.7}}
    return urllib.request.Request(f"{HOST}/api/generate", data=json.dumps(body).encode(), method="POST")


def one_call(model: str, context_words: int, in_flight: int) -> Sample:
    """Stream one reply and time its first token and its end."""
    start = time.perf_counter()
    ttft = None
    final: dict[str, int] = {}
    with urllib.request.urlopen(_request(model, build_prompt(context_words)), timeout=300) as resp:
        for raw in resp:
            chunk = json.loads(raw)
            if ttft is None and chunk.get("response"):
                ttft = time.perf_counter() - start
            if chunk.get("done"):
                final = chunk
    total = time.perf_counter() - start
    out, eval_ns = int(final.get("eval_count", 0)), int(final.get("eval_duration", 0))
    return Sample(
        model,
        context_words,
        in_flight,
        ttft or total,
        total,
        int(final.get("prompt_eval_count", 0)),
        out,
        out / (eval_ns / 1e9) if eval_ns else 0.0,
        os.getloadavg()[0],
    )


def burst(model: str, context_words: int, in_flight: int) -> list[Sample]:
    """``in_flight`` NPCs ask the same model at once."""
    with ThreadPoolExecutor(max_workers=in_flight) as pool:
        return list(pool.map(lambda _: one_call(model, context_words, in_flight), range(in_flight)))


def run(models: list[str], contexts: list[int], in_flight: list[int], repeats: int) -> list[Sample]:
    samples: list[Sample] = []
    for model in models:
        one_call(model, 50, 1)  # warm-up: loads the model; not counted
        for words in contexts:
            for n in in_flight:
                for _ in range(repeats):
                    samples += burst(model, words, n)
    return samples


def summarise(samples: list[Sample]) -> list[str]:
    keys = sorted({(s.model, s.context_words, s.in_flight) for s in samples})
    out = ["model | context words | in flight | TTFT min / median s | full reply median s | decode tok/s | load"]
    for model, words, n in keys:
        group = [s for s in samples if (s.model, s.context_words, s.in_flight) == (model, words, n)]
        ttft = [s.ttft_s for s in group]
        out.append(
            f"{model} | {words} | {n} | {min(ttft):.2f} / {statistics.median(ttft):.2f} | "
            f"{statistics.median(s.total_s for s in group):.2f} | "
            f"{statistics.median(s.decode_tok_s for s in group):.1f} | "
            f"{statistics.median(s.load_avg_1m for s in group):.1f}"
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--models", nargs="+", default=["qwen2.5:3b", "qwen2.5:7b"])
    parser.add_argument("--contexts", nargs="+", type=int, default=[300, 1500, 3000])
    parser.add_argument("--in-flight", nargs="+", type=int, default=[1, 2, 4])
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    samples = run(args.models, args.contexts, args.in_flight, args.repeats)
    results = HERE / "results"
    results.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    meta = {"machine": platform.machine(), "platform": platform.platform(), "host": HOST}
    lines = [json.dumps({"meta": meta}), *(json.dumps(asdict(s)) for s in samples)]
    (results / f"{stamp}.jsonl").write_text("\n".join(lines) + "\n")
    print("\n".join(summarise(samples)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
