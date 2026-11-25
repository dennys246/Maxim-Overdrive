# Records layout design, delta round: Architecture and Bio-faithful (2026-11-24)

I read the diff 239f267..9d1e747 (the design, the RL1–RL10 log, `fold.md`, the two roadmap rows). I checked it against
`scripts/lint_ids.py`, `scripts/check_plan.py`, `scripts/lint_gates.py`, CLAUDE.md's "A record id names one record",
`docs/known_gaps.md`, `docs/standards_backlog.md`, the lessons file, the decision logs and
`docs/design/reviews/docs_contracts/rulings.md`. I ran `lint_ids._decision_rows` over the decision logs at 1ed9caa
and at 9d1e747, a whitespace word count of the longest record in each family, and greps for lesson anchors and for
lesson citations under `docs/maxim_upstream/`. Nothing was edited except this report.

## Round-1 statuses

| Finding | Status | Evidence |
|---|---|---|
| A-B1 | fixed | RL9 turns the conflict into the detector. §1 withdraws the claim that records stop conflicting. §5 and §6 put one id-ordered, one-line-per-record index in each id-bearing family (the head of the lessons file, `decisions_index.md`, the backlog table), and R1 has the two-branch conflict test. A same-id pair at one insertion point conflicts, and one id with one slug is an add/add conflict on the record file. The detector holds under GitHub's merge button with RL8. |
| A-B2 | fixed | RL10 and §4: a lesson's body and title may change, and its `amended` list only grows. The generated file shows the trail, so lesson 29's correction stays visible where it is read. This matches CLAUDE.md's "add or update an entry". |
| A-B3 | fixed | §5 adopts `lint_ids`' family (an id prefix across every log). The ten cross-listed ids (O3–O7, O7a, O31, T1, T2, D20; checked with `_decision_rows`) become one record with `also_in`, and restating and id-less rows get slug ids. Decision citations are no longer resolved, so "(A1 and D1)" can't resolve wrongly. The slug-id format N-S2 found broken is fixed at 01cbb25: §3 and §5 now make such an id a plain slug, unique in its log's directory, in a file named `<slug>.md`, and define id order. |
| A-B4 | fixed | §4 adds `amends` and `supersedes` naming external rulings, plus `restates`. §8 says no derived status loses information, and R2 tests every non-`live` cell, external rulings included. N-S3 found that the anchor form it specified doesn't exist. That is fixed at 01cbb25: `amended_by_external` names a path and the ruling's first cell, and `confirms` and `corrects` were added. |
| A-S1 | fixed | §5: `renumber` rewrites only the lines the branch added or changed against its merge base, and lists `main`'s citations without rewriting them. R1 tests a shared file. The residual (a citation in a file the branch didn't edit) is named and accepted under RL1. |
| A-S2 | fixed | §5 delegates the grammar to `lint_ids::check_lessons`, whose docstring reads every form round 1 listed ("Lesson N", "lessons N and N", "lesson §N", the file name followed by §N), and R1 tests those forms. |
| A-S3 | fixed | §1 now says `lint_ids` misses a duplicate until both PRs merge. RL8 keeps "require up to date" off by name, and the real detector is GitHub refusing a conflicted merge (RL9). |
| A-S4 | fixed | §8 drops the PR list. `migrate-branch` maps every edit of an existing entry to a change §4 allows, or refuses it by name, which covers the lesson-23 and backlog-status kinds of edit. R2 tests it. |
| A-S5 | fixed | RL4 and §6 set the caps at 500, 400, 400 and 600. My counts: the longest lessons, 31 and 36, at 473 words each, decision 361 (O79), gap 343, backlog row 540 (B5). All four agree with the caps. |
| A-S6 | fixed | §7 keeps the `OD-` half of `missing_ids`. `check_plan.py` has it as `PHASE3`, so the half exists to keep. |
| A-S7 | deferred | §6 shows each gap's slug in the generated file. The `reason=` rewrite and its test are scheduled at §9 R3 (trigger: R3), with the rule in §5. |
| A-S8 | fixed | §3 and §6 add a hand-written `_header.md` per family, in `lint_contracts` scope and under O22. The lessons file has no per-section intros (checked), so a single header suffices. |
| A-S9 | fixed | §4 names one reader, `records.py::read_record`, built on `simcore.adapters.loaders` and `simcore.core.schema` (which exists), with versions per family and a gate-registry row. Scripts already import the loaders (`scripts/fuel_fixtures.py`). |
| A-S10 | fixed | §5: an unmerged lesson is never cited upstream, and `renumber` refuses ids cited under `docs/maxim_upstream/`. The refusal N-S1 found misfiring is fixed at 01cbb25: `renumber` never rewrites a file under `docs/maxim_upstream/` but still renumbers, and `check_records` refuses an added upstream citation of a lesson not on the base. |
| A-N1 | fixed | At 01cbb25, §5 says that `B` numbers are a family, but that their duplicate check stays `lint_guards`' (§7), so there is one owner. At 9d1e747 this was open: §5 made `lint_ids` the duplicate check for every family, `B` included. |
| A-N2 | fixed | §4: "the whole body is mutable"; a gap may change anything but its slug. |
| A-N3 | fixed | §7: a stale generated file names the record or `_header.md` to edit; findings in `docs/known_gaps.md` name the record, and the headings stay stable. |

