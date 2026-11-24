# Bio-faithful integration: torch_pilot.md at fcc6e55

I checked every item below against the tree at fcc6e55. On the Maxim side I read `b98954f7` read-only with `git show` and `git grep`. `b98954f7` is the same commit as the local `origin/main` ref. I did not fetch, so I cannot say whether that ref is current.

**B-S1. §12 sends OD-A16 to R4, against the roadmap, and misses two Maxim texts that predict kindle's credit failure.** Location: `docs/design/torch_pilot.md::§12`. Kind: contract (routing a Phase 3 item; `docs/roadmap.md` owns that row).
- **The routing contradicts the roadmap.** §12 says "OD-A16 stays a question to R4". The roadmap's OD-A16 row (`docs/roadmap.md:203`) sets its plan as "amendment". That row's draft is `docs/maxim_upstream/propose_settle_amendment_DRAFT.md`, "an amendment to `tool_failure_credit.md` (#1200)", and the row rides on OD-A18. So §12 restates, wrongly, a route that has one owner. That breaks one owner per contract, and it leaves two contradicting texts after merge.
- **The search missed what bears directly on kindle.**
  - `docs/plans/tool_failure_credit.md:76-80` (an ACTIVE plan, TF1–TF3): "Retiring at invocation end removes the 300 s pending window for tool events … R4 delayed credit must not assume the window."
  - `docs/plans/roadmap_1_4.md:69-71`, R4's own definition: "credit is anchored to the executor CALL window … relief landing after a call returns credits the NEXT call."
  - Together these say what will happen to an NPC's kindle. Its invocation retires when the intent is applied. The `accepted` receipt arrives in the first delivery after the merge (`sem_stimuli.md` §6.2). The flash comes at `t_flash`, physics steps later and while the pilot is still live (§9.1 beat 7). Whatever the flash causes is then credited to the NPC's *next* call, or only to the `tool:kindle` eligibility trace. That trace is 0.3 at completion, ×0.9 per loop iteration, pruned below 0.01. It lands on the 0.20-capped `_reward_bias` surface (`lookback_primitive.md` §"What exists", item 1).
- **§12's description of the trace is incomplete.** It cites only "pruned after about 44 loop iterations". The path a seconds-late outcome actually uses is the temporal-anchor tier. That tier ages on `time.time()` (`src/maxim/decisions/nac.py:3715`, `temporal_window_seconds = 300.0` at `:439`), which is the wall-clock divergence of OD-A20/OD-A21. §12 omits it.
- **Failure scenario.** A Phase 4 NPC kindles a slab, then moves away. The flash's consequence (pain, or a later relief) credits `move`, not `kindle`. The roadmap says OD-A16 tracks this. §12 says R4 does. Whoever later flips the red gate reads two owners.
- **Fix (unverified):** make §12 a link to the roadmap's OD-A16 row. Cite `tool_failure_credit.md:80` and `roadmap_1_4.md:69-71` as what was found.

**B-S2. The named evidence for OD-A16 measures the wrong quantity, and the future-bar rule's isolating evidence is missing.** Location: `torch_pilot.md::§12` ("The time from `kindle` to `t_flash` … is its evidence"). Kind: contract (CLAUDE.md, "A future bar is tracked, never dropped").
- `t_flash` is host state, a latch in the solid. An agent never sees it. The delay that matters for credit runs from the receipt (`sem_stimuli.md` §6.2) to the first change in a bound stimulus row the body actually has.
- In Phase 1 no row carries flame. `client_objects.md` §5.4: "a … just-ignited [stick] looks the same to an NPC as unburnt wood at that temperature", OPEN against OD-C8. So kindle→`t_flash` can be short while the perceived effect never arrives.
- CLAUDE.md requires "a separate, passing test that what our membrane hands Maxim … carries the stimulus". §12 names none.
- **Failure scenario.** At 6.1b the evidence shows "flash at 8 s". The OD-A16 draft reads that as an 8 s credit horizon. The real perceptual horizon is undefined, because no row sees fire, so the amendment is sized on the wrong number.
- **Fix (unverified):** name both delays. One is kindle→`t_flash` (physics). The other is receipt→first change in a declared stimulus row (membrane), recorded as "none in Phase 1" with OD-C8 cited.

