# Fire sub-steps 6.0–6.1 (`fire_solid.md`): Bio-faithful integration

Reader: Bio-faithful integration lens (`docs/code_review.md`). Design: `docs/design/fire_solid.md` on disk in the
`fire-design` worktree (staged, uncommitted). Membrane read in the `gates` worktree at its checked-out HEAD
(`src/simcore/adapters/sem/bridge.py`, `src/simcore/core/frames.py`, `applier.py`, `damage.py`). Maxim read only via
git, at 437ec7b1.

**A correction to the brief first.** The local `origin/main` ref in the Maxim checkout is **50ad83bb**, not 437ec7b1.
437ec7b1 is an ancestor, 10 commits behind. Nothing was fetched. Neither `src/maxim/embodiment/sem.py` nor
`runtime/bio_stack.py` differs between the two commits, so the Maxim facts cited below hold at both.

Counts: **1 BLOCKER, 4 SHOULD-FIX, 3 NIT.**

**Summary.** 6.0–6.1 adds no NPC, no percept and no Maxim ask, and nothing in it works around Maxim. One line of §2,
though, gives the NPC surface a shape before the deferred note can rule on it. It feeds fuel-object surface
temperatures into the existing `temperature_*` region instruments. Those instruments are the omniscient path that
fire_model §5.5 forbids an NPC, and the only `src/` builder that ships them hands them to any Maxim agent. The same
§2 change attaches a `structure` modulator, with `ignite`'s outcome text, to regions that hold only objects. The
deferral to "a separate NPC fire note" has no trigger, and it lumps open Bio findings together under "the rest",
including one (delta1 NS3) that touches the very code 6.0 changes.

---

## BLOCKER

### B1. §2 changes the meaning of `temperature_max` / `temperature_mean` under the same names, which widens the omniscient region instrument to see fuel objects, hidden ones included, with no caller in 6.0–6.1

