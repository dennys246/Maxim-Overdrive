# Docs-contracts plan: one owner per contract (B36)

**Status:** awaiting the owner's sign-off. Branch `phase1/docs-contracts` from `origin/main`
dc0e1aa. Evidence: five reports in `docs/design/reviews/docs_contracts/inventory_*.md`, written by read-only readers
at dc0e1aa. The author re-read each headline contradiction. Ids such as W3, L8, A6, P2 and X1 are item
numbers in those reports (Wire, Log, Agents, Packaging, World).

## 1. What the inventory found, said plainly

1. **Most copies disagree.** Of 80 contracts stated more than once, 13 have copies that agree. Collapsing
   differing copies *chooses a meaning*, so "move text; don't rewrite meaning" needs a ruling for those (§3).
2. **The root cause is supersession by name.** A later design says it supersedes an earlier section (SS §6.2 on
   receipts, FS §5.6 on channels, FM §10.1 on the tile), but the earlier text is never edited. A second cause:
   decision rows restate contracts. O4, O6 and O13 each sit in two §0 tables, in different words.
3. **Superseded designs still own live contracts.** `realtime_lanes_coop.md` alone holds the handshake (§5), world
   config (§2.2) and the `seq` range. `world_v2.md` has **no superseded banner**, and WM §8 says "v2 §8 stands".
4. **No owner at all:** save v0 (L3, six versions, one a plan overriding a design), world config (L12), and the core
   refusal list FS §5.3 appends to.
5. **`fire_model.md` is "the direction, not the build spec"**, yet its §10.1 is treated as revising the tile.

## 2. Inventory: contract → proposed owner

Abbreviations: B boundaries, N npcs_and_sem, IP inference_placement, IG inference_gateway, SS sem_stimuli, T
tile_and_client, C client_rendering, WM world_model, V2 world_v2, RL realtime_lanes_coop, FM fire_model, FS
fire_solid, VH verify_harness, IL ip_and_licensing, AR architecture, RM roadmap, CL checklists, FP foundations_plan,
LT long_term_features. Kind: **=** copies agree; **∪** copies add to each other without conflict; **S** a later text
supersedes by name; **✗** a conflict (§3).

