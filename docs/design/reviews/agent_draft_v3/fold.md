# Fold status: Maxim's plan review of the agent draft v3

Reviewer's statuses (O25), read from the tree at `phase1/agent-review` c12c19b, not from the fold commit's message.
Maxim read only on `origin/main` f0b1cea4. "Draft" is `docs/maxim_upstream/embeddable_agent_DRAFT.md` (v4); "npcs" is
`docs/design/npcs_and_sem.md`.

| Item | Gist | Status | Where |
|---|---|---|---|
| DNB §2/§6 robot parity | exit tests for B1 (bit-identical digest on recorded replies, Exp 49/60) and B2 (settle immediately) before either is built | fixed | draft §2 robot bullet, §6 OD-EA14, OD-EA15; roadmap Phase 3 exit (`:208-209`), OD-A15, OD-A18 |
| SF shortcut stale | deleted for everyone (#1689, PR #1694); #1691: fallback books no credit but still echoes | fixed | draft §1 "Gone", §2 parse bullet; roadmap OD-A17, Phase 4 bypass test as a regression; npcs §6.1 leak row, §6.6, §12.1 item 1, §12.2 |
| SF basis and staleness | adopt §A.1b.5 (tracked rights after `basis_seq`, efference copy), typed pre-emption handler, drop "superseded" | fixed (O38) | draft §2 staleness bullet; npcs O38, §6.6; roadmap OD-A15; lesson 14 |
| SF `apply` vs `settle` | second write door needs a reason, or merge | fixed (O39) | draft §1, §2 table; npcs O39, §6.2/§6.6, §11.3; `boundaries.md`; `world_model.md` 9b; lesson 16 |
| SF request value | produced at `LLMRouter._complete_text`; who supplies `n_ctx` to `PromptBudgeter` | fixed | draft §2 request bullet; npcs §6.1 cut row; roadmap OD-A14 |
| SF receipts | `settle` publishes through the agent bus | fixed | draft §2 table; npcs §6.6; OD-EA4 |
| SF `MAXIM_DATA_HOME` exception | A4 waits for A1; no env exception | fixed | draft §1, §3; npcs §6.6 environment bullet; `boundaries.md` agent-homes row; roadmap OD-A17 |
| SF Q9 premise | SCN hour/day reach the model via `temporal_patterns`/`[TEMPORAL]`; classify both sides | fixed | draft §4 OD-A20 bullet; roadmap OD-A20 ("v3 lean was wrong"); lesson 15 |
| SF gate scope (§5, Q2) | per-agent key is a new gate item, not a widened `1305.owned-rng`; scope tied to `seed_all` | fixed | draft §4, §5; npcs O40, §6.6; roadmap OD-A7, Phase 3 prose; plan Tier A |
| SF OD-EA7 "none found" | it is `1263.thread-guard` | fixed | draft §6 OD-EA7; roadmap Phase 3 exit; plan exit list |
| NIT one derivation | `make_agent_rng` (SHA-256) already exists; drop `stable_hash_64_signed` | fixed (O40) | draft §4; npcs O40, §3.4, §6.6; roadmap OD-A7 |
| NIT "5–15×" arithmetic | show it; 50-pass τ is 1.7–5 s | fixed | draft §4 τ_elig bullet (9.49 passes, 0.32–0.95 s vs 4.75 s; distinguishes the 50-pass τ) |
| §7 background-worker thread | belongs to A4's closure via `build_memory_hub(start_background_workers=False)` | fixed | draft §5 step 3; roadmap OD-A12. Residue: the draft's id table still maps OD-A12 to cand. A1, and §5's first-NPC list says "OD-A12's host-driven thread"; harmless but the owner of the thread reads two ways |
| §7 `agent_id` and #1305 | persisted NPC key, both conditions; timing Maxim's owner | fixed | draft §4; npcs §6.6; Maxim's owner then decided (Q2 row) |
| §7 A3 | split already folded; host duration is the root fix | fixed | draft §4 machinery and duration bullets; roadmap OD-A4 |
| §7 G2b | checks one trace vs its anchor; OD-EA12 needs the fixture widened, a #1361 slice decision | deferred: named draft §7 Q2; reason, Maxim's #1361 decision; trigger, its answer (if no, OD-EA12 is ours in Phase 3 against S3b, roadmap Phase 3 prose) | draft §6 OD-EA12, §7 Q2; roadmap `:99` |
| §7 shortcut | deleted at the root | fixed | as the SF row |
| §7 static ban | host on `utils/audit.py` with `lint_dead_imports`' resolver; `importlib` blind spot; no env exception | fixed | draft §3; roadmap OD-A17 |
| §7 `environment.step` | B2's call; suggestion: no environment embedded, follow-up in receipts | fixed (our position recorded; the decision stays B2's) | draft §2; roadmap OD-A18 |
| §7 B1 | host-owns-the-call valid only embedded; robot keeps `_complete_text_abandonable`; shape fixed in B1's plan after 1.4.0 | fixed | draft §2 reply bullet |
| §7 OD-A20 | raised on #1361, pending | fixed (overtaken by the Q9/OD-A20 owner decision) | see that row |
| §7 MaximHandle | separate constructor via `AgentFactory`; `save()` not `stop()`'s contract; consolidation its own call | fixed | draft §2 construction and consolidation bullets; npcs §6.1 row, §6.6 codec kinds |
| Citation drift | eight sites moved since 6fee7377 | fixed | draft §2–§4, roadmap, plan, npcs; all eight hold (Check 1). One unlisted stale citation remains: npcs §6.1 `router.py:185`, `:1080` for `_inference_lock` (now `:192`, acquire `:1094`) |
| `src/` before 1.4.0 | steps 1–4 not hybrid-family if A4 exposes no `think`/`Pending`/continuation and basis/staleness stay out of B2 | fixed | draft §5 "Before 1.4.0"; roadmap Phase 3 prose; draft §2 staleness ("stays out of B2") |
| Owner Q2 | A2's key after the cut, new gate item; `1305.owned-rng` unchanged | fixed | draft id table, §4, §5; npcs O40, §6.6; roadmap OD-A7; plan Tier A |
| Owner Q9 / OD-A20 | host calendar stays; noted, not adopted; aging on experience clock | fixed (author, after this review; not re-verified) | recorded as declined everywhere (draft §4, roadmap OD-A20, npcs §12.2, lesson 17). The divergence's strict red gate (`checklists.md`) does not reliably go red as specified (Check 3), and npcs §12.2 and lesson 17 still describe it as "two host hours", the variant `checklists.md` itself says passes | Author fix: the gate now settles one receipt on a live-trace node and an anchor-only node across midnight, plus an anchor-survives-a-pause assertion; §12.2 and lesson 17 aligned; the divergence restated as a sharing effect.
| Owner Q10 | `save()` not `stop()`'s contract; consolidation bounded host call | fixed | draft §2; npcs §6.1 row, §6.6 |

