**Verdict:** I found 1 BLOCKER, 10 SHOULD-FIX and 7 NITs. The §7 arithmetic and most file:line citations are correct. The design's central claim, that "the backends are what the lane needs", is false at 043eab8f: no backend can stream to its caller, the cloud backends turn almost every failure into an empty reply, and §1 gets the peer backend's cancellation wrong.

# Executor review: `docs/design/inference_placement.md` (diff 814dea9..04ab810)

All Maxim reads were done with `git show origin/main:<path>` at 043eab8f79ea.

## BLOCKER

**E-B1. No Maxim backend gives its caller a stream, so the gateway's `chunk` message has nothing to produce it in Phase 4.**
- **Where:** `inference_placement.md::§3` (the message kinds, `chunk(attempt_id, seq, text)`), `::§1` ("The backends are what the lane needs") and `::§8` (Phase 4: "Maxim's three backends in the gateway").
- **What the code does:**
  - `complete_with_usage(..., stream: bool = False) -> LLMResponse` takes no chunk callback, sink or iterator, in `backend_protocol.py:72-84` and in all three backends.
  - With `stream=True`, every backend collects the text internally and returns one `LLMResponse`: `anthropic_backend.py:473-480` (`text_parts`), `openai_backend.py:406-407` → `:547-559`, and `maxim_peer_backend.py::_stream_response` (`:987`).
  - I searched `src/maxim/models/language` for `on_chunk`, `callback`, `on_delta`, `stream_cb`, `token_callback` and `chunk_sink`. The only hit was Anthropic's `input_json_delta` event parsing.
- **Failure scenario:** in Phase 4, an NPC speaks to the player through `_OpenAIBackend` on loopback Ollama. The gateway can't send any `chunk` until the whole reply returns, roughly 1.3–2.2 s for a short prompt (spike, full-reply median). That breaks four things:
  - `npcs_and_sem.md` §4.5 item 3 ("Streaming the first token for P2 speech, so the gap closes on time-to-first-token").
  - Per-chunk speech validation (§5.2, `:581`).
  - Interruptible mid-stream speech (`:385`).
  - `cancelled(prefix)` carrying delivered speech (§6.6).
- §3's cost line compares the local hop with the spike's 0.32–1.40 s **TTFT**. The spike measured that by streaming Ollama's native API directly (`spikes/llm/measure.py:63-64`), not through any Maxim backend.
- This is contract: the closed message kinds and the TTFT budget depend on it, and §1's "three facts" leave it out.
- **Fix (unverified):** add it as a fourth fact and an upstream ask (a chunk sink on `complete_with_usage`, or similar), or name a transport that streams. Either way §3 and §8 have to change.

## SHOULD-FIX

**E-S1. The cloud backends collapse nearly every failure into `empty`, so most of §2.6's closed outcomes can't happen on two of the three transports.**
- **Where:** `::§1 fact 1`, `::§2.6`; `roadmap.md::OD-I9`.
- **Fact 1 is incomplete for Anthropic.** It says Anthropic returns empty only when the client can't be built. The code also returns `LLMResponse(content="")`:
  - on shutdown (`anthropic_backend.py:377`, `:404`);
  - after its retries are exhausted, for every exception (`:384-409`, ending "Anthropic call failed after %d attempt(s)", then `:409`);
  - when `_stream_response` finds no client (`:477`).
- **Consequence:** with Anthropic or OpenAI, `refused(auth|quota|policy)`, `timeout` and `context_overflow` can never be produced. Everything becomes `empty`.
- **Failure scenario:** a prompt overflows a `third_party` placement. Anthropic returns empty, the lane maps it to `empty` (a failure), and under §2.6 it is retried on the next placement. §2.1 says `context_overflow` "is never retried". The per-outcome cooldowns (§2.6) also collapse into one class.
- OD-I9's text repeats the omission.

**E-S2. `_OpenAIBackend` returns a partial stream as success.**
- **Where:** `::§1`, `::§2.6`.
- `llm_routing.md:686` (which the design cites) says `_OpenAIBackend._stream_response` "doesn't re-raise — it returns whatever text was collected so far … a silent partial-response path that the router's empty-content detection will not catch."
- **Failure scenario:** the default placement is `loopback` through `openai_compatible` (§2.2). Ollama is killed mid-reply. The gateway gets non-empty text and maps it to `ok`. The truncated reply is cached as a first-class `ok` entry, and a rerun reproduces the truncation as though it were the model's answer.
- None of the "three facts" covers this, and no outcome maps it.

