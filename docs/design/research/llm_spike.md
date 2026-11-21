# The LLM spike: first run (2026-11-19)

Owner decision O20: a throwaway measurement outside the replayable core, with raw calls to a local model and no
Maxim. It makes no claim about NPC behaviour. Script: `spikes/llm/measure.py`. Raw samples:
`spikes/llm/results/20261119T195328.jsonl`.

## Setup

- **Machine:** Apple M2, 24 GB, macOS. Ollama 0.17.0 on 127.0.0.1.
- **Models:** `qwen2.5:3b` and `qwen2.5:7b`, Ollama's default quantisation.
- **Prompt:** an NPC turn. A ripperdoc persona, padded with remembered lines to about 300, 1,500 or 3,000 words, then
  one player line and an instruction to reply in one or two sentences.
- **Decoding:** at most 60 output tokens, temperature 0.7.
- **Sampling:** each cell sends 1, 2 or 4 requests at once ("in flight": NPCs asking one model together), five
  repeats, after a warm-up call that isn't counted.
- **Not measured:** no cloud model, because no API key and spending cap were set (an owner decision).

## The run was not on a quiet machine

The plan requires timing on a quiet machine (`foundations_plan.md` §6). This run wasn't one. Other sessions' gates
ran during it, and the 1-minute load average rose from about 7 to between 35 and 93 after the first three cells.

**Only the cells below were measured near the quiet baseline.** Every other cell mostly measures the other sessions'
CPU use. They are kept in the raw file, but no conclusion rests on them.

| `qwen2.5:3b`, ~300-word prompt | TTFT, min / median | full reply, median | decode | load |
|---|---|---|---|---|
| 1 in flight | 0.30 / 0.32 s | 1.29 s | 23.8 tok/s | 6.7 |
| 2 in flight | 0.15 / 0.54 s | 1.46 s | 31.5 tok/s | 7.5 |
| 4 in flight | 0.18 / 1.40 s | 2.18 s | 31.4 tok/s | 8.0 |

TTFT is the time to the first token.

## What these three cells suggest (tentative: one run, near-quiet, short prompts only)

- **One NPC can speak a real first word inside O11a's account window.** O11a's timeline is filler, then an account at
  about 600–700 ms, then a yield after 1 s of silence (`npcs_and_sem.md` O11a). A median TTFT of 0.32 s means the
  model's own first token arrives before the account is due, for a short prompt.
- **About two NPCs per local 3B model hold that, on this machine.** At 2 in flight the median is 0.54 s, still
  inside the account window. At 4 it is 1.40 s, past the yield. Ollama's default server queues requests, so the
  growth with in-flight count is the cost of sharing one model.
- **The full reply takes 1.3–2.2 s, longer than the first token.** Speech is stamped per syllable (OA4) and, once streaming
  lands (OD-A25; not before, O50), the NPC speaks while the rest decodes.

## What it does not show

- **Anything at 1,500 or 3,000 words, or for the 7B model.** Those cells ran at load 35–93.
- **Maxim's real prompts.** Maxim's prompt sizes and its multi-call deliberation (up to 3 model calls with a percept
  source, 2 without; `npcs_and_sem.md` §6.1) aren't modelled here. A thought can cost two or three of these calls.
- **Quality.** No reply was judged for whether it sounds like the NPC.
- **Cost.** No cloud model was measured.

## Next

1. Rerun on a quiet machine, with no other session's gate running, and record the load before and after.
2. Measure prompt sizes taken from a real Maxim prompt once the bridge prototype (O37) can produce one.
3. Measure cloud TTFT and cost if the owner sets an API key and a cap.
4. Feed the results into the speed trait's slow-tail question (O30) and the account timing (O11a), and only then
   into a budget.
