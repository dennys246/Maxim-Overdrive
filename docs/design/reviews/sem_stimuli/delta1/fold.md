# Fold table: `sem_stimuli.md` v2 → v3 (delta round 1, 2026-11-21)

**The author's table, not a verdict.** One row per delta-1 finding that was open or new: what v3 did and where. The
**Status** column is the reviewers' (O25): every row reads `open` until a reviewer reads v3. "proposed:" marks the
author's suggested deferral or rejection, with reason and trigger. Findings the reviewers already set `fixed`,
`deferred` or `rejected` aren't repeated; their conditions are honoured (below).

**The owner's rulings (2026-11-21)** govern several rows: D12 provisional, re-costed with a capped refresh schedule
and re-ruled on a measured number; D14, D5 (c) kept as the contract with delivery at the cognition rate until a body
has a pain path; M16 merged into M4. v3 is 5,997 words: v2 was rewritten shorter to make room.

**Checked before folding** (lesson 26). Measured in the session scratchpad, on L3's column
(`_durable/sem_research/scratch/skin.py`, 45 nodes, Δt 0.1 s, from steady state):
- **The plant (Exec B1):** one ulp on `H_CONV` first moves a node at tick 152 (2 kW/m²) and 120 (20 kW/m²), never in
  200 ticks at zero flux. 10⁻¹², 10⁻⁹ and 10⁻⁶ relative all move one at tick 0. The Executor's "tick 42 at 20 kW/m²"
  didn't reproduce exactly (the mesh or start may differ); its conclusion did.
- **Rest (Phys S2):** with L3's outer boundary (h 8, ε 0.95) the surface rests at 32.4 °C. The reviewer's "37 °C"
  holds only with no loss; L3's column had the loss, and v2's text omitted it.
- **Join (Phys S3):** a column started uniform at 37 °C comes within 0.1 K of rest after 1,060 s (the reviewer's
  estimate was ~1,200 s).
- **Short write (Conc F5):** a non-blocking macOS Unix socket took 8,192 of 20,000 bytes, then raised
  `BlockingIOError`; the socket stayed healthy.
- **Digest form (DP2-S4):** the reviewer's `digest_form.py` re-run gives 2.94 µs raw against 110.7 µs JSON.

Checked by reading:
- **The overlap gate (Conc F1)** can't fail in replay: step 5 is empty there, so overlap on and off run the same
  code. DP's "checked, can fail" note disagrees; the author sides with F1.
- **Chain localisation (DP2-N1):** a chain stored every N ticks localises to the window, by construction.
- **Import-linter 2.6 `protected`** (venv source): direct imports only; allowed importers subtracted for every
  descendant; unmatched allowed importers silently empty.
- **Maxim at `043eab8f`:**
  - `body.py:258` `evaluate_failures` drifts on `time.time()` (`:293-297`);
  - `percepts.py:122` calls it alone (`agentic_runtime.py:605` is a wiring comment, so the draft doesn't cite it as a
    call);
  - `spec.py:1035-1038` no-op; `audio_localization.py:733-762` stores no owner;
  - `body.py:674-682` and `backends/cerebellum_modulator.py:260` write `vital_metrics` directly;
  - `concept_extractor.py:542-560` and `agentic_runtime.py:255` start threads.

**Unverified, folded only as rules that are safe either way:** DP2-S2's SuperLU ordering claim (v3 bans the
libraries and solves per component anyway); Phys S5's penetration numbers (v3 adds the sub-mesh and makes
object-side nodes a convergence axis); DP's derived costs (73–90 ms, 365–450 ms), taken as **D** from the reviewer,
not re-measured.

**Deferred and rejected conditions honoured:**
- Conc S6 (d): named as the fallback in §11.3.
- DP-S8: overdraft as a ledger residual, §3.1.
- Exec B1 (3): an events plant with the first producer, §5.
- Wire S3 and S5: triggers unchanged.

## Executor