**E-S3. The peer backend's cancellation claim is false, and a cancel shows up as `BackendDown`.**
- **Where:** `::§1 fact 3` ("checks for cancellation only before it makes the call (`:555-566`)"), `::§2.5`, `::§2.6`; `roadmap.md::OD-A23`.
- `_MaximPeerBackend` checks `utils.cancellation.is_cancelled()` at three points:
  - before the call (`:566`);
  - **after a non-streaming call returns** (`:929-941`);
  - **between SSE chunks while streaming** (`:1086-1097`).
- The flag is a per-context `threading.Event` in a `ContextVar` (`utils/cancellation.py:19`, `:90`), so a gateway thread can set it per call. A streaming peer call can therefore end mid-call and free its slot, which contradicts §2.5's "the slot stays held until the call returns" for this transport.
- All three checkpoints raise `BackendDown` (`fix_hint="Request cancelled by caller …"`). Read literally, §2.6's mapping turns a host-initiated cancel into `transport_down` and puts a healthy placement into cooldown.
- `plans/reviews/maxim_side.md:35` already records Maxim's advice to "ride on `utils/cancellation`". OD-A23 should be checked against that before it is sent.

**E-S4. "Retries configurable to zero" ignores the SDK clients' own retries.**
- **Where:** `::§1` (Anthropic, `:172-190`), `::§1 fact 2`, `OD-I9`.
- Neither backend passes `max_retries` to the SDK constructor: `Anthropic(api_key=..., timeout=...)` at `anthropic_backend.py:237`, and `client_kwargs` at `openai_backend.py:276-280` → `OpenAI(**client_kwargs)` at `:305`.
- Both SDKs retry inside the client by default (2 retries, from memory; **unverified**: the SDKs are optional extras, not in `constraints/py3.12.txt`, and not installed in this worktree).
- If that holds, setting `max_retries: 0` still gives up to three HTTP attempts per backend attempt, so "one call, one outcome" fails for Anthropic too, not only OpenAI's gateway retries. OD-I9 should include it.

**E-S5. "Retries follow the existing policy" misstates the existing policy.**
- **Where:** `::§2.6`.
- The existing text retries **timeouts** only: "Under the dilate policy a timeout retries" (`npcs_and_sem.md` §1, `:96`).
- Other failures are not retried: "Machine-decided failures (an LLM error, refusal, out-of-memory) are recorded in the cache as first-class responses" (§4.4, `:415`).
- §2.6 re-dispatches any failed attempt and lets selection fail over to another placement. That is a new policy, and it changes which replies become cache entries, so it should be stated as new rather than cited as existing.

**E-S6. The §4.2 question: no existing text says live play reads the cache, but "never reads it" leaves a save/load gap.**
- **Where:** `::§4.2`.
- What the text says today:
  - §4.8 covers rerun reads and loud rerun misses, and replay never opens the cache (`:526`).
  - §4.4 and §6.6 only *write* machine-decided failures to it.
  - The lifecycle (`:815`) has the call "run in the host's thinking lane" with no cache lookup.
  - `boundaries.md` §7.1's "with the response cache" is ambiguous.
- So I found no text saying live play reads the cache, and none saying it never does. The design's claim is consistent with the existing text, but it is new text, not a confirmation.
- **The gap:** "Early replies are held by the host" until the landing tick (§4.4, `:417`). The host-owned header holds ids, counters, landing ticks, cancel status and the delivered prefix, but **not the held reply's text** (`:808-813`).
- **Failure scenario:** a save is taken between a reply arriving and its landing tick, then loaded. If live play never reads the cache, the host must dispatch again. A real model then gives a different answer, which breaks DET-S5's resume equivalence. The [now] test uses the deterministic double, so it can't go red.
- The contract should say where a held reply lives across a save.

**E-S7. Text elsewhere still contradicts the edits.**
- **Where:** `inference_placement.md::§10`.
- `docs/maxim_upstream/embeddable_agent_DRAFT.md:87` still says "supplying the bound model's `n_ctx` and tokenizer (`token_counter`) to the `PromptBudgeter`". This is the draft that goes to Maxim (O35), and §10 doesn't list it.
- `npcs_and_sem.md` §12.2 (`:1201`): "Any shared router serialises inference; the host never shares one across NPCs". That implies routers on the host's path, against O46.
- `checklists.md` (edited): "Maxim's router is never built on this path". `npcs_and_sem.md` §6.1 and OD-A14 still produce the request "at the `LLMRouter._complete_text` cut" in the worker, which implies a worker-side router object. Either the cut moves in B1 or "never built" is wrong; the docs should pick one.
- `boundaries.md:664`: a ledger record pins "the model profile", which is now per reply.
- `architecture.md` (edited): "a late thought dilates the world or holds the floor" leaves out O16's interim co-op policy (silent late landing) and `latency_policy: abandon`.
- I found no remaining text that puts the model id in the cache key (`grep -rn "model id|weights digest|weights or quant"` over `docs/`).

