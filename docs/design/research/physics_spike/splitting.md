# Q3: several laws stepped together (physics spike, 2026-11-19)

Answers Q3 of `preregistration.md`. Code: `spikes/physics/splitting/`. Results: `spikes/physics/splitting/results/*.json`, scored by `analyze.py` into `results/summary.md`.

## Result

| Criterion | Result | Numbers |
|---|---|---|
| 3a stable | **PASS** | All 62 runs (2 scenarios × 3 grids × Lie/Strang × forward/reverse × 1×/10× substeps, plus the 3b reruns) stay finite and inside [T_amb − 0.5 K, 2,300 K], with no negative mass. Peak skin is 947 °C. The worst mid-step dt/bound ratio is 0.90, which is the safety factor |
| 3b deterministic | **PASS** | A hash of every state array after every physics step is identical across a run, its rerun, thread count 8 and thread count unset, at every grid in both scenarios (6 groups × 4 runs) |
| 3c splitting error ≤ 5% | **PASS on the established fire; MISS (unevaluable) on the pilot scenario** | Established fire, Lie: \|e\| ≤ 0.35% (t_glow) and ≤ 0.03% (t_gone) at every grid. Pilot scenario: t_gone never occurs, and t_glow occurs only at 0.2 m (+0.44%) |
| 3d order ≤ 5% | **MISS** | Established fire: ≤ 3.5% (t_glow, 0.2 m) and ≤ 0.1% (t_gone). **Pilot scenario at 0.2 m: reversing the order flips the outcome class.** 84 MJ released and 27.6 kg left becomes 464 MJ and 3.1 kg (Lie), or 506 MJ and 1.9 kg (Strang). With 10× substeps the reversed order returns to 84 MJ and 27.6 kg, so this is a splitting artifact. The 5a note must fix an order (§6) |

**The headline isn't the splitting error. It is that, in this prototype, the law order decided whether a
near-critical fire spreads.** The mechanism is general (§6): an O(dt) overshoot past a projection's invariant, which
diffusion then carries across an ignition threshold. On a developed fire, splitting error is two orders of magnitude
inside tolerance, and Strang buys nothing measurable over Lie.

**A finding for Q1, stated here because it shaped Q3:** with tile §5.1's constants and a tile-faithful structure,
this prototype's 2 kW, 120 s pilot never grows into a bed fire at any grid. At 0.2 m 4.8 kg burns, at 0.1 m 1.6 kg,
and at 0.05 m nothing (§2.3). For that reason 3c and 3d were also scored on an **"established" scenario**: tile §5.3's
design point, the whole bed lit at t = 0, with every constant unchanged. Q1's own, fuller model decides 1a. This
prototype doesn't refute it, but it shows that sustaining from a small pilot isn't automatic.

## 1. Choices and deviations, disclosed

