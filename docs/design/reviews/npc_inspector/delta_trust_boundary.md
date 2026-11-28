# NPC inspector design: Trust boundary delta review (round 2)

**Lens:** Trust boundary (`docs/code_review.md`). **Reviewed:** the fold diff `git diff bd0137d -- docs/design/npc_inspector.md`. v2 is the working-tree blob `20b6cbb1` (4,038 words), against Overdrive `origin/main` `e6d6a7f`. I set the statuses from the v2 text and the sources it cites. I did not take them from `fold.md` (blob `5791d71e`), which was read only as the author's claims. **Read:** `npcs_and_sem.md` §5.2, §6.4, §6.6 (the continuation header, receipt projections); `sem_stimuli.md` §3.2, §4.2 (`BoundFrame`, `StimulusEvent`), §6.2 (receipts, `receipt.kinds`); `boundaries.md` §5.3 (gate table, handshake), §6.1 (the audit record, redaction records), §6.2; decisions O17, O18, O26, O54, O55; `src/simcore/host/server.py:6, 58-60`; `scripts/lint_inputs.py::INPUT_GATES`; `scripts/lint_gates.py` header. **Ran:** nothing beyond `git` and `grep`. I fetched nothing, installed nothing and did not open Maxim.

**Verdict.** The fold's central move, a record with no free text, is the right root fix, and for the kinds v2 lists it mostly holds. There are three things wrong with it:
1. **The no-free-text claim depends on a contract v2 doesn't cite and that another section contradicts.** The `stimulus` row copies "the receipts it carried". The receipt's owner (`sem_stimuli.md` §6.2) makes a receipt `(pid, kind)`, but `npcs_and_sem.md` §5.2 still says a speech receipt "carries the spoken prefix".
2. **Nothing in §9 guards the claim.**
3. **The fold's transport and single-reader rules together rule out both browser UIs that §7 and §10 item 6 offer the owner.** Browsers always send `Origin`, and §5.3 refuses it.

None of the new findings is a BLOCKER, and no new BLOCKER sits in text the fold added. TB-B1 and TB-B2 are fixed, conditional on new finding D-S1.

## Status of round-1 findings

