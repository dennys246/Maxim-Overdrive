<!-- Moved verbatim from `docs/design/npcs_and_sem.md` at 5c054f6 by phase1/docs-contracts (CLAUDE.md, "One owner per
contract": fold tables live in reviews/). A record: never edited. -->

## Fold table: the foundations review (`reviews/foundations_v1/`)

Every BLOCKER and SHOULD-FIX that touches this part. Status is **folded** (with the section), **partial** (what is
missing), or **elsewhere** (the document that owns it).

| Finding | Severity | Status |
|---|---|---|
| Arch B1 the agent lane is defined nowhere | BLOCKER | folded: §6.3, §11.1 |
| Arch B2 mode (a) + dilation deadlock | BLOCKER | folded: mode (a) dropped (O6); §4.4 DLP-B2 fixes and no-deadlock invariant |
| Arch B3 `AgentPort` isn't Maxim's thought seam | BLOCKER | folded: §6.1 gateway, §6.2 port split *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Arch S3 `to_maxim_entity` takes `World` | SHOULD-FIX | folded: §6.5; boundaries §7.2 |
| Arch S5 agent foundations have no PR; the marker can't come out | SHOULD-FIX | folded: §6.2 (`phase1/agents`, its TEMPORARY marker); world_model §10 |
| Arch S7 part 2 quietly extends the log record | SHOULD-FIX | folded: §9; the key and `apply_us` are in boundaries §6.2 |
| Arch S8 SEM paths disagree across docs | SHOULD-FIX | folded: §8.1, §12.3; boundaries §9.3 |
| Arch S9 [now] tags need tier A | SHOULD-FIX | folded: tags, §3.1, §4.8 |
| Arch S10 no fold table; world_v2 §6 not superseded | SHOULD-FIX | folded: this table, the world_v2 table, §11.2 |
| Arch S13 mode (a) credits only instant effects | SHOULD-FIX | folded: §6.4 (OPEN with a red gate; perceiver-relative credit) |
| Arch S14 tier C holds independent items | SHOULD-FIX | partial: §12.1 Q3 asks whether C2 gates Phase 4; the tier split is roadmap Phase 3's (other fold) |
| X-2 [now] claims false with real Maxim | BLOCKER | folded: §3.1, §4.8, §1 (`context_pool`) |
| X-3 the counts | SHOULD-FIX | folded: §1, §12.3 |
| X-4 `hash()` is not a determinism break | SHOULD-FIX | folded: §1 |
| X-5 CC3 misquoted | SHOULD-FIX | folded: §8.1 |
| X-6 refusal and settle keys never reach dispatch | SHOULD-FIX | folded: §6.4, §8.1 |
| X-9 `Clock` can't give three phases | SHOULD-FIX | folded: §3.2, §8.2 item 3 |
| X-10 M76 vs G4; M72 | SHOULD-FIX | elsewhere: the world-clock draft and roadmap OD-H3 (other fold); this part cites no M76 |
| X-11 step-size test tolerance and plant | SHOULD-FIX | folded: §2.1 |
| X-12 schema, prompt and protected tests | SHOULD-FIX | folded: §3.1 (schema, prompt); boundaries §10 (protected) |
| X-13 additive disagreement; stale note | SHOULD-FIX | folded: §8.1, §12.3 |
| Wire B2 mode (a) can't reach the pipeline | BLOCKER | folded: mode (a) dropped; §6.2 intent sink as a required port *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Wire B3 no Maxim thought entry point | BLOCKER | folded: §6.1, §6.2 *(superseded by `npcs_and_sem.md` O6a and v3.1 §6.6: one host-called port; intents return in `StepOutput`; the gateway is the host's thinking lane)* |
| Wire S1 three time inputs, no invariant | SHOULD-FIX | folded: §9 (the clock advances exactly by stepped dts); the draft's test is elsewhere |
| Wire S3 seed path owner; counter keying | SHOULD-FIX | folded: §3.4 |
| Wire S4 log record lacks fields and kinds | SHOULD-FIX | folded: §4.3, §4.4, §9; boundaries §6.1–§6.2 |
| Wire S5 speech has no wire | SHOULD-FIX | folded: §5.2, §5.3 |
| Wire S6 which frame a pull reads; leaks | SHOULD-FIX | folded: §7.3, §3.1 |
| Wire S7 dilation has no channel | SHOULD-FIX | folded: §5.4; boundaries §6.3 |
| Wire S9 the cache is unregistered; can't hit | SHOULD-FIX | folded: §4.8 |
| Wire S10 stale Phase 3 ids | SHOULD-FIX | folded: §8.1 (ids as at 35b9c3e, updated with any renumbering); §12.2 closes two clocks with S2 and A2 |
| Wire S12 settle double credit | SHOULD-FIX | folded: §6.4 |
| DR-B1 agent code races the tick | BLOCKER | folded: §6.3 |
| DR-B2 the host doesn't own the LLM call | BLOCKER | folded: §6.1 |
| DR-B3 the cache isn't canonical | BLOCKER | folded: §4.8 |
| DR-B5 throughput is the wrong bound | BLOCKER | folded: §4.5 |
| DR-S1 Δt invariance vs bits; crossings | SHOULD-FIX | folded: §2.1 |
| DR-S2 sub-tick units and field | SHOULD-FIX | folded: §9; boundaries §6.2 |
| DR-S3 three ordering keys | SHOULD-FIX | folded: §9, §11.1; boundaries §6.2 |
| DR-S4 Philox stability | SHOULD-FIX | folded: §3.4 |
| DR-S5 agents share module state | SHOULD-FIX | folded: §6.3 (one real agent per process until proven); the exit test is the draft's (other fold) |
| DR-S6 dial-invisibility test can't fail | SHOULD-FIX | folded: §3.1 |
| DR-S7 replay reproduces the world only | SHOULD-FIX | folded in boundaries §6.2–§6.3 (tiers and the rerun manifest) |
| DR-S8 speech is world input; chunking | SHOULD-FIX | folded: §5.2, §5.3 |
| DR-S9 unmeasured budgets | SHOULD-FIX | folded: §4.5, §6.3 meters; boundaries §4.2, §6.2 |
| DR-S10 the agent adapter is unsealed | SHOULD-FIX | folded: §1; boundaries §3 |
| DR-S11 machine-decided failures | SHOULD-FIX | folded: §4.4 |
| TB2-B1 the NPC tool surface | BLOCKER | folded: §6.1 roster, §3.1 prompt test; boundaries §5.3 |
| TB2-B2 one shared home; pickle | BLOCKER | folded: §6.1, §6.3, §12.2 |
| TB2-B3 no thought budget; liveness | BLOCKER | folded: §4.4, §4.7 |
| TB2-S1 speech has no kind or gate | SHOULD-FIX | folded: §5.2 |
| TB2-S2 the log excludes and includes LLM text | SHOULD-FIX | folded: §5.2; boundaries §6.2 (per-kind rule) |
| TB2-S3 the memory-write gate can't exist yet | SHOULD-FIX | folded: §12.2; boundaries §5.3 (gate-to-be) |
| TB2-S4 the cache is an untrusted input | SHOULD-FIX | folded: §4.8 |
| TB2-S5 kind from model output | SHOULD-FIX | folded: §4.2 |
| TB2-S6 who stamps player ticks | SHOULD-FIX | folded: §9, §5.2 |
| TB2-S7 authority misses policy and cancels | SHOULD-FIX | folded: §4.3, §4.4, §4.7 |
| TB2-S8 identity from the object called | SHOULD-FIX | folded: §6.5 |
| TB2-S9 host data before tier A | SHOULD-FIX | partial: §12.1 Q1–Q2 put the guard and disclosure to the owner; closed code vocabulary in boundaries §5.4 |
| BF2-1 the cognitive reserve | BLOCKER | folded: §2.3, §4.6 |
| BF2-2 reply onset vs gap | BLOCKER | folded: §4.2, §5.1 |
| BF2-3 mode (a) emits no D53 valence | SHOULD-FIX | folded: §6.1, §6.4, §8.2 item 5 |
| BF2-4 citation corrections | SHOULD-FIX | folded: §2.3, §3.2, §4.2, §4.6, §9 |
| BF2-5 sleep as gating | SHOULD-FIX | folded: §2.4 |
| BF2-6 two meanings of instrument | SHOULD-FIX | folded: §7.1 |
| BF2-7 no interim time sense; calendar oracles | SHOULD-FIX | folded: §3.2, §3.1, §12.2 |
| BF2-8 hardware still decides competence | SHOULD-FIX | folded: §1, §4.1 |
| BF2-9 O4 vs §4.6 on sleep pressure | SHOULD-FIX | folded: §2.3 (owner answer OA5: fatigue feeds sleep pressure, marked) |
| MP-B1 no front gate | BLOCKER | partial here: §6.1 names the existing pieces; the survey itself is the drafts' (other fold) |
| MP-B2 oscillator breaks "robots unchanged" | BLOCKER | folded: §3.3 (tier B) |
| MP-B3 CC3 misread | BLOCKER | folded: §8.1 |
| MP-S5 decisions argued against unnamed | SHOULD-FIX | folded for this part: §3.3 names the ANALOG row and #1361 §(g); G4, G17 and M72 are the drafts' |
| MP-S9 experiment ids; BF2 floors | SHOULD-FIX | folded: §10 |
| MP-S12 the injected actor key isn't additive | SHOULD-FIX | folded: §6.5 |
| MP-S13 the owner decision recorded only here | SHOULD-FIX | folded: §8.2 (recorded in Maxim's `DECISIONS.md` by the plan PR) |
| MP-S14 stale tree; two trees' lines | SHOULD-FIX | partial: this part reads `origin/main` 7084f561; line numbers carried from the audit (1.3.3) are not all re-checked |

Findings in the foundations review that touch neither this part nor boundaries (the world-clock draft's PR plan,
fence, tripwire mechanism and exit tests; the SEM plan's venue, format and precedents; roadmap tiering): Wire B4,
Wire S2, X-7, X-8, DR-S12, MP-S1 to MP-S4, MP-S6 to MP-S8, MP-S10, MP-S11. They are the upstream drafts' fold. (X-1's
tripwire mechanism is also folded into `boundaries.md` §3.)
