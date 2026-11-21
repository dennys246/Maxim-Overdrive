# Fire model v1: Architecture lens

Reviewed: `docs/design/fire_model.md` at 54358fd, against CLAUDE.md, the charter, `architecture.md`, `roadmap.md`, `foundations_plan.md`, `world_model.md` §0–§10, `tile_and_client.md` §0, §2, §3.2, §5–§7, §11, `boundaries.md` (field registry, write window), fire_ladder L3 §2–§4 and L4 §5, the hot-surface spike's results §5, and `gates`' `core/grid.py`, `core/applier.py`, `core/intents.py`, `adapters/sem/bridge.py`, `core/imagination.py`.

**Counts:** 4 BLOCKER, 9 SHOULD-FIX, 5 NIT.

The diagnosis is sound and the fix is at the root: the flame had no body, and cited flame objects give it one. I agree with the direction. The findings are about where the new state lives, what is quietly loosened, and the scope hidden in "step 6".

---

## BLOCKER

### A-B1. Elements and patches are keyed to cells with a fixed K = 2, so capacity and partition depend on dx
**Location:** `fire_model.md::§2.1` (Containers), also §0.3 ("grid-independent by construction") and §1's last row.

The design says fuel and flames are "sized in metres, beside the grid, not cells". Its containers say the opposite:
- elements are keyed (cell, slot) with K = 2;
- "an object that straddles cells is one element per cell it occupies";
- inventories are "kg/m³ of cell";
- patches are keyed (cell, slot, patch), each holding one ignited-area fraction.

**Failure scenario 1 (slot overflow).** The exit scene (§7): a slat bed, cardboard inside, kindling leaned on the face, a wax starter under it. At 0.2 m an envelope cell holds bed, cardboard and a stick: three fuels against K = 2. At 0.05 m they mostly fall in different cells. The scene is refused at 0.2 m only (the "fits depending on the rig" known gap again) or silently drops a fuel. The resolution rule breaks.

**Failure scenario 2 (partition).** Upward spread along a 1 m stick is decided per patch, one ignited fraction each: 5 patches at 0.2 m, 20 at 0.05 m. A flame tip at a long patch's lower edge raises only its mean flux, so it ignites later than its leading point would, and spread rate depends on dx. This is "average then threshold", and the failure §1's last row cites. §6's subset-independence test is not partition independence. L3 §4 named the straddling object "the adversarial case"; the design dropped that test.

**Fix direction:** give elements identity in metres: an object id, with patches segmented by length or area in metres and rows ordered by (object id, segment). Map them to cells only for coupling, by overlap. Drop the fixed K, or cap it per object instead of per cell. Add the straddle test to §6.

### A-B2. Rate and time convergence across grids is dropped, loosening a gate that is already recorded, and §10 doesn't list it
**Location:** `fire_model.md::§6` (preamble: "Across grids, only outcome classes are graded; rates and times are reported"), §0.5, §1 ("grade class across grids").

What is recorded today:
- `tile_and_client.md` §6.3 item 8 gates `t_crack`, `t_glow` and `t_gone` against the 0.05 m reference at 15%, 15% and 10%, and says "tightened by measurement, never loosened";
- world_model D20 and §1.1 make the verification rule "the 0.1 m answer must lie within a stated tolerance of the 0.05 m reference, and must converge from 0.2 m";
- CLAUDE.md: "If a cross-tier test fails, fix the physics; never loosen the test."

The design replaces all of that with class-only grading plus "reported with their observed order". R4's "peak within ×1.5 on every grid" is a band against data, not agreement between grids. Two grids could sit at 0.6× and 1.4× of the reference and both pass.

**Failure scenario:** after A-B1 lands unfixed, `t_gone` is 1,800 s at 0.2 m and 3,000 s at 0.05 m. Every class gate passes, the playtest passes, and the exit ships with a 1.7× grid dependence that today's tile gate would have refused.

The cited justification is corrected in the same paragraph (current FDS converges at 4 and 2 cm). If the objects are grid-independent by construction, rate convergence is the test that proves it; dropping it hides A-B1's residual dependence. This revises D20, tile §6.3 and a CLAUDE.md rule: list it in §10, or keep the tile §6.3 item 8 gate.

### A-B3. Step 6 becomes a multi-PR research programme, and the plan, the roadmap and the tile spec aren't revised to match
**Location:** `fire_model.md::§6`, §7, §10, §11.5–6.

