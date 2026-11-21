**Verdict:** 16 of my 18 round-1 findings are fixed, one is deferred and one is open (E-N7). The fold adds no BLOCKER. It adds 6 SHOULD-FIX (5 contract, 1 mechanism) and 6 NITs. Most of v2's new citations and every number I checked hold at 043eab8f. Two of v2's "verified" facts are wrong or out of date: F3, and the router property name in §1.2.

**A correction to my own round-1 report comes first.** E-S8 said the router exposes `last_served_*` at `router.py:287-313`. No property of that name exists at 043eab8f. Lines 285-316 hold `last_used_model`, `last_used_provider`, `last_used_backend_class` and `last_used_endpoint`, and the served record is `_dispatch_served` (`:185`, `:1176`). v2 §1.2 and lesson 29 copied my wrong name (new NIT D-N1).

# Delta review, Executor lens: `inference_placement.md` v2 (274f297..caca211)

All Maxim reads used `git show origin/main:<path>` at 043eab8f79ea.

## 1. Status of my round-1 findings

| Finding | Status | Evidence at caca211 |
|---|---|---|
| E-B1 no stream producer | **fixed** | O50 (§0); F1 (cites true at `anthropic_backend.py:473-480`, `openai_backend.py:547-559`, `maxim_peer_backend.py:987`); §3.3 reserves `chunk`; §6.3 states the cost with the spike's numbers; OD-A25 in `roadmap.md`. The promised Known gap entry is missing (D-S5). |
| E-S1 cloud failures collapse to empty | **fixed** | F2 now lists shutdown (`:377`, `:404`) and exhausted retries (`:384-409`). §2.6 marks `failed(empty)` as a stand-in until OD-I9, and OD-I9's row was rewritten to match. |
| E-S2 partial stream as success | **fixed** (moot under O50) | `stream=False` (O50); `truncated(stream_broken)` row. The fact behind it, F3, is out of date, and the row misfires without streaming (D-S2). |
| E-S3 peer cancellation | **fixed** | F5 cites `:566`, `:937` and `:1093` (verified: `BackendDown` with "before / after peer call returned / during stream"). §2.5 gives cancel semantics per transport, and §2.6 maps a cancel to `cancelled`, never `unreachable`. OD-A23 is redirected to B1's cancel clause. |
| E-S4 SDK retries | **fixed** | F4 marks the SDK retries *unverified*, OD-I9 includes them, and §2.5's kill ceiling bounds them. Maxim's own code now supports the claim: `openai_backend.py:450` says "the SDK's own max_retries has already re-tried the dial". F4 could cite that line (NIT D-N3). |
| E-S5 retry policy misstated | **fixed** | §2.6 says "This is a change from `npcs_and_sem.md` §1's 'a timeout retries'", and `npcs_and_sem.md` §1 (`:96`) was edited. |
| E-S6 live reads; held reply across a save | **fixed** | §4.2 gives three modes with a poisoned-entry test, and the held reply's text is saved in the header. `npcs_and_sem.md` §4.4 (`:417`) and §4.8 (`:520`) were edited. |
| E-S7 stale text elsewhere | **fixed** | Upstream draft `:84-89`; the `npcs_and_sem.md` §12.2 line is deleted; OD-A14; `boundaries.md` §8.4 `:665`; the `architecture.md` line. One leftover, `boundaries.md` §7.1 `:512` "a host-owned gateway" (singular, against O53), is NIT D-N5. |
| E-S8 router case overstated | **fixed** | §1.2 now says the caller "didn't choose … isn't told unless it asks" and calls the drain constraint "injected". The property name is wrong (D-N1, my error). |
| E-S9 import allowlist | **fixed** | §3.2 makes the allowlist the transitive module set, recorded at the build step, plus a no-effect test. Whether call-time imports (peer `llm_worker`, OpenAI `mesh_trace` at `:373`) are captured depends on the test making a call. That is mechanism, for the build step. |
| E-S10 unmapped `BackendError` kinds | **fixed** | §2.6's table has a row for each of the seven subclasses. |
| E-N1 seed, top-p, top-k | **fixed** | F6. |
| E-N2 spike method; batching | **fixed** | §2.2: "The spike measured Ollama's native API, so this path is measured at §8"; "batches" no longer appears. |
| E-N3 "imports maxim nowhere" | **fixed** | §3.1, and `npcs_and_sem.md` §6.6 `:791` now says "workers and inference gateways". |
| E-N4 §5.3 citation | **fixed** | removed. |
| E-N5 peer key path | **fixed** | §5.4 cites `maxim_peer_backend.py:791-802`, verified: a literal `api_key` on the entry comes before the environment. |
| E-N6 `allow_local_endpoints`, `is_loopback_url` | **deferred** | Mechanism. Trigger: Phase 4's fake-server test of `openai_compatible` against loopback and `owner_lan` (§8). |
| E-N7 envelopes only reported | **open** | IP §4.3 now refuses envelopes, but `boundaries.md` §6.3 `:456-457` still reads "the placement table's digest and role envelopes (reported, never refused: `inference_placement.md` §4.3)". §10 claims §6.3 was changed; the diff to `boundaries.md` touches only §5.3, §6.1, §8.1 and §8.4. See D-S1. |

