# The world model (design v3, part 1 of 3, 2026-11-16)

**Status:** DRAFT, for a design review before any code. It is the first of three documents that replace
`world_v2.md`. The owner decided on the split after v2's review (`reviews/world_v2/`: 19 BLOCKER, 73 SHOULD-FIX, 35
NIT), which found that v2 overreached. This part covers:
- how matter, energy and time are represented and stepped;
- the laws that change them;
- the formats that carry them.

Part 2, `npcs_and_sem.md`, covers what NPCs sense, how they act, and SEM. Part 3, `lab_and_core_loop.md`, covers the
development tile and the core loop. `world_v2.md` and `realtime_lanes_coop.md` stay as records.

**How the review is folded.** Each v2 finding this part covers is cited by its id (P1 = `physics.md`, A-B2 =
`architecture.md`, F1 = `wire_trust.md`, DLP-B1 = `determinism_lanes_performance.md`, E1 = `executor.md`). The fold
table (Review records) maps every finding in scope to where it lands, or says why it doesn't. v2 claimed folds it hadn't made
(A-B1, BF-13); its fold table (Review records) lets the claim be checked.

**Numbers.** Every number is marked as measured (with its probe in `research/states_of_matter/probes/` or a review
file), derived, or *from memory* and to be verified before it reaches `data/` or `docs/`.

## 0. Decisions this part rests on

This document's decisions (11 rulings) are kept as records, with their dates, owner sections and status, in `decisions/world_model.md`.

## 1. Resolution: one truth

### 1.1 The truth resolution

- **The world is simulated at 0.1 m base cells on every machine.** On the 16×10×4 m synthetic tile, today's heat
  substep costs 14 ms at 0.1 m, and 3.9 ms with cached conductances and preallocated buffers (DLP, measured). That
  leaves headroom for zones, skins and fuel at real time. 0.05 m doesn't: about 1.6× real time in a quiet room even
  after caching, and slower during a fire (DLP, measured).
- **The rig profiles stop deciding physics.** `laptop`, `rig` and `max` become rendering tiers: how much of the
  snapshot the client draws, and at what detail.
- **Thin features** must be at least two cells of the coarsest verification grid (0.2 m) thick, or one cell becomes the
  whole feature and a scratch becomes a breach. The rule holds for resolved cells; fuel objects are exempt only as
  `rod`, `slab` or `bed` recipes of fuel, never structure (a plank wall stays cells) (docs-contracts ruling 72;
  `fire_solid.md` §1.3).
- **The 0.2 m and 0.05 m grids stay, as verification grids.** The cross-tier tests become convergence tests: the
  0.1 m answer must lie within a stated tolerance of the 0.05 m reference, and must converge from 0.2 m. They no
  longer promise that different machines play different-but-equivalent games. They check that the one game is
  numerically right.
- **What changes in the standing rules:** the resolution rule ("a rig may change precision, never the outcome
  class") becomes a verification rule: "the truth resolution's outcomes agree with the reference resolution's, within
  a gated tolerance". CLAUDE.md, `docs/architecture.md` and the review charter's Physics lens change with it.
- **Why this is the root fix:** every resolution finding in PR 1's eight review rounds, and P1 to P5 here, existed
  because different machines simulated different worlds. One truth removes the class. The sub-cell laws below are
  still required, now for correctness against the reference rather than for fairness between machines.

### 1.2 Resolution follows the world (D21)

- **Phase 1 runs uniformly at 0.1 m.** No refinement yet.
- **Phase 2's "Scale" item adds deterministic adaptive refinement.** Finer cells near fronts (fire, craters, phase
  change), chosen by a criterion computed from world state (a gradient, or an error estimate). Every machine refines
  identically, and refinement events are part of the deterministic state.
- **Sleeping quiet chunks is the only budget lever that touches the simulation.** A chunk that is uniform, has no
  sources, and whose halo is uniform takes no step, because a step there changes nothing. It wakes the moment a
  neighbour, an action or a source touches it. Results are bit-identical with sleeping on or off, and a test holds
  that.
- **As a law is verified resolution-independent by its convergence test, it earns budget freedom:** the dial
  extends law by law, measured.
- **When nothing safe is left to trade, the world dilates.** The tick status reports the effective time scale.
  Never hidden.

## 2. Matter: containers by phase

