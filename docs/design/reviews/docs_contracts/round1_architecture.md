# Round 1, Architecture lens: phase1/docs-contracts

Reviewer: Architecture (independent, read-only). Diff: `git diff 5c054f6..HEAD` (HEAD c043920). Charter:
`docs/code_review.md`. Probes were run against the real tree by importing `scripts/lint_contracts.py` and calling
`check_contracts` on the tracked `docs/**/*.md` with one planted block appended to `docs/design/fire_model.md` (or a
plan). On the unmodified tree the result is `[]`. The probe scripts live only in the session scratchpad. Every claim
below was checked against the file at HEAD.

Findings come most severe first. A proposed fix is marked **unverified** unless it says otherwise.

---

## A1. BLOCKER: `scripts/lint_contracts.py::blocks` / `restatements`: a bulleted copy of a vocabulary is invisible by design, and B36 is marked done for enumerations

**Failure scenario.** A plan or design restates the `thought_failed` reasons in the usual Markdown form, one reason
per bullet (`- \`budget\`: …`, `- \`timeout\`: …`, five items). `blocks` makes each top-level list item its own
block, so no single block reaches `min(3, n)`, and the lint passes. Someone later edits the reasons in IP §2.6 and
the bulleted copy goes stale. That is the PR #27 failure the lint was built to catch.

**Evidence.**
- Probe: five `thought_failed` reasons as five bullets gave 0 findings. The same five inline in one sentence gave 1.
  Two short paragraphs holding two reasons each also gave 0.
- `tests/test_lint_contracts.py::test_members_in_neighbouring_list_items_are_references` pins this behaviour as
  intended.
- The owner side is asymmetric. `list_run` ("a list defines as a whole") merges consecutive items into the owner's
  block, and `test_a_marked_list_defines_as_a_whole` holds that. The same shape counts as a definition in the owner
  section and as a set of references everywhere else.
- No reader-facing text states the weakening. The module docstring says "Any other block in scope that holds at
  least `min(3, n)` distinct members restates it". `docs/design/contracts.md` lists its limits, but this isn't one of
  them. `docs/standards_backlog.md` B36 now reads "**done** for enumerations", and CLAUDE.md's guard names
  `check_contracts` for "the registered vocabularies".
- So "done" is false for the most common enumeration shape, and the hole is recorded only in a test name. Under the
  brutal-honesty rule, that claim has to be corrected or the hole closed before hand-off.

## A2. BLOCKER: `scripts/lint_contracts.py::resolve` and the markers: the marker's member list is a hand-kept second copy of the vocabulary, already drifted, which reintroduces split ownership inside the owner section

**Failure scenario.** Someone adds a field or code to an owner table, or a copy elsewhere lists the members the
marker leaves out. The lint checks only that marker ⊆ block, never that block ⊆ marker, so neither change is seen.
The docstring claims "so the marker can't drift from the text". That holds in one direction only.