| Id | v3 | What v3 did | Status |
|---|---|---|---|
| B1 | §5 | plant is 10⁻¹² relative (measured); test finds the first differing tick and requires the per-tick lanes to name it; order plant inside `reduce.py`, `join` unchanged; events plant with the first producer | open |
| S6 | §3.3, §4.4 | the modulator is named, `overdrive_world`; every affordance on it goes to the outbox | open |
| S8 | §6.3 T9 | T9 runs both divisors from one fixed intent stream | open |
| N8 | §4.2 | refuses writable arrays, as `CellFrame` does, and arrays whose base chain doesn't end in `bytes` | open |
| X1 | §4.4 | the owner check is by value: before the body step, each bound sensor is compared with what was pushed. The thread check runs at every park. Not done: the reviewer's second comparison after the body's own update | open |
| X2 | §7.3 | `AGENTS_SURFACE` and the equality test; `protected` contracts allow `simcore.adapters` wholesale, narrowed by skip-layer; a test that every allowed importer exists. The composition module is named by role (`Simulation`'s, layer 6), not by path, since 5a names it | open |
| X3 | §3.2, §7.1 | `Binding` in `core/stimuli/schema.py`, validated when `join` applies; an invalid join is refused before any reduction; the worker keeps only Maxim-side checks | open |
| X4 | §6.3 | table repaired; "T2 merged into T1 in v2" | open |
| X5 | §4.1 | the overlap requires `apply_tick > observed_tick`, which the lane minimum enforces | open |
| X6 | §8 | the skin row says one substep per tick; a +30 ms row near a fire; the contact system is listed as unmeasured | open |
| X7 | §11.1 | schema, frame, reduce, contracts and checks land together with `tissue_temperature`, their first caller | open |

## Architecture

| Id | v3 | What v3 did | Status |
|---|---|---|---|
| A-B2 | §5 | digest in per-row lanes keyed by `(name, derivation_version)`; replay compares unchanged lanes and refuses only on a changed bound lane; plants for an unbound add (green) and a bound bump (red) | open |
| A-S3 | §7.1, §4.1 | one owner, `core/body/contact.py`, at step 3: skin through the store's window, object through the solid law's exchange API, one antisymmetric entry per substep; a fifth writer class for `boundaries.md` §6.4 | open |
| A-S8 | §7.3 | as X2 | open |
| A-S10 | §11.1, §5 | each format gets a version and gate row; the §7.4 lints, YAML digest, worker check and save state are each assigned a step. **proposed: deferred** for the `foundations_plan.md` rows: the plan is at its 2,500-word budget, and 5a's "composition note" and 5b's "bodies" already name the vehicles. Trigger: the PR that opens 5a | open |
| A-S12 | §7.1; tracker | tracker reads "units (ranges are Maxim's transduction)"; §7.1 supersedes `boundaries.md` §2.2's map by name, with a layer per module | open |
| A-N4 | §7.4 | the exemption is narrowed to the binding loader; the lint's blind spots are stated | open |
| A2-S1 | §3.1, §7.1, §7.3 | `core/body/spec.py` holds plain data; `CORE_PUBLIC_SURFACE` gains `body.spec`, `stimuli.schema` and `stimuli.frame` only | open |
| A2-S2 | §7.4 | a `perceivable` flag, default false; completeness refuses non-perceivable `reads` | open |
| A2-S3 | §3.2 | as X3 | open |
| A2-S4 | §11.1 | 5a reserves only log slots, seams and the recursive module list; the frozen types land with their caller | open |
| A2-N1 | §7.1 | `reduce.py` split out | open |
| A2-N2 | §7.1 | tissue reaches models only through the `FieldReader`, over a perceivable point container | open |
| A2-N3 | §6.3 | table repaired | open |
| A2-N4 | §7.3 | says `protected` can't scope submodules and skip-layer narrows instead; the allowed-importers-exist test | open |

## Wire integrity and trust

| Id | v3 | What v3 did | Status |
|---|---|---|---|
| S4 | §7.3 | `agents-reads-body-frames` sets `allow_indirect_imports = false` | open |
| W1 | §4.4, §4.2, §6.2 | `execute` returns a fixed `pending`; receipts `(pid, kind)` ride `BoundFrame` under `STIMULUS_SCHEMA_VERSION`; T7 and T12 cover the return and the receipts | open |
| W2 | §6.2 | precedence `malformed`, `limit`, `unavailable`, `applied`. v1 merges unperceived and out of reach into `unavailable` (ANALOG) until a vision row defines perception from A's frame. T11 sweeps an unavailable target. Mapping `StructureModulator`'s refusals goes to `phase1/agents` under S5's accepted deferral | open |
| W3 | §3.2 | as X3; replay reads `join` through the same gate | open |
| W4 | §3.2, §4.2 | `bindings_digest` in `welcome` and every `BoundFrame`; the worker refuses a mismatch | open |
| W5 | §6.3 | table repaired; T2 noted | open |
| W6 | §2.2 | the v1 row's `valid` range and rounding freeze with the tissue law's PR | open |
| W7 | §5 | version and gate row for the body instance, binding table, `BoundFrame`, receipt and save body state, each with its step | open |
| W8 | §3.1, §6.1 | convection's one receiver is the skin's outer boundary; the supersession cites `boundaries.md` §4.2 | open |

## Concurrency and lanes

| Id | v3 | What v3 did | Status |
|---|---|---|---|
| S9 | §4.1 | step 4 is the simulation lane's; a host pump encodes, sends, receives and stamps; scatter-gather, so the slowest worker sets the wait; push and body step sit inside the ceiling. Not quantified: the per-tick critical path, which waits on the body step's measurement (M4) | open |
| F1 | §4.1 | the gate runs live with stub workers, two delay schedules, overlap on and off, then replay; planted merge during step 6 | open |
| F2 | §8, §6.1 | scatter-gather stated; §6.6's levers superseded by name; a B5 row at 1× and the dial's maximum, the highest sustainable dial, hung kills per 1,000 parks. **proposed: deferred** for the numbers: the body step is unmeasured until M4. Trigger: M4's answer | open |
| F3 | §4.2, §4.6, §11.3 | events cover "since this NPC's last delivered frame", valid at any divisor; the fallback (d) is named and priced against a full step | open |
| F4 | §4.2 | events stamped `(tick, offset_us)`, delivered in the first frame after; latency stated | open |
| F5 | §4.3 | a partial send goes to a per-channel outbox; only ceiling expiry is `hung`; the budget sits below the socket buffer; the one-byte reader test (measured) | open |
| F6 | §4.4 | thread set checked at every park against post-build, citing OD-EA7; planted at the third step | open |
| N-a | §4.1 | merge is step 7, after the join; the ceiling is judged on pump stamps | open |
| N-b | §8 | the counter gate reads parks from the log | open |
| N-c | §4.5 | a restart's first frame carries no events; the dropped count is logged | open |

## Physics and resolution

| Id | v3 | What v3 did | Status |
|---|---|---|---|
| N1 (r1) | §8 | the basis is 58 points, the 0.1 m tier, light load, one emitter, stated once | open |
| N5 (r1) | §3.1 | perfusion is a skin–core exchange; metabolism a source into the core; only the ambient is a reservoir | open |
| S1 | §2.3, §11.1 | occlusion against authored primitives in metres; volume-fraction transmittance after B28; B28 is a prerequisite of the irradiance law; a grid-only march is the planted red case | open |
| S2 | §2.3 | outer boundary: convection plus radiation to ambient, immersion convection per point; rest measured at 32.4 °C; the closed-form steady profile | open |
| S3 | §2.3, §4.5 | join and restart at the steady profile by a direct solve (transient measured, 1,060 s) | open |
| S4 | §2.3, §7.4 | v1 chooses (b): no cell exchange; strict red face-contact and face-emission gates; a Known gap with P1's number; face skins as the named fix | open |
| S5 | §2.3 | an object-side sub-mesh refined to the substep's penetration depth, remapped conservatively; object-side nodes as a convergence axis | open |
| S6 | §8 | motion refresh costed (every tick ~365–450 ms) and bounded by the capped schedule (owner, D12) | open |
| S7 | §2.3 | contact onset and release are interpolated between tick poses; radiation keeps the one-tick hold | open |
| N1 (new) | §2.3, §5 | K tolerance derived from a stated Ω error; both in the header | open |
| N2 | §11.2 | Weaver–Stoll's figure tagged **M** | open |
| N3 | §3.1 | as N5 (r1) | open |
| N4 | §6.3 | the fingertip test, once a pain path exists; until then a build check refuses a mean on `noci_heat` | open |
| N5 (new) | §11.2 | angular spread is the maximum over the emitter's quadrature points | open |

## Determinism, replay and performance

| Id | v3 | What v3 did | Status |
|---|---|---|---|
| DP-S5 | §8 | a moving-crowd row (every tick ~365–450 ms); counter thresholds in the B5 row | open |
| DP2-B1 | §8, §10 | one stated basis; the 100-NPC forecast corrected (~2.5–2.9 s stationary, **D**; 2.7–3.8 on v2's basis); the capped schedule with cost `10·K·c` and staleness `⌈P/K⌉`, worked at K = 116 and 290; D12 provisional, re-ruled on a measured outcome bound; failure paths named | open |
| DP2-S1 | §8, §6.1 | rows for substeps, contact (unmeasured), the body step (unmeasured, critical path) and the emitter multiplier; §6.6's levers superseded by name; whether 20× is a target follows the B5 row | open |
| DP2-S2 | §7.2, §6.3 | contact solved per connected component in canonical order; per-point substeps; clusters never span bodies; the lint extends to `scipy.linalg` and `scipy.sparse.linalg`; T11 plants all three | open |
| DP2-S3 | §5 | the save holds all carried `core/body` state; the controller is memoryless; the save-load test, planted with an omitted reference pose | open |
| DP2-S4 | §5 | lanes hash dtype, shape and little-endian bytes, length-prefixed; the config canonicaliser is for the header only | open |
| DP2-N1 | §5 | "first bad interval"; the first bad tick needs a reference run | open |
| DP2-N2 | §4.2 | `local_id` is assigned after sorting by a world-side key | open |
| DP2-N3 | §6.3 T11 | "B reaches A only through world state" | open |
| DP2-N4 | §8 | an absolute target (~140 ms per world second at 10 NPCs) in the B5 row | open |

## Bio-faithful integration

| Id | v3 | What v3 did | Status |
|---|---|---|---|
| SF-1 | §0, §4.6, §10, §11.3; roadmap Phase 4 | §0 says it in the reviewer's words. The owner's D14 keeps D5 (c) as the contract, runs delivery at the cognition rate until a pain path exists (Known gap, T16 strict red), and gates Phase 4's fire scenarios on a pain path. That is option (c)'s "Known gap", not (a) or (b) | open |
| SF-2 | §3.3 | region modulators with vital sub-sensors, affinities, weights and failure modes (ANALOG map); a planted-burn build test, red on a stripped modulator | open |
| SF-3 | §9 M4; `embeddable_agent_DRAFT.md` §7 | M16 merged into M4, asked about `evaluate_failures` (verified), the LLM-only evidence dropped, search terms added | open |
| N-1 | §3.3 | an Overdrive port, `scripts/lint_body_rest.py`, lands with the first body, planted off-centre | open |
| N-2 | §9 M15 | relabelled **New**, with the terms searched and the encoder route's closure cited; downstream habituation tagged ANALOG | open |
| N-3 | §6.3 | table repaired; negative controls on T3 and T11; T15 with a pass rule | open |
