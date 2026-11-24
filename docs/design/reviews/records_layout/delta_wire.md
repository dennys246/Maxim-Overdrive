# Records layout design, delta round: Wire integrity (2026-11-24)

Read: the diff `239f267..9d1e747` (the design, its rulings RL1–RL10, `fold.md`, the two roadmap rows), checked against
the tree at `9d1e747` and at `1ed9caa`. Ran (read-only): `lint_ids`' own `_decision_rows`, `_ID_CELL` and `_HEADING`
over both revisions; word counts of every lesson, decision row, gap bullet and backlog row; a listing of every
non-`live` status cell, every "Who, date" cell, every cross-listed pair's owner-section cell, and each log's row
order; `simcore.adapters.loaders.read_yaml` on a scratch record file (`<scratchpad>`); `scripts/lint_standards.py`
and `scripts/check_plan.py`.

## Formats

| Format | Writer | Reader | Version | Owner |
|---|---|---|---|---|
| Record front matter (four families) | humans; `records.py migrate`, `migrate-branch`, `renumber` | `records.py::read_record` (named parser: `loaders`' strict YAML, `core.schema`); through it `lint_records`, `lint_ids`, `lint_guards`, `records.py index` | `version` per family, 1 at R1 | §4 |
| Record file name `<id>-<slug>.md` (gaps `<slug>.md`) | humans, `migrate`, `renumber` | `lint_records` | none | §3 |
| `_header.md` per family directory | humans | `records.py index`; `lint_contracts` | none | §3, §6 |
| Generated files: lessons file, ten logs, `known_gaps.md`, backlog, `docs/generated/decisions_index.md` | `records.py index` | humans; `lint_records` (byte compare); git merge (the RL9 detector); `check_plan`'s `ID_SOURCES` (five logs); `lint_contracts` (`known_gaps.md`); `lint_standards` hands the backlog file to `lint_guards` today | one marker line | §6 |
| Lesson citation grammar | humans | `lint_ids::check_lessons`; `renumber` | none (`lint_ids`' docstring) | §5, held by `lint_ids` |
| Decision and B-id citations | humans | `renumber` (grammar unstated); `lint_guards` (`Guard:` lines) | none | §5 |
| External ruling reference `path#anchor` | humans, `migrate` | `lint_records` | none | §4 |
| Gap slug in red-gate `reason=` strings | humans (R3) | a test (R3) | none | §5 |

## Round-1 statuses

| Finding | Status | Evidence |
|---|---|---|
| W1 | fixed | RL8 and RL9 rule the policy. §5 makes each id-bearing family's id-ordered index the detector, and §1 withdraws "no conflict". R1's second test covers it, with the add-one-id-two-slugs case. Checked: two branches adding the same id insert at the same index position under any total order, so git conflicts. |
| W2 | fixed | §5: `renumber` rewrites only lines added or changed against the merge base, and lists `main`'s citations without rewriting them. R1's third test runs on a shared file. The stacked-branch residual is stated and accepted under RL1. |
| W3 | fixed | §5 adopts `lint_ids`' lesson grammar, which already reads "Lesson N", "lessons N and N", en-dash ranges, "lesson §N" and the file-name forms (`lint_ids.py::_CITE`). Decision citations are no longer resolved, so the day-one reds (`D53`, `D2395`, `B905`) and false passes (`T1-S1`) are gone. R1 tests every spelling. `renumber`'s decision grammar is a new finding (S5). |
| W4 | fixed | §5 defines a family as `lint_ids` holds it: a prefix across every log. Cross-listed rows become one record with `also_in`; restating and id-less rows get log-qualified slug ids. Checked against `_decision_rows`: all ten cross-listed ids (O3–O7, O7a, O31, T1, T2, D20) and all fifteen non-id rows are covered. The new text's own defects are B1, S3 and S4. |
| W5 | open | §4's four relations (supersedes, amends, also_in, restates) and the bold-lead title fix part of it. Status cells the fields still can't express: "confirmed by O69" (O67, O68), "confirmed by O74" (O73) and "corrected by O73" (O71) have no field. "restates world_model §0" or "boundaries §0" (six cells), "restates CLAUDE.md" and "restates `client_rendering.md`" name sections or files, not ids, and `restates` holds ids only. `RT1–4` "restates realtime decisions 1–4", but RT1–RT4 have no record, so §7's unknown-id refusal reds the migration commit. A cross-listed id's two rows carry different statuses (D20, O31 and T1: `live` in one log, "restates" in the other), and one record has one derived status. The two non-ISO date cells (`standing`, `owner, 2026-11-17/18`) are unaddressed: `date` must be ISO, and §8's `unknown` isn't an ISO date. R2's first test will fail on these cells, not pass. |
| W6 | open | The gap and backlog fields and #52's deletion rule are fixed. Still open: (a) `gate` and `closes_at` duplicate the body's "Red gate: …" text, and the backlog `status` duplicates the "Lands with" cell's prose (`**done**`). The byte-identical round trip needs that prose kept, so there are two copies and no rule says which wins or that they agree. (b) `done_in` is "the commit", but the source cells say `step 3b part b` (B29) and `the owner's decision` (B21). B6's "done locally; pending its first …" and B19's "(1) done; (2), (3) open; (4) d…" fit `open`/`done in part`/`done` only by losing information. (c) §8's `unknown` isn't a legal value of the closed `kind` enum, of `gate` ("a test id, or `none` and a reason") or of `date`, so the schema refuses what the converter must write. |
| W7 | fixed | RL4 sets the caps; §6 states them. Recounted (whitespace words): the longest lesson record is 473 words (31 and 36), decision row 361 (O79), gap 343, backlog row 540 (B5), giving 500, 400, 400 and 600, as §6 says. The plan's §4 table at about 1,083 words is stated. |
| W8 | fixed | RL10; §4's "What may change" compares against the merge base and gives each family's deletion rule. |
| W9 | fixed | §8 is rewritten. #48, #49, #52 and #55 are on `main` at `1ed9caa` (checked with `git log`). `migrate-branch` runs before the branch merges `main` and maps or refuses edits, and R2's last two tests cover it. (Its "checkout of `main`" is N4.) |
| W10 | fixed | §7 keeps `check_plan::missing_ids`' `OD-` half; `check_plan` passes at `9d1e747`. The decision half's retirement has a side effect (N5). |
| W11 | open | Fixed in part: the reader (`records.py::read_record`), its `---` grammar, versions per family and the gate row (`lint_gates.py::GATE_MODULES`) are named. Still open: the named parser is the one W11 said can't do the job. `loaders`' only public strict reader is `read_yaml(path)`, and on a record file it returns `Refused: not valid YAML: expected a single document in the stream` (run on `<scratchpad>`). No text-taking entry exists, and `_StrictLoader` is private. `core.schema` has no converter for a date (unquoted `date: 2026-11-24` loads as `datetime.date`, which `Text` refuses since it isn't a `str`). It has none for a list of strings either (`ListOf` yields mappings), and none for an "id or `path#anchor`" union. So the stated contract can't be met without new `loaders`/`core` API, and the design doesn't name it. |
| W-N1 | open | §6 generates the heading's date from `date`, but lesson 11's heading reads "(2026-11-15, reworded 2026-11-20)". `amended` is empty at creation (§4), and §8's round trip doesn't exempt headings. |
| W-N2 | deferred | The author's call, triggered at step 4's R2. It isn't in §9's tests, and §3 now depends on it (S4). |
| W-N3 | fixed | §5 and §9's R3 schedule the `reason=` rewrite and a test that each one names a real gap. |
| W-N4 | fixed | §5: `renumber` applies one whole mapping at once; R1 tests a range shift. |

## New findings

### BLOCKER

- **B1, §8 against §4–§6: the round trip can't hold, so the migration has no valid proof.** §8 requires the
  regenerated files to match the originals byte for byte, except for the marker line, the lessons index and the
  derived status column. The fold's own formats rule that out in three families:
  - *Cross-listed decisions are one record* (§5), but their two rows differ in the ruling text (O3: "**The agent
    substrate** runs outside the sealed core, behind an engine-defined `AgentPort`…" against "The substrate runs
    outside the sealed core behind `AgentPort` (as refined by O6 and O6a)"; O31 and D20 likewise). They also differ in
    `owner_section` (O3: "—" against "§1, §6"; T1: "§1, §2" against "—") and in status (D20, O31, T1). A record has one
    body and one `owner_section`.
  - *Row order is not id order, and no field records it.* boundaries: `… O41 O42 O25 O8 O57 …`; npcs_and_sem:
    `… O12 O11a …`, `… O20 O56 O26 …`, `… O45 O7a OA4 …`; sem_stimuli interleaves the id-less rows with D12 to D15.
    §6 doesn't say what order a log is generated in, and no record field holds today's order.
  - *`known_gaps.md` is regenerated "grouped by `kind`, each with its slug shown"* (§6). The original has no slugs, no
    kind groups, and a "Known gaps (tracked, not gated yet)" sub-heading over an unbold run.

  Lesson 11's heading (W-N1) is a fourth case. *Failure:* R2's round trip goes red on the real files. The easy ways
  out at build time are both forbidden: widening the exemption list loosens the test (CLAUDE.md, "No band-aids"), and
  keeping one row's text loses information (§8: "none loses information"). Deciding which differences are allowed,
  and where the lost text lives (per-log text on a cross-listed record, an `order` field, or a named reformatting
  commit), is a contract choice. Under the stop rule it goes to the owner. *Fix:* none proposed.

### SHOULD-FIX

- **S1, §4 `supersedes`/`amends` with external rulings: the direction is undefined, and the anchor doesn't exist.**
  Internally the amending record carries `amends: [Y]`. The seven "amended by docs-contracts ruling N" cells (O8, O14,
  O24, O11a, D26, `ruled 2`, and the restating rows) name an external amender that has no record to carry the field.
  So the reference must sit on the amended decision, which inverts the field. A later external ruling would then
  need an edit to a decision file, and §4 says a decision file "never changes". Also,
  `docs/design/reviews/docs_contracts/rulings.md#41` doesn't resolve: rulings 41, 45, 49, 50, 59 and 61 are table rows
  with no heading or HTML anchor, and the same file has two separately numbered lists "1."–"6.". *Failure:*
  `lint_records`' "missing external anchor" refusal (§7) either reds every external reference at R3 or gets an
  unreviewed row-number lookup at build time. *Fix (unverified):* define the external form as an inverse relation
  (`amended_by`) with a resolvable target grammar (path plus table row id), and say whether a later external
  amendment needs a record of its own.
- **S2, §2: the gap count is wrong, and five gaps have no title source.** `docs/known_gaps.md` has 18 top-level
  bullets (`grep -c '^- '` at both revisions), not 13: five (NPC inference, the coarse-rig lag, structural glow, no
  convection, destroyed cells lose heat) have no bold lead. §4 gives decisions a hand-title rule ("a row without one
  is given a title by hand … listed there") and gaps none. *Failure:* a converter written to §2 ("13 bold bullets")
  drops five gaps or invents their titles, and §8 forbids both. The round-1 count was 18.
- **S3, §3 and §5: slug ids don't fit the file-name grammar, and the slug has no front-matter key.** A restating or
  id-less record's id is "the log-qualified slug (`world_model/d26-to-d28`)". Its file is `<id>-<slug>.md` inside
  `docs/design/decisions/<design>/`, so the name holds a `/` (a nested `world_model/` directory) and an `_`, which the
  slug grammar ("lowercase ASCII words joined by hyphens") refuses. §3 also says "a file's id and slug must equal its
  front matter", but §4's keys are `version`, `id`, `title` and `date`: there is no `slug`. And `D26–D28` sits in
  `tile_and_client.md`, not `world_model.md`. *Failure:* `lint_records`' name check (§7) has no rule it can apply to
  15 rows, so R1 picks one ad hoc, and the decisions index's slug column has no source.
- **S4, §3: the placement rule for a cross-listed decision can't be evaluated.** "The design its owner section names
  first". The owner-section cells of the ten cross-listed pairs name sections of their own log's design ("§1, §6",
  "cites §1", "—"), never a design, except boundaries' O6 and O7 ("cites `npcs_and_sem.md` …"). The rule also doesn't
  say which of the two rows' cells counts. D20 has "—" and "cites §1". *Failure:* the directory of eight of the ten
  records is undefined. §8 has R3 rerun `migrate` from scratch, and a rerun is free to place them differently, which
  moves files and changes `lint_records`' name expectations.
- **S5, §5: `renumber` has no citation grammar for decision and backlog ids.** Once "decision citations are not
  resolved", nothing defines what `renumber <old>=<new>` matches in the added lines. `lint_ids`' `_ID_CELL` admits
  any `[A-Z]+\d+` family, including `S` (sem_stimuli's S4), `T`, `C` and `W`. Review-finding ids share those shapes
  (round 1's S1–S4, C1–C3, W1–W11, `T1-S1`), and so do Maxim's D-ids and ruff rules. *Failure:* a branch renumbering
  its new `S5` to `S6` also rewrites a review report's "S5" finding, added in the same branch, and no check sees it,
  because decision citations aren't resolved. A B-id renumber has the same gap in CLAUDE.md's `Guard:` lines. *Fix
  (unverified):* state the token grammar `renumber` uses per family (word boundaries, no `-` suffix, prefix filter,
  which files), and test it in R1.

### NIT

- **N1, §2:** the decision counts say "at `1ed9caa`", but 174 rows, 164 ids and ten logs are `9d1e747`'s: they include
  RL1–RL10. At `1ed9caa` it is 164 rows, 154 ids and nine logs (`lint_ids._decision_rows`).
- **N2, §3 and §7:** `lint_contracts` has no out-of-scope list. `SCOPE` is an in-scope regex
  (`^docs/(design|plans)/[^/]+\.md$|…`), which no record directory already matches. The `_header.md` files don't
  match it either, so keeping them in scope means widening `SCOPE`. And `docs/known_gaps/_header.md` is then checked
  twice, alone and inside the in-scope generated `docs/known_gaps.md`.
- **N3, §6:** "id order" isn't defined (lexicographic or natural: `O7a`, `O8`, `O80`). The detector works under any
  total order, but the byte comparison needs one fixed order, and R1 should test it.
- **N4, §8:** `migrate-branch` "runs from a checkout of `main`". Git refuses to check out `main` in a second worktree
  while the main checkout has it, and CLAUDE.md keeps sessions out of the main checkout. It means a detached checkout
  of `origin/main`.
- **N5, §7:** `check_plan::missing_ids` reads decision ids from five designs as well as their logs (`DECISION`,
  `WORLD_DECISION`, `TILE_DECISION`). Retiring the decision half also drops the only check that an O, D or T id cited
  in a design is listed somewhere. With decision citations unresolved (§5), a design citing a decision id that has no
  record then passes everything.
