# Architecture lens: world_v2.md (design v2 draft, at d596418)

Reader: Architecture. Inputs: CLAUDE.md (brutal honesty; the resolution and reconstruct-decide-integrate rules),
`docs/code_review.md` ("Design reviews", the Architecture lens), `docs/architecture.md`, `docs/roadmap.md` and
`docs/standards_backlog.md` (here and in `.worktrees/act-validation`), the design, v1 (`realtime_lanes_coop.md`),
`reviews/realtime_lanes_coop/delta1_architecture.md` and `README.md`, and `research/states_of_matter/architecture.md`
and `sem.md`. Checked against code in `.worktrees/act-validation` (`world/grid.py::Region`, `MaterialGrid.paint`,
`world/scene.py::_check_no_solid_overlaps`, `footprint_of`, `sem_env/bridge.py::parse_action`, the reach and
`centroid_m` code, `data/world/actions.yaml`) and Maxim (`embodiment/sem.py::Entity`, which has a free
`entity_type`).

Counts: 3 BLOCKER, 17 SHOULD-FIX, 8 NIT.

**The short answer to the lens's question.** Containers by phase is the right structure for solids and gases, and the
cheapest way to keep the resolution rule for fluids. It isn't a band-aid. What makes it expensive to undo is not the
idea but three things v2 leaves out or contradicts: (1) the gas *consumer interface* that the research made the
condition for swapping zones for a finer gas model later, which v2 dropped (SF-3); (2) liquids as per-zone pools,
which lose position and can't hold the puddles, spills and molten pools that v2's own SEM and lab sections ask for
(SF-3, SF-4); (3) rubble as mobile cells (decision 14), which v2 adopts without working out what it does to strikes,
breaches, derived fields and caches (B3, SF-8, SF-10). The order of work is mostly buildable. The weak points are the
protocol "freeze" (it freezes frames only, with no second reader until PR 11), save v0 landing before the lanes, and
PR 7, which is three PRs' worth of physics plus Phase 2's structural support.

## Fold check: delta1_architecture (DA-1 to DA-24)

v2 says the four `delta1_*.md` files are "folded here for the first time". For this lens that is not true: 5 of 24
are folded, 2 partly, and the rest are neither folded nor answered in writing, which `docs/code_review.md` step 4
requires for every BLOCKER and SHOULD-FIX.

| Id | Sev | Verdict | Where, or what's missing |
|---|---|---|---|
| DA-1 | B | Folded | §6 delivery at `max(T + d_min, first tick after arrival)`; stub releases at T + L |
| DA-2 | B | Folded | Decision 11 and §6's world-time latency mode for cradles. Where the mode runs is still open (NIT N3) |
| DA-3 | B | Folded in substance, wrong in text | §6 says "PR 3 builds the lane skeleton; PR 4 only adds to it", v1's numbers. In v2 the skeleton is PR 5 and the lanes PR 10 (SF-2) |
| DA-4 | S | Moot or silent | "deadline" is gone from v2, but v2 says "v1 §4 stands", and v1 §4.2 and §4.3 still say "deadline" and "request-id order". DD3's single sort fixes the order, but v1's text is still in force (SF-1) |
| DA-5 | S | **Not folded** | NPC-originated intents: tick, order, validation, logging. Nothing in v2 |
| DA-6 | S | **Not folded** | Load rule for thoughts in flight. v2 §8's save contents don't mention thoughts at all (SF-12) |
| DA-7 | S | Folded | §5 "Everything `Simulation.step` reads is hashed world config" |
| DA-8 | S | **Not folded** | Header pinned vs provenance fields, record size bounds. Without the split every golden log fixture goes red on the next commit (SF-11) |
| DA-9 | S | Folded in code | `sem_env/bridge.py::parse_action(affordance, params, limits)` takes no `World`. Sound |
| DA-10 | S | Partly | §5 adds a keyword-only clock for `RegionSensor`. Missing: `SensorReading.timestamp`'s epoch, the snapshot's time fields moving to `StepOutputs` |
| DA-11 | S | **Not folded** | v1 §3.1's "the dial never changes the outcome class" still stands. With live models the dial and the rig's dilation change NPC deliberation per world second, which is the resolution rule reached through timing. Decision 11 covers cradles only |
| DA-12 | S | **Not folded** | CLAUDE.md still says "Never work around it in this repo", with no end state for a declined proposal |
| DA-13 | S | **Not folded** | The roadmap's Phase 3 still lacks v1 items 10 to 18. `hybrid_1_5_line_DRAFT.md` cites items 11, 12, 13 and 17, while the roadmap's items 10 and 11 are now PR 1's two SEM items: two meanings for "item 11" (SF-14). B15 still says "A lint can check both" and "open" |
| DA-14 | S | **Not folded** | P5 names #1361 but not the §(g) rows (reflex cooldowns, PainBus refractory) |
| DA-15 | S | Partly | See SF-13 for what's still missing. The split (docs that state the accepted design land on acceptance) isn't adopted: v2 lands everything "in the PR that lands each piece" |
| DA-16 | S | **Not folded** | No table of which Maxim item blocks which Phase 4 capability, and no fallback if Maxim declines |
| DA-17 | N | Moot | |
| DA-18 | N | Open | There is no `reviews/world_v2/README.md` yet recording how v2 folds anything |
| DA-19 | N | **Not folded** | §12's "Not now" omits LAN play, NAT traversal, prediction and rollback, accounts |
| DA-20 | N | Partly | See N3 |
| DA-21 | N | Moot | P1 to P7 replace the list |
| DA-22 | N | **Not folded** | `substeps_per_physics_step` still couples to `physics_every_ticks` with no loader refusal |
| DA-23 | N | **Not folded** | The seed as a required `Simulation` constructor argument |
| DA-24 | N | **Not folded** | An `overtaken` refusal code for the stale-refusal meter |