**E-S8. §1's case against the router overstates two facts.**
- **Where:** `::§1`.
- **"Fails over silently … without anything showing it."** The router records which provider served each successful dispatch: `_dispatch_served` and `call_accounting.ServedCall` (provider, model, backend kind, endpoint; `router.py:1171-1182`, `call_accounting.py:39-54`), exposed as `last_served_*` (`router.py:287-313`).
  - What is true: after earlier providers failed, a successful dispatch clears the attempt buffer and suppresses the aggregated WARN (`:1344-1349`).
  - The accurate claim is that the caller didn't choose the model and isn't told unless it asks.
- **"Reads … drain state in `~/.maxim/util/drained_nodes`."** The router reads drain state only through an injected `drain_constraint` callable, which defaults to `None` (`router.py:178`, `:195`, `:603`). The file is read by `peer/drain_routing.py:132-176`. Citing `drain_state.py:10` and `:145` as router state is indirect.
- O46 doesn't depend on either point, but lesson 29 repeats the framing.

**E-S9. The gateway's import allowlist can't be met as written.**
- **Where:** `::§3` ("Its imports are an allowlist: `maxim.models.language` and the backend modules its transports name").
- Importing any backend runs `maxim/models/language/__init__.py`, which imports `LLMRouter` (`:19`).
- `router.py` imports `llama_backend`, `cost_tracker`, `cloud_audit` and `cloud_redaction` (`:15-43`). `cloud_redaction` is the module under the OD-I5 advisory.
- The peer backend lazily imports `maxim.agents.llm_worker` on every call (`:583`), plus `maxim.runtime.llm_server` (`:253`) and `maxim.runtime.llm_call_registry` (`:115`).
- `_OpenAIBackend` imports `mesh_trace` per call (`:373`).
- **Failure scenario:** the allowlist test from §3, written as stated, goes red on the first `dispatch`, or gets widened at build time without anyone deciding to widen it.

