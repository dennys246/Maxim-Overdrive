# Determinism and replay (design review, torch_pilot.md at fcc6e55)

What I read at fcc6e55: torch_pilot.md in full, numbers.md, the commit's diffs to contracts.md, fire_solid.md and checklists.md, tile §2.2, §3.1–§3.2 and §6, sim_core §3, §5.1, §6, §7, §9 and §12, fire_solid §1, §2, §4.1–§4.4, §5.2, §5.4–§5.6 and §6, sem_stimuli §4.1, §4.5 and §5, boundaries §6.1–§6.3, and fire_solid's determinism review (FS-S11 / D1-S9). I ran nothing beyond reading and grep.

---

**D-B1. The pilot's lifecycle has no tick-order rule, and the deposit for the last partial interval has no state to come from.**
`docs/design/torch_pilot.md::§2, §5` (also `§9.1` beat 2). Contract defect: the digest, the save, `pilot_live`, the wire's pilots row and the ledger all depend on it.

- §5 computes n_t as "the number of the pilot's ticks in (t − 5, t]" from the record's [apply_tick, end_tick). §2 says the record "ends at `end_tick`, or on leave or `region_gone`". It never says at which tick-order step it ends (sem_stimuli §4.1: 1 apply … 6 physics), or what happens to end_tick when it ends early.
- sim_core §3 solved this same problem for sources. It adds `source_exposure`, whose closed segments `(key, value, ticks)` are digested and saved, and each physics step clears them. Nothing equivalent exists here.

Failure scenarios:
1. **Expiry on a physics tick.** apply_tick 70 and D = 50 give end_tick 120, a physics tick. Suppose the record is removed at step 1 of tick 120. The physics step at step 6 then no longer sees it, and ticks 116–119 are never deposited: 0.4 s of torch energy lost. The ledger reads the same missing record, so it still closes and nothing goes red. Every measured band edge in D is then biased by up to 4 ticks, depending on where end_tick falls in phase with `physics_every`.
2. **The record lingers instead.** If the implementation keeps the record until the physics step after end_tick, `pilot_live` refuses a second `kindle` at ticks 120–124 that tile §3.2 says should apply. The pilots row also stays live past end_tick, which contradicts §9.1 beat 2's [apply_tick, end_tick).
3. **`leave` mid-interval.** `leave` runs at kind_rank 0 in step 1. At L = 118, either the record vanishes and ticks 116–117 are lost, or end_tick is rewritten to 118. The second choice changes a saved, digested field that the wire also carries, and §2 doesn't say it happens.
4. **`region_gone` mid-interval.** In 6.1 burnt-out rows stay (fire_solid §1.1), so for a fuel object it is undefined when its region is "gone". Burnout happens inside step 6, so it is also undefined whether the pilot ends at step 6 of tick t or at step 1 of t + 1.
5. **The digest.** sim_core §9 rehashes a member only on a tick whose window wrote it. If expiry is a filter rather than a windowed write, the running digest keeps the expired record. A digest seeded on load from the saved state would not, so §9.3's "save at a mid-pilot tick, loaded, equals one continuous run" goes red, or green by accident, depending on the implementation.

Minimal fix (unverified): state the end rule as a tick-order step. One option is truncating end_tick at the ending event, applied in step 1's window, with the record kept until the first physics step whose interval contains end_tick − 1. Another is a closed-segment input on sim_core §3's `source_exposure` pattern. Add the phase-boundary cases (end_tick on and off a physics tick, leave and burnout mid-interval, a save at each) to the step 6 checklist.

---

**D-S1. The digest and registry placement of the pilot record are claimed but owned elsewhere and not routed.**
`docs/design/torch_pilot.md::§2, §10`. Contract defect.

- §2 says the record is "saved and digested, in key order", with its "registry entry beside `sources` (sim_core §6)".
- sim_core §9 owns an explicit, ordered member list: registry fields, then `sources`, `source_exposure`, regions and records. An input that is not a registry field has no member there. That leaves its position, its byte layout and whether `centre_um`'s i64 is written signed undefined. The record encoding says integers are u64.
- §10's edit table names neither a sim_core §6 or §9 edit nor a sim_core §12 or boundaries §6.3 recorded golden break. Today the only owner of the pilot's digest bytes is a sentence in a document that doesn't own the digest.

Failure scenario: the build adds pilots as a member after `sources` while the save loader seeds members in registry order. The tick digest after load differs from the running digest, and the replay golden regenerates without a recorded change.