| # | Contract | Owner | Kind (report ids) |
|---|---|---|---|---|
| 1 | Intent kinds, vocabulary v1 | T §3.2 | S (W2) |
| 2 | `kind_rank` values | B §6.2 | ✗ (W3) |
| 3 | Ordering key | B §6.2 | S (W4, L7) |
| 4 | Intent record fields | B §6.2 | ∪ `invocation` (L6) |
| 5 | Record kinds | B §6.1 | ∪ (L13) |
| 6 | Agent receipt | SS §6.2 | ✗ (W1, A6) |
| 7 | Wire `intent_result` | T §3.3 | ✗ with 6 |
| 8 | `kindle` target, pilot deposit | ruling | ✗ (W5, X12) |
| 9 | Refusal codes, check order | T §3.4 | no core owner (W) |
| 10 | Snapshot channels | C §4.2 | ✗ (W6, X5) |
| 11 | Frame header, catalogue, bump rules | C §4.1 | ∪ (W9) |
| 12 | `welcome` fields | C §4.1 | ∪ (W10) |
| 13 | Messages per step | C §4.1, T §3.3 | S (W11) |
| 14 | Frame bytes per cell | C §4.2 | S (W7) |
| 15 | Buffer caps | C §4.3 | S (W8, P8) |
| 16 | Handshake: token, `Origin`, loopback, `hello` once | B §5.3 | = |
| 17 | Strict JSON, 2⁵³ | B §9.1 | = |
| 18 | Two-stage validation | B §5.3 | ✗ caps' home (P7) |
| 19 | Frame publication, snapshot cadence | T §4; C §4.1 | ∪ (X17) |
| 20 | Log header | B §6.3 | ∪ (L8) |
| 21 | Determinism tiers | B §6.3 | S (L5) |
| 22 | Rerun manifest | B §6.3; items IP §4.3 | ✗ refuse rule (L9) |
| 23 | Keyed streams | N §3.4 | ∪ O40 (L10) |
| 24 | Timing units at load | N §9 | ✗ (L11) |
| 25 | World config | none (RL §2.2) | no owner (L12) |
| 26 | Save v0 | none | no owner, ✗ (L3) |
| 27 | Fuel save tables | FS §5.5 | S (L4) |
| 28 | Scene format and versions | T §1.3 | ✗ (L1, L2, X11) |
| 29 | Version rules F1, F15 | WM §8 | ∪ (L20) |
| 30 | `session_id` and pids | N §6.6 | = (L14) |
| 31 | Thought request id, authority | B §6.1 | S (L16) |
| 32 | Tick order | SS §4.1 | S (L18) |
| 33 | Tripwire scope | B §3 | S (L19, P4) |
| 34 | `AgentPort` signature | N §6.6 | S (A1) |
| 35 | Agent lane, barrier | N §6.3 | ∪ `consolidate` (A2) |
| 36 | "Gateway" | IG §2 | S (A3) |
| 37 | Worker environment and `HOME` | N §6.6 | ✗ (A4) |
| 38 | `agent_failed` reasons, lifecycle records | N §6.6 | ∪ `build` (A5) |
| 39 | Phase 3 rows (OD ids) | RM Phase 3 | S (A7, P9) |
| 40 | Three clocks | N §1 | ∪ (A8) |
| 41 | Latency policies, floor thresholds | N §4.4 | ✗ (A9) |
| 42 | Thought budgets | N §4.7 | ∪ (A10) |
| 43 | Model request, priority | IP §2.1, §4.2 | ✗ (A11) |
| 44 | Response cache leftovers | IP §4.2 | = (A12) |
| 45 | Guest-session gates | RM Phase 4 | ✗ wording (A13) |
| 46 | Guest-text character list | N §6.6 | ∪ (A14) |
| 47 | Consent and taint | IG §6 | = |
| 48 | Worker codec | N §6.6 | = (P) |
| 49 | Package layers | B §2.2 | ✗ as built (P1) |
| 50 | Write-window owners | B §4.1 | ✗ (P2) |
| 51 | Core banned list (`logging`) | B §3 | ✗ (P3) |
| 52 | Who imports `maxim` | B §8.1 | ∪ (P5) |
| 53 | Where the gates are | B §5.3 | S (P6) |
| 54 | Gate contract | B §5.4 | = |
| 55 | Experiment harness's home | B §8.4 | ✗ (P11) |
| 56 | Content and licence | B §8.2 | ∪ (P) |
| 57 | Golden method | C §6 | S (P10) |
| 58 | Requirements by step | CL | = (P) |
| 59 | Phase 1 exit | RM Phase 1 | S, owner 2026-11-20 (X1) |
| 60 | Band gate | WM §3 | ✗ (X2) |
| 61 | Convergence predicate | VH §4 | ✗ (X3) |
| 62 | Material files and split | FS §5.1 | S (X4) |
| 63 | Energy ledger lines | FM §9.2 | ✗ (X6) |
| 64 | Object–grid coupling | FS §1.1, §3.1 | S (X7) |
| 65 | Pyrolysis rate law | FS §4.2 | S (X8) |
| 66 | Extinction | FM §4.3 | ✗ (X9) |
| 67 | R0 and R1 grading | FS §4.5–§4.6 | S (X10) |
| 68 | Radiation to receivers | FM §4.4; SS §2.3 | ✗ (X13) |
| 69 | Body model, core temperature, tags | SS §3.1, §2.2 | S (X14, X15) |
| 70 | Push path into bodies | SS §4.4 | S (X16) |
| 71 | Region ownership, PR 1 gaps | WM §5 | ✗ (X20) |
| 72 | Thin-feature rule | WM §1.1 | ✗ (X21) |
| 73 | Heat state, ledger tolerance, field registry | WM §4; B §9.1 | S (X23) |
| 74 | B-13, lab-only region sensors | B §4.4 | = |
| 75 | Stimulus split, leak tests | SS §1 | = |
| 76 | `world_set_axis` | SS §4.4 | = |
| 77 | Tick 0.1 s, physics every 5 | T §6.1 (T3) | = |
| 78 | Reconstruct, decide, integrate | WM §3 | = |
| 79 | `crack`'s second meaning | C §4.2 | ✗ (W6) |
| 80 | `thought_failed`, `truncated` reasons | IP §2.6 | done by PR #27; gaps A |

Stale text that no owner holds (X22, and the modulator path in P6) is changed to links.

## 3. Rulings

The owner agreed to the recommendations on 2026-11-21. `reviews/docs_contracts/rulings.md` records the tiebreakers
and each ✗ row's ruling. Row 28 was settled from #32's merged code. CLAUDE.md stays untouched.

## 4. Fold and decision tables

**Fold tables** move verbatim, leaving a one-line pointer. They follow the numbered sections, so nothing
renumbers:
- B "v1 review" (1,158 words) → `reviews/boundaries/fold.md`;
- B and N "foundations review" (1,223 and 1,433) → `reviews/foundations_v1/fold_<doc>.md`;
- N "world_v2 findings" (348) → `reviews/world_v2/fold_npcs_and_sem.md`;
- N "last two rounds" (2,912) → `reviews/npcs_v3/fold.md`;
- WM (497) → `reviews/world_model/fold.md`.