v2 §2.1 stands (solids in cells; gas, and later liquid, in zones; no gas in cells; no per-cell phase tag), with these
changes.

- **A gas consumer interface from the start** (A-SF). Consumers read gas only through `gas.at(zone)` and
  `gas.over(mask)`, never the zone tables directly. A later per-cell gas grid or a two-layer smoke zone is then a swap
  behind the interface, not a refactor of every consumer.
- **Liquids have a level but no position yet** (A-SF). A per-zone pool is a film across the zone's floor. Puddles
  with a position are Phase 2, behind the same kind of interface (`liquid.at`, `liquid.over`).
- **Mass is never silently deleted** (D22's foundation). A strike that destroys solid mass moves it to the zone's
  fines species, so the ledger is exact from day one and Phase 2's rubble only changes where that mass goes.
- **Zones are authored in metres** in the scene format (`tile_and_client.md` §1.3). Their volumes and gap areas are
  computed from **integer cell counts** at the truth resolution, never from running float sums (DLP-B1, §6).

## 3. Every law reconstructs, decides at the point, and integrates

**v2 applied the principle to one law** (ignition). The physics review measured five more that still decide on a
cell's mean or a cell's boundary, and prototyped fixes for most (P1–P5, S1–S10). Each law below states its
reconstruction.

| Law | v2 | This part | Evidence |
|---|---|---|---|
| Heat exchange, cell to zone | cell-mean temperature × h | **a surface skin on every exposed face that exchanges heat**, not only fuel faces, with its depth set in metres | P1: a concrete wall under an 800 °C zone absorbs 104 / 104 / 85 MJ/m² at 0.2 / 0.1 / 0.05 m against a converged 48; the skin gives 47.9 / 48.1 / 48.1 (measured) |
| Ignition | skin per fuel face, face-mean flux | **deposit by area overlap; each face carries an ignited area fraction** computed from the pilot's footprint in metres; losses included, so a critical heat flux exists | P2: a 2 kW pilot on a corner lit the crate in 1.5 s at 0.05 m and never at 0.2 m (measured) |
| Burning away (ablation) | per-face recession | **sub-box recession per cell:** each burning cell tracks the receding surface inside it in metres | P3: a 0.6 m box kept 0.205 / 0.268 / 0.311 of its mass at t = 0.1 against an exact 0.370; with sub-box recession 0.370 at every grid (measured) |
| Pyrolysis | energy-limited, T_bulk from the cell mean; a volumetric threshold branch | the rate law is `fire_solid.md` §4.2's | S2 |
| Strength and breach | strength by mass fraction; breached when strength < ½ | **breach decided by remaining thickness in metres** along the wall's normal | S1: a strength-½ breach fires at 0.30 / 0.35 / 0.375 m of burn depth against a true 0.40 m |
| Fuel initialisation | by cell centre | **by volume overlap;** unaligned fuel geometry is refused in Phase 1, and a known gap records it | S3: cylinder volume 0.38–1.13 of true at 0.2 m; voxel-sphere area tends to 1.5× (confirmed) |
| Flame feedback | fixed flux per m² | **fixed flux per m², scaled by the zone's extinction factor and debited from the heat release** | S5: otherwise a sealed crate keeps pyrolysing without heat to pay for it |
| Zone exchange | implicit step, (I + dt·V⁻¹L) | **(I + dt·L·V⁻¹), applied as antisymmetric per-gap transfers**; vents are a separate closed-form term, not a symmetric exchange | S7, DLP S-3: the v2 form loses 0.18% of mass (measured); per-gap transfers change the total by 0.0 (measured) |
| Collapse, rubble settling, fragment size | in Phase 1 | **Phase 2** (D22): collapse by a min cut of the intact cross-section in metres; settling by continuous column heights; fragment size in metres | P4, P5, S10 |

**Binary outcomes keep a band however good the laws are** (P-where-they-disagree). Ignition near the critical heat
flux, a breach near the minimum ligament, "goes out", "burned away". They are gated by a **band gate** (S4): for each
binary outcome, measure the width of the input range where the truth and the reference disagree, record it in Known
gaps, and gate that width. The operating point also clears the band by a margin (docs-contracts ruling 60).

**"Goes out" is defined** (S9): flames are extinguished when the zone's O₂ fraction falls to the extinction limit,
with a ramp from 15% to 10% (*from memory*; the sources conflict, so both are cited in data). By derivation, the
3×3×2 m sealed scene burns 1.07 kg of fuel down to 15% and about 2.0 kg down to 10%. Decided by the flames design
(after R0–R1); for 6.1's cone, extinction is `fire_solid.md` §4.4's.

## 4. Energy and the heat state

- **Temperature plus phase-change progress** (v2 decision 18) stands, with two corrections:
  - Converting every cell takes 63.9 ms at 0.05 m. The 5.1 ms v2 quoted applies only when 0.1% of cells are
    mid-transition and a per-cell cache exists (E3). At the truth resolution, 0.1 m, one eighth of the cells, it is
    proportionally less.
  - Caches must be float64, or "matches the old tests to 1e-12" doesn't hold: float32 caches gave a 2.5e-6 °C
    difference (DLP S-9, measured).
- **Air leaves the conduction solve only when the solve runs over solids or active chunks** (DLP). Removing air cells
  saves nothing while the solve still sweeps the whole grid.
- **The ledger's tolerance is relative,** not 1e-10 absolute, because a tile holds about 1e11 J (DLP S-3): changes
  close to 1e-12 of the tile's total energy, per substep.

## 5. Ownership: one owner per cell, authored shapes in metres

- **Regions become one `region_id` array** (u16), and each cell has one owner (v2 §2.4).
- **That alone doesn't remove PR 1's interim rules** (A-B2). PR 1 refuses overlapping named solids because reach and
  fire placement read the authored bounding box. The fix is to make each region's authored shape exact:
  - A region's authored geometry is its solid primitives minus the air carved into them, held as a small CSG in
    metres (boxes and cylinders, union and difference).
  - "Is this point on the region" and "does this fire touch the region" are decided on that CSG, in metres, the
    same at any resolution.
  - The centroid is the CSG's volume-weighted centroid, minus the carved air.
  - With that, the overlap rule can relax to "a later solid may not overlap an earlier named solid's *CSG*" (true
    overlap, not bounding boxes). The four ownership known gaps from PR 1 close: a destroyed region claiming its
    space, overlap judged on boxes, a carved region's centroid in air, and the authoring cost for windows in walls.
- **Region ids are never reused, and are versioned** (F10). A `regions_version` bumps on every new region; the
  protocol carries the change.
- **Zone and region names have separate namespaces** (F11), so `act.region` can't mean a zone.

## 6. Determinism of incremental state

- **Integer counts, not float sums** (DLP-B1). Zone volumes are stored as cells per zone, and gap areas as faces per
  zone pair and z-bin. Each event's change is after minus before, assembled in sorted order. A Hypothesis property
  checks that incremental state equals a full recompute bit for bit. That is what lets the save's derived-state
  check work.
- **Topology work is batched once per physics step,** not per substep, with 6-connectivity (DLP S-6). Relabels cost
  0.6–0.9 / 3.9–5.7 / 31–47 ms at 0.2 / 0.1 / 0.05 m (measured, solids plus the anchor test). At the 0.1 m truth,
  that's affordable once per physics step.
- **Labels from `ndimage.label` are not identities** (DLP S-4). Anything that needs an identity (Phase 2 rubble
  clusters) gets a persisted id and an ordering key in metres.
- **The tripwire** is `boundaries.md` §3's profile hook, not patching (DLP S-8).

## 7. Foundations for Phase 2 rubble and collapse

Laid now, so that Phase 2 adds behaviour without changing a format or a saved field's meaning:
- **Reserved channels:** `loose` (u8) and `packing_fraction` (f32) are declared in the field registry and the frame
  grammar, absent until Phase 2.
- **Mass conservation** (§2): destroyed solid mass goes to fines, so rubble later redistributes it.
- **The topology choke point:** `set_material` and `topology_version` (v2 §2.2), with the batched relabel (§6).
- **Persisted cluster ids and a metric ordering key** (§6), defined now, used by rubble later.
- **Fragment size is a length in metres from the start,** never "a cell".
- **Strike and breach semantics are written for loose matter now** (A-B3): a hole filled with rubble doesn't count
  as breached unless its open area, in metres, exceeds the breach threshold. The crater test measures destroyed
  solid volume, which stays well defined when mass becomes fines or rubble.

## 8. Formats and trust

v2 §8 stands (self-describing frames, whose grammar is now `client_rendering.md` §4.1's; one grammar for wire and
save), with these rules from the Wire and Trust review.

- **A name is an identity** (F1). A channel's or sensor's name, units, grid and meaning are fixed for the life of the
  format. A new meaning gets a new name:
  - `crack` stays 1 − integrity, and mean strength gets its own channel.
  - Air cells' `temperature_c` stays cell temperature, and the zone temperature is a zone column.
  - `extinguish` is retired for `douse` (F7; the vocabulary is `tile_and_client.md` §3.2's).
  
  Units are part of a channel's identity, from a closed vocabulary, and a lint checks them against the fixtures.
- **A save has no optional fields** (F5). The code's registry and loaders are authoritative. Embedded copies of the
  registry, scene and specs are compared against them, never executed. A save from a newer build is refused, loudly.
  A content change is refused too, and a save holds no in-flight thoughts, since agent state lives outside
  `Simulation` (docs-contracts ruling 26, owner, 2026-11-21).
- **Saves, scene files and replay logs are untrusted input** (F14), under the gate contract (`boundaries.md` §5.4):
  - the memory budget is checked before anything is allocated, from the header's declared shape;
  - shape, sizes and offsets are validated against the scene and rig;
  - every saved cell value is validated as the loaders validate data;
  - embedded scene and specs go back through `Scene.from_dict` and `imagination.spec.place`, and logged intents
    through the first-stage validator;
  - loading is all-or-nothing.
- **Frame rules** (F2, F3, F4, F6) are `client_rendering.md` §4.1's; its fixtures (§4.2) include a non-default
  linear scale, so a decoder that hard-codes 1/255 fails.
- **The material data** (its files and versions are `fire_solid.md` §5.1's) uses the strict loader that
  `ActionLimits.load` has, under the gate contract
  (`boundaries.md` §5.4), species keyed by name, never by position (F8). Its reactions close their mass and atom
  balances. The research's example `wood_flaming` doesn't (2.15 in, 2.40 out), and the loader would rightly refuse it
  (E-NIT).
- **The scene format's strict loader** (F13) is `tile_and_client.md` §1.3's. Zone counts are capped, and the zone
  channel's dtype is fixed at u16 (F9).
- **Per-face state has a container before the grammar freezes** (DLP S-11). Surface skins (§3) are state per exposed
  face, not per cell. The registry declares a face table keyed by (cell index, face 0–5), and the frame grammar
  carries it as a table, so the fuel PRs add rows, not a format.
- **Migration defaults are literals, `null` or the name of a migration function registered in code,** never an
  expression to evaluate (F12). Derived fields carry a `derivation_version` (F15); a better estimate bumps
  `derivation_version` or the law's version, goldens regenerated in a commit saying so.
- **The intent log header's fields** (F16, DLP S-7) and its one digest form are `boundaries.md` §6.3's.

## 9. Performance, measured

On the 16×10×4 m synthetic tile (DLP, measured):
- **Today's heat substep** costs 2 / 14 / 113 ms at 0.2 / 0.1 / 0.05 m.
- **With cached conductances and preallocated buffers** it costs 0.6 / 3.9 / 34.6 ms. These go in `phase1/sim-clock`;
  v2 had dropped them from the plan (A-SF).
- **Memory is about 100–125 B/cell** with every field v2 lists (DLP S-10), against v2's 91. At 0.1 m that's 64–80 MB
  per tile.
- **The budget check counts transients:** today's substep peaks at 412 MB of temporaries at 0.05 m.
- **Region reductions (the SEM sensors) are one `bincount` pass over `region_id`,** published once per physics step
  as a frozen object: 23 ms against 88 ms for 50 per-region masks at 0.05 m (DLP S-12, measured).
- **The fire's sphere overlap** keeps its full-grid cost for sparks and torches until it's computed over the sphere's
  bounding box. That goes in `phase1/sim-clock` (E6).

## 10. Order of work

| # | PR | What |
|---|---|---|
| 1 | `phase1/act-validation` | **Done** (review complete, awaiting the owner). |
| 2 | | Parts 1, 2 and 3 of this design accepted. |
| 2b | `phase1/boundaries` | Structure: the engine package re-homed by layer, the config split, the intents layer, the bridge split, the import contracts (`boundaries.md` §11.1). |
| 2c | `phase1/gates` | Behaviour, limited to what has a caller then: the ownership write window, frames published as copies, validating constructors, the gate contract and registry (`boundaries.md` §11.1). |
| 3 | `phase1/verify` | The verification harness. Heat retrofitted, with its order-of-accuracy test fixed by refining space and time separately (E2). The resolution rule becomes the verification rule (§1.1). |
| 4 | `phase1/sim-clock` | The `Simulation` and its integer clock; the truth resolution; cached conductances and preallocated buffers; the fire's bounding-box overlap; `set_material`, `topology_version` and the region id array; memory budget with transients. |
| 5 | | Material table v1, strict. |
| 6 | `phase1/protocol` | Frames with the generic grammar from the first fixture. Versioned, extensible messages (`client_rendering.md` §4.1, `tile_and_client.md` §3.3; A-SF-11). The lane skeleton. A minimal Godot fixture reader, so the grammar has a second reader before it freezes. |
| 7 | `phase1/zones` | Zones, gaps and vents in the scene (`tile_and_client.md` §1.3). The gas interface. Surface skins for heat exchange on exposed faces. |
| 8a | `phase1/fuel-surface` | Fuel by volume overlap; area-overlap deposit and ignited fractions; sub-box recession; reconstructed pyrolysis. |
| 8b | `phase1/fuel-combustion` | Combustion per zone, products, extinction, flame feedback debited. Fines from destroyed mass. The CSG footprints (§5). |
| 9 | | Phase-change progress, with bound water as the first transition. |
| 9b | `phase1/agents` | The agent foundations: one host-called `AgentPort` (`step`, resumable `think`, `settle`; O39), `StepOutput`, `Pending`, `Reply` and `ThoughtOutput`, the continuation's host-owned header, receipts and settle, `data/agents/`, per-NPC streams, the tool-roster and home checks, the worker channel and its codec (a registered gate), the scripted test double in a spawned worker behind that channel; real Maxim a strict red gate until its tier A (`boundaries.md` §11.1, `npcs_and_sem.md` §6.2, §6.6). |
| 10 | `phase1/lanes` | The agent barrier over worker channels, `agent_failed` on a hung or dead worker, meters (the channel round trip per park), crash injection (`npcs_and_sem.md` §4.4, §6.3, §6.6). Thinking lane and gateways: `phase1/agents` (`inference_placement.md`). |
| 11 | | **Save v0, after the lanes,** with §8's load rule (F5, F14; A-SF-12, DA-6). |
| 12 | `phase1/lab` | The lab as a physics benchmark tile, and the Godot client (part 3). |

**The fuel model's acceptance test is restated** (E1). PR 1's red gate ran on a scene with no vents, which becomes a
sealed room once O₂ exists. Its 5 kg of O₂ can burn only about 2.5 kg of the 130 kg crate, so the gate would pass
under any burn law. The fuel PRs are accepted on:
- **a vented crate scene** that burns away, agreeing with the 0.05 m reference within the band gate;
- **a sealed one** that goes out by the §3 definition.

## 11. Numbers from memory, to verify before `data/`

These are relied on by this part (E11, P-numbers): L_g, T_p, T_ig; flame flux; Tewarson's yields and ΔH_c,eff
(12.4 MJ/kg); the pyrolysate formula; the O₂ extinction limits; Kawagoe's 0.5·A√H; steel melting data; Eurocode 3
k_y,θ; char strength; wood's critical heat flux; angle of repose and packing fraction; a fragment-size relation.
Verified: Huggett's 13.1 MJ per kg of O₂; the thermally thick ignition closed form and its constants; the voxel-sphere
area limit; the sealed room's 3.96 kg of O₂ (cross-tier scene) and about 4.95 kg (the gate's scene).

## 12. Open questions for the owner (all answered as recommended: D27, 2026-11-17)

1. The truth resolution: 0.1 m, as measured above, or another value?
2. The band gate (§3) as the answer to v2's Q3, how the resolution rule treats binary outcomes?
3. CSG footprints (§5) in `phase1/fuel-combustion`, or earlier?

## Review records

This document's fold tables are kept with their reviews: `reviews/world_model/fold.md`.
