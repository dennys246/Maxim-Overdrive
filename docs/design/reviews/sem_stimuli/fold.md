# Fold table: `sem_stimuli.md` v1 → v2 (2026-11-20)

**The author's table, not a verdict.** Each row says what v2 did and where. The **Status** column is the
reviewers' to set (O25): it reads `open` on every row until a reviewer reads v2 and sets `fixed`, `deferred` or
`rejected`. Where the author proposes a deferral or rejection, the row says "proposed:" with the reason and trigger.

**The owner's ruling** (2026-11-20) on D1–D12, as recommended, governs several rows: D5 (c), D7 answered, D11 (a),
D12 at 10 NPCs. v2 is 5,999 words; v1's 5,979 words were cut and rewritten to make room.

**Claims checked before folding** (Maxim `git show origin/main` at `043eab8f`; not fetched):
`setpoint_aware_neutral.md` (DEFERRED, DO-NOT-BUILD), `archive/world_channel_weighting.md:222`,
`scripts/lint_body_rest_neutral.py`, `spec.py:1025` `apply_damage`, `base_humanoid.yaml:108-120`,
`tool_bridge.py:295-321` and `:548-560`, `encoder.py:596` (A4 gain, exponent 3 on `world`),
`infant_humanoid.yaml:43-49` (`celsius_norm`), `deferred/sem_environmental_proximity_sensing.md`. Overdrive:
`world_clock_release_DRAFT.md` §3.5 and §4 (the PainBus row exists), tile §2.1 (245 kJ/K, `body_key`), tile §2.3's
tick order. All held.

**Author's own errors found while folding.**
- The recommendation message for D11 quoted per-site occlusion at "about 38 ms per physics step at 100 NPCs". That
  figure is the shared 9-ray form, staggered. Per-point is 82 ms per flame per physics step at 10 NPCs as measured. v2
  §8 uses the true figures.
- v2's first cost draft also understated skin and flux. Quadrature evaluated every tick costs about 38 ms per world
  second at 10 NPCs. v2 §8 now says the 10-NPC total, ~130–245 ms, is at or over the ~140 ms target.

## Executor

