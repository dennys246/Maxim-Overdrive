# Offline generation harness: plan (draft, 2026-11-22)

**Status.** A plan, approved in direction by the owner (2026-11-22); not built. It lands after the spec generator
spike's results, and its first consumer is stage 2 (generalise at the second use). Until then the spike's code stays
in `spikes/specgen/` (PR #50), frozen while its runs go.

**Scope.** Imagined-object specs generated in bulk, offline, by local models, and the checks every generated object
must pass before anything uses it. Runtime imagination by an NPC is not this: it goes through the inference gateway
under a thought's deadline (`npcs_and_sem.md`, `inference_placement.md`). This harness is the content pipeline's
offline half, like a game's baking tools.

## 1. Why

We will generate often:
- **stage 2's training and evaluation data** (the spike's plan, `docs/design/research/specgen_spike/plan.md` §6);
- **regression checks** whenever a model, the engine build, the spec format (`subcell_solids.md` §11.2, PR #51) or a
  law changes: rerun a fixed prompt set and compare;
- **possibly pre-generated props** for shipped scenes, which then become game content under
  `ip_and_licensing.md` §6.

Each of these needs the same three things the spike built once: a resumable batch runner that proves its engine, the
grammar-plus-feedback generation protocol, and the scoring kit. Each also needs something the spike never had: a
standard test of whether a generated object works for everything that will use it (§5).

## 2. Rules it keeps

- **Only `place` writes the world.** Generated specs enter only through `simcore.core.imagination.place`, which
  validates them. The harness never writes cells, never builds a region by hand, and never imports `simcore.core`'s
  private names.
- **Generation is not reproducible across machines; its committed records are the truth.** A run's identity is its
  header: the frozen inputs' hashes, the engine's measured build and weights digest, the code commit and the data
  hashes. Rescoring reads the records; it never regenerates.
- **Pre-registered experiments freeze the harness, not the other way round.** A spike pins a harness version and a
  config digest in its freeze manifest, as the spike pinned `arms.yaml`. A harness change never alters a frozen run.
- **Local first (O58).** Batch jobs run on owner machines. A hosted model is only ever the player's opt-in through the
  gateway (IG §6), and an owner batch job is not a player session (§4, Q4).

## 3. Where it lives

**`src/maxim_overdrive/generation/`, the game layer** (`boundaries.md` §2.1–§2.2, the `layers` contract):
- **It is content production for this game:** its prompts, its prop sets and its training data are game content
  (`boundaries.md` §2.1's table). The engine stays ignorant of it.
- **It imports the engine only through public surfaces:** `imagination.place`, `Simulation.from_scene`, the applier,
  `adapters.sem`'s `to_maxim_entity`, `protocol.encoding.snapshot`, `digest`, and the loaders. The skip-layer rules of
  `boundaries.md` §2.2 hold it as they hold any caller.
- **Not `simcore.core`:** the core has no IO and no clock, and the harness is all IO.
- **Not `scripts/`:** scripts are repository tooling. The harness is shipped-path code with a CLI
  (`python -m maxim_overdrive.generation`), measured by coverage like the rest of `src/`.
- **Not Maxim's experiment harness:** that one is for Maxim's pre-registered experiments (`npcs_and_sem.md` §10). This
  is not a Maxim experiment, and game runs never go on Maxim's ledger.

## 4. Inference: the gateway's contract, not a second one

The harness asks for completions through the inference contract the game already designed. It doesn't get a second
endpoint scheme:
- **Functions and envelopes:** a batch job declares a function and its envelope (IP §2.1), including `thinking`.
  The spike found that the thinking switch is necessary (lesson 36).
- **Placements:** `placements.yaml` names the server, its egress class (`loopback`, `owner_lan` or `third_party`),
  model, tier, `context_per_slot` and `max_in_flight` (IP §2.2). Endpoints and credentials stay in `endpoints.yaml`,
  which only the gateway reads (IG §8). So the harness never holds a URL, which is the spike's rule made structural.
- **The channel:** requests go through the gateway's channel and classification (IG §3, §5), and the harness acts on
  IG's outcome classes rather than raw HTTP codes. The spike's overflow rule (only `exceed_context_size_error` is
  `truncated`) becomes a classification row there, not harness code.
- **Batch settings live in placements, not in requests:**
  - reproducibility needs one slot (`max_in_flight: 1`);
  - throughput wants more, so a job states which it is.
  - The spike's engine proof (exact build, context, slots, measured weights digest) is checked against the
    placement's declared values. IP §2.2 declares a weights digest "which is not checked"; the harness needs it
    checked (Q3).

**Until the gateway exists** (`engine.adapters.inference` is not built, `boundaries.md` §2.2), see Q2.

## 5. The use battery

A generated object is usable for a purpose only if it passes that purpose's checks, run on the real path. The model
is Maxim's own standing tests at `origin/main` 16aaf664:
- **`tests/substrate/test_components_smoke.py`,** for every bundled component:
  1. instantiates a fresh `Entity` through `ComponentRegistry`;
  2. wraps it in an `Embodiment` and reads every scalar sensor;
  3. calls `evaluate_failures()`;
  4. drives a durability failure and checks that it publishes a `PainSignal`.

  It is a drift guard: "sensors that silently read as None, failure modes that never fire".
- **`tests/substrate/test_sem_execution_production.py`** drives the same cascade through the real executor and
  `ModulatorAffordanceTool`, with no hand-rolled harness.

The battery does the same for each accepted spec. It has a version, it records a verdict per check, and a consumer
takes only specs whose needed checks passed.

| Check | What passes | Consumer | Exists today |
|---|---|---|---|
| U1 placement | `place` accepts at the truth grid, inside the world | everything | `place`; the spike's scorer bounds check |
| U2 representation | the same verdict and class at 0.2, 0.1 and 0.05 m, judged in µm (`subcell_solids.md` §2) | physics, shipped props | pattern in `tests/test_cross_tier.py`; new per spec |
| U3 physics smoke | some turns at two grids: every field finite, temperatures bounded, integrity in [0, 1], the outcome class (breached, burning) the same; the energy ledger closes once `fire_solid.md` §5.4's ledger lands | physics | new; the ledger isn't built |
| U4 fire | `kindle` on the object (`torch_pilot.md` §3 on `phase1/torch-pilot`, from 6.1b) ignites only if it is fuel, and no fire lands on air | fire | the spike's `burn.py` (M5, today's `Ignite`); new once `kindle` lands |
| U5 SEM entity | region → `to_maxim_entity` → a real Maxim `Entity`; wrapped in `Embodiment`, every sensor reads finite; `evaluate_failures()` runs; a strike through the applier moves `integrity` | NPCs | `tests/test_sem_bridge.py` (one region); new per spec |
| U6 SEM production path | an NPC's affordance call reaches the object through Maxim's executor and `ModulatorAffordanceTool`, as Maxim's production test does | NPCs | new; needs tier A's embeddable agent (roadmap Phase 3) |
| U7 wire | the frame's snapshot (`protocol.encoding.snapshot`) holds the object's channels, and the client decoder accepts it (`client_objects.md` §3) | the client | Python encode and the client fixtures exist; object tables are new (`subcell_solids.md` §10, S6) |
| U8 determinism | placing the spec twice gives bit-identical digests (`core/digest.py`) | replay, saves | new, small |
| U9 replay and save | an intent log containing the `imagine` replays to the same digest; a save round-trips | replay, saves | new; waits for the intent log (B2, step 5a) and save v0 (B4, step 9) |
| U10 support | the spec meets D33's placement rule; statics holds or fails it the same way at each grid | physics | new; waits for `subcell_solids.md` S4 |
| U11 provenance and IP | SpecId, licence and the IP gate (`ip_and_licensing.md` §3, §6) | shipped props | the spike's SpecId; the gate itself is new |

**Two rules make this a standard and not a one-off.** Each check that waits on an unbuilt step is a strict red gate
for that step, not a skip. And when a consumer's contract changes (a law, the wire, the SEM mirror), its check changes
in the same branch, as Maxim's smoke test is the drift guard for its components.

**The spike's results are not re-judged.** Running the battery over the spike's committed records is an
**exploratory analysis outside its pre-registration**. It is labelled so in its report, and it never changes the
spike's metrics or §6 decision.

## 6. What moves from the spike, and how

| Piece | Spike file | Moves as | Changes |
|---|---|---|---|
| Resumable JSONL with identity headers, torn-line repair, completeness | `generate.py` | as is, generalised over the record type | header keys become a declared list per job type |
| Engine proof | `generate.py::check_server`, `check_weights` | redesigned | checked against the placement (§4), not `arms.yaml` |
| Windows, log masking | `run_window.sh` | redesigned | a Python scheduler with windows in a versioned file; the gateway's log (IG §2) replaces masking |
| Reply classification and the A3 loop | `protocol.py` | as is, configured | a versioned job file (`schema.py`'s `Format`) replaces `arms.yaml`'s hard-coded protocol; spec v1 (`subcell_solids.md` §11.2) replaces v0 |
| Bootstraps, per-statistic generators, completeness, paired Δ | `score.py` | as is | metrics register by name, so a job declares which it computes |
| Blind labelling | `labelling.py` | as is | |
| Geometry metrics (contact graph, SpecId, raster, Vendi) | `geometry.py` | as is | judged in µm per `subcell_solids.md` §2.1 |

## 7. Build steps

Each step is its own branch with a review round (Executor, Architecture, Wire integrity, Trust boundary, plus
Bio-faithful for H3), and a closed set of tests written first.

- **H0, the design review of this plan's contract,** once the spike's results are in. They decide what the runner
  must handle: how often retries fire, and the per-sample cost.
- **H1, the runner and protocol.** Tests:
  - resume after a kill at every byte offset of the last record (a property test);
  - a header that differs in any declared key is refused;
  - the engine proof refuses each mismatched placement field;
  - every gateway outcome class maps to one record class;
  - the job file refuses unknown versions and keys.
- **H2, the scoring kit.** Tests:
  - each statistic's interval doesn't change when other inputs are added;
  - incomplete or duplicated data is refused;
  - a pinned digest of the scorer's output on a committed fixture.
- **H3, the battery, U1–U5 and U8.** Tests:
  - each check is planted to fail once (a spec built to break it) and goes red;
  - a battery run is bit-identical under two hash seeds.

  U6, U7, U9, U10 and U11 arrive as strict red gates, flipping with their steps.
- **H4, the first real consumer:** stage 2's data job, or a regression rerun of the spike's prompt set on a new model.

## 8. Open questions for the owner

1. **Where it lives.** I recommend `src/maxim_overdrive/generation/` (§3). The alternative, a separate tools package,
   would sit outside the import contracts.
2. **Before the gateway exists.** Either wait for `engine.adapters.inference`, or move the spike's direct llama-server
   client in as a marked band-aid, `TEMPORARY(phase4/…)`, listed in the roadmap and removed when the gateway lands. I
   recommend the band-aid only if stage 2 starts first; otherwise wait.
3. **Checking the weights digest.** IP §2.2 declares it for `loopback` and `owner_lan` but doesn't check it. I
   recommend IP check it: the spike measured it on the mini in seconds per run. That is a change to IP, made by its
   owner section.
4. **Hosted models for batch jobs.** I recommend none: owner batch jobs stay local (O56's rule, extended). A hosted
   model would need its own ruling and a spend cap (IG §8).
