**Verdict: not ready on performance.** One BLOCKER: the `chunk` message has no producer in Maxim's backends, so no reply can stream. There are seven SHOULD-FIX and two NIT findings. The §7 arithmetic is correct as written, but it assumes the barrier parks agents one after another.

# Performance review: `docs/design/inference_placement.md` (v1 draft)

Diff range `814dea9..04ab810`. I read the design in full, plus the diffs to `npcs_and_sem.md`, `boundaries.md`, `checklists.md` and `architecture.md`. I also read `npcs_and_sem.md` §4.4, §4.5, §6.3 and §6.6's cost line, `research/llm_spike.md`, the cost table in `checklists.md` and the B5 row in `standards_backlog.md`. On the Maxim side I read, at `043eab8f` with `git show`: `backend_protocol.py`, `types.py::LLMResponse`, the `_stream_response`, `_parse_response` and `_build_system_blocks` paths in `anthropic_backend.py`, `openai_backend.py` and `maxim_peer_backend.py`, and `utils/cancellation.py`. I ran one script, a queueing fixed point for finding 5, which is described there.

---

## BLOCKER

### B-1. `inference_placement.md::§3` (the `chunk` message) and `§1`: no backend emits chunks, so the first word arrives only when the whole reply is done

**Defect.** The gateway contract has `chunk(attempt_id, seq, text)`. §3 compares the hop's cost against time to first token, which assumes the gateway streams. The only call the design names is `complete_with_usage(...)`, and it returns one `LLMResponse`. With `stream=True`, all three backends read the stream internally and still return one value at the end:
- `_AnthropicBackend._stream_response` collects `text_parts` and returns an `LLMResponse`.
- `_OpenAIBackend._stream_response` does `for chunk in stream: … text_parts.append(...)`, then `"".join(text_parts)`.
- `_MaximPeerBackend._stream_response` does the same.

None of them takes a per-token callback or returns an iterator. I searched the three backends, `backend_protocol.py` and `types.py` for `on_token`, `on_chunk`, `callback`, `Iterator` and `yield`, and found nothing. The only per-chunk hook is `_register_byte_received_safe()`, a stall detector, and it carries no text. So the gateway has nothing to relay as a `chunk`, and the design's alternative (c), its own HTTP clients, was declined.

**Failure scenario.** One NPC answers the player on the spike's measured configuration (`qwen2.5:3b`, about 300 words, one call in flight):
- Through this gateway, the first token reaches the host with the full reply, at a median of **1.29 s** instead of **0.32 s**.
- At 2 in flight it is **1.46 s** instead of 0.54 s.
- Both are past O11a's account at about 600–700 ms and its yield at about 1 s (`npcs_and_sem.md` §4.4), even for one NPC alone.

The spike's one hopeful conclusion ("one NPC can speak a real first word inside O11a's account window") rests on streaming. This design takes that away, and §4.5's lever 3 ("streaming the first token for P2 speech") goes with it. The same applies under dilate: P2 speech waits on L(full) rather than L(first token).

**Why BLOCKER.** The channel names a message that nothing in the chosen transports can produce. The §3 cost claim rests on it, and §9 has no upstream ask for it.

**Possible fixes (unverified):**
- An OD-I item asking Maxim for a streaming surface on the backends: an iterator, or a chunk callback.
- Or a recorded decision that P2 speech goes without streaming until that lands, with §4.5's table recomputed on full-reply latency.

---

## SHOULD-FIX

### S-1. `inference_placement.md::§1` (fact 3) and `§2.5`: "a cancelled call holds its slot until it returns" is not true of every transport, and the capacity model is off in both directions

**Defect.** Fact 3 cites only the peer backend's non-streaming check before the call (`:555-566`). But `_MaximPeerBackend._stream_response` also checks `is_cancelled()` between SSE chunks and raises `BackendDown`. That check reads a `ContextVar` holding a `threading.Event`, which a caller in the gateway can set (`utils/cancellation.py`, docstring and usage pattern). On a peer stream, a cancelled call can therefore free its slot within about one chunk: about 30–40 ms at the spike's 24–31 tok/s.

The OpenAI and Anthropic stream loops have no such check, so there the design's claim holds.

