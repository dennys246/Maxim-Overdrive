# Fire model v2: Architecture lens, delta round 1

Reviewed: `fire_model.md` v2 as staged on disk (uncommitted), against `fold.md`, the round-1 report, CLAUDE.md, the
charter, the roadmap, the plan, world_model, tile, `client_rendering.md`, boundaries, `checklists.md`, and the
fire tests, `actions.yaml`, `world.py` and `damage.py` in the tree.

**Counts:** statuses 12 fixed, 1 deferred, 5 open, 0 rejected. New findings: 2 BLOCKER, 11 SHOULD-FIX, 5 NIT.

## 1. Status of the Architecture findings

| Id | Status | Reason (read from the tree) |
|---|---|---|
| A-B1 | fixed | §2.1: objects by persisted u32 id, any count per cell, segments sized in metres, inventories in kg; §6.1 adds the straddle test at dx/3 and 2dx/3. |
| A-B2 | fixed | §6.1 keeps tile §6.3's 10–15% against 0.05 m, converging from 0.2 m (owner ruling 2). What gets graded for the new exit is undefined, which is new finding D-S2. |
| A-B3 | fixed | §10.1 has a row for each document I named (plan step 6 and its Phase 2 line, roadmap exit and Phase 2, D23, D26, D28, tile §11). §10.2 has sub-steps ordered against steps 5, 7 and 8, the size is stated as "unknown", and the legibility clips moved to step 8. Leftovers are new findings D-S1 and D-S9. |
| A-B4 | open | The server side is fixed: wire tables, grammar before step 7, save, digest. The client side is not. `client_rendering.md` §5.1 voxel-raymarches cell channels and can't draw a 20 mm stick in an air cell. `crack` has no source in v2. `client_rendering.md` isn't in §10.1. See D-B2. |
| A-S1 | fixed | §10.1 rows for T13, T14, T17, T5, tile §5.1–§5.4, and §5.3's failure path ("it fired… not a rescue"). |
| A-S2 | open | Fixed: `ignite`/`extinguish` leave `parse_action`, and `kindle`'s pilot becomes a flame object. Still open: the red gates and `actions.yaml`'s `TEMPORARY` ceilings appear only as a §12 proposal. `HeatSource` and `World.sources` (the second heat path) have no stated fate. See D-S5. |
| A-S3 | open | §2.2 defines the coupling, but the convective power it deposits into air cells has no Phase 1 sink, and §4.2's "through those cells' open-air loss (6a)" names a law that exists only on solid skins. See D-B1. |
| A-S4 | open | Fixed: the occupancy consumer list, the exemption's definition, and the rule's other homes. Still open: `damage.strike`/breach on fuel objects (v2 says so itself), `crack`, and `thermal_degrade` on objects. Wood *cells* lost their fire law (D-S4). |
| A-S5 | fixed | §5.4 has one `kindle` and no NPC acts in Phase 1. In §7 the fire is authored and the player only kindles. |
| A-S6 | open | Fixed: §9.1 splits the material data by owner. Still open: no per-layer placement (§12 says so). The refusal list still reads as one loader ("the loader refuses"), not a validator per owner composed by the loader. See D-S6. |
| A-S7 | fixed | §2.3 defers per-species zone state to Phase 2 (D26) and keeps the closure checks; species reach only a ledger line per name. |
| A-S8 | fixed | §4.1: stateless flames, min-member-key id; §4.4: occlusion a pure function of geometry, walls receive, no tilt in still air, held field saved. The new held-field issue is D-S10. |
| A-S9 | deferred | §11 item 10 routes each ask to a Phase 3 roadmap row and a `maxim_upstream/` draft, reusing ids. Reason: they stay proposals until the owner rules. Trigger: the ruling on item 10, and the rows land in that same commit. |
| A-N1 | fixed | §10.1's last row: O34's one registry. |
| A-N2 | fixed | §2.1: kg per object and segment. |
| A-N3 | fixed | §9.1: the validation materials are test fixtures. |
| A-N4 | fixed | §7: "Two of them have no oracle, so the exit is a prediction". |
| A-N5 | fixed | world_model §2 is now cited in §2.3's dripping note, not listed as a revision. |

## 2. New findings on v2

### BLOCKER

**D-B1. Convective heat goes into air cells, which have no Phase 1 sink, and the air temperature it produces depends on dx and feeds back into the fuel.**
`fire_model.md::§2.2` (convection h(T_s − T_cell) with each overlapped cell; "Cells keep one temperature"), `§4.2` (Q_gas).

v1 and tile §1.2 exported the plume: "the flame's convective plume leaves the open-topped alley". v2 deposits power
into the air cells:
- every segment convects h(T_s − T_cell) into the cells it overlaps;
- Q_gas "goes to the overlapped cells' gas by overlap" and then "reaches the outside reservoir through those cells'
  open-air loss (6a)".

