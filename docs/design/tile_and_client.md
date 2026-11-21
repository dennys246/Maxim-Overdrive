# The tile: world side (design, step 0d, v3, 2026-11-18)

**Status:** v3, frozen (owner T13, 2026-11-18). v1 (f6afd66) had a six-lens review, v2 a delta review
(`docs/design/reviews/tile_v1/`, with the reviewer's fold status in `fold.md`, O25). This document holds the world
side: the alley, bodies, intents and their pipeline, the simulation `Frame`, what step 6 must deliver, the exit
scenario and the Bio-faithful note. `client_rendering.md` holds the client protocol layer's wire encoding and the
Godot side (the split is O31). Finding ids (PH-, AR-, WT-, BF-, EX-, CR-, DPH-, DC-) point into the review files.

**Numbers** are *measured*, *derived*, *from memory, to verify*, or `[engineering]`; §5's literature constants are
in §5.1.

**Corrections to the repo's text** (each lands in the plan step named):
- `docs/architecture.md:20` ("turn-based, classic Fallout") is stale: real time with pause on a fixed tick
  (`origin/phase1/realtime-design:docs/design/realtime_lanes_coop.md`, decisions 1–4); its Transport caveats are
  restated in `client_rendering.md` §4. Step 1.
- `docs/roadmap.md` Phase 1 lists the clinic (D27) and a "laptop and rig profiles" exit (D20): step 8.
  `data/rigs/*.yaml`'s comments and tier fields (D20): step 3a's `config` split. `docs/standards_backlog.md` B5–B7's
  stale step numbers (EX-N7): step 2.

## 0. Decisions this document rests on

| Id | Decision | Owner, date | Source |
|---|---|---|---|
| T1 | Camera: isometric 3/4, fixed elevation, 90° steps, bounded zoom, a cut-away rule | owner, 2026-11-18 | `client_rendering.md` |
| T2 | Movement: click-to-move and WASD, both validated intents through the one door, logged; the client never moves the player | owner, 2026-11-18 | §2, §3 |
| T3 | Tick 0.1 s, physics every 0.5 s; the 6 s turn is retired | owner, 2026-11-18 | §6.1 |
| T4 | `kindle`, with power from a held item; `ignite` retired | owner, 2026-11-18 | §3.2 |
| T5 | A body heat state from Phase 1 | owner, 2026-11-18 | §2.1 |
| T6 | File OD-C11 (egocentric locomotion) with Maxim | owner, 2026-11-18 | §3.1 |
| T7 | The walk direction is an integer vector, canonicalised at stage 1 | owner, 2026-11-18 | §2.3 |
| T13 | Frozen at v3; no more paper rounds on the fire physics. Step 6's PR carries a short design note under the Physics lens, the final review's FPH-B1 to B3 are its requirements, and its convergence tests and pre-registered failure path decide | owner, 2026-11-18 | §5 |
| T14 | The flame radiates into bodies by a point source in Phase 1; into walls in Phase 2 | owner, 2026-11-19 | §9 |
| T15 | The crate: 20 mm slats at φ = 0.25 | owner, 2026-11-19 | §9 |
| T16 | Protocol v0 freezes only the kinds a Phase 1 client sends | owner, 2026-11-19 | §3.3, §9 |
| T17 | An accelerant lights the crate, not the pilot alone; step 6 researches char oxidation first (`physics_spike.md`) | owner, 2026-11-20 | §5, §6.3 |
| T18 | The accelerant is a pore-loading field the SEM bridge reads, never an SEM rule (`physics_spike.md`) | owner, 2026-11-20 | §5, §9 |
| RT1–4 | Real time with pause on a fixed tick; a dial; pause a state; host-only time control | owner, 2026-11-15 | realtime decisions 1–4 |
| D20, D25 | One truth at 0.1 m, rigs are rendering tiers; reconstruct, decide at the point, integrate | owner, 2026-11-16 | world_model §0 |
| D26–D28 | Tile first, exit as written; clinic after; heat-debt prototype after the tile | owner, 2026-11-17 | world_model §0 |
| D29, D30 | Step 6 = 6a open-air loss, 6b surface skin, 6c porous fuel bed, 6d char oxidation; solid sub-cell recession moves to Phase 2 | owner, 2026-11-18 | world_model §0 |
| O23, O24, O31 | Frames publish on change; `simcore` in four layers (core, adapters, game, client protocol); this split | owner, 2026-11-17/18 | boundaries §0 |

T8–T12 are client decisions (`client_rendering.md` §0).

## 1. The alley in metres

### 1.1 Geometry

- **Extent 12.0 × 4.0 × 4.8 m** (x east along the alley, y north, z up): 60 × 20 × 24 cells at 0.2 m, whole on every
  axis. A dead-end alley off a street: x 0–1.2 m is pavement (the spawn); walls from x = 1.2 m; clear width 3.2 m;
  walls 4.0 m tall `[engineering]`. Every solid and every air gap a test relies on is ≥ 0.4 m.

| Name | Material | min_m | max_m |
|---|---|---|---|
| `floor` | concrete | (0, 0, 0) | (12.0, 4.0, 0.4) |
| `wall_south` | concrete | (1.2, 0, 0.4) | (12.0, 0.4, 4.4) |
| `wall_north` | concrete | (1.2, 3.6, 0.4) | (12.0, 4.0, 4.4) |
| `wall_end` | concrete | (11.6, 0.4, 0.4) | (12.0, 3.6, 4.4) |
| `crate` | wood bed | (6.0, 2.6, 0.4) | (6.6, 3.2, 1.0) |
| `crate_far` | wood bed | (9.0, 0.8, 0.4) | (9.6, 1.4, 1.0) |

- **The crate is a porous fuel bed** (D30): slats around air, authored as a 0.6 m box whose cells carry a fuel volume
  fraction φ and a surface area per volume σ. Content values `[engineering]`: 20 mm slats, φ = 0.25, so σ = 2φ/δ =
  **25 m²/m³**; 0.054 m³ of wood, **32.4 kg**, **5.4 m²** of fuel surface (derived). The thin-feature rule applies to
  the box, not the slats, which live inside the cell's state.
- **`crate_far` is a placement guard,** not a fire-spread control (PH-S3): heat can't reach it 2.68 m away through
  air (diffusion length √(αt) = 0.34 m over the 5,400 s cap, α_air 2.2×10⁻⁵ m²/s, PH's value).
- **No bounding-box overlaps between named solids** (`scene._check_no_solid_overlaps`); no other props until D27.

### 1.2 Light and open air

- **No light field in Phase 1.** The client's fixed night is rendering only (BF-N1).
- **Open air (D29, D30):** every exposed surface loses heat to ambient through 6a; the flame's convective plume leaves
  the open-topped alley; the flame's radiation is exported unreceived except by bodies, a metered Known gap (§5.4).
  The domain boundary stays insulated for conduction, which carries almost nothing through air.

### 1.3 Scene format and files

- **Scene v1 = world_model F13's strict loader plus a required `spawns` list** (WT-S8), in step 3b; zones become v2
  in Phase 2. v0 is refused by version (step 3b); `join` with no spawn for its archetype is refused.
- **The format checks syntax and extent only;** clearance is checked at construction and `join` (AR-S9); spawns
  convert to integer mm by F13's rule.
- **Files:** `content/scenes/alley.yaml` (rights reserved, step 8); engine tests and step 5 use an Apache fixture
  with the same boxes, `tests/fixtures/scenes/alley_box.yaml`. Cut-away walls are client data (DC-N4).

```yaml
version: 1
extent_m: [12.0, 4.0, 4.8]
ambient_c: 15.0
spawns:
  - {name: runner, archetype: human, holding: torch, at_m: [0.6, 2.0, 0.4]}
primitives:
  - {kind: box, name: floor,      material: concrete, min_m: [0.0, 0.0, 0.0],   max_m: [12.0, 4.0, 0.4]}
  - {kind: box, name: wall_south, material: concrete, min_m: [1.2, 0.0, 0.4],   max_m: [12.0, 0.4, 4.4]}
  - {kind: box, name: wall_north, material: concrete, min_m: [1.2, 3.6, 0.4],   max_m: [12.0, 4.0, 4.4]}
  - {kind: box, name: wall_end,   material: concrete, min_m: [11.6, 0.4, 0.4], max_m: [12.0, 3.6, 4.4]}
  - {kind: box, name: crate,      material: wood, min_m: [6.0, 2.6, 0.4], max_m: [6.6, 3.2, 1.0]}
  - {kind: box, name: crate_far,  material: wood, min_m: [9.0, 0.8, 0.4], max_m: [9.6, 1.4, 1.0]}
```

### 1.4 Size (derived; counts recomputed by PH)

230,400 cells at the 0.1 m truth (28,800 at 0.2 m, 1,843,200 at 0.05 m); 59,312 solid (25.7%); 23–29 MB at
100–125 B/cell. Today's uncached heat substep on the alley: **0.59 / 4.5 / 38.3 ms** at 0.2 / 0.1 / 0.05 m (PH,
measured). With caching, **1.4 ms** at 0.1 m is a projection (world_model §9's 3.9 ms × 230,400/640,000), not a
measurement. `stable_dt` is 46.9 s at 0.1 m: one substep per 0.5 s physics step.

## 2. Bodies: one model for every actor

### 2.1 The model (BF-B2, AR-S1, AR-S3, BF-S2, BF-S6, DPH-S4)

- **One body model, world-owned, in the `simcore` core** beside `Simulation`. Players and, from Phase 4, NPCs are
  actors with bodies in one actor table. Maxim's `Entity` holds only what is felt, fed by `world_set_axis`
  (boundaries §4.3); Overdrive never models a body twice (npcs §2.2).
- **A body archetype** is an engine type with a strict loader; the game supplies instances under `content/bodies/`.
  Phase 1 has `human`:

| Field | Value | Tag |
|---|---|---|
| collision cylinder | radius 0.25 m, height 1.8 m | `[engineering]`; shoulder width *from memory* |
| walk speed | 140 mm per tick (1.4 m/s) | *from memory, to verify* |
| reach | 1.5 m, 3-D, from the body's axis segment (feet to head) (DC-N9) | `[engineering]` |
| heat store | 70 kg × 3,500 J/kg·K = 245 kJ/K | *from memory, to verify* |
| convection | h = 10 W/m²·K over 1.9 m² | *from memory, to verify* |
| radiation | ε = 0.95; projected area 0.5 m² toward a source | *from memory, to verify* |
| exchange volume | the cylinder grown by 0.2 m radially and on top | ≥ 0.4 m across: two coarse cells |

- **Convection** is superseded by `sem_stimuli.md` §3.1 (2026-11-21): per skin point, against a fixed reservoir in
  Phase 1. The exchange volume's air (1.53 kJ/K) reaches the body's temperature in about 80 s (DPH, derived), so a
  volume-mean sink makes the body fire-blind.
- **So the body also receives radiation** (§9 Q1): from each hot exposed skin face by a view factor computed in
  metres, debiting that face's 6a loss; and from the flame by the point-source model q'' = χ_r·Q̇/(4πd²) (*from memory,
  to verify*), debiting the unreceived flame line (§5.4). It radiates to ambient at εσ(T_b⁴ − T_amb⁴): about 240 W at
  37 °C in 15 °C surroundings (derived). Metabolism and regulation: `sem_stimuli.md` §3.1.
- **What it feels near the fire (derived from §5's numbers):** in the flaming phase (Q̇ ≈ 780 kW, χ_r 0.3), 18.5 kW/m²
  at 1 m and 2.1 kW/m² at 3 m; absorbed over 0.5 m², 9.3 kW (+2.3 K/min) and 1.0 kW (+0.25 K/min). In the ember phase,
  4–12 kW/m² at 1 m from a face (envelope 640–920 °C), under 1 kW/m² at 3 m. D28's body is therefore
  location-dependent.
- **Tests:** superseded by `sem_stimuli.md` §3.1 and its checklist (2026-11-21); a cross-grid test at 0.2 / 0.1 /
  0.05 m.
- **Receptor volumes** (head, hands) are declared in the schema with no Phase 1 caller (DC-N8); a head is under two
  coarse cells, a Known gap needing the reconstruct-then-integrate path (BF-S6).
- **Body occupancy is derived from the bodies part of the `Frame` at reduction time,** never stored in the cell part
  (DC-S3). The actor table as a direct view is an ANALOG divergence until occupancy percepts exist (AR-S3).
- **Identity:** `actor_id` is session-scoped; save v0 maps each body to a persistent `body_key` (BF-N3), with no
  `:` (npcs §3.4), so it can serve as an NPC's key.

### 2.2 The actor table and pilots

Frozen per tick, replaced by `Simulation.step`; column-major, integer keys, no strings (world_model §8):

| Column | dtype | Meaning |
|---|---|---|
| `actor_id` | u32 | key |
| `archetype` | u8 | 1-based index into `welcome`'s archetype list |
| `pos_mm` | 3 × i32 | feet position |
| `facing` | 2 × i16 | unit vector × 1000, set from movement, kept when stopped (BF-S2) |
| `motion`, `path_state` | u8, u8 | idle/held/path; none/walking/arrived/blocked |
| `path_version` | u16 | bumps on every new or replanned path |
| `held_item` | u8 | 1-based index into `welcome`'s item list, 0 none (DC-N10) |
| `body_temp_mk` | i32 | body temperature in millikelvin (the core holds float64) |
| `energy`, `dose` | i32, i32 | present as zero with a `derivation_version` until Phase 4/5 (DC-N2; F5) |

38 B per actor (derived). **Pilots** are a second per-tick table (DC-S4): `actor_id` (u32), `region_id` (u16),
`end_tick` (u32), 10 B each.

### 2.3 Movement in integers

- **Tick order** (realtime §2.1): records, **move bodies**, agents, physics, outputs; stage 2 reads the body as of the
  tick's start.
- **Direction (T7; DC-S8):** stage 1 canonicalises `dir` = (dx, dy), integers, not both zero, to m = max(|dx|, |dy|)
  = 1000: d'_i = sign(d_i)·((2000·|d_i| + m) // (2m)). Only the canonical form is logged, so (1, 1) and (1000, 1000)
  are one record. The core's step: n = isqrt((dx'² + dy'²)·10⁶), step_i = sign·(140·|d'_i|·1000 // n); axis steps
  140 mm, (1000, 1000) gives (98, 98), 1.0% slow (derived). The vector is allocentric on the wire; Phase 4's adapter
  reduces an egocentric body command to it (OD-C11).
- **One blocked predicate** (AR-S4): the cylinder overlaps a solid truth cell in [feet + 0.05 m, feet + 1.8 m], or
  leaves the extent less the radius; disc–square in integer mm. A fuel-bed cell counts as solid while its remaining
  fuel fraction is above zero. **Sliding:** full step, else x part, else y part, else stay; 140 mm < the radius.
- **Walk grid:** 2-D, 0.1 m, a node free iff the blocked predicate is false at its centre. **A\*:** 8-connected,
  octile 10/14, no corner cutting, ties (f, h, j, i), cap = the grid's 4,800 nodes.
- **Path walking** (EX-S6): first leg from the exact position; last waypoint the exact target if free, else the
  nearest free node within 0.3 m (ties (distance², j, i)), else `unreachable`; pruning keeps the farthest waypoint
  whose segment passes the predicate sampled every ≤ 50 mm; each tick steps by the normalisation, landing exactly when
  the remainder ≤ 140 mm. Property test: every per-tick step passes the predicate.
- **Precedence:** a non-null `move` cancels a path; `move {dir: null}` clears a held direction; `move_to` replaces
  a path.
- **Replanning:** only `imagine` and admin `set_material` can block a path in Phase 1; a change replans once
  (bumping `path_version`), else `path_state` = blocked. Bit-identical on one machine; outcome class across (PH-S6).

## 3. Intents: one door

### 3.1 The pipeline (AR-B2, WT-B1)

Decode → stage 1 (`simcore` core intents) → log → stage 2 against the world at apply → one receipt. The record is boundaries §6.2's: `schema_version`, `kind`, `actor_id` (from the session token),
`seq`, `observed_tick`, `issued_tick`, `apply_tick`, `apply_us`, canonical `params`, `target`. Ordering key
`(apply_tick, kind_rank, apply_us, actor_id, seq)`.
- **Cause (the efference copy, npcs §6.6).** Receipts carry the intent's id, `(actor_id, seq)`; each bodies-part
  event and pilots row also carries it as `cause`. An agent's intent logs Maxim's invocation pid as opaque
  `invocation` (null for players), which its adapter maps `cause` to. The host copies it and never mints one; it is null, never a
  stand-in, until Maxim's G17 stage (npcs §6.6). Step 5b owns both; step 7
  freezes `cause`.
- **`observed_tick`** is the tick of the last cell frame sent to that session (DC-S1, boundaries §4.2), not the last
  `tick` message. Phase 1 has no stale rule, so it has no caller; it is logged for Phase 4 (DC-N8).
- **Authority** (boundaries §6.1): `move`, `move_to`, `kindle` are "any actor"; a body or an igniter is capability,
  checked at stage 2 (DC-N1).
- **`kind_rank`** `[engineering]`: join/leave 0, `time` 1, moves 2, `kindle`, `strike`, `douse`, `imagine` 3.
- **A held direction applies every tick until replaced.**
- **Walking is a body affordance NPCs will share** (T6, OD-C11). Maxim's bodies (6fee7377, `fold.md` Check 1):
  `base_humanoid.yaml`'s `legs.move {direction: str, speed: str}` takes any string, `minecraft_player.yaml`'s
  `avatar.move_to {x, z}` and `minecraft_bench57.yaml`'s offset sensors are a compass, a GPS and a position oracle
  no body has. Proposed: egocentric `move {forward, turn}` and target-by-percept-id.

### 3.2 `kindle` (T4; WT-B2, BF-S4, BF-S5, PH-S4, DC-S5–S7)

- **Action vocabulary v1** adds `kindle` (a bounded pilot) and retires `ignite`, as F7 retired `extinguish`. It ships
  with the first log writer (step 5), so no v0 intent log ever exists and the v0-log refusal test is moot (DC-S5).
  Until step 6's skin exists, step 5's `kindle` deposits by sphere volume overlap at the point with the item's radius,
  a marked, scheduled band-aid that step 6 removes. The red gate
  `test_a_fire_that_has_burned_its_fuel_stops_heating` is rewritten to use `kindle` when step 6 flips it.
- **`data/world/actions.yaml` v1** carries `kindle`'s physics-safety ceiling (`max_power_w`, `max_duration_s`,
  `min_radius_m` = 0.2) and drops `ignite`. It is repo-only, so v0 is refused by version with a test, never migrated (step
  3b). Limits are the ceiling intersected with the item's capability (boundaries §6.1 rule 3).
- **Power belongs to the item.** `content/items/torch.yaml`: `power_w`, footprint `radius_m` (≥ 0.2 m),
  `max_duration_s`, `restrike_s` (world time, seconds). Phase 1's torch is a propane pilot of order 2 kW, 15.9 kW/m²
  over its 0.2 m disc (*from memory*); its values come from step 6's band measurement (§6.3).
- **Checks:** stage 1 checks types and the ceiling; the item's maximum is a logged stage-2 code, `over_item_max`
  (DC-S6). Stage 2 derives the region: the named solid whose authored box surface lies within 50 mm of `point_mm`
  with the point no deeper than 50 mm inside; two candidates is `ambiguous_point`. Exact for boxes; non-box fuel waits
  for the CSG (AR-N4).
- **A body affordance, not a region one** (DC-S7): an NPC's `kindle` comes through its per-actor body modulator
  (boundaries §7.2), never `crate.kindle`. The log carries `target: null`; the derived region is in the receipt,
  recomputed on replay. The agent-facing parameter is `hold: brief | steady | long`, which the adapter converts to
  ticks from the item's data, so no tick count reaches an agent (npcs §3).
- **Deposit:** the footprint disc by face-area overlap onto the bed's skin (6b), no single-cell fallback. The pilot
  covers ticks [apply_tick, apply_tick + D); a physics step at tick t covers (t − 5, t], and receives P × 0.1 s per
  overlapping tick (DC-N6).
- **Lifecycle:** one live pilot per actor (`pilot_live`); it ends on expiry, on leave or when its region is gone.
- **Receipt meaning:** `applied` means placed, not ignited. Credit for a pilot that never lit is the **OPEN divergence
  OD-A16 / OD-C5**; the tile's numbers go to the OD-A16 draft as evidence.

### 3.3 Protocol v0's client messages (DC-B2)

| Client → server | Fields | Final reply |
|---|---|---|
| `hello` | `protocol: 0`, `token` | `welcome`, or `error` then close |
| `move` | `seq`, `dir: [int, int] \| null` | `intent_result` |
| `move_to` | `seq`, `target_mm: [int, int]` | `intent_result` (+ `path_mm`) |
| `kindle` | `seq`, `point_mm: [int, int, int]`, `duration_ticks` | `intent_result` |
| `time` | `seq`, `pause \| resume \| set_scale`, `scale` | `time_decision` |
| `snapshot` | `seq` | a cell frame with `in_reply_to` |

- **No client message names a region or actor.**
- **`strike`, `douse` and `imagine` have no wire message in v0** (T16); they join as versioned additions when a
  client caller exists. NPCs reach them through the adapter.
- **One receipt shape for every intent** (boundaries §7.2): `(actor_id, seq)`, outcome (`applied`, `refused`, `stale`,
  `cancelled`; the last two have no Phase 1 producer), refusal code, measured effect, before and after frame ids.
  `intent_result` wraps it with wire-only `apply_tick` and `path_mm`. Agent-facing receipts carry no tick.
- **Server → client** messages (`welcome`, `regions`, `tick`, cell frames, `error`) are specified in
  `client_rendering.md` §4.

### 3.4 Refusals (WT-S1, EX-S8), in check order

| Code | Stage | Reply | Logged | Step |
|---|---|---|---|---|
| `bad_json`, `unknown_kind`, `unknown_field`, `busy` | decode | `error` | no | 7 |
| `not_int` (bool, `5500.0`, `1e3`), `bad_shape` | stage 1 | `error` | no | 7 |
| `out_of_range` (`dir` both zero, a ceiling exceeded), `outside_extent` | stage 1 | `intent_result` | no | 7 |
| `rate_limited` (wall flood guards: `kindle` ≤ 5/s, `move_to` ≤ 10/s), `coalesced` | stage 1 (client protocol layer) | `intent_result` | no | 7 |
| `out_of_reach`, `not_on_surface`, `ambiguous_point`, `region_gone`, `no_igniter`, `over_item_max`, `pilot_live`, `restrike_wait` | stage 2 | `intent_result` | yes | 6 |
| `no_body`, `no_path`, `unreachable` | stage 2 | `intent_result` | yes | 5 |
| time refused (role) | `TimeAuthority` | `time_decision` | yes | 7, by a direct `HostOnly` test (WT-S9) |

- **The code enum lives in the core;** the client protocol layer produces `rate_limited` and `coalesced` (DC-N7).
- **A stop is never refused** (WT-S5): `move` and `move_to` are latest-wins per session per tick; the superseded
  one gets `coalesced`. Test: fill the queue while paused, release, resume; the body is still.
- **Planning:** at most one plan per actor per tick, a B5 meter (WT-S4).

### 3.5 The log header

Its content digests (boundaries §6.3) gain the body archetypes, items, spawns, the vocabulary and `actions.yaml`
versions, and the navigation constants (WT-S3). Rate limits are pre-log and stay out.

## 4. The simulation `Frame` (BF-B1, AR-S2, DC-S2–S4)

- **Two parts, one tick stamp; frame ids are ticks.** The cells part is a copy published when cells' version changes,
  shared by reference otherwise. The bodies part holds the actor table, the pilots table and that tick's events
  (`arrived`, `path_blocked`, `pilot_ended`, each with its new state).
- **A `Frame` is published every tick on which any intent was applied or refused, or any actor or pilot changed**
  (DC-S2; O23), usually the bodies part plus a reference to the unchanged cells. So a receipt's after-frame
  always exists.
- **Perceivers read the `Frame`, never the wire.** Test: an adapter's pinned actor table at tick T is identical at
  1×, at 20× and under a wire stall.
- **State carries what events announce,** so nothing is lost at speed (a pilot row, `path_version`, `path_state`). The client's events and their bounds are `client_rendering.md` §4.

## 5. What step 6 must deliver (D29, D30)

### 5.1 Constants, each with provenance (DPH-B1)

Each goes into material table v1 with a provenance row. **No constant is fitted to make the exit pass:** one changes
only with a new citation, and the exit's outcome follows from it.

| Constant | Value | Tag |
|---|---|---|
| ΔH_c,eff of wood volatiles | 12.4 MJ/kg | *from memory* (world_model §11) |
| char yield χ | 0.25 | *from memory* (0.2–0.3) |
| ΔH of char to CO₂ | 32.8 MJ/kg | *from memory* |
| heat of gasification L_g | 1.8 MJ/kg | *from memory* |
| pyrolysis surface temperature T_p | 380 °C | *from memory* |
| flame feedback q''_f, per m² of burning fuel surface | 25 kW/m² (literature range 15–35) | *from memory*: the cited source decides |
| critical heat flux | 12 kW/m² | *from memory* |
| radiative fraction χ_r | 0.3 | *from memory* |
| surface ε, h_c | 0.9, 10 W/m²·K | *from memory* |

### 5.2 The four laws

- **6a open-air loss:** each exposed face loses h_c(T_s − T_amb) + εσ(T_s⁴ − T_amb⁴) from its skin. In a bed, the
  envelope's loss is spread over a radiative penetration depth ℓ = 4/σ = 0.16 m (derived; a random-slat bed's
  extinction coefficient σ/4, *from memory*), in metres, so it doesn't depend on dx (D25).
