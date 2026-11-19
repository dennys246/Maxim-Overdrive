# Determinism and replay, Performance: world_model.md (design v3 part 1, at 66310f4)

Reader brief: `docs/code_review.md`, the **Determinism and replay** and **Performance** rows, and "Design reviews".
Read: `docs/design/world_model.md`, `reviews/world_v2/determinism_lanes_performance.md` (DLP), the P1 section of
`reviews/world_v2/physics.md`, the probes in `research/states_of_matter/probes/`, and the code in
`.worktrees/act-validation` (`world/heat.py`, `world/grid.py`, `data/materials/core.yaml`), plus the installed
pymaxim.

Measurements were run here (numpy 2.5.4, scipy 1.18.1, Python 3.14.6, arm64, Accelerate), best of 5 to 7. The tile
is rebuilt to DLP's description: 16×10×4 m, a 0.4 m floor, 0.4 m outer walls, three 0.4 m interior walls, 40 crates
of 0.8 m. It comes out 31% solid against DLP's 24%, because DLP's exact crate geometry isn't committed. Scripts are
in the session scratchpad (`dp/p1.py` to `p8.py`), not committed. Every run took under 30 s.

Counts: **1 BLOCKER, 11 SHOULD-FIX, 5 NIT.**

---

## B-1. BLOCKER: "budget freedom, law by law" lets the wall clock choose what is simulated