| Id | Status | Evidence (v2 tree) |
|---|---|---|
| TB-B1 | **fixed** (conditional on D-S1) | §2:70-74 removes every text-bearing copy: `write` becomes `write_ref` (sequence number, kind, count), `thought` becomes `thought_state` (counters only), and intents and speech are read from the log. Field by field: binding receptor and site names are authored binding-table data (`sem_stimuli.md` §3.2), not guest strings. The triggering input id is an id. Refusal codes are `refusal.codes`. The intent kind is recorded only "if it parsed", so it comes from the closed intent vocabulary. Gap entries are ticks plus a closed reason. The header holds ids and digests. The one weak point is "the receipts it carried": see D-S1. "Text stays in the log and audit record, which O26 already reaches" holds: O26 names "saves and the intent log", and the audit record is "saved with the agent home" (`boundaries.md` §6.1:397-399), so it lies inside "saves". The live, unsaved audit record is reached only if it counts as one of O26's "agent stores", which neither document says (D-N2). |
| TB-B2 | **fixed** (conditional on D-S1) | With no text in the record, the record adds nothing for a bug report to drop (§2:74). Whether a bug report ships the agent home's audit record, which O17 covers, is outside this design (D-N2). |
| TB-S1 | **fixed** | The `refusal` row says "never its parameters". "Excluded by name" (§2:96-102) lists the held reply, the agent-owned body, raw model text and "anything decoded from a refused frame". `write` text is gone, so OD-A18's open gate no longer reaches the record. |
| TB-S2 | **fixed** | §7:288-292 makes plain text a rule for every view: Godot `Label`, or `RichTextLabel` with BBCode off; `textContent`; terminal views escape C0, C1 and bidi controls. Every view gets a planted-markup test (§9:338). |
| TB-S3 | **fixed**, with residuals | §4:171-173: there is one Python gate in `simcore.host`, it is the only reader in any language, and it gets a gate-registry row and an `INPUT_GATES` entry. `simcore.host` already holds an input gate (`lint_inputs.py:47`), so the lint machinery accepts that placement. The reader's budgets are contract (§3:165-166). Residuals: the browser path breaks "only reader" (D-S2), and one of the three budgets can't come from the codec (D-N1). |
| TB-S4 | **fixed** | §3:158-160: every record bound equals its codec bound, with a test. A value that fails anyway becomes a `stopped` gap, "never an exception at the barrier". §9:336-337 adds a plant with the world digest unchanged. Blast radius: D-N3. |
| TB-S5 | **fixed** | "Excluded by name" (§2:96-102) covers paths, exception text, pids, the host environment and the gateway's outcome detail. Failures are shown by closed reasons only (§2:104). §3:141-146 states the header's fields as a closed list. The plants are in §9:335. |
| TB-S6 | **open** (one part) | Fixed: §5:188-192 says the tiers bind display, not confidentiality; the record leaves the host only in a save or bug report the host chooses; a guest's client receives a server-cut slice. Open: "Handing a save to another person is a disclosure under O54 and O55's consent rules" claims rules that don't exist. O54 governs purge and release "to a remote class" (an inference class), and O55 defines who the speaker is. Neither says that handing a save to a person needs consent. Round 1 asked for this to go to the owner as a ruling, and §10 doesn't list it. See D-S3. |
| TB-S7 | **fixed** as stated | §7:284-287: a file the user chose; no listener; any listener uses §5.3's handshake; Maxim's console is named as differing. D-S2 shows what this rules out. |
| TB-N1 | **fixed** for what it named | Intents, speech and receipts now come from the log, so a forged record can't contradict them. Stimuli are re-derived and compared (§2 table; §9:332-333). Residual: `refusal` and `thought_state` are "recorded only", so a foreign record can forge them and nothing can check. A view of a stranger's record should label them unverifiable. NIT, unverified. |
| TB-N2 | **open** | The fold says there is "no guest text, so no release question" (fold.md). But §6:269-270 names a consumer that compares reports with recordings "over game runs", and reports are speech from the log (§2:115), which includes guest speech. Sending that evidence upstream releases guest words beyond the machine, which O18 and O54 ("only the speaker may release") govern. The fix stands: name single-player runs, or §6's consent. |
| TB-N3 | **fixed** | §7:305-306: a purge can't recall what was already shown, a known limit beside O26's replay boundary. |
| TB-N4 | **fixed** | The `stimulus` row resolves receptor and site from the binding table it names, and no label or region name enters. `StimulusEvent` is numeric (`sem_stimuli.md` §4.2:193). |
| TB-N5 | **fixed** | §1:66: "the writer reads no clock, including for file names". |

## Trust lens on the fold

- **The single Python gate in `simcore.host`.** The placement is sound. The layer is already a gate home. The import rule names the gate's module and refuses the host's restore path (§4:174-175), which keeps the record an output. "Strictest class of input" cites §5.3/§5.4, and §8 lists the §5.3 gate-table row. The weakness is outside Python: D-S2.
- **Budgets.** They are contract and derived from the codec. "Bytes per line" and "values per delivery" can come from the codec. "Entries per file" can't (D-N1).
- **The plain-text rule.** Correct and complete for the three view kinds. It covers authored strings too ("All of it").
- **The file-picker transport.** It is correct for Godot, which can call the Python gate through a process without a listener. It is broken for browsers (D-S2).
- **Confidentiality and O54/O55.** Mostly fixed. The save-handover sentence overclaims what the decisions say (D-S3).
- **Failure handling.** Gaps with closed reasons, a typed host status and a meter make missing data explicit rather than silent. That is the right trust property: a view can't mistake a hole for "nothing happened". The open question of stopping the run is correctly put to the owner (§10 item 4). Residual: D-N3.

## New findings in text the fold added

### D-S1. SHOULD-FIX: the no-free-text claim depends on a receipt form the `stimulus` row doesn't name, and another section contradicts it
**Location:** `npc_inspector.md::§2` (the `stimulus` row, "the receipts it carried"; the "no free text" claim at :70); `::§9` (no test).

