# Fold table, round 1 (v1 at 04ab810 → v2)

The **claim** column is the author's statement of where each finding is folded, and it is not a status. A delta
reviewer reads the tree and sets the status (`fixed`, `deferred`, `rejected` or `open`; O25). Owner decisions made
for this fold, on 2026-11-21: O50 (no streaming until OD-A25), O51 (per-speaker consent), O52 (the OD-A24 pushback)
and O53 (one gateway per placement). In the claim column, "IP" is `inference_placement.md`.

**How the author checked the reviewers' central claims at Maxim 043eab8f** (`git show` / `git grep`):
- there is no stream callback in any backend;
- the `llm-routing.md` placement invariant exists;
- the "proxy wins" decision exists (`utils/http.py:830`, `:839-843`);
- the peer backend checks for cancellation at `:566`, `:937` and `:1093`;
- `PromptBudgeter(total_budget, response_reserve, token_counter, …)` is at `:73`;
- cache writes are only logged (`anthropic_backend.py:546-571`);
- the OpenAI streamed `stop_reason` defaults to `""` (`:559`);
- `detect_tiers` is at `lane_models.py:412`.

The author did not check:
- the SDKs' default retries (not installed here);
- httpx sending a loopback URL through a system proxy.

| Finding | Sev. | Claim |
|---|---|---|
| **Executor** | | |
| E-B1 no stream producer | B | O50; F1; IP §3.3 (`chunk` reserved), §6.3 (the cost, with numbers); OD-A25 |
| E-S1 cloud failures collapse to empty | S | F2 widened; IP §2.6 (`empty`, a stand-in); OD-I9 |
| E-S2 partial stream as success | S | F3; `stream=False` (O50); `truncated(stream_broken)` |
| E-S3 peer cancellation | S | F5; IP §2.5 (cancel per transport); §2.6 (`cancelled`, never `unreachable`) |
| E-S4 SDK retries | S | F4 (unverified noted); IP §2.5 (kill ceiling); OD-I9 |
| E-S5 retry policy misstated | S | IP §2.6 "a change from §1"; npcs §1 edited |
| E-S6 live reads; held replies across save | S | IP §4.2 (three modes, held text saved); npcs §4.4 and §4.8 edited |
| E-S7 stale text elsewhere | S | upstream draft, npcs §12.2 line deleted, OD-A14 (no router built), boundaries §8.4, architecture line |
| E-S8 router case overstated | S | IP §1.2 rewritten (`last_served_*`, injected drain); lesson 29 |
| E-S9 import allowlist | S | IP §3.2 (transitive set, no-effect test) |
| E-S10 unmapped BackendError kinds | S | IP §2.6 table (all seven) |
| E-N1 seed, top-p, top-k | N | F6 |
| E-N2 spike method; batching | N | IP §2.2 (native API, measured at §8) |
| E-N3 "imports maxim nowhere" | N | IP §3.1 rewritten |
| E-N4 §5.3 cite | N | removed |
| E-N5 peer key path | N | IP §5.4 |
| E-N6 `allow_local`, `is_loopback_url` | N | open: mechanism for the Phase 4 build step |
| E-N7 envelopes reported | N | IP §4.3 (envelopes refuse) |
| **Architecture** | | |
| A1 no package, layer or importer | B | IP §3.1; boundaries §8.1 row; npcs §6.6 sentence; §3.5 gates; per-user path via `maxim_overdrive.data` (IP §2.2) |
| A2 classification location | S | IP §2.6 (the gateway classifies, the lane decides, attribution) |
| A3 `empty` band-aid | S | IP §2.6 (narrow definition, marked stand-in until OD-I9) |
| A4 retry policy; ledger | S | IP §2.6; IP §4.3; boundaries §8.4 |
| A5 head-of-line | S | IP §2.4 (per-placement queues) |
| A6 envelope channel | S | IP §2.1; npcs §6.6 (`load`) |
| A7 router cut | S | OD-A14 (no router built); upstream draft |
| A8 who reads endpoints | S | IP §2.2 (three files), §5.4 |
| A9 gateway liveness | S | IP §3.3 (`ping`/`pong`), §3.4 |
| A10 allowlist | S | IP §3.2 |
| A11 "gateway" means two things | N | npcs §6.3 sentence; the fold tables are left as history |
| A12 `open(table)` content | N | IP §3.3 (transport settings only) |
| A13 cache question left to a reviewer | N | IP §4.2 |
| A14 where `spill` is enabled | N | IP §2.2 |
| A15 abandoned spend; status message | N | IP §5.5, §5.6 |
| **Wire integrity** | | |
| B1 outcomes unmapped | B | IP §2.6 table |
| S1 `thought_failed` reasons | S | IP §2.6 closed list; boundaries §6.1 points to it |
| S2 BackendError mapping | S | IP §2.6 |
| S3 manifest contradiction | S | IP §2.2 (files split), §4.3 |
| S4 envelope names and units | S | IP §2.1 (Maxim's names, max-tokens rule, digest identity) |
| S5 envelope channel | S | as A6 |
| S6 channel lifecycle | S | IP §3.3 rules, §3.4 |
| S7 endpoint location | S | as A8 |
| S8 merge and versions | S | IP §2.2 (replace whole, versioned, injected path) |
| S9 provenance bounds | S | IP §4.1 |
| S10 router cut; `thinking` | S | OD-A14; IP §2.1 (`thinking` in the envelope) |
| S11 guest refusal; status kind | S | IP §5.6; checklist |
| S12 "gateway" | S | as A11 |
| N1–N7 | N | N1 cite removed; N2 boundaries §8.4; N3 npcs §12.2; N4 open (vocabulary note in IP §2.2 `egress`); N5 IP §5.5; N6 IP §4.3; N7 world_model row 10 |
| **Trust boundary** | | |
| B1 system proxy | B | F9; IP §5.3 (proxied gateway is `third_party`); OD-I10 |
| B2 consent outlives session | B | O51; IP §5.1 (per speaker, taint through speech) |
| S1 egress is declared | S | IP §5.2 (owner_lan address ranges; loopback first-hop gap) |
| S2 endpoint holder | S | IP §2.2, §5.4 |
| S3 gates unregistered | S | IP §3.5; IP §3.3 rules |
| S4 allowlist | S | IP §3.2 |
| S5 HOME fallback; no-effect test | S | IP §3.2 |
| S6 cleartext LAN | S | IP §5.4 (`cleartext: true`, disclosed) |
| S7 gateway output | S | IP §3.2 (gateway log, never bundled) |
| S8 unbounded reported values | S | IP §4.1 |
| N1–N5 | N | N1 IP §3.2; N2 IP §5.4; N3 IP §2.2 id; N4 IP §5.4 and §2.6; N5 IP §5.5 (soft cap); gateway memory B5 |
| **Concurrency and lanes** | | |
| C1 no whole-call bound | B | O53; IP §2.5 (`call_ceiling_s` kill) |
| C2 pinned full; ceiling start | B | IP §2.5 (ceiling from enqueue); kills free slots |
| C3 hang criterion; blast radius | B | O53; IP §3.4 |
| C4 head-of-line | B | IP §2.4 |
| C5 lifecycle races | B | IP §3.3 rules |
| C6 no chunk producer | B | as E-B1 |
| C7 concurrent backend safety | S | deferred by the author to Phase 4's concurrency test (IP §8), which picks the instance model; reviewer to rule |
| C8 health feedback | S | IP §2.6 (pinned waits on load failures), §2.7 (probe; request outcomes don't cool) |
| C9 server capacity; killed spend; pool | S | IP §2.2 (`server`, real parallelism, at most 10 on `maxim_peer`); IP §5.5 |
| C10 I/O model | S | IP §3.3 (reader threads, bounded outboxes) |
| C11 shutdown and orphans | S | IP §3.4 |
| C12 shared slots across functions | S | open: meter only (IP §8); no reservation proposed |
| N1, N2 | N | N1 IP §2.2 (1 to 16); N2 moot under O50 |
| **Determinism and replay** | | |
| B1 failover after delivered speech | B | IP §2.6 (never retried once delivered; moot under O50) |
| S2 one entry per occurrence | S | IP §4.2 |
| S3 live never reads | S | IP §4.2; npcs §4.8 |
| S4 no read-through mode | S | IP §4.2 |
| S5 manifest; envelope source | S | IP §2.2, §4.3 |
| S6 pure counters | S | IP §2.1 |
| S7 a test that can't fail | S | IP §6.4 |
| S8 injected clock | S | IP §6.4 |
| S9 save, load and branches | S | IP §4.2 |
| N10–N12 | N | N10 IP §2.6 list; N11 IP §2.1 digest; N12 IP §4.3 per segment |
| **Performance** | | |
| B-1 streaming | B | as E-B1 |
| S-1 cancel per transport; wasted decode | S | IP §2.5; B5 abandoned tokens |
| S-2 `timeout_s` isn't a whole-call bound | S | IP §2.5 |
| S-3 server concurrency; context per slot | S | IP §2.2 (`server`, `context_per_slot`) |
| S-4 cost of `pinned` | S | IP §2.4 (cites the reviewer's number); B5 meter |
| S-5 prompt layout; spend undercount | S | F8; IP §4.1, §5.5; OD-I9. Prompt layout (stable text in `system`) is open: it is Maxim's render, so it goes with B1 |
| S-6 co-located model | S | B5 rows |
| S-7 per-chunk cost; rows missing from B5 | S | B5 rows added; chunk cost moot under O50 |
| N-1, N-2 | N | IP §7 (both figures; "derived") |
| **Bio-faithful** | | |
| BF-1 Maxim's placement rule | B | IP §1.2; O52; OD-A24; lesson 29 |
| BF-2 the role comes from hardware | B | IP §2.1 (declared function); OD-A14; upstream draft |
| BF-3 pinned follows load; fatigue | S | IP §2.6 (load failures wait); IP §6.2 (fatigue OPEN) |
| BF-4 profile changes within a life | S | IP §6.2 (OPEN; per-NPC meter) |
| BF-5 cut-off stream as ok | S | F3; IP §2.6 |
| BF-6 OD-I9 framing | S | OD-I9 reframed as a pushback |
| BF-7 OD-A23 sent to the wrong owner | S | OD-A23 reframed to B1's cancel clause |
| BF-8 transcript clause can't fail | S | IP §6.4 |
| BF-9 lesson 29 | S | rewritten |
| NIT-1 to NIT-3 | N | NIT-1 renamed to "function"; NIT-2 IP §4.1; NIT-3 IP §6.2 and §9 |