## BLOCKER

### B1. The fold claim is false: 11 SHOULD-FIX and 5 NIT findings from delta1_architecture are dropped without an answer
**Where:** `world_v2.md` header ("folded here for the first time"), §5, §6, §8; the table above.
**Scenario:** The owner accepts v2 on the strength of "folded". PR 5 commits golden intent-log fixtures with the
code SHA in a refused header field (DA-8), and they go red on the next commit. Someone then loosens the match ad hoc,
which is exactly what DA-8 warned against. PR 9 ships save v0 with no rule for a thought in flight (DA-6). Phase 4
finds that NPC intents have no tick or order (DA-5). Each was found, written down and then lost. That breaks the
charter's rule that every BLOCKER and SHOULD-FIX is folded or answered in writing, and CLAUDE.md's first principle.
**Fix:** Add a fold table to v2 (or `reviews/world_v2/README.md`) for every delta1 file, with one line per finding:
the section where it's folded, or the written reason it isn't. Change the header to say what was actually folded.
Until then, v2 isn't ready for the owner's decision.

### B2. The region id array doesn't remove PR 1's overlap rule or its known gaps, because v2 keeps the footprint that causes them
**Where:** §2.4 ("removes PR 1's interim rule ... and its two known gaps"; "A `Region` keeps its authored footprint
for 'is this point on it' and for where fires land"). `act-validation`: `scene.py::_check_no_solid_overlaps` (its
docstring gives the reason), `grid.py::MaterialGrid.paint` ("A later paint takes cells from any earlier region"),
`bridge.py` reach and `centroid_m`, and `docs/architecture.md`'s Known gaps, which say the id array "removes both".
**Scenario:** Per-cell exclusive ownership already exists at `act-validation`: `paint` takes cells from earlier
regions, so `Region.cells` is already one owner per cell, just stored as masks. The overlap rule exists for a
different reason: the *footprint* is a bounding box in metres, and reach and fire placement read the footprint, not
the cells. PR 3 builds the id array and, following §2.4, deletes `_check_no_solid_overlaps`. A scene puts a steel
sign inside a named wood crate's box. A strike or `ignite` aimed "at the crate" lands by footprint on the sign's
cells and breaks or heats the sign. That is the bug PR 1 closed. The other two gaps behave the same way: a burnt-out
crate still owns its footprint, so `ignite` still lands in air; a hollow region's centroid is still in air. The id
array is a storage change (it fixes the 5 MB-per-region cost) and nothing more.
**Fix:** Separate the two claims. (a) The id array replaces masks, and the overlap rule stays. (b) Removing the rule
needs a new reach and placement semantics. Following §3.0, that is the authored geometry (the exact primitives, not
their bounding box) intersected with the matter the region still owns, read as a volume-weighted reduction in metres,
so it is both current and rig-independent. Design that in v2, or record it as an open item, and correct
`docs/architecture.md`'s "removes both" in the PR that lands the id array.

