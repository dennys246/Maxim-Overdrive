# The offline generation harness: the contract (design, 2026-11-22; round 1 folded)

**Status.** A design, written now and built after the spec generator spike's results (owner, 2026-11-22). Its first
consumer is stage 2. It replaces `docs/plans/generation_harness_plan.md`, which round 1 reviewed
(`reviews/generation_harness/`). Until it is built, the spike's code stays frozen in `spikes/specgen/` (PR #50).

**Scope.** Imagined-object specs generated in bulk, offline, by local models, and the checks a generated object must
pass before anything uses it. Runtime imagination by an NPC is not this: it goes through the inference gateway under a
thought's deadline (`npcs_and_sem.md`, `inference_placement.md`).

**This document owns:**
- the job, run-header, record, battery and verdict formats (§5);
- the verdict classes (§6);
- the checks (§7);
- the harness's inference client (§4).

Everything else is linked to its owner and never restated.

**It depends on unmerged work:**
- PR #51 (`subcell_solids.md`: spec v1, the µm rule, S1–S6);
- `phase1/torch-pilot` (`torch_pilot.md` §3, `kindle`'s target rule);
- the spike's code in PR #50;
- PR #52 (`docs/known_gaps.md`, where §2 and §6 record their gaps).

H0 (§10) lists them as preconditions.

## 1. Purpose

We will generate often:
- **stage 2's training and evaluation data** (the spike's plan §6);
- **regression reruns** when a model, the engine build, the spec format or a law changes;
- **possibly pre-generated props** for shipped scenes, which then become content under `ip_and_licensing.md` §6.

Each needs:
- a resumable batch runner that proves its engine;
- the grammar-plus-feedback generation protocol;
- the scoring kit;
- a standard test of whether a generated object works for its consumers, which the spike never had (§6, §7).

## 2. Rules

