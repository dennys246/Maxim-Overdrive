# Physics spike: pre-registration (2026-11-19, committed before any spike code runs)

This spike exists because the owner chose, on 2026-11-19, to research step 6's physics before steps 3b to 5b lock in
assumptions about it. It is throwaway numerical prototyping: code in `spikes/physics/`, never promoted into `simcore`.
Step 6 still builds the real laws, with tests, review and step 4's convergence harness. This spike produces numbers
and design decisions only.

T13 froze paper rounds on the fire physics, and this spike measures instead. The criteria below are fixed now. A
result that misses one is reported as a miss, with its numbers. **No constant is tuned to make a criterion pass, no
criterion is loosened after the run, and no criterion is reinterpreted after it.**

## Rules for every question

- **Constants come from cited sources only.** Each constant gets a provenance row: value, units, source (author,
  year, title or URL) and whether it was verified against the source or taken from memory.
- **No fitting.** A constant tuned until the outcome looks right is forbidden. Where the literature gives a range, the
  run covers the ends of the range and reports both.
- **The geometry is the tile spec's crate** (`docs/design/tile_and_client.md` §1, §5, D30, T15): a 0.6 m cube, a porous
  fuel bed of 20 mm slats at fuel volume fraction φ = 0.25, so surface area per volume σ = 25 m²/m³, in open air at
  20 °C.
- **Grids.** Cell sizes 0.2, 0.1 and 0.05 m, with the 0.05 m run as the reference.
- **Each script is deterministic:** two runs with the same inputs give bit-identical outputs, and the script asserts it.
- **Each question's result** goes in its own file in this directory, giving each criterion's pass or miss with its
  numbers, plus what the run doesn't show.

## Q1: does the porous bed sustain a fire, and do its embers glow? (de-risks step 6 and its glow exit)

The model must include:
- radiation exchange between slats inside the bed, and the draught's air-supply loss (FPH-B1);
- a char-surface product (CO or CO₂) chosen from a cited source, never chosen to make glow pass (FPH-B2).

| Criterion | Pass when |
|---|---|
| 1a. The fire sustains | After the pilot (`kindle`'s energy and duration from `tile_and_client.md`) ends, flaming continues until the bed's volatile fuel is consumed. It doesn't go out early |
| 1b. The embers glow | At least 0.08 m² of the bed's envelope has a surface temperature ≥ 625 °C for at least 60 s of continuous simulated time |
| 1c. Burnout | Remaining fuel (wood plus char) falls below 5% of its initial mass within the tile spec's cap of 5,400 s |

**Report** `t_ignite`, `t_glow` and `t_gone`, the peak and mean ember temperature, and the result under each end of
every constant's literature range.

## Q2: does it converge across grids? (de-risks step 4's harness and step 6's convergence tests)

Ignition and flame spread are evaluated on a reconstructed sub-cell surface, never on a cell mean (FPH-B3).

| Criterion | Pass when |
|---|---|
| 2a. Times converge | For `t_crack`, `t_glow` and `t_gone` (tile spec §6.3 items 3, 4 and 8), with absolute error e against the 0.05 m reference and tol = 15% (`t_crack`, `t_glow`) or 10% (`t_gone`): \|e₀.₁\| ≤ tol, and (\|e₀.₂\| ≥ \|e₀.₁\| or \|e₀.₁\| ≤ tol/4) |
| 2b. Observed order | The observed order of convergence p, from the three grids, is greater than 0.5 for each time, and a Richardson estimate of the 0.1 m error is reported beside the measured one |

## Q3: do several laws stepped together stay stable and deterministic? (de-risks step 5a's core)

The prototype is an ordered list of laws: conduction, the surface skin, the porous-bed fuel law and open-air loss.
Each law has `stable_dt(state)` and `step(state, dt, ledger)`. The tick is 0.1 s, with physics every 0.5 s (T3), and
substeps come from the stability bound.

| Criterion | Pass when |
|---|---|
| 3a. Stable | No NaN, no infinity and no temperature outside physical bounds over the full Q1 scenario, at all three grids |
| 3b. Deterministic | Two runs are bit-identical, and a run with numpy's thread count changed is bit-identical too |
| 3c. Splitting error | Against a reference with a tenth of the substep, `t_glow` and `t_gone` differ by ≤ 5% |
| 3d. Order sensitivity | The splitting order is reversed and the change in each time reported. Pass when ≤ 5%, otherwise the step 5a note must fix an order and say why |

## Q4: does the energy ledger close? (de-risks the ledger interface in steps 5a and 6)

| Criterion | Pass when |
|---|---|
| 4a. Closure | At every physics step, \|energy in − Δstored − energy out\| ≤ 1% of the cumulative energy released, using the ledger lines in `tile_and_client.md` §5.1 (sources, plume convective, flame radiative, open-air loss, removed with mass, bodies, Δskins) |
| 4b. Meaningful | The closure test goes red when any single ledger line is deleted |

## Q5: what does a body near the fire feel? (de-risks D28, the heat-debt prototype)

The body is the T5 body model with flame radiation from a point source (T14), plus radiation from hot surfaces by
view factor, at 1, 2 and 3 m from the crate.

| Criterion | Pass when |
|---|---|
| 5a. Reported | Time from the fire's peak to the skin reaching a pain threshold (≈ 44 °C, from a cited source) at each distance, and the rate the core warms |
| 5b. A playable window exists | At 1–2 m, time to the pain threshold lies between 10 s and 120 s, so standing near the fire is a trade-off, neither instant nor irrelevant. This window is `[engineering]`: a game-feel judgement, not physics. A miss isn't a physics failure; it goes to D28's design note |

## What happens with the results

`physics_spike.md` in this directory summarises them. Then:
- **Any miss on 1a, 1b, 1c or 2a goes to the owner before step 6 is designed,** per the pre-registered failure path
  (T13).
- **The step 5a and step 6 design notes start from these numbers.**
- **The spike's code stays in `spikes/physics/`** as a record and is never imported by `src/`.
