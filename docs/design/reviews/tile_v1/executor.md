# Executor lens: `docs/design/tile_and_client.md` at f6afd66

**Checked and true:** `docs/architecture.md:20`; `MaterialGrid.empty`'s whole-cell check; wood id 4 (degrades from
250 °C), concrete from 300 °C; `GLOW_START_C`/`GLOW_FULL_C`; `WOOD_FLAME_C` (in `tests/test_cross_tier.py`, not
`world.py`); `test_cross_tier.py::SCENE` and its strict red gate; the 538 / 613 °C peaks; heat.py's insulated
boundary; on act-validation `Scene.from_dict`'s keys, `SCENE_VERSION = 0`, `_check_no_solid_overlaps` (strict `<`),
`parse_action`, `_ignite`, `data/world/actions.yaml`, `ActionLimits.load`; realtime §2.1, §2.2, §7; boundaries
`engine.*` and §4.2; world_model §9's numbers. All the spec's arithmetic holds. Wrong: `research/states_of_matter/
architecture.md` needs its `docs/design/` prefix, and it says partial updates are "likely whole-texture".

---

## BLOCKER

### EX-B1. The exit needs physics that no Phase 1 step builds
`tile_and_client.md::7.3` (observations 3 and 9), `::6.4`, `::2.3`; `foundations_plan.md::§2` step 6.

Step 8 is done when "the exit scenario passes automatically". Three of its observations rest on laws that step 6's
row ("fuel by volume overlap, a burn law, burnout, material table v1") doesn't contain, and that D26 moved to
Phase 2 ("fuel recession and pyrolysis"):
- **Glow (obs. 3)** needs ≥ 8 crate surface cells at `glow` ≥ 26. The measured peaks are 613 °C at 0.1 m (`glow`
  23) and 538 °C at 0.2 m (`glow` 3), because wood degrades away from 250 °C. §6.4 makes it "depend on step 6's
  surface law" giving char or embers. Step 6 has no surface or char law, and its done-when doesn't name glow.
- **Convergence (obs. 9)**: "`t_gone` agrees with the 0.05 m reference within the band gate." world_model §3 P3
  measured burn-away diverging by grid without sub-box recession: 0.205 / 0.268 / 0.311 of the mass left against an
  exact 0.370. Sub-box recession is "fuel recession", which is Phase 2. The band gate (world_model §3) is defined
  for binary outcomes as a width of the *input* range; it gives no tolerance for a time like `t_gone`, so obs. 9
  has no threshold at all.
- **The pilot (§2.3)**: "Step 6 owns the pilot's physics (area-overlap deposit, world_model §3)". Area-overlap
  ignition was world_model §10 PR 8a (`fuel-surface`), the same PR as recession. Plan step 6 doesn't list it. P2
  measured a 2 kW corner pilot lighting the crate at 0.05 m and never at 0.2 m, so without it the P that is "≥ 2×
  the reference grid's minimum" may not light every grid.