Counts, after the RL13 fold at 01cbb25: 16 fixed, 1 deferred, 0 open. At 9d1e747 they were 15, 1 and 1 (A-N1).

## New findings

### BLOCKER

None.

### SHOULD-FIX

- **N-S1, §5 "It refuses" (`records.py renumber`): the upstream and frozen refusals are keyed on the id, not on whose
  record the citation names, so they fire in exactly the case the rest of §5 protects.** §5 also rules that a lesson
  is cited upstream only after it is on `main`. So any upstream citation of a colliding number names `main`'s record,
  never the renumbering branch's. Scenario:
  1. Branch A adds a new lesson numbered `41` and, in the same PR, a draft under `docs/maxim_upstream/` citing it. This is allowed,
     since it is on `main` once A merges, and the drafts already cite lessons (`hybrid_1_5_line_DRAFT.md` cites
     lesson 1).
  2. A merges.
  3. Branch B, which also took 41, merges `main`, regenerates, and the duplicate check fails.
  4. `renumber 41=42` is refused, because lesson number `41` is cited under `docs/maxim_upstream/`.

  The one sanctioned resolution is blocked, and B is left to renumber by hand. The refusal can never fire for its
  intended case unless the author broke the "after `main`" rule. "A file listed in any `freeze.sha256`" reads the same
  way when a frozen file on `main` cites `main`'s record. Fix (unverified): scope both refusals to citations in lines
  the branch added, the same rule as the rewrite, and let `main`'s lines take the "list, don't rewrite" path.

- **N-S2, §3 and §5: the slug id given to restating and id-less rows contradicts the file-name and slug contract.**
  - §3: a decision file is `docs/design/decisions/<design>/<id>-<slug>.md`, its id and slug must equal its front
    matter, and a slug is lowercase ASCII words joined by hyphens.
  - §5: such a row's id is "the log-qualified slug (`world_model/d26-to-d28`)". That id contains `/` and `_`, so it
    can't be a slug.

  The file name becomes `…/world_model/world_model/d26-to-d28-<slug>.md`, a nested path with the id doubled, or the
  name check refuses it. §6's "id order" for the decisions index doesn't say where such ids sort either. Two builders
  (the converter at R2 and `lint_records` at R1) must agree on this format, so it is contract. Fix (unverified):
  define such a record's `id` as its slug alone, unique within its design directory, name the file `<slug>.md`, and
  say these ids sort after the numbered ones.

- **N-S3, §4 Decisions, `amends` and `supersedes`: the external-ruling form "a repository path and an anchor … that
  must exist" has no anchor to point at.** Its own example, `docs/design/reviews/docs_contracts/rulings.md#41`, names a
  table row: `rulings.md` holds `| 41 | O16 is the live interim policy …` (line 36). There is no heading, so neither
  GitHub nor any Markdown slugger makes an `#41` anchor. Multi-row cells (`| 6, 7 |`) have no single target either. As
  written, `lint_records` must either refuse all eight "amended by docs-contracts ruling" statuses that A-B4 is about,
  or invent its own resolution of a row id. Then the generated link wouldn't land on GitHub. Fix (unverified): define
  the anchor as the first table cell of a row in the named file, matched as a whole id or one item of a comma list,
  and render it as a plain path plus "row 41" rather than a URL fragment. Alternatively, migrate those rulings as
  records (round 1's other option).

### NIT

- **N-N1, §2:** "Counts are at `1ed9caa`", but "174 rows with a single id (164 ids …) in ten logs" is the count at
  9d1e747. At 1ed9caa, `_decision_rows` gives 164 rows, 154 ids and nine logs. The tenth log is this fold's own
  `decisions/records_layout.md` (RL1–RL10). Restate the revision, or the numbers.
- **N-N2, §5:** the restating example `world_model/d26-to-d28` names the wrong log. The `D26–D28` restating row is in
  `decisions/tile_and_client.md` (line 28); `world_model.md` holds D26 itself. Under §5's own rule, the example would
  be `tile_and_client/d26-to-d28`.
- **N-N3, §4 "What may change":** a lesson may change its body, title and `amended` list, but not its `section`. RL7
  adds "Game and general engineering", so an existing lesson filed under a Maxim heading can move there only at the
  migration. After R3, reclassifying one is refused. That is fine if intended, but say so.
- **N-N4, §4 and §8, Bio:** lesson 11's heading today reads "(2026-11-15, reworded 2026-11-20)". §6 generates the
  heading from `date` alone and shows the trail under the lesson. The round trip's listed exceptions (the marker line,
  the lessons index, the status column) don't cover that heading change or the trail's new lines, so R2's
  byte-for-byte test fails on lesson 11 unless the exceptions say so. No in-repo link uses a lesson anchor (grep for
  `lessons_maxim_in_games.md#` finds none), so this costs nothing beyond the exception list.
