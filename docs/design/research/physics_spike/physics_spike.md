# Physics spike: summary (2026-11-20)

The criteria were pre-registered in `preregistration.md` (commit 3bd5ced) before any spike code ran. Detail is in
three result files: `bed.md` (Q1, Q2, Q4), `splitting.md` (Q3) and `body.md` (Q5). Code and run summaries are in
`spikes/physics/`. The per-run arrays (`*.npz`, 5.7 MB) aren't committed, and the scripts regenerate them.

All runs were on one machine at a load average of 61–152, shared with other sessions. Timings are CPU-dominated and
recorded per run; outcomes don't depend on the load.

## The headline: the pre-registered fire doesn't happen

The tile spec's pilot, a 2 kW torch for up to 1,800 s, never lights the crate.

- **What the model shows.** The torch lights only the 0.031 m² of slat faces it heats, after 415 s, not the ~60 s
  the spec assumed: the spec ignored surface heat loss. Those faces burn out by about 1,040 s, with 99.4% of the wood
  unburnt. This holds at all three grids and at every literature range end.
- **The cause is structural, not a constant.** Step 6's porous-bed law (6c) pins burning surfaces at the pyrolysis
  temperature and has no path for flame heat to reach unburnt fuel. Only the radiative fraction χ_r·q''_f leaks into
  the bed, which is too little. **A fire can't spread through the bed under 6c as written.**
- **The law-splitting spike's simplified model saw the same thing independently** (`splitting.md` §1).

**This is the T13 failure path.** No constant was tuned, and the decision goes to the owner before step 6 is designed.

## Results by question