What the ladder now puts on Phase 1's critical path:
- material table v1 with species, atom and Hess closure;
- a channel registry;
- element and patch tables;
- a 1D in-depth solid with two rate laws fitted;
- flame objects with two flame-height correlations, a contact overlap, view-factor radiation, a visibility cache and clustering;
- the rungs R0, R1, R2a/b, R2.5, R3a/b/c and R4, across PMMA, white pine, plywood, cardboard, paraffin, Jiang's dowels and NIST's crib;
- a pre-registered bench measurement.

None of it is broken into PRs or sized. The spike's verdict was "option 1 is the larger job" and "option 3 (change the exit) becomes the realistic Phase 1 path"; the design does option 1 *and* a harder option 3.

Documents and decisions it changes without naming them in §10:
- `foundations_plan.md` §2 step 6: its "Done when" is still "tile §6.3 passes at three grids", and its "Deferred to Phase 2" line still lists pyrolysis and phase change;
- `roadmap.md` Phase 1's exit bullet, and Phase 2's "Moved from Phase 1 by D26" bullet;
- D23 and D26 moved the lab benchmark tile to Phase 2. R0–R4 *is* a benchmark lab (a cone heater, a crib), so the lab comes back into Phase 1 under another name;
- D28: the heat-debt prototype was meant to come "before more physics breadth". The ladder is physics breadth placed ahead of the tile, so D28's fun test moves out by an unknown amount;
- `tile_and_client.md` §11's requirement-by-step table.

**Dependency inversion:** §6 gives "each rung ... a legibility check: a short clip". Clips need the client drawing elements and flames, which is plan steps 7 (protocol) and 8 (tile), and both come after step 6.

**Failure scenario:** the owner accepts §11 items 1–6; the plan still says step 6 is done when tile §6.3 passes, and nobody can say when Phase 1 ends.

**Fix:** a §10 row for each document above, a step list (R-rungs mapped to PRs and their order relative to steps 7 and 8), and a stated estimate or an explicit "unknown".

### A-B4. Nothing specifies what consumes the new state: wire, client, SEM, save or frame
**Location:** `fire_model.md::§2.1`, §4.1, §10 (world_model §8 row).