**Failure scenario:**
- §2.5, as written, under-uses `maxim_peer`: an abandoned 60-token reply holds its slot for about 2 s when it could free it in tens of milliseconds.
- On a `loopback` server, an abandoned call costs more than a slot. The server keeps decoding it in the same batch as live requests, and that slows them: the spike's median time to first token rises from 0.32 s to 0.54 s to 1.40 s as in-flight calls go from 1 to 2 to 4.
- The meter "slots held by abandoned calls" counts the slot and not the compute taken from live calls.

**Fix (unverified).** §2.5 states, per transport, whether cancelling frees the slot and stops the decode. It meters compute wasted on abandoned calls, as abandoned output tokens per placement.

### S-2. `inference_placement.md::§2.2` (`timeout_s`) and `§2.5`: `timeout_s` is not a wall ceiling on these transports, so a slot can be held for minutes, and under `pinned` that takes the whole role down

**Defect.** §2.2 calls `timeout_s` "the wall ceiling per call". The transports apply it in two ways that make it something else:
- **It is per operation.** They pass it as the HTTP client's timeout (`Anthropic(api_key, timeout=…)`, `anthropic_backend.py:237`; `timeout=self._get_timeout()`, `openai_backend.py:279`, `:288`). From httpx's documented semantics, which I did not run, a single float is a timeout per operation, so on a stream it is an idle gap between reads, not a limit on the whole call. A slow stream that is still alive can run past it without limit.
- **It is multiplied by retries.** The Anthropic SDK and Maxim keep their own retries unless set to zero. `_OpenAIBackend` adds `max_gateway_retries = 4`, about 50 s of backoff by its own comment. A slot's worst-case hold is then about (1 + `max_retries` + 4) × `timeout_s` + about 50 s. That is about 7.8 min at the backends' default 60 s with `max_retries = 2`.

**Failure scenario.** A role is `pinned` to a `loopback` placement with `max_in_flight: 2`, and the server stalls (it swaps a model, or the GPU is saturated):
1. Both calls are abandoned at the liveness ceiling. Under §2.5 the placement is then "full", not failed.
2. A cooldown (§2.6) starts only when an outcome arrives, and no outcome arrives until a call returns.
3. Under `pinned`, a full placement means wait (§2.4), so every thought in that role ends as `thought_failed(timeout)` for minutes.
4. This happens even though an eligible `owner_lan` placement sits idle, and the run goes to tier 3.

**Fix (unverified).** A placement whose slots are all held by abandoned calls counts as failed for selection: it enters cooldown and the next eligible placement takes over. That needs a contract change in §2.4 and §2.5. The OD-I9 ask should also cover setting `max_retries` to zero for the OpenAI backend.

### S-3. `inference_placement.md::§2.2` (`max_in_flight`, `context_tokens`): slots are not tied to the server's real concurrency, so dispatch by deadline is lost

**Defect 1: deadline order.** `max_in_flight` is a whole number the player declares. If it exceeds the server's real parallel slots (Ollama's `OLLAMA_NUM_PARALLEL`, llama.cpp's `-np`), the server queues the extra calls first come, first served. The spike notes that "Ollama's default server queues requests". The lane's dispatch by deadline (`npcs_and_sem.md` §4.4: "the host never waits on a request queued behind later-due ones") then holds only up to the server's real concurrency. Beyond it, a request due soon waits inside the server behind one due later, and the meter "how long requests wait for a slot" reads zero while it does.

**Defect 2: shared servers.** Two placements on one server are counted separately: two roles on one Ollama, or a 3B and a 7B model. Their slots add up and oversubscribe the server. With two models on one Ollama instance, Ollama may also swap models in and out of memory, which takes seconds (unverified).

**Defect 3: context per slot.** Per llama.cpp's documentation (unverified here), `llama-server -c 8192 -np 4` gives each slot 2,048 tokens. A player who declares `context_tokens: 8192` passes the envelope check at load, and every long request then fails at dispatch as `context_overflow`.

**Fix (unverified).**
- The contract groups placements by the server behind them, with a combined slot count.
- `max_in_flight` must not exceed that server's real concurrency.
- `context_tokens` means context per slot.
- B5 gets a probe that measures the real concurrency.

### S-4. `inference_placement.md::§0` (O48) and `§2.4`: the throughput cost of `pinned` is never stated, and §4.5's formula has no term for queueing, which is where that cost sits

