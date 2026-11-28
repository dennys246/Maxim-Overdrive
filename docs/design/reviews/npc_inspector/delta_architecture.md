# NPC inspector design v2: Architecture delta review (round 2)

**Lens:** Architecture (delta round on a design). **Read:** `docs/design/npc_inspector.md` v2, the working-tree blob `20b6cbb1` (4,038 words), against v1 at `bd0137d` (`git diff bd0137d -- docs/design/npc_inspector.md`). I also read my round-1 report (`reviews/npc_inspector/architecture.md`) and the author's claims (`reviews/npc_inspector/fold.md`, blob `5791d71e`). I treated those claims as claims and checked each against the tree.

**Context read on the tree:**
- CLAUDE.md;
- `boundaries.md` §5.3, §5.4, §6.1 (lines 390–410), §6.3 and §7.1 (line 540);
- `npcs_and_sem.md` lines 600–616 and 700–806, which cover the double, the codec, the restart segment and the continuation header;
- `sem_stimuli.md` §4.2–§4.4 and §5;
- `realtime_lanes_coop.md` §4.1;
- `inference_placement.md` §4.2;
- `src/simcore/core/schema.py` (the tick rule, which cites tile §3.2);
- `scripts/lint_inputs.py::INPUT_GATES` and `scripts/lint_gates.py`;
- `docs/roadmap.md` (the OD-A15 row);
- `docs/plans/next_steps/4_records_build.md`.

**Ran:** `scripts/lint_contracts.py` (exit 0) and `scripts/lint_paths.py` (exit 0), with bytecode writing off. The tree was unchanged afterwards.

**Not checked:** Maxim and Maxim-pulse citations, and the state of PR #81, because I did nothing that needed the network.

**Verdict:** the fold fixes the round-1 blocker at its root. v2's §2 removes every copied log fact and all free text, which fixes A1 and makes A5 moot rather than reframing it. The writer and the reader now sit in `simcore.host`, and §8 makes each edit to another owner's contract explicit. One round-1 finding stays open on a narrow remainder (A3). The fold's text adds no BLOCKER, so the charter's stop rule is not triggered. It does add three SHOULD-FIX findings: D1, D2 and D3.

## Status of round-1 findings

| Finding | Status | Evidence (v2 tree) |
|---|---|---|
| A1 (BLOCKER) | fixed | §2: "Memory writes are recorded agent-side, after OD-A15 (`boundaries.md` §6.1), and the record only points at them". `write_ref` holds a pointer, not the write, and §8 lists the §6.1 amendment as a proposed edit to its owner. There is now one record of memory writes. The new dependency this creates is D2. |
| A2 | fixed | The `stimulus` row is "one delivery as it crossed to the worker". "Excluded by name" lists the host-only body frame (`sem_stimuli.md` §4.2). "A stimulus is not a percept" names the worker's clamp (§4.4). The remainder (a partial restatement of `BoundFrame`'s fields) is N1. |
| A3 | open | §6 "On Overdrive's side" and §8 now name `npcs_and_sem.md` §6.6 (the `step_output` frame) and `sem_stimuli.md` §5 (its version and gate row). They also give `readout` its own barrier-budget line, and the "No extra round trip" claim is gone. Still missing: `StepOutput`'s contents are stated in `boundaries.md` §7.1 (line 540: "intents (with `apply_us`), `speak` acts, thought requests, and memory writes"), and its types in `npcs_and_sem.md` §6.2 (line 603). Neither §6 nor §8 names them, so a `readout` field would leave §7.1's list stale. The fix is to add §7.1 to §8's `readout` line. It is [later], so this is NIT-sized. |
| A4 | fixed | §4 puts the writer and the reader in `simcore.host`, which already holds an input gate (`INPUT_GATES` lists `host/server.py`). The reader gets a gate-registry row and an input-gate entry. The import rule now names the module and its two permitted importers. The engine/game split is stated. One Python gate serves every view. Two remainders are D1 and N3. |
| A5 | fixed | Moot rather than reframed. The kinds table holds no free text: refusals keep a code and a byte length, `thought_state` holds counters and ids, and `write_ref` holds a sequence and a count. Old question 4 is gone from §10, and §2 places guest words "only where O26's purge already reaches". |
| A6 | fixed | §8 lists save v1 (`roadmap.md` Phase 4, `boundaries.md` §7.1) and the §5.3 gate table as proposed owner edits, "None of them is made here". The bug-report redaction rule is no longer restated. §5 says there is nothing new to drop. |
| A7 | fixed | §10 item 7 states that step 4's exit test requires no open PR. It says the branch is in neither O79's nor O81's order, and it states #80's terms ("no PR, no merge and no record edit until step 4 merges"). The remainder ("like PR #81") is N4. |
| A8 | fixed | The header names one future owner: "until a draft in `docs/maxim_upstream/` takes it (§9)". `phase3/joint-plan` text is marked unmerged. The "condition 3" and BF-B2 citations are gone. In §9 the joint plan gets only a link both ways. |
| A9 | fixed | §9 "Upstream, after step 4 merges (O79)": the question gets an `OD-` id and a Phase 3 row, and so do its three pushbacks. The trigger is named. |
| A10 | fixed | §4: "no function outside the writer's module opens a record for writing". This is a file-write scan, not the world-writer allowlist. The remainder is N2. |
| A11 | fixed | §3: "One record per agent per log segment", with the parent segment in the header. Worker restarts open segments, which matches `npcs_and_sem.md` line 728. On/off is a log-header field (§3, §8). Whether that is the right place is D3. |
| A12 | fixed | The §2 table's "On replay" column: `refusal` is recorded only, because the log holds stage-1-accepted intents. Cancels, failures and `reply_landed` are read from the log, not copied. Tier 3's cost and the stalled-writer test wait on `phase1/lanes`' meters (§1, §9). |