## Checks

### 1. Maxim citations on f0b1cea4

Hold (26): `router.py:958` `_complete_text`; `:998` `_complete_text_abandonable`; `console/handle.py:176`
`MaximHandle`, `:741` `stop`; `llm_fallback.py:267` `generate_llm_fallback`, `:296-304` the `'{question}'`
templates (module docstring `:8` confirms `generate_simple_answer` deleted by #1689); `llm_worker.py:1301-1318` the
fallback call; `agent_loop.py:3110-3111` `3 if percept_source … else 2`; `tool_dispatch.py:1419` `exec_elapsed`,
`:695` `_observe_energy_cost`, `:1574` `environment.step(result)`; `loop_controller.py:154`
`llm_submit_interval = 0.5`; `input_handlers.py:171` `_handle_phrase_text`; `utils/seeding.py:79` `make_agent_rng`
(SHA-256 of `f"{base_seed}:{agent_id}"`); `bio_stack.py:489` `start_background_workers=False` inside
`build_memory_hub(` at `:481`, `:654` the start; `experience_time.py:36` `ExperienceClockDriver`; `bootstrap.py:623`
`AdaptivePlanner(`; `adaptive_planner.py:487`; `tool_pain_bridge.py:806`; `fear_agent.py:303`, `:317`;
`nac.py:3707` `decay_eligibility`, `:3625-3640` the anchor fallback, `:3715` `time.time()`, `:875` session-scoped;
`prompt_builder.py:229`, `:1122-1124`.

Fails (1, not on Maxim's list): npcs §6.1 `router.py:185`, `:1080` for `_inference_lock`; on f0b1cea4 it is created
at `:192` and acquired at `:1094` and `:1225`.

A side confirmation for draft §7 Q3: `make_agent_rng` hashes `f"{base_seed}:{agent_id}"`, so `agent_id =
"npc_key:stream"` gives exactly the string a three-argument `f"{base_seed}:{agent_id}:{stream}"` would. The interim
key survives the change if the gate item keeps that join.

### 2. Leftovers (`git grep`, outside dated review records and fold tables)

- Four-call `AgentPort` (`apply` as a host call): **none.** `boundaries.md:75`, `:165` are the world bridge's own
  `apply`, unrelated. Inside a fold table: npcs `:1440` still reads "`apply` and `settle` the only writers"
  (historical row; excluded).
- "Superseded" staleness verdict: **none;** npcs `:816`, draft `:38` and lesson 14 mention it only as dropped.
- `stable_hash_64_signed` derivation for agent streams: **none;** npcs `:850`, draft `:128`, lesson 15 say it is
  dropped. The rest are review records.
- Shortcut claimed to exist in Maxim: **none outright.** Two softer hits: npcs O14 (`:56`, a dated decision text)
  lists "the short-question shortcut" among the bypass-test targets, and §12.1 item 1 (`:1116`) lists "the
  shortcut" before saying at `:1119` that Maxim deleted it. Roadmap `:225` recasts it as a regression test, which is
  the consistent reading; O14 and `:1116` could say the same.
- `MAXIM_DATA_HOME` exception: **none;** npcs `:757`, draft `:42`, roadmap `:142` say it is dropped. Inside a fold
  table: npcs `:1458` still says "`MAXIM_DATA_HOME` the one allowed read until OD-A12" (historical; excluded).

### 3. Can the OD-A20 red gate go red against real Maxim?

What the code does (f0b1cea4). `NucleusAccumbens.distribute_reward` (`nac.py:3589-3655`) and
`TemporalCreditDistributor.distribute` (`temporal_credit.py:202-270`) both build `all_eligible` = live traces
(> 0.01) plus, for nodes without one, `0.3 × anchor_sig.similarity(TemporalSignature.now()) × activation`, then
**normalise: each node's credit is `reward × strength / Σ strength`.** `TemporalSignature.similarity` is
`1 − 2 × mean(circular distances)` over circadian, weekly, monthly (`(day−1)/31`) and annual (`(yday−1)/365.25`)
phases from `datetime.fromtimestamp(time.time())`. Anchors are pruned in `decay_eligibility` (`:3715-3738`) once the
trace is gone and `time.time() − sig.timestamp > 300`.

Numbers. A 12 h shift: circadian distance 0.5, weekly 0.5/7, plus 1/31 and 1/365.25 if a date boundary is crossed,
giving similarity ≈ 1 − (0.5 + 0.071 + 0.032 + 0.003)/2 ≈ 0.70 (0.71 without the date step). Crossing midnight at
23:59:50 with a short delay: the monthly phase steps 1/31 (2/31 into a short month's wrap), similarity ≈ 0.983. The
docs' numbers are right. Two start hours, same pacing, no boundary: identical distances, identical credit; the
checklist is right that this variant cannot go red.

Where the redesign still fails.
- **Normalisation cancels the similarity for the scenario as written.** "A receipt settled after its trace
  expires" credits one anchor-only node; its share is `x / x = 1` whatever the similarity (it only has to clear
  0.01: 0.3 × 0.70 = 0.21 does). With several anchor-only nodes anchored within the same window, every strength
  scales by nearly the same factor and the shares move by rounding at most. So under midnight, the gate as specified
  passes, and a strict `xfail` then fails as XPASS: the gate is broken, not red. It goes red only if the scenario
  also holds a **live** trace (a node still above 0.01 on the fast path, whose strength does not depend on host time)
  beside the anchor-only node. Then the anchor's share `0.3s/(t + 0.3s)` moves with similarity `s`, and the midnight
  step (s 1 → 0.983) changes the shares, enough for an exact-equality assertion. The checklist must say so.
- **The 12 h pause, today, goes red for a different reason than the docs give.** On f0b1cea4 the 300 s window is
  wall time: the next `decay_eligibility` after a 12 h host pause sees age 43,200 s > 300 and deletes the anchor. The
  node drops out of credit entirely (a lone anchor node: no credit at all). That is red, robustly, and it is the
  larger host-time leak, but it is pruning, not the "about 0.70" similarity the docs cite. After #1361 S3b anchors age
  on the experience clock, the prune stops firing, the 0.70 similarity appears, and the variant then has the same
  normalisation problem: red only with a co-eligible live trace.
- A 12 h pause "inside the 300 s window" is only coherent in experience time; the docs should say the window is
  experience time after S3b and wall time today.

Verdict: **not reliably red as specified.** Fix: the scenario holds one live-trace node and one anchor-only node
(activation 1 each), and asserts their shares equal across a 09:00 run and a 23:59:50 run; the pause variant, kept,
should assert separately that the anchor survives (red today by the wall-clock prune, red after S3b by the share
shift). Also bring npcs §12.2 and lesson 17 ("two host hours") in line with `checklists.md`.

### 4. Word counts

- Draft: 2,495 (`wc -w`), under the 2,500 cap, by 5.
- Plan (`docs/plans/foundations_plan.md`): 2,494; `scripts/check_plan.py`: PASS (0 findings).
- `npcs_and_sem.md`: 23,729 now vs 23,735 at 8f06269 (and at aae1992): shrank by 6, so O22 holds.