The burning, glowing and charring state now lives in element and patch rows and flame objects, not in cell channels. The design never says how each consumer gets it:
- **The client** draws `crack` and `glow` from per-cell arrays. A glowing char patch has no cell channel, and flame geometry (which L4 §5 says the client should size from the server's correlation) isn't on the wire. The exit shows nothing, or the client invents flames, breaking "visuals come from snapshot channels".
- **Protocol v0 (step 7) freezes the grammar.** world_model §8 (DLP S-11) put the face table in it first so "the fuel PRs add rows, not a format". The design replaces that table and adds patches and flames without placing them in the grammar before step 7.
- **SEM.** `bridge.py`'s `temperature_max` and `temperature_mean` are cell reductions. A burning stick in an air cell reads as cold air. §5 says booleans become fractions, but not what reduction produces them from element rows.
- **Save v0** (plan step 9: "grid, scene, actor and pilots tables") gains elements, patches and possibly flames, and none of that is named.

**Failure scenario:** protocol v0 freezes with cell channels only; step 8 renders a crate whose fire exists only server-side, and the fix is a version bump on day one.

**Fix:** a consumers table (client channel or table, SEM reduction, save, digest) for each new container, and the field-registry and grammar entries placed before step 7.

---

## SHOULD-FIX

### A-S1. Tile decisions the design silently contradicts
**Location:** `fire_model.md::§10`.

The design contradicts these decisions without listing them in §10:
- **T13** ("no more paper rounds on the fire physics"). This is one; justified perhaps, but list it.
- **T14** (flame radiation reaches bodies by a point source in Phase 1, and walls in Phase 2). §4.1 radiates to all receiving patches, and §5.1 to body regions.
- **T17** (an accelerant lights the crate). The exit now uses a starter and kindling.
- **T5 / tile §2.1** (one lumped 245 kJ/K body). §5.1 needs per-region incident flux, a skin conduction model and a Henriques integral.
- **Tile §5.1–§5.4** (the constants q''_f = 25, T_p and L_g, and the ledger lines `flame_radiative` / `unreceived`).
- **Tile §5.3's pre-registered failure path** ("the exit fails, and the measured balance goes to the owner"). Say plainly it fired and §11 is that ruling, so the new model doesn't read as a rescue.

**Scenario:** a later session follows T14 (flame radiation into walls is Phase 2) and builds R2.5 to radiate only into bodies.

### A-S2. `ignite` and `extinguish` "kept as lab instruments" reverses two retirements, and the existing fire gaps are left without owners
**Location:** `fire_model.md::§5.4`, §10 (bridge row).

T4 already retired `ignite` ("kindle ... and retires ignite", tile §3.2), and world_model §8 F7 retired `extinguish` in favour of `douse`. Keeping both as instruments keeps `HeatSource(power, radius)` as a second heat path beside the flame objects. That path is the one with the Known gaps "fires heat air to 2.67 million °C" and "a sub-cell source heats one cell".

The design doesn't say which of these it closes and how:
- `test_a_fire_that_has_burned_its_fuel_stops_heating`;
- `test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`, which the roadmap's Phase 1 requires flipped;
- the `TEMPORARY` ceilings in `data/world/actions.yaml`;
- `kindle`'s scheduled sphere-deposit band-aid, which "step 6 removes" (tile §3.2), but into what? A flame object, or a disc onto patches?

**Scenario:** step 6 ships flame objects; the strict red gates stay red with no plan, or are rewritten against the instrument (a loosening).

### A-S3. How elements exchange heat with the dense grid is undefined (one truth)
**Location:** `fire_model.md::§2.1`, §3 items 1 and 4, §4.1 ("Into the gas").

The 1D model's back boundary is "an element's far side, or its neighbour", and its surface balance uses h(T_s − T∞) and εσ(T_s⁴ − T∞⁴). Questions the design leaves open:
- Which T∞: the outside reservoir, or the host cell's temperature?
- Where does the convective (1 − χ_r)Q go? "The zone (the outside reservoir in Phase 1)" exports it.
- Does a stick resting on the concrete floor conduct into floor cells?
- What is an air cell's `temperature` when it holds a burning element?

**Scenario:** tile §6.4's V_floor control turns vacuous because no element heat reaches a cell; or a later ad hoc coupling leaves cell and element temperatures disagreeing, so glow and SEM read two truths.

### A-S4. Existing laws and checks that don't know elements
**Location:** `fire_model.md::§2.1`, §10 (thin-features row).

Each of these reads cells or authored boxes, and the design says nothing about how it treats elements:
- `damage.strike`, the crater and breach logic (world_model §3, "breach by thickness"), and `thermal_degrade`;
- the `crack` channel (tile §5.5 defines it for a bed *cell*);
- `kindle`'s region derivation ("the named solid whose authored box surface lies within 50 mm");
- `imagination.place`'s occupancy check ("smaller than one cell");
- region footprints and ownership.

**The thin-features exemption has no definition.** Nothing says what may be authored as an element rather than a cell. A 0.1 m wooden plank wall authored as a `slab` element escapes the rule, and then breach and strike semantics for it are undefined.

**The rule's text lives in more places than CLAUDE.md:** `architecture.md` "How the rule is kept", the Physics lens question in `code_review.md`, and the imagination Known gap that names thin features as its fix. §10 should name each one.

**Scenario:** an NPC (Phase 4) strikes a crate made of elements. The applier finds a footprint with no solid cells of the crate's region and refuses, or the strike destroys the host air cell and leaves the fuel untouched.

### A-S5. Act vocabulary: two verbs for one act, NPC verbs in a phase with no NPCs, and a "build" the player can't do
**Location:** `fire_model.md::§5.4`, §7.

- §5.4 adds `light` and `apply` "with R3", next to the player's `kindle` (T4), which tile §3.2 (DC-S7) already makes a body affordance for NPCs too. Having two vocabularies for the player and the NPC is two doors.
- Phase 1 has no NPCs (roadmap; O10), so "with R3" puts NPC verb work into Phase 1 without naming it.
- §7 says "the player builds a fire". But `carry`, `drop` and `place` "need item entities", which Phase 1 doesn't plan (`held_item` is a u8). So either the starter and kindling are authored in the scene, and the player only lights, or item entities become new Phase 1 scope.

**Scenario:** the exit script (tile §6.2) can't be written with Phase 1's vocabulary.

### A-S6. No placement table, and material table v1 mixes three owners
**Location:** `fire_model.md::§9`, and the design as a whole (no counterpart to tile §7).

The design never places its pieces in layers. The element, patch and flame code, the correlations, the clustering, the view factors and the visibility cache all go somewhere in core, adapters or game, and the design doesn't say where.

§9 puts these in one table and one loader:
- engine physics data: species, components, reactions and transitions;
- game content: recipes. Tile §7 puts "the bed's φ and σ, fuel calibrations" in game `content/`, which is rights reserved, not Apache;
- the imagination trust surface: variants.

It also never says how today's structural materials (`data/materials/core.yaml`, with `fracture_energy_j_m3` and `degrade_*`) relate to components. Is concrete a recipe, and which id does a cell's u8 `material` hold? Without that there are two parallel vocabularies.

**Scenario:** a recipe edit forces an engine data version bump, and one loader validates chemistry, content and LLM bounds together: the god table.

**Fix:** split by owner: engine `chemistry` (species, reactions), engine `components`, game `recipes`, and `variants` read by `imagination`. Each gets its own strict validator, composed by the loader.

### A-S7. Species, atom and Hess machinery with no Phase 1 consumer
**Location:** `fire_model.md::§2.3` items 2–3, §9.

In Phase 1, products go to "the outside reservoir": no zone reads CO, CO₂ or H₂O, and O₂ is unlimited. Atom balance and Hess closure are good loader checks, but per-species gas bookkeeping is D26's deferred "combustion per zone and its products". That makes it capability with no caller (CLAUDE.md, "A fix ships with a caller"), and the D26 revision row in §10 covers only pyrolysis and fusion.

**Scenario:** species columns freeze in the format untested, and Phase 2's zones find them wrong.

**Fix:** keep the loader's closure checks, and defer species state, or list it as a D26 revision.

### A-S8. Flame objects: state, identity and order unspecified
**Location:** `fire_model.md::§4.1`, §2.3 item 4.

Unstated: whether flames are recomputed per step or persisted; their identity (clustering is connected components, and DLP S-4 says labels aren't identities); whether they are in the digest (§2.3 lists only latches); what draught tilts them in Phase 1; the visibility cache's occlusion and invalidation as the crate burns; whether walls receive radiation (T14).

**Scenario:** two clusters swap label order after a merge; deposit order and float sums change, and replay isn't bit-identical.

### A-S9. The Maxim asks aren't routed into the roadmap
**Location:** `fire_model.md::§11.8`, §10.

MP-1 and MP-2 are Maxim changes. CLAUDE.md says they go "under Phase 3 in `docs/roadmap.md`", with drafts in `docs/maxim_upstream/` where needed. §10 lists no roadmap row, and §5.4's "MP-3 to MP-6 follow" have no ids in the roadmap. L6b does cite Maxim `origin/main` 437ec7b1, so the search rule is met at research level.

**Scenario:** the owner accepts §11.8 and no Phase 3 item exists to track it.

---

## NIT

- **A-N1.** `fire_model.md::§10`, CellStore row: "a channel registry ... landing with material table v1". O34 already puts "the field registry" in plan step 5a, and boundaries §9.1 makes it primary. Name that decision instead of a new registry with a different landing point. Today `CellStore` has 10 public members against the 12 tripwire. The design is right that the tables can't be added as more properties.
- **A-N2.** `fire_model.md::§2.1`: inventories "kg/m³ of cell" make the element's own mass depend on the host cell volume. Per element volume, or kg per element, is the natural unit and survives A-B1's re-keying.
- **A-N3.** `fire_model.md::§6`, Materials: PMMA and plywood are validation materials, not game content. Say whether they ship in `data/materials/` or live as test fixtures, because §9's "recipes (what a scene ... may name)" would otherwise make PMMA authorable in the alley.
- **A-N4.** `fire_model.md::§7` says "every beat is a graded rung", but R3b and R3c are "reported as predictions, class only" with "no dataset". "Every beat is a gated rung, two of them without an oracle" is the honest wording, and §7's next paragraph half says it.
- **A-N5.** `fire_model.md::§10`: the world_model §2 row isn't a revision; move it to §2.2.

---

## Checked, nothing found

- **Root cause vs band-aid:** the fix changes the mechanism (flame contact), not a constant or tolerance; §4.2 keeps T18's spread-from-heat-transfer.
- **Reconstruct, decide, integrate** for the flame deposit: metric quadrature and overlap, nothing at cell centres (§4.1), apart from A-B1's partition.
- **Authoritative server; imagination through validation:** nothing client-side feeds back; imagined objects name recipe, metric geometry and bounded variants, refused not clamped (§9), matching `core/imagination.py`.
- **The bridge never decides** (§5.5): consistent with T18 and `bridge.py`. Henriques' world/Maxim side left to Bio-faithful.
- **Determinism:** integer keys, `bincount`, capped substeps with reported dilation (D21), the identity pattern; only flame identity is open (A-S8).
- **Word budget:** 5,187 of 6,000 (O22). **Size:** `CellStore` at 10 of 12 public members (A-N1).
- **Gap honesty in the design:** §12 states the missing in-crib flux, merging, unpiloted ignition, oracles and GL2b/GL3 plainly; they reach `architecture.md` Known gaps at build time.