## 2. New findings

### SHOULD-FIX

**D-S1. `boundaries.md::§6.3` (the rerun manifest) contradicts IP §4.3, and IP §10 claims an edit that wasn't made.** **Contract.**
- `boundaries.md:456-457` says role envelopes are "reported, never refused", citing §4.3.
- IP §4.3 says "`functions.yaml`'s digest and the envelopes refuse on mismatch".
- It also keeps "role", which v2 renamed to "function".
- **Failure scenario:** the rerun-manifest checker is built from `boundaries.md` §6.3, the registry document. A rerun with a changed envelope then starts and fails partway through on a cache miss, instead of being refused up front. That is the outcome E-N7 named.

**D-S2. The `truncated(stream_broken)` row rests on a fact that is out of date, and it misfires on calls that don't stream.** **Contract** (the closed outcome table is golden-fixtured).
- **F3 is wrong at 043eab8f.** `_OpenAIBackend._stream_response` (`:547-627`) has no try/except around `for chunk in stream`. A mid-stream exception propagates into `complete_with_usage`'s retry loop (`:442`), which either retries the whole call or returns `LLMResponse(content="")` (`:505`).
  - F3's source, `llm_routing.md:686`, cites old line numbers (`:421-478`) and describes code that has since changed.
  - Partial text with an empty `stop_reason` can now happen only when a stream ends without a finish chunk and without an error.
- **The row misfires under O50.** With `stream=False`, the peer backend's non-streamed path sets `stop_reason = str(first.get("finish_reason") or "")` (`maxim_peer_backend.py:958`).
  - **Failure scenario:** a healthy OpenAI-compatible server that omits `finish_reason` sends a complete reply. The reply is classified `truncated(stream_broken)` and attributed to the placement, so every reply starts a cooldown and the placement flaps.
  - The cloud parsers do the opposite: `str(getattr(choice, "finish_reason", ""))` (`openai_backend.py:542`) and `str(getattr(resp, "stop_reason", ""))` (`anthropic_backend.py:467`) turn a `None` into the non-empty string `"None"`, which classifies as `ok`.
- "Empty `stop_reason`" therefore means different things on different transports, so the table's producing column isn't a transport-independent rule.

**D-S3. `failed(refused)` has no producer, and the `ok` row absorbs real refusals.** **Contract.**
- None of the seven `BackendError` subclasses is a refusal (F7).
- The cloud backends collapse exceptions into empty content (F2). A provider refusal therefore reaches the gateway only as a `stop_reason`: Anthropic's `refusal`, or OpenAI's `content_filter`. Both values are from my knowledge of the provider APIs; I did not check them in this tree.
- §2.6 maps "content with a non-empty `stop_reason` other than a length stop, or empty content with a non-empty `stop_reason` (the model chose silence)" to `ok`.
- **Failure scenario:** an Anthropic safety refusal lands as `complete("")` or `complete(<refusal text>)`. It is cached as an `ok` entry, and `thought_failed(reason=refused)` never fires.
- The producing column for `refused` needs named `stop_reason` values per transport, or the reason should be marked unreachable until OD-I9.

**D-S4. "A prompt rendered once fits every placement" holds only if the envelope's counter never undercounts a placement's tokenizer.** **Contract.**
- §2.1's fit rule is `context_per_slot ≥ total_budget`. `PromptBudgeter` keeps `total_budget − response_reserve − template_overhead` for the prompt (`prompt_budgeter.py:96`), so the arithmetic is consistent.
- But the count comes from the envelope's single pure `token_counter`, while each placement's model has its own tokenizer.
- **Failure scenario:** `total_budget` is 2,048 and a placement has `-c 8192 -np 4`, so 2,048 tokens per slot. The counter undercounts that model's tokenizer by about 10%. The server overflows, and the result is `failed(context_overflow)`: request-attributed, never retried, so the thought fails even though another placement would fit it.
- The contract needs either a counter that is an upper bound for every placement's tokenizer in the function, or a margin per placement. That is a rule for the loader.