| Id | v2 | What v2 did | Status |
|---|---|---|---|
| B1 | §5 | the plant goes below a bypassed header check, on surface conductance; a second plant reverses binding order | open |
| S1 | §7.3 | false sentence corrected; `agents-reads-body-frames` forbids `world` and the rest | open |
| S2 | §7.3, §11.1 | `_core_modules` recursive in 5a; every module classified; site names arrive as data | open |
| S3 | §2.4 | the 20% contact figure stated; error-controlled substeps in K replace the fixed step | open |
| S4 | §8 | list retitled "deterministic and independent of the observer"; bounds are header truth constants | open |
| S5 | §4.2 | `BodyFrameFeed` beside `Frame`, never inside it | open |
| S6 | §4.4 | credit withholding, backend hosting and `execute` as the outbox stated; build test for credit | open |
| S7 | §9 M2 | withdrawn, citing the plan and `world_channel_weighting.md:222` | open |
| S8 | §6.3 T9 | the oracle defined: byte-identical frames at every tick across cognition divisors; plant reads `dt_ticks` | open |
| N1 | §0, §1, §6.3 | "twelve gates and a probe"; the leak tests renamed | open |
| N2 | §6.3 T12 | plants moved to the core and channel | open |
| N3 | §3.1, §8, §11.2 | 17 regions, 58 points in costs; the buttocks share left to Q1 (proposed: deferred, trigger Q1's convergence run) | open |
| N4 | §7.2 | cited to `checklists.md:103` | open |
| N5 | §10 D1 | the figure dropped from D1 | open |
| N6 | §2.3 | "yaw thresholds" | open |
| N7 | §9 M4 | "New, nearest home OD-A10"; M3 dropped | open |
| N8 | §4.2 | `__post_init__` refuses writable arrays; constructor-site scan | open |
| N9 | §7.4 | exemptions name `adapters/agents` | open |

## Architecture

| Id | v2 | What v2 did | Status |
|---|---|---|---|
| A-B1 | §7.3 | `protected` contracts on `core.stimuli` and `core.body`; a models allowlist test; recursive classification; `PLANTED` rows | open |
| A-B2 | §5 rule 5 | agent homes record bound rows only; a change is a logged body change; refuse-or-warn is D13 for the owner | open |
| A-S1 | §2.1 | `receptors` and `tag` are non-identity; closing a tag bumps the version | open |
| A-S2 | §7.1 | `core/body/irradiance.py` owns flux, visibility, contact; cost in §8 | open |
| A-S3 | §7.1 | the three seams handed to 5a | open |
| A-S4 | §4.2 | as Executor S5 | open |
| A-S5 | §3.2, §5 | reduction in the core, digested; only reduced values sent | open |
| A-S6 | §10 D1 | option (a): one route; Maxim's `frame` argument carries nothing of it | open |
| A-S7 | §7.1 | runner keeps order and handout; no due-set under D5 (c); cutoffs per row; refresh in irradiance | open |
| A-S8 | §7.3 | `agents-reads-body-frames` | open |
| A-S9 | §6.1 | D10 splits `region_parts`; modulators stay | open |
| A-S10 | §11.1 | a step table; each format's loader, version, gate row and fixture assigned to its step (proposed: deferred to those steps) | open |
| A-S11 | §4.5 | posture, gaze, breathing are logged intents | open |
| A-S12 | §3.1, §3.3, §6.1, §4.1 | revisions named: ANALOG→EARN, BF-15's reading, pinned frames, D10 insertion, the ledger; the tracker's "ranges" (§2.1 says why none) | open |
| A-N1 | §7.2 | digests and ids sort by name | open |
| A-N2 | §4.2 | constructor-site scan | open |
| A-N3 | §4.2 | the core owns `tick`; the worker drops it | open |
| A-N4 | §7.4 | exemptions listed | open |
| A-N5 | §7.1 | the protocol lives in `schema.py` | open |
| A-N6 | §4.3 | a non-finite value in the core is a world bug, stopping loudly | open |

## Wire integrity and trust

| Id | v2 | What v2 did | Status |
|---|---|---|---|
| B1 | §6.2 | receipts as a closed vocabulary, effect as stimuli; T4, T5, T11 over receipt bytes; T12 sentinel in `absorbed_j` | open |
| B2 | §4.1 | the tick order stated as an insertion into D10 | open |
| B3 | §3.1 | one body model: tile §2.1's store is the core node; one `bodies` ledger line; `npc_key` is `body_key` | open |
| S1 | §6.1 | a supersedes list; the actor table leaves the NPC path | open |
| S2 | §4.2 | `caused_by` only when self-caused; name settled | open |
| S3 | §4.2 | offsets within one tick (one frame per tick); `local_id` per NPC. The strip-list exemption is left to `phase1/agents` (proposed: deferred, trigger its schema test) | open |
| S4 | §7.3 | `agents-reads-body-frames`, including `adapters.sem.bridge` | open |
| S5 | §6.1 | D10 rescoped; the environment entity designed in `phase1/agents` under T8, T13 (proposed: deferred, trigger that design) | open |
| S6 | §5 rule 5 | as A-B2 | open |
| S7 | §5 | canonical values, not codec bytes; deltas ruled out | open |
| S8 | §4.3, §2.1 | raise scope named; validity and empty-patch rule per row; NaN, ±inf, `1e400`, `bool` planted | open |
| S9 | §3.2 | binding invariants checked; no unit transform, so `celsius_norm` drives can't bind | open |
| S10 | §2.1, §4.4, §9 M18 | backend specified as the outbox; embedded path as M18; the worker counts clamps | open |
| S11 | §4.2, §5 | `npc_key` check, `registry_digest` against `welcome`, round trip plus goldens | open |
| S12 | §6.3 | T12 plants fixed; host load named as a known leak until D3 | open |
| N1 | §1 | renamed | open |
| N2 | §4.2 | `fields_sequence` | open |
| N3 | §4.2 | the worker checks `tick` rises, then drops it | open |
| N4 | §4.2 | a gate holds `events` empty until sound lands | open |
| N5 | §6.1 | sentence removed | open |
| N6 | §7.3 | `__init__` classified | open |
| N7 | §3.1, §11.1 | site tables in an Overdrive body-instance file with its own loader, not Maxim YAML | open |
| N8 | §4.3 | validate all before any write | open |

## Physics and resolution

| Id | v2 | What v2 did | Status |
|---|---|---|---|
| B1 | §2.4, §8, §10 D11 | per-point visibility (owner, D11 (a)); clustering only within an angular bound; half-shaded test | open |
| B2 | §7.4 | cross-tier tests per coupling, shown red by plants | open |
| S1 | §2.4 | accuracy in K; error-controlled substeps; convergence to 80 kW/m² and contact before the law ships | open |
| S2 | §2.4, §11.2 | contact as one implicit system, booked from the object; h_c citation and ISO anchor before `data/` (proposed: deferred, trigger the tissue law's PR) | open |
| S3 | §2.4 | contact and free sub-columns | open |
| S4 | §8 | refresh on motion and topology, never by index; staleness measured first | open |
| S5 | §2.2, §7.1 | flux every tick at the pose; radiance `tick`; re-costed | open |
| S6 | §2.4, §8, §11.2 Q4 | quadrature costed until an analytic form is measured; self-shadowing as a Known gap (proposed: deferred, trigger the irradiance law) | open |
| S7 | §3.2 | pooling fixed by receptor class; means refused on pain paths | open |
| S8 | §11.2 | constants traced, Ω graded, Jasiński's miss recorded, all before `data/` (proposed: deferred, trigger the tissue law's data) | open |
| S9 | §2.2, §11.2 Q3 | radiance from surface temperatures only; cell-mean path a strict red gate | open |
| N1 | §8 | 58 points; tier not yet stated (proposed: deferred, trigger the measured cost) | open |
| N2 | §2.4 | a node at each declared depth | open |
| N3 | §2.2 | ITD shortfall stated; rise time as ANALOG source data | open |
| N4 | §2.2, §2.3 | `flicker_depth` dropped; the reason restated | open |
| N5 | §3.1 | reservoir terms ledgered | open |
| N6 | §3.3 | burned area is no longer a row; quantisation moves to the damage delta (proposed: rejected as moot, burned area isn't delivered) | open |

## Determinism and performance

| Id | v2 | What v2 did | Status |
|---|---|---|---|
| DP-B1 | §4.2, §5 | ids by sorted name in the header; bodies and bindings in `join`; under D5 (c) the stepping set is every body, from logged records | open |
| DP-B2 | §7.2, §8, §6.3 T11 | batch invariance in the contract; BLAS lint; T11 join plant; parallelism serial until then | open |
| DP-S1 | §4.2 | `StimulusEvent` defined; one frame per tick removes the cross-tick sort | open |
| DP-S2 | §4.1 | tick pinned, but not in this order: physics after agents keeps D10 and lets lanes overlap (Concurrency B1). `fields_sequence` names the input (proposed: rejected in part, the reorder) | open |
| DP-S3 | §7.1 | flux, visibility, contact in the irradiance law every tick, independent of cadence | open |
| DP-S4 | §5, §8 | constants in the header; phase-by-index removed | open |
| DP-S5 | §8 | totals table; budget and work counters (D12); p99 advisory; the 10-NPC breach stated | open |
| DP-S6 | §3.2, §5 | reductions in the core, digested; canonical values; codec goldens | open |
| DP-S7 | §6.3 T9, §5 | worker half as a strict red gate; tier-2 caveat | open |
| DP-S8 | §3.1, §6.3 T11 | bodies are ledger-only receivers (ANALOG); T11's perturbation set defined. The non-conservation figure isn't measured (proposed: deferred, trigger the irradiance law) | open |
| DP-N1 | §8 | the reuse cache dropped | open |
| DP-N2 | §5 | chained digest at log v0's interval | open |
| DP-N3 | §2.3 | floored once | open |
| DP-N4 | §5 | length-prefixed | open |
| DP-N5 | §4.3, §4.5 | apply tick stated; inert NPCs built and digested, not sent | open |

## Bio-faithful integration

| Id | v2 | What v2 did | Status |
|---|---|---|---|
| B1 | §0, §4, §10 D5 | D5 (c) is v1 (owner); M16 asks Maxim for body steps without cognition; the fallback is a strict red gate and a Known gap | open |
| B2 | §1, §2.2 | `exposed_area_fraction` withdrawn | open |
| B3 | §3.3, §9 M2 | M2 withdrawn; bodies pass Maxim's rest lint | open |
| S1 | §3.3 | channel (world, no drive), gain weights at 45 and 60 °C, range OPEN to measure (proposed: deferred, trigger the first body's measurement) | open |
| S2 | §6.4 | D7 answered with citations; R15 claim rule; M19 to OD-A11 | open |
| S3 | §3.3, §9 M17 | damage through `apply_damage`; burned area never bound; ANALOG | open |
| S4 | §9 M5–M8, §10 D3 | citations of the world-clock draft; evidence in the future tense | open |
| S5 | §9 M14 | pushback against the proximity plan's mechanism | open |
| S6 | §9 M15 | question to the salience route; OPEN | open |
| S7 | §3.2 | pooling by receptor class; EARN | open |
| S8 | §6.2, §6.3, §9 M9 | R1 lead-time gate, R8 per-act test, R14 in M9; lessons 23 and 25 recorded in this commit | open |
| N1 | §2.2, §9 M12 | EARN | open |
| N2 | §9 | MP ids added; MP-2b in M9 | open |
| N3 | `fire_model.md` §5.1, lesson 24 | both reworded in this commit | open |
| N4 | §9 M13 | check done; New confirmed | open |
| N5 | §9 | M3 dropped | open |
| N6 | §10 D4 | OD-A2 cited | open |
| N7 | §2.2 | a melanopic band reserved | open |
| N8 | §2.2, §2.3 | offsets within the tick | open |
| N9 | §6.4, §4.4 | ΣV OPEN stated; backend's modulator named; `experienced` kind | open |
| N10 | §11.2 Q6 | recorded as open | open |

## Concurrency and lanes

| Id | v2 | What v2 did | Status |
|---|---|---|---|
| B1 | §4.1 | the standing order kept, with insertion; overlap allowed, gated by an on/off digest test | open |
| B2 | §4.3 | events capped, coalesced, checked before sending; nothing accumulates for an inert NPC; both tests | open |
| S1 | §3.2, §8 | only bound values cross; B5 rows; the "few hundred bytes" claim gone | open |
| S2 | §4.3 | non-blocking sends; crashes map to `agent_failed(crashed)`; both tests | open |
| S3 | §4.4 | thread and owner check after build; planted writer | open |
| S4 | §8 | fork-join rules; serial until T11's plant | open |
| S5 | §4.2 | as Executor N8 | open |
| S6 | §10 D5 | (c) ruled; (d), the wake predicate, not taken (proposed: rejected, (c) needs no wake; trigger: M16 fails and (c) is unaffordable) | open |
| S7 | §4.5 | lifecycle table; membership from records | open |
| S8 | §4.5 | breath as a logged record; default schedule when inert | open |
| S9 | §8, §2.1 | B5 rows named; the worker counts clamps | open |
| N1 | §8 | no index phase | open |
| N2 | §8 | the cache dropped | open |
| N3 | §5 | deltas ruled out | open |
| N4 | §4.2 | `npc_key` checked | open |
| N5 | — | pause rule cut for length (proposed: deferred, trigger `phase1/agents`' barrier design) | open |

## Counts

130 findings: 15 BLOCKER, 66 SHOULD-FIX, 49 NIT. The author proposes 11 deferrals and 3 rejections (one in
part); every other row claims a fold. One question goes to the owner: D13.
