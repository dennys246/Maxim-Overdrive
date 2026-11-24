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
| A-B3 | fixed | §5 adopts `lint_ids`' family (an id prefix across every log). The ten cross-listed ids (O3–O7, O7a, O31, T1, T2, D20; checked with `_decision_rows`) become one record with `also_in`, and restating and id-less rows get slug ids. Decision citations are no longer resolved, so "(A1 and D1)" can't resolve wrongly. The slug-id format this adds is broken: see N-S2. |
| A-B4 | fixed | §4 adds `amends` and `supersedes` naming external rulings, plus `restates`. §8 says no derived status loses information, and R2 tests every non-`live` cell, external rulings included. The anchor form it specifies doesn't exist: see N-S3. |
| A-S1 | fixed | §5: `renumber` rewrites only the lines the branch added or changed against its merge base, and lists `main`'s citations without rewriting them. R1 tests a shared file. The residual (a citation in a file the branch didn't edit) is named and accepted under RL1. |
| A-S2 | fixed | §5 delegates the grammar to `lint_ids::check_lessons`, whose docstring reads every form round 1 listed ("Lesson N", "lessons N and N", "lesson §N", the file name followed by §N), and R1 tests those forms. |
| A-S3 | fixed | §1 now says `lint_ids` misses a duplicate until both PRs merge. RL8 keeps "require up to date" off by name, and the real detector is GitHub refusing a conflicted merge (RL9). |
| A-S4 | fixed | §8 drops the PR list. `migrate-branch` maps every edit of an existing entry to a change §4 allows, or refuses it by name, which covers the lesson-23 and backlog-status kinds of edit. R2 tests it. |
| A-S5 | fixed | RL4 and §6 set the caps at 500, 400, 400 and 600. My counts: the longest lessons, 31 and 36, at 473 words each, decision 361 (O79), gap 343, backlog row 540 (B5). All four agree with the caps. |
| A-S6 | fixed | §7 keeps the `OD-` half of `missing_ids`. `check_plan.py` has it as `PHASE3`, so the half exists to keep. |
| A-S7 | deferred | §6 shows each gap's slug in the generated file. The `reason=` rewrite and its test are scheduled at §9 R3 (trigger: R3), with the rule in §5. |
| A-S8 | fixed | §3 and §6 add a hand-written `_header.md` per family, in `lint_contracts` scope and under O22. The lessons file has no per-section intros (checked), so a single header suffices. |
| A-S9 | fixed | §4 names one reader, `records.py::read_record`, built on `simcore.adapters.loaders` and `simcore.core.schema` (which exists), with versions per family and a gate-registry row. Scripts already import the loaders (`scripts/fuel_fixtures.py`). |
| A-S10 | fixed | §5: an unmerged lesson is never cited upstream, and `renumber` refuses ids cited under `docs/maxim_upstream/`. The refusal as worded misfires: see N-S1. |
| A-N1 | open | §7 says `lint_guards` keeps backlog duplicates. But §5 defines a family to include "`B` numbers" and then says "The duplicate check is `lint_ids` … two records with one id in a family fail". Read together, `lint_ids` also checks B duplicates, so there are two owners again. |
| A-N2 | fixed | §4: "the whole body is mutable"; a gap may change anything but its slug. |
| A-N3 | fixed | §7: a stale generated file names the record or `_header.md` to edit; findings in `docs/known_gaps.md` name the record, and the headings stay stable. |

Counts: 15 fixed, 1 deferred, 1 open.

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