- **The pilot's duration D isn't fixed by the tile** (§3.2 leaves it to step 6's band). It was set before any run to
  **1,200 ticks (120 s)**, twice the tile's 60 s closed-form ignition time.
- **The established scenario was added after the first runs**, because the pilot scenario has no t_gone. It is
  labelled everywhere, and the pilot results stand as misses.
- **3a's bounds were fixed in code before scoring:** T ≥ T_amb − 0.5 K (nothing in the model is colder than ambient)
  and T ≤ 2,300 K (above any wood-flame adiabatic temperature). Mass ≥ 0.
- **3c's reference** is the same scheme and order with n_ref = 10 n, re-chosen by the same rule every physics step.
- **Three structural versions ran before scoring. No constant changed between them.**
  1. The pilot spread over ℓ couldn't ignite anything: 240 kJ against about 2 MJ to heat the region.
  2. Flame heat routed through the cell-mean bulk had to heat the slat cores before anything could spread.
  3. P1 flame radiation absorbed in emptied cells ran away to 6,600 °C. The 3a bound caught it: a model bug, fixed by
     letting only fuel absorb.

## 2. The prototype

**Domain and grids.** A 1.0 m cube with an insulated boundary, as in `heat.py`: a 0.2 m concrete floor, the 0.6 m
crate bed at x, y 0.2–0.8 and z 0.2–0.8, and air elsewhere. Cells are 0.2, 0.1 and 0.05 m: 125, 1,000 and 8,000
cells, of which 27, 216 and 1,728 are bed. The envelope (top plus four sides) is 1.8 m².

**State.** Every cell has a bulk temperature T; in a bed cell that is the slat cores plus the pore air. Each bed cell
also carries a skin temperature Ts (1 mm over the cell's fuel surface σV, tile 6b), its wood and char masses, and a
`lit` latch.

### 2.1 The four laws (`laws.py`), in forward order

1. **Conduction**
   - The bulk field uses `heat.py`'s explicit finite-volume scheme with harmonic-mean faces.
   - In-bed re-radiation between neighbouring skins (FPH-B1) uses the Rosseland conductivity 16σT³/(3β), with
     β = σ_v/4 (tile 6a).
   - It is nonlinear, so its bound tightens as the bed heats. It sets n in 94–99.5% of established-fire steps.
2. **Skin**
   - Skin–core exchange goes through a quarter-slat conduction resistance, k_wood/(δ/4) = 30 W/m²K: a two-node slat.
   - The pilot deposits on the skins behind its disc by face-area overlap (tile §3.2).
3. **Porous bed**: the flux-threshold sources.
   - *Ignition* follows tile 6b's "area overlap with a critical heat flux". Cells at least half under the disc light
     once the 15.9 kW/m² pilot (≥ CHF 12 kW/m²) has run the thermally thick closed-form time
     (π/4)kρc(T_p − T_a)²/q''² = 61.5 s. A cell whose fuel receives a flame flux ≥ CHF, or whose skin reaches T_p,
     lights too.
   - *Flame feedback* follows tile §5.4's identity, q''_f × A_burning × dt. It is spread over the bed by a P1
     (screened-Poisson) solve with extinction β, so over ℓ, in metres, factorised once with SuperLU.
   - *Pyrolysis is a projection.* A skin above T_p with wood behind it is reset to T_p, and the excess energy gasifies
     volatiles at L_g (tile 6c). Release minus feedback is the plume.
   - *Char oxidation* runs at tile 6d's 0.86 g/m²s into the skin, once the cell's wood is gone and its skin is ≥ T_p.
4. **Open-air loss** (tile 6a). The envelope loss h_c(Ts − T_a) + εσ(Ts⁴ − T_a⁴) is spread over the skins within
   ℓ = 0.16 m of an exposed face, by volume overlap.

Each law has `stable_dt(state)` and `step(state, dt, ledger)`. Static geometry comes from `model.prepare`, the
architecture review's row 5 seam. Kernels are array-only.

The ledger uses tile §5.4's lines and closes to ≤ 4 × 10⁻¹⁰ of the cumulative release on established runs and
≤ 2 × 10⁻⁶ on pilot runs. That is a diagnostic only; Q4 owns closure.

### 2.2 Observables, mapped to tile §6.3

- **t_glow** (item 4): the first physics tick at which ≥ 0.08 m² of envelope face has an envelope-layer skin
  ≥ 625 °C.
  - A face's envelope-layer skin is the radiometric mean (Σ w Ts⁴ / Σ w)^¼ over the bed cells in the ℓ-deep column
    behind it, where w is each cell's depth overlap with [0, ℓ].
  - That is what the outside sees, and it is defined in metres, so it doesn't depend on the grid.
- **t_gone** (items 5 and §5.5): the first tick with wood plus char ≤ 5% of 32.4 kg.
- **t_ignite** (item 2's 0.1 m²): reported only.
- All times are resolved to the 0.5 s physics step.

### 2.3 Behaviour

- **Established fire.** t_glow is 431–450 s, t_gone 1,782–1,882 s and peak skin 917–947 °C across the grids. Total
  release is 567 MJ. This matches tile §5.3's derived ember balance (about 920 °C) and its 567 MJ, and its t_gone
  (about 2,200 s) to the same order.
- **Pilot scenario: subcritical.**
  - 0.2 m: three cells light at 68 s and one at about 1,500 s, and embers glow from 1,931 s.
  - 0.1 m: 13 cells light and release 26 MJ.
  - 0.05 m: no pyrolysis at all; peak skin 330 °C.
  - The lit region's feedback, spread over ℓ, can't hold its neighbours at CHF against cold cores and envelope loss.
    That which cells ignite depends on dx is the D25 hazard: thresholds decided per cell (half a face, a whole cell's
    skin).

## 3. The scheduler (`scheduler.py`)

```
physics_step(laws, state):            # every 5 ticks = 0.5 s (T3); laws is a fixed tuple
    tick += 5; pilot power from the integer tick overlap (tile §3.2)
    n = refine * max(1, ceil(0.5 / min(law.stable_dt(state) for law in laws))); dt = 0.5 / n
    repeat n times:
        Lie:    for law in laws: law.step(state, dt, ledger)
        Strang: laws[:-1] at dt/2, laws[-1] at dt, laws[:-1] reversed at dt/2
```

- **n is fixed at the start of each physics step**, so dt = 0.5/n exactly and time is counted in integer ticks.
  `heat.py` instead accumulates `elapsed += dt` in floats and trims the last substep.
- **Audit.** Before every later substep the bound is recomputed on the current state. The worst dt/bound ratio was
  0.90, and the bound was never exceeded, so a mid-step re-check can stay a debug assertion.
- **n reaches 5 at 0.05 m, 2 at 0.1 m and 1 at 0.2 m.** The bed law's bound is ∞: the projection is unconditionally
  stable, and its sources don't depend on temperature.
- **Cost.** 22 ms per physics step at 0.05 m (Lie with the audit). Strang costs 1.5–3× that.

## 4. The criteria

**3a, PASS.** All 62 runs stay in bounds. The pre-scoring runaway (§1) shows the check can fail.

**3b, PASS.** Each grid and scenario ran in four child processes, each with an explicit environment
(`experiments.py::env_for`): threads 1, a rerun at 1, 8, and unset. The thread variables set were
`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS` and `MKL_NUM_THREADS`, with `PYTHONHASHSEED=0`.
A blake2b hash covers T, Ts, wood, char and `lit` after every one of 10,800 physics steps, and all four runs in each
group match. `analyze.py` asserts it.

**3c.** Each base run against its 10× reference, same scheme and order:

| Grid | Lie t_glow | Lie t_gone | Strang t_glow | Strang t_gone |
|---|---|---|---|---|
| 0.2 m | 431.0 vs 429.5 s (+0.35%) | 1,882.0 vs 1,882.5 (−0.03%) | +0.81% | 0.00% |
| 0.1 m | 450.0 vs 450.0 (0.00%) | 1,827.5 vs 1,827.5 (0.00%) | +0.22% | +0.03% |
| 0.05 m | 449.5 vs 448.5 (+0.22%) | 1,782.0 vs 1,782.0 (0.00%) | 0.00% | +0.03% |

- **Established fire: PASS.** The errors are 0–3 physics steps.
- **Pilot scenario: MISS, unevaluable.** t_gone never occurs. t_glow occurs only at 0.2 m, where the error is +0.44%
  (Lie) and −0.21% (Strang). t_ignite at 0.1 m moves 3.6% (625.5 s against 649.0 s): a latch firing on a threshold
  crossing.

**3d.** The reversed order is open-air, bed, skin, conduction.

| Scenario, grid | Lie | Strang |
|---|---|---|
| Established, 0.2 m | t_glow +3.48%, t_gone −0.05% | +0.58%, −0.03% |
| Established, 0.1 m | +0.11%, −0.08% | −0.22%, −0.08% |
| Established, 0.05 m | 0.00%, −0.06% | +0.22%, −0.06% |
| Pilot, 0.2 m | **flip**: 84 → 464 MJ, 27.6 → 3.1 kg left, peak skin 687 → 936 °C | **flip**: 84 → 506 MJ, 27.6 → 1.9 kg |
| Pilot, 0.1 and 0.05 m | no change (≤ 0.4% in release) | same |

**Reversed order at 10× substeps** (run to test whether the flip is an artifact):
- Pilot, 0.2 m: 84 MJ and 27.60 kg left under both Lie and Strang, identical to forward.
- Established, 0.2 m: Lie t_glow is 431.0 s. The reversed base (446.0 s) is therefore 3.48% off its own reference,
  ten times the forward order's 0.35%.

## 5. Lie against Strang

On the established fire, Strang's error is no smaller than Lie's: +0.81% against +0.35% at 0.2 m. The two 10×
references agree within 0.12%. Strang also costs 1.5–3× the time, and it flips the pilot outcome under reversal just
as Lie does. This is the expected order reduction. Strang's second order assumes smooth operators, and here there is
a projection, latches and threshold gates. Sportisse (2000) shows that the classical splitting-error analysis fails
when the step is much longer than the fastest time scale. Verwer and Sportisse (1998) report Strang reducing from
second to first order in a stiff case.

**Recommendation: Lie with a fixed order.** Revisit only if step 4's harness shows a splitting term above its
tolerance.

## 6. The recommended order and substep rule for step 5a

**The mechanism, measured at 0.2 m in the pilot scenario.** The projection keeps an invariant: **Ts ≤ T_p wherever
wood remains**.
- **Forward order** (conduction, skin, bed, open-air). Every law that adds heat to a skin runs before the
  projection. The invariant held at the end of every physics step: 0 violations in 4,000 steps.
- **Reversed order.** The skin law and conduction run after the projection. In 803 of 4,000 steps a skin ended above
  T_p over wood, by up to 4.1 K. Conduction then diffused the overshoot into neighbours. Cells lit at 1,480, 2,657,
  2,765, 3,311 s and later, each starting its step 0–2.5 K above T_p, and so passing the "skin ≥ T_p" ignition test.
- **Why forward doesn't spread.** A neighbour of a skin clamped at T_p approaches T_p only asymptotically. Only one
  late cell lit.

**Rules:**

1. **Order: transport, then exchange, then sources and projections, then losses.** For step 6 that is
   `conduction → skin → bed → open_air`.
   - A law that enforces an invariant (a projection, a clamp, a phase-change cap) runs after every law that can break
     it. Laws that only remove heat, like 6a, may follow it.
   - The order is the static, reviewed tuple (architecture review row 1). Each law's PR states the invariants it
     reads and the ones it can break.
   - This only partly matches Sportisse's "stiff operator last": the projection sits third, followed only by a
     heat-removing law.
2. **Never decide a binary outcome at a threshold that diffusion can only approach asymptotically.**
   - "Skin ≥ T_p" next to skins clamped at T_p fires or not depending on numerical overshoot.
   - Step 6's ignition should be the tile's flux criterion with an outcome margin and a band (CLAUDE.md: binary
     outcomes keep a band).
   - **This is the real fix.** Fixing the order alone removes this instance but hides the sensitivity.
3. **Substep rule.**
   - n = max(1, ⌈0.5 s / min_law stable_dt⌉), fixed at the start of each physics step; dt = 0.5/n exactly; integer
     ticks; safety 0.9; a mid-step bound check as a debug assertion only.
   - `stable_dt` returns ∞ only for an unconditionally stable update, and its docstring says so.
4. **Step 4's harness gets a splitting test per scenario.**
   - At fixed dx, run n and 10n, and require the observables within tolerance and an unchanged outcome class.
   - Run the reversed tuple too, and require the same outcome class.
   - This test catches today's 0.2 m flip.

## 7. Determinism hazards

**Nothing in the prototype broke bit-identity.** `determinism_probe.py` (results in `results/determinism_probe.json`)
ran a set of operations in child processes at threads 1, 2, 8 and unset. On this machine **none was sensitive to the
thread count**: `@` (matmul and matvec), `np.dot`, `einsum(optimize=True)`, `linalg.solve`, `np.sum`, `cumsum`,
`exp`, `np.power`, weighted `bincount`, scipy `splu`, `spsolve` and `cg`. The hazards that remain:

1. **The BLAS here is Apple Accelerate, and the test can't prove the thread setting took effect.** A 3,000² matmul
   took 2.56 s at 1 thread and 2.15 s at 8, on a loaded machine.
   - Linux CI's OpenBLAS splits reductions (`dot`, `gemv`, `gemm`) across threads, a known source of thread-dependent
     rounding. It is untested here, since no installs were allowed.
   - *Avoid:* keep BLAS out of the kernels; the prototype uses only elementwise ops, slicing, `bincount`, pairwise
     `np.sum` and one SuperLU solve. Pin the thread variables to 1 in the server's environment, and run the
     determinism test in CI at 1 and N threads.
2. **Same maths, different association, different bits.** Measured on 10⁷ values: `np.dot(v, v) != np.sum(v*v)`.
    - Rewriting a kernel algebraically (`x**4` against `(x*x)*(x*x)`) breaks golden replays.
   - *Avoid:* make each kernel's expression part of the replay contract, guarded by the per-kernel parity test the
     review proposes (row 5). The prototype writes T⁴ as two multiplies and avoids `np.power`, whose fast paths vary
     between numpy versions.
3. **Sparse solvers.** SuperLU was deterministic here, but may call the linked BLAS, so hazard 1 applies to it on
   OpenBLAS. *Avoid:* factor once per topology version, and include the solver in the CI threads test.
4. **Float time accumulation** (`heat.py::step`). It is deterministic, but its substep count depends on rounding.
   *Avoid:* integer ticks and n fixed per physics step.
5. **The digest must include the latches.** `lit` decides outcomes, and a hash without it would detect the 3d
   divergence late. This supports the field-registry item (review row 2).

## 8. What this run doesn't show

- **This is not Q1's model.**
  - The constants are tile §5.1's, all *from memory*.
  - Several pieces are this prototype's own structural choices: the k/(δ/4) skin–core resistance, the P1 spread of
    q''_f, Rosseland re-radiation between skins, the ≥ T_p gate on char, "half a face under the disc", and D = 120 s.
  - None was tuned to a target, but they settled over three iterations after looking at behaviour (§1).
- **3c and 3d pass only on the tile §5.3 design point, not on the exit scenario.**
- **No Arrhenius source.** The bed's stiffness sits in a projection, so its bound is ∞. A kinetic law would add a
  finite, source-limited bound, and that case is unmeasured.
- **One machine and one stack** (Accelerate, Python 3.14).

## References

- B. Sportisse, "An analysis of operator splitting techniques in the stiff case", J. Comput. Phys. 161 (2000).
  https://data-ww3.ifremer.fr/BIB/Sportisse_JCP2000.pdf. Abstract read; volume and title from memory.
- J. G. Verwer, B. Sportisse, CWI report on operator splitting in a stiff linear case (1998).
  https://ir.cwi.nl/pub/4597/04597D.pdf. Abstract read.
- Rosseland approximation (Modest, *Radiative Heat Transfer*) and the thermally thick ignition time: from memory.
- Physical constants: `tile_and_client.md` §5.1 and `data/materials/core.yaml`, with provenance rows in
  `model.py::CONSTANTS`.