6a as written (tile §5.2) is "each exposed face loses … from its skin", which is a law on solid faces. Air cells
have no 6a. Phase 1 has no advection either (convection is a Phase 2 bullet). So an air cell's only sink is
conduction through air.

Scale (D): a 0.2 m air cell holds about 9.6 J/K, and 0.1 m of 20 mm stick 500 K above it puts in about 100 W. The
far-field conductance, about 4πkL with k_air = 0.026 W/m·K, allows thousands of kelvin: the "2.67 million °C" Known
gap again. L is the overlapped cells' size, so the air temperature depends on dx, and it sets T_env (convective loss,
neighbours' preheat) for every overlapped segment.

This runs through the "segment–cell coupling" path that §6.1's cross-grid gates exercise. The physics would fail
those gates, and fixing the gates is not allowed. It also trips the `≤ WOOD_FLAME_C` assertion in
`test_the_fiercest_allowed_fire_…`, which §12 proposes to flip. Even if Q_gas is read as "booked straight to the
reservoir", the segments' own convection still has no sink.

**Failure scenario:** R3b (starter beside a stick) at 0.2 m against 0.05 m. Air around the starter reaches different
temperatures on each grid, so the stick's preheat differs, and the class flips across grids.

**Fix direction:** pick one Phase 1 convective sink and write it as a law in metres:
- segment convection to ambient, with the air cell used only for bookkeeping, as tile v3 did;
- or a defined plume export from the overlapped cells.

Then state T_env per receiver. Either way it is a §10.1 row against tile §1.2.

**D-B2. `client_rendering.md` isn't revised, and its renderer can't draw what v2 puts on the wire. Every exit path, the fallback included, goes through it.**
`fire_model.md::§9.2`, `§10.1`, `§10.2` 6.4; `client_rendering.md` §4.2, §5.1, §5.4, §6.

What the client is designed to do (frozen v3):
- it raymarches cells (DDA over a 3-D texture);
- it draws a fuel-bed cell "as solid while it has fuel left";
- its cracks are per-cell Voronoi patterns driven by `crack`, a cell's charred fraction;
- its goldens G2 and G3 are measured "over cracked cells" and glowing cells;
- flames are particles "at burning cells".

v2 makes all of that stale:
- Sticks, cardboard and the starter are sub-cell objects in air cells, so the raymarch passes through them.
- The client needs a second, mesh-based path, with instanced rods, slabs and beds from the segment table and a
  flame mesh from the flame table.
- `crack` has no source: §9.2 names only `segment_glow` and `burning`, and charring is a lab instrument (§5.1).
- The roadmap's exit is "watch it crack, glow and burn away", and CLAUDE.md requires that cracks "change shape and
  shading".

None of this is in §10.1, in §10.2's PR list, or in the size. The fallback exit, "a burning slab that flames out
and glows", still needs it.

**Failure scenario:** step 7 freezes the snapshot grammar with segment and flame tables (§9.2). Step 8 then finds
the client can't draw them without a renderer redesign, which nobody has sized. Alternatively, the table columns
are chosen without their consumer and get a version bump on day one: A-B4's scenario, moved from the server to the
client.

**Fix:** a §10.1 row for `client_rendering.md` §4.2, §5 and §6, and a client sub-step in §10.2 before step 8. Say
what replaces `crack` and the G2 golden.

### SHOULD-FIX

**D-S1. 6.0 freezes formats before 6.1 and 6.2 decide what goes in them, and it has to land inside step 5a.**
`fire_model.md::§10.2` 6.0, `§9.1`, `§3.1`.

Ordering:
- 6.0 must land before "step 5's log writer" and puts the tables "in the registry".
- Both the registry and the intent log are step 5a deliverables (O34; plan §2).
- Plan step 6 is blocked by 5b.

So 6.0 is really a 5a prerequisite or a 5a sub-step, and the plan row doesn't say so.

Content:
- 6.0 freezes material data v1, including kinetics refusals on A, E and n.
- R0, in 6.1, then chooses between a threshold law (T_p, L_g) and Arrhenius with a cutoff.
- 6.0 also adds flame snapshot columns before 6.2 has designed flames.

The design's own goal, "no replay golden is recorded on v0", just moves the problem to v1 → v2.

**Scenario:** R0 picks the threshold law, and material data v1 has no T_p field. That forces a migration and
re-recorded goldens after step 5's log exists.

**Fix:** either make v1 carry both rate-law forms and declare the flame table extensible, or move material-data
freezing after R0. Add a 5a/6.0 row to the plan.

**D-S2. Tile §6 isn't revised, so owner ruling 2 has nothing to grade.**
`fire_model.md::§6.1`, `§7`, `§10.1` ("tile §6.3 item 8: kept").