**B-S3. A player's and an NPC's kindle are one act only at the record level: the hold→ticks data is missing.** Location: `torch_pilot.md::§3` (the producers bullet), §6 (row "D, the hold"), §10 (`content/items/torch.yaml` fields). Kind: contract (a versioned item format that layer 6's adapter depends on).
- tile §3.2 says the NPC's `hold: brief | steady | long` is converted to ticks "from the item's data". §10's item fields are only `flux_w_m2`, `radius_m`, `max_duration_s` and `restrike_s`. There is no brief/steady/long duration.
- §6 sets D from the exit's band (≥ 2× its upper edge). That is a single scripted `duration_ticks`, the player's wire field (tile §3.3).
- The torch's data is a contract §0 claims to own, yet nothing says where an NPC's `long` sits relative to the band.
- **Failure scenario.** At Phase 4 the adapter has no field to read, so someone hard-codes the three durations in layer 6. Alternatively `long` comes out shorter than the band's lower edge. Then every NPC kindle is fruitless by construction, and the miss is booked against Maxim's learning.
- **Fix (unverified):** either add the three hold durations to the item's fields, with their relation to the band stated or "measured at 6.1b", or say they are deferred to the Phase 4 body design, citing tile §3.2.
- §3's claim that the same function runs on the same record kind is sound: stage 2 lives in the applier, and the log carries `target: null`. Phase 1 has no NPC producer, so the checklist's "one call site for every producer" test can only cover the player path today. The design should say so.

**B-N1. The leak rules cover the record but not its derived Frame rows.** Location: `torch_pilot.md::§2` ("It is not perceivable"), §11 Q5. Kind: contract (leak rule).
- §2 marks the pilot record non-perceivable. It says nothing about the Frame's pilots table, `pilot_ended`, or Q5's proposed `point_mm` (tile §2.2, §4).
- Today nothing leaks. `sem_stimuli.md` §7.4's completeness gate and §4.2's `BodyFrameFeed` both keep agents off the `Frame`.
- But Q5 adds an exact footprint point. `region_id` is the derived target. Together they would form an existence and target oracle if either is ever made perceivable, and that is the oracle `sem_stimuli.md` §6.2 removed `applied`/`unavailable` to prevent.
- **Failure scenario.** A later sight row reads "pilots" to draw a torch for NPCs. A reviewer sees §2's "not perceivable" and takes it to cover the table.
- **Fix (unverified):** one sentence stating the pilots table, `pilot_ended` and any `point_mm` stay non-perceivable, linked to `sem_stimuli.md` §7.4.

**B-N2. The design names target-dependent `applied` outcomes without saying that the agent's receipt cannot tell them apart.** Location: `torch_pilot.md::§4.1` (side face: `applied`, zero deposit), §4.4 (cell target: `applied`, null `object_id`), §9.1 beat 1. Kind: contract (link only).
- These are `intent_result` outcomes (tile §3.3), not the agent receipt. Under `sem_stimuli.md` §6.2 the agent receipt is `accepted` in every case.
- §6.2's T11 sweeps "every target-dependent *refusal*". §4.4's case is an `applied` with a target-dependent difference, which that sweep does not name.
- **Failure scenario.** A later edit adds a deposit total to the agent receipt "for the exit's beat 1". T11 stays green, because nothing was refused.
- **Fix (unverified):** link `sem_stimuli.md` §6.2. Add §4.1 and §4.4's cases to the T11 sweep list in checklist step 6.

**B-N3. "The torch heats no body" is missing from the Known gaps.** Location: `torch_pilot.md::§3` (the candidates are fuel objects and cell regions only), §7. Kind: Known gap.
- No actor body is a candidate, and the footprint deposits only on fuel segments. So a torch held against an arm, the holder's or another body's, deposits nothing a tissue row can sense.
- That is moot unless 6.2's flame object slips past Phase 4, which §7 of fire_model's fallback makes possible. It should still be named next to "the torch heats no structural cell".
- **Failure scenario.** Under the fallback, an NPC learns that a lit torch on skin is harmless.

**B-N4. Lesson not recorded (CLAUDE.md, B18).**
- `docs/lessons_maxim_in_games.md` does not hold this. No text in the repo says that "a held act's effect arrives after Maxim retires its invocation, so call-window credit pays the next call". I grepped for "next call", "call window", "invocation end" and "pending window" over `docs/lessons_maxim_in_games.md`, `docs/maxim_upstream/propose_settle_amendment_DRAFT.md` and `docs/design/npcs_and_sem.md`: no hits. The draft's "Slow effects" paragraph says the opposite: "Consequences that take seconds stay with NAc's temporal window."
- This lesson exists only if B-S1 folds. It is evidence against the amendment draft's own slow-effects assumption, so it belongs in the same commit that folds B-S1.

**Checked, nothing found:**
- **Maxim search terms** (`kindle`, `igniter`, `held item`) find nothing on kindle or igniters. `kindle` hits only experiment JSON data.
- **Held items.** `base_humanoid.yaml:153` has `use` "a held or nearby object … activate", a free-string act. That is fire_model §5.4's NPC-builder pin to enforce, not this design's. `embodiment/motor.py`'s `ProgramRegistry` indexes motor programs "by entity type" ("I'm holding a sword"). It bears on kindle only once held items are entities (Phase 4). Not a defect here.
- **§12's other citations hold.** `lookback_primitive.md` is SHIPPED. `deferred/three_factor_credit_assignment.md` is "Revive when: the R4 credit build starts". `deferred/credit_on_progress_not_execution.md` is DOWNGRADED and was not cited; it is relevant only as background to fire_model §5.4's "fruitless act succeeds".
- **fire_model §5.5** (what the bridge must never do): the design adds no outcome description, no flammability or threshold exposure, and no instrument to the bridge. The pilot condition and the unpiloted-crossing counter are host-side, and §9.1 reports them as "logged server state".
- **Clock.** The deposit runs on `Simulation.step` ticks. The hold reaches agents as a word, never ticks, per tile §3.2. No wall-clock read is introduced.
- **§8's flame asymmetry** is correctly filed against `client_objects.md` §5.4 / OD-C8.

Count: 0 BLOCKER, 3 SHOULD-FIX, 4 NIT.