Fix (unverified): add sim_core §6, §9 and §12 rows to §10's table, and step 9's save checklist entry.

---

**D-S2. "Exact, in whole micrometres, from the authored integers" is not true of the geometry the target and overlap read.**
`docs/design/torch_pilot.md::§2` (`centre_um`, `radius_um`), `§3`, `§4.3`. Contract defect: the fields are saved, digested, and are candidates for the wire (Q5).

- fire_solid §1.1 stores object geometry as "f64 per kind": a rod's unit axis, and a slab's origin and two unit edge axes. fire_solid §5.2's scene `fuel:` entries are "metric geometry". Only cell edges and segment lengths are integer micrometres (F13).
- For any rod, or any slab whose axes are not grid-aligned, the nearest surface point and the point-to-geometry distance are irrational. The design gives no rounding rule (floor, half-even, or the order of operations) for `centre_um` or for `radius_um` from the item's `radius_m`.
- Rounding a centre to micrometres also moves it off a tilted face's plane, and the design doesn't say whether the overlap projects it back.

Failure scenario: a slab rotated 30° and a point 1.0004 mm from a tie. Two implementations of "exact µm", truncating against rounding, differ on `ambiguous_point` against `applied`. The tie bound also becomes an f64 comparison whose class could flip across machines at the 1 mm edge.

On one machine replay still agrees, because it runs the same code. But the record's meaning is unspecified, and bit-identity of rebuilt overlaps depends on the projection step.

Fix (unverified): either restrict 6.1b targets to axis-aligned authored geometry in integer micrometres and say so, or state the f64 evaluation order and one rounding rule for each integer field.

---

**D-S3. The `face` field has no tie rule at edges and corners, and the outcome depends on it.**
`docs/design/torch_pilot.md::§2` (`face`), `§3`, `§4.1`. Contract defect: `face` is a saved, digested field, and §4.1 makes the deposit zero or non-zero on it.

- A point just outside a slab's top edge has its nearest point on the edge, equidistant from the top face and the side face.
- A point inside near a corner has equal depth to two faces.
- §3 refuses ties between candidates (objects), not between faces of one candidate.

Failure scenario: a `kindle` at the slab's top long edge. If the code orders faces top-first it records the top face and the slab lights. If it orders them side-first it records `applied` with zero deposit (§4.1) and the slab never lights. The rule then rests on an undocumented enumeration order that a refactor can change. That changes the replay golden and the class of the outcome, with no recorded change.

Fix (unverified): one written face-precedence rule, or refuse at a face tie within the same 1 mm band. Add a build test at an edge and at a corner.

---

**D-S4. The clock arithmetic hard-codes T3 and is undefined at the refined steps §9.2 gates on.**
`docs/design/torch_pilot.md::§5` ("q''_t · A_ov,p · 0.1 s · n_t", "n_t / 5"), `§9.2` ("at the 0.5 and 0.25 s steps", "at dt and dt/2"). Contract defect: the gate's definition and the ledger depend on it.

- sim_core §3 states a source's energy as a per-tick sum "times `tick_us`, in integers", with `physics_every` as config. The pilot writes the literals 0.1 s and 5.
- fire_solid's 0.25 s and dt/2 runs refine time below the 0.5 s physics step through `substep_refine` (sim_core §8), with ticks unchanged. The design doesn't say how n_t's ticks are spread over the solid's substeps (step-mean on every substep, or per-substep tick counts), or whether the pilot condition "at that step" is per substep or per physics step.

Failure scenario: at the 0.25 s step a pilot whose last covered tick is t − 1 gives n_t = 1 of 5. One implementation deposits 1/5 of the flux on both substeps and lets either substep flash. Another deposits on the second substep only. The dt/2 beats differ by implementation, not physics, and the time-convergence gate measures the choice.

There is also a stated equality that is false as written. §5 says "Ledger and solve use the same f64 expression". The ledger is q·A_ov·0.1·n_t, while the solve is q·(A_ov/A_part)·n_t/5, multiplied by A_part and 0.5 s to book it. In f64 these are not bit-equal, so either the sentence or one of the formulas must change.

Fix (unverified): write both in terms of `tick_us`, `physics_every` and the substep's share, as one named expression that both the ledger and the solve call.

---

**D-S5. The overlap's build site, cache key and eviction are unstated, and rebuild-equals-running is exposed to the SIMD offset problem.**
`docs/design/torch_pilot.md::§2` ("rebuilt from the record … equal bit for bit to a rebuild"), `§4.3`, `§9.3`. Mechanism; the build test belongs in the step 6 checklist.

