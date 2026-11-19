# Benchmarking new signals: a field contract and a verification ladder

Design note for Maxim Overdrive, 2026-11-15. Nothing in the repo was modified. Two measurements below were run
against the current code (`tests/test_heat.py::_error` at extra cell sizes); everything else is proposal.

## The short version

- Treat each new signal (O2, CO2, smoke, toxins, water, sound, light, electricity, radiation, load) as a **field** that
  has to be admitted. Admission takes two things: a **contract** (a YAML file that declares units, what is conserved,
  boundaries, couplings, stability, cost, snapshot channel and percept) and a **ladder** of benchmarks it has to pass.
- "The standard" a field is compared against is not one thing. It is a fixed order of preference: **exact analytic
  solution > manufactured solution > lumped (0-D) reference for couplings > the field's own Richardson-extrapolated
  limit across the rigs > an external solver (offline, committed as a fixture)**. Self-convergence alone never counts
  as correctness, because a wrong model converges just as happily as a right one.
- Verification follows the split that computational science uses. **Code verification** (is the equation solved
  right: closed forms, manufactured solutions, observed order of accuracy) runs on small standalone grids at any cell
  size and costs seconds. **Solution verification** (how far each rig is from the continuum, and is the outcome class
  safe) runs on the real rigs. The current tests mix the two. Separating them is the single most useful change.
- Gate performance on **deterministic counts** (substeps, cell-updates, snapshot bytes), which are exact and
  portable. Gate wall time only against a baseline from the same machine, using best-of-N after a warm-up.
- Build the small shared harness first (observed order, three-grid GCI, conservation helpers) and retrofit heat to it.
  Then make **oxygen the first new field**: its coupling benchmark (a fire in a sealed room) also gives Phase 1 its
  missing "fire goes out" fuel model. Hold off on a generic field-plugin framework until the second field exists.

## Two findings from the current code that motivate this

**1. Heat's observed order on the rig ladder is about 3, not 2. The current test can't tell.**
`test_error_falls_with_resolution` asserts `fine < coarse / 4`. Measured max-norm error for the Gaussian pulse:

| cell (m) | 0.2 | 0.1 | 0.05 | 0.025 |
|---|---|---|---|---|
| rig substeps (4·4^k), error | 9.95e-3 | 1.14e-3 | 8.91e-5 | 2.21e-5 |
| observed order p between neighbours | | 3.13 | 3.68 | 2.01 |
| fixed 2048 substeps, error | 1.28e-2 | 3.37e-3 | 8.17e-4 | 1.69e-4 |
| observed order p | | 1.93 | 2.04 | 2.27 |

The scheme is second order (the fixed-dt column shows it). On the rigs, though, `min_substeps_per_turn` refines dt as
dx², so the forward-Euler time error and the spatial truncation error partly cancel. The laptop grid also resolves the
pulse with only 1.5 cells per sigma, so it sits outside the asymptotic range, and the order only settles to 2 at
0.025 m. The architecture doc's "1% / 0.1% / 0.01%, second-order" is true for both numbers, but the rig ladder is
evidence of *error*, not of *order*. Oberkampf and Roy's standard for code verification is that the observed order
should match the formal order. An observed order *above* the formal order is a warning sign, not a bonus: it means
errors are cancelling or the grids are pre-asymptotic. The fix is to refine one thing at a time on purpose-built
grids (fixed small dt for space, fixed fine dx for time) and assert `p` inside a band around the formal order.

**2. The late-burn lag is, formally, a non-asymptotic solution.** The crate's integrity after 150 turns is
0.55 / 0.37 / 0.38 at 0.2 / 0.1 / 0.05 m. Write ε₃₂ = 0.55 − 0.37 = 0.18 and ε₂₁ = 0.37 − 0.38 = −0.01. The two
differences have opposite signs, and Celik et al.'s procedure classes that as oscillatory convergence: no GCI can be
computed, and the coarse rig is outside the asymptotic range. A harness that computes this every run turns the
known-gap prose into a number that is recorded, can be watched over time, and goes red if the gap widens.