## Architecture lens on the fold

- **Layer and owner.**
  - The writer is in `simcore.host`, which owns the barrier and saves. That is the right layer.
  - The record lane follows `realtime_lanes_coop.md` §4.1's pattern by link.
  - Segmenting follows `inference_placement.md` §4.2 by link.
  - The tick-field rule is attributed to `schema.py` and tile §3.2. This matches the code's own citation (`schema.py:12`, `:424`), although tile §3.2's heading is `kindle`.
  - The engine/game split is right: record, lane and gate are engine; audiences and fiction are game.
- **Contracts in two places.** The fold removed the big duplications (log facts and memory writes). Two small restatements remain (N1, and the reactivation count in N5).
- **Silently amended decisions.** I found none. Every outside edit is in §8 as a proposal. One amendment is phrased as settled: §3 says "Whether the record was on **is** a field of the log header (§8)", while §8 says it is only proposed. That is honest enough under a status line that says "Nothing here is decided", but see D3.
- **Band-aids.** I found none. A `stopped` gap for a value that fails anyway is a typed status with a meter, not a swallow (§3).
- **Decided versus proposed.**
  - §10 holds the owner's choices.
  - §8 holds the proposed edits.
  - The upstream question is a question to the EVENT seam, and its fields are left to Maxim.
  - The design holds no decision or fold table, `lint_contracts` passes, and it is within its word budget (4,038 of 6,000 for a new design).
- **Charter stop rule.** No new BLOCKER is in the text the fold added.

## New findings

### D1. SHOULD-FIX: `npc_inspector.md::§2 table "On replay"` and `§9 "Replay against the record"` contradict `§4 "The import rule"`

§2 says a `stimulus` is "re-derived, and compared with the recorded copy" on replay. §9 says replay "recomputes the deliveries in memory and compares them byte for byte with the recorded ones". Comparing them means reading the record, which goes through the one reader gate (§4: "It is the only reader in any language"). §4's import rule, though, lets only "the view's entry point and the save-copy path" import that gate, and refuses every other module through an import contract. Replay is neither of those modules.

**Failure scenario:** `phase1/agents` builds the comparison inside the replay tool, and the import contract fails it. Or the builder adds replay to the allowlist, and a record reader now sits on replay's path, which §1's "never an input" is meant to keep clear. Or the builder parses the file directly to dodge the rule, which bypasses the gate.

**Fix (unverified):** say whether the comparison is a test only (under `tests/`, outside the contract) or part of replay. If it is part of replay, name it as a third permitted importer.

### D2. SHOULD-FIX: `npc_inspector.md::§2 write_ref` and `§8` bullet 6: the pointer's key has no owner on either side, and it may need a codec field or a Maxim ask that neither section lists

`write_ref` points at "the write's sequence number" in the agent-side audit record. §8 proposes that `boundaries.md` §6.1's audit record "gets a sequence number per write". That record lives in the agent home and arrives with OD-A15. OD-A15 is a Maxim "embeddable" item (`roadmap.md` line 287) that lands after Maxim's 1.4.0 cut. So the side that assigns the number is a cross-module interface, and v2 doesn't state it:

- **If Maxim numbers its writes,** it is a Maxim ask. §9's upstream list doesn't carry it: it names the §6 question and three pushbacks only.
- **If the host numbers them** (it already orders writes canonically before `settle`, `npcs_and_sem.md` §6.6), the number has to reach the agent-side record over `settle`. That is a codec field, against §1's "never adds a codec kind or field", or it is a `boundaries.md`/`npcs_and_sem.md` codec change that §8 doesn't list.