- The disc-against-rectangle closed form uses asin, acos or atan2 and sqrt. A vectorised numpy evaluation can return different bits for an element depending on its offset or tail position in the array. That is fire_solid's open FS-S11 / D1-S9 for `exp`.
- The running path builds overlaps for one pilot at stage 2 or at its first physics step. A rebuild on load builds all live pilots' overlaps, possibly in one batched array.
- sim_core §7 requires a cache to be keyed by the values it reads, and evicted on replace, remove and rollback. The design gives no key (record values against `(actor_id, seq)`), no build site, and no eviction at expiry.

Failure scenario: two actors pilot one slab in co-op. After a load, both pilots' overlaps are computed in one 2×N array, and pilot B's elements sit at a SIMD tail position they didn't occupy live. One ulp differs, and the digest of the solid's nodes diverges from the continuous run at the next physics step. The checklist's "rebuild of the overlaps, bit-identical" test catches this only if it rebuilds with more than one pilot and runs on x86-64.

Fix (unverified): state that overlaps are computed per pilot, in one call shape on both paths, or by scalar `math` functions. Add the D1-S9 offset and subset case, with two or more pilots, to the step 6 checklist.

---

**D-S6. Several pilots on one part have no stated summation order.**
`docs/design/torch_pilot.md::§4.2` ("It adds to everything else the part receives"), `§9.3` ("summed in segment key order"). Mechanism, close to contract because it fixes the digest's arithmetic.

- §9.3 orders the sum by segment key. A part covered by two pilots (two actors, or one actor's lingering record plus a new one per D-B1) needs a pilot-key order, plus a fixed order against q''_fl (Q2) and the other terms. sim_core §5.1 and §7 require sorted-key order for accumulations over named collections.
- The convective-off share Σ f_p·n_t/5 can exceed 1 with two pilots, and no clamp or order is stated.

Failure scenario: an implementation that iterates pilots in insertion order agrees with sorted order until a load rebuilds the table sorted. After that, a three-term f64 sum reassociates and the digest diverges.

Fix (unverified): one sentence: per part, sum in (actor_id, seq) order, then add q''_fl. Add a build test with two overlapping pilots, applied in both orders.

---

**D-S7. The target's candidate set doesn't say whether `pending` objects count.**
`docs/design/torch_pilot.md::§3` ("every live fuel object"). Contract defect in the shared target function; mechanism for the test.

- fire_solid §1.4 holds an accepted `imagine` in `pending` until its batch drains. An `imagine` and a `kindle` share kind_rank 30, so within a tick their order is apply_us, then actor, then seq.
- If `pending` counts, a pilot can name an `object_id` that isn't yet in `objects`. Its overlap built at apply would then read pending geometry, while a rebuild after the drain reads the table. If `pending` doesn't count, the same `kindle` targets the floor, or returns `not_on_surface`.

Failure scenario: an NPC imagines a slab and kindles it in the same tick. The result depends on a rule nobody wrote down, and save-at-that-tick against continuous rests on the choice.

Fix (unverified): state the candidate set, for example "objects in `objects` as of the start of stage 2; `pending` excluded".

---

**D-N1. The 6.2 migration should be named a recorded digest break for logs, not only saves.**
`docs/design/torch_pilot.md::§2` ("6.2 migrates each saved record to a flame object, under a save version bump"). A replay golden recorded at 6.1b and replayed under 6.2's flame-object law gives a different world. sim_core §12 and boundaries §6.3 require that to be a recorded change. The design mentions only the save bump.

**D-N2. Step 9's save checklist doesn't name the pilot record.**
`docs/plans/checklists.md` step 9 lists "the actor and pilots tables" (the wire table). torch_pilot §2 says the record is step 9's save requirement, and §10 doesn't route that edit.

---

What I checked and found sound:
- The [apply_tick, end_tick) against (t − 5, t] convention matches tile §3.2 and sim_core §3.
- Apply at step 1 precedes physics at step 6, so a `kindle` applied on a physics tick counts that tick.
- Recomputing the target on replay from the logged point, with `target: null`, matches tile §3.2 and boundaries §6.2.
- Item data is covered by the log header's content digests (boundaries §6.3).
- `flux_w_m2` copied into the record keeps a save independent of later item edits.
- The pilot condition is a pure function of the record and the schedule.
- Cross-machine libm differences in the overlap are within the promise that only the outcome class holds across machines, which §9.3 states.
- No RNG or wall clock is introduced.

Count: 1 BLOCKER, 7 SHOULD-FIX, 2 NIT.