## 1. What established practice says, and what we take from it

| Practice | What it is | What we adopt |
|---|---|---|
| Code vs solution verification (Oberkampf and Roy; ASME V&V 20) | Code verification checks that the equations are solved correctly and that the observed order matches the formal order. Solution verification estimates the numerical error of one particular run. Validation compares the model with reality. | Rungs L1–L2 are code verification and L4 is solution verification. We do no formal validation, because there is no experimental data and this is a game. Each field records "reference facts" with citations instead (for example, Huggett's 13.1 MJ released per kg of O2 consumed). |
| Method of manufactured solutions (Roache; Salari and Knupp, SAND2000-1444) | Pick a smooth function, push it through the PDE to get a source term, run the code with that source, and check the error falls at the formal order. It catches any bug that affects the order of accuracy. | Required wherever no closed form exercises a term: variable coefficients, coupling terms, every boundary type. Derive the source terms with sympy offline and commit them as plain numpy code, so there is no symbolic maths in CI. Every field must accept an arbitrary per-cell source term (heat's `power` callable already does). |
| Grid convergence, Richardson extrapolation, GCI (Roache; Celik et al. 2008; NASA NPARC tutorial) | From three grids with refinement ratio r: observed order p = ln(ε₃₂/ε₂₁)/ln r, an extrapolated value f_ext = f₁ + (f₁ − f₂)/(r^p − 1), and GCI_fine = 1.25·\|ε₂₁/f₁\|/(r^p − 1). Celik recommends r > 1.3 and flags oscillatory convergence. | Our rigs form a natural three-grid family with r = 2. Compute p, f_ext and GCI for every decisive SEM reading (onset turn, integrity, peak temperature). Record them, but don't gate on them, except that a scenario must not show oscillatory or divergent convergence unless it is a declared known gap. |
| ASME V&V 20 validation interval | The comparison error is the centre of an interval whose width comes from the numerical, input and data uncertainties. | Adapted as an **outcome margin**: a canonical scenario's decisive quantity must sit at least 2× its cross-rig spread (or 2× GCI) away from the outcome threshold. A scenario that sits on a threshold flips class through rounding and proves nothing. |
| Conservation and invariants | A scheme in conservative finite-volume form conserves to round-off in a closed box, so a residual above round-off is a bug, not an approximation. | Already in place for heat (1e-9). It generalizes to a **budget closure**: for every conserved quantity, change in total = sources − sinks + boundary flux, to round-off, including across couplings. |
| Benchmark suites (Ghia et al. lid-driven cavity; NIST FDS Verification Guide and its Firebot CI; Erez, Tassa and Todorov's engine comparison) | A small number of canonical cases with tabulated reference answers, rerun automatically on every change. Erez et al.'s main lesson: an engine does best on the systems it was tuned for, so the suite has to contain *your* scenarios. | A fixed set of canonical scenarios per field, with committed reference answers, run in pre-push. FDS (NIST's open fire, smoke and oxygen solver) is the natural external reference for fire, O2, CO2 and smoke. Use it offline only. |
| Performance benchmarking (Python `timeit` docs; pytest-benchmark; CodSpeed and instruction counting) | Report the minimum of repeats rather than the mean, because noise only ever adds time. Warm up first. On shared CI machines wall time is noise, so gate on counts instead. | Exact counters are gated everywhere. Wall time is measured best-of-5 after one warm-up and gated at 20% (B5) only against a same-machine baseline. In CI it is reported, not gated. |
| Game practice: deterministic lockstep and replays (Factorio's Friday Facts #47 and #315: a CRC every tick; "heavy mode" saves, reloads and compares each tick) | Determinism is tested by replaying and comparing state hashes. A mismatch is a bug report that reproduces. | Every field's state goes into `digest()`. Add a "heavy mode" test per field: snapshot and restore mid-run, and require the same hash. This is cheap and catches state the save format forgot. |
| Feature toggles (Hodgson, on martinfowler.com) | Release toggles are short-lived and removed once the feature ships. Experiment toggles exist to compare variants. | A candidate field is an experiment toggle with a removal date: off by default, never in a shipped scene, and either admitted or deleted. A lint enforces it, in the same style as the `TEMPORARY(phaseN)` markers. |

## 2. The field contract

Each field gets one file, `data/fields/<name>.yaml`, which is loaded and validated strictly in the same way as
`actions.yaml` (closed key set, finite reals, B12). It is a declaration, so the checks can read it. Example for oxygen:

```yaml
format: 1
name: oxygen
status: candidate            # candidate | admitted | retired
owner_phase: phase2
quantity:
  symbol: rho_O2
  unit: kg/m3                # per unit volume, always (resolution rule)
  dtype: float64             # float32 only with a declared conservation tolerance to match
  initial: 0.279             # 0.232 mass fraction x 1.204 kg/m3 air at 20 C
  bounds: [0.0, 0.33]        # physical range; Hypothesis and a runtime assertion check it
conserved: true              # if true: an insulated-box budget closure to 1e-9 relative is mandatory
transport:
  model: diffusion           # diffusion | advection_diffusion | wave | quasi_steady | topological
  coefficient: {name: D_eff, unit: m2/s, per_material: true}
  time_model: explicit       # explicit | implicit | quasi_steady (solved once per turn) | event
  stability: "dt <= 0.9 * dx^2 / (6 D_max)"   # code must implement exactly this bound; a test checks it
  formal_order: {space: 2, time: 1}
boundaries: [insulated]      # every type listed needs its own manufactured-solution case
lives_in: [air]              # cells where the field exists; solids are zero-flux walls
couplings:                   # every term: sign, unit, partner field; each one needs a coupling benchmark
  - {term: "-P_fire / H_O2", unit: kg/m3/s, partner: heat.source, sign: sink,
     constant: {H_O2: 13.1e6, unit: J/kg, ref: "Huggett 1980"}}
  - {term: "fire extinguished below X_O2 < X_lim", partner: world.sources, kind: threshold,
     constant: {X_lim: 0.15, unit: mole fraction, tunable: data/fields/oxygen.yaml}}
outcomes:                    # outcome classes the resolution rule protects, each with its threshold
  - {name: fire_starved, sensor: region.oxygen_min, threshold: X_lim}
  - {name: unbreathable, sensor: region.oxygen_mean, threshold: 0.16}
percept:                     # what it can feed on the SEM side
  sensor: oxygen_mean        # a reduction over cells (mean/max), never a single-cell probe
  maxim_type: SensorReading  # nothing beyond Maxim's frozen fields
snapshot:
  channel: o2
  encoding: uint8            # quantize (X_O2 / 0.21) * 255; 1 B/cell
  shown_by: "haze density + desaturation"   # never colour alone (client standard)
cost:
  bytes_per_cell: 8          # state; plus scratch for the flux arrays
  flops_per_cell_update: 20  # stencil estimate; the perf rung checks measured cell-updates against this model
  substeps_scale: "dx^-2"    # explicit diffusion
reference_facts:             # validation stand-ins: textbook numbers the field must reproduce in limit cases
  - {fact: "13.1 MJ per kg O2 consumed (most fuels, +-5%)", ref: "Huggett, Fire and Materials 4 (1980)"}
```

What the contract forces you to decide early, field by field, with numbers worked out for the 16 × 10 × 4 m first tile
(80 k / 640 k / 5.12 M cells at 0.2 / 0.1 / 0.05 m):

- **Time model.** For sound, an explicit 3-D wave equation needs c·dt/dx ≤ 1/√3. At 343 m/s and 0.05 m cells that
  gives dt ≤ 8.4×10⁻⁵ s, which is about 71,000 substeps per 6 s turn. So sound, light, electricity and radiation have
  to be **quasi-steady** (one solve or one propagation pass per turn: an energy-diffusion or geometric model for
  sound, rays or a steady solve for light, a Laplace solve with scipy.sparse for current, inverse-square plus
  attenuation for radiation). Gases, heat and liquids are transient. Structural load is quasi-static or topological
  (connectivity to support).
- **Transport realism.** Molecular diffusion of O2 in air is about 2×10⁻⁵ m²/s, so in 240 s it spreads
  √(2Dt) ≈ 0.1 m. A diffusion-only gas would starve every fire locally within seconds. That is the outcome class of
  the wrong model, and the coupling benchmark below makes it obvious. Gases need an effective (turbulent) diffusivity
  or convection. A cheap option that is rig-independent by construction is a per-room well-mixed zone model (in the
  style of NIST's CFAST), with cells used only for display. Decide this in the contract, not in review.
- **Memory.** A float64 field costs 0.64 / 5.1 / 41 MB per tile. Four gas species at max would be 164 MB. Halving it
  with float32 breaks the 1e-9 conservation check (float32 rounding is about 6e-8 per operation), so the dtype and the
  conservation tolerance are declared together.
- **Compute.** Explicit diffusion costs cells × substeps ∝ dx⁻⁵: 32× from laptop to rig, 1024× from laptop to max
  (`min_substeps_per_turn` already scales 4 / 16 / 64). Each field states its scaling, and the perf rung checks the
  measured cell-updates against it.
- **Snapshot.** Today it is 5 B/cell: material, crack and glow at 1 B each, temperature at float16. Each uint8 channel
  adds 0.08 / 0.64 / 5.1 MB per tile. The channel's quantization error must be smaller than the smallest
  outcome-relevant difference it has to show.

## 3. The ladder

Each rung has a pass criterion and states which standard it compares against. L0–L3 run on small standalone grids
built with `MaterialGrid.empty` at whatever dx the test wants, so they are fast and independent of the rigs. L4–L5 run
at the rig profiles.

| Rung | What | Standard compared against | Pass criterion |
|---|---|---|---|
| **L0 Contract** | YAML loads and validates. The code's stability bound matches the declared one. Every declared coupling, boundary and outcome has a test with the matching marker. | the contract | strict loader. `lint_standards.py` maps contract entries to marked tests and fails on any gap. |
| **L1 Exactness** | Solutions the scheme must reproduce to round-off: uniform state stays uniform; a steady linear profile across a two-material interface (exact for the harmonic-mean face conductance); zero source with an insulated boundary gives no change. | exact | error ≤ 1e-12 relative |
| **L2 Order of accuracy** | One closed-form case (Gaussian pulse, plane-wave decay, inverse-square) plus one manufactured solution per boundary type and per coupling term. Refine **space and time separately**: space at fixed tiny dt, time at fixed fine dx. 4 grids, r = 2. | analytic / manufactured | observed p within [formal − 0.2, formal + 0.3] on the two finest pairs. An observed order above the band fails too, because it signals cancellation or pre-asymptotic grids. |
| **L3 Conservation and invariants** | Insulated box, random materials and state, no sources: total conserved to tolerance. Budget closure with sources: Δtotal = ∫sources dt. Hypothesis over random scenes: bounds hold, values stay finite, nothing goes negative, monotone quantities stay monotone (integrity, B9). `derandomize=True` as `test_act_validation.py` already does. | exact (round-off) | 1e-9 relative for float64. Zero Hypothesis failures at a fixed `max_examples`. |
| **L4 Cross-tier outcome class** | 2–4 canonical scenarios per field at every rig, asserting the declared outcomes (as `test_cross_tier.py` does). Also: three-grid p, f_ext and GCI per decisive reading, written to the results file. | finest rig and f_ext (Richardson) | Same outcome at every rig. Outcome margin ≥ 2× cross-rig spread. Convergence not oscillatory or divergent, unless it is a declared known gap with an `xfail(strict=True)`. |
| **L5 Coupling** | One benchmark per declared coupling, each with a 0-D or limit-case reference (fire and O2 below). | lumped ODE, limit case | budget closure exact, plus bounds and limits as stated per benchmark |
| **L6 Performance and size** | Exact: substeps per turn, cell-updates, snapshot bytes per channel, state bytes. Timed: turn time and snapshot encode time, best-of-5 after one warm-up, reported as cell-updates/s. | committed baseline | Counts: equal to the baseline (any change must be committed deliberately). Bytes ≤ the declared budget. Time: no more than 20% slower than the same-machine baseline (B5). |
| **L7 Determinism and replay** | The field is in `digest()`. Two runs are bit-identical. Different `PYTHONHASHSEED` values agree. A mid-run snapshot and restore gives the same hash (heavy mode). | itself | bit-identical |

**What counts as the standard, in order of preference:**
1. **Analytic solution.** The only standard that proves correctness on its own. Per field: gas uses the same
   Gaussian as heat; liquid uses hydrostatic level, communicating vessels and Torricelli draining (t = (A/a)√(2h/g));
   sound uses inverse-square in the free field and Sabine's RT60 = 0.161 V/A for a diffuse room; light uses
   inverse-square and a hard shadow edge; electricity uses series and parallel resistor bars (Ohm's law, Joule heating
   I²R into heat for an L5 budget); radiation uses inverse-square times exp(−μx); structural load uses an unsupported
   block (falls / doesn't) and a cantilever's support reaction.
2. **Manufactured solution,** for every term no closed form reaches. Most bugs sit in variable coefficients, boundary
   faces and coupling signs.
3. **0-D lumped reference,** for couplings. It is exact in the well-mixed limit and is a strict bound otherwise.
4. **The field's own Richardson limit** across rigs. This is solution verification: it tells you how wrong the laptop
   rig is. It is never evidence of correctness.
5. **External solver** (FDS for fire, O2 and smoke; an acoustics or electrical solver offline). Run it once, commit
   the output as a fixture with its version and inputs, and compare at outcome-class level. Treat it as validation
   flavour, not a gate dependency.

### The canonical coupling benchmark: a fire in a sealed room

The cross-tier scene is 3 × 3 × 2 m = 18 m³. Subtract the crate (0.216 m³) and the wall (3.6 m³) and 14.18 m³ of air
is left, which is 17.1 kg of air and 3.96 kg of O2. A 60 kW fire consumes O2 at P/H_O2 = 60e3 / 13.1e6 = 4.58 g/s.
Taking extinction at X_O2 = 0.15 against 0.209 ambient, about 28% of the O2 must burn, so 1.11 kg. The well-mixed
reference is therefore t_ext ≈ 242 s ≈ 40 turns. These are illustrative numbers: compute the reference in the model's
own variables so it is exact for the model.

Pass criteria:
- **Budget closure (exact, every rig):** O2 lost = ∫P dt / H_O2, and Δheat = ∫P dt, both to 1e-9 relative. This
  couples the two fields' L3 checks.
- **Bound:** t_ext ≤ t_wellmixed + 1 turn. Local depletion can only bring extinction earlier.
- **Limit:** with D_eff set very large (or in a well-mixed mode), t_ext equals the ODE answer within one turn.
- **Cross-tier:** the fire is extinguished at every rig, at onset turns within 10% of each other.
- **Physical-plausibility guard:** t_ext must exceed some declared floor, for example 50% of well-mixed. This is the
  check that catches the diffusion-only starvation described above.
- **The fire goes out:** once extinguished, peak temperature never rises again. This retires
  `test_a_fire_that_has_burned_its_fuel_stops_heating` together with its fuel half.

## 4. How it fits this repo

**Layout**
```
data/fields/<name>.yaml            the contract (heat.yaml and damage.yaml first, admitted retroactively)
src/maxim_overdrive/verify/        harness: observed_order(), richardson(), gci() (Celik's 3-grid form,
                                   flags oscillatory), budget(), outcome_margin(), count_cell_updates()
                                   (in src/, so it is typed and inside the 100% coverage floor)
src/maxim_overdrive/fields/<name>.py   physics, one module per field
tests/fields/<name>/test_l1_exact.py ... test_l5_coupling.py    the gate; normal pytest
benchmarks/perf_<name>.py          L6 timed runs, not collected by default pytest (testpaths stays ["tests"])
benchmarks/results/<name>.json     committed: per rig, the error norms, p, f_ext, GCI, conservation residual,
                                   margins, exact counts, bytes; timings keyed by machine fingerprint
scripts/bench.py                   runs L4 and L6, writes or compares results, --update to rebaseline
```

**Markers and tiers.** Add `field(name)` and `rung(L0..L7)` markers (registered, `--strict-markers`). The fast suite
runs L0–L3 and L5 on small grids plus L4 and L7 at laptop and rig. That costs seconds per field, because the
convergence grids are small boxes, not tiles. `MAXIM_OVERDRIVE_ALL_TIERS=1` adds max to L4. Pre-push already runs all
tiers, then calls `scripts/bench.py --check`. Anything over a few seconds gets `slow`, as today.

**Results and comparison.** `benchmarks/results/<name>.json` works like a golden fixture. The check fails if any
exact count differs from the committed value, if a numeric error norm gets worse by more than 1% (the code is
deterministic on one machine, so a drift means the maths changed), or if timing regresses by more than 20% on a
machine that has a baseline. A machine with no baseline prints `perf: no baseline for <fingerprint>, not gated`
instead of passing quietly. Rebaselining is a separate commit, and its diff is reviewed. Commit the fingerprint as the
CPU model and OS only, never the hostname.

**Candidate lifecycle.**
1. Open a branch `phase2/field-<name>` with `status: candidate`. The field is enabled only through a required
   keyword, `World(..., fields=frozenset({...}))`, so it can never be on by accident. The set of enabled fields goes
   into the scene, save and wire headers, so formats stay versioned and a reader refuses a field it doesn't know.
2. A candidate needs only L0, L1, L3 and L7 to merge, so exploration can land behind the toggle. Its results file
   records whichever rungs it has reached.
3. The lint fails if a shipped scene or the default `World` enables a candidate, or if a candidate is older than its
   `owner_phase` (the toggle has to be removed or admitted, as with `TEMPORARY`).
4. **Admission** is a PR that flips the status to `admitted`, with every rung green, the outcome margins recorded,
   and known gaps added to `architecture.md` with numbers. A field that fails is set to `retired` and deleted, and a
   one-line note in the results history says why.

Exploration (parameter sweeps, plots) lives in `benchmarks/explore/` on the experiment branch and is not merged. What
gets merged is the results file.

## 5. Opinion: rigour versus speed

- **Worth the cost now.** L1–L3 and L7 are cheap, catch most bugs, and compound. L2 with separated refinement is a
  few dozen lines per field and would already have caught the heat finding above. Budget closure across couplings
  matters most once fields interact, because sign errors in coupling terms are the classic bug and only an exact
  budget catches them. Exact performance counters cost nothing and never flake.
- **Build first, in order:**
  1. `verify/` plus heat retrofitted to it, with the order test refining space and time separately, and GCI computed
     for the late-burn reading, which honestly reports "oscillatory, known gap". About a day.
  2. `heat.yaml` as the first contract. If the contract can't describe heat cleanly, fix the contract before oxygen.
  3. Exact counters and snapshot bytes in a results file. This is B5's deterministic half.
  4. The generic Hypothesis invariant (B9).
  5. Oxygen as the first new field, with the sealed-room benchmark. It closes the Phase 1 fuel gap at the same time.
     Make the convection or zone-model decision before writing the solver.
- **Over-engineering now:**
  - ASME V&V 20 validation uncertainty: there is no experimental data, and game physics doesn't need it.
  - Gating on GCI values: record them, and gate only on oscillation and margins.
  - FDS in the loop.
  - Instruction-count tooling: Valgrind is painful on macOS, and the exact counters cover the same need.
  - A benchmark dashboard such as asv.
  - Mutation testing beyond B10's periodic run.
  - A generic field plugin or registry before two concrete fields exist. Write oxygen concretely and extract the
    abstraction at field two or three; the contract YAML is the abstraction for now.
  - Running max in every L2 test: code verification belongs on small grids.
- **The main risk** is turning the ladder into a checklist nobody reads. Keep each rung's output to one line in the
  results file, and make "decisive margin" the number reviewers actually look at, because it is the one that protects
  the resolution rule.

## Sources

- Oberkampf and Roy, *Verification and Validation in Scientific Computing*, Cambridge UP 2010 (2nd ed. 2025 as
  *Verification, Validation, and Uncertainty Quantification in Scientific Computing*):
  https://assets.cambridge.org/97805211/13601/frontmatter/9780521113601_frontmatter.htm
- Salari and Knupp, *Code Verification by the Method of Manufactured Solutions*, SAND2000-1444:
  https://www.osti.gov/biblio/759450
- Roy et al., verification of Euler/Navier–Stokes codes using MMS (history of MMS, Roache and Steinberg):
  https://www.aoe.vt.edu/content/dam/aoe_vt_edu/people/faculty/cjroy/Publications-Articles/IJNMF.final.2004.pdf
- Celik, Ghia, Roache and Freitas, "Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD
  Applications", J. Fluids Eng. 130(7) 078001, 2008: https://qa12.asme.org/wwwasmeorg/media/ResourceFiles/Shop/Journals/JFENumAccuracy.pdf
- NASA NPARC, spatial convergence and GCI tutorial: https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html
- NASA slides on the ASME V&V 20 five-step GCI procedure: https://ntrs.nasa.gov/api/citations/20140011325/downloads/20140011325.pdf
- ASME V&V 20-2009 overview (Sandia): https://sandia.gov/research/publications/details/overview-of-asme-vv-20-2009-standard-for-verification-and-validation-in-com-2010-03-01
- Eça, Dowding and Roache on the interpretation of V&V 20: https://www.marin.nl/en/publications/on-the-interpretation-and-scope-of-the-vv-20-standard-for-verification-and-validation-in-computational-fluid-dynamics-and-heat-transfer
- NIST FDS Verification and Validation Guides (SP 1018-2 and SP 1018-3; the Firebot CI framework). A search returned
  this NIST PDF, https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1017-3.pdf, but SP 1017 is the
  Smokeview series, so go to the SP 1018 volumes on nist.gov. CFAST V&V technical note (it describes reusing FDS's
  automated V&V process): https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.1889v3.pdf
- Lid-driven cavity benchmark (Ghia, Ghia and Shin 1982): https://cfd-online.com/Wiki/Lid-Driven_Cavity_Problem
- Erez, Tassa and Todorov, "Simulation tools for model-based robotics", ICRA 2015: https://homes.cs.washington.edu/~todorov/papers/ErezICRA15.pdf
- Python `timeit` docs (use the min of repeats): https://docs.python.org/3/_sources/library/timeit.rst.txt
- pytest-benchmark usage (compare, compare-fail, rounds, warm-up): https://pytest-benchmark.readthedocs.io/en/latest/usage.html
- CodSpeed, benchmarks in CI without noise: https://codspeed.io/blog/benchmarks-in-ci-without-noise ; instruction count vs
  wall time measurements: https://tak.jdx.dev/guide/methodology
- Factorio Friday Facts #47 (CRC replay) and #315 (heavy mode): https://cf-www.factorio.com/blog/post/fff-47 ,
  https://cf-www.factorio.com/blog/post/fff-315
- Pete Hodgson, Feature Toggles: https://martinfowler.com/articles/feature-toggles.html
- Hypothesis settings (derandomize, profiles): https://hypothesis.readthedocs.io/en/latest/settings.html
- Huggett's oxygen-consumption constant (13.1 MJ/kg O2): C. Huggett, *Fire and Materials* 4(2), 1980. Cited from
  memory and not fetched this session; verify it before committing the number to `data/`.
