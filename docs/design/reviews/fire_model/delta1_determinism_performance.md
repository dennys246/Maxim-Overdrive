# Fire model v2 delta round 1: Determinism, replay and Performance

Reviewed: `fire_model.md` v2 on disk (staged), against v1 (08310d1), `fold.md`, CLAUDE.md, `code_review.md`,
`world_model.md` §1.2, §6, §8–§9, `gates` `boundaries.md` and `architecture.md`.

**Measurements** (D): `scratch/d1_probes.py`, `d1_probe_a2.py`, `d1_out.txt`; numpy 2.5.5, scipy 1.18.1, Python
3.14.6, arm64, threads 1, `process_time`, best of 3, **load 2.1–2.7**.

**Counts:** statuses 10 fixed, 3 open, 0 deferred, 0 rejected. New: 2 BLOCKER, 9 SHOULD-FIX, 3 NIT.

## Status of round-1 findings

| Finding | Status | Reading of the tree |
|---|---|---|
| DP-B1 cap that "dilates" | **fixed** | §8.1: local substeps, cap events in digest and tick status, same in play and test, world time fixed, forced test. Residue: D1-S8 |
| DP-B2 history-dependent cache | **fixed** | §4.4 pure occlusion; held field saved and digested; §6.2 save/load every step. New holes: D1-B1, D1-S4 |
| DP-B3 K = 2 | **fixed** | §2.1: objects by persisted u32 id, any count per cell; coupling rows CSR by (cell, object, segment) |
| DP-S1 delta form; Arrhenius | **fixed** as asked | §8.1, §3.1 cutoff, §6.2 sleep on/off. My round-1 predicate doesn't fire (D1-S2) |
| DP-S2 bounding box, cropped sums | **fixed** | §8.2 compact-support sleep only; reductions over full tables; §4.4 cutoff as a law; §9.2 ledger line for dropped power |
| DP-S3 order, labels, RNG | **fixed** | §8.2, §4.1 min-key stateless, §6.1 straddle. D1-N1 |
| DP-S4 retirement | **fixed** | §8.2 conserving merge, front fold, floor sweep |
| DP-S5 costs understated | **open** | Fixed: full 1D kernel, coupling frequency, flame count before R2.5. Open: no radiation figure under ruling 1; occlusion row can't see sub-grid fuel (D1-S5); clustering row is v1's kernel (D1-N2); §3.3 has no row (D1-B2); 1D row counts burning parts only (D1-S2) |
| DP-S6 no budget | **fixed** | §8.3 budget before R2.5, Known gaps, counters primary; §6.2. Must be a per-step max (D1-S1) |
| DP-S7 state; lazy profiles | **fixed** | §3.1; §9.2 full list; §5.4 vocabulary. Coupling rows missing (D1-S4) |
| DP-N1 cap 16 against heat's substeps | **fixed** | §8.1 "local cap (per law)" |
| DP-N2 arm64 only | **open** | §12 names it; no sub-step lands it. Raised (D1-S9) |
| DP-N3 one load, one stack | **open** (NIT, author's call) | not folded |

---

## New findings: BLOCKER

### D1-B1. A held field in watts can't conserve energy while Q changes, R2.5 can't see it, and nothing defines its keys

**Location:** `fire_model.md::§4.4` (Multi-rate), `§4.2`, `§6.2` R2.5, `§9.2` (held radiation field).

v2 holds "the radiation field" and saves it (save/load equality: fixed), but doesn't say what it holds. If it holds
absorbed power per receiver, three things break.

1. **The ledger.** §4.2 partitions each step's Q exactly: Q_rad,view + … = χ_r·Q(t). The held field delivers
   χ_r·Q(t_r)·F, frozen at the recompute step t_r. Suppose R4's crib grows from 200 to 300 kW between recomputes with
   N = 10 (5 s at 0.5 s per step). Receivers then absorb up to a third less than the partition books, every step but
   one. When the fire decays, receivers absorb power that no flame emits. Either the ledger fails (a standing gate,
   `world_model.md` §4) or a balancing line hides the gap.
2. **A flame that appears or vanishes between recomputes.** `kindle`'s pilot is "a flame object … heating by §4 like
   any flame" (§5.4). A torch applied at step t_r + 1 radiates nothing for N − 1 steps, while its Q is booked. A torch
   removed keeps radiating from the held field. A pilot shorter than N steps may never radiate at all.
3. **Keys.** Flames are stateless with min-key ids (§4.1), so a cluster's id changes whenever its minimum segment
   burns out, merges or splits. A field held per flame loses its flames. A field held per receiver row breaks when the
   topology batch retires a segment (§8.2) or `imagination.place` adds an object between recomputes: if the field is
   indexed by row, every later receiver inherits its neighbour's flux.

**R2.5 can't fail on this:** its Q is prescribed and constant, so a held field conserves there by accident.

**Fix.** Hold the expensive part, not watts.
- Hold **normalised transfer weights** w(emitter key, receiver key), the view factor times visibility, keyed by
  persisted keys and stored sparse and sorted.
- Each step, absorbed power = χ_r·Q_current(emitter) × w, and Q_rad,escape = χ_r·Q·(1 − Σw). This conserves every
  step by construction, and it costs one sparse product per step.
- **Emitter key.** Either the emitting segment (each segment's share of its cluster's emission), which survives
  clustering changes, or the cluster min key with a written rule. One such rule: a cluster whose key isn't held
  forces a recompute in that step's topology batch. That is deterministic, because it is decided from state.
- **Tests.** R2.5 gets a ramped and a stepped Q with N > 1, and must conserve to round-off on every step. N = 1 must
  reproduce the per-step scheme bit for bit (the identity pattern). And a pilot applied for fewer than N steps must
  still radiate.

### D1-B2. §3.3's surface-to-surface radiation has no cost, scheme, schedule or save status; "The cost is in §8.3" is false

**Location:** `fire_model.md::§3.3` ("The cost is in §8.3"), `§8.3` (no row), `§0` item 4 (the crib sustains
*because* its surfaces exchange radiation).

§8.3's table has rows for the 1D step, flame view factors, occlusion and clustering. It has none for exchange between
segments. Ruling 1 covers flame emitters only. This kernel scales with **segment pairs**, S(S − 1)/2, and in a crib
most nearby pairs are partly occluded by other rods.

The crib's segment count is unknown: the layout is "not in hand" (§12). As an illustration, about 100 sticks (§2.1)
at 10–20 segments each gives S = 1,000–2,000, so 5×10⁵ to 2×10⁶ pairs.
- **View factors** at round 1's measured ~40 ns per pair cost **20–80 ms per evaluation**.
- **Occlusion** must test each ray against the rods, since a voxel march can't see them (D1-S5). Measured at
  **55 ns per (ray, rod) test** (`d1_probes.py` (b)), that is 5×10⁵–2×10⁶ rays × 100 rods = **2.7–11 s per
  evaluation**. A 0.5 s step is the whole budget.

**Determinism holes.**
- Is the exchange recomputed each step, held like §4.4's field (saved state), or a pure function of geometry
  recomputed on change?
- Geometry changes continuously: char recession, and PMMA "thickness shrinks" (§2.3). "On change" therefore means
  stale weights after a load, which is DP-B2's failure again, unless they are snapped or saved.
- The exchange is also a coupling between parts with different local substep counts (§8.1). No scheme says which
  neighbour state a substep sees.

**Fix.**
- Give §3.3 a scheme:
  - pair weights as a pure function of geometry snapped to a stated tolerance in metres, recomputed in the topology
    batch when a snapped geometry key changes, and stored sparse and sorted;
  - a pair cutoff as a written law, with its power booked;
  - exchange applied once per physics step at frozen T, or implicitly.
- A row in §8.3, measured at R1's scale and estimated for R4 once the layout is in hand.
- Pair counts as a work counter.
- An F14 budget on pairs, which also covers imagined objects.
- Until then, remove "The cost is in §8.3".

---

## New findings: SHOULD-FIX

### D1-S1. Multi-rate divides the mean, not the step; the schedule's phase and start are unstated

**Location:** `fire_model.md::§4.4`, `§8.3` ("What owner ruling 1 buys", the fire budget "per physics step"),
`§11` item 1.

**The spike.** The recompute step costs the whole evaluation (round 1: ~275 ms uncached at the 1.92×10⁶-cell tile,
on a server already at 0.7 s per 0.5 s step). The host paces per step, so every N steps brings a hitch or dilation
burst; ruling 1's "÷ N" is the mean only.

**Schedule.**
- "A fixed schedule" doesn't say whether it is `step_index mod N == 0` from scene start, from the first flame, or
  from the last recompute. Every choice except the first adds a phase that must be saved.
- N is a content constant that changes bits, so it must be in the log header and the rerun manifest, and refused on
  mismatch.
- Scene start isn't stated. Is step 0 a recompute, or does the field start at zero?

**Fix.**
- Use `step_index mod N` from scene start, with step 0 a recompute, and put N in the header.
- Make the budget and the work-counter gate a **per-step maximum** over the worst scene.
- Or **stagger** the work: recompute the receivers whose `key mod N == step mod N` each step. That is just as
  deterministic and flattens the spike, and with D1-B1's normalised weights it still conserves.

### D1-S2. v2's sleep predicate never fires after heating, and the round-1 proposal behind it was mine

**Location:** `fire_model.md::§8.2` ("at bitwise equilibrium with zero forcing"), `§3.1` (profiles from authoring),
`§8.3` (the 1D row).

I proposed "bitwise equilibrium" in round 1, and it is wrong. Measured on delta-form backward Euler (`d1_out.txt`):
- **(a2)** 200 preheated 1 cm, 10-node profiles cooling to 293.15 K all reached a **state fixed point** (T + ΔT == T
  bitwise) after 32,000–34,700 steps (**≈ 4.8 h of world time**). None had a residual of exactly 0. None sat exactly
  at ambient: they stalled up to **625 ulp** away, with a residual of about 4×10⁻¹¹ W/m² that rounds away.
- **(a)** 200 stretched 20-node profiles about 10 cm deep: **none** reached a fixed point within 400,000 steps
  (55 h). They were still 0.03 K warm.

So "residual exactly 0" never fires for a part that was ever heated. Even the correct predicate fires only hours of
world time after the fire.

**Fix.**
- The predicate becomes: the part's last step was a bitwise no-op, and its inputs (coupled cell temperatures, held
  flux, neighbours' exchange) are bitwise unchanged since. Sleep on and off are then identical by construction.
- The cost table counts **every fuel part a fire has heated**, plus all fuel in a room whose air has warmed. It does
  not count only burning parts.

### D1-S3. Coupling once per physics step is explicit, and stiff for beds and for crowded fine cells

**Location:** `fire_model.md::§8.1` ("Coupling frequency"), `§2.2` (convection by overlap weight), `§2.1` (any number
of objects per cell).

Explicit exchange at Δt = 0.5 s between a segment and a cell's air is stable only while Σ h·A_overlap·Δt / C_cell
stays below about 1. Here ρc_air ≈ 1,211 J/m³K (D).

| Object in a cell | Ratio Σh·A·Δt/C_cell |
|---|---|
| A slab face crossing a cell, ratio h·Δt/(ρc·dx) | 0.04–0.12 at 0.1 m, **0.08–0.25 at 0.05 m** (h = 10–30) |
| A bed with exposed area a per m³ filling the cell, ratio h·a·Δt/ρc | **≥ 1 once a ≳ 240 m²/m³**, on every grid |
| Cardboard sheets 4 mm thick, 10–30% solid | a ≈ 50–150, ratio 0.2–0.6 |
| Crumpled paper, or unfilled sawdust | ratio about 4–10, which oscillates and grows |

A compact sub-cell object's ratio scales as 1/V_cell (stable at 0.1 m, unstable at 0.05 m); objects in one cell add.
§8.1's local substeps don't cover coupling, and the lag check (R0, R1: a slab in open air) never meets a bed, the
starter or a crowded cell.

**Fix.**
- Exchange per cell implicitly. For one object that is the exact two-body exponential relaxation, which conserves
  energy pairwise. For several, a small per-cell solve, in sorted object order.
- Count Σh·A·Δt/C per cell as a work counter.
- Add a lag check on a bed and on the starter at 0.05 m.

### D1-S4. Coupling rows: the rebuild trigger is unstated, and they are not in the save list

**Location:** `fire_model.md::§2.1` ("recomputed in the topology batch"), `§9.2`.

**Trigger.** "The topology batch" runs every physics step (`world_model.md` §6), but its work is event-driven. If the
rows are rebuilt only when a topology event happens, the weights depend on the geometry at the last event, which goes
stale as surfaces recede or shrink. A loaded save then rebuilds them from current geometry and diverges. That is
DP-B2 again.

**Save.** The rows are neither in §9.2's save list nor declared derived with a `derivation_version`.

**Cost.** Cylinder–cell overlap for every segment each step is unmeasured.

**Fix.**
- State one of two schemes:
  - (a) rebuild every step as a pure function of current geometry, with its cost measured; or
  - (b) rebuild on a snapped geometry key in metres.
- Either way, declare the rows derived, and add world_model §6's Hypothesis property: incrementally maintained rows
  equal a full rebuild bit for bit.

### D1-S5. Occlusion by voxel march can't see sub-grid fuel; making it see fuel adds a dx path §6.1 doesn't name

**Location:** `fire_model.md::§8.3` (occlusion row), `§4.4`, `§6.1` (dx paths), `§2.2` (occupancy `solid |
holds_fuel`).

Cells holding fuel stay air (§2.2, "Cells keep one temperature"). A march over `solid` therefore misses the crib's
own sticks, so every stick is lit from every flame. A march that treats `holds_fuel` as opaque makes a 2 cm stick
block a whole 0.1 m or 0.2 m cell, so shadowing grows with dx. That is a grid-dependent path §6.1's list omits.

**Fix.**
- Occlude against the objects in metres: rays or groups against rods and slabs, measured at 55 ns per test, with a
  broad phase.
- Keep solid cells for walls only.
- Re-derive the row.
- If any cell-based occlusion stays, add it to §6.1's dx paths.

### D1-S6. The smooth merge band, one emitter per cluster and min-key ids don't define a flame count

**Location:** `fire_model.md::§4.1`, `§8.3` ("Flame count is the crux"), `§11` item 1.

A smooth merge weight implies partial membership. A min-key id and one emitter per cluster imply a partition. If a
pair inside the band is one cluster, then at the band's outer edge one emitter has to reproduce two separate flames.
If it is two clusters, the weight blends nothing. Either way the cost-model's count, which v2 calls the crux, isn't
defined.

**Fix.**
- Partition by the band's outer edge, so components and min keys follow.
- Define emission inside a component as a weighted blend that equals the separate flames at weight 0 (several
  emitter cylinders per component is allowed).
- Count flames as emitters, not components, and add that count as a work counter.

### D1-S7. The opposed-spread front law divides by a vanishing quantity, and the hand-off between segments is unordered

**Location:** `fire_model.md::§3.2` (V = Φ/[kρc(T_ig − T_s)²]), `§2.1` (front position per segment).

**The singularity.** As T_s → T_ig, V → ∞. This is the K2_005 class: a near-zero denominator.

**The hand-off.** In one step a front can then cross several segments. v2 doesn't say how a front hands off to the
next segment. If the hand-off sweeps in segment-index order (Gauss–Seidel), a rod authored with its axis reversed
spreads differently, so the outcome depends on authoring direction.

**Fix.**
- Bound V by a written law: above a stated T_s the part flashes (§3.2), and V is never evaluated there.
- Advance fronts Jacobi-style from the previous step's state, at most one segment boundary per step. Any excess
  becomes a counted event, like a cap event.
- Test: one rod authored in both axis directions gives identical fronts.

### D1-S8. Cap events have no named client, and the fallback's accuracy is untested

**Location:** `fire_model.md::§8.1`.

v2 names no law that stays explicit: if none, the cap machinery has no client; if some, each needs two integrators.
The forced test checks only bits, yet ungraded play scenes can hit cap events, and an ulp across machines can flip a
part between paths.

**Fix.**
- Name the explicit laws, or state that none exist and the counter guards that.
- Make the forced cap-event test also require the **same outcome class** as an uncapped reference, per law.

### D1-S9. Subset independence is now load-bearing, and the golden CI is x86 (DP-N2 raised)

**Location:** `fire_model.md::§8.1` (local substeps per part), `§8.2` (sleep), `§12`.

Local substeps gather the parts needing step k, and sleep crops the awake set, so elementwise kernels (`exp`,
`expm1`, powers) see state-dependent offsets and lengths. Sleep-on/off identity holds only if a value's bits don't
depend on its array position: checked on arm64 only (0 of 170 slices). `golden.yml` runs `ubuntu-latest`, x86-64.

**Fix.** Land the offset test in 6.1's PR, run it on the CI matrix at 1 and N threads, and include the gathered
local-substep path in the sleep-on/off test.

---

## NIT

### D1-N1. Counter-based randomness revises a CLAUDE.md rule without saying so

**Location:** `fire_model.md::§8.2`, `§10.1`.

CLAUDE.md says randomness "comes from one seeded `numpy.random.Generator` owned by `World`". Keying by (cluster id,
tick) is a different rule; it is better, but it needs a row in §10.1. Two details also need stating: how the tuple
(object id, segment index) id is encoded into the key, and that the run seed is mixed in.

### D1-N2. The clustering row measures a kernel v2 dropped

**Location:** `fire_model.md::§8.3`.

The 10 ms figure is round 1's cell-adjacency `connected_components`. As a proxy for the metric version, a cKDTree
pair search at 0.05 m over 20,000 segment centres plus components took **14 ms** (`d1_probes.py` (c)); capsule
distances for candidate pairs would add to that.

The min-key partition was identical under permuted input; the raw pair order is unspecified, so any other consumer
must sort it.

### D1-N3. The cost table's count basis is ambiguous

**Location:** `fire_model.md::§8.3`.

The header says "At 20,000 segment parts", and the row says "22 ms at 52,000 parts". Each segment has two parts, each
with a profile, so state whether a figure counts segments or parts, and how many parts the exit scene and R4 hold.

---

## What is sound

- Local substeps with world time fixed.
- Cap events as counted state.
- Stateless min-key flames (the partition is order-free, measured), persisted object ids, profiles from authoring,
  full-table `bincount`, work counters, the every-step save/load test.

v1's determinism BLOCKERs are closed; what is new is conservation and cost in multi-rate and §3.3.