### B3. Decision 14 changes what a strike does on the shipped path, and v2 doesn't say what a breach, a crater or a region is afterwards
**Where:** §4 ("A strike or a burn no longer deletes solid mass"; settling "per cluster, on events"); §3.3
(`breached` "stays a threshold on connectivity"); §11 PR 7 ("loose solids"); `tests/test_damage.py`'s crater
closed form; `docs/architecture.md` (craters within 25% of the closed form; the breach red gate).
**Scenario:** PR 7 lands. An NPC strikes a 0.4 m concrete wall. The fractured cells become loose solid *in place*,
because settling runs per cluster on events and its rule isn't designed. Then:
- The hole is full of rubble. Whether the wall is `breached` depends on whether loose cells count as open, which v2
  doesn't say. Gas through rubble "at a reduced open area" suggests partly.
- The crater closed form compares destroyed volume, but now nothing is destroyed. The test has no defined meaning.
- Settling moves cells. `original_material` and `region_id` were derived from the scene, so they can no longer be
  rebuilt, and the save's "derived fields recomputed on load and checked against a digest" (§8) fails after the first
  settled strike. Does crate rubble keep the crate's region id? If so, `integrity` and `breached` on the crate read a
  pile on the floor. If not, what owns it? N1's `matter` kind is deferred.
- A binary outcome that agrees across rigs at least above the threshold band today, breach, now depends on a
  settling rule whose cross-tier behaviour nobody has measured.
**Fix:** Before PR 7 is scoped, write four definitions into §4: when a loose cell counts as open, for gas, for
breach and for passage; what the crater test measures (fractured volume); which fields become saved state once cells
can move (at least `region_id`, `original_material` and the loose fields), with the derived and saved split in §2.1
and §8 updated; and who owns rubble's identity. Then either design settling with its own closed form and cross-tier
test, or take settling out of Phase 1 (SF-5) and state what a strike leaves until it lands.

## SHOULD-FIX

### SF-1. v1 is both "a record" and in force, and three of its sections are in limbo
**Where:** header and Supersedes ("`realtime_lanes_coop.md` becomes a record"); §5 "v1 §2 stands", §6 "v1 §4
stands", §8 "v1 §7 stands"; v1's own banner ("Kept as the record"). Not mentioned at all: v1 §3 (dial, day,
experience clock, 24-hour play), §5 (sessions, host and guest tokens, `TimeAuthority`, host-leave pause) and §6 items
10 to 18.
**Scenario:** The PR 5 implementer reads v2's order of work: "Protocol v0 with the self-describing frame grammar,
plus the lane skeleton". Sessions, tokens, `hello` deadlines and the B14 refusals (v1 PR 3's whole test list, the 41
trust-boundary rejection paths) aren't named anywhere in v2, and v1 says it's only a record. Either they're dropped
by accident, or they're built from a superseded document whose `deadline` and ordering text (DA-4) contradicts v2.
**Fix:** List which v1 sections stay normative, by number, and which are replaced. Put sessions, tokens and B14 in
PR 5's row explicitly. Better: make v2 self-contained for anything a PR will be built from.

### SF-2. §6 still uses v1's PR numbers
**Where:** §6 last bullet ("PR 3 builds the lane skeleton; PR 4 only adds to it ... PR 3's golden fixtures already
include the `busy` error code") against §11 (PR 3 is `sim-clock`, PR 4 the material table, PR 5 the protocol and
skeleton, PR 10 the lanes).
**Scenario:** Someone building PR 3 (`sim-clock`) reads §6 and puts the simulation-lane thread, `host_seq` and the
log into it, before there's a protocol. That is the PR boundary DA-3 fixed, broken again.
**Fix:** Renumber §6 to PR 5 and PR 10. Name every PR's branch (N2).