**E-S10. Two `BackendError` subtypes have no outcome in the closed vocabulary.**
- **Where:** `::§2.6` ("`BackendError` subtypes … each map to exactly one of these").
- `types.py:146-270` defines `BackendOverloaded`, `Down`, `Timeout`, `AuthFailed`, `ModelMissing`, `InferenceBroken` and `ContextOverflow`.
- `BackendModelMissing` (the model isn't loaded) and `BackendInferenceBroken` (the server is alive but inference fails; Maxim backs off 15 s on it) have no obvious target among the seven outcomes.
- The set is closed and golden-fixtured, so the mapping is contract, and the design should state it.

## NIT

- **E-N1. `::§1 fact 3`, `npcs_and_sem.md` §4.8.** The canonical request keeps top-p, top-k and seed, but no `complete_with_usage` takes any of them (`backend_protocol.py:72-84`). The peer backend accepts `**_kwargs` (`:550`), so a seed passed to it is dropped with no error. Fact 3 names only the seed.
- **E-N2. `::§2.2`.**
  - "The spike measured exactly this (Ollama at 127.0.0.1)": the spike used Ollama's native `/api/generate` (`measure.py:64`), not an OpenAI-compatible endpoint, and no Maxim code.
  - "A server batches the requests in flight" contradicts the spike's own text: "Ollama's default server queues requests" (`llm_spike.md:40`).
- **E-N3. `::§3`, reason 1.** "The host imports `maxim` nowhere" drops §6.6's qualifier "Once the adapter is split" (`npcs_and_sem.md:790-791`). Today the host does import it: `simcore/adapters/sem/bridge.py:29`, `:34`.
- **E-N4. `::§3`.** It cites `npcs_and_sem.md` §5.3 for stream validation. Per-chunk validation is in §5.2 (`:581`) and §6.6 (`:882`); §5.3 is syllable stamps.
- **E-N5. `::§5.2`.** `resolved_entry_key` applies to the Anthropic and OpenAI backends only. `_MaximPeerBackend._get_api_key` takes a literal `api_key` on the entry first, then env (`:791-802`). The approach still works, but the citation is broader than the code.
- **E-N6. `::§5.1`, `::§2.2`.** `openai_compatible` reaching loopback or `owner_lan` needs `allow_local_endpoints: true` on the entry. Otherwise the address policy is `"public"` and refuses non-public addresses (`openai_backend.py:286-288`, `utils/net.py:102-106`). Maxim also has `is_loopback_url` (`net.py:74`), but it accepts `localhost`, which §5.1's literal-IP rule refuses.
- **E-N7. `::§4.3`, `boundaries.md` §6.3 edit.**
  - Envelopes are "reported, never refused" on a rerun, but the key carries the envelope version and the prompt is rendered to it. A changed envelope therefore guarantees a loud miss partway through the run instead of a refusal at the start.
  - The boundaries edit leaves out the per-placement provenance summary that §4.3 lists.

## What I checked

| Claim / citation | Result |
|---|---|
| `router.py:192` `_inference_lock` ("llama-cpp not thread-safe"); `:1094`, `:1225` acquires | true |
| `router.py:77` env read (`MAXIM_INFERENCE_LOCK_TIMEOUT_S`); `:201` `CostTracker` | true |
| `router.py:958` `_complete_text` | true |
| `llm_routing.md` "the concurrency wall" (`:156`); `_try_provider` treats empty content as failure (`:146-148`) | true; the "silently" framing is E-S8 |
| `worker_pool.py:72` `Origin` LOCAL/CLOUD/PEER | true (it is in worker_pool, not router.py) |
| `mesh/__init__.py` networked modules deleted 2026-04-12 | true |
| multi-peer dispatch plan revived 2026-10-18, not built | true ("REVIVED 2026-10-18", still a deferred shell) |
| `peer/drain_state.py:10`, `:145` path | true; the router reads it only via injection (E-S8) |
| `peer/config.py` `peer.yml`; `mesh_config.py:316` `mesh.yml`; shared cluster key | true; a `LeaderProxy` exists (`admin_core.py`) |
| `types.py:25-53` `LLMResponse` fields | true (it also has `latency_ms`, `tool_calls` and cached-token fields) |
| `anthropic_backend.py:172-190` retries; `:165-170` timeout; `:145-163` key | true; SDK retries are E-S4 |
| `anthropic_backend.py:223-241`, `:333-335` empty on no client | true; incomplete (E-S1) |
| `anthropic_backend.py:318-329`, `maxim_peer_backend.py:537-549` signatures: no deadline, no seed | true |
| `maxim_peer_backend.py:537-552` "ONE HTTP call", typed errors | true |
| `maxim_peer_backend.py:555-566` cancellation "only before" | **false** (E-S3) |
| `openai_backend.py:358-360`, `:505` empty; `:391` `max_gateway_retries = 4`; `:396-398` ~50 s; `:288` address policy | true |
| `llm_path_fast_failover.md:771` typed-errors lesson | true, verbatim |
| `overdrive_refactor_candidates.md` B3 "which the host … schedules" | true (`:342-344`) |
| `http_deadline_1715.md` exists | true |
| Streaming hooks in the backends | none (E-B1) |
| `npcs_and_sem.md` §6.6 "maxim itself only in workers" | true, with the qualifier "once the adapter is split" (E-N3) |
| §6.6 cost line, 20 × 200 × 50–200 µs = 0.2–0.8 s | true (`:792-793`) |
| §7: 20 × 200 × 1 ms = 4 s; at 1× (10 ticks/s) 20 × 10 × 1 ms = 0.2 s | arithmetic correct; serial round trips assumed, as in §6.6 |
| `checklists.md` cost table, 100 stationary NPCs ~2.5–2.9 s per s | true (`:463`, marked **D** = measured in research or reviews) |
| spike TTFT 0.32 s (1 in flight) to 1.40 s (4 in flight) | true; method caveat in E-N2 |
| Old §4.8 / §6.1 / boundaries §6.3 text quoted in §2.1, §4.2, §4.3 | true at 814dea9 |
| §4.2: does existing text say live play never reads the cache? | not stated either way; the gap is E-S6 |
| `npcs_and_sem.md` §1 "Where wall time remains", §4.5, §4.6 (`LLMEnergyTracker`), §6.2 router sentence, O13, O18, O29, OD-I5 | present and as described |
| `boundaries.md` §5.3 cache row, §6.3 manifest, §7.1 lane, §7.3 dial test (`:575`) | present; edits consistent apart from E-N7 |
| Remaining "model id in key", "bound model's n_ctx", "router built" across `docs/` | stale in the Maxim draft, `npcs` §12.2, and a checklists vs OD-A14 tension (E-S7) |
| Word budgets: new doc 4,204 words; `npcs_and_sem` 23,788 → 23,786; boundaries 13,983 → 13,982; architecture 2,829 → 2,828 | within the rules (existing docs did not grow) |
| BackendError subtypes against the closed outcomes | two unmapped (E-S10) |