**Defect.** O48 was decided without a number. The formula in `npcs_and_sem.md` §4.5, `1/(f·L/D + (1−f)/dial_max)`, takes L as the service latency. Under `pinned`, the time a request waits for a slot on one placement adds to L, and the formula leaves that out.

**Measurement (verified by running a script; the model is mine, not the doc's).** I used the doc's formula, with L replaced by service time plus mean wait in a standard multi-server queue (Erlang C), random arrivals, and iterated to a fixed point. The inputs are §4.5's own:
- 20 NPCs, 2 thoughts per world minute each, D = 1 s, dial_max = 20;
- f = 0.49, from random overlap of the pending windows;
- service time S = 1.46 s, the spike's full reply at 2 in flight.

| Case | Effective dial | Mean L | Share of requests that wait |
|---|---|---|---|
| `pinned` to one placement with 2 slots | **1.03×** | 1.95 s | 33% |
| `spill` over 2 + 2 slots on two machines | **1.34×** | 1.49 s | 5% |

So `pinned` costs about **23% of the dial** in this scene. For speech, a third of turns start late; the mean wait among those that wait is S/(c − a) ≈ 1.46 s at the fixed point, which pushes them past the 1 s yield.

**What the design should add (unverified):**
- §4.5's scenario table recomputed for `pinned`.
- The meter list (§6.3) has "spills" but no meter for what `pinned` gives up. The missing meter is: wait time while another eligible placement had a free slot.

### S-5. `inference_placement.md::§2.1` (envelopes, rendered once) and `§5.3`: whether prompts stay cache-friendly is left unstated, and the spend arithmetic undercounts cached calls

**Defect, cache layout.** `complete_with_usage` takes only `system` and `user` strings. `_AnthropicBackend._build_system_blocks` puts one `cache_control: ephemeral` marker on the system block and nothing else. Only the system text can be cached, so a call hits the cache only if the system text is the same as last time.

The design's "rendered once to the role's envelope" says nothing about layout: the parts of the prompt that stay the same for an NPC (persona, long-term memories) belong in `system`, and the parts that change every call (percepts, time) belong in `user`.

**Failure scenario, cloud.** If the render puts anything that changes per call into `system`, every call writes the cache (priced above plain input, about 1.25× on Anthropic's published pricing, unverified) and no call ever reads it. That pays a premium for nothing.

**Failure scenario, local.** llama.cpp and Ollama reuse the KV cache of a prompt prefix per slot. With 20 NPCs taking turns on 2 slots, each call evicts the previous NPC's prefix, so every call processes its whole prompt again. The spike could not measure time to first token at 1,500 or 3,000 words (those cells ran at load 35–93), so this cost is unknown.

**An omission in the case for `pinned`.** Under `spill`, one NPC's calls move between placements and its cache goes cold on both. That is a real argument for O48, and the design doesn't make it.

**Defect, spend.** §5.3 computes spend as tokens × `price`, with one input price and one output price. At 043eab8f, `_AnthropicBackend._parse_response` and `_stream_response` fill in `LLMResponse` as follows:
- `input_tokens` is Anthropic's `usage.input_tokens`. Anthropic reports that count separately from cache reads and writes (the backend's own comment in `_log_cache_usage` says "three disjoint counts"). That breaks `LLMResponse`'s own CC12 contract, under which `input_tokens` is the total.
- `uncached_input_tokens = max(0, input_tokens − cached)` subtracts the cached count twice, so it reads too low.
- Cache-write tokens are logged and dropped from `LLMResponse`.

**Failure scenario, spend.** A 3,000-token prompt has a 2,500-token system part that was just written to the cache. `LLMResponse` reports `input_tokens=500`. The host prices 500 input tokens, while the true charge is about 500 + 1.25 × 2,500 = 3,625 token-equivalents: about **7× under**. A cache read is undercounted by about a third (true cost about 500 + 0.1 × 2,500 = 750). The session cap, which §5.1 makes a precondition of consent for `third_party`, can then be passed several times over without the host noticing.

**Fix (unverified).**
- The provenance record carries cache read and write tokens.
- `price` carries cache read and write rates.
- An OD-I item asks Maxim to report all three Anthropic counts in `LLMResponse`.
- A design line states the prompt layout rule: stable prefix in `system`, volatile text in `user`.

### S-6. `inference_placement.md::§2.2` (local models are loopback servers) and `§6.3`: a model on the same machine competes with the world server for compute and memory, and the design has no budget for that

**Defect.** The default placement is `loopback`, so the model runs on the machine that runs the world server. Three measured facts are relevant:
- The heat law already runs 1.4× slower than real time at 1.92×10⁶ cells (B5).
- A pinned frame is about 100 MB at 5×10⁶ cells, and `phase1/agents` pins one per NPC (B5).
- The spike's numbers became meaningless when the machine's 1-minute load average rose from about 7 to 35–93.

The spike machine has 24 GB of unified memory. A 7B model at Ollama's default quantisation, about 4–5 GB (unverified), plus 20 pinned frames at about 2 GB fills a large part of it.

**Failure scenario.** At the max profile with 20 NPCs and a 7B model on loopback, decoding and physics slow each other down. Turn time and time to first token both regress, and no meter attributes the loss to running both on one machine, because every listed meter is either per placement or per lane.

**Fix (unverified).** B5 rows for:
- turn time with the loopback model under load;
- time to first token with physics at the max profile;
- a memory budget for weights, KV cache and pinned frames together.

### S-7. `inference_placement.md::§3` ("Its cost") and `§6.3`: the hop is measured per call while the cost comes per chunk, and none of the "B5 rows" is in B5

**Defect 1: per chunk, not per call.** "One local hop per call: microseconds to a millisecond" is given as fact, though it is unmeasured. Once B-1 is resolved, the cost comes per chunk, not per call. Each chunk is:
1. framed as length-prefixed JSON in the gateway;
2. decoded in the host;
3. checked by the host's stream validation (`npcs_and_sem.md` §5.3: NFC and the refusal rules, per chunk and on the whole text).

At 16 concurrent cloud streams of about 50–100 tok/s (unverified), that is about 800–1,600 frames per second into the host. If the lanes are threads of one interpreter (`boundaries.md` §7.1), they share the GIL with the simulation lane.

**Defect 2: the rows are not in B5.** §3 says "the hop is measured as a B5 row", and §6.3 is titled "Meters (B5 rows)". `docs/standards_backlog.md` is not in the diff, and B5 has no new row, so the guard exists only in the design.

**Defect 3: gateway restarts are not costed.** One gateway serves every placement. Killing it ends every in-flight attempt as `transport_down`, which sets off a burst of retries at once. The time for a new gateway to start (a `spawn` with `-I` that imports `maxim.models.language`) is not measured.

**Fix (unverified).** Add to B5:
- chunk rate and host CPU per chunk, measured on the host lane with the simulation lane running;
- gateway time to start and restart count;
- gateway memory;
- cache hit ratio per placement;
- prefill tokens per call.

---

## NIT

### N-1. `inference_placement.md::§7` (the barrier): the 4 s figure assumes agents park one after another

I checked the arithmetic, and it is right as written: 20 × 200 × 1 ms = 4 s per wall second at 20×; 20 × 10 × 1 ms = 0.2 at 1×; and 0.2–0.8 locally. But multiplying by N treats the time each park spends on the network as summed. The 50–200 µs local figure is mostly host CPU for encoding and decoding, and that does add up across agents. Network wait does not have to: the barrier can send `step` to all 20 worker processes and then wait for all of them. Then the network part is about one round trip per tick: 200 × 1 ms ≈ 0.2 s per second at 20×.

The case against remote agents is weaker than stated. It still holds, because the levers it names remain true. Fix (unverified): say whether parks are serial, or quote both figures.

### N-2. `inference_placement.md::§7`: "the scaling cost we've measured" is derived, not measured

The cost table in `checklists.md` is marked **D** and has "contact and the Maxim body step unmeasured". The 100-NPC figure of about 2.5–2.9 s is scaled up from a 10-NPC basis. Fix: "derived".

---

## What I checked and found sound

- §3's comparison against time to first token, 0.32–1.40 s, matches the spike's three near-quiet cells. The 1.40 s is the 4-in-flight cell, where queueing dominates.
- §7's arithmetic is correct, with the assumption noted in N-1.
- §2.1's one render per role is sound for retries and spill within a role, apart from the cache layout point in S-5.
- The meters in §6.3 are named per placement: calls in flight, slot wait, time to first token and to the full reply, failures, abandoned slots, spend, spills. What is missing is listed in S-1 to S-7.
