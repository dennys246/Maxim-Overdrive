# Fold table, delta round (v2 at caca211 → v3)

**What this table is.** The claim column is the author's: where each finding was folded. It is not a status. The
round-1 statuses the delta readers set stand as they wrote them in `delta_*.md`. A short delta check sets the statuses
below (O25). The paper rounds stop here (CLAUDE.md, "Review finds; it doesn't design"; owner, 2026-11-21).

**Owner rulings for this fold** (2026-11-21):
- the stop rule;
- splitting the design into IP (`inference_placement.md`, the lane) and IG (`inference_gateway.md`);
- load never moves a pinned function;
- taint covers every guest-supplied string;
- O54: either the speaker or the save's owner may purge; only the speaker may release;
- cache pairing covers only the shared prefix.

**The author verified:**
- `NO_PROXY=*` makes `urllib.request.getproxies()` return `{'no': '*'}` and httpx 0.28.1's `get_environment_proxies()`
  return `{}`, with `env -i` (IG §2);
- the rest of the cited lines, read at 043eab8f.

**Mechanism findings** go to `checklists.md`, "Deferred from the delta round", and each keeps the trigger its reader
named.

| Finding | Sev. | Claim |
|---|---|---|
| **Concurrency** | | |
| D1 kill attribution; two "down" rules | S | IP §2.5: the trigger is `call_timeout` (load), the rest are host collateral. IG §4: only failed starts count. |
| D2 cooldown vs pinned | S | IP §2.3 and §2.7: a load delay leaves the placement eligible. |
| D3 "finished" undefined | S | IG §3 rules: finished means one `reply` or a dead gateway; the host cancels at the liveness ceiling. |
| D4 `call_ceiling_s` unbounded | S | IP §2.2: refused unless it is below the liveness ceiling. |
| D5 group `max_in_flight` | N | IP §2.2: the `servers` entry owns it, and members declare none. |
| D6 orphaned server work | S (mech.) | checklist, deferred to Phase 4. |
| D7 branch cache as-of point | S | IP §4.2: the copy is as of the save point. |
| D8 probe wedge | S (mech.) | IP §2.7 (the probe is re-issued); checklist. |
| D9 start ceiling | S (mech.) | IG §4 (`start_ceiling_s`); checklist. |
| D10 unnamed tunables | N | IG §4: the `health` block in `placements.yaml`, with its relations. |
| D11 outbox overflow | N (mech.) | IG §3 (a full outbox counts as hung); checklist. |
| D12 gateway sleeps | N (mech.) | checklist, Phase 4. |
| **Determinism and replay** | | |
| B1 cancel in flight, rerun misses | B | IP §4.2: the read point is the landing tick; a request ended before it is never looked up; the index is assigned at creation. |
| B2 branch copy collides | B | IP §4.2: the copy is as of the save point. |
| S3 pairing needs a fourth mode | S | IP §4.2: pairing covers only the shared prefix, and an arm ends at its first miss (owner). |
| N1 dial-test schedule | N (mech.) | IP §6.4 (recoverable schedule, world digests, waits per reply); checklist. |
| N2 home of the taint | N | IG §6: saved with the save, versioned; logged consent and purges. |
| N3 stale text | N | npcs §4.4 (final outcome); boundaries §7.4 and §5.3's thought-budget row. |
| **Performance** | | |
| D-1 §4.5 lever 3 | S | npcs §4.5 (unavailable until OD-A25); the spike note. |
| D-2 peer cancel under `stream=False` | S | F5; IP §2.5. |
| D-3 pinned under load | S | IP §2.7 (load delay); kills don't count (IG §4). |
| D-4 group cap and order | S | IP §2.2 `servers`; §2.4 (one queue per group). |
| D-5 cost of a kill | S (mech.) | the B5 row (collateral per kill); checklist. |
| D-6 transport timeout | N | IG §3: `open` carries it. Its relation to the ceiling is mechanism (checklist). |
| D-7 B5 owners; instance model | N | B5 row split between `phase1/agents` and Phase 4; IP §8: more than one process per placement goes to the owner. |
| D-8 Known gap location; reply length | N | IP §6.3, with an `architecture.md` pointer; the vertical slice's lesson is cited, not restated. |
| S-3 (round 1, open) | — | the B5 rows; the real-concurrency probe at Phase 4. |
| S-5 (round 1, open, layout) | — | **open:** the prompt layout (stable text in `system`) is Maxim's render. Not folded; the author proposes adding it to OD-A14 at the next upstream pass. |
| **Architecture** | | |
| A1 (round 1, open) / D1 layer and codec home | S | IG §1 (`engine.inference_wire` at 7a, the adapter at 7b, the forbidden contract); boundaries §2.2. |
| D2 cooldown vs pinned | S | as concurrency D2. |
| D3 kill attribution | S | as concurrency D1. |
| D4 health in a refused file | S | IP §2.2 and §2.7: the `health` block and the policy move to `placements.yaml`. |
| D5 `boundaries.md` §6.3 | S | boundaries §6.3 points to IP §4.3. |
| D6 `load` at spawn | N | IP §2.1; npcs §6.6. |
| D7 missing `finish_reason` | N | IG §5 (`absent` counts as `ok`); `stream_broken` removed. |
| D8 marker for `empty` | N | IG §5 (`TEMPORARY(phase3)`, listed under Phase 3). |
| D9 no-effect allowed set | N | IG §2. |
| D10 policy precedence; endpoints merge | N | IP §2.2 (the policy is in `placements.yaml` only); IG §8 (replace whole, ids match). |
| D11 `spill` order; group slots | N | IP §2.4. |
| D12 package naming; tunables; registry | N | IG §1, §4, §9. |
| **Trust boundary** | | |
| D-B1 taint only through speech | B | IG §6: every guest-supplied string, by any channel (owner). |
| D-S1 clearing taint | S | IG §6: only `purge(S)` clears it, O54. OPEN: it spreads and persists. |
| D-S2 `owner_lan` overclaim; HTTPS | S | IG §7: honest promises; Known gap (IP §6.3). The HTTPS check is mechanism, Phase 4. |
| D-S3 proxy read at build | S (mech.) | IG §2 `NO_PROXY=*`; IG §7 re-read; checklist. |
| D-S4 gateway log rule | S | IG §2: the only place an endpoint may appear; bounded; outside saves; purged. |
| D-S5 no-effect test | S (mech.) | IG §2's allowed set; checklist. |
| D-S6 out of bounds; spend floor | S | IG §3 (null and meter); IG §8 (the host's floor). |
| D-S7 cache row strictness | S | IP §4.2 owns it (versioned, strict decoder, budgets). |
| D-S8 oversized frame | S | IG §3 and §5 (`failed(oversized)`). |
| D-N1 `open` fields | N | IG §3. |
| D-N2 endpoints ids | N | IG §8. |
| D-N3 header test wording | N | IG §2; checklist. |
| D-N4 proxied single-player | N | IG §7. |
| D-N5 Known gaps written | N | IP §6.3; `architecture.md`. |
| D-N6 first hop on `owner_lan` | N | IG §7. |
| D-N7 OD-I10 cites the strict mode | N | roadmap OD-I10; IP §9. |
| **Wire integrity** | | |
| B-1 `truncated` payload | B | IP §2.6: delivered prefix only (TB3-S5); one closed reason list, owned there; npcs §6.6 points to it. |
| S-1 `boundaries.md` §6.3 | S | as architecture D5. |
| S-2 rerun read point | S | as determinism B1. |
| S-3 "finished" | S | as concurrency D3. |
| S-4 stop-reason rows | S | IG §5 (normalisation and per-transport values; refusal values *to verify*); the enumeration is mechanism, Phase 4. |
| S-5 cooldown vs pinned | S | as concurrency D2. |
| S-6 spill in two files; health refused | S | as architecture D4 and D10. |
| S-7 held reply in the header; bug reports | S | npcs §6.6 (`held_reply`); IP §4.2 (the exporter strips it). |
| S-8 "failover off" | S | IP §2.4 (`single`); §4.3 (the ledger pins it). |
| S-9 streaming text elsewhere | S | npcs §5.2, §6.1, §6.2; boundaries §7.4. |
| N-1 failure encoding on rerun | N | IP §4.2 (the reason is in the logged record, which a rerun reads). |
| N-2 `unreachable` row | N | IP §2.6. |
| N-3 `thinking` | N | IP §2.1 (a budget, sent by the host). |
| N-4 fresh spawn | N | as architecture D6. |
| N-5 code list; `ready` fields; tunables | N | IG §3, §4. |
| N-6 npcs §4.4 ceiling wording | N | npcs §4.4. |
| N-7 `inference_status` target | N | IG §8 (`client_rendering.md` §4); IP §10. |
| N-8 retired vocabulary | N | npcs §4.5 meters; the Exp 64 prereg draft. |
| N-9 singular "gateway" | N | npcs §6.1; boundaries §7.1; the upstream draft. O13 is left as a record. |
| **Executor** | | |
| D-S1 `boundaries.md` §6.3 | S | as architecture D5. |
| D-S2 F3 stale; row misfires | S | F3 rewritten; IG §5. |
| D-S3 `refused` has no producer | S | IG §5 (refusal stop reasons, *to verify*). |
| D-S4 counter undercounts | S | IP §2.1 (counters declare their families). |
| D-S5 Known gaps unrecorded | S | IP §6.3; `architecture.md`; npcs §4.5. |
| D-S6 OD-I10 framing; HTTPS check | S | roadmap OD-I10; the HTTPS check is mechanism, Phase 4. |
| D-N1 `last_used_*` | N | IP §1.2; lesson 29. |
| D-N2 F8's `_parse_response` | N | F8. |
| D-N3 F4's SDK evidence | N | F4. |
| D-N4 missing package raises | N | F2; IG §5 (`unclassified`). |
| D-N5 boundaries §7.1 | N | as wire N-9. |
| D-N6 echoed model; request id | N | IP §4.1; IG §2. |
| E-N7 (round 1, open) | — | as architecture D5. |
| **Bio-faithful** | | |
| B-1 pinned under load | B | IP §2.7 (load delay; `empty` on cloud and OpenAI-compatible counts as load; kills don't count); Known gap (IP §6.3). |
| S-1 no call site declares a function | S | IP §2.1; roadmap OD-A14. |
| S-2 never-degrade restriction | S | IP §2.1 (tiers checked at load). |
| S-3 placement facts reach `think` | S | IP §2.6 (only `Reply` variants; `stream_broken` removed); §6.4 schema test. |
| S-4 OD-A25 duplicates B1 | S | roadmap OD-A25: now a question to B1. |
| S-5 `NO_PROXY` | S | IG §2 (verified); roadmap OD-I10. |
| S-6 taint state and clearing | S | IG §6; O54. |
| N-1 `last_used_*` | N | as executor D-N1. |
| N-2 OD-I9 cites `:771` | N | roadmap OD-I9. |
| N-3 OPEN registered; meter | N | npcs §12.2 pointer; IP §6.2 (per-NPC meter). |
| N-4 O27 | N | IP §6.1. |
| BF-3 (round 1, open) | — | as bio B-1. |