The pointer also has to be scoped. After a `rewound` restart, the restored home continues its own numbering, so the same number can name two different writes in parent and child segments. The record being per segment helps only if the number is scoped to the home's lineage, and v2 doesn't say that it is.

**Failure scenario:** OD-A15 lands with no per-write number, or with one reset at each session. Every `write_ref` either cannot be built or points at the wrong write after a restart, and the explorer joins writes to the wrong cause.

**Fix (unverified):** state who assigns the number and what scopes it. Then add the matching line to §8: a codec field, by its owner. Or add it to §9: the Maxim ask under OD-A15.

### D3. SHOULD-FIX: `npc_inspector.md::§3` ("Whether the record was on is a field of the log header") and `§8` bullet 1: an observation setting in the world log's header meets the header's refuse-on-mismatch rule and can't express a toggle within a run

`boundaries.md` §6.3 refuses a replay on a content mismatch and holds the rerun manifest to the same rule. v2's on/off test (§1, §9) compares a record-on run with a record-off run. The header flag makes those two logs differ. Nothing says whether the flag counts as content, so it is undecided whether a tool that refuses on a header mismatch, or compares logs byte for byte, will treat the two runs as different runs. The `off` gap reason also implies the record can be switched off inside a segment, so a header written at segment start can say "on" for a segment that is partly off. The opposite case, switched on mid-segment under an "off" header, has no representation.

**Failure scenario:** the builder adds the flag as an ordinary header item. A tier-2 rerun of a record-on log, run with the record off (replay never writes one), is refused as a content mismatch, and the on/off invariant test can't be run through the shipped replay path. Or a save's record exists under a header that says "off", and §3's "a missing record reads as off" rule has a case it doesn't cover.

**Fix (unverified):** in §8's proposed §6.3 edit, mark the flag as metadata that is never refused on and never digested, as §6.3 already does for dilation. Say whether a mid-segment toggle is allowed, and if it is, how it is recorded in each direction.

### N1. NIT: `npc_inspector.md::§2 stimulus` partially restates `BoundFrame`'s fields

The row lists "its tick, bindings digest, one value per binding, the receipts it carried". That is `sem_stimuli.md` §4.2's `BoundFrame` without `registry_digest` and `events`. The class is never named, and the field list is not linked to its owner. When sound lands, `events` stops being empty and the row goes stale. This is the restatement the one-owner rule forbids.

**Fix (unverified):** say the row holds the delivered `BoundFrame` (§4.2) plus the receptor and site resolved from the table it names, and drop the field list.

### N2. NIT: `npc_inspector.md::§4 "The writing scan"` and `§3` ("A save carries each record truncated at the save's barrier")

The save-copy path writes a truncated record into the save. That is a function outside the writer's module opening a record for writing, which the scan forbids.

**Fix (unverified):** put truncation in the writer's module, or name the save-copy path in the scan.

### N3. NIT: `npc_inspector.md::§4 "The reader"`: the gate's output, which Godot and web views read, is an interface with no owner

"A Godot or web view reads only that gate's validated output, never the raw file." That output crosses from Python to another language, so it is a format between modules, and it is contract. v2 neither states it nor defers it.

**Fix (unverified):** defer it by name to §10 item 6's UI choice, or state its owner.

### N4. NIT: `npc_inspector.md::§10 item 7`: "It can be reviewed and merged before step 4, like PR #81"

Neither the step 4 brief nor the roadmap says PR #81 merges before step 4. The brief's only amendment names the two late branches. I did not check the PR's state.

**Fix (unverified):** cite where #81's path is decided, or drop the comparison.

### N5. NIT: `npc_inspector.md::§2` opening, against `write_ref` and `stimulus`

§2 says the record holds "only what neither the world log nor the agent's own audit record holds". Two rows don't quite fit that:

- `write_ref` copies "the count of reactivated trace ids", a fact the audit record's entry already holds.
- `stimulus` is, by §2's own table, re-derivable from the log.

The `stimulus` copy is defensible as a check copy, but the sentence overstates the rule.

**Fix (unverified):** drop the count, or keep it and soften the sentence to say the record holds check copies that are compared, never trusted.

## Summary

| Severity | Count | Findings |
|---|---|---|
| BLOCKER | 0 | none (the charter's stop rule is not triggered) |
| SHOULD-FIX | 3 | D1, D2, D3 (all in text the fold added) |
| NIT | 5 | N1–N5 |

**Round-1 statuses:** 11 fixed and 1 open (A3, with a narrow remainder). Every proposed fix in this report is unverified.