**Defect.**
- **The receipt form.** v2's guest-text and bug-report folds rest entirely on the record holding no free text. Its only copy of a structured agent-facing value is a delivery's receipts. The receipt's owner, `sem_stimuli.md` §6.2:315-320, makes the delivered receipt `(pid, kind)` over the closed `receipt.kinds` vocabulary, which supersedes the "measured effect". But `npcs_and_sem.md` §5.2:530 ("Its receipt carries the spoken prefix") and :348 ("the spoken prefix, which the speech receipt carries") still stand. `npcs_and_sem.md` §6.6:839-841 adds a second projection, the "full receipt" that `settle` gets. The row doesn't say which receipt it copies.
- **No guard.** §9's plants refuse paths, exception text and pids. No test asserts that the schema has no free-text field at all. A future field that holds text, say a `readout` value with a string, or a receipt carrying a prefix, passes every listed test unless someone happens to plant exactly that.

**Failure scenario.** The writer's implementer follows `npcs_and_sem.md` §5.2 and copies the speech receipt with its prefix. Guest words are now in the record with no provenance. That is round 1's TB-B1 scenario again, and §2 tells reviewers the record "holds no free text", so nobody looks.

**Fix (unverified).**
- The `stimulus` row names the receipts as `sem_stimuli.md` §6.2's `(pid, kind)`, `receipt.kinds`, never the `settle` projection.
- §8 lists the stale prefix sentences in `npcs_and_sem.md` §5.2 for their owner to reconcile.
- §9 adds a schema test: every string field in the record's schema is a registered closed vocabulary, an authored id, or a digest. Prove it by adding a free `str` field and watching the test go red.

