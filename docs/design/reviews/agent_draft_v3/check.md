# Pre-send check: `embeddable_agent_DRAFT.md` v3 (dbf816b)

Checked against Maxim `origin/main` 6fee7377 (read with `git show` / `git grep` only) and Overdrive's
`npcs_and_sem.md` §0 and §6, `roadmap.md` Phase 3 tier A, `boundaries.md`, `reviews/maxim_response_1/`.

**Counts:** 0 BLOCKER, 6 SHOULD-FIX, 9 NIT.

## Citations checked (all hold on 6fee7377 unless listed below)

`agent_loop.py:3089-3093` (3 cycles with a percept source, else 2) and `llm.deliberation_max_cycles`
(`config_loader.py:139`); `llm_worker.py:1322-1339` (fallback on an unparsed reply); `llm_fallback.py:395-400` (the
`'{question}'` echo); `llm_fallback.py::generate_simple_answer` `:290`; `loop_controller.py:157`
(`llm_submit_interval`); `prompt_builder.py:1102-1137`, `:1125-1127`; `bootstrap.py:623` (`llm=llm` at `:630`) →
`adaptive_planner.py:487`; `tool_pain_bridge.py:806` (error logged at debug, `None` returned); `fear_agent.py:303`,
`:317`; `input_handlers.py:202`, `:274-312` (inside `_handle_phrase_text`); `experience_time.py:36`; `seeding.py:121`
and the A2 derivation string; `tool_dispatch.py:1343`, `:626`, `:1516`; `nac.py:3629`; `bio_stack.py:654`;
`LLMRouter._complete_text_abandonable` (`models/language/router.py:998`); `utils/cancellation`; `cli_utils.py::_GLOBAL_PATHS`;
`MAXIM_DATA_HOME`; `scripts/lint_dead_imports.py` (#1436); `1305.owned-rng`; #1150 in the length baseline; D53; #984.
Plans: candidates A1–A6, B1–B3, C1, §Order, §Not decided; #1361 Q1 (exact quote), §(c), §(g) ("host calendar by
design"), S3a–S6, G2b; M72; `bounded_stop.md` title; HANDLE's `consolidation: "full" | "lightweight"` and
`maxim_ui.md`'s "embodied + headless flavors". τ arithmetic: today τ_eff 9.49 passes, 4.75 s after S3a, so 5×
at 10 Hz and 15× at 30 Hz, correct. Maxim's 2026-11-19 answer (`response_4.md`): timing and the front gate are
represented accurately.

No citation is wrong. Drift: none on line numbers. The candidates doc cites `_complete_text_abandonable` at `:985`
(98c6889c); the draft's `:998` is right for 6fee7377.

## SHOULD-FIX

**AD-S1 (header, "For a reader…", §1, §7 closing line). Overdrive references can't be followed cold.** `npcs_and_sem.md`
§6, `roadmap.md` Phase 3, `reviews/maxim_response_1/`, `tool_failure_credit.md`'s OD-A16 amendment and
`decisions_entry_DRAFT.md` are named with no repo, branch or commit. Maxim's candidates doc points at
`phase1/design-v2` (PR #4); this draft sits on `phase1/agent-draft`. Fix: one line giving
`dennys246/Maxim-Overdrive`, the branch and the commit the paths resolve on.

**AD-S2 (§3 shortcut bullet; §7 Q5). The shortcut's premise is overstated.** The draft says it "answers any
`triggering_input` without the model" and, in Q5, answers any input "with a canned reply rendering the host's
clock". It *fires* on any `triggering_input`, but `generate_simple_answer` answers only short time, date, identity and
greeting questions (A4's own wording, and `:290`'s docstring). It also skips requests that carry held inputs (`:1129-1131`,
#1451). Fix: "it fires on any `triggering_input`, a relayed stranger's line included, and answers time, date,
identity and greeting questions past the model, the time and date ones from the host clock". The ask still holds.

**AD-S3 (§4 OD-A20). Doesn't say Maxim already took this on, and the ask isn't in §7.** In `response_3.md`
Maxim said it would raise the anchor-similarity read as a question on #1361. #1361 still reads "host calendar by
design" in §(g). The draft states the ask as an instruction ("Read it from the perceived-time port") and has no §7
question for it, which breaks CLAUDE.md's "Search Maxim before proposing to it" and the header's rule that §7 asks.
Also, A3 keeps the perceived-time port for what prompts render and gives temporal windows to #1361, so a credit
computation reading the port crosses A3's own split. Fix: add a §7 question: "You said you'd raise this on
#1361 (`response_3.md`). Is it there yet, and does the read belong on the port (A3) or on the machinery clock
(#1361 §(g))?"

**AD-S4 (§7 Q9, Q10). HANDLE has shipped, and Q9 cites only plans.** `console/handle.py::MaximHandle` (`:131`) is
the headless flavor, with `stop(consolidation="full" | "lightweight", deadline=)` (`:704`). `bounded_stop.md`'s
as-built text (#1536) already bounds a per-handle stop's consolidation by its deadline. Citing the deferred plan
suggests we haven't read the code. Fix: cite `MaximHandle` and `MaximHandle.stop`, and merge Q9 and Q10 into one
question: "Should `save()` take `MaximHandle.stop`'s contract (consolidation flavor plus caller deadline)?"

**AD-S5 (§5 first paragraph). Our condition is presented as Maxim's order.** "Your §Order governs: … `AgentHome`
with A1 and #984, after #1685" is not in the candidates §Order. There, A1 runs in step 1 in parallel with #984,
and A4 is step 3. "After #1685" is Overdrive's condition (roadmap OD-I3: the pickle load becomes reachable from
saves). The list is also not in Maxim's order. Fix: list the items in §Order's sequence, and mark "after #1685" as
"(our condition, OD-I3)".

**AD-S6 (§7 Q1, Q2). Two half-questions that the candidates doc already answers.** Q1's first half: A1's guard
already reads "`_GLOBAL_PATHS` becomes the checked registry", and its filesystem-trace test is OD-EA2 (your own §6 table
says so). Q2's `base_seed` half: A2 already says "a host supplies its own". Asking again reads as not having read
the doc. Fix: state both as agreed ("A1 makes `_GLOBAL_PATHS` the checked registry; OD-EA2 runs over it"), and ask
only about the ConceptExtractor thread's owner and the `agent_id` key.

## NIT

- **AD-N1 (header).** "Citations are `file::symbol`… the symbol is the citation", but most citations have no symbol
  (`agent_loop.py:3089-3093`, `llm_worker.py:1322-1339`, `input_handlers.py:202`, `tool_dispatch.py:1343`,
  `:1516`…). Add the symbols (`_handle_phrase_text`, `execute_and_learn`, `LLMWorker._process_request`), or soften the rule.
- **AD-N2 (§7 Q8).** `router.py:998` should be `models/language/router.py`.
- **AD-N3 ("Ids.", table).** The dependency list says OD-A2 to OD-A8, but §5 needs OD-A9 (O29: OD-A2 to OD-A11). OD-A21
  is listed as a dependency but is "not blocking" in §4 and §5. OD-A5, A6 and A8 to A9 map to no candidate in the table.
- **AD-N4 (throughout).** Terms that are Overdrive's own and left unglossed: O26, O28, O29, O35, O36 (one gloss line:
  "Overdrive owner decisions"), "rate divisors" (OD-EA12), "log root", "guest", "frame", "our erratum" (name
  `erratum_1.md`).
- **AD-N5 (§3, last bullet).** A4's embedded roster has "no env reads". The draft's "exactly one read,
  `MAXIM_DATA_HOME`" differs from it, and §7 doesn't ask (the header says §7 asks about every difference). Add a clause to Q6
  or Q1.
- **AD-N6 (table, OD-A14/A15 row).** The candidates doc's B1 heading claims "Overdrive's OD-A10–A15", while the draft maps
  OD-A10/A11 to A4 and OD-A12 to A1. Say so in one line so Maxim can correct its heading.
- **AD-N7 (§5 vs §7 Q7).** §5 puts `environment.step` "out of dispatch for a host that owns the step", which is the answer
  Q7 then asks for. Phrase §5 as "(Q7)".
- **AD-N8 (§4 OD-A21).** "A 10–30 Hz robot" has no source. Cite the loop rate, or mark it *to verify*.
- **AD-N9 (§2 OD-H6).** Say it is not C3: C3 is the behavioural change to `llm_submit_interval`, and OD-H6 only notes that a host-called
  `think` bypasses it. Also: "`load` refuses … rather than refusing the save" reads as both refusing and not refusing. The
  checklist wording is clearer ("loads as a logged `thought_failed(reloaded)`, never a refused save").

## Consistency with Overdrive's decisions

The draft is consistent with O6/O6a (the port and the cut), O13 (spawned worker, allowlist, latch, gateway in the host), O15a
(stepped `think` after 1.4.0), O19/O36 (frozen, with a reopen trigger), O26 (recorded replies, redaction boundary), O28 (guests
Phase 5+), O29 (the subset matches the roadmap paragraph word for word in substance; the roadmap's "plus OD-B1 to OD-B7
for Exp 64a" is omitted, which is fine for this audience), O35/O37 (the bridge NPC claims nothing), §6.6 (header/body split,
staleness vocabulary, budgets per input and per minute, model doors, parse failure), §6.6's substream erratum
(A2 on OD-A7's conditions) and `boundaries.md` (planted `BashTool`, `MAXIM_DATA_HOME` as the single interim read). I found no
contradiction. One rule the draft leaves out: §6.6's "`think` resumes only at the modelled landing tick" (the header
carries the landing time, but the rule is never stated). It is the host's rule, so this is optional.

## Security

The draft names OD-I5 only and describes no mechanism. It contains no keys, personal details or private paths. The
references it sends the reader to (`npcs_and_sem.md` §6, `maxim_response_1/`) carry only redacted mentions.

**Outside the draft, for the owner:** Maxim's own `docs/plans/overdrive_refactor_candidates.md` on `origin/main`
(§"Filed alongside this list", the advisory bullet) describes the advisory's mechanism and its proof inputs. If that
repo is public, the advisory's details are public on Maxim's side. Tell Maxim privately, not in this draft.

## Verdict

**Not ready to send as is.** There are no blockers. Fix AD-S1 to AD-S6, all edits of one to three lines, and then it is ready.
