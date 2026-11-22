# Follow-up rulings: Wire integrity review (`phase1/b36-followup`, 5394e3e vs origin/main)

Lens: Wire integrity (`docs/code_review.md`), plus CLAUDE.md "One owner per contract". Read: `git diff
origin/main..HEAD`, then every live consumer of each changed contract outside the hunks (docs/design/*.md except
superseded `world_v2.md` and `realtime_lanes_coop.md`, docs/plans/*.md, docs/roadmap.md, docs/architecture.md,
CLAUDE.md, docs/lessons_maxim_in_games.md, src/, tests/). Ran: `scripts/lint_contracts.py::check_contracts` over the
tracked docs (no problems), `ruff check` and `ruff format --check` on the three changed Python files, a heading diff
of every changed doc against origin/main, and `wc -w` per design doc with `<!-- contract:` lines removed.

## Contract table

| Contract | Owner (after) | Consumers read | Agree with owner? |
|---|---|---|---|
| Stale credit | `sem_stimuli.md` §6.2 | boundaries §7.2, §13; npcs §6.4, §12.2; roadmap OD-A16, Phase 3 exit; lessons §9; checklists agent line | **no** (W-S1, W-S2) |
| Run seed vs root id | `boundaries.md` §6.3 (header) | npcs §3.4, §6.6; boundaries §11.2; checklists replay ids | partly (W-S4) |
| O26 rerun on purged text | `inference_placement.md` §4.2 | boundaries §6.2 redaction records; foundations_plan O26 row; inference_gateway §6 | **no** (W-S3) |
| Scene versions | `fire_solid.md` §5.2 (fuel), `tile_and_client.md` §1.3 (zones) | fire_model §7, §10.2; scene.py `_LATER`; schema.py; test_scene_v1 | yes; test file breaks the gate (W-B1) |
| `BoundFrame` push unlogged | `sem_stimuli.md` §11.2 Q8 / §5 | checklists agent line | yes (W-N2) |
| CLAUDE.md owner links | world_model §3, boundaries §5.3 | CLAUDE.md | yes; both headings exist and hold the rule |
| `agent_failed.reasons` | `npcs_and_sem.md` §6.6 | sem_stimuli §4.3–§4.5; boundaries §6.1; roadmap OD-A18 | owner disagrees with itself (W-S5) |
| `record.kinds` restates-at 6 → 5 | `contracts.md` | the lint | yes; lint passes at 5 |

## Findings

### W-B1. BLOCKER: `tests/test_scene_v1.py::test_the_phase_2_keys_are_refused_by_path_with_the_reason`

**Failure scenario:** `scripts/prepush.sh` runs ruff and stops; no `prepush: PASS` is possible for 5394e3e.
**Evidence:** `ruff check tests/test_scene_v1.py` gives `E501 Line too long (127 > 120)` at 116:121, and `ruff
format --check` says the file would be reformatted (it splits the `pytest.raises(` call). The message string itself
agrees with `scene.py::_LATER`, so only the line wrap is wrong. Executor owns the hunk; I report it because a red gate
blocks every other fold.

### W-S1. SHOULD-FIX: stale credit. `boundaries.md` §7.2 and §13, `npcs_and_sem.md` §6.4 and §12.2, `roadmap.md` OD-A16 and the Phase 3 exit still say the old rule

**Failure scenario:** ruling 1 says the host withholds a stale intent's credit, and the new checklist test asserts
"its settle books nothing, while its receipt still reads `accepted`". If settle books nothing, Maxim's failure path
never books a stale intent as NEGATIVE. But the copies still say Maxim does and that only Maxim can fix it:
- boundaries §7.2: "Until Maxim promotes a refusal-kind key through the bridge's failure path (OD-A16), stale
  refusals are an OPEN divergence with a strict red gate";
- boundaries §13: "Stale refusals stay an OPEN divergence until Maxim promotes a `stale` refusal kind (OD-A16)", while
  ruling 1 says v1 receipts need no `stale` kind;
- npcs §6.4 (the same bullet), and npcs §12.2: "Stale refusals book NEGATIVE; closes with OD-A16";
- roadmap OD-A16 still asks Maxim for a `stale` kind, and the Phase 3 exit (line 285) still requires "OD-A16 has
  closed the stale-refusal divergence before Phase 4".

An author building the agent PR gets two readings: write a strict red gate for NEGATIVE booking (boundaries,
npcs), or a green test that settle books nothing (checklists, sem_stimuli). Phase 4 stays gated on an upstream
change the ruling may have made unnecessary. Both bullets also keep their lead "**Stale is context, never credit**
(lesson 9)" after the fold removed the only clause that said what "context" means.
**Also:** the owner sentence in §6.2, "A stale intent gets no credit, withheld host-side", doesn't say which
staleness it means: the wire outcome `stale` (`tile_and_client.md` §3.3, "no Phase 1 producer"; §3.2, "Phase 1 has no
stale rule") or Maxim's agent-side §A.1b.5 staleness (`npcs_and_sem.md` §6.6, O38), where the agent drops or re-plans
the reply itself and the host sees no intent. Ruling 1's "which its log names" doesn't name the record. A contract
that other sections now link to needs that term pinned.

### W-S2. SHOULD-FIX: `docs/lessons_maxim_in_games.md` §9 contradicts ruling 1

**Failure scenario:** lesson 9's consequence still reads "stale refusals go to the next thought's context; a Maxim
change is needed for the failure path to respect that." The ruling drops exactly that clause, and the design bullets
cite "(lesson 9)" as their basis. A pushback to Maxim drafted from the lessons file, which CLAUDE.md calls "the
evidence base for pushbacks", would argue for a mechanism the owner just removed. CLAUDE.md "Record lessons as
they're learned" says a design reversal updates the lesson in the same commit.

### W-S3. SHOULD-FIX: O26. `boundaries.md` §6.2 "Redaction records" and `docs/plans/foundations_plan.md` O26 still scope the boundary to replay

**Failure scenario:** ruling 3 says O26 is about the tier-2 rerun and that "tier-1 replay calls nothing". But
boundaries §6.2 still says "replay is bit-identical only up to the first redacted reply, which the log marks as a
replay boundary", and foundations_plan's O26 row says "replay exact to the first redacted reply". A replay
implementer reading boundaries stops tier-1 world replay at a redaction record, which by ruling 3 it doesn't need to
do. That cuts a bug-report replay short for no reason.
**Owner side:** the new `inference_placement.md` §4.2 bullet says a rerun "reads the recorded replies", but
boundaries §6.2 says the reply that quoted the purged words "is redacted too". §4.2's miss rule exempts only
thoughts with a `thought_cancelled` or `thought_failed` record ("Any other miss is a loud error"). It doesn't say what
a rerun does at a redacted reply: read the redacted text (and diverge), stop at the boundary, or fail loudly.
Two sections now speak to that case without agreeing.

### W-S4. SHOULD-FIX: `npcs_and_sem.md` §3.4 still calls the seed "root"

**Failure scenario:** ruling 2 separates the root id (identity) from the run seed (randomness), and fixes only "the
log header's root seed". The same section still reads `SeedSequence(root, spawn_key=(NS_AGENT, npc_key,
stream_key))`, "`spawn_key=(NS_WORLD,)` from the same root", and "`base_seed` from this tree's root (O40)". §6.6 and
`checklists.md`'s replay ids use "the root id" for the log's identity. An implementer who reads `root` as the
header's root id seeds every NPC stream from an identity value. Two runs with different run seeds but the same log
root (a restore, say) then draw identical noise, and that breaks the determinism contract quietly.

### W-S5. SHOULD-FIX: `npcs_and_sem.md` §6.6. The owner's own signature lists three reasons

**Failure scenario:** the newly registered vocabulary is `hung crashed protocol build`, but the same owner bullet
still gives the record's signature as `agent_failed(npc, reason = hung | crashed | protocol)`, and the marker's
`not:` clause excludes that span so the lint can't see the mismatch. A codec or enum written from the signature
(the first and most code-like statement) has three members, and `sem_stimuli.md` §3.2 and §4.5's
`agent_failed(build)` is then refused as an unknown reason. That build failure is the one that turns a bad binding
table into a logged record. The registration hid a disagreement inside the owner rather than removing it.

### W-S6. SHOULD-FIX: word budgets. Four design documents grew

`wc -w`, `<!-- contract:` lines excluded, origin/main → HEAD:

| File | Before | After |
|---|---|---|
| `inference_placement.md` | 4,607 | 4,626 (+19) |
| `contracts.md` | 527 | 539 (+12) |
| `sem_stimuli.md` | 5,888 | 5,898 (+10) |
| `tile_and_client.md` | 5,351 | 5,354 (+3) |

The others shrank: boundaries −7, fire_model −26, npcs_and_sem −10. **Failure scenario:** CLAUDE.md (O22): "an
existing design document doesn't grow". B24 has no check over `docs/design/`, so nothing else catches this.
`contracts.md` may count as an index (owner to say). The other three are design documents, and each growth comes from
this diff (§4.2's new bullet, §6.2's sentence and Q8's answer, §1.3's reworded zones line).

### W-N1. NIT: "(follow-up ruling 1)" in `sem_stimuli.md` §6.2 and "(follow-up ruling 3)" in `inference_placement.md` §4.2 don't name their record

`sem_stimuli.md` keeps its own "20 rulings". A bare "follow-up ruling 1" can be read as one of them, or can't be found
at all. Name `reviews/docs_contracts/rulings.md`.

### W-N2. NIT: `checklists.md` agent line, the `BoundFrame` test

"a rerun with every push stripped from the record matches each per-tick digest". Under Q8 the record holds no
pushes, so stripping them changes nothing and can't go red. The planted push is the only half that can fail. Word the
first half as what is compared (digests recomputed from the world alone), or drop it.

### W-N3. NIT: `checklists.md` agent line, the stale-credit test has no Phase 1 producer

`tile_and_client.md` §3.3 says `stale` has no Phase 1 producer, and §3.2 says Phase 1 has no stale rule. So the agent
PR's test needs an injected stale intent, and nothing says so. This ties to W-S1's undefined term.

### W-N4. NIT: `fire_model.md` §2 table, pre-existing and not in a hunk

The fuel-object row still lists `rod` "with any axis" and `bed`. `fire_solid.md` §5.2 admits `rod` with a finite
non-zero axis or `slab`, with `bed` dropped. Ruling 4 says `fire_solid.md` overrides, but only fire_model §7 was
turned into a link, so a second fuel-geometry list survives in the same document.

## Checks that passed

- **References (2):** every `<doc> §N` the diff adds resolves to a heading. These are `sem_stimuli.md` §6.2, §5
  (Q8's "(§5)"), `world_model.md` §3 ("Every law reconstructs, decides at the point, and integrates"), `boundaries.md`
  §5.3 (it holds the handshake, `Origin`, token and 127.0.0.1 text), `fire_solid.md` §5.2, `npcs_and_sem.md` §6.6,
  `inference_placement.md` §4.2. "Q8" names an item in `sem_stimuli.md` §11.2, not a heading; it is findable.
- **Headings (3):** no heading was renumbered, removed or renamed in any changed file. The only heading change is the
  new "Follow-up rulings" section in `reviews/docs_contracts/rulings.md`.
- **"root seed":** no live copy remains (W-S4 is the bare "root"). "scene v2": no live copy in docs, src or tests,
  apart from the superseded designs.
- **`lint_contracts`:** passes on the tree, including the new `agent_failed.reasons` row and `record.kinds` at 5.
- **Dropped fire_model §7 text:** its "placement inside an owner's footprint, which the overlap rule now allows"
  contradicted `fire_solid.md` §1.3 (no fuel object may overlap a solid footprint by more than 1 mm), so turning it
  into a link removed a live contradiction.

## Counts

BLOCKER 1 (W-B1) · SHOULD-FIX 6 (W-S1 to W-S6) · NIT 4 (W-N1 to W-N4).