### D-S2. SHOULD-FIX: under v2's own rules, neither browser UI can be built without bypassing the gate
**Location:** `npc_inspector.md::§4` ("the only reader in any language … a Godot or web view reads only that gate's validated output"); `::§7` "Transport"; `::§7` "Which UI" (pulse's kit, a static page); `::§10` item 6.

**Defect.** A browser view gets the gate's output in one of two ways, and v2 forbids or undermines both:
- **Through a listener.** The listener must follow `boundaries.md` §5.3's handshake, which refuses any request carrying `Origin`. Browsers always send one (`server.py:6`, `:58-60`, verified by reading). So no browser can connect, by construction.
- **Through a file the user picks.** The gate would have to write a "validated" export file, and the page parses that file. The page can't tell a gate export from a hand-made file, so the page becomes a second reader of an untrusted file. "Only reader in any language" is then false for the browser path.

The fold took both rules from round 1 (TB-S3, TB-S7), and the conflict is new in v2. A Godot view can satisfy both by running the Python gate as a child process and reading its output, with no listener. §10 item 6 still offers the owner pulse's kit and a static page as though either fits the contract.

**Failure scenario.** The owner picks pulse's kit. The builder can't use a listener, so the gate writes `inspector_export.json` and pulse's page opens it with a file picker. Someone shares a crafted "export" next to a save. The page parses it with `JSON.parse`, with no budget, no duplicate-key refusal and no closed schema. That is round 1's TB-S3 failure, reached through a path v2 appears to forbid.

**Fix (unverified).** Choose one, as contract:
1. Browser views are out of contract until a reviewed design gives them a transport. §10 item 6 narrows to Overdrive's Godot viewer, or to pulse after that design.
2. A browser view re-validates against the same schema, through a generated validator held equal to the Python gate's by a shared fixture set. That validator gets its own row, and "only reader" is reworded to "one schema".
3. A localhost listener for the viewer with its own reviewed handshake: an exact-origin allowlist plus a per-launch token. That is a §5.3 change and gets its own review, which §7 already allows.

### D-S3. SHOULD-FIX: the save-handover consent rule cites decisions that don't hold it, and it isn't put to the owner
**Location:** `npc_inspector.md::§5:191-192`; `::§10`.

**Defect.** "Handing a save to another person is a disclosure under O54 and O55's consent rules". O54 is "only the speaker may release them to a remote class", and its reach is inference classes (IG §6). O55 defines the speaker's persistent identity. Neither covers giving a save file to a person. The sentence makes up a rule and attributes it to two live decisions. That matters even though the record holds no text: the save it travels in carries the log's speech and the audit record's guest memory text, and §7's explorer is built to display exactly that.

**Failure scenario.** In Phase 5, the host gives a save to guest B. A reviewer checks O54 and finds no rule about save handover, so nothing enforces consent. B's explorer shows guest A's words from the log and the audit record, while §5 says this was governed.

**Fix (unverified).** Reword it as an open question: "whether handing a save to another person needs the speakers' consent (O54's release rule extended to people) is the owner's ruling". Add it to §10.

### D-S4. SHOULD-FIX: views read audit-record text from a stranger's agent home, and no reader or gate for it is named
**Location:** `npc_inspector.md::§1:45-46` ("No such reader exists yet, so until one does, the record and the logs are the only sources"); `::§2` `write_ref`; `::§7:288-289` ("a view also shows … audit-record text"); `::§4`; `::§8`.

**Defect.** v2 moves memory text out of the record into the agent-side audit record, which is saved inside the agent home. It then has views display that text. §1 says nothing may read an agent home until a reader exists that is shown not to touch it, and §4 names a gate only for the record. A stranger's save is the strictest input class, and the audit record's reader has no gate, no budgets, no row and no owner. §8 asks OD-A15 for a sequence number but not for a gate.

**Failure scenario.** The explorer resolves each `write_ref` by opening the agent home's audit file with an ad-hoc parser, the easiest path because §4's gate doesn't cover it. A crafted save's audit file is a 4 GB line with markup. The plain-text rule handles the markup. Nothing bounds the allocation, and nothing refuses unknown fields.

**Fix (unverified).** Until OD-A15 lands with a reader gate, `write_ref` resolves to "not readable". §8 adds a gate row for the audit record's reader in OD-A15's owner section (`boundaries.md` §6.1), under §5.3's strictest class. §1's "only sources" sentence then names that gate.

### D-N1. NIT: "entries per file" can't be derived from the codec
**Location:** `::§3` "Size". The number of entries grows with the length of a segment, not with any codec bound. Bound it from a byte budget per segment, or from a rotation rule, measured at the build step. Otherwise the reader has to accept files of any size. *(unverified)*

### D-N2. NIT: "the log, the agent home, saves" is wider than O26's list
**Location:** `::§2:73-74`. O26's reach is "agent stores, continuation bodies, the response cache's requests, saves and the intent log". The live audit record is in reach only if it is an "agent store", and the design doesn't say so. Whether a bug report ships the agent home's audit record, which O17 says never to do, is unowned. The fix is to cite O26's list verbatim and flag both points to OD-A15's owner. *(unverified)*

### D-N3. NIT: one bad value stops the record for every NPC
**Location:** `::§3:155-160`, the `stopped` gap. The writer "stops" after an error, so one agent's out-of-bound value ends recording for all agents for the rest of the segment. A compromised worker that finds a bound mismatch blinds the inspector exactly while it misbehaves. Scope the stop to the agent whose entry failed, or say why a global stop is intended. This sits beside §10 item 4. *(unverified)*

### D-N4. NIT: say where an entry is validated
**Location:** `::§3` "The lane". Entries are "built as frozen values" in the simulation lane. If the frozen value validates in its constructor, a refusal is raised at the barrier, which contradicts :160. State that validation happens in the record lane, or that construction can't raise. *(unverified)*

## Summary

| Id | Severity | Location | In fold-added text |
|---|---|---|---|
| D-S1 | SHOULD-FIX | §2 `stimulus` row, §9 | yes |
| D-S2 | SHOULD-FIX | §4, §7, §10.6 | yes |
| D-S3 | SHOULD-FIX | §5, §10 | yes |
| D-S4 | SHOULD-FIX | §1, §2 `write_ref`, §7, §8 | yes |
| D-N1–N4 | NIT | §3, §2 | yes |

**New BLOCKERs in text the fold added: none.** Two round-1 findings stay open: TB-S6 (the consent part, now D-S3) and TB-N2. The other twelve are fixed. TB-B1 and TB-B2 hold only once D-S1's receipt form is named in the `stimulus` row. The world server's `127.0.0.1`/`Origin`/token rule is untouched.
