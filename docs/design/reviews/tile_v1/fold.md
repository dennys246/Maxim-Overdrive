# Tile spec v1 review: fold status (O25)

Set by the fold-status reviewer, not the author, from the working tree of `phase1/tile-spec` on 2026-11-18 (on top of
f6afd66, uncommitted). Read: the six reports here; `tile_and_client.md` v2 (**W**, world side); `client_rendering.md`
v2 (**C**, client side); `docs/plans/checklists.md` (**CL**); `docs/plans/foundations_plan.md` (**P**); D29 in
`world_model.md` §0. Maxim claims read from `origin/main` 6fee7377 with `git show`.

**Key.** Prefixes: BF Bio-faithful, AR Architecture, PH Physics, WT Wire and trust, EX Executor, CR Client and
rendering; -B BLOCKER, -S SHOULD-FIX, -N NIT. Status: `fixed` (the docs now say what the fix needs; where = doc §),
`deferred` (named with a reason and a trigger or step), `rejected` (with the docs' reason), `open` (not handled, or
handled only in part or vaguely). "Owner Qn" means the fix is written as a proposal that still needs the owner's yes.

## BLOCKER and SHOULD-FIX

| id | gist | status | where |
|---|---|---|---|
| BF-B1 | Perceivers would read the wall-throttled wire frame | fixed | W §4.1, §8; CL step 5 |
| BF-B2 | No body heat before D28; a second body model would follow | fixed (owner Q5) | W §2.1, §2.2; CL step 5 |
| BF-S1 | NPC "perceives ignite from the log" | fixed | W §8 |
| BF-S2 | Facing exists only in the client | fixed | W §2.2 (`facing`); `turn` deferred, W §10 |
| BF-S3 | Locomotion not a body affordance; Maxim's is allocentric | fixed (owner Q6) | W §3.1, §3.3; P §3 lists OD-C11 |
| BF-S4 | The actor chooses watts | fixed (owner Q3) | W §3.2 (item power, `no_igniter`) |
| BF-S5 | Pilot receipt "success" vs slow-effect credit | fixed | W §3.2 (receipt meaning, OD-A16/OD-C5) |
| BF-S6 | One cylinder; head receptors under two coarse cells | fixed | W §2.1 (receptor volumes, Known gap) |
| AR-B1 | New mechanism has no layer; `engine.*` names retired | fixed | W §7 |
| AR-B2 | Movement bypasses the one pipeline | fixed | W §3.1, §3.3, §2.3 |
| AR-B3 | Burn energy has no destination | fixed | W §5.1, §6.4; D29 |
| AR-S1 | `player` special-cased; needs a body archetype | fixed | W §2.1 |
| AR-S2 | Actors in the frame break O23; no owner for the table | fixed | W §2.2, §4.1, §4.2 |
| AR-S3 | Bodies perceivable only through an omniscient table | fixed | W §2.1 (occupancy field, ANALOG) |
| AR-S4 | Two "blocked" predicates | fixed | W §2.3 |
| AR-S5 | Glow and fire encoded from cell means | fixed | W §4.2 (`surface_glow`, `burning`), §5.2 |
| AR-S6 | Engine/game split of data and client ignored | fixed | W §1.3, §7; C §7.1 |
| AR-S7 | Godot knobs in the Python engine | fixed | C §5.5 |
| AR-S8 | Movement vocabulary shaped by the camera | fixed | W §2.3 (integer `dir`) |
| AR-S9 | Spawn validation in the scene format is a layer inversion | fixed | W §1.3, §7 |
| AR-S10 | "Maximum only falls" cannot fail | fixed | W §6.4 |
| PH-B1 | Open air has no heat sink | fixed | W §1.2, §5.1; D29 6a |
| PH-B2 | `t_gone` convergence needs recession | fixed | W §5.2; D29 6c |
| PH-B3 | Glow thresholds the cell mean | fixed | W §4.2, §5.2, §6.3 item 4; D29 6b |
| PH-S1 | 3,600 s cap ~8× faster than the block burns | fixed (owner Q2, Q4) | W §5.3 |
| PH-S2 | Criteria count cells | fixed | W §6.3 |
| PH-S3 | Controls and item 5's second clause can't fail | fixed | W §6.4, §1.1 |
| PH-S4 | Pilot lost its footprint; "2× minimum energy" not a band gate | fixed | W §3.2, §6.3 item 7 |
| PH-S5 | Band gate applied to a continuous time | fixed | W §6.3 items 7, 8 |
| PH-S6 | "Identical on every machine" overclaimed | fixed | W §2.3; C §6.5 |
| PH-S7 | `crack`'s driver unspecified | fixed | W §5.2, §6.3 item 8 |
| WT-B1 | `move`/`move_to` fork protocol v0 and the log record | fixed | W §3.1, §3.3, §3.4 |
| WT-B2 | Ignite redesign changes the vocabulary unversioned | fixed | W §3.2, §3.4 |
| WT-B3 | Decoder hard-codes `glow`/`crack` scales | fixed | W §4.2; C §4 |
| WT-B4 | Client can't turn a pick into a region | fixed | W §3.2, §4.2 |
| WT-S1 | Refusal vocabulary incomplete; `busy` collides; NaN unreachable | fixed | W §3.4 |
| WT-S2 | Committed hand-written log vs the strict reader | fixed | W §6.2 |
| WT-S3 | New world-affecting data not in the log header | fixed | W §3.5 |
| WT-S4 | `move_to` unlimited and unbudgeted | fixed | W §3.4 (rate limit, slot, one plan per actor per tick); no numeric budget, only a B5 meter |
| WT-S5 | A stop can be dropped while paused | fixed | W §3.4 |
| WT-S6 | No first frame in a quiet world | fixed | W §4.2; C §7.5 |
| WT-S7 | Actor table and `tick` list undefined | fixed | W §2.2, §4.2 |
| WT-S8 | Two scene v1s; spawn migration | fixed | W §1.3; CL step 3b |
| WT-S9 | Guest refusal tests have no guest | fixed | W §3.4 |
| WT-S10 | Pilot lifetime float, keyed by region | fixed | W §3.2 |
| WT-S11 | Integers from GDScript unpinned | fixed | W §3.4; C §3, §9 |
| WT-S12 | Transport caps half-specified | fixed | C §4; W corrections list |
| WT-S13 | Catalogue hash missing; exact size gate | fixed | W §4.2; C §4 |
| EX-B1 | The exit needs physics no Phase 1 step builds | fixed | D29; W §5, §6.3; P row 6 |
| EX-B2 | Client has no region data | fixed | W §4.2; C §5.6 |
| EX-B3 | The golden gate has no machine | fixed | C §6.5; CL step 2 (P row 2's done-when not reworded: see EX-S1) |
| EX-S1 | Requirements with no step or the wrong step | **open** | W §11, C §12, CL added; but P rows 2, 5, 7, 9 not updated (see below) |
| EX-S2 | `check_plan.py` blind to this doc | fixed | `scripts/check_plan.py`; P §4, §5; check passes |
| EX-S3 | Observation 1 is a wish | fixed | W §6.2 ticks 42, 50 |
| EX-S4 | Two observations pass with mechanism deleted | fixed | W §6.4 |
| EX-S5 | Live run can't reproduce ticks | fixed | W §6.2 (stepped mode) |
| EX-S6 | Path walking underspecified | fixed | W §2.3 |
| EX-S7 | Rate limits drop the stop; `move` has no reply | fixed | W §3.3, §3.4 |
| EX-S8 | Rejection paths untested; order undefined | fixed | W §3.4 |
| EX-S9 | Frame-size gate contradicts channels; cadence | fixed | W §4.2 |
| EX-S10 | Crack goldens can't see the crack | fixed | C §5.4, §6.2 |
| EX-S11 | Exit runtime and tier gating unstated | fixed | W §6.5 |
| EX-S12 | Budget meters pass vacuously | fixed | C §8 |
| EX-S13 | Scenario goldens go stale silently | fixed | C §6.1 |
| EX-S14 | *To verify* items need a probe list | fixed | C §9; CL step 2 |
| EX-S15 | Cut-away test: no denominator, position or deletion proof | fixed | C §2 (but threshold lowered 95% → 90%, see Checks) |
| CR-B1 | B6 gate trusts Godot's exit codes | fixed | C §7.3; CL step 2 |
| CR-B2 | No region identity in the client | fixed | W §4.2; C §5.6, §6.4 |
| CR-B3 | No CI rendering context | fixed | C §6.1, §6.5; CL step 2 |
| CR-S1 | `DEPTH` formula by renderer | fixed | C §5.3 |
| CR-S2 | Raymarch cost 2–3× v1's | fixed | C §5.1, §5.2 |
| CR-S3 | Cut-away fails its own test; hides distant fire | fixed | C §2 |
| CR-S4 | Cracks sub-pixel at `t_crack` | fixed | C §5.4, §6.1 (G2), §6.4 |
| CR-S5 | GPU meter reads 0.0 | fixed | C §8, §9 |
| CR-S6 | CPU pick ignores the cut | fixed | C §5.6 |
| CR-S7 | Warning list partial | fixed | C §7.2 |

**Why EX-S1 is open.** The requirement-to-step tables exist (W §11, C §12) and CL now has sections for 2, 3b, 5, 6,
7, 8 and 9, but EX-S1's fix also said "update the plan rows' done-when to match", and the plan still contradicts the
spec:
- P row 7 still lists `act_result`; the spec replaced it with `intent_result` (W §3.3).
- P row 9 still says "grid plus scene spec"; W §11 and CL step 9 say the actor table and `body_key`.
- P row 2's done-when is still "the gate runs Godot headless and passes" with "one golden frame" in its scope; the
  golden needs the Linux Xvfb job (C §6.5).
- P row 5 doesn't mention the bodies, intents or the alley fixture it now owns (W §11), nor its new dependency on
  step 3b's scene v1.
- W §11's last line says "`checklists.md` has no sections for steps 3b, 5, 6, 8 or 9; the lines to add are in this
  fold's hand-off note, not edited here". CL now has them. The sentence is stale.
- Unowned still: the `data/rigs/*.yaml` comment correction and the tier fields leaving the rig files (EX-S1's
  "no owner" row). The corrections list says "each lands with the PR that touches the file", which is no step.
- Step 6's done-when (P row 6) is not "obs. 3 and 8 pass at three grids" as EX-B1 asked; CL step 6 carries the
  reference run, so this is a residual, not a reopened BLOCKER.

## NITs

- **BF (4):** N1, N2, N3 folded (W §1.2/§8, §3.4, §2.1). N4 deferred to the boundaries PR (W §10), with a trigger.
- **AR (5):** N1 (`dir: … | null` in canonical params, `motion` enum), N2 (C §5.1 includes), N3 (W §7), N4, N5
  (W §3.2) all folded.
- **PH (5):** all folded. N1 moot (glow now a skin temperature in °C); N2 C §5.3; N3 W §6.2; N4 W §2.3 (exact
  target). N5 folded in W §1.4 and §6.5, but with a wrong number (Checks, 2a).
- **WT (8):** all folded. N1 moot (`point_mm` now integer); N2 C §3; N3 W §6.2; N4 C §3.1; N5 W §3.1; N6 C §6.1; N7,
  N8 W §4.2.
- **EX (7):** all folded or moot. N1 moot (new normalisation, 1.0% stated correctly); N2 moot; N3 C §5.5; N4 C §6.3;
  N5 C §7.2; N6 W §6.3; N7 W corrections list.
- **CR (7):** all folded. N1 C §5.1, §5.5; N2 C §2; N3, N6 C §3; N4 C §5.3; N5 C §3.1; N7 C §4, §7.3.

## Checks

### 1. OD-C11's Maxim citations (W §3.1, §8, §9 Q6)

Verified on `origin/main` 6fee7377 (dated 2026-11-17):
- `src/maxim/_data/components/bodies/base_humanoid.yaml`, `legs` modulator, affordance `move`: `params: {direction:
  str, speed: str}`, description "Move in a direction (north/south/east/west) at a speed (walk/run/sneak)",
  `requires: {integrity: 0.1}`. **True.**
- `src/maxim/_data/components/bodies/minecraft_player.yaml`, `avatar` modulator (abstract), affordance `move_to`:
  `params: {x: float, z: float}`, "Pathfind to the given x/z coordinates". **True.** `avatar.turn {degrees: float}`
  (BF-S2's claim) is also there.
- `OD-C11` appears nowhere in Maxim or in this repo's roadmap, so the id is free. P §3 lists it as "proposed, tile §9";
  it is described in W §3.1 and asked in §9 Q6.

What's imprecise:
- W cites `_data/components/bodies/…`, not the repo path `src/maxim/_data/components/bodies/…`, and gives
  `minecraft_player.yaml` with no directory. Two other files share these names:
  `src/maxim/_data/components/npcs/base_humanoid.yaml` (no `move` affordance) and
  `scripts/survival_world/body_spec_minecraft_player.yaml`. The OD-C11 draft must give full paths.
- W writes `direction: north|south|east|west` as if it were an enum. In Maxim it is a free `str`; the compass words
  are only in the description. Say so in the draft, since an LLM can pass any string.
- BF-S3 also named bench57's signed world offsets as sensors (`minecraft_bench57.yaml`) as the same oracle. W drops
  that. Not wrong, but the proposal is weaker for it.

### 2. Numbers against the reviewers' verified numbers

**a. Contradiction: W §1.4 "with caching, about 1.6 ms at 0.1 m is a projection from world_model §9".** The physics
reviewer's arithmetic (PH-N5) and v1 both give 1.4 ms: world_model §9's cached 3.9 ms on the 640,000-cell tile ×
230,400 / 640,000 = 0.36 → 1.40 ms. Nothing in either doc supports 1.6. Fix it to 1.4 or show the arithmetic.

Not contradictions, but things the next reviewer should know:
- **b. The cut-away gate was lowered without a reason.** v1 and CR-S3 had ≥ 95% visible. C §2 now says ≥ 90%,
  while its own derivation says the 0.3 m stump "hides at most the feet's edge". A threshold set below what the
  derivation predicts, before any measurement, is the loosening CLAUDE.md forbids. Restore 95% or derive 90%.
- **c. The diffusion-length argument is for the old cap.** W §1.1 keeps PH's "about 0.28 m in an hour" for
  `crate_far`, but the cap is now 36,000 s: √(2.2×10⁻⁵ × 36,000) ≈ 0.89 m (derived, PH's α). Still far below 2.68 m,
  so the conclusion holds, but the stated figure is for a run that no longer exists.
- **d. Re-derived, not contradicted:** C §5.2's 108-cell floor ray (CR's 118 started at z = 4.8 m; C starts rays at
  z = 4.4 m, as CR itself recommended). Checked: 4.0/0.643 = 6.22 m, 3.37 m in x and y → 34 + 34 + 40.
- **e. Checked and consistent with the reviewers:** cell counts, 59,312 solids, 23–29 MB, 0.59 / 4.5 / 38.3 ms,
  `stable_dt` 46.9 s, 129.6 kg, 1.61 GJ, 67%, ≈ 7,300 K, 27,700 s and 18,500 s, 58 kW, 29 kW/m² and 53 kW, 2.68 m,
  τ = 12,900 s, 36 B per actor, 7 B per cell and 1,612,800 B, 29% for `temperature_c`, 3,600 B of bricks, 4,800 walk
  nodes, 208 pick steps, 72 px/m, 0.72 px and 2.9 px grooves, 1,015.9 mm to (5500, 2925) with arrival at tick 57,
  (5080, 2000, 400) at tick 42, Godot's defaults (65,535 B, 4,096 packets), the upload timings, 10.9 ms first update,
  the GPU meter at 0.0, the `DEPTH` formula, and the 16 s / 5.4 min / 46 min run costs.
- **f. One thing to watch.** 1.4 ms for "six channels" (C §4) counts the six wire channels. The brick occupancy texture
  (C §5.2) is a seventh upload per frame. It is tiny, but the meter row should say what it counts.

### 3. Process note (not a finding status)

P row 0d still budgets the tile spec at "≤ 6,000 words" in one document. The fold split it into W (5,904 words) and C
(4,069), about 9,970 in total. Each half is under O22's 6,000 for a new document, but together they are about 66% over
the row's budget. Splitting a document so each half fits the per-document cap is a way round O22. The owner should
accept the split explicitly and amend row 0d, or the docs should shrink.

## Verdict

No BLOCKER is open. Every one is `fixed` in the text, but four rest on proposals that still need the owner's answer:
BF-B2 (Q5), PH-B1/PH-B2/PH-B3/EX-B1 (on D29, already recorded as the owner's), and the exit cap (Q2, Q4). One
SHOULD-FIX is open (EX-S1: the plan rows weren't updated and W §11 is stale), and there is one wrong number (1.6 ms).
Fix those, and settle the 90% gate and the word budget, before the delta review.