**D-S5. Four "Known gaps" are declared but recorded in no Known-gaps list.** **Contract** (CLAUDE.md: gaps are recorded "with numbers, instead of hiding them").
- The four:
  - O50 and §6.3 ("a Known gap with its number");
  - §5.2, loopback promises only the first hop;
  - §5.4, `owner_lan` cleartext;
  - §5.5, the spend cap's Anthropic undercount.
- `grep` of `architecture.md` (Known gaps, `:53`) and of `npcs_and_sem.md` §12.2 finds none of them.
- **Failure scenario:** the gaps exist only inside a design document. Nothing that tracks Known gaps lists them, so they can be closed or forgotten without anyone deciding to.
- Related NIT: `npcs_and_sem.md` §4.5 lever 3 (`:464`, "Streaming the first token for P2 speech") still reads as an available lever. IP §6.3 says it is unavailable until OD-A25.

**D-S6. OD-I10's ask doesn't cite Maxim's existing no-proxy mode, and §5.2's `owner_lan` address rule has no connect-time enforcement over `https`.** **Contract** (the OD-I10 ask text) **and mechanism** (the address check). Two separate defects.
- **(a) OD-I10 skips an existing mechanism.** Maxim already has the mode the ask requests:
  - `HTTPEndpoint.strict_address_check` (`utils/http.py:228`, `:522`);
  - `_checked_client(strict=…)`, which builds a client with `mounts=None` (`:875-881`);
  - `_EXTERNAL_PUBLIC_ENDPOINT`, "never through a proxy (#824)" (`:928-931`);
  - all clients go strict under the offline latch (`:875`).
  §9 lists "proxy" among its search terms but cites none of these. Under CLAUDE.md's "Search Maxim before proposing", the ask should be to expose the existing strict mode per backend, not to add a new mechanism.
- **(b) The `owner_lan` rule has no connect-time check over `https`.** `base_url_address_policy` returns `"any"` for `https://` with `allow_local` (`utils/net.py:94-106`). `address_checked_client` then returns `None` (`http.py:916-917`), so the SDK dials with no address check.
  - The gateway can enforce "private, link-local or CGNAT" only by resolving first, which is the separate lookup that `net.py:95-97` says DNS rebinding defeated.
  - **Failure scenario:** an `https://` `owner_lan` name resolves to a private address when the gateway checks it and to a rented cloud host when the SDK dials. That breaks §5.2's promise that "a rented cloud machine can't be labelled as the player's own".
  - This part is mechanism, deferred to Phase 4's transport step, with the promise kept as contract.

### NIT

- **D-N1.** `inference_placement.md::§1.2` and `lessons_maxim_in_games.md` §29 say `last_served_*`; the real properties are `last_used_*` (`router.py:285-316`). This was my round-1 error. It matters because lesson 29 is the evidence base for the OD-A24 pushback. **Contract** (upstream evidence).
- **D-N2.** `::F8` cites the streaming parser (`anthropic_backend.py:546-571`). Under O50 the gateway uses `_parse_response`, where the same defect sits at `:416-422`: `cache_creation` is computed and logged but left out of `LLMResponse`, under a comment that says it should "also count … as uncached". **Mechanism.**
- **D-N3.** F4's "SDKs retry by default (*unverified*)" can cite Maxim's own comment at `openai_backend.py:450` as supporting evidence. **Mechanism.**
- **D-N4.** `::F2` says a missing client returns empty, citing `:223-241`. A missing `anthropic` package **raises** through `require_optional_dependency` (`:230`, outside the retry try-block); only a missing key or a failed client init returns `None`. §2.6's closed table has no row for a non-`BackendError` exception. Today that ends as a gateway crash, then restarts, then down-for-session, which is acceptable, but the table should say so. **Contract.**
- **D-N5.** `boundaries.md::§7.1` (`:512`) says "a host-owned gateway" (singular, against O53) and still says the lane executes "with the response cache", which reads as if live play reads it, against §4.2. **Contract wording.**
- **D-N6.** `::§4.1` says only `_OpenAIBackend` echoes the model. `_AnthropicBackend._parse_response` echoes it too (`model=model`, `:464`), and both report `provider` as the config key. On both cloud transports, then, §5.2's "provenance can attest [the provider] only where the transport reports it" attests nothing. The peer backend's reported model is real only after `warmup()` (`maxim_peer_backend.py:967-979`). Separately, the checklist's "no `X-Maxim-*` ids" is stricter than §3.2: `_OpenAIBackend` always sends a random `X-Maxim-Request-Id` (`openai_backend.py:381-383`), so a header test written from the checklist goes red on that transport. **Mechanism.**