§6.3 items 2–5 define ignited, `t_crack`, `t_glow` and `t_gone` on bed cells, "envelope cell faces" and the
envelope-layer skin (6b, now replaced). The §6.4 controls disable 6a, deposit `plume_convective` into the floor and
flip the red gate. The §6.2 script lights a crate with an accelerant. For a built fire, v2 keeps item 8's tolerances
but names no graded times.

**Scenario:** at 6.4, R4's "peak within ×1.5" is the exit's only quantitative gate: A-B2's loosening, back.

**Fix:** a §10.1 row for tile §6.2–§6.5 that names the exit's graded times and their observables on segments.

**D-S3. "6b replaced" takes the skin off structural faces just as v2 starts irradiating them.**
`fire_model.md::§4.4` (receivers include "solid cell faces", revising T14), `§10.1` (D29/D30 row).

Three facts:
- world_model §3 put a skin "on every exposed face that exchanges heat, not only fuel faces" because without it a
  concrete wall absorbs 104/104/85 MJ/m² against a converged 48 (P1, measured).
- 6a is defined "from its skin".
- v2 replaces 6b wholesale.

So the walls now take flame radiation (tile §5.4: 20–40 kW/m² at `wall_north`) through cell means, which
`thermal_degrade` then thresholds (the D25 gap).

**Scenario:** concrete face cells near the fire degrade at 0.2 m but not at 0.05 m, and V_floor and `crate_far` read
it differently per grid.

**Fix:** scope the replacement to fuel ("6b for fuel replaced; the structural skin kept") and say so in §10.1.

**D-S4. Wood cells keep no fire law.**
`fire_model.md::§9.1` (structural wood cells kept), `§10.1` (thin-features row: "a plank wall stays cells").

With 6b–6d replaced by objects, a wood *cell* burns only by `thermal_degrade` (`damage.py:73`), a threshold on the
cell mean. That is exactly the cause of the roadmap's Phase 1 requirement ("a per-cell ignition or pyrolysis
threshold would inherit it"). Or it doesn't burn at all. Either way there are now two truths for wood, and what
decides between them is how the wood was authored.

**Scenario:** a scene author or a later imagined wooden door puts wood cells beside the built fire. It never
ignites, or it ignites differently per grid.

**Fix:** pick one:
- wood cells are non-combustible structure in Phase 1, refused next to fire or recorded as a Known gap with numbers;
- or structural wood is authored as `slab` objects with breach deferred.