| Q | Criterion | Pre-registered result | Notes |
|---|---|---|---|
| 1 | 1a sustain | **MISS** | The pilot never lights the bed. In the labelled conditional scenario F (whole bed lit at t = 0, tile §5.3's premise), 1a **passes** |
| 1 | 1b glow | **MISS** | Also a miss in F with cited char-oxidation kinetics: char is born at T_p = 380 °C, below its 590–676 °C self-heating threshold, so it never glows |
| 1 | 1c burnout | **MISS** | In F, 25.4% of the fuel (8.2 kg of char) remains at 5,400 s |
| 2 | 2a convergence | **MISS** | The pilot scenario's times don't exist. Where a time exists on every grid, it passes the tolerance |
| 2 | 2b observed order | **MISS everywhere** | Differences change sign or p < 0.5. Flaming duration diverges with refinement (449 → 575 → 770 s), because the envelope's ~0.10 m radiative boundary layer is unresolved at 0.2 m and 0.1 m |
| 3 | 3a stable | **PASS** | All 62 runs finite and in bounds |
| 3 | 3b deterministic | **PASS** | Bit-identical across reruns and thread counts, on this machine |
| 3 | 3c splitting error | **MISS (unmeasurable)** on the pre-registered scenario; passes (≤ 0.35%) on an added fully-lit scenario | The added scenario is a post-registration deviation, labelled as such |
| 3 | 3d order sensitivity | **MISS** | In the pilot scenario, reversing the law order flips the outcome, from 84 MJ released to 464 MJ. With 10× substeps it returns to 84 MJ: a splitting artifact at a threshold |
| 4 | 4a ledger closes | **PASS** | Residual ≤ 1.9 × 10⁻¹⁴ of release. The check caught one real leak (fixed). It missed a 1,000× units bug, booked consistently on both sides, which a closed form found |
| 4 | 4b every line matters | **Partial MISS** | Every line except `bodies` (zero here) goes red when deleted in some scenario, but lines under 1% of release can't trip a 1% tolerance |
| 5 | 5a reported | **Reported** | At 1, 2 and 3 m, clothed and bare, three flux models (`body.md`) |
| 5 | 5b playable window | **MISS** (game feel, `[engineering]`) | At 1 m, bare skin hits pain in 1–5 s. The window exists at about 2–3 m bare and 1–2 m clothed |

## What the misses teach

1. **Fire spread needs its own law.** Burning faces must heat their unburnt neighbours through flame convection and
   radiation to adjacent fuel, which is how real fires climb a crib. Neither 6c nor the spec's §5 has a cited spread
   mechanism, and FPH-B3 flagged it. **This is the root cause of Q1.**
2. **Glow is decided by the char-oxidation model, not by constants.** Glow passes only without kinetics: embers
   average 738 °C with CO products, or 939 °C with CO₂ only (the spec's 6d). With cited Arrhenius kinetics, char
   handed over at T_p never ignites. Which model is right for a 20 mm slat crib is a research question for the
   literature, not a dial to set. Char's temperature at hand-over matters too.
3. **0.1 m doesn't resolve a fire's surface layer.** Q2 shows flaming duration still changing between 0.1 m and
   0.05 m, so the "reference" isn't converged either. This is D25's rule biting: the envelope layer must be a
   sub-cell surface model sized in metres, not cells, or the truth grid's answer depends on its grid.
4. **Ignition at a threshold is order-sensitive.** Deciding ignition when a diffusing temperature crosses T_p made
   Q3's outcome flip with the law order. Ignition needs a flux criterion with a margin band, as CLAUDE.md requires for
   binary outcomes. Fixing the order would only hide the sensitivity.
5. **The energy ledger is necessary, not sufficient.** It caught a leak, but a closed-form check caught a units bug
   it couldn't see. Step 6 needs both.
6. **The body needs a skin layer, and the mechanic should key to heat flux.** Pain arrives long before the core warms.
   Pain in 10–120 s corresponds to about 2–6 kW/m² on bare skin. Clothing is the biggest lever after distance.

## What steps 5a and 6 should take from it (whatever the owner decides)

- **Step 5a's scheduler** (`splitting.md`):
  - Lie splitting, not Strang;
  - the law order conduction → skin → bed → open-air loss;
  - substeps fixed per physics step, so time runs in integer ticks;
  - latches such as `lit` included in the state digest;
  - each kernel's expression treated as part of the replay contract, because `np.dot(v, v)` ≠ `np.sum(v*v)` in the
    last bit;
  - BLAS kept out of kernels;
  - a CI determinism check at 1 and N threads on Linux, which is untested.
- **Step 4's harness:** a splitting test per scenario (n against 10n substeps, plus the reversed order, requiring the
  same outcome class), and convergence reported with the observed order. It must say when the reference itself hasn't
  converged.
- **Step 6:** ignition by flux with a band; a sub-cell envelope layer; the ledger plus closed-form checks; a cited
  spread law; a cited char-oxidation model; T_p checked against its literature range (349–364 °C for softwood, against
  the spec's 380 °C).
- **D28's prototype** (`body.md`): a skin node, a design keyed to flux, and clothing as a lever. Its feel shouldn't be
  tuned until step 6 measures the fire's real heat release.

## Decisions for the owner

The exit (D26, D30) can't pass as specified. These are the honest options; none tunes a constant:

1. **Research and add the missing physics to step 6.** Add a cited flame-spread law and a cited char-oxidation
   model, then rerun this spike's Q1 and Q2 before step 6 is designed. *Most faithful; the most research, with the
   outcome still uncertain.*
2. **Change the ignition, not the physics.** The player lights the crate with something that really engulfs it, such
   as an accelerant or incendiary. That's the fully lit scenario F, where the fire sustains (1a passes). *It keeps the
   physics honest and is plausible in-world.* Glow and burnout still fail with cited kinetics, so they need option 1's
   char work or option 3.
3. **Change the exit's glow and burnout criteria** to what honest physics produces: "the crate burns, cracks, chars
   and the flames go out", with ember glow deferred until char oxidation is researched. *Fastest; it gives up the
   glowing embers in Phase 1.*

**Recommended: 2 now, with 1's char-oxidation research as step 6's first task, and 3 as the fallback.** An
accelerant-lit crate is honest and good gameplay (fire as a tool the player prepares). It keeps the exit's flames, and
it leaves glow to depend on the one research question that decides it.
