# Architecture lens: world_model.md (design v3 part 1, draft, at 66310f4)

Reader: Architecture. Inputs: CLAUDE.md, `docs/code_review.md` ("Design reviews", the Architecture lens),
`docs/architecture.md`, `docs/roadmap.md`, `docs/standards_backlog.md` (B5, B7), the design,
`reviews/world_v2/architecture.md` (whose findings it folds) and `reviews/world_v2/determinism_lanes_performance.md`
(the measurements D20 rests on). Checked against code in `.worktrees/act-validation` at 2f200b5: `config.py::RigProfile`,
`data/rigs/*.yaml`, `world/world.py` (`World.from_scene(scene, rig)`, `min_substeps=self.rig.min_substeps_per_turn`),
`world/scene.py::Scene.build(rig, …)`, `_check_no_solid_overlaps`, `footprint_of`, `world/grid.py::Footprint`, `Region`,
`sem_env/bridge.py` (reach, `centroid_m`), `data/world/actions.yaml` (`min_sigma_m: 0.2 # at least the coarsest rig's
cell`), `tests/conftest.py` (`rig` / `rigs` fixtures over `ALL_TIERS`), and PR 1's strict red gates in
`tests/test_act_validation.py` and `tests/test_cross_tier.py`.

Counts: 3 BLOCKER, 12 SHOULD-FIX, 6 NIT.