*Failure:* step 6 meets its own done-when, step 8 runs the scenario, obs. 3 never fires (`t_glow` doesn't exist),
so obs. 6 fails, and obs. 9 can't be evaluated. Step 8 has no route to done except loosening the tests, which
CLAUDE.md forbids.

*Fix:* add a blocking owner question to §12. Either (a) put area-overlap ignition, sub-box recession and a char
surface temperature law into step 6, amending D26 by name, and make step 6's done-when "obs. 3 and 9 pass on the
alley at 0.2, 0.1 and 0.05 m"; or (b) restate the exit: glow is gated at 0.1 m only, obs. 9 checks the outcome
class only, and the measured `t_gone` spread goes into Known gaps with a numeric gate (for example, the measured
spread + 20%). Whichever is chosen, give obs. 9 a number.

### EX-B2. The client has no region data, so `act`, picking and every ID-mask test are unbuildable
`tile_and_client.md::5.1`, `::4.3`, `::8.3`, `::8.4`, `::3.2`.

The client gets `material`, `crack`, `glow`, `temperature_c` and later `fire`. realtime §7's `welcome` carries
"the region list with each region's affordances", with no geometry. But:
- `F` sends `act {region, …}`. `crate` and `crate_control` are both wood (id 4), so the picked bytes can't say which
  region was hit.
- §8.4's ID pass "renders region and actor ids as flat colours". The shader has no region input.
- §8.3's "ID-mask areas of the crate, glow region and player" and §3.2's "player ≥ 95% visible" are built on that
  pass.

*Failure:* step 8 finds no region in any channel or message, and either changes the format after step 7's fixtures
froze or hard-codes the crate's box in the client.

*Fix:* in step 7, put each region's authored footprints (boxes in metres, from the scene) in `welcome`, with a
golden fixture. Or add a u8 `region` channel (+230,400 B per frame; see EX-S9). Let the server derive the region from
`point_m` with `_on_region`'s rule, and refuse a mismatch, so the client's `region` field is a check and not an
authority.

### EX-B3. The golden gate has no machine that runs it
`tile_and_client.md::8.1`, `::8.5`; `foundations_plan.md::§2` step 2; `standards_backlog.md` B6, B7;
`.github/workflows/test.yml` (on `origin/phase1/standards`).

- Step 2's row says "one golden frame" and "done when the gate runs Godot headless". §8.1 says goldens can't run
  `--headless`, because the dummy renderer draws nothing. Step 2 can't meet both.
- §8.5: canonical goldens "render in CI on Linux with Mesa's llvmpipe, identical across runners". The only
  workflow runs `scripts/prepush.sh` on `ubuntu-latest` and `macos-latest`, with no display. No step adds an
  Xvfb (or EGL) job, a pinned Mesa, or a container image. `ubuntu-latest` moves its Mesa version, so "identical
  across runners" is not true over time.
- The owner's Mac "reports without gating", and CLAUDE.md's hand-off rule is `prepush: PASS <sha>` locally. So the
  commit handed over has never passed B7.

*Failure:* a shader regression passes `prepush` on the Mac, and no CI job renders goldens.

*Fix:* assign a golden CI job to one step (step 2 is the natural place: the "one golden frame"). It needs a pinned
container image with Godot 4.7.2 and a named Mesa version, `xvfb-run godot --rendering-driver opengl3 …`, and runs
on Linux only. Change step 2's done-when to "headless parse and tests in the gate; one golden frame in the Linux
golden job". State in §8.5 that B7 is a CI-required check, and that `prepush` runs only the tier-agreement and
greyscale checks, and only if a GPU context exists.

---

## SHOULD-FIX

### EX-S1. Requirements with no step, or with the wrong step
`tile_and_client.md::13`, `foundations_plan.md::§2`, `checklists.md` (which has no sections for steps 2, 5, 6, 8
or 9).

| Requirement | Spec says | Plan row | Problem |
|---|---|---|---|
| Heat substep measured on the alley | step 5 (§1.4) | step 8 authors the alley | step 5 needs `data/scenes/alley.yaml` and scene v1 before step 8 makes them |
| `move`, `move_to`, `move_result`, `ignite`'s new params, actors in `tick` and the frame | step 7 (§13) | step 7 lists only `welcome`, `act_result`, `error` | the fixtures freeze without them; step 8 then has to bump the protocol |
| `fire` channel, P, D | step 6 (§13) | not in step 6 | Q4 is open, and step 7's frame fixture doesn't know it exists |
| Client runner testing `tests/fixtures/wire/` | step 2 (§9.2) | fixtures are step 7 | step 2 has nothing to decode |
| HUD hides time controls, "tested in step 7 with controls forced visible" | step 7 (§4.3) | the HUD is step 8 | step 7 has no HUD |
| Scene v1 with `spawns`, the v0 migration test, `data/world/player.yaml`, `data/server/` presets and rate limits, the walk grid, A*, the actor table | none | step 8 implicitly | none of these is named anywhere |
| Tier fields moving to `engine.tiers`; `cell_size_m` leaving the rig files | "when D20 is enforced" | step 3a, 4 or 5? | no owner |
| Save v0 "with the actor table" | step 9 (§13) | "grid plus scene spec" | the two say different things |

*Fix:* add a `checklists.md` section per step (2, 5, 6, 7, 8, 9), carrying each row above to exactly one step,
and update the plan rows' done-when to match.

### EX-S2. `check_plan.py` can't see this document's decisions or questions
`scripts/check_plan.py::ID_SOURCES`, `::QUESTIONS`; `foundations_plan.md::§4`, `::§5`.

T1 and T2 ("owner, 2026-11-18") are in neither plan §4 nor any ID source, and Q1–Q6 are not in plan §5. The plan
claims it "fails if this drops a decision … or an open question", and for this document that claim is false. Q5
(the renderer) also blocks step 2, since `project.godot` sets the renderer, but it isn't marked as blocking. *Fix:*
add this document to `ID_SOURCES` (with a `T\d+` pattern) and to `QUESTIONS`; list T1, T2 and §12 in the plan; mark
Q1 as blocking step 5 and Q5 as blocking step 2.

### EX-S3. Observation 1 is a wish next to an exact script
`::7.3` obs. 1. "x ≥ 1.2 m by tick 40" is already true at tick 15 (600 + 5 × 140 = 1,300 mm). The script derives
exact values (5,080, 2,000) mm at tick 42, and arrival by about tick 58. *Fix:* assert `pos_mm == (5080, 2000, 400)`
at tick 42, and the path's end within 50 mm of the target by tick 58.

### EX-S4. Two of the observations can pass with their mechanism deleted
`::7.3` obs. 5 and 7.
- "From `t_gone`, `fire` is zero everywhere" passes if `fire` is never populated. *Fix:* add a positive control,
  `max(fire) > 0` at some tick in (70, `t_gone`).
- `crate_control` integrity ≥ 0.99 can't fail by heat. With no convection, air's diffusion length over 3,600 s is
  about √(2.2×10⁻⁵ × 3600) ≈ 0.28 m, against a 2.68 m gap (*derived*, α of air *from memory*). It guards only
  mis-targeting (a fire placed at the wrong region). *Fix:* say that is what it guards, and prove it by deletion: an
  ignite whose region resolution is broken must fail it.
- The floor's 0.95 is "measured first". Name the procedure: measure, record it in Known gaps, commit the number, and
  gate the measured value with a stated margin, in step 8.

### EX-S5. "Live through the socket" can't reproduce the script's ticks
`::4.5`, `::7.3` obs. 8. A live paced run applies an intent at whatever tick it arrives. A client that sends `move`
on seeing tick 9 can land it at tick 11, so 5,080 mm at tick 42 fails, and "two runs … bit-identical" fails
intermittently. Paced at 10×, the 3,600 world-seconds also take 6 minutes of wall time. *Fix:* the live run uses
realtime §8 PR 3's **stepped** host mode, with a Python test client that sends each record when the server reports
the tick before its apply tick. Assert that the logged apply ticks equal the script's. State that the two
determinism runs are stepped.

### EX-S6. Path walking is not specified well enough to implement deterministically
`::4.2`, `::2.2`.
- After line-of-sight pruning, segments point in any direction. The integer heading table covers 8 directions
  only. No rule says how a 140 mm step along (420, 900) is rounded to integer mm (`math.isqrt`, a carried
  remainder?).
- "Arrival within 50 mm" with 140 mm steps: a body 60 mm short of a waypoint steps to 80 mm past it and never
  arrives, unless the last step is clamped. That is not stated.
- "Deterministic line of sight" is undefined. If it is checked on the walk grid's nodes but walking uses §2.2's
  continuous disc test, a pruned segment can graze a corner, the body gets blocked, and the path fails with
  `path_blocked` on clear ground.
- Whether a held WASD heading or a path wins on a tick is not stated. `move {null}` on releasing a key held before
  a click cancels the click's path.
- Start and target are off node centres (5,080 mm; 5,500 mm). Is the path from the node or from the point?

*Fix:* specify the per-tick step for paths in integers (clamped to the waypoint), use the continuous disc test for
line of sight, and give the precedence rule (a new `move` non-null cancels a path; `null` cancels only a heading).

### EX-S7. Rate limits drop the stop, and `move` has no reply
`::4.1`, `::2.3`; realtime §7 ("every client message gets exactly one final reply").
- A refused 31st `move` in a second can be the key-up `move {null}`, and the body walks until it hits a wall. Which
  clock "per second" means is not stated. Stage-1 limits are wall-time and pre-log, so the refusal is not
  reproducible.
- `move` has no reply kind, which contradicts W-F1.

*Fix:* coalesce `move` latest-wins per tick instead of refusing it (a stop is never dropped); state the clock for
each limit; define `move_ack {tick_applied}` or record an exemption in realtime §7.

### EX-S8. Rejection paths that no test covers
`::2.3`, `::4.2`, `::7.2`. CLAUDE.md requires every rejection path of a trust boundary to be tested. The variants
cover `out_of_reach`, `not_on_region`, `limit`, `not_finite` and the guest `time`. Not covered: `busy`, `no_path`,
`unreachable`, `path_blocked`, an out-of-range heading, both rate limits, `duration_s` over its limit, and the
oversize frame (§5.2 says "with a test" but gives no step). Check order is undefined. *Fix:* a refusal table (code, input, check order, the step that tests it).

### EX-S9. The frame-size gate contradicts the spec's own channels, and the cadence contradicts realtime
`::10` (frame bytes "≤ 1,154,048 B, exact"), `::5.1` (`fire` u8), `::5.3` (actors in the frame); realtime §7.
1,152,000 B counts 5 B per cell. With `fire` it is 6 B (1,382,400 B), plus the actor table and region data
(EX-B2). §5.3 also publishes cells "after each tick that applied an intent", so every WASD change triggers a 1.15 MB
frame, while realtime §7 sends a snapshot "when cells' version changed" (O23 is "on change"). *Fix:* derive the gate
from the channel list (Σ dtype bytes × cells + header bound), and send cell frames on cells-version change only.
Boundaries §4.2's internal frame cadence can stay as it is.

### EX-S10. The crack goldens can't see the crack the spec carves
`::6.2`, `::8.4`, `::8.2` ("crack carving disabled must fail G2"). The fissure half-width is "0.02 m × c", with c
undefined. If c = `crack`/255, then at `t_crack` (`crack` ≥ 64, c ≈ 0.25) it is 5 mm. The golden camera (size
10 m over 720 px) gives 72 px/m, so 0.36 px, and 0.18 px on laptop at 0.5 scaling. The ≥ 2× Sobel test and the
"carving disabled fails G2" proof can't pass. Or they pass on char albedo darkening alone, which is darkening, not
shape. *Fix:* define c, show the pixel arithmetic, and pick G2's tick and zoom so a fissure is ≥ 2 px. The deletion
proof must disable carving with char darkening *kept*.

### EX-S11. The exit tests' runtime and tier gating are unstated
`::7.3`. The cap is 36,000 ticks (7,200 physics steps) × (two runs + a replay) at 0.1 m, plus a 0.05 m reference
(1.84 M cells, about 8× the work) and a 0.2 m run. At a few ms per physics step that is minutes. CLAUDE.md requires
`slow` marks behind a tier variable. *Fix:* say which observations run in the default gate (for example 0.2 m, and
0.1 m with a smaller cap) and which run under `MAXIM_OVERDRIVE_ALL_TIERS`, with a measured wall budget.

### EX-S12. Budget meters that can pass vacuously or have no runner
`::10`. GPU time on the Compatibility renderer may be unsupported and read 0, which passes "≤ 8 ms". The GPU rows
name the owner's Mac and "an integrated GPU", neither of which gates. "`tick` delay p99" is wall time, against
§10's own CPU-time method, and is flaky at load 20. *Fix:* assert every meter reads > 0, mark machine-bound rows as
reported, and say where each B5 row gates.

### EX-S13. Scenario goldens go stale silently, and "tests never rewrite goldens" contradicts §8.1
`::8.1` ("the scenario writes frames … to `client/tests/goldens/frames/<tick>.bin`"), `::8.5`. If physics changes
`t_crack`, the committed frames still render green. The scenario goldens then can't fail on the thing they claim to
cover. *Fix:* only `scripts/update_goldens.sh` (to be created; mark it so) writes frames. A Python test regenerates
the five frames' digests and compares them with committed digests, failing with "re-record goldens". Name G5's
tick.

### EX-S14. The *to verify* items need a probe list, and many can't be probed headless
Header, §5.2, §6.1, §8.1, §9.2, §9.3, §10. About 15 items, among them reversed-Z, `DEPTH`, bloom under
Compatibility, `--headless`, GPU timing. The header says "step 2 probes each headless", but
rendering behaviour can't be probed with the dummy renderer. *Fix:* a table (item, probe, renderer context, step,
what changes if it fails). Make it step 2's checklist.