`reviews/npcs_v3/foldtable.py` writes into `npcs_and_sem.md`, so a rerun would put the table back. **Proposed:**
retarget it, since it is a tool, not a lens report. Otherwise it stays a record and the lint fails a rerun.

**One pattern for decision tables.** A decision is a dated ruling, a record. A contract is live text. So:
- Every design's decisions move verbatim to `docs/design/decisions/<doc>.md`, as one table:
  `| Id | Ruling | Who, date | Owner section | Status |`.
  - Owner section comes from the existing "Where" column, and is filled in for B, which lacks one.
  - Status is `live`, `amended by Ox` or `superseded by Ox`, taken only from existing text.
- The design keeps its `## 0` heading, with the ids and a link.
- Contract text found only in a ruling is copied to its owner section.
- This covers B, N, WM, T, C, IP, SS §10, FM §11 and IL §1.
- Plans (VS §1) keep their lists. **Owner to confirm.**

**`check_plan.py`:**
- `ID_SOURCES` gains the decision files of its six documents, and the D and T patterns follow them.
- A new test checks that the required id set at dc0e1aa equals the set after the move, and goes red if a decision
  file is dropped.
- **OD-EA9 appears only in a fold table.** Proposed: add it to the roadmap row for `embeddable_agent_DRAFT.md`.
- The open-question headings don't move.

## 5. References and section numbers

Review records cite design sections more than 600 times. Four scripts cite C §6.2, §6.5, §7.3 and §12.
- **No renumbering.** A moved section keeps its heading and gains a pointer line. New text joins an existing section,
  or a new last subsection.
- **`reviews/docs_contracts/moves.md`** maps each old location at dc0e1aa to its owner, with the commit. Records are
  never edited, and `git show dc0e1aa:<path>` recovers the text they cite.
- **Superseded designs stay as records.** `world_v2.md` gains the banner. Their live contracts are copied, not cut.
- **The reference check:** a script resolves every `<doc> §N` in live documents, scripts and tests against
  headings, before and after. The run is saved with the review.

## 6. The B36 lint: `scripts/lint_contracts.py`

**Registry.** `docs/design/contracts.md` indexes `| Contract | Owner | Kind |`, with no members. The owner's
defining block is preceded by `<!-- contract: <name> -->`. Its members are the code spans heading its rows or items.

**Defined against referenced.**
- A *definition* is any block outside the owner's that holds ≥ min(3, n) distinct members, for n ≥ 3.
- A *signature* contract, such as the ordering key, defines wherever its string appears.
- A *reference* names, cites, or uses fewer members. One `thought_failed` reason passes; a list of five fails.

**Scope.** The plan's scope documents. It skips `reviews/`, `research/`, `decisions/`, `maxim_upstream/` and
superseded files. CLAUDE.md is out of scope; its handshake line duplicates row 16.

**Structural checks:**
- no `## Fold table` heading in a design document;
- no decision table (first-column cells matching the decision-id patterns) outside `decisions/`;
- every registry row has exactly one marker, in the section it names, and every marker has a row.

**First contracts:** every vocabulary and field list in rows 1–80 that has a closed member list, starting with
rows 80, 6, 1, 9, 5, 48, 38, 10, 12, 4, 20 and 3.

**Honest limit.** It catches enumerations, the failure PR #27 found five times. It cannot see a rule restated in
prose ("live play holds the floor"). Those stay with Wire integrity under B36's row.

**Tests, red first.** Each of these fails:
- a planted five-reason copy;
- three members, where two pass;
- a missing, duplicate or orphan marker;
- a fold heading;
- a decision table.

Superseded files and records are skipped, and the real tree passes. Deleting the owner's marker turns the lint red,
which the commit message records. `lint_standards.py` wires it in, and B36 is marked done.

## 7. Order, coordination, budgets

1. Fold tables out, with the generator retargeted. These are B, N and WM, which no open PR edits.
2. Decision files and `check_plan.py`, with tests.
3. The `=`, `∪` and S rows, then each ✗ row once ruled.
   - T §1.3, §3 and §11, FS §5.1–§5.3, CL and RM wait for #32.
   - C §2, §5.3–§5.5, §6.5 and §8–§10 wait for #31.
   - #31's session is asked before C §4 changes.
4. The lint, with B36 marked done.
5. Review by Executor, Architecture and Wire integrity, with reports in `reviews/docs_contracts/`. Then merge
   `origin/main` and run `prepush.sh` on the Mac mini (asking before the first SSH).

**Budgets:** each design's word count at dc0e1aa is its ceiling. `moves.md` tabulates before and after. Cuts: N
−7,343, B −3,498, WM −1,145, T −466, IP −345, C −212. C is tight, so the handshake goes to B §5.3.