**Evidence** (probe: `members(block)` against the marker's names, for every registered contract).
- `refusal.codes`: the §3.4 table holds `busy` and the marker doesn't. It drifted on the day it was written.
- `intent_record.fields`: the marker names `schema_version issued_tick params target invocation`. The core of the
  record (`kind`, `actor_id`, `seq`, `observed_tick`, `apply_tick`, `apply_us`) isn't in it. A copy of the six fields
  that most need one owner passes unseen.
- `record.kinds`: the marker names only the six host-record kinds. `intent`, `control`, `join` and `leave` are left
  out, though contracts.md justifies leaving out only words "other vocabularies share" (`imagine`, `speak`).
- The fallback inference (`members`, the table, list and paragraph parsing) gets 10 of the 12 owner blocks wrong. It
  picks up `kindle`, `move_to`, `dir`, `5500.0` and `1e3` as refusal codes, and file paths and YAML keys as intent
  kinds. Since every marker names its members, `members` never runs on the shipped path. It is capability with no
  caller, and the module docstring describes it as the primary mechanism.
- So the actual design is "a contract is whatever its marker lists". That makes the marker a second statement of
  each vocabulary in the same section, which is the duplicated-copy failure B36 exists to remove. The workaround
  hides the inference's imprecision; the root cause is still there.

## A3. SHOULD-FIX: `docs/design/contracts.md` "Restates at" column and `lint_contracts.py::restatements`: thresholds tuned on the tree after the first run are a loosened tolerance, and the lint's own docstring still states the old rule

**Failure scenario.** A plan copies the six stage-1 refusal codes (`bad_json` … `outside_extent`), or four of the six
intent kinds. With counts of 8 and 5, both pass.
- Probe: seven refusal codes in one sentence gave 0 findings, and so did four intent kinds.
- The plan (§6) specified `≥ min(3, n)`, with the test "three members, where two pass". The commit message says the
  counts were "set after the first run, just above the blocks flagged as references".
- That is a bar chosen after the measurement so that today's tree passes, which the standards call a loosened
  tolerance. It never went to the owner for a ruling: rulings.md doesn't mention it.

**Stated where?** In contracts.md and B36, yes. In `lint_contracts.py`'s docstring, no. The docstring still documents
a three-column row (`| name | path §N | kind |`) and `min(3, n)`, while `ROW` requires five columns and the code uses
`c.threshold`. Anyone reading the code learns the wrong rule.

## A4. SHOULD-FIX: `lint_contracts.py::check_contracts` (`owners`): every contract's owner block is exempt from every other contract's check

**Failure scenario.** An owner block of contract X restates contract Y in full, and nothing flags it.
- `owners` is the union of all owner blocks' lines, and `restatements` skips any block in that set, whatever the
  contract.
- On the real tree, the `client.messages` owner table (tile §3.3, line 223) holds four `server.messages` members,
  `welcome`, `intent_result`, `time_decision` and `error`. That is exactly that row's count of 4, and it is exempt
  only because the table owns a different contract.
- The `ordering.key` owner bullet (boundaries §6.2, line 442) restates four of the six intent kinds as the
  `kind_rank` list. When T §3.2 gains a kind, that list goes stale without a finding.
- contracts.md states the exemption ("An owner block may name another contract's members"), but as a blanket rule
  rather than per contract. The exemption needs to be scoped to the block's own contract, or each cross-reference
  justified per pair (**unverified**).

## A5. SHOULD-FIX: `lint_contracts.py::in_scope` / `SUPERSEDED`: one blockquote line removes a whole live document from the check

**Failure scenario.** A live design marks one section as superseded with a line starting `> **Superseded in part`, as
`realtime_lanes_coop.md:179` does. `SUPERSEDED` is searched `re.M` over the whole file, so every restatement in that
file stops being checked.

**Evidence.**
- Probe: adding `> **Superseded in part.** x` and three `thought_failed` reasons to `fire_model.md` gave 0
  findings. The reasons alone gave 1.
- The docstring says only "a design marked superseded (a line starting `> **Superseded`)". It doesn't say that a
  partial banner anywhere in the file counts. The exemption should key on a document-level banner near the top
  (**unverified**).

## A6. SHOULD-FIX: `docs/design/world_v2.md` and `world_model.md` §2, §8: a document called a record still owns live contracts, and the plan's banner step was dropped silently

**Failure scenario.** A reader follows WM §2's "v2 §2.1 stands" or §8's "v2 §8 stands" into `world_v2.md`, whose
status still reads "DRAFT, for a design review". WM's own line 11 calls it a record. If the planned banner is ever
added, the lint drops `world_v2.md` from scope while WM still names it as live text. The contracts in v2 §2.1, §2.2,
§2.4 and §8 then have an owner the lint can't see.

**Evidence.**
- Plan §1 item 3 lists this as a root-cause finding.
- Plan §5 says "`world_v2.md` gains the banner". `world_v2.md` is untouched in the diff, and neither moves file
  records the step as skipped.
- Also, `ip_and_licensing.md` §4 (line 56) still cites `realtime_lanes_coop.md` §5 for the loopback bind and tokens.
  Row 16 moved those to `boundaries.md` §5.3, and IL is not in row 16's list of copies made links.

## A7. SHOULD-FIX: `docs/design/decisions/*.md` (Status column): the decisions pattern can't record a later ruling, so it already reports overruled decisions as `live`

**Failure scenario.** A reader checks a decision's status in its record and builds on a ruling the owner has
replaced.
- `decisions/boundaries.md` O24 ("Three or four layers") is `live`, but ruling 49 fixes five layers as built.
- O8 ("Only the applier and the physics laws hold the write handle") is `live`, but ruling 50 names four window
  owners as built.
- `decisions/npcs_and_sem.md` O11a is `live`, but ruling 41 says "O11a stays a record", and the moved text in N §4.4
  says §6.6's thresholds "supersede O11a's".
- `foundations_plan.md` keeps "O24 | Three or four layers", and check_plan requires it.

**Cause.** Two pieces of the pattern conflict, so the pattern is not yet sound as one rule for every design:
- The header rule says "Status comes only from supersessions and amendments the rulings state", and "a new ruling is
  a new row".
- The owner's 2026-11-21 rulings live in `reviews/docs_contracts/rulings.md`, a review record, and no row was added
  for them in any `decisions/` file.

**Also in the pattern.**
- **Duplicate rows.** One ruling now has two records in different words: O3, O4, O5, O6, O7 and O7a in both
  boundaries and npcs; T1 and T2 in both tile and client; D20 and O31 in three. The plan's §1.2 named this exact
  root cause ("O4, O6 and O13 each sit in two §0 tables, in different words"). The move carried it over verbatim and
  labelled it "also in".
- **Owner section mostly empty.** Plan §4 says it is "filled in for B, which lacks one". In `decisions/boundaries.md`,
  15 of 20 rows read `—` and the other 5 read "cites …, not necessarily its owner". In `decisions/sem_stimuli.md`, 15
  of 20 read `—`. So a ruling-only contract has no pointer to an owner.
- **CLAUDE.md disagrees on location.** CLAUDE.md ("One owner per contract") says decision tables "are kept in
  `docs/design/reviews/` and indexes". The branch created `docs/design/decisions/`.

## A8. SHOULD-FIX: `tile_and_client.md` §3.2 against `boundaries.md` §6.1: a contradiction made by the union and not surfaced

**Failure scenario.** A replay or log writer reads B §6.1 and logs `imagine` as its own record kind. A stage-1 parser
reads T §3.2 and treats `imagine` as an intent kind. The two disagree on what an `imagine` record is.

**Evidence.**
- At 5c054f6, T §3.2 said only that vocabulary v1 "adds `kindle` … and retires `ignite`". The full kind list
  including `imagine` was assembled in this branch "from T §3.1 and §3.3" (moves.md row 1).
- B §6.1's record table now has `intent` ("the kinds of `tile_and_client.md` §3.2") and a separate `imagine` row.
  Before, its intent row was "strike, ignite, douse, …", without `imagine`.
- The `record.kinds` marker leaves out `imagine` as "shared". That suggests the overlap was noticed.
- It isn't listed as a contradiction for the owner in rulings.md "Not decided" or in moves.md.

## A9. SHOULD-FIX: `boundaries.md` §4.3 and `npcs_and_sem.md` §7.2: a contract claim was deleted without a ruling

**Failure scenario.** Step 5's log writer has no statement on whether a `BoundFrame` push needs a log record. Before
this branch, two sections said it needed none. After it, neither says anything, and SS §6.1 and §4.4 are silent too.
- The diff removes "(so it needs no log record)" from both sections.
- moves_3d_3e.md records it as "Open … The claim was dropped with the pinned frame and not restated", but rulings.md
  "Not decided" doesn't list it.
- The owner asked for moves that don't rewrite meaning, and for contradictions to come to them. A dropped rule is a
  change of meaning, and it should be on the owner's list, not only in a moves table.

## A10. SHOULD-FIX: `reviews/docs_contracts/rulings.md`, ✗-rows table row 79 against "Not decided": the record contradicts itself

**Failure scenario.** A reader takes row 79 as ruled ("`crack` keeps one meaning; the bed's second meaning is
dropped") and edits C §4.2 or tile §5.5 to match. "Not decided" in the same file says rows 10 and 79 wait on #31.
moves.md confirms that row 79's edit "was reverted on review". The ruled row needs a pointer to its suspension, or
it should move to "Not decided" (**unverified** wording).

## A11. SHOULD-FIX: CLAUDE.md ("Rules that matter here", the thin-feature line) against `world_model.md` §1.1: the standing rule now contradicts its owner

**Failure scenario.** A reviewer applies CLAUDE.md's "Thin features must be at least two cells of the coarsest
verification grid (0.2 m) thick" to a fuel object, such as a 1 cm stick, and blocks a correct design.
- Ruling 72 exempts fuel objects, and moves_3d_3e row 72 copied FM §10.1's exemption into WM §1.1.
- CLAUDE.md is out of the lint's scope and was edited on this branch only for the guard line.
- The plan's "CLAUDE.md stays untouched" stops a fix, so this is a contradiction for the owner, the same class as
  the handshake line rulings.md already lists. It isn't on that list.

## A12. SHOULD-FIX: the change to the word-budget rule is recorded only in a commit message

**Failure scenario.** A later word count includes the markers and finds a design over its 5c054f6 ceiling, or one
excludes them and another doesn't, so two counts of the same document disagree.
- c043920's message says "Marker lines don't count toward a design's word budget".
- O22 and CLAUDE.md ("Documents have a word budget") have no such exception, and no ruling grants one.
- contracts.md, B24 and moves.md don't say it.
- The `refusal.codes` marker alone is 21 words. Adding an exemption to an owner-set budget is a rule change, and it
  needs the owner and a recorded home.

## A13. NIT: `lint_contracts.py::structural`: fold and decision detection keys on exact headings

- `FOLD` matches only a heading beginning "Fold table". The decision check matches only a header whose second cell
  starts "Decision" or "Ruling".
- Probes: "## Review fold" over a `| Finding | Status |` table gave 0 findings, and a `| Id | What | When |` table
  of `O99` rows gave 0.
- The plan said "first-column cells matching the decision-id patterns". The SS §10 and FM §11 tables that this
  branch moved didn't use the "Decision" header either.

## A14. NIT: `lint_contracts.py::markers` scans every `docs/**/*.md`, records included

A review report or moves file that quotes a marker on a line of its own (not inside a code span) creates a duplicate
or orphan marker. The lint then fails the tree from a record, though records are declared out of scope. Scope
marker discovery as `in_scope` does, plus the registry's owner paths (**unverified**).

## A15. NIT: `reviews/docs_contracts/moves.md` §3b and §3c

The step 3b and 3c sections say "uncommitted on this branch until the owner commits". They are committed (94881a5,
ca71f92).

---

## What was checked and holds

- **`scripts/check_plan.py`.** The check is whole.
  - The five decision records join `ID_SOURCES`, and the D and T patterns follow them through `WORLD_DOCS` and
    `TILE_DOCS`.
  - `test_the_required_ids_never_shrink` holds the tree to the 5c054f6 floor, which is 168 ids after the documented
    drop of OD-EA9.
  - The decision records of IP, SS and FM aren't sources, but their designs weren't sources before either, so
    nothing is lost.
  - The OD-EA9 drop and the roadmap/plan disagreement over OD-EA6 and OD-EA9 are correctly routed to the owner.
- **Module fit.** `lint_contracts.py` is 271 lines, with no function near 40 code lines and one job. Its
  `check_contracts(files)` signature and its wiring in `lint_standards.py` (the `designs` guard and note line) match
  `check_inputs` and `check_gates`. `resolve` both validates and selects members, which is borderline but within one
  concern.
- **Rows checked against their owner.** fire_model §3.1's link to FS §4.2 is consistent: FS §4.2 drops the threshold
  law. The region-membership move to FS §1.3, the 3a wire rows and the handshake copy in B §5.3 (verbatim from RL §5)
  also hold.
- **Word ceilings.** All designs are under their 5c054f6 ceilings. The plan is 2,363 words, and every review record
  here is under 3,000.

## Counts

| Severity | Count |
|---|---|
| BLOCKER | 2 (A1, A2) |
| SHOULD-FIX | 10 (A3–A12) |
| NIT | 3 (A13–A15) |