**D-S5. The red gates and the `ignite` retirement are a test migration with no owner.**
`fire_model.md::§5.4` ("`ignite` and `extinguish` leave `parse_action`, and a test refuses both through
`execute`"), `§12`.

Three strict gates call `execute("ignite", …)`:
- `test_a_fire_that_has_burned_its_fuel_stops_heating` (cross_tier:79);
- `test_the_fiercest_allowed_fire_…` (act_validation:286);
- `test_a_fire_on_a_region_carved_hollow_…` (act_validation:820).

The last one guards with `if res.success`, so retiring `ignite` turns it XPASS. The strict gate goes red, and the
easy fix is deleting it with its Known gap unexamined. The other two can only flip once they are rewritten against
`kindle` and an object crate, and the roadmap names them as Phase 1 requirements. Rewriting a red gate's scenario
is exactly where a loosening hides: today's fiercest-fire gate checks integrity within 0.1 on every turn on every
rig.

Also: `kindle`'s sphere-deposit `TEMPORARY` was to go when "step 6's skin exists" (tile §3.2), which no longer
exists (now 6.2), and `tests/` has 73 `ignite`/`extinguish` call sites.

**Fix:** a §10.2 row that maps each gate to its rewritten form and to the invariant it keeps (at least as strict),
reschedules the markers, and lists the lab builder's replacement for `HeatSource`.

**D-S6. Object state sits outside boundaries' write window and published frame, and placement is needed before 6.0.**
`fire_model.md::§2.1`, `§12`; `boundaries.md` §2.2, §4.1, §4.2.

What boundaries says:
- §4.1: "every array the core owns is read-only at rest", and writable only through `cells.writing()`.
- §4.2: observers read published frames.
- §2.2: layer 2 geometry has "no cells", layer 3 `engine.cells` holds the window, and layer 4 holds the laws.

Where v2's pieces would have to go:
- fuel objects are metric geometry plus mutable state;
- coupling rows are keyed by cell and by object;
- flames are recomputed per step.

Nothing places them, puts them in the window, or adds them to the frame. Without a placement, the obvious place for
the new tables is `World` or `CellStore` (10 of 12 public members). That is how a god object starts.

**Fix:** write a placement note before 6.0. It needs a layer per container, window ownership, the frame's contents,
and the module split (solid, flame, coupling, radiation). It also needs a home outside v2, because of D-N4.

**D-S7. The held flame's lifecycle is on step 5's critical path, not step 6's.**
`fire_model.md::§5.4` ("the vocabulary is v1 amended before step 5 ships it"), `§12`.

`kindle`'s intent shape (duration, `restrike_ticks`, what `leave` or dropping does to a lit pilot) freezes with
step 5's first log writer (tile §3.2). §10.2 has no row for it.

**Scenario:** step 5 ships vocabulary v1 with the sphere deposit's semantics, and 6.2's flame object needs a v2
vocabulary.

**D-S8. FPH-B1, a recorded step 6 requirement, is half-dropped without a revision row.**
`fire_model.md::§3.3`; `checklists.md` FPH-B1 (from T13).

FPH-B1 requires in-bed radiation and "the draught's air-supply loss". v2 keeps radiation for authored beds but
drops draught and O₂. That may well be right, since the risk is named for R4. But it revises a requirement the owner
froze under T13, and §10.1 doesn't list `checklists.md` or FPH-B1 to FPH-B3.

**D-S9. The time-box is counted in reruns, not effort, and the fallback isn't cheap.**
`fire_model.md::§10.2`, `§7`.

"At most two pre-registration reruns" doesn't limit the months it can take to build 6.1 or 6.2 before their first
run. Owner ruling 3 asked for a time-box. Also, the fallback still needs 6.0, the client path (D-B2) and the gate
migration (D-S5), so A-B3's "nobody can say when Phase 1 ends" partly survives.

**Fix:** a calendar or PR-count bound per sub-step, and the fallback's own remaining scope stated.

**D-S10. With multi-rate radiation, the flame budget's "no term added on top" needs a definition of what is held.**
`fire_model.md::§4.2`, `§4.4`.

Q changes every step, because flames are stateless, but the radiation field is held for N steps. There are two ways
to read "held":
- If view factors and occlusion are held and multiplied by the current χ_r·Q, the partition closes.
- If fluxes in W/m² are held, Q_rad,view and Q_contact,rad no longer sum to χ_r·Q, and the closed-shell ledger test
  fails between recomputes.

**Fix:** state that geometry is held, not power, and add a ledger test at a step between recomputes.

**D-S11. Imagined fuel objects are capability with no Phase 1 caller.**
`fire_model.md::§9.2` (spec v1, `imagination.place` creates fuel objects).

`imagine` has no wire message in v0 (T16), and Phase 1 has no NPCs. Spec v1 with per-recipe ranges, variant keys
and budgets is a trust surface built before anything calls it (CLAUDE.md, "A fix ships with a caller").

**Fix:** in Phase 1, `place` refuses fuel recipes, with a test. Spec v1 lands when `imagine` joins the wire.

### NIT

- **D-N1.** `fire_model.md::§9.2`: `burning` is listed under "channels whose meaning changes get new names (F1)" but
  keeps an existing name. `client_rendering.md` §4.2 already defines `burning` per cell. Rename it, for example
  `segment_burning`.
- **D-N2.** `fire_model.md::§10.1` misses:
  - world_model §3's law-table rows: ignition by face fraction, "unaligned fuel geometry is refused", flame feedback;
  - boundaries §2.2, §4.1 and §4.2;
  - the `architecture.md` Known gaps v2 claims to close (air at 2.67 million °C, sub-cell source heats one cell).
- **D-N3.** `fire_model.md::§12`: `douse` on fuel objects (F7: water as heat and O₂ sink) is missing from the
  not-yet-designed list next to `strike`. Neither has a Phase 1 caller (T16), so the honest status of both is "the
  applier refuses on a fuel object until …", with a test. A-S4 can close that way.
- **D-N4.** `fire_model.md` is at 6,000 words by `wc -w`, the O22 cap for a new document, with five design items
  still open (§12 plus D-B2). Name the companion note or notes now, rather than growing v2.
- **D-N5.** Owner ruling 3 is ruled, but on disk `foundations_plan.md` step 6 still reads "Done when: tile §6.3
  passes at three grids", and the roadmap's exit still reads "set a crate on fire". State in §10 that the revisions
  land in the acceptance commit, or land the ruled ones (§11 items 1–3) with this fold.

## 3. Checked, nothing found

- **Root cause:** patch-mean ignition and per-patch extinction are removed (§3.2, §4.3), not tuned; dripping and
  autoignition are refused and recorded.
- **Rulings 1–3** are recorded accurately (§11) and applied (§4.4, §6.1, §10.2).
- **Determinism and the bridge** (§4.1, §8.2, §5.4–§5.5): consistent with world_model §6, D21 and boundaries B-13.
