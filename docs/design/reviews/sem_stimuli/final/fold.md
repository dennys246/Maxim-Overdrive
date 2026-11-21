# Fold of the final round into `sem_stimuli.md` v5 (2026-11-21)

**The owner stopped the paper rounds** (2026-11-21). By the drafted standard (`phase1/standards-bars`), a second
paper round that finds new blockers in text the folds added ends the rounds. So **no design round reviews v5**. Every
status below stays **open (for the reviewer, on the code PR)**: the reviews of 5a, 5b, `phase1/agents` and the tissue
row set each status when they read the tree. The author sets none (O25).

**What v5 does.** It folds the final round's one BLOCKER and its contract-level SHOULD-FIXes into the design. It
moves every law-level finding into `docs/plans/checklists.md` as a test that cites the finding's id. And it carries
the owner's re-ruling of PH2-S2 to (c): the world is the body's plant and the NPC is its controller (§3.1).

**Word counts:** v5 is 5,999 words (v4 was 5,982). `tile_and_client.md` went from 5,977 to 5,927, and
`embeddable_agent_DRAFT.md` from 2,500 to 2,499.

**Verified before folding** (lesson 26; scripts in the session scratchpad, `v5/`):
- **The reordered layers contracts** (A3-S2): Architecture's `v4_layers_fixed.sh`, rerun, keeps every implied import
  and breaks on `spec → store` and `models → run`.
- **`as_packages = false`** (N-S3): `package_forbid.sh`, rerun. A package in the list is BROKEN; with the setting
  false it is KEPT.
- **Per-tick coalescing** (R2 and its duplicates): my `coalesce_per_tick.py` shows delivered content equal to
  divisor 1's at every divisor from 1 to 50. Per-delivery coalescing differs from divisor 2 on.
- **Maxim at `origin/main` `043eab8f`:**
  - `llm_worker.py:665` and `:822` (`thread_name_prefix="LLMCall"`);
  - `autonomic_layer.md` §3.1.4 (G9's out-of-band producer: `drain_outcomes()`, `CauseRef.cause_pid`, latched
    emission);
  - `autonomic_layer.md` §3.3 (two-sided needs) and R-2;
  - no effector output for skin blood flow, sweat, shivering or metabolic rate, after searching `docs/plans`,
    `DECISIONS.md` and `src` for thermoreg, shiver, sweat, vasoconstrict, vasomotor, perfusion and core_temp.
- **Overdrive:**
  - the applier's five target-dependent refusals (`applier.py:73-80`, `:104`, `:122`);
  - `boundaries.md` §2.2 placing receipts in `engine.intents`;
  - `boundaries.md:572`'s strip exemption;
  - `src/simcore/core/__init__.py` importing nothing.

**Not verified, taken from the reviewers:**
- Physics' `wood_horizon.py` numbers (54.2 s, 12.5 s, 1.9 K margin);
- DP's `final_checks.py` (two emitters can't go red);
- Concurrency's `thread_names.py` model;
- the physiology ranges in the checklist's core item, which are **M** (from memory) and must be cited before `data/`:
  basal metabolism about 80 W, skin blood flow up to about 6–8 L/min, sweat up to about 1–2 L/h, shivering up to
  about 3–5× basal, and Gagge's two-node model.

**Found false:** none of the reviewers' claims that I checked.

**One design choice is mine, beyond a reviewer's text** (N-S2): the worker sends intents as wire data, and stage 1
parses them on the host. So `AGENTS_SURFACE` shrinks to `stimuli.wire`, `checks` and `readonly`, and the worker
imports nothing from `intents`. The code PR's reviewers should weigh it.

## Executor

| Id | Where it went | Status |
|---|---|---|
| S-F1 | Checklist, laws: "Plants for §6.3's gates", a plant for every gate; T11's plants moved there from the design | open (for the reviewer, on the code PR) |
| S-F2 | Design §7.1, §7.3, §11.1: `schema.py`'s rows, site sets and binding validation land with `phase1/agents`, and the `StimulusModel` protocol with the tissue row; checklist, agent half | open (for the reviewer, on the code PR) |
| S-F3 | Design §4.2, §5: the bound lane chains every tick, independent of delivery, and T9 holds delivery to it | open (for the reviewer, on the code PR) |
| S-F4 | Checklist: 5a keeps toy-row plants; the reduction, law and bound-home plants move to the tissue row | open (for the reviewer, on the code PR) |
| S-F5 | Design preamble: every strict red gate states `raises=`; checklist, agent half, with the tooling test proposed to the standards line (outside this branch) | open (for the reviewer, on the code PR) |
| S-F6 | As R2 | open (for the reviewer, on the code PR) |
| N-F1 | As R3 | open (for the reviewer, on the code PR) |
| N-F2 | Checklist 5b: the core node's closed form and plant; laws: the core item's pass rule | open (for the reviewer, on the code PR) |
| N-F3 | Design §11.1: T16a–c move to the tissue row | open (for the reviewer, on the code PR) |
| N-F4 | Tracker SEM row rewritten | open (for the reviewer, on the code PR) |
| N-F5 | Checklist 5a: the numbers are marked as pre-rounding | open (for the reviewer, on the code PR) |