**Location:** D21 ("A machine's time budget may coarsen or sleep only regions where the outcome is provably
unchanged"); §1.2 ("As a law is verified resolution-independent by its convergence test, it earns budget freedom:
the dial extends law by law, measured").

A convergence test proves agreement **within a tolerance**, not bit for bit. If a machine coarsens a law because its
time budget is short, the decision depends on how long the last steps took on the wall clock. So:
- the same scene and intent log, replayed on the same machine under a different load, take different coarsening
  decisions and give different bits. The rerun test (CLAUDE.md, "Determinism") fails, or passes only because its
  scenario never hits the budget;
- a replay on a faster machine never coarsens and diverges from the session it reproduces;
- the wall clock reaches `World` without being logged, which is the exact thing the Determinism lens asks about;
- two machines simulate different worlds again, which is what D20 exists to remove.

"Provably unchanged" is satisfied only by sleeping (§1.2's bit-identical test). "Verified by its convergence test"
is a different and weaker property, and the document treats them as the same.

**Fix:** a lever that changes bits is never chosen at run time from a wall budget. Either it is hashed world config,
fixed at session start and recorded in the log header (so a replay makes the same choice), or it is a logged input
that the replay applies. Restate D21 as: "the only run-time budget lever is one whose bit-identity is tested
(sleeping); every other lever is world config; otherwise the world dilates". Strike "the dial extends law by law" or
make it explicitly a config-time choice.

## S-1. SHOULD-FIX: "uniform, no sources, uniform halo" is not the condition for a bit-identical sleep

**Location:** §1.2 ("A chunk that is uniform, has no sources, and whose halo is uniform takes no step … Results are
bit-identical with sleeping on or off, and a test holds that").

Bit-identity is achievable. With today's stencil (`heat.substep`), a cell whose six neighbours hold its exact bits
gets `q = kf·0 = 0`, `flux_sum = 0`, `T += 0`, unchanged. A chunked evaluation of the stencil gave **bit-identical**
results to the full-grid one when the six face terms were added in the same order (measured, `p8.py`). But the
stated condition is not sufficient:
- **"Halo uniform" must be "halo equal to the chunk's value".** A chunk at 20 °C next to a uniform halo at 21 °C is
  uniform with a uniform halo, and gets a flux.
- **Every law must be inert, not only conduction.** Damage weakens a uniform chunk above `degrade_above_c` with no
  flux at all (`core.yaml`: concrete 300 °C). An Arrhenius rate is never exactly zero. Phase-change progress, skins
  (§3) and zone exchange each need their own inert condition. Each law should export its own "inert on this state"
  predicate, and quiet is their conjunction.
- **Zones are part of the halo.** With skins on every exposed face (§3), a solid chunk is quiet only if every skin
  node in it, and the temperature of every zone its faces touch, equal the chunk's value bit for bit.
- **Global quantities must ignore sleeping.** `stable_dt` and the substep count must be computed over all cells,
  including sleeping ones. Otherwise sleeping changes dt and every bit after it. Every reduction that crosses a
  sleeping chunk (zone sums, ledger, region reductions) must run over the full fixed index set in a fixed order.
  **Measured:** in 1000 random sums, `np.sum` of only the awake entries differed in the last bits from `np.sum` of
  all entries with exact zeros for the sleeping ones **771 times** (`p4.py`, pairwise summation regroups). `bincount`,
  which accumulates sequentially, gave identical results with interleaved zero weights. So an "optimisation" that
  sums only the awake list breaks the promise.
- **Wake by predicate, not by notification.** "Wakes the moment a neighbour, an action or a source touches it"
  reads as event notification. A missed event (a zone temperature changed by the implicit solve, which no one calls a
  "touch") silently diverges. Evaluate the quiet predicate from state at the start of every substep.
- **The on/off test is only as good as its scenarios.** A quiet-room scenario passes trivially. It needs one scenario
  per wake path (a neighbour's flux, a zone temperature change, an action, a new source, a law crossing its threshold),
  and it must be proven by deleting each wake condition in turn.

**Fix:** write the quiet predicate as above, in §1.2, with the reduction and `stable_dt` rules. Keep the test, with
the per-wake-path scenarios and the proof by deletion.

## S-2. SHOULD-FIX: sleeping saves nothing in the worst case, so it isn't a budget lever during a fire

**Location:** §1.2 ("Sleeping quiet chunks is the only budget lever that touches the simulation"); §1.1 (headroom).

Three measurements on the 0.1 m tile:
- **Every solid chunk has an exposed face.** 747 of 747 solid-bearing 0.8 m chunks (8³ cells), and 160 of 160 at
  1.6 m (`p2.py`). Walls are 0.4 m, thinner than a chunk.
- **The implicit zone step couples every connected zone in one step.** The inverse of (I + dt·L·V⁻¹) on a connected
  gap graph is dense (derived). A fire in one room changes the gas temperature bits of every zone connected to it at
  the first physics step, so every skin facing those zones gets a non-zero flux and every chunk holding one wakes.
- **Per-chunk evaluation costs more than the full grid.** The same stencil over all chunks costs 34.8 ms (8³) or
  14.5 ms (16³) against 6.0 / 5.2 ms full-grid, in numpy (`p8.py`). Sleeping only pays when fewer than **17%**
  (8³) or **36%** (16³) of chunks are awake.

So sleeping helps a quiet world, where the budget doesn't bind, and helps none during a fire, where it does. What is
sound: bit-level quiet genuinely persists in thick interiors (a concrete surface held at 800 °C perturbs bits only
4 / 5 / 9 cells deep after 10 / 60 / 1200 s at 0.1 m; steel 6 / 9 / 19; `p2.py`). The tile simply has no such
interiors.

**Fix:** say plainly in §1.2 that during a fire there is no budget lever, and the world dilates. Either defer
sleeping to Phase 2 "Scale" with chunk kernels written below numpy's per-call overhead, or keep it for the
whole-world-quiet case and record that.

## S-3. SHOULD-FIX: skins on every exposed face are costed nowhere, and their integration isn't stated

**Location:** §3 (heat exchange row: "a surface skin on every exposed face"); §8 (face table); §9; §1.1 ("That leaves
headroom for zones, skins and fuel").

P1 asked for a choice between a 16-node skin on every fine face and a skin on a fixed 0.2 m face lattice, before
`phase1/zones`. §3 and §8 take the first without saying so and without a cost. **Prototype** (`p1.py`): 16 float64
nodes per face, explicit diffusion, convection plus radiation at the surface node, the deep node coupled to its cell,
cell and zone exchange by `bincount`:

| | 0.2 m | 0.1 m | 0.05 m |
|---|---|---|---|
| exposed solid–air faces | 14,604 | 59,200 | 237,312 |
| skin update, per substep | 0.9 ms | **4.1 ms** | 22.6 ms |
| 1-node skin, for comparison | 0.3 ms | 1.4 ms | 7.4 ms |
| node state (16 × f64) | 2 MB | 8 MB | 30 MB |

At 0.1 m a skin substep costs about as much as a cached heat substep (3.1 ms here, f64). It is affordable, but it
doubles the per-substep cost, and the document doesn't say so. More importantly:
- **The skin has its own stability bound, set in metres, not by dx.** With 16 nodes over 5 cm (3.1 mm spacing), an
  explicit skin needs dt ≤ dz²/2α: about 7 s for concrete, **0.37 s for steel**, and about 0.05 s for aluminium or
  copper (derived). A conductive metal in the material table forces about 10 skin substeps per 0.5 s physics step,
  roughly 40 ms at 0.1 m. State the integrator: implicit (a batched tridiagonal solve per face) or subcycled, and
  cost it.
- **The face table's size follows exposed area, not the grid.** It isn't in §9's 100–125 B/cell (here +13 B/cell
  at 16 nodes). Fire, and Phase 2 rubble, grow it: a fully broken-up region approaches 3 faces per cell, 136 B each.
  F14's "memory budget checked from the header's declared shape" must also bound the declared face-row count, with a
  hard cap.

**Fix:** record the per-face choice against P1's lattice option, with the numbers above. State the integrator and
its stability bound. Add the face table to §9's memory and to the budget check, as DLP S-11 asked ("count its bytes
against the budget, as a function of exposed area").

## S-4. SHOULD-FIX: sub-box recession and breach by thickness reintroduce continuous topology next to the integer counts

**Location:** §2 and §6 (zone volumes and gap areas from integer counts); §3 (sub-box recession "tracks the receding
surface inside it in metres"; breach "decided by remaining thickness in metres").

The integer counts fix DLP-B1 because topology becomes a pure function of the cells. §3 then makes a burning cell's
open volume, and a breaching wall's open area, continuous quantities in metres. One of two things follows, and the
document must say which:
- the zone's volume and gap areas ignore sub-cell recession and change only when a cell is fully gone (the counts
  stay exact, and the zone's volume jumps by dx³). Then §3's metre-level geometry and the zone's geometry disagree,
  and the gap opens at "cell gone", not at "breach by thickness";
- or they include it. Then volumes and areas are float sums again, and the incremental-equals-recompute property
  fails as DLP-B1 measured, unless they are recomputed from scratch, in a fixed order, every step.

**Fix:** state that zones and gaps read the integer counts only, and that a breach opens a gap through a topology
event (`set_material`) when the thickness rule fires, not continuously. Or state the full-recompute rule for the
continuous part.

## S-5. SHOULD-FIX: the tripwire's matching rule is unstated, and identity matching is unreliable

**Location:** §6 ("The tripwire uses a per-thread `sys.setprofile` hook … The hook catches all three in a test").

DLP S-8 said the hook sees built-ins "by object identity". Measured (`p5.py`, `p6.py`):
- **`datetime.datetime.now` is a fresh bound object on every access** (`a is not b`). A banned set of `id()`s
  captured at import holds an id that is freed and reused. In one run that produced **false positives** on
  `list.append`, `str.rstrip`, `get` and others inside `np.random.default_rng()`. In another, a true positive by
  coincidence of id reuse. Match on `(arg.__self__, arg.__name__)` or on module and qualname, never on `id()`.
- **An unseeded `random.Random()` escapes both checks.** It seeds from OS entropy inside C, so the hook sees no
  `urandom` call. It is a new instance, so the global `random.getstate()` doesn't change. pymaxim constructs
  `random.Random(...)` in five modules (`simulation/dm_runtime.py:132`, `rng or random.Random(campaign.seed)`, is
  unseeded if the seed is None). `np.random.default_rng()` unseeded *was* caught, through `SeedSequence`'s
  `urandom`.
- **Overhead:** on a numpy-heavy loop the hook costs nothing (19.4 → 19.6 ms). On pure-Python code it costs
  **4.7×** (6.5 → 30.9 ms). The document doesn't say whether the hook runs in production or only in tests. Once the
  SEM bridge and percepts run Python on the simulation thread (part 2), that matters.
- A profiler (cProfile) on the simulation thread replaces the hook silently.

**Fix:** state the matching rule (by owner and name). Add constructing an unseeded `random.Random` or `Generator`
to the banned list (or require every RNG in the simulation path to come from `World`'s generator, checked by a
test). State that the hook is test-only or measure its production cost. Have the hook check that it is still
installed at the end of `step`. Keep DLP's three-way proof, which §6 doesn't restate.

## S-6. SHOULD-FIX: batched topology leaves an intra-step state undefined, and the cache rebuild isn't batched

**Location:** §6 ("Topology work is batched once per physics step, not per substep"); §10 (4, cached conductances).

- **Between substeps.** A cell destroyed in substep 1 of a physics step has its material changed at once (conduction
  must see it), but zone membership, gap counts, region ownership and the face table update only at the step's end.
  For the remaining substeps, what does the newly open cell's face exchange with, which zone owns its volume, and
  does its skin exist? Any answer is deterministic, but it has to be written, or two implementers (or a live run and
  a load mid-step) differ.
- **Cache rebuilds.** Cached conductances and `stable_dt` must be rebuilt on every material change. DLP S-6 asked for
  this **per affected chunk**. §6 and §10 don't say so. Today's `stable_dt` costs 12 ms at 0.1 m per call (DLP),
  about the cost of three cached substeps. A per-chunk rebuild is bit-safe: the harmonic mean is elementwise, and a
  min doesn't depend on order.
- Record the relabel cost per physics step as a B5 row (DLP S-6), which isn't in the document.

**Fix:** write the intra-step rule (for example: a cell destroyed mid-step is air for conduction at once, and joins
its zone, gaps and face table at the step's end, with its skin removed then), the per-chunk cache rebuild, and the
B5 row.

## S-7. SHOULD-FIX: the fold table claims more than §§2–9 fold

**Location:** the fold table and its "Not in this part" list.

Row by row against DLP:

| DLP | Cited | Folded as asked? |
|---|---|---|
| B-1 integer counts | §2, §6 | **Partly.** Counts, after minus before, sorted assembly and the Hypothesis property are there. Missing: computing the delta over the changed cells **dilated by one** (otherwise two adjacent changed cells count their shared face twice), and proving the test by switching one counter back to a float. S-4 above opens a new hole. |
| B-2 latency mode | part 2 | Correctly deferred. |
| S-1, S-2 | part 2 | Correctly deferred. |
| **S-5 settling order and fixed point** | "part 2, the thinking lane" | **Misattributed.** S-5 is about rubble settling: whether `loose` is sticky, whether loose cells carry load, the order-independent settle and its iteration cap. It belongs to §7, and its first question decides the meaning of the `loose` channel that §7 reserves now in the frozen grammar. Fold the meaning of `loose` (sticky or not) into §7. |
| S-3 conservation | §3, §4 | **Partly.** L·V⁻¹ and per-gap transfers are folded. Missing: limiting each transfer by what the donor holds; correcting the research's formula at its source; a tolerance **per conserved quantity** (§4 states one for energy only). |
| S-4 labels | §6 | **Partly.** Persisted id and metric key are there. Missing: the overlap-matching rule and its tie-break, the split rule, and "never iterate in label order". |
| S-6 relabel | §6 | **Partly.** Batching and 6-connectivity are there. Missing: per-chunk cache rebuild, the B5 row, and retracting v2's "O(changed region)". The quoted range 0.6–0.9 / 3.9–5.7 / 31–47 ms spans 6- and 26-connectivity; with 6 chosen, the figure is 0.6 / 3.9 / 31 ms. |
| S-7 header | §8 | **Partly.** Library versions, platform and dirty flag are there. Missing: the code SHA (D2, DD8); the new outcome-deciding values as hashed world config (connectivity structure, settle iteration cap, zone exchange coefficient and aperture rules); a replay labelling a mismatch "environment changed"; regenerating golden logs on an environment bump as their own commit. |
| S-8 tripwire | §6 | Folded, with S-5 above. The three-way proof isn't restated. |
| S-9 f64 caches | §4 | **Folded.** |
| S-10 memory | §9 | **Partly.** The figures and "counts transients" are there. Missing: transients declared as registry rows of kind `scratch`, and the B5 tracemalloc-peak gate that makes "counts transients" a check. |
| S-11 face state | §8 | **Partly.** The container is there. Missing: its iteration order (sorted by linear face index) and its bytes in the budget (S-3 above). |
| S-12 reductions | §9 | Folded for this part. |
| N-1 log inputs, canonical hash | not listed | Half-folded by §8's "SHA-256 over a canonical serialisation". The normative input list belongs to part 2; say so. |
| N-2 | not listed | Part 2. |
| N-3 probes | E8 row | Folded (the probes are committed). |
| N-4 denormal floor in the ledger | not listed | **Dropped.** |
| Performance verdict: "air out of the solve" needs a PR, or a Phase 2 note, and a dial per profile | §4 | **Not folded.** §4 restates the condition but names no PR and no dial. See S-10 and S-11 below. |

**Fix:** correct the S-5 attribution, fold the partial rows or list what is deferred and where, and add N-1, N-2 and
N-4 to the table. The table's claim to list "every v2 finding within this part's scope" is false as it stands, which
is the A-B1 failure the table exists to prevent.

## S-8. SHOULD-FIX: "relative, close to 1e-12 of the tile's total energy" isn't a bound

**Location:** §4 ("The ledger's tolerance is relative … changes close to 1e-12 of the tile's total energy, per
substep").

- **The total depends on the reference temperature.** On this tile (196.8 m³ of concrete, 4.2×10⁸ J/K) the heat
  content at 20 °C is 1.2×10¹¹ J from 0 K, but 8.3×10⁹ J from 0 °C, which is what `heat_energy_j` uses by default. The
  tolerance changes 15× with an arbitrary choice.
- "Close to" is not a gate.
- The round-off a ledger accumulates scales with the magnitudes it adds (the stock and every transfer), not only the
  stock.

The magnitude is achievable: 1e-12 × 1.2×10¹¹ is 0.12 J per substep, against an ulp of 1.5×10⁻⁵ J at that total
(measured). The definition is what's missing.

**Fix:** state the reference (0 K for energy), and a bound of the form |ΔE − (sources − outflow)| ≤ k·ε·(|E| + Σ|transfers|)
with k stated, per conserved quantity (energy, each species' mass, O₂).

## S-9. SHOULD-FIX: Phase 2 refinement needs foundations now, like rubble's, and isn't identical across machines

**Location:** D21, §1.2 ("Every machine refines identically"); §7 (foundations listed for rubble only); §8 (face table
keyed by cell index).

- **Identical only on one machine.** A refinement criterion is a threshold on floats. Across machines (different
  libm, BLAS) the last bits differ, and a refinement decision near its threshold flips, so the two runs then hold
  different cells. CLAUDE.md promises only the outcome class across machines. Say so, and give refinement
  hysteresis and a band like the binary outcomes in §3.
- **The formats assume one uniform grid.** The face table key (cell index, face 0–5), `region_id`, the integer
  counts and the snapshot grids all mean "a cell of the one grid". Refinement changes what a cell index is. §7
  reserves rubble's channels so Phase 2 "adds behaviour without changing a format". Refinement needs the same:
  counts in units of the finest level, and a key with room for a level.
- **Cost lands where the budget is tightest.** Refinement concentrates cells at fronts, so it adds cost exactly
  during a fire (S-2), and finer cells shrink the global stable dt unless time steps are local.

**Fix:** add refinement to §7's foundations (key format, count units), or state that refinement will be a format
version bump.

## S-10. SHOULD-FIX: with zones and skins, air must leave the conduction solve for correctness, not speed

**Location:** §4 ("Air leaves the conduction solve only when the solve runs over solids or active chunks"); §8
("Air cells' `temperature_c` stays cell temperature").

Today air conducts (`core.yaml`, air k = 0.026). Once skins exchange heat between solid faces and zones (§3), any
remaining conduction through air cells is a second path for the same heat. A solid face then exchanges with the zone
through its skin and with the adjacent air cell through conduction, which double counts. Air faces must carry zero
conductance whatever the solve sweeps. §4 reads as a performance option.

Then an air cell's temperature is never updated, but it is still saved, digested and sent as `temperature_c`, "cell
temperature". It is stale state with a claimed meaning. Define it (for example, the zone's temperature, written each
step, or absent for air).

**Fix:** state that air faces have zero conductance from `phase1/zones`, and define air cells' `temperature_c`.

## S-11. SHOULD-FIX: D20's cost lands on the time dial, and the document doesn't state the ceiling

**Location:** §1.1 ("That leaves headroom … at real time"), §9.

"At real time" is right. The dial is what D20 costs. Estimate per 0.5 s physics step at 0.1 m on this machine, with
2 substeps per step (DLP's schedule):

| Work | Quiet room | During a fire |
|---|---|---|
| heat, 2 cached substeps (3.1–3.9 ms each, measured) | 6–8 ms | 6–8 ms |
| skins, 2 substeps (4.1 ms each, measured prototype; more with metals, S-3) | 8 ms | 8–40 ms |
| latent correction (DLP's 30 ms at 0.05 m ÷ 8, derived) | about 4 ms | about 4 ms |
| region reductions (about 3 ms per field, derived from DLP's 23 ms at 0.05 m) | 3–15 ms | 3–15 ms |
| relabel, 6-connected plus anchor test (DLP) | 0 | about 4 ms |
| face table rebuild (full scan, measured) | 0 | 3 ms |
| conductance and `stable_dt` rebuild (full: 12 ms; per chunk: less) | 0 | up to 12 ms |
| fuel laws over about 20 k fuel cells, if sparse (estimate) | 0 | 1–3 ms |
| **total** | **about 20–35 ms** | **about 30–90 ms** |

So on this machine the dial tops out at roughly 15–25× in a quiet room and 5–15× during a fire. A laptop two to three
times slower gets a third of that. Real time holds everywhere. A cradle running "at 300×" (DLP B-2's example) can't,
at the 0.1 m truth, without a lever that S-2 shows doesn't exist during a fire. Part 2 depends on this.

**Fix:** put the dial ceilings per machine class in §9, as derived figures to replace with measurements in
`phase1/sim-clock`, and carry them to part 2.

## N-1. NIT: the 3.9 ms figure was measured with float32 conductances; §4 requires float64

DLP's table says "cached f32 conductances". Measured here with the same kernel: f32 3.3 ms, **f64 3.1 ms** at 0.1 m
(28.4 / 27.3 ms at 0.05 m, `p7.py`). The mixed-precision multiply upcasts anyway, so float64 costs nothing. Say so,
so the number in §1.1 matches the decision in §4.

## N-2. NIT: the dilation report is a wall-derived value; say it never enters the simulation

The tick status's effective time scale (§1.2) is measured on the wall clock. State that it is computed by the host,
outside `Simulation.step`, is never read by it, and is not a logged input. Otherwise someone feeds it to a "budget
freedom" law (B-1).

## N-3. NIT: name `bincount`'s accumulation order as part of the contract

Region reductions by `bincount` (§9) accumulate sequentially in linear cell order: deterministic, and unaffected by
exact zeros (measured). A later "faster" reduction (per-mask `sum`, `add.reduceat` over a sorted permutation)
changes the bits. Write the order down as part of the reduction's definition.

## N-4. NIT: §9's 64–80 MB per tile leaves out the face table

8 MB at 16 nodes on today's exposed area (S-3), growing with exposure.

## N-5. NIT: platform paths for transcendental functions

On this machine `np.exp` and `np.power` gave identical results on strided and contiguous inputs, in float32 and
float64 (`p3.py`, `p4.py`). numpy's SIMD dispatch differs on x86 (AVX2, AVX-512), and chunked or masked evaluation
(sleeping, sparse fuel laws) passes strided views where the full-grid path passes contiguous ones. Run the sleep
on/off test, and the sparse-versus-dense fuel tests, on each platform that replays are expected to run on.

---

## Checked and found sound

- **Bit-identical sleeping is achievable** for the conduction stencil: a chunked evaluation matched the full grid bit
  for bit when the face terms were added in the same order (measured). The conditions are S-1's.
- **Bit-level quiet does persist** in thick interiors: an 800 °C surface perturbs bits only 4–9 cells into concrete
  over 20 minutes at 0.1 m (measured). Sleeping is sound in principle; S-2 is about where it pays.
- **Integer counts** are the right root fix for DLP-B1. Integer ± is exact and order-independent, and m³ = count·dx³
  is a pure function.
- **`bincount` reductions** don't change when exact-zero weights are interleaved (measured), so a reduction over the
  full index set with sleeping regions as zeros is bit-safe. The 23 ms against 88 ms claim is DLP's measurement.
- **Float64 caches** cost nothing measurable (N-1), and keep the 1e-12 regression meaningful.
- **A per-chunk cache rebuild is bit-safe:** the harmonic mean is elementwise, and `stable_dt`'s min doesn't depend
  on order.
- **The per-thread `sys.setprofile` hook** catches `urandom` through an unseeded `np.random.default_rng()`, and costs
  nothing on numpy-heavy code (S-5 for its gaps).
- **Relabels once per physics step** at 0.1 m (about 4 ms) are affordable, about 1% of a 0.5 s step.
- **The ledger's magnitude** is achievable: 1e-12 of the total is about 6,500 ulps (S-8 for the definition).
- **The exposed-face table** can be rebuilt from scratch in 3 ms at 0.1 m (measured), so a sorted-array container
  rebuilt or merged once per physics step is cheap.
- **0.1 m is affordable at real time** with zones, 16-node skins and fuel, on this machine by a margin of 5× or more
  (S-11's table). §1.1's claim holds. The open question is the dial.
- **§8's log header** (library versions, platform, dirty flag) is the core of DLP S-7.
- **The zone row in §3** (L·V⁻¹, antisymmetric per-gap transfers) is the right form and cites DLP's measurement
  correctly.