- **6b the skin:** a 1 mm surface layer `[engineering]` on every exposed face and on each bed cell's fuel surface,
  carrying its own temperature and stored energy. Explicit stability at 0.5 s: ρc·δ/h_r = 600 × 1,700 × 0.001 / 420 =
  2.4 s (derived; h_r at 1,000 °C ≈ 420 W/m²·K, DPH-N3). Ignition is by area overlap with a critical heat flux.
- **6c the porous bed:** pyrolysis per m² of burning fuel surface is **m'' = q''_net / L_g**, with q''_net = q''_f +
  q''_pilot − the 6a envelope loss per m² of fuel surface. Volatiles burn at ΔH_c,eff; the flame deposits q''_f per m²
  of burning surface; the rest of the release leaves as plume. Char accumulates at χ per kg pyrolysed.
- **6d char oxidation:** diffusion-limited, m''_c = h_m·Y_O₂·ρ_air·(12/32), with h_m = h_c/(ρ_air·c_p) = 8.3 mm/s
  (derived): **0.86 g/m²s, 28 kW/m²** of char surface (derived, CO₂ assumed).
- **Thresholds on cell means:** `thermal_degrade` no longer drives fuel. It still drives concrete, a recorded D25
  Known gap.

### 5.3 The bed's numbers (derived from §5.1; DPH-B1, DPH-B2)