## 3. What I checked

| Claim or citation (v2) | Result |
|---|---|
| F1 streaming citations | true |
| F2 `anthropic_backend.py:377`, `:384-409`, `:334`; `openai_backend.py:360`, `:505` | true; the missing-package path raises (D-N4) |
| F3 `llm_routing.md:686`; `openai_backend.py:559` | `:559` (`stop_reason = ""`) true; the partial-on-exception claim is **out of date** (D-S2) |
| F4 `max_retries` 2 (`:175`), `capacity_max_retries` 6 (`:185`, "≈ ~90s"), `max_gateway_retries = 4` (`:391`), `Anthropic(api_key, timeout)` `:237`, `OpenAI(**client_kwargs)` `:276-305` | true |
| F5 `:566`, `:937`, `:1093`; per-context Event (`utils/cancellation.py:101`) | true. Under `stream=False` only the before-call and after-return checks run, so a peer cancel frees nothing early. §2.5 is consistent, but the build step should know it saves only the parse. |
| F6 `backend_protocol.py:72-84` | true |
| F8 | true; cites the stream path only (D-N2) |
| F9 `http.py:827-860`, `:839-843`; "the proxy wins" `:830` | true; the existing strict mode is not cited (D-S6) |
| `prompt_budgeter.py:73` signature; `prompt_budget()` `:96` | true (`builder_gate` is a required keyword, covered by "…") |
| `lane_models.py:412` `detect_tiers`; `token_counter.py:38` `_LazyTokenCounter`; `types.py:302` `resolved_entry_key` | true |
| `http.py:67` pool of 10 | true |
| `llm-routing.md:73` placement invariant, quoted | true, verbatim |
| `llm_path_fast_failover.md:43`, `:769`, `:771` | true |
| `hybrid_arbitration.md:97-98` | true |
| `router.py:77`, `:192`, `:201`, `:958`, `:998`; package `__init__` imports `LLMRouter` (`:19`); router imports `llama_backend`, `cost_tracker`, `cloud_audit`, `cloud_redaction` (`:15-27`) | true |
| `router.py` `last_served_*` | **false**: the properties are `last_used_*` (D-N1) |
| §2.4 1.03× vs 1.34× | matches `reviews/inference_placement/performance.md:89-90` |
| §6.3 1.29 s, 0.32 s, 1.46 s; O11a 600–700 ms and about 1 s | match `llm_spike.md:28-29`, `:37` |
| §7 0.2–0.8 s; 4 s and 0.2 s at 1 ms; 0.3–1.4 s; 2.5–2.9 s (`checklists.md:472`, **D**) | arithmetic correct; sources match |
| Edits to other documents | `npcs_and_sem.md` §1, §4.1, §4.4, §4.8, §6.1, §6.6, §12.2 consistent, apart from lever 3 (D-S5). `boundaries.md` §6.3 not edited (D-S1), §7.1 stale (D-N5). Upstream draft, OD-A14, OD-A23–A25, OD-I9, OD-I10, B5, `world_model.md` row 10, `foundations_plan.md` ids and lesson 29 consistent, apart from D-N1 |
| Word budgets (`wc -w`) | IP 5,988 (≤ 6,000); `npcs_and_sem.md` 23,786 → 23,777; `boundaries.md` 13,982 → 13,982; `architecture.md` 2,828 → 2,827; `foundations_plan.md` 2,499 → 2,500 (exactly at the limit) |

Mechanism findings that should go to the `phase1/agents` or Phase 4 checklists: D-S6(b), D-N2, D-N3, D-N6, E-N6, and the capture of call-time imports in E-S9. Contract findings that still need a fold: D-S1, D-S2, D-S3, D-S4, D-S5, D-S6(a), D-N1, D-N4 and D-N5.