- **N-N5, Bio, §4 and RL10:** a lesson cited by a draft under `docs/maxim_upstream/` can now have its body amended
  after the draft quotes its evidence. The `amended` trail makes that visible in the generated file, but nothing
  points the draft's author at it. This is not a relitigation of RL10. It is a candidate for the same treatment as
  N-S1: `lint_records` could list upstream citations of an amended lesson. Low cost, and this is the path by which
  stale evidence would reach a Maxim proposal.

**Bio-faithful overall:** nothing in the fold touches what NPCs sense, act through or keep time by. The upstream
surface (lessons cited by Maxim drafts) is better protected than at round 1: they keep their ids, stay citable by
path and `### N.` heading, and corrections stay visible. N-S1 is the one place the fold's upstream rule backfires.

## Status check after the RL13 fold (2026-11-24)

I read `git diff 14c2e5d 01cbb25`: the design, RL11–RL13, and `fold.md`'s "After the delta round". I checked the
diff against the tree. All eight rows that read "amended by docs-contracts ruling" (rulings 41, 45, 49, 50, 59 and 61)
have a single first cell in `rulings.md` (lines 36–45). The id-less and restating first cells in the logs are
`D26–D28`, `RT1–4`, "ruled 1–3", "the split", "the rounds stop", `CLAUDE.md` and four "—" rows.

| Finding | Status | Evidence |
|---|---|---|
| N-S1 | fixed | §5: `renumber` "never rewrites" a file under `docs/maxim_upstream/` instead of refusing to run, so the branch's record is still renumbered. `check_records` (§7) refuses an added upstream citation of a lesson that isn't on the base, which enforces the "only once it is on `main`" rule. §9 R1 tests the exact case of `main`'s record being cited upstream. The frozen-file refusal moved into the same "never rewrites" list. |
| N-S2 | fixed | §3: a decision whose id is a slug is `<slug>.md`. §4 adds a `slug` key. §5: the id is a plain slug, unique in its log's directory (`d26-to-d28` in `tile_and_client/`). Id order is defined, with slug ids after their log's numbered ids. §9 R1 tests that a slug id makes a valid file name. |
| N-S3 | fixed | §4: `amended_by_external` takes `{path, ruling: "41"}`, which matches a row's first cell. Every external ruling cited today has a single first cell (checked above). It is migration-only, and a later external ruling must be a decision record. §7 refuses an unknown path or ruling. |
| N-N1 | fixed | §2 now reads 164 rows, 154 ids and nine logs at 1ed9caa, which matches my `_decision_rows` run, and names the tenth log as this branch's. |
| N-N2 | fixed | §5's example is now `d26-to-d28` in `docs/design/decisions/tile_and_client/`, where the row is. |
| N-N3 | fixed | §4: a lesson may change its `section`, with an `amended` entry. |
| N-N4 | fixed | §8 stage 1 keeps lesson 11's heading tail in `legacy`, and the byte-for-byte exception list is now the marker line alone. §9 R2 tests it. |
| N-N5 | deferred | `fold.md` (the author's call): "step 4, R1: a note when an amended lesson is cited under `docs/maxim_upstream/`". The trigger is step 4, R1. It is not yet a §9 test line, so the trigger lives only in `fold.md`. |

### New BLOCKER in the fold

None.

Not a BLOCKER, and noted for step 4 rather than for another fold. §4's change rules ("a decision file never changes";
a lesson changes only `body`, `title` and `section`, each change adding an `amended` entry) give no exception for R3's
presentation commit. That commit removes `legacy` fields from existing decision and lesson records, and duplicated
prose from gap and backlog bodies. If both R3 commits land in one PR, every record is new against the base, and the
check passes. If the presentation commit lands as its own PR after the first has merged, `check_records` refuses it.
§9 R3 says "in two commits" without saying whether they share a PR. Trigger: step 4, R3.