### SF-3. The design drops the gas consumer interface, and liquids as per-zone pools are the real pigeon-hole
**Where:** §2.1 (Liquid: "pools held by zones ... level from the zone's open-volume profile"); §2.2; §7 N1
("`matter` (tracked puddles, clouds and rubble clusters)"); §11 ("Phase 2 adds ... a fixed gas grid"). Research
`architecture.md` §3.3: "Design the consumer interface so the swap doesn't touch consumers ... `gas.at(zone)` and
`gas.over(mask)`".
**Scenario:**
- Gas: PR 6 lets combustion, the SEM zone sensors and the frame writer read `zone.species_kg` directly, because v2
  never says they mustn't. Phase 2 adds the fixed 0.2 m gas grid (or a two-zone smoke layer) for "smoke drifting down
  the alley" or "crouch under the smoke", and every consumer has to be rewritten. That is the lock-in the owner is
  worried about. The research had the escape hatch and v2 dropped it.
- Liquids: a pool per zone has a level, not a position. A beaker spilled in the wet lab becomes a uniform film over
  the whole room floor. A melted steel beam becomes a molten layer from wall to wall. The "tracked puddles" that N1
  names, and that an NPC would perceive and avoid, have no representation in the world at all, so the SEM entity
  would be a fiction beside the cells, which is the thing N3 forbids for `target_effect`. This is Phase 2, but §2.1's
  table and the registry's container enum present it as decided.
**Fix:** Put the consumer interface in §2.2 as a rule for PR 6: consumers read gas only through
`gas.at(zone)` and `gas.over(region_in_metres)`, and liquids the same way. In §2.1, mark the liquid container *not
decided*, and name the rig-independent local candidate (a heightfield or a volume per column on the same fixed 0.2 m
grid the gas grid would use), so Phase 2 chooses between per-zone pools and local liquid from a scene that needs one.
Keep N1's `matter` kind tied to what the container model can actually hold.