- **Only `place` writes the world.** Specs enter only through `simcore.core.imagination.place` (until step 5a makes it
  the `imagine` intent's stage 2). The harness never writes cells or builds a region.
- **A shipped prop enters through `place`** when its scene is built, and never as a hand-authored scene primitive. So
  `place`'s budget, name rule and ownership hold for it.
- **Batch jobs never use a hosted model.** This is hard-coded: a job's placement must have egress `loopback` or
  `owner_lan` (IP §2.2), there is no consent path, and a reported proxy refuses the run. `owner_lan` admits a
  Tailscale-joined machine the owner doesn't physically hold (IG §7). That is a declaration this code can't check,
  recorded in `docs/known_gaps.md`.
- **Committed records are the truth.** Rescoring and the battery read records; they never regenerate.
- **Pre-registered experiments pin the harness,** never the other way round. A spike's freeze manifest pins the
  harness version and the job file's digest (§5.1). A harness change never alters a frozen run's numbers.
- **Nothing private is committed.** The repository is public. Endpoints, gateway logs and the inference client's own
  logs live in the per-user directory that `maxim_overdrive.data` resolves, never in `data/` or a run directory.
  Anything written into a run directory passes the mask of §4.

## 3. Reproducibility

Each promise names its pins and the test that proves it.

| What | Promise | Pins | Proven by |
|---|---|---|---|
| Generation | bit-identical rerun on one machine and one engine build | seeds and `retry_seed`; samplers; one server slot; the engine build; `cache_prompt: false` (a prompt-cache hit changes the floating-point path) | H1: two runs of one fixture cell on the mini give byte-identical records, with and without a resume in the middle |
| Generation, across machines | none; the records are the truth | none | none |
| Scoring | bit-identical on one machine. Across machines, integer and boolean statistics (rates, `rng_for` intervals) are bit-identical, while `pow` and BLAS statistics (cylinder masks, Vendi) hold to an outcome class within a band | per-statistic generators; the scorer version | H2: a digest of the integer statistics on a committed fixture, and an outcome-class comparison, with a band derived from their error and written before measurement, for the rest |
| The battery | bit-identical verdicts on one machine; the same outcome class across grids and machines, within §7's margins | battery version, engine commit, data digests, lockfile, pymaxim version (§5.4) | H3: a spec's verdict alone equals its verdict in a shuffled batch, under 1 and N BLAS threads, in two processes with different hash seeds |

A timed-out or retried request is recorded as one (§5.3) and excluded from the generation row's claim.

## 4. Where it lives, and its inference client

**The package: `overdrive_tools`, a new root never shipped** (owner, 2026-11-22). It joins `[tool.importlinter]`'s
`layers` above `maxim_overdrive`, is absent from the wheel's `packages`, and is measured by coverage like `src/`. Why
not the game package: everything there ships, so players would get the bootstraps, the blind labelling and the batch
CLI. Why not `scripts/`: the harness has a consumer on a product path (stage 2), not repository upkeep.

**Its import surface is a contract** (proposed edit to `boundaries.md` §2.2). It may import:
- `simcore.core.imagination`'s public functions;
- `Simulation`'s scene entry;
- the applier;
- `simcore.core.digest`;
- `simcore.protocol.encoding`;
- the loaders' public readers;
- the lab builder at its new home (D10, NS3; §7's L5).

A new `generation-surface` contract names exactly these and forbids every other `simcore.core` module. Spike code that
imports `grid`, `scene` internals or `world` is rewritten onto that surface, or the surface gains a public entry point
through its owner. Two more proposed changes: `overdrive_tools` may import `simcore.verify`, because
`verify-ships-nowhere` protects shipped packages and this one never ships; and it may import `maxim` only in its lab
module, a named exception to `maxim-through-adapters`.

**The repository's gates it needs,** each reviewed as a trust-boundary change:
- an entry in `tests/test_determinism.py`'s `NOT_SIMULATION`, because windows and `wall_s` read the clock (no scored
  value does);
- an `ALLOWED` row in `tests/_imports.py` for each external (json, hashlib, urllib, subprocess);
- gate-registry rows (`scripts/lint_gates.py`) and `INPUT_GATES` entries for the job reader, the record reader and
  writer, and the battery and verdict readers.

**The inference client: `TEMPORARY(phase4/inference)`.** The gateway (IG) and placements (IP) can't yet carry the
generation protocol:
- the canonical request (IP §4.2) has no `response_format`, `min_p` or `repeat_penalty`;
- F6 (IP §1.3): no backend takes a seed, top-p or top-k;
- OD-I12: Maxim's backend can't switch a template's thinking off;
- the envelope's `thinking` is a token budget, not that switch;
- there is no host-side caller without a session (IP §2.3, §2.5).

So the harness keeps its own client to llama-server until IG and IP gain these, listed in the roadmap's Phase 4 for
removal. It carries these conditions:
- **No proxy:** `urllib.request.build_opener(ProxyHandler({}))`.
- **A literal-address egress check,** matching IG §3's `open` check. The endpoint must be loopback, or the placement's
  declared `owner_lan` address. Anything else is refused before a socket opens.
- **No fallback, the lesson of OD-I11.** The client is built from the placement's address alone and never from the
  environment. It checks its effective base URL against the placement before the first request, and refuses on any
  difference.
- **Logs outside the worktree** (§2), and the address never printed in a traceback: transport errors are relayed as
  §5.3's outcome classes, not exception text.
- **A mask** for anything written into a run directory: the endpoint address and `$HOME` are replaced, as the spike's
  `run_window.sh` does.
- **The server binds loopback** when generator and server share a machine. Otherwise it needs an API key the client
  holds.

**Proposed edits when the gateway path is built** (each made in its owner section):
- **IP §2.1:** batch functions as rows of `functions.yaml`, with their envelopes, so a job only names a function.
- **IP §2.2:** declared `build`, `context`, `slots` and a weights-digest encoding, all checked.
- **IP §2.3:** an eligibility rule for a caller without speakers.
- **IP §4.2:** `response_format`, `min_p`, `repeat_penalty`, `seed` and the thinking switch in the canonical request.
- **IG §3:** a `ready` or probe field carrying the server's measured build, context and slots.
- **IG §5:** unchanged. The harness maps IG's outcomes to its record classes itself (§5.3), so NPCs' outcomes don't
  change for a batch's sake.
- **Phase 3 asks:**
  - against F6: seeds and samplers on the backends;
  - against OD-I12: a thinking switch per provider;
  - OD-I11: refuse rather than fall back.

## 5. Formats

Every format is versioned, readers refuse unknown versions loudly, and each has a round trip and committed golden
fixtures. Replies and records are decoded strictly, with `boundaries.md` §9.1's decoder:
- repeated keys are refused;
- `NaN` and infinities are refused;
- nesting depth and line length are bounded;
- a reply too deep to decode is the class `parse_failure`, never a crash.

### 5.1 The job file

A job file, `schema.py`'s `Format`, versioned, replaces `arms.yaml`'s hard-coded protocol. It names:
- the placement id (a job selects a placement; it never sets slots);
- the function;
- the generation protocol: arms, samplers, seeds, `retry_seed`, the thinking switch, the schema, instructions,
  examples and feedback template;
- the prompt files;
- the battery version it requires.

**What is fed back is code, not configuration:** only `place`'s `agent_text` for refusals classed `spec_fault`
(§6). A world outcome and a battery verdict are never fed back, so the generator can't learn the grid. A job file that
names anything else to feed back is refused.

A job's identity is the c14n digest (`sha256/c14n-1:`) of its file plus the harness version string. A freeze
manifest pins both.

### 5.2 The run header

The first record of a run file. **Every key is classified** in this document's table of header keys, kept in code
beside the reader. A test fails on a key in neither class.

| Class | Keys |
|---|---|
| `must_match` (a resume or a rescore refuses a difference) | format version; job digest; harness version; frozen-input hashes; engine build; context; slots; measured weights digest; `cache_prompt`; `reproducible` (one slot and pinned seeds); machine label, when `reproducible`; simcore commit; data digests; lockfile hash; spec format version |
| `informational` (recorded; a difference is allowed, with the reason) | start time, because a resume restarts it; window schedule, because windows don't change outputs; the operator's free-text label |

The spike's v0 header is a named exception: readable for rescoring, never resumed under this harness.

### 5.3 Records

One JSON line per sample or attempt. Fields:
- the prompt id and seed;
- the attempt and its derived seed;
- the raw reply;
- the record class;
- `place`'s code, field and `agent_text`;
- tokens and `wall_s`;
- the IG outcome or the client's transport outcome;
- IP §4.1's provenance value, by reference, once the gateway path exists.

**The record classes:** `accepted`, `place_refused`, `outside_world`, `length_stop`, `overflowed` and
`parse_failure`, plus `timed_out` and `transport_error`. The last two are excluded from generation identity. This
document holds one versioned mapping from IG's outcomes, and from the client's, to these classes. The spike's v0
records (one `truncated` for both a length stop and an overflow) are a named exception, read by a v0 reader.

### 5.4 The battery file

Versioned. It fixes the battery's inputs, so a verdict depends on nothing else:
- the fixture scenes (§7's placement-in-context scene included);
- the `Budget`: the world's own, from `data/`, and never above it;
- each check's scenario, turns and grids (§7);
- the margins;
- a per-spec cost bound, derived from those inputs and measured at H3.

### 5.5 Verdicts

A verdict file: versioned, and keyed per spec on the SpecId (§8), the spec's name (for the IP gate, which reads names
that SpecId excludes), the battery version and the header's `must_match` digests. Each check has one of:
- `pass`;
- `spec_fault` (with a code);
- `world_outcome` (with a code);
- `engine_gap` (with its strict red gate's id);
- `within_margin`, for a binary outcome inside its band;
- `not_run` (with `waits_on=<step>`).

A consumer declares the checks it needs. It refuses a spec with `spec_fault`, `not_run` or `within_margin` on any of
them, and refuses a verdict file whose key differs from its current tree in any `must_match` digest. `world_outcome`
and `engine_gap` never exclude a spec.

## 6. Verdict classes, and the engine-property suite

A check judges the spec, not the engine. There are three outcomes and one suite:
- **`spec_fault`:** the spec's own error. Only `place`'s refusals classed spec faults (tile §3.4's class column,
  `subcell_solids.md` §11.3), plus a name failing §7's text checks.
- **`world_outcome`:** the spec meeting the world as it is, such as not igniting, failing statics, or a `too_small`
  refusal under D34 today. Recorded, never a fault.
- **`engine_gap`:** a failure a Known gap explains (`docs/known_gaps.md`), carrying that gap's strict red gate id. It
  never excludes a spec, because filtering on it would steer stage 2's data away from shapes the engine mishandles.
- **The engine-property suite:** engine invariants are checked over the generated corpus as property tests of the
  laws, not as spec verdicts. Every field finite, temperatures within the material's bound, integrity in [0, 1], and
  the ledger closing within `world_model.md` §4's tolerance. A failure stops the batch loudly, names the spec as a
  reproducer, and is filed as an engine defect with a red gate. It never marks the spec.

## 7. The checks

Grids: the truth grid is 0.1 m, compared against the 0.05 m reference (`world_model.md` §1.1). 0.2 m is recorded,
never judged, because its known lags are red gates. Every bar names its kind (CLAUDE.md: verification, validation,
or process) and its source, or reads "measured at H3, before the first battery run". Binary outcomes are gated with
an outcome margin from `simcore.verify`'s `band_gate`. Inside the band, the verdict is `within_margin`.

| Check | What it judges | Path | Bar | Until |
|---|---|---|---|---|
| U1 placement | `place` accepts, at the truth grid, inside the world; refusals classed §6 | `place` (later the `imagine` intent) | process: `place`'s own rules | U1 through `imagine` at step 5a |
| U1c placement in context | the spec placed in a fixture scene with spawns and neighbours, under the world's budget: no `space_taken` on its neighbours' reach, no name colliding with a spawn | `place` in the fixture | process | — |
| U2 representation fidelity | per part, cell volume over authored volume at each grid, and whether any part has no cells at the truth grid | `place`, then a read | **recorded, not judged**, except "a part with no cells at the truth grid", which is a `spec_fault` when the part is above the representation threshold and `engine_gap` (D34) otherwise | judged in µm from `subcell_solids.md` S1 |
| U3 heat | a fixed source (power, radius and position named in the battery file) for a named number of turns, at 0.1 m against 0.05 m: the peak temperature and the onset tick | `Simulation` | verification: the closed-form and cross-grid bar of `tests/test_cross_tier.py`'s onset, rederived per B30 | — |
| U3s strike | a fixed strike (energy from the spec's own material and mass): `region_breached` and integrity at 0.1 m against 0.05 m | the applier | verification, band-gated | — |
| U4 fire | `kindle` on the object ignites if and only if it is fuel | `kindle` (`torch_pilot.md` §3) | process | `not_run` until 6.1b; fire-on-air stays a diagnostic (`engine_gap`) |
| L5 lab surface | the region's lab instruments (§4, D10) read finite values, and the entity declares no failure modes and no drive. A strike through the lab path publishes nothing on a subscribed `PainBus`, since the world never writes pain | the lab builder, real Maxim classes | process. Measured 2026-11-22: 0 signals, 0 failure modes | object-only regions: the expected verdict is the refusal (D36 (2), `subcell_solids.md` §7.3), and their lab readings are checked under their new lab names; a planted 0.38, 0.40 and 0.42 m triple |
| N5 NPC perception | an NPC body near the object receives its effect as stimuli at receptors (`sem_stimuli.md` §2.2–§2.3, §6.3 T3 and T11) | the perceiver path | perception and learning | `not_run` until the first body (Phase 4); strict red gate |
| N6 NPC act | an NPC intent naming the object goes outbox → `pending` → receipt `accepted` → the effect as stimuli (`sem_stimuli.md` §3.3, §6.1–§6.2) | Overdrive's designed path, never Maxim's tool bridge on a region | perception and learning | `not_run` until `phase1/agents` and the first body |
| T7 name | the name passes `sem_stimuli.md` T7's denylist and `engine.text.player_text` (`npcs_and_sem.md` §7), claims no property the physics contradicts, and meets the shipped adapter's tool-name rule (length and charset of the names Maxim builds from it) | the text gates | process | — |
| U7 wire | the frame's snapshot carries the object's region identity (`region_id`, the spec id in `welcome`, IP §6.4), and the object is distinguishable from a same-material neighbour by more than colour | the encoder; the client decoder in a test | process | object tables at `subcell_solids.md` S6; the wire codec |
| U8 determinism | the spec placed, then run for U3's turns, gives the same digest twice, in two processes, at 0.1 m | `Simulation` | determinism (one machine) | a digest of grid state names its scheme, proposed to `digest.py`'s owner |
| U9 replay and save | an intent log with the `imagine` replays to the same digest; a save round-trips | intent log, save | determinism | `not_run` until step 5a's intent log and step 9's save |
| U10 support | D33's placement rule, and statics outcome class at 0.1 m against 0.05 m, band-gated | statics | verification | `not_run` until `subcell_solids.md` S4; cell parts `engine_gap` until D22 |
| U11 provenance and IP | SpecId (§8), licence and the IP gate on the name and geometry (`ip_and_licensing.md` §3, §6) | the IP gate | process | the gate's build. Offline-batch provenance is `ip_and_licensing.md` §6.2's to define, before any shipped prop |
| C cost | turn time, snapshot bytes, and the tile, node and contact limits (`subcell_solids.md` §3.1) | the frame | process: B5's budgets | — |

Each `not_run` check has one strict red gate in the suite, `xfail(strict=True, raises=CheckUnavailable)`, where
`CheckUnavailable` is a type this harness defines. A precondition the gate needs raises something else. The gate
flips when its step lands.

**Prior art.** Maxim's `src/maxim/simulation/foundry.py::run_sem_protocol_tests` (the archived asset foundry, at
`origin/main` 16aaf664) judges generated SEM components "usable, useful, used". It takes component spec dicts, not
Entities, so it can't run on a region. Its test 4 (tool generation with a collision check) is adopted as part of T7.
"Used" is N6.

## 8. SpecId

One implementation, owned by `simcore.core.imagination` (proposed under `subcell_solids.md` §12's `SPEC_KEYS` row).
It is `ip_and_licensing.md` §6.1's digest of the migrated v1 form, with `version` and `role` in it, and the harness,
the scorer and the IP gate all call it. The spike's v0 function stays frozen for stage 1 only, and stage 1's ids are
never compared with v1 ids.

## 9. The scoring kit

The spike's scorer moves with:
- metrics registered by name;
- per-statistic generators;
- completeness, duplicate and split refusals;
- run headers checked against the tree;
- a `scorer_version` in its output, so a rescoring of a frozen run can't pass for its pre-registered numbers.

Contact and connectivity metrics call the engine's one contact rule (`subcell_solids.md` §4.1), never a scorer copy.
A regression comparison takes two headers and refuses unless they differ only in the declared variable:
- a model or engine change regenerates;
- a format change re-parses;
- a law change reruns only the battery.

Rescoring the spike's records under the current engine is the baseline for a later comparison, and an exploratory
analysis outside its pre-registration, labelled so.

## 10. Build steps

The mechanisms and their tests are in `docs/plans/checklists.md`, under "Generation harness". In brief:
- **H0, preconditions,** after the spike's results: PRs #50 and #51 and `phase1/torch-pilot` merged; the per-check
  costs measured at the spike's scene; this document's open contract items checked by a delta review.
- **H1:** the package, its gates and contracts, the client and the runner.
- **H2:** the scoring kit.
- **H3:** the battery and the engine-property suite.
- **H4:** the first consumer, stage 2's data job, with the verdict filter on its path.

## 11. Open questions

1. **The 0.05 m reference per spec, or on a stratified sample?** Extrapolated from Physics P4 (not measured past 30
   turns), U3 at 0.05 m costs about 5 s a spec, so 5,000 specs is roughly 7 hours. I recommend per spec, measured at H0
   first.
2. **`owner_lan` as "owner machines".** I recommend accepting it as a declaration, a known gap, as §2 records.