**Location:** `fire_solid.md::§2` (consumer table, the `frames.CellFrame.reading` row: "adds object reductions for
the quantities objects carry (`temperature_*` over segments' surface nodes)"); `fire_model.md::§5.5` ("give an NPC
an omniscient region instrument (today's `temperature_*` and `breached`)"); `world_model.md::§8` F1 ("A channel's or
sensor's name, units, grid and meaning are fixed for the life of the format. A new meaning gets a new name");
`gates:src/simcore/core/frames.py::QUANTITIES`, `::Frame.reading`; `gates:src/simcore/adapters/sem/bridge.py::region_parts`,
`::to_maxim_entity`; `437ec7b1:src/maxim/embodiment/tool_bridge.py:1005-1020` (the auto-generated "Read all sensors
on <entity>" tool), `437ec7b1:src/maxim/tools/discovery.py:119` (`entity.read_all_sensors()`).

What the tree does today:
- `region_parts` builds one `RegionInstrument` per `QUANTITIES` entry.
- Each one reads `frame.reading(region, quantity)` from anywhere.
- `to_maxim_entity` (in `src/`, not `tests/`) puts them on a real Maxim `Entity`.
- Maxim's `generate_tools_for_entity` gives any agent holding that Entity a read-all-sensors tool, and Maxim's
  discovery tool reads the same sensors by name.

The `RegionInstrument` docstring calls this "an ANALOG divergence … never an NPC's input". That rests on convention
only: no builder separates lab from NPC (delta1 NS3, still open).

6.0 changes what those instruments report in three ways:
1. **Meaning changes, name stays.** `temperature_max` stops meaning "the hottest cell in the region" and becomes
   "the hottest cell or fuel-segment surface node". F1 rules this out for sensors by name. Recorded logs, goldens and
   any `SensorReading` history keep the old name with the new meaning, so readings before and after 6.0 can't be
   told apart.
2. **The omniscience widens.** §1.3 lets cardboard sit inside the crate's footprint where it is air, and its
   `region_id` names the crate. The crate's `temperature_max` would then report the surface temperature of cardboard
   that nothing outside the crate can see or feel. That is the "instrument that measures what no receptor at the
   observer's position could" which leak test 1 (fire_model §5.1) exists to catch. Today's reading at least comes
   from the region's own cells. The new one reaches inside a closed container.
3. **It pre-empts the NPC note.** fire_model §2.2 says segment temperature is what "glow, SEM and the client read".
   §2 answers "how does SEM read it" with "through the region instrument" before the NPC note has ruled. fire_model
   §5.1 points that note toward a different answer: incident flux at the receptor, and sight as "luminance … of
   whatever is in view". Shipping the region-instrument join first makes it the path of least resistance in Phase 4.

**Nothing in 6.0–6.1 calls it.** R0 and R1 are unit tests on `core/solid.py`. The straddle and coupling tests read
coupling totals and the floor. The FDS verification reads the solver's own surface temperature. No 6.0–6.1 test in
§6 reads `CellFrame.reading` for an object. That makes it capability without a caller (CLAUDE.md, "A fix ships with a
caller").

**Failure scenario.** 6.0 ships the change. A Phase 3 or Phase 4 harness, or any experiment, hands
`to_maxim_entity("crate")` to a Maxim agent, as the module docstring invites ("a Maxim agent perceives and acts on a
wall exactly as it does on its own arm"). Through Maxim's generated read tool, the agent learns that the crate is
heating up from cardboard smouldering inside it before any receptor could know. Fear and credit then condition on an
oracle. The LLM prior hides the leak, as fire_model §7 warns. Separately, a replay from before 6.0 and one from after
both report `temperature_max` with different meanings, and no lint catches it, because the name didn't change.

**Fix (cheap).** Delete the `CellFrame.reading` row's change from §2:
- **`temperature_*` keeps cell-only meaning.** The consumer table should say "unchanged in 6.0, with the
  `QUANTITIES` set pinned by a test", the way it does for `damage.py`.
- **Lab readings of object surfaces, if a 6.x test ever needs them, get new names** (F1) on a lab-only surface under
  `tests/`, never in `QUANTITIES`.
- **Name the SEM read path of segment temperature as an open question for the NPC note**, and correct fire_model
  §2.2's "SEM … read" accordingly.

---

## SHOULD-FIX

### S1. The new `Region.solid` join attaches `structure` (`strike`, `ignite`, `extinguish`) to object-only regions, and `ignite`'s text promises an outcome the 6.0 physics can't deliver

**Location:** `fire_solid.md::§2` (`grid.Region.solid` row: "cells, plus a `fuel_objects` index"; `applier` row;
`bridge.StructureModulator.__init__`, `region_parts`: "the same join"), `::§3` ("never into air cells");
`gates:bridge.py::StructureModulator.affordances` ("Start a fire at this structure's surface; it burns until
extinguished"); `gates:applier.py::_ignite` (a `HeatSource` sphere at the authored centroid, into cells);
`fire_model.md::§5.5` (that description "breaks this").

With the join in place, a region made only of fuel objects (a pile of cardboard, a stick) passes
`frame.is_solid(region)`. `region_parts` then gives it a `structure` modulator. `ignite` on it deposits a sphere of
heat into **cells**, and §3 rules that objects exchange heat only with ambient T∞ and with solid cells by contact,
**never with air cells**. The cardboard sitting in that heated air therefore never warms. The act returns
`success=True` under a description that says the region "burns until extinguished". That is outcome text that is
false on the shipped path, the exact §5.5 violation, now extended to fuel.

There is also an undecided case. `applier._check_region` refuses `"the {region} is gone"` when
`not regions[region].cells.any()`. §2 rewrites only the air check ("refuse only a region with no solid cells and no
objects"), so whether an object-only region is refused as "gone" or accepted is left to the implementer.

**Failure scenario.** A lab script, or later a careless Phase 4 wire-up of `region_parts`, calls `ignite` on
"kindling". It succeeds and says the kindling burns, yet the kindling's surface stays at ambient. Any learner that
credits the act records a false success, and any reader of the description is told an outcome. Fire_model §5.4's
remedy (drop `ignite` from `parse_action`, one `kindle` act) is owned by 6.4, after 6.0 has widened the surface.

**Fix.** In 6.0, keep `StructureModulator` and `region_parts` on **solid cells only**: "unchanged in 6.0, like
`damage.py`". Fuel objects get no act surface until `kindle`. State how `_check_region` treats an object-only region,
with a test.

### S2. Object-only regions read `integrity = 0.0`, as if destroyed

**Location:** `fire_solid.md::§2` (`damage.py` "unchanged in 6.0"; region membership as cells ∪ objects);
`gates:damage.py::region_integrity` (`… if n else 0.0`).

Once object-only regions are legal regions, the shipped instrument set reports `integrity` 0.0 for an intact stick,
because the region has no original solid cells. A lab instrument that reports a pristine object as destroyed is a
wrong reading, not a gap, and it is the default the NPC note would inherit.

**Failure scenario.** A lab run or a future agent reads `integrity` on the "kindling" region at t=0, sees 0.0, and
treats it as destroyed or "gone": nothing to act on, nothing to fear.

**Fix.** Either keep object-only regions off the instrument surface in 6.0 (the same move as S1), or state the
reading (NaN with an "undefined" schema, or a refusal) and test it. Don't let 0.0 stand by accident.

### S3. The NPC-note deferral has no trigger, and "the rest" leaves specific open Bio findings without an owner, one of them in code 6.0 changes

**Location:** `fire_solid.md::§7` (last row: "The NPC surface, Maxim asks, lesson 24's wording (Bio NB1, NB2 and the
rest) | a separate NPC fire note, ruled on its own; none of it blocks 6.0–6.1"); `reviews/fire_model/delta1_bio_faithful.md`
(open S2, S7, N3; new NB1, NB2, NS1–NS5, NN1–NN4); CLAUDE.md O25 (`deferred` needs "a reason and a trigger").

The row is a deferral without a trigger. The note has no date, no "before step N" and no roadmap row. The delta1 Bio
review left 3 round-1 findings open and raised 11 new ones. "And the rest" doesn't list them, so a reviewer can't set
`deferred` on any of them from the tree. Three of them bind a moment that comes before Phase 4:
- **NS3 (which builder `to_maxim_entity` becomes)** concerns shipped `src/` that 6.0 itself edits (`region_parts`,
  §2). "None of it blocks 6.0–6.1" is false for NS3 as long as B1 and S1 stand. If they're fixed by leaving the bridge
  untouched, NS3 still needs a trigger, because `to_maxim_entity` stays a lab surface in `src/`.
- **NS5 (lesson 24 exports the leaking sight sensor)** is live documentation that other engines read today.
- **NB1 and NB2 (the MP-1 premises)** must be corrected before any MP-1 draft lands in `docs/maxim_upstream/`.
  fire_model §11 item 10 says each ask "needs a roadmap row under Phase 3". The roadmap has OD-C10 but no MP-1 or
  MP-2 rows (`docs/roadmap.md`, grep).

**Failure scenario.** 6.0–6.4 build and ship over several weeks. The note is never written because nothing schedules
it. Step 5 freezes vocabulary v1 (the held-flame lifecycle row in §7 *is* tied to step 5, but the NPC builder and
`ignite`'s removal aren't). Then Phase 4 finds `to_maxim_entity` in `src/` with `ignite` and object-aware omniscient
instruments, the exact delta1 NS3 scenario, now aggravated by B1 and S1.

**Fix.** Give the row a trigger: "the NPC fire note is ruled before step 5 ships vocabulary v1, and before any MP-*
draft enters `docs/maxim_upstream/`". List the delta1 Bio ids it owns (S2, S7, N3, NB1, NB2, NS1–NS5, NN1–NN4).
Either take NS3 into 6.0's scope or state that 6.0 leaves the bridge untouched (B1, S1), which is what makes "doesn't
block" true.

### S4. Whatever object reduction survives, its weighting is unspecified and, done the obvious way, depends on dx

**Location:** `fire_solid.md::§2` ("object reductions … `temperature_*` over segments' surface nodes");
`gates:frames.py` module docstring ("Readings are reductions over a region's cells, so they read the same at every
grid spacing"); CLAUDE.md, the resolution rule and "every consumer reads at its own scale".

`temperature_mean` today is a count mean over cells. Joining it with segment surface nodes needs a weighting, and the
design gives none.
- **A pooled count mean:** cells scale as dx⁻³ and segments are fixed in metres (§1.1), so the objects' share of the
  mean changes 64× between 0.2 m and 0.05 m. Same scene, different reading per rig.
- **Volume and area together:** mixing a volume mean with an area mean has no unit-coherent answer at all.

Under B1's fix this goes away with the join. It is listed separately because the NPC note will need *some* reduction
of segment temperature (for luminance, or for radiant flux at a receptor), and that reduction must be area-weighted
in metres, from the receptor's view, never a pooled count with cells.

**Failure scenario.** The join ships as a pooled mean. A cross-tier comparison of the crate's `temperature_mean`
then differs across tiers by an amount set by the cell count, and a later NPC note inherits the reduction because it
is "what the frame already computes".

**Fix.** With B1, none is needed. Otherwise, specify it (per-region area-weighted surface temperature in its own
named quantity) and add a cross-tier test for it.

---

## NIT

- **N1. `kindle`'s target derivation lost its row.** `fire_model.md::§2.2` lists "`kindle`'s target derivation
  (§5.4)" among the occupancy consumers. `fire_solid.md::§2`'s table and `::§7` drop it. It is an act-surface element
  (the nearest fuel-object or solid surface within 50 mm, `ambiguous_point` on a 1 mm tie) that depends on 6.0's
  geometry tables. Add it to §7, owned by 6.4 with `kindle`'s pilot. Also check that the `objects` geometry columns
  are enough for a nearest-surface query on rods and slabs in metres.
- **N2. Snapshot names diverge from fire_model without saying so.** `fire_model.md::§9.2` names `segment_glow` and
  `burning` (the ignited area fraction). `fire_solid.md::§5.3` ships `surface_temperature_c` and `ignited_fraction`,
  and keeps `burning` reserved (Wire WT-S6). The Bio content is fine: it is a fraction, not a boolean, and it goes to
  the client, not an NPC. But fire_model §9.2 and §2.2 need the matching edit, or a later reader takes `burning` for
  the NPC fraction fire_model §5.3 talks about. One line in §5.3: "supersedes fire_model §9.2's names".
- **N3. Pin the instrument set.** Whatever B1 and S1 settle, add a 6.0 test that `QUANTITIES` and the `structure`
  affordance set are exactly today's. Then a later sub-step can't add `burning`, `ignited_fraction` or an object
  reading to the region-instrument path (fire_model §5.1: fractions "never reach an NPC through a region instrument")
  without touching a test. Prove it by adding a quantity and watching the test fail.

---

## Questions asked of this lens, answered

- **Does 6.0–6.1 expose state to the bridge or an NPC?**
  - Yes, through `CellFrame.reading` (B1, S4) and through the `Region.solid` join into `region_parts` (S1, S2).
  - The snapshot tables go to the client only and carry fractions, not booleans (N2).
  - Region membership by `region_id` is the channel B1's hidden-cardboard leak travels through.
- **Does it respect fire_model §5.5 and the prior reviews?**
  - **No omniscient instrument:** violated by widening (B1).
  - **No outcome text:** violated by extension (S1).
  - **Fractions, not booleans:** respected.
- **Does the deferral orphan anything?** Yes, formally: no trigger, no list (S3), and NS3 sits in code 6.0 edits.
- **Does 6.0 freeze something the note would need different?** The SEM read path and the reduction of segment
  temperature (B1, S4). The snapshot's u8 display quantisation doesn't constrain the note, because percepts read
  server state, not the wire.
- **A workaround of Maxim?** None found. 6.0–6.1 makes no Maxim call, adds no Maxim construction and asks nothing of
  Maxim. Searched 437ec7b1 for how an `Entity`'s sensors reach an agent: `tool_bridge.py` and `discovery.py` read
  every sensor by name, and that is why B1 matters. The §3 ambient sink is a physics simplification, not a Maxim
  workaround.