### SF-4. The lab's Phase 1 rooms need physics that v2 schedules for Phase 2
**Where:** §9 table (only the wet lab and lower level are marked Phase 2); §3.1 (boiling "pool, cell"); §11 ("Phase 2
adds pools, melting and freezing, evaporation"); §2.2 ("Rooms are isobaric").
**Scenario:** PR 11 builds the lab. The cryo store needs liquid nitrogen boiling off: a liquid, a pool and boiling,
all Phase 2. The coolant loop needs coolant boiling and steam: the same. The vented burn bay lists a "smoke layer",
which the research reserves as `upper_layer_*`, "not built". PR 11 then builds three Phase 2 mechanisms under a
Phase 1 heading, or ships rooms whose lesson the physics can't teach.
**Fix:** Mark the cryo store, the coolant loop and the smoke layer as Phase 2. If the cryo store is wanted in
Phase 1, say how: LN₂ as an authored N₂ gas source with a heat sink, with no liquid. That's honest and cheap.

### SF-5. PR 7 is too big, and pulls Phase 2's structural support into Phase 1
**Where:** §11 PR 7 ("Fuel mass, surface skin, pyrolysis, O₂ and products per zone, vents, strength by mass
fraction, loose solids"); §4 (connectivity against anchored support, angle-of-repose settling); roadmap Phase 2
("Structural support: cells left unsupported fall as debris").
**Scenario:** One PR carries the fuel field, a new per-face state (SF-17), pyrolysis, zone combustion with
extinction, vents, a new strength model, connectivity, settling, the loose and packing fields, the `extinguish`
redefinition, two red-gate flips and the envelope's removal. Its review round needs Physics, Executor,
Architecture, Wire, Bio-faithful and Determinism on all of it, and every fold re-runs them. For a small team that's a
branch that lives for weeks and is reviewed shallowly. The exit test (sealed starves, vented burns away) needs none
of the loose-solid work.
**Fix:** Split PR 7 into `phase1/fuel` (fuel, skin, pyrolysis, zone combustion, vents, strength by mass fraction:
the two red gates) and a separate rubble PR, or move rubble to Phase 2 where the roadmap already has structural
support. If rubble moves, reserve its fields in the registry with defaults so save v0 stays additive, and settle B3's
definitions anyway.

### SF-6. PR 6 takes air out of the conduction solve but doesn't say what replaces it, or where a source's power goes
**Where:** §2.1 ("No gas in cells. An air cell's temperature becomes its zone's"); §11 PR 6 ("air out of the
conduction solve"); research §3.2 (solid-to-zone surface exchange h·A·(T − T_zone); a Newton-cooling closed form;
crate numbers "re-derived, not carried over").
**Scenario:** PR 6 lands before the fuel model. Fires are still sphere sources, and `World._power_field` still falls
back to air cells when there's no solid under a sphere. With air gone from the solve, that power has nowhere defined
to go. If it goes into the zone, 500 kW into the crate room's roughly 22 kg of air is about 20 K/s of zone heating,
which is the fuel gap again, spread over the room. Without a surface exchange term every solid becomes adiabatic.
v2's table doesn't name the exchange, its coefficient (a new tunable for `data/`) or its closed form. The crate's
cross-tier numbers are then re-derived twice, in PR 6 and PR 7.
**Fix:** PR 6's row names the surface exchange with its closed form and cross-tier test, says where an external
source's power over open cells goes (into the zone, through the ledger), and states that the fuel-gap red gate stays
red until PR 7. Consider landing PR 6 and PR 7's heat path together, so the crate numbers are re-derived once.

### SF-7. The power-field caching fix is dropped from sim-clock, but sparks and torches still need it
**Where:** §5 ("Fire power comes from burning cells, so the 453 ms `_power_field` cost at max disappears rather than
just being cached"); §11 PR 3's contents (no caching); v1 §2.3 ("the root fix comes first", before any real-time
loop); research §3.2 ("The sphere-overlap deposit remains only for external sources such as a spark or a torch,
which v1's caching fix covers").
**Scenario:** PR 3 raises substeps 3× / 1.5× / 1.125× (DX1) without the per-source caching. PR 5 starts the
real-time host on that cost, and the max profile runs at about 0.4× (v1's table) or worse for PRs 5 to 7. After PR 7
the sphere deposit still exists for every external source. v1 called the caching the root fix, and v2 drops it
because of a cost that only disappears for one kind of source, two PRs later.
**Fix:** Keep the per-source overlap, computed once over its bounding box and cached behind `topology_version`, in
PR 3. It's small, and it stays correct after the fuel model.

### SF-8. Per-material property caches and topology-keyed invalidation don't fit a world whose properties are per-cell state
**Where:** §5 ("Precomputed per-material bounds remove the per-substep rebuild of conductances"); §2.2
(`topology_version` from `set_material` only); §2.1 (fuel mass, packing fraction, phase-change progress); §3.2
(strength by mass fraction); bound water in drywall and concrete.
**Scenario:** A burning wood cell loses fuel mass every physics step, so its ρc and k change continuously. Char,
bound water and packing fraction do the same. None of these is a `set_material` call, so `topology_version` doesn't
move, and caches of k, ρc and face conductances keyed by it go stale. Either they're rebuilt every substep, which is
the cost v1 removed, or they're wrong. "Per-material bounds" for the stability limit only hold if every
continuous-state effect is bounded by its material's extremes, which nobody has stated.
**Fix:** Decide the property model in v2: properties are a function of (material, per-cell state), with a stated
bound per material for `stable_dt`, and a second version counter (or a dirty mask) for state-driven property changes.
Put the dirty mask in the registry's process declaration so the lints can see it.

### SF-9. Region reductions cached per physics step go stale after an action, recreating P3's problem inside Overdrive
**Where:** §2.4 ("cached once per physics step, not recomputed on every read"); CLAUDE.md ("Actions change cells").
**Scenario:** An NPC strikes the crate at tick 1203. Physics runs at 1205. A sensor read at 1203 or 1204 returns the
cached pre-strike integrity, so the NPC (and Maxim's cerebellum, which reads sensors in the same call) learns that
`strike` did nothing. That's the delayed-credit error §7 P3 asks Maxim to fix, produced by Overdrive's own cache.
**Fix:** Key the cache to a cell-write version that both actions and physics bump, not to the physics step.

### SF-10. Two rig dependences in the rubble model: the fines split and chunks as entities
**Where:** §4 ("Mass finer than any cell (dust, powder) becomes the zone's soot-and-fines species"; "laptop rubble
is 0.2 m chunks and max rubble 5 cm chunks"; "The client groups ... the grouping is the client's"; "For Maxim, a chunk
is a real thing, an entity").
**Scenario:**
- If "finer than any cell" means finer than *this rig's* cell, a strike at laptop puts more mass into airborne fines
  than the same strike at max. Zone soot, visibility and breathing then depend on the rig, which breaks the resolution
  rule.
- If chunks are entities an NPC perceives and later carries, the number and size of entities differ per rig, so NPC
  perception and affordances differ per rig.
- And if the client does the grouping, the player and the NPC see different rubble. The server is authoritative, so
  it must own anything an NPC can perceive.
**Fix:** Take the fines fraction per strike or per burn from material data, a kg/kg independent of the cell. Define
rubble entities on the server, as clusters above a minimum volume in metres. The client draws them and may subdivide
them visually.

### SF-11. The "protocol freeze" freezes frames only, and has no second reader until PR 11
**Where:** §1 ("a new field never forces a protocol bump"); §8; §11 PR 5 ("This is the protocol freeze"), PR 11
(the Godot client); v1 §7 (closed schemas for every JSON message); research §2.1 ("Verify this on the pinned engine
before freezing the delta layout").
**Scenario:**
- PR 6 adds zones, so `welcome` needs its zone list. PR 7 adds `vent` and `douse`, and the error vocabulary grows
  (`overtaken`, DA-24). `welcome`, `act_result` and `error` are closed JSON schemas, so each is a protocol bump,
  contrary to §1.
- More seriously, the grammar is frozen with Python as its only reader. B3's rule that golden fixtures are "decoded
  by the Python tests and by the GDScript client tests" can't be met until PR 11, six PRs after the freeze. If Godot
  4.7.2 can't upload a channel the way the grammar assumes (an f16 3-D texture, a table layout, `ImageTexture3D`
  partial updates), the frozen grammar changes after everything was built on it.
**Fix:** Freeze `welcome` in PR 5 with every catalogue it will carry (an empty zone list is fine), or extend the
required and optional rule to message fields. Move a minimal Godot reader, the fixtures decoded plus one texture
upload, into PR 5 or right after it, ahead of zones and fuel. That's also the earliest visible result for a small
team, against an order that otherwise shows nothing until PR 11.

### SF-12. Save v0 lands before the lanes, and v2's save omits checkpoint state the lanes add
**Where:** §11 (PR 9 save v0, PR 10 lanes); §6 (the stub "releases it from checkpointed state at exactly T + L";
`max_age_ticks`; request ids); §8 save contents; v1 §2.1 ("A save is a `Simulation` checkpoint plus ... the thoughts
in flight"); DA-6.
**Scenario:** PR 9's heavy-mode test passes with no thoughts in the world. PR 10 adds a stub's pending result
scheduled at T + L, which is `Simulation` state. A save taken mid-thought then loses it, and the heavy-mode test only
catches that if PR 10 extends a format already committed as v0. Save v0 was placed last precisely so no saved
content would change afterwards.
**Fix:** Either reserve the in-flight request table in save v0, with DA-6's load rule (live requests failed with
`save_load`, stub requests recomputed) and a mid-thought heavy-mode test using the stub, or move save v0 after the
lanes.

### SF-13. Supersedes is still incomplete
**Where:** §Supersedes. Missing, beyond what DA-15 listed and v2 kept:
- **CLAUDE.md:** "Performance: turn time"; the single "per-launch token"; Layout entries for the `Simulation`
  package, `server/`, `data/world/fields.yaml`, `data/sem/vocabulary.yaml` and `data/server/`; "Push back on Maxim"
  (DA-12).
- **`docs/code_review.md`:** the Executor entry point `World.advance`; the Call contract row; Lifecycle's "turn
  start and end"; Performance's "the turn loop" and "per turn".
- **`docs/architecture.md`:** the diagram ("fixed turn", "Maxim agents (AgentPool)"); "interpolation between turns";
  the SEM section's copy of "only `World.advance` moves time"; "far less than a turn of physics"; the Known gaps PR 1
  added that B2 says the id array won't remove.
- **`docs/roadmap.md`:** Phase 0's "turn loop"; Phase 1's "Save format v0: the world grid plus the scene spec";
  Phase 1's missing sessions and co-op line; Phase 2's "Convection" and "Close the known gap: late-burn lag" (both
  now Phase 1 work); Phase 3's header ("the 1.4 line") and exit; Phase 4's three NPCs "on the first tile" (the
  ripperdoc clinic is no longer the first tile) and "Movement runs in substrate-primary mode".
- **`docs/standards_backlog.md`:** B3 (six fixtures, Godot as second reader), B4 (heavy mode, embedded registry), B9
  (the ledger property replaces "energy is conserved"), B14 (the `server/` exemption, a single token), B15 (DA-13's
  rewording), and every "Phase 1 step N" in "Lands with".
- **`docs/maxim_upstream/`:** the hybrid draft's item numbers (SF-14) and the Exp 64 draft's tile and NPCs.
- **Code and tests:** `tests/test_snapshot.py`'s fixed-key assertion, the crater test's meaning (B3),
  `RegionSensor`'s timestamp, `snapshot()["time_s"]`, the determinism scan's `server/` exemption.
**Fix:** Add each line with what it becomes. Land the doc lines that state the accepted design (roadmap Phase 3
items, CLAUDE.md rules, the review charter) on acceptance, not with code (DA-15's split).

### SF-14. Phase 3 numbering now has three schemes that collide
**Where:** v1 §6 items 10 to 18; `act-validation`'s roadmap items 10 and 11 (validation in the executor; done-to vs
done-by); v2's P1 to P7 ("PR 1's items 10 and 11 become P2 and P1"); `hybrid_1_5_line_DRAFT.md` ("item 11", "(12)",
"(13)", "item 17").
**Scenario:** A Maxim reviewer follows the hybrid draft's "Phase 3 item 11" and lands on the roadmap's affordance
direction item, not the Default Network. v2's "renumbered to fold in v1's items and P1–P7" doesn't say into what
numbers, so the collision persists until some later PR.
**Fix:** Decide the final list in v2: one numbering covering v1's 10 to 18, PR 1's two items and P3 to P7, each with
`Argues against:` (DA-13). Update the roadmap and the hybrid draft on acceptance.

### SF-15. One transition row contradicts §3.0
**Where:** §3.1 Pyrolysis: "volumetric when a cell's bulk passes the pyrolysis point".
**Scenario:** That is a threshold on a cell's mean temperature, which §3.0 and CLAUDE.md now forbid where structure
inside the cell matters. A coarse cell's bulk crosses the point later than a fine one's, and the mass-loss onset
splits by rig, the same late-burn lag again.
**Fix:** Make in-depth pyrolysis a rate integrated over a reconstructed in-cell profile, or justify why bulk
pyrolysis has no sub-cell structure that matters, with numbers.

### SF-16. Rig-bound saves are a product decision, recorded as a technical "not now"
**Where:** §8 ("tied to one rig's cell size"); §12 ("rig-portable saves" under Not now).
**Scenario:** A Steam player lowers the quality profile, or moves to a laptop, and can't load any save. That will be
reported as a bug, and the fix then lands under pressure in a committed format.
**Fix:** Make it an owner question in §13. The save already embeds the scene and placed specs, so note that a later
conservative remap (exact coarsening, piecewise-constant refinement) stays possible, and keep nothing in v0 that
rules it out. For example, don't store derived ids without the authored inputs they come from.

### SF-17. The surface skin is new saved state with no container
**Where:** §3.1 ("a heat-balance skin per exposed fuel face"); §2.5 (the registry's containers are cell, zone, pool,
gap and debris in the research; v2 lists rig cell, fixed metres and zone as grids).
**Scenario:** The skin integrates a heat balance over time, so it's state that must be saved and digested before
save v0. Exposed faces appear and disappear with topology. The registry has no face container, so PR 7 adds one ad
hoc (six arrays per cell, or a sparse table), and the save, digest, memory budget and lints all learn about it late.
**Fix:** Add a `face` (or sparse surface) container to §2.5 now, with how it's keyed and what happens to its state
when a face is created or covered.

## NIT

- **N1.** PR 2 (verify) before PR 3 (sim-clock) means the heat tests are retrofitted to the harness, then rewritten
  for `heat.step` in physics steps, and their error figures re-derived. That's decision 17, but say it costs a
  second retrofit, or have the harness target the post-sim-clock API.
- **N2.** PRs 4, 8 and 9 have no branch names. CLAUDE.md requires `phaseN/<step>`.
- **N3.** §6 says "three implementations behind one apply path", then adds a fourth behaviour, the world-time latency
  mode. Name it as a fourth source (or a property of the live one), and say it lives in a cradle or experiment
  harness, never in the shipped host (DA-20). Then a misconfigured play session can't block the world.
- **N4.** §2.3 says "converting every cell takes 5.1 ms at the max rig with cached property arrays". The research
  says the full inversion costs 63.9 ms, and 5.1 ms is the correction with 0.1% of cells at a transition.
- **N5.** The 91 B/cell and 7 / 58 / 466 MB estimates predate the loose flag, packing fraction, skin state and
  strength factor. Recompute them from the registry once it exists.
- **N6.** N7 versions names, but §8 changes meanings: `extinguish`, and `ignite`, which becomes a spark in the fuel
  model (research §2.4), though v2 doesn't say so. An NPC's learned causal links on the old `ignite` survive a
  meaning change under the same name. Say whether a meaning change renames the tool.
- **N7.** §12's "Not now" should restore v1 v0's list (LAN play, NAT traversal, prediction and rollback, accounts),
  per DA-19.
- **N8.** There is no `reviews/world_v2/README.md` to record how this round's findings are folded (DA-18's lesson).

## What I checked and found sound

- **Containers by phase for solids and gases.** Gas in zones is rig-independent by construction, costs microseconds,
  holds mixtures, and has closed forms. Rejecting a per-cell phase tag is right: it's the most expensive choice to
  undo, and it splits rigs at every threshold. Zones that never merge, with gaps measured by overlap, give stable ids
  for SEM and saves.
- **Temperature plus phase-change progress as the solid state (decision 18).** A solid cell holds only its solid
  phase, so this is exact, keeps every consumer of T unchanged, and is fixed before save v0.
- **The ledger rule** (donor-limited, antisymmetric, never clamped afterwards) and **`set_material` as the one choke
  point,** with topology updated in the same substep. The SS14 lesson is applied correctly, with B2 and SF-8 as
  caveats.
- **The registry as a declaration, not a plugin framework,** with concrete solver modules. That's the right level of
  abstraction for a small team, and it's what lets the save, the digest, the memory budget and the lints stay in
  sync.
- **Self-describing frames** with `required`, per-grid cell size and origin, tables, and `delta` reserved. The
  grammar-before-fields order for the frame is right (within SF-11's limits).
- **Save v0 after every change to a saved field's meaning** is the right principle. SF-12 and B3 are where the order
  doesn't yet honour it.
- **SEM as a membrane inside Maxim's frozen types.** `Entity.entity_type` is a free string (`maxim/embodiment/sem.py`),
  so N1 needs no Maxim change. N5's world-backed `check_affordance_requires` uses Maxim's `hasattr` hook, not a
  workaround. P3 (credit after the call) is the most valuable Maxim finding in the design and names what it argues
  against. Nothing here pigeon-holes Maxim. The proposals widen it.
- **PR 1 as the trust boundary only (decision 16).** Its parser is already pure (`parse_action` takes limits, not a
  `World`), which folds DA-9. Its red gates are honest. Its interim `Region` with footprints is a sound interim, as
  long as B2's claim about what replaces it is corrected.
- **Folded correctly from delta1_architecture:** DA-1 (one delivery rule), DA-2 (decision 11 and the latency mode),
  DA-3 in substance, DA-7 (hashed world config), and the clock part of DA-10.
- **Honest physics framing:** the sealed-room O₂ budget driving vents, the measured non-convergence of
  threshold-and-delete, §3.3's admission that `breached` still flips, and Q3 left open for the owner rather than
  quietly decided.