**The short answer.** D20 is the right root fix, and I agree with it on the merits, not to be agreeable. "Different
machines play different-but-equivalent games" was a constraint the project imposed on itself, and it generated most
of PR 1's eight review rounds. One truth makes saves, replays, co-op and cradles portable across machines for free
(it moots v2's A-SF-16), and the measured cost (3.9 ms per cached substep at 0.1 m, about 2 substeps per 0.5 s step)
leaves real headroom. But the draft doesn't finish the decision. (1) D21's "budget freedom, law by law" puts the
machine and the wall clock back into the simulation, which is the class D20 removes (B1). (2) The resolution rule has
dependents everywhere: CLAUDE.md, the roadmap, B5, B7, `data/rigs/`, `actions.yaml`, about 20 source and test files,
and PR 1's four strict red gates, every one of which asserts "the same at every rig". The draft names three documents
and no disposition for the gates, so D20 can be read as permission to loosen cross-tier tests (B3). (3) The fold
table repeats the defect it was added to fix (B2). The expensive-to-undo risk is not 0.1 m itself but freezing the
uniform 0.1 m grid into formats while D21 plans refinement (SF-2), and hard-coding the truth size while §12 Q1 still
asks what it should be (SF-1).

## Fold audit: reviews/world_v2/architecture.md

| Id | Sev | Table says | Verdict | What's missing |
|---|---|---|---|---|
| B1 fold honesty | B | this table | **Not folded** | The table omits SF-8, SF-9, SF-10, SF-13 and SF-16 (part 1's scope), SF-15 and SF-17 (folded under other ids but not cited), and SF-1, SF-2, SF-14 and N1–N8, which appear neither here nor in "Not in this part" (B2 below) |
| B2 id array vs overlap rule | B | §5 | **Partly** | §5 makes the authored shape exact (CSG), which is half of what was asked. Missing: "intersected with the matter the region still owns", without which "a destroyed region claims its space" does not close (SF-5); that the overlap rule *stays* when the id array lands in PR 4; and correcting `docs/architecture.md`'s "removes both" in that PR |
| B3 rubble on strike | B | §7 | **Partly** | Asked for four definitions. §7 gives breach by open area (but §3 defines breach by thickness: SF-6), and the crater test's measure. Missing: when loose matter counts as open for gas and for passage; which fields become saved rather than derived once cells move (`region_id`, `original_material`); who owns rubble's identity (cluster ids exist, region ownership doesn't) |
| SF-3 gas interface | S | §2 | Folded | `gas.over(mask)` takes cells where SF-3 asked for a region in metres (N3). The frame writer is a consumer too; say whether it goes through the interface |
| SF-3 liquids | S | §2 | Folded | Per-zone film now, positioned puddles behind `liquid.at`/`liquid.over` in Phase 2. Acceptable |
| SF-5 PR 7 too big | S | §10 (8a, 8b) | Folded, with a loss | The split and rubble's move to Phase 2 are right. Breach by remaining thickness (§3, S1) is now in no PR (SF-7) |
| SF-6 air exchange | S | §3 (skins) | **Partly** | The exchange is named and measured. Still missing: where an external source's power over open cells goes once air leaves the solve (into the zone, through the ledger); that the fuel-gap red gate stays red until 8b; the skin's coefficient and depth as `data/` tunables; and the "re-derive the crate numbers once" question (now PRs 7 and 8a) |
| SF-7 caching dropped | S | §9, §10 | Folded | In `phase1/sim-clock`. But the cache key SF-8 questioned is unanswered (SF-9) |
| SF-11 protocol freeze | S | §10 (6) | Folded, mostly | Extensible `welcome`/`act_result`/`error` and a Godot reader in PR 6. SF-11 also asked for one texture upload on the pinned engine, which is the risk it named (N4) |
| SF-12 save before lanes | S | §10 (11) | Folded in order | The load rule (DA-6) is promised but not stated; name part 2 as its owner |

## BLOCKER

### B1. D21's "budget freedom" lets a machine's speed change the simulation, which undoes D20 and the determinism rule
**Where:** §0 D21 ("A machine's time budget may coarsen or sleep only regions where the outcome is provably
unchanged"); §1.2 ("As a law is verified resolution-independent by its convergence test, it earns budget freedom:
the dial extends law by law, measured").
**Scenario:** PR N "earns budget freedom" for heat conduction, because its convergence test passes within tolerance.
A slow host under a 10× dial coarsens a quiet-ish wall's conduction to 0.2 m. The run now differs in bits from the
same intent log replayed on the owner's machine, and from the same machine replayed when it's less loaded, because
the decision was taken from wall-clock time. That breaks "the same scene and intents give bit-identical state on one
machine" (CLAUDE.md, Determinism), makes the intent log no longer the bug report (Replays are first-class), and
recreates "different machines simulate different worlds", now invisibly, for any law that passed a tolerance.
A convergence test within a tolerance is not "provably unchanged"; it is "changed by less than ε", and a binary
outcome near its threshold (the band gate's own premise, §3) flips on ε.
**Fix:** Keep exactly two levers, and say so in D21: (a) sleeping, which is bit-identical by construction and tested
(SF-3); (b) dilation, which changes only the world-time-to-wall-time mapping. Delete "budget freedom, law by law".
Any coarsening or refinement is decided from world state only, the same on every machine (D21's first sentence),
which makes it part of the truth, verified like any other law, and never a machine's choice. If the owner wants a
machine-dependent lever anyway, it must be a recorded intent in the log (an explicit "this session runs law X coarse"
event) and the design must say that two such sessions are different worlds.

### B2. The fold table repeats A-B1: part-1 findings are missing, and three marked as landed are only partly folded
**Where:** "Fold table" and "Not in this part"; the audit above.
**Scenario:** The owner accepts part 1 on the strength of a fold table that "maps every finding in scope". Then:
- PR 4 caches conductances keyed by `topology_version`. PR 8a makes fuel mass change ρc and k every step with no
  `set_material`, so the caches go stale or are rebuilt every substep (A-SF-8, unanswered).
- §9 publishes region reductions "once per physics step as a frozen object", the exact cache A-SF-9 showed goes
  stale after an action, so a strike reads as having done nothing until the next physics step. The draft doesn't
  only omit A-SF-9; it re-adopts the defect (SF-8 below).
- A-SF-10 (fines and chunk entities depending on the rig), A-SF-13 (Supersedes) and A-SF-16 (rig-bound saves) are
  in part 1's scope. D20 moots A-SF-16 and partly A-SF-10, which is good news the table should record, not omit.
- A-SF-1 (which older sections are normative), A-SF-2 (stale PR numbers), A-SF-14 (Phase 3 numbering) and every NIT
  are in no part's list. They fall between the parts.
The charter requires every BLOCKER and SHOULD-FIX to be folded or answered in writing. "Findings for parts 2 and 3 are
listed there" can't be checked while those parts don't exist.
**Fix:** One master fold index for the whole v2 review (all six lenses, every id including NITs), in
`reviews/world_v2/README.md` (A-N8, still absent), with the part that owns each id. Part 1's table cites the
index. Mark partial folds as partial with what remains, as the audit above does.

### B3. D20 changes the standing resolution rule but gives no disposition for what depends on it, including PR 1's strict red gates
**Where:** §1.1 ("What changes in the standing rules … CLAUDE.md, `docs/architecture.md` and the review charter's
Physics lens change with it"); §10 PR 3 ("The resolution rule becomes the verification rule"). There is no Supersedes
section at all; v2 had one, and A-SF-13 found it incomplete.
**Scenario:** PR 3 rewrites the cross-tier tests as convergence tests. PR 1's gates assert agreement at 0.2 m:
`test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn` (spread ≤ 0.1 on every turn,
across all grids), `test_a_strike_breaches_a_thin_wall_the_same_at_every_rig`, `test_a_fire_on_a_region_carved_hollow…`
and `test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`. "0.1 m within tolerance of 0.05 m, and
converging from 0.2 m" is a strictly weaker assertion than "0.2 m agrees". Without a written disposition per gate, a
red gate that would have forced a physics fix can be satisfied by the new, weaker test, which CLAUDE.md forbids ("If
a cross-tier test fails, fix the physics; never loosen the test"). D20 is the owner's legitimate decision to change
the rule; the risk is that the change happens gate by gate, unrecorded. Everything else that says "rig" goes stale
with no owner:
- **CLAUDE.md:** the resolution rule; "Thin features must be at least two cells of the coarsest rig thick" (SF-4);
  Determinism's "Across machines only the outcome class is promised, as with rigs"; the Commands comments ("laptop +
  rig profiles", "the 0.05 m max profile"); Exit tests' "golden screenshots per profile"; Performance's "per profile".
- **`docs/roadmap.md`:** Phase 1's exit ("look the same, apart from detail, at the laptop and rig profiles", which
  becomes a rendering-tier test with the physics identical by construction); Phase 2's preamble, "Scale" (coarser
  cells beyond `full_res_radius_m` around agents, which D21 now governs) and "Close the known gap: the coarsest rig's
  late-burn lag" (now a verification failure, not a gameplay gap); Phase 6's exit "at every rig"; the standing rules.
- **`docs/standards_backlog.md`:** B5 (budgets "per profile"; there is now one physics budget at the truth, which
  needs a reference machine and a minimum spec, SF-12) and B7 (golden screenshots per profile become per tier).
- **`docs/code_review.md`:** Physics ("cross-tier test"), Performance ("at the max profile (about 5×10⁶ cells)"),
  Client ("the same at both profiles").
- **`docs/architecture.md`:** "voxelized at whatever cell size the rig profile chooses", the resolution-rule section,
  and each Known gap phrased across rigs (several change meaning: the sub-cell source, the imagined-object fit, the
  `actions.yaml` minimums).
- **Data and code:** `data/rigs/*.yaml` (their header comment states the old rule; `min_substeps_per_turn` and
  `full_res_radius_m` are simulation parameters, not rendering ones), `data/world/actions.yaml`'s `min_sigma_m`
  comment, `config.RigProfile`, `World.from_scene(scene, rig)`, `Scene.build(rig, …)`, `MaterialGrid.empty(…, rig, …)`,
  docstrings in `bridge.py`, `scene.py`, `spec.py` and `world.py` that justify a design by "the same at every rig",
  and `tests/conftest.py`'s `rig`/`rigs` fixtures, which parametrise most of the suite.
- **v2 text this part says "stands"** (SF-10): v2 §2.1's table ("rig cells"), the per-rig memory budget, "the rig
  field is substeps per physics step".
**Fix:** Add a Supersedes section with one line per item above and what it becomes. Add a red-gate disposition
table: for each of PR 1's four strict gates, the old assertion, the new assertion, and the owner's sign-off that the
change is a rule change and not a loosening. Land the doc lines that state the accepted rule on acceptance (DA-15's
split), and the code lines with PR 3.

## SHOULD-FIX

### SF-1. "One truth" isn't held by a type, and the truth size is a constant while §12 Q1 is still open
**Where:** §1.1; §10 PR 3 and PR 4; `config.RigProfile` (bundles `cell_size_m` and `min_substeps_per_turn`);
`World.from_scene(scene, rig)`.
**Scenario:** The verification harness needs `World` at 0.2 and 0.05 m, so `World` keeps accepting any cell size.
Nothing then stops the shipped host, a cradle runner or a benchmark from constructing a 0.2 m world, which is a
second truth by accident. Separately, PR 3 builds the harness on `RigProfile`, and PR 4 ("the truth resolution")
changes the same signatures again: a double retrofit, on top of v2's A-N1, which §10 still doesn't answer. And
formats key to 0.1 m (scene alignment "checked in integers at the truth resolution", face keys, integer counts) while
Q1 asks whether 0.1 m is right; changing the answer later is a migration of every committed fixture.
**Fix:** Split `RigProfile` in PR 3, the first consumer: a `Resolution` (cell size and substep policy, refined in
space and time separately per E2) that is part of hashed world config and carried in every format header, and a
`RenderTier` that the server never reads. The shipped path builds `Resolution.truth()` from config; the harness
passes verification resolutions explicitly, by a separate constructor, so a non-truth world on the shipped path is a
type error or a loud refusal. Say where the verification grids' definitions live once `data/rigs/` means render
tiers. Then Q1 can change with one config value and a version bump, not a refactor.

### SF-2. The formats freeze a uniform grid while D21 schedules adaptive refinement
**Where:** §1.2 (Phase 2 refinement, "refinement events are part of the deterministic state"); §6 (zone volumes as
"cells per zone"); §8 (face table "keyed by (cell index, face 0–5)"); §2 (`gas.over(mask)`); §8's grids with one cell
size each.
**Scenario:** Phase 2 refines near a fire. A refined parent face now borders four child faces, so `(cell index, face)`
no longer names a face. Zone volume "in cells" mixes 1 m³/1000 and 1 m³/8000 cells. A mask is per level. Every one of
these is in save v0 and the frame grammar, so refinement becomes the format change and refactor D22 promised to avoid
for rubble. This is the expensive-to-undo decision in the draft.
**Fix:** Either reserve now (integer counts in units of the finest allowed level; face keys as (level, cell index,
face); a patch or sparse-grid container in the grammar; consumers read in metres, per SF-3 of v2), or write into
D21 that refinement is a format version bump with a migration and that Phase 1's formats assume a uniform grid.
Either is defensible. Silence isn't.

### SF-3. "Provably quiet" needs a per-law predicate and activity-independent reductions, and no PR builds chunks
**Where:** §1.2 (sleeping bit-identical on or off, "and a test holds that"); §4 ("solve runs over solids or active
chunks").
**Scenario:** A wood chunk at 20 °C has a non-zero Arrhenius pyrolysis rate and a non-zero bound-water rate, so a
step changes it in the last bits; it is never exactly quiet unless the law has a cutoff, which is a threshold the
design must own. A wall chunk whose skin faces a zone at a different temperature isn't quiet either, though its cells
and halo are uniform: "uniform with a uniform halo" omits zone coupling. And numpy's pairwise summation means a sum
over a compacted array of active cells differs in bits from the same sum over the full array with zeros, so any
ledger total, bincount reduction or zone exchange that feeds back into state breaks the bit-identity test the moment
sleeping is implemented by compaction.
**Fix:** Every process in the registry declares its quiet predicate (an exact zero of its update, including
coupling to zones and faces). Every reduction that feeds state iterates a fixed index set in a fixed order,
independent of activity. Name the chunk size and the PR that builds chunks and sleeping (none in §10 does), or move
sleeping to Phase 2 "Scale" with active-chunk solving.

### SF-4. Which grid do authored features, alignment and action minimums refer to now?
**Where:** CLAUDE.md "Thin features … coarsest rig"; §3 ("unaligned fuel geometry is refused"); §8 ("grid alignment
checked in integers"); `data/world/actions.yaml` (`min_sigma_m: 0.2 # the coarsest rig's cell`, `ignite` radius at
least 0.3 m); Known gap "whether an imagined object fits can depend on the rig".
**Scenario:** An author reads D20 and makes a 0.2 m partition (two truth cells). The 0.2 m verification grid sees it
as one cell, so "must converge from 0.2 m" fails for reasons that have nothing to do with the law under test. Or the
loader checks alignment at 0.1 m, and the 0.2 m verification run voxelizes the same fuel unaligned and is refused.
Conversely, if every limit stays at 0.2 m, D20 buys no finer authoring at all, which the owner may not expect.
**Fix:** Decide and state it: scenes, fuel and specs aligned to the coarsest verification lattice (0.2 m) and thin
features at least two of its cells, so all three grids resolve every authored feature; or verification at 0.1/0.05
plus a different coarse check. Update `actions.yaml`'s minimums and comments to say which grid they protect.

### SF-5. CSG footprints don't close "a destroyed region claims its space", and land after the protocol freezes their meaning
**Where:** §5; §10 8b; §12 Q3; `grid.py::Footprint` (bounding box and centroid); `bridge.py` reach and `centroid_m`.
**Scenario:**
- A crate burns away. Its CSG is authored and static, so a strike "at the crate" is still on it, `ignite` still lands
  in the old box, and `spec.place` still refuses an object there. §5 says all four ownership gaps close; this one
  doesn't. A-B2 asked for authored geometry *intersected with the matter the region still owns*, read as a
  volume-weighted reduction in metres. §3 already has the pieces (sub-box recession gives the current surface in
  metres; fines account for struck mass).
- A cell straddles a wall's CSG and a window's. It has one owner and one material, so "does this fire touch the
  wall" (decided on the CSG) and "which cells does it heat" (decided on ownership) disagree at that cell. The rule for
  a straddling cell's owner is unstated.
- Timing: the region catalogue, centroids and reach go on the wire in PR 6. Moving them from boxes to CSG in 8b changes
  a field's meaning after the freeze, which §8's F1 forbids under the same name.
**Fix:** Region shape now = authored CSG ∩ current matter; state the straddling-cell owner rule (volume majority, ties
by authoring order) and that decisions in metres use the CSG, cells only for deposition. Land the CSG with the region
id array in PR 4 (it is small: boxes and cylinders, union and difference, and the scene already orders carving), or
keep footprints and centroids off the wire until 8b. State that `_check_no_solid_overlaps` stays until the CSG lands.
Persist the CSG as authored input in the save, not a derived id (A-SF-16's note). On Q3: earlier, for this reason.

### SF-6. §7's rubble foundations leave three format meanings to change in Phase 2
**Where:** §7; §2 ("destroyed solid mass … to the zone's fines species"); §3 (breach by remaining thickness); §8 F5
("A save has no optional fields").
**Scenario:**
- Save v0 treats `region_id` and `original_material` as derived from the scene and checks them against a digest
  (v2 §8). Phase 2 rubble moves cells, so they become saved state, which changes a saved field's meaning, the thing §7
  promises won't happen.
- `loose` and `packing_fraction` are "absent until Phase 2", but a save has no optional fields, so Phase 2 bumps the
  save version anyway. Either they're present (zeros) in v0, or the promise is "a migration with a literal default".
- The fines species means "all destroyed solid" in Phase 1 and "true fines" in Phase 2. Same name, new meaning (F1).
- §3 decides breach by remaining thickness along the normal; §7 by open area. Two definitions of one outcome.
- What happens to a face's skin state when rubble covers the face (asked in A-SF-17) is unstated.
**Fix:** Save `region_id` and `original_material` as state from v0, or say v0's derived set excludes them. Make the
reserved channels present-with-default in v0. Name Phase 1's sink `debris_kg` (or similar) so Phase 2's split adds a
species instead of redefining one. Give one breach definition (open area through the wall's CSG, where open = neither
intact nor packed loose), with thickness as its Phase 1 computation. State the face-state rule on cover and uncover.

### SF-7. §10 assigns no PR to several part-1 laws and mechanisms, and three PRs still have no branch
**Where:** §10 against §3, §5, §6, §1.2.
**Scenario:** Unassigned: breach by remaining thickness (S1), the band gate (S4), sleeping chunks (§1.2), the
`sys.setprofile` tripwire (§6), the bincount region reductions (§9), the `RigProfile` split and the red-gate
disposition (B3, SF-1), F10's `regions_version` and F11's namespaces. Implicit only: integer counts and the zone
operator (presumably PR 7). §2 says mass is never deleted "from day one", but fines land in 8b, so PRs 4 to 8a still
delete struck mass and its heat. PRs 5, 9 and 11 have no branch name (A-N2 again; CLAUDE.md requires
`phaseN/<step>`).
**Fix:** Give every law and mechanism in §1–§9 a PR row, and every PR a branch. Put the band gate in PR 3 (it is
harness), breach by thickness in 8a, and say "from 8b" instead of "from day one".

### SF-8. Region reductions published once per physics step re-adopt A-SF-9
**Where:** §9 ("published once per physics step as a frozen object").
**Scenario:** An NPC strikes the crate between physics steps; its sensor read returns the pre-strike integrity, and
Maxim's cerebellum learns that `strike` did nothing. That is the delayed-credit error the design asks Maxim to fix
(v2 P3), produced by Overdrive's own cache.
**Fix:** Recompute on a cell-write version that actions and physics both bump (A-SF-9's fix), or recompute the
affected regions after each action. The bincount pass stays; only its key changes.

### SF-9. Property caches keyed by topology_version go stale when per-cell state changes properties (A-SF-8, unanswered)
**Where:** §9 (cached conductances in PR 4); §3 (fuel mass, char, bound water, phase progress in PRs 8a and 9).
**Scenario:** After 8a, a burning cell's k and ρc change every step with no `set_material`; the PR 4 cache either goes
stale (wrong physics) or is rebuilt every substep (the cost PR 4 removed). `stable_dt` from per-material bounds holds
only if every state effect is bounded by its material's extremes, which nobody has stated.
**Fix:** Decide the property model in part 1: properties as a function of (material, per-cell state), a stated bound
per material for `stable_dt`, and a second version counter or dirty mask declared in the registry.

### SF-10. world_v2 is now both a record and in force (A-SF-1, repeated one level up)
**Where:** header ("`world_v2.md` and `realtime_lanes_coop.md` stay as records"); §2 ("v2 §2.1 stands"), §5 (v2
§2.4), §7 (v2 §2.2), §8 ("v2 §8 stands"), §10 PR 4 ("The `Simulation` and its integer clock", which is v2 §5).
**Scenario:** The PR 4 implementer builds from v2 §5, which says "the rig field is substeps per physics step" and
sets a memory budget per rig (128 / 512 / 2048 MB). Both contradict D20, and part 1 doesn't say so. v1's sessions,
tokens and B14 refusals (A-SF-1) are still unclaimed by any part.
**Fix:** List the v2 and v1 sections still normative, by number, each with its rig text corrected, or copy them into
the part that owns them. Name the part that owns sessions, tokens and B14.

### SF-11. D20's "one truth" covers physics only; cradles and live deliberation still depend on the machine
**Where:** §0 D20, D21 ("the world dilates and says so"); `docs/architecture.md` ("Cradles and experiments run the
same server headless").
**Scenario:**
- Exp 64 cradles a life per NPC. At the truth, a headless cradle costs roughly 16–20× what it did at laptop (8×
  cells, about 2× substeps). If cradles run at the 0.2 m verification grid to afford it, NPCs grow up in different
  physics precision than they play in, the rig rule again through the back door; if they run at the truth, the
  cradle budget has to be re-measured. Either way it is a Maxim-facing cost nobody has named.
- A weak host dilates the world. With live models, deliberation per world second then depends on the machine
  (v1's DA-11): NPC behaviour differs across machines even though physics doesn't.
**Fix:** In D20, say the truth is the physics truth, and hand both items to part 2 by name: the cradle resolution
(with its cost measured), and what dilation does to deliberation.

### SF-12. D20 makes 0.1 m the minimum host spec, but the measurements don't say on what machine, and rendering tiers are undefined
**Where:** §1.1 (DLP numbers); §9; B5; "rendering tiers: how much of the snapshot the client draws".
**Scenario:** The figures come from the development machine (Accelerate BLAS). A Steam player's 2019 laptop may be
3–5× slower before zones, skins, fuel, SEM and a local model share the CPU. With D20 there's no coarser fallback, only
dilation, and in co-op a weak host dilates for every guest. Also §1.1's "0.05 m … about 1.6× real time" reads as
"1.6× slower"; the DLP table means it runs 1.6× faster than real time in a quiet room and slower during a fire.
"Rendering tiers" don't say whether the server sends coarser frames per tier (snapshot bytes, B5) or the client
downsamples (purely visual, allowed). That falls between part 1 (formats) and part 3 (client).
**Fix:** Name the machine for every measured number. State a minimum host spec as an owner decision, and make B5 one
physics budget at the truth on a named reference machine, plus snapshot bytes per tier. Say which part defines
tiers, and that a tier never changes what the server simulates or what an NPC senses.

## NIT

- **N1.** §1.1 "One truth removes the class" overclaims. P1 shows the old exchange law 2× off the converged answer
  *at 0.1 m* (104 vs 48 MJ/m²). D20 removes the fairness class; the correctness class remains, and it is now
  invisible in play, so the verification harness is the only thing that sees it. Say that, since it is why PR 3
  comes first.
- **N2.** 0.05 m as "the reference" is only a reference in the asymptotic range (P1's 0.05 m figure was 85 against a
  converged 48). Prefer the closed form or a Richardson estimate where one exists, and say when 0.05 m is trusted.
- **N3.** `gas.over(mask)` takes cells; A-SF-3 asked for a region in metres. Under D21 a mask is per level (SF-2).
- **N4.** PR 6's Godot reader should include one 3-D texture upload of a fixture channel on 4.7.2, the risk A-SF-11
  named.
- **N5.** Region ids "never reused" in u16 cap a world's lifetime at 65,535 regions, imagined objects included. Say
  what happens at the cap (a loud refusal).
- **N6.** "Findings for parts 2 and 3 are listed there" can't be checked while those parts don't exist; B2's master
  index fixes it.

## Is the split clean?

Mostly. Matter, laws and formats are the right first part, and the ordering of the three parts is buildable. What
falls between them today: A-SF-1, A-SF-2, A-SF-14 and the NITs (B2); sessions, tokens and B14 (SF-10); rendering
tiers (SF-12); the cradle resolution and dilation's effect on deliberation (SF-11); the thoughts-in-flight load rule
(the A-SF-12 row). Each needs a named owner.

## What I checked and found sound

- **D20 as the root fix.** It removes a constraint rather than adding a mechanism, makes saves, replays and cradles
  portable across machines (A-SF-16 becomes moot), and keeps every sub-cell law the physics review asked for, now
  justified by correctness. The cost is measured and affordable at 0.1 m on the dev machine: about 2 cached substeps
  of 3.9 ms per 0.5 s step, against roughly 0.3 s at 0.05 m. Keeping 0.2 and 0.05 m as verification grids keeps the
  convergence evidence the old rule produced.
- **D21's first half:** refinement from world state, identical on every machine, as deterministic state; and
  dilation reported in the tick status rather than hidden. Both are right; only the budget lever is wrong (B1).
- **The gas consumer interface,** liquids behind the same kind of interface, and mass to a sink instead of deletion
  (with SF-6's naming caveat).
- **Integer counts for incremental state** with a full-recompute property, labels not used as identities, and
  topology batched once per physics step.
- **A face table in the grammar before the fuel PRs** (A-SF-17 / DLP S-11 folded in substance).
- **Save after the lanes, a Godot reader with the protocol, and the 8a/8b split** with rubble moved to Phase 2.
- **The restated fuel acceptance test** (vented burns away, sealed goes out): it can now fail under a wrong burn law,
  which PR 1's sealed-room gate couldn't.
- **CSG in metres as the authored half of ownership** is the right model: it is rig- and resolution-independent,
  cheap for boxes and cylinders, and derivable from the scene's existing ordered carving. It needs SF-5's current-
  matter half and an earlier landing.
- **For Maxim:** nothing here constrains Maxim's types. Sensors stay reductions in metres, and one physics truth
  makes "the physics an NPC grows up in is the game's physics" literally true, subject to SF-11.
