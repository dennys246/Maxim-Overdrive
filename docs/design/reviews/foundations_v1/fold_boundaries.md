<!-- Moved verbatim from `docs/design/boundaries.md` at 5c054f6 by phase1/docs-contracts (CLAUDE.md, "One owner per
contract": fold tables live in reviews/). A record: never edited. -->

## Fold table: the foundations review (`reviews/foundations_v1/`)

Every foundations BLOCKER and SHOULD-FIX that touches this design. Status is **folded** (with the section),
**partial** (what is missing), or **elsewhere** (the document that owns it). Findings that touch only part 2 are in
`npcs_and_sem.md`'s fold table; those that touch only the Maxim drafts or roadmap Phase 3 are the drafts' fold.

| Finding | Severity | Status |
|---|---|---|
| Arch B1 the agent lane is defined nowhere | BLOCKER | folded: §7.1 (one owner per agent, the barrier); lanes §4.1 superseded in part 2 §11.1 |
| Arch B2 mode (a) + dilation deadlock | BLOCKER | folded: O6 drops mode (a); §7.2, §7.4 (DLP-B2's fixes) |
| Arch B3 `AgentPort` isn't the thought seam | BLOCKER | folded: §7.1 (port split, gateway) *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Arch S1 sibling layers aren't independent | SHOULD-FIX | folded: §2.2 sub-layers 5a/5b, 7a/7b/7c |
| Arch S2 restricted importers need what's forbidden; writers outside the core | SHOULD-FIX | folded: §2.2 skip-layer rule (stage-2 checks, `entity_key` in checks, save split, `ActionLimits.load` in loaders) |
| Arch S3 `to_maxim_entity` takes `World` | SHOULD-FIX | folded: §7.1 |
| Arch S4 frames can mutate; thread scope; cadence | SHOULD-FIX | folded: §4.1 (thread scope), §4.2 (copies, cadence) |
| Arch S5 agent foundations have no PR; the marker can't come out | SHOULD-FIX | folded: §6.4, §11.1 (`phase1/agents`); world_model §10 |
| Arch S6 `memory_write` in the world log | SHOULD-FIX | folded: §6.1 |
| Arch S7 the log record lacks the sub-tick key | SHOULD-FIX | folded: §6.2 (`apply_us`, one key) |
| Arch S8 SEM paths disagree; two items have no home | SHOULD-FIX | folded: §9.3, §5.1 (OD-C6, OD-C7) |
| Arch S11 no seam for game rules | SHOULD-FIX | folded: §2.1 (data only) |
| Arch S12 calibrations leave the resolution gate | SHOULD-FIX | folded: §8.2 |
| Arch S13 credit for slow effects; instruments | SHOULD-FIX | folded: §7.2 (OPEN with a red gate; declared sensors) |
| Arch S15 the registry check overstated | SHOULD-FIX | folded: §5.2 (mechanical rule, four plants) |
| X-1 the tripwire can't see what it claims | BLOCKER | folded here: §3 (profile hook); the world-clock draft's tripwire is the drafts' fold |
| X-2 [now] claims false with real Maxim | BLOCKER | folded: §7.3 (strict red gates until tier A) |
| X-5 CC3 misquoted | SHOULD-FIX | folded: §9.3 |
| X-12 schema, prompt, protected tests | SHOULD-FIX | folded: §7.3, §8.1, §10 |
| X-13 additive disagreement | SHOULD-FIX | folded: §9.3 |
| Wire B1 the window and frames before `Simulation` | BLOCKER | folded: §4.1, §11.1 |
| Wire B2 mode (a) can't reach the pipeline | BLOCKER | folded: O6; §7.1 (intent sink as a required port) *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Wire B3 no Maxim thought entry point | BLOCKER | folded: §7.1, §8.1 (the gateway) *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Wire S1 three time inputs, no invariant | SHOULD-FIX | folded: §7.3 |
| Wire S3 the seed path; CLAUDE.md drift | SHOULD-FIX | folded: §7.3, §11.2 |
| Wire S4 record fields and kinds | SHOULD-FIX | folded: §6.1, §6.2 |
| Wire S5 speech has no wire | SHOULD-FIX | folded: §6.1, §6.2 (`speak`); detail in part 2 §5.2 |
| Wire S6 which frame; leaks | SHOULD-FIX | folded: §4.2, §4.4 |
| Wire S7 dilation has no channel | SHOULD-FIX | folded: §6.3 |
| Wire S8 the header misses inputs | SHOULD-FIX | folded: §6.3 |
| Wire S9 the cache is unregistered | SHOULD-FIX | folded: §5.3 |
| Wire S10 stale Phase 3 ids | SHOULD-FIX | folded: OD- ids throughout (§4.3, §5.3, §7, §8.1, §9.3, §13) |
| Wire S11 §9.3 vs the SEM plan | SHOULD-FIX | folded: §9.3 |
| Wire S12 settle double credit | SHOULD-FIX | folded: §7.2 |
| DR-B1 agent code races the tick | BLOCKER | folded: §7.1 (barrier) |
| DR-B2 the host doesn't own the LLM call | BLOCKER | folded: §7.1, §8.1 |
| DR-B3 the cache isn't canonical | BLOCKER | folded: §5.3 (gate); the key in part 2 §4.8 |
| DR-B4 the v1 D-B4 fold doesn't hold | BLOCKER | folded: §4.1 (ownership window, the unlock-then-close proof) |
| DR-B5 throughput is the wrong bound | BLOCKER | elsewhere: part 2 §4.5 (boundaries carries no throughput claim) |
| DR-S1 Δt invariance vs bits | SHOULD-FIX | folded: §7.1 (`dt_ticks` from the schedule); detail in part 2 §2.1 |
| DR-S2 sub-tick units and field | SHOULD-FIX | folded: §6.2 |
| DR-S3 three ordering keys | SHOULD-FIX | folded: §6.2 |
| DR-S4 Philox stability | SHOULD-FIX | folded: §7.3 |
| DR-S5 agents share module state | SHOULD-FIX | folded: §7.1 (one real agent per process); the exit test is the drafts' |
| DR-S6 the dial test can't fail | SHOULD-FIX | folded: §7.3 |
| DR-S7 replay reproduces the world only | SHOULD-FIX | folded: §6.2, §6.3 (tiers, rerun manifest) |
| DR-S8 speech is world input | SHOULD-FIX | folded: §6.2 |
| DR-S9 unmeasured budgets | SHOULD-FIX | folded: §4.2 (frame copies, on change), §10 (barrier meters); remaining rows in part 2 |
| DR-S10 the agent adapter is unsealed | SHOULD-FIX | folded: §3 |
| DR-S11 machine-decided failures; policy changes | SHOULD-FIX | folded: §6.1, §6.2, §6.3 |
| TB2-B1 the NPC tool surface | BLOCKER | folded: §5.3 (roster gate) |
| TB2-B2 one shared home; pickle | BLOCKER | folded: §5.3 (homes gate-to-be), §7.1 |
| TB2-B3 thought budgets; liveness | BLOCKER | folded: §5.3, §6.1, §7.4 |
| TB2-S1 speech kind and gate | SHOULD-FIX | folded: §5.3, §6.1 |
| TB2-S2 the log excludes and includes LLM text | SHOULD-FIX | folded: §6.2 (per kind) |
| TB2-S3 the memory-write gate can't exist yet | SHOULD-FIX | folded: §5.3 (gate-to-be), §13 |
| TB2-S4 the cache is untrusted | SHOULD-FIX | folded: §5.3, §6.2 (replay never opens it) |
| TB2-S5 kind from model output | SHOULD-FIX | folded: §7.4 |
| TB2-S6 who stamps player ticks | SHOULD-FIX | folded: §4.2, §5.3 |
| TB2-S7 authority misses policy, requests, cancels | SHOULD-FIX | folded: §6.1 |
| TB2-S8 identity from the object called | SHOULD-FIX | folded: §5.3, §7.2 |
| TB2-S9 host data before tier A | SHOULD-FIX | partial: §5.4 (closed code vocabulary); the guest-session guard and LLM locality are owner questions in part 2 §12.1 |
| TB2-S10 in-process inputs from Maxim | SHOULD-FIX | folded: §5.2 |
| BF2-6 two meanings of instrument | SHOULD-FIX | folded: §4.4 |
| MP-B3 CC3 misread | BLOCKER | folded: §9.3 |
| MP-S12 the injected actor key isn't additive | SHOULD-FIX | folded: §9.3 |

NITs folded where they touched a section: Arch N1 (inline later is a future decision, §7.1); BF2-15 (§11.2).