| Quantity | q''_f = 25 kW/m² | q''_f = 15 kW/m² |
|---|---|---|
| Envelope loss at T_p, 1.8 m² × 12.6 kW/m² | 22.7 kW | 22.7 kW |
| Sustains if σ·V·q''_f > envelope loss: σ_min | 4.2 m²/m³ (the bed has 25: 6×) | 7.0 m²/m³ (3.6×) |
| m'' = (q''_f − 22.7 kW / 5.4 m²) / L_g | 11.6 g/m²s | 6.0 g/m²s |
| Flaming heat release, m''·5.4 m²·12.4 MJ/kg | **777 kW** | 402 kW |
| Flaming phase, 24.3 kg of volatiles | **390 s** | 750 s |
| Feedback as a share of release per m² | 17% (of 144 kW/m²) | 20% (of 74 kW/m²) |

- **Cross-check:** Heskestad's crib regression rate for 20 mm sticks, about 2.3×10⁻⁵ m/s (*from memory*), gives
  13.8 g/m²s, the same order as 11.6.
- **The lone solid block (D30)** is all envelope, keeps none of its re-radiation, and goes out (DPH: 63 kW lost at
  600 °C against 58 kW released).
- **Embers (6d):** an envelope ember with the loss spread over ℓ balances 4 × 28 = 112 kW/m² of surface loss at
  **about 920 °C**. A bare exposed char face balances 28 kW/m² at about 550 °C (both derived). The visible envelope
  layer is above the 625 °C glow criterion, with margin from constants that are *from memory*.