## Architecture

| Id | Where it went | Status |
|---|---|---|
| A3-S2 | Design §7.3: the verified orders; checklist 5b | open (for the reviewer, on the code PR) |
| A3-S5 | Design §5, §7.4: producers are the transitive closure over every law's declared reads and writes; plants: 5a (a toy law two hops upstream), tissue row (a bound home refused) | open (for the reviewer, on the code PR) |
| N-S1 | Design §6.2, §7.1: `Receipt`'s one home is `stimuli.wire`; `intents` keeps its refusal codes and layer 6 maps them; `boundaries.md` §2.2's "receipts" and `settle`'s type are superseded by name; stimuli imports nothing from `intents` | open (for the reviewer, on the code PR) |
| N-S2 | Design §4.5, §7.3: the worker sends wire data and imports nothing from `intents`; `AGENTS_SURFACE` = `stimuli.wire`, `checks`, `readonly` (the author's choice; **accepted by the owner, 2026-11-21**) | open (for the reviewer, on the code PR) |
| N-S3 | Design §7.3: `as_packages = false`, asserted by the equality tests (verified); checklist 5a | open (for the reviewer, on the code PR) |
| N-N1 | Design §7.3: each surface module lands with its step; checklist, agent half | open (for the reviewer, on the code PR) |
| N-N2 | Design §7.1: `wire.py` imports `readonly`, which is on the surface; the closure plant becomes `body.spec` | open (for the reviewer, on the code PR) |
| N-N3 | Design §7.1: `events.py` is its own sole writer, in step 4, with a row in §6.4's table | open (for the reviewer, on the code PR) |

## Wire integrity and trust

| Id | Where it went | Status |
|---|---|---|
| W-N1 | As R2 | open (for the reviewer, on the code PR) |
| W-N2 | Design §6.2: kinds are decided by stage 1 alone, and every stage-2 result is `accepted`; checklist: T11 sweeps all five applier refusals, once per affordance, each planted | open (for the reviewer, on the code PR) |
| W-N3 | Design §4.2, §5: the per-tick bound lane keeps delivery out of every digest (Wire's first option) | open (for the reviewer, on the code PR) |
| W-N4 | Checklist 5b: the NaN plant gives a `malformed` receipt | open (for the reviewer, on the code PR) |
| W-N5 | Design §7.3: the closure test covers each member's parent packages; §7.4: `core/stimuli/__init__.py` imports nothing; checklist: a re-export plant | open (for the reviewer, on the code PR) |
| W-N6 | Tracker fixed; §11.3's "recommended" dropped; §6.2 times receipts for refused intents; S3's trigger (`offset_us`) in the agent checklist | open (for the reviewer, on the code PR) |

S3 and S5 remain deferred, with Wire's triggers.

## Physics and resolution

| Id | Where it went | Status |
|---|---|---|
| PH2-S1 | Design §3.1: tile §2.1's exchange-volume convection is superseded by name, and convection against the fixed Phase 1 reservoir is booked in `bodies`; tile §2.1 edited (net −50 words); checklist sinks | open (for the reviewer, on the code PR) |
| PH2-S2 | Re-ruled to (c) by the owner: design §3.1, §10; the checklist's core item rewritten, with (a) and (b) gone | open (for the reviewer, on the code PR) |
| P-S1 | Resolved by (c): a free core, every watt booked and signed, `core_temperature` informative; tile §2.1's closed forms superseded | open (for the reviewer, on the code PR) |
| P-S2 | Checklist contact: a 10 s horizon, a 1.9 K margin, 54.2 s recorded, and the 120 °C tolerance from the reference's convergence spread | open (for the reviewer, on the code PR) |
| P-N1 | Design §2.3: 3× is limited to shade | open (for the reviewer, on the code PR) |
| P-N2 | Checklist accuracy: 7.0–7.8% per 0.1 K under Henriques | open (for the reviewer, on the code PR) |
| P-N3 | Checklist sinks: a fixture gas field; the shipped-path test waits for zones | open (for the reviewer, on the code PR) |

PH2-S3 remains deferred, with Physics' trigger.

## Determinism and performance

| Id | Where it went | Status |
|---|---|---|
| DP-F-S1 | Design §7.2: canonical order by the smallest `(object id, sub-mesh node id)`; checklist: a save–load test with two components on one cell | open (for the reviewer, on the code PR) |
| DP-F-S2 | As R2; the coalesced events are digested by the events lane | open (for the reviewer, on the code PR) |
| DP-F-S3 | Design §5 header and §8: above the maximum emitter count no value changes; it is logged and the counters read it; checklist 5a slot | open (for the reviewer, on the code PR) |
| DP-F-S4 | Checklist: T11's plant fixtures (three or more emitters; a crowd or a cap below demand; B raising the merged substep count), each asserting first that its permutation changes the output | open (for the reviewer, on the code PR) |
| DP-F-N1 | Design §7.1: `radiant_emitters` keyed `(writer law, source object id, primitive id)`; checklist 5a | open (for the reviewer, on the code PR) |
| DP-F-N2 | Checklist refresh: body sort position dropped | open (for the reviewer, on the code PR) |
| DP-F-N3 | Checklist refresh: k = 12 is the stationary floor | open (for the reviewer, on the code PR) |
| DP-F-N4 | Design §4.1: every leg's lanes and record stream are equal; checklist | open (for the reviewer, on the code PR) |

## Bio-faithful integration

| Id | Where it went | Status |
|---|---|---|
| B-F-B1 | Design §4.6, §6.3: T16 splits into T16a (red under D14), T16b (the world half, green whatever D14 says) and T16c (the future bar). T16c runs under D5 (c) on real pymaxim and asserts that the between-pass publish joins its crossing tick, so lifting D14 can't flip it; only G9's producer can. Roadmap OD-A22, with its trigger | open (for the reviewer, on the code PR) |
| B-F-S1 | Design §9 M4; `embeddable_agent_DRAFT.md` §7; lesson 27: routed to `autonomic_layer.md` §3.1.4 (G9) and #1176, with GL3.B0 as evidence | open (for the reviewer, on the code PR) |
| B-F-S2 | Design §4.6: the lead is at least a cited withdrawal latency plus one cognition interval, at the dial's maximum over every phase, under D5 (c), recorded in ticks; checklist | open (for the reviewer, on the code PR) |
| B-F-S3 | Resolved by (c); §9 adds M20, a question to `autonomic_layer.md` §3.3 and R-2; roadmap OD-C12; T17 is a future bar; lesson 28 | open (for the reviewer, on the code PR) |
| B-F-N1 | Design §4.6 defines the test, and §6.3's conditional sentence is gone | open (for the reviewer, on the code PR) |
| B-F-N2 | Design §4.6: the stamp is the host tick of the `evaluate_failures` call whose subscriber saw it, and the fixture has one entry because of the wall-clock refractory | open (for the reviewer, on the code PR) |
| B-F-N3 | The checklist's core item rewritten | open (for the reviewer, on the code PR) |
| B-F-N4 | Checklist, agent half: a host step planted on a cognition tick must make the count read 2 | open (for the reviewer, on the code PR) |

SF-2 (delta 1) remains deferred, with its trigger.

## Concurrency and lanes

| Id | Where it went | Status |
|---|---|---|
| R1 | Design §4.4 and §11.3: real NPCs wait on OD-EA7, which the roadmap's Phase 4 subset already lists; checklist: a real-pymaxim test (one LLM step, then a park), `xfail(strict=True, raises=AssertionError)` on OD-EA7 | open (for the reviewer, on the code PR) |
| R2 | Design §4.2, §4.3: events coalesce per tick in `BodyFrame` against a per-tick budget; a delivery's bound is the budget times the largest divisor, refused at start against the socket buffer; receipts are never coalesced and are bounded by `ActionLimits`' per-step cap; "nothing is lost" replaced. Verified on a toy. Checklist: a burst at divisors 1 and 10 | open (for the reviewer, on the code PR) |
| R3 | Design §4.4: "under D5 (c) … under D14 never" | open (for the reviewer, on the code PR) |
| R4 | Design §4.4: each re-baseline logs its delta, which must be empty or name session restarts; checklist: a leaking-session plant | open (for the reviewer, on the code PR) |

S9 remains deferred, with its trigger.

## Not done, said plainly

- **The tooling test requiring `raises=` on every `xfail`** (S-F5) belongs to the standards line. It is noted for
  `phase1/standards-bars`, not added here, because that branch owns `docs/standards_backlog.md`'s new rows.
- **The physiology numbers are from memory.** Gagge 1971, Rowell and ISO 8996 must be traced before the core law's
  `data/` file. The checklist says so.
- **The withdrawal latency in the pain-path margin has no citation yet.** It is marked **M**.