### EX-S15. The cut-away test has no denominator, no position and no deletion proof
`::3.2`. "≥ 95% visible" against what? If the ID pass draws the actor without a depth test, the answer is always
100%. At the tick 70 pose (5.5, 2.9), the SE yaw's line of sight from the body's +y edge enters the crate about
0.45 m out, hiding roughly the bottom 0.2 m of 1.8 m. That is near the 5% limit with correct code (*derived*,
rough). *Fix:* the denominator is the player's pixels with the cell volume hidden; the position is named (G5's);
and a deletion proof (cut-away off) must fail at that yaw.

---

## NIT

- **EX-N1** `::2.2`: (99, 99) mm is 140.007 mm, a 0.005% speed error, not 0.007% (0.007 is the error in mm).
- **EX-N2** `::7.3` obs. 3: `glow` ≥ 26 means T ≥ 622.5 °C (25.5 × 975 / 255 + 525), not 625 °C.
- **EX-N3** `::5.4` / `::6.1`: a Godot sampler's filter is a compile-time uniform hint. "nearest" on laptop and
  "trilinear" on rig needs two uniforms or shader variants. Without mipmaps, trilinear is linear.
- **EX-N4** `::8.3`: only laptop is compared against rig. The plan says "each rendering tier", so either compare max
  too or say why not (the roadmap says laptop and rig).
- **EX-N5** `::9.2`: `return_value_discarded` as an error forces handling of every `Tween`/`connect` return.
- **EX-N6** `::7.3`: define "crate cell" and "crate surface cell" (region id after a cell burns away; a face
  adjacent to air).
- **EX-N7** corrections list: `standards_backlog.md` B5, B6 and B7 cite "Phase 1 step 3/4/5", which is stale
  against plan steps 5, 2 and 8.

---

Counts: 3 BLOCKER, 15 SHOULD-FIX, 7 NIT.

**Verdict:** not buildable as written. The exit depends on Phase 2 physics and on region data the client never
gets, and the golden gate has no runner. Fold those three, and assign every requirement to exactly one step,
before steps 2 and 5 start.