- **Ember phase:** 8.1 kg of char at 0.86 g/m²s over 5.4 m², 4.6 g/s: **about 1,750 s** at about 150 kW (derived).
- **Burn-out:** about 60 s to ignite (the thermally thick closed form at 15.9 kW/m², derived), then flaming, then embers: **t_gone ≈ 2,200 s (37 min)** at q''_f = 25 and 2,560 s at
  15. Minutes, not hours.
- **Energy:** 24.3 kg × 12.4 + 8.1 kg × 32.8 = **567 MJ** (derived).

**Pre-registered failure path (DPH-B1, DPH-B2):** if, with cited constants, the bed doesn't sustain or the envelope
doesn't reach 625 °C, the exit fails, and the measured balance goes to the owner. No constant moves to rescue it, and
625 °C is never lowered.

### 5.4 The ledger (DPH-S1, DPH-S2; AR-B3)

**Inputs** `sources` (the pilot's P·D·0.1 s) + `combustion` (volatiles and char) = **storage** Δ(cells) + Δ(skins) +
Δ(bodies) + **outputs** `open_air_loss` + `plume_convective` + `flame_radiative` (received by bodies, and
`unreceived`) + `removed_with_mass`. Relative tolerance per substep and cumulatively (world_model §4).
- **The deposit test is not an identity:** Σ deposited = q''_f × A_burning × dt, with A_burning taken independently
  from the bed state.
- **Known gap, metered:** the flame's radiation is exported unreceived except by bodies: 0.3 × 777 kW = 233 kW for
  about 390 s, 91 MJ (derived). On `wall_north`, 0.4 m away, the point-source estimate is 20–40 kW/m², which would
  raise the concrete face 235–470 K in 390 s (semi-infinite, derived). That passes concrete's 300 °C degrade
  threshold, but the model's wall stays cold. Phase 2 radiation returns it.
- **`removed_with_mass`** books a burned-away or destroyed cell's sensible heat, never deleting it silently.

### 5.5 Fuel, char and crack (DPH-S5, PH-S7)

- **Remaining fuel = virgin wood + char, by mass.** `t_gone` is when it falls to 5% of 32.4 kg (1.62 kg). Ash is
  ignored (Known gap).
- **`crack` for a bed cell** = 1 − integrity, with integrity the cell's virgin wood fraction of its initial fuel, so
  charring shows as cracking and shape change.

## 6. The exit scenario

### 6.1 The clock

T3: tick 0.1 s (`tick_us` = 100,000), physics every 5 ticks.

### 6.2 The script (WT-S2, EX-S5)

A versioned script of inputs at apply ticks, `tests/scenarios/alley_exit.yaml`. It runs unpaced through
`Simulation.step`, and live in realtime §8's stepped host mode, with a Python client that sends each input when the
server reports the tick before its apply tick. Each run produces a log, and the replay test replays it.

| Tick | Input | Assert |
|---|---|---|
| 0 | `join` (host) | actor 1 at (600, 2000, 400) mm, holding `torch` |
| 10 | `move {dir: [1000, 0]}` | 140 mm per tick |
| 42 | `move {dir: null}` | `pos_mm` == (5080, 2000, 400) |
| 50 | `move_to {target_mm: [5500, 2925]}` | one segment, 1,015.9 mm; `pos_mm` == (5500, 2925, 400) at tick 57 |
| 70 | `kindle {point_mm: [6000, 2925, 725], duration_ticks: D}` | applied; region `crate` in the receipt; 500 mm from the axis |
| 75 | `time {set_scale: 10}` | granted |
| ≤ 54,000 | none | §6.3 |

- **The cap is 5,400 s** (54,000 ticks, 10,800 physics steps), 2× the slower estimate `[engineering]`.
- **Stage-2 variants** each assert their logged refusal and an unchanged world digest: `kindle` from the spawn
  (`out_of_reach`), at (6000, 2000, 725) (`not_on_surface`), twice (`pilot_live`), with no item (`no_igniter`), over
  the item's maximum (`over_item_max`). Decode and stage-1 variants are socket tests (§3.4).

### 6.3 Observed, automatically

Areas and masses in metres and kilograms, from the bed and face state. The crate's envelope is its cell faces
adjacent to air.
1. **Positions** as in §6.2.
2. **Ignited:** burning fuel surface ≥ 0.1 m² 60 s after the pilot ends `[engineering]`.
3. **Crack:** `t_crack` = first tick with ≥ 0.08 m² of envelope over cells with ≥ 10% of their fuel charred.
4. **Glow:** `t_glow` = first tick with ≥ 0.08 m² of envelope whose envelope-layer skin is ≥ 625 °C.
5. **Burned away:** `t_gone` (§5.5), before the cap.
6. **Order:** all exist, and `t_crack` < `t_gone`, `t_glow` < `t_gone`.
7. **Binary outcomes are band-gated** (S4): ignited, glow reached, burned away, `crate_far` intact. Step 6 measures
   the band in D (the torch's P fixed) at 0.2, 0.1 and 0.05 m and records its width in Known gaps. The script's D is
   ≥ 2× the band's upper edge at every grid `[engineering]`.
8. **Times converge** (DPH-S5), with absolute errors e against the 0.05 m reference and tol = 15% (`t_crack`,
   `t_glow`) or 10% (`t_gone`) of the reference value. Pass when |e₀.₁| ≤ tol, and (|e₀.₂| ≥ |e₀.₁| or |e₀.₁| ≤ tol/4).
   Tightened by measurement, never loosened.
9. **Determinism, on one machine:** two stepped runs, the unpaced run and the replay are bit-identical at every
   physics tick.

### 6.4 Controls that can fail (DPH-B3, DPH-S3)

| Control | Deletion that must turn it red |
|---|---|
| The ledger closes (§5.4) | drop one line |
| Max skin ≤ 1,300 °C, the surface balance at 4× the flaming release flux (DPH, derived) | disable 6a |
| Destroyed concrete within 1.0 m of the crate ≤ V_floor | deposit `plume_convective` into the floor |
| `crate_far` keeps every cell and rises ≤ 1 °C | resolve the pilot's region as the last wood region in the map |
| max(burning area) > 0 in (70, `t_gone`); after `t_gone`, burning and `combustion` are zero | never populate burning |
| `test_a_fire_that_has_burned_its_fuel_stops_heating` flips green; its gate is removed | (the gate itself) |

**V_floor is not circular** (DPH-S3). The contact temperature is fixed before the run at a 900 °C bound (the ember
balance, §5.3) for the cap's 5,400 s. V_floor is the same `thermal_degrade` law applied to the closed-form profile's
cell averages at each grid. For scale (derived), concrete passes 300 °C to 0.092 m under that bound. The control
inherits concrete's cell-mean threshold consistently per grid; that is the §5.2 gap, not a looser gate.

### 6.5 Runtime and tiers (EX-S11)

Heat cost from PH's uncached measurements: the **default gate** runs to tick 6,000 at 0.2 and 0.1 m (positions,
refusals, ignition, crack), 1,200 × 4.5 ms ≈ 5 s; **`slow`** runs to the cap, 10,800 × 4.5 ms ≈ 49 s; the
**verification run** (0.05 m reference, band sweep) takes 10,800 × 38.3 ms ≈ 7 min per run, results committed.

### 6.6 By the human

The owner plays at 1× through flaming (about 8 minutes), then 10× (about 3 minutes): walking, visibility behind every
wall, crack read as crack, glow as heat, burn-out as fuel running out, the dial. Verdict and latency go in the PR.

## 7. Placement (AR-B1, O24's four layers; DC-N7)

| What | Layer |
|---|---|
| Actor and pilots tables, body archetype type, motion, blocked predicate, walk grid, A\*, path walking, body heat (convection and radiation), the bed and laws 6a–6d, intents, the refusal-code enum, receipts, `Frame` | core (motion and navigation as two modules, AR-N3) |
| File gates (archetypes, items, scene v1, `actions.yaml` v1), the SEM membrane and agent adapter (the `hold` conversion) | adapters |
| The alley, `human`, `torch`, the bed's φ and σ, fuel calibrations | game (`content/`, rights reserved, step 8) |
| Wire encoding, sessions, latest-wins slots, rate limits, `TimeAuthority`, the network lane | client protocol |
| Godot | `client/` (`client_rendering.md` §7) |

## 8. Bio-faithful note

- **Perceivers read the simulation `Frame`,** never the wire or the log. The fire is perceived through physical
  channels at the perceiver: heat now (§2.1), light and sound in Phase 2 (BF-S1).
- **One world-owned body model.** Regions in metres are what Phase 4's surface percepts reduce over (world_model §9).
- **Divergences named:** the actor table as a direct view (ANALOG); receptors under two coarse cells (Known gap);
  `kindle` credit (OPEN, OD-A16/OD-C5); allocentric locomotion (OD-C11); no metabolism (Maxim's drives).
- **The world's day** is realtime §2.2's `epoch_us` and `day_length_ticks`. An SCN entrains on Phase 2 light at the
  perceiver, never on a time-of-day number or the client's sky.

## 9. Open questions for the owner

1. **The flame radiates into bodies by a point source in Phase 1,** walls in Phase 2: decided, T14.
2. **The crate as 20 mm slats at φ = 0.25** (σ = 25 m²/m³, 32.4 kg), step 6's content value: decided, T15. A denser
   crate burns longer and a sparser one may not sustain (σ_min 4.2–7.0 m²/m³).
3. **Protocol v0 freezes only the kinds a Phase 1 client sends:** decided, T16.
4. **The accelerant's form:** decided, T18.

## 10. What this does not settle

- **Step 6's measurements:** constants, torch values, band widths, the three times, ember temperature.
- **Phase 2:** flame radiation to surfaces, convection, zones, solid sub-cell recession, non-box fuel (CSG), ash.
- **Phase 4/5:** receptors, damage and pain, metabolism, line of sight, `turn`, egocentric locomotion (OD-C11).
- **The boundaries PR:** `cell_size_m` leaves the bridge's readings and metadata (BF-N4).

## 11. Requirements by plan step

| Requirement | Step |
|---|---|
| Amend realtime §7 to §3.3's table; architecture.md line 20 | 1 |
| Scene v1 (+ `spawns`), loader types for archetypes and items, the refusal-code enum | 3b |
| `Simulation` with actor and pilots tables, body motion, walk grid, A\*, body heat (convection; radiation closed forms), `move`/`move_to`, `cause` and `invocation` (§3.1), vocabulary v1 with the interim `kindle` deposit, `actions.yaml` v1 and its refusal of v0, the `Frame` rule, the alley fixture and its B5 meters | 5 |
| 6a–6d, the constants' provenance, the ledger lines, the skin deposit for `kindle`, the torch's band, the 0.05 m reference, V_floor, the red gate's flip | 6 |
| §3.3's messages, `intent_result`, `observed_tick` stamping, `cause` in events, the wire (`client_rendering.md` §4) | 7 |
| The game package and `content/`, the exit script, the controls by deletion, the stage-2 refusal scripts, the playtest | 8 |
| Save v0 with the actor and pilots tables and `body_key`; agent homes (O43) are save v1 | 9 |
