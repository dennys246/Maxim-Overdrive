# NPC inspector design: Trust boundary review (round 1)

**Lens:** Trust boundary (`docs/code_review.md`). **Reviewed:** `docs/design/npc_inspector.md` and its new `mind_record.kinds` row in `docs/design/contracts.md`, as staged on `phase3/npc-inspector`. The staged tree is `00b97665`, against Overdrive `origin/main` `e6d6a7f`. **Read for context:** `CLAUDE.md`; `docs/code_review.md`; `boundaries.md` §5.3, §5.4, §6.1–§6.3; `npcs_and_sem.md` §5.2, §6.6; `decisions/npcs_and_sem.md` O13, O14, O17, O18, O26, O28; `inference_placement.md` §2.6, §4.2; `inference_gateway.md` §2 (its log) and §6 (consent and taint); `src/simcore/host/server.py`; `src/simcore/core/text.py`; `scripts/lint_inputs.py`; `scripts/lint_gates.py`. **Ran:** one read-only probe of `simcore.core.text.player_text` in the worktree's own venv (below). For Maxim I read only `src/maxim/console/server.py`'s header in the local clone at HEAD `70f0fa88`, which is not the design's `b90800e`, so that claim is marked as read at another revision. I fetched nothing and installed nothing.

**What holds.** §1's rule (never call `AgentPort`, no new codec kind, nothing runs in a worker) adds no new way into the worker channel. That is the strongest trust property here, and it is right. §7 keeps the host's `127.0.0.1`/`Origin`/token rule closed and says a web client would be a protocol change. §5 names the host-data leaks (`energy_status`, `memory_recall`, pulse's `ts`) and keeps them out. Writing the record without gzip removes the decompression-bomb case from its reader. The findings below are about which values reach the record and in what state, who can purge them, what leaves in a bug report, and how a viewer reads and draws them.

---

## BLOCKER

### TB-B1. The purge can't reach the record as specified, and O26 already says it must
**Location:** `npc_inspector.md::§3 "Guest text"`, `::§2` (entry fields), `::§9 item 4`.

**Defect.** §3 says a guest's purge "redacts the record's spans", and §9 item 4 asks the owner whether the record joins O26's reach. That question is already decided. O26 sets O17's reach as "the agent stores, continuation bodies, the response cache's requests, **saves** and the intent log", and §3 puts the record inside the save. Answering "no" would break O17 ("purged on request"). More important, the format gives a purge nothing to find spans by. Of the entry kinds, only `write` carries provenance ("with provenance as stamped"). Guest words also reach other kinds:
- `receipt`: a `speak` receipt "carries the spoken prefix" (`npcs_and_sem.md` §5.2);
- `thought`: it holds the "triggering input", which for a dialogue thought is the guest's line, and its speech can quote the guest (O26: "a reply that quoted the purged words is redacted too");
- `percept`: once speech is heard through a B-13 sound channel (Phase 4), the percept holds the heard text;
- `intent`: an NPC's `imagine` label or written text authored from guest words carries taint (`inference_gateway.md` §6, O51).

**Failure scenario.** Guest S tells NPC A a secret. A's memory write carries S's provenance, and the purge removes it. The same words are also in A's `thought` entry (as the triggering input) and in the `receipt` of A's reply quoting them. Neither entry carries a provenance set, so the purge has no key to find them. The save keeps S's words in plain JSON lines after a purge reported complete, and O26's redaction records claim spans that are still on disk.

There is a second purge target too. `boundaries.md` §6.1 already plans "an agent-side audit record after OD-A15" for memory writes. The record's `write` kind is a host-side copy of the same text, and the design doesn't relate the two.

**Fix (unverified).**
- Declare the record inside O26's reach as a consequence of O26, not as a question for the owner.
- In v1 of the format, give every entry that holds text a provenance/taint set. Use the host's lower bound: O26's provenance and O51's taint.
- Name the exit test: the relay-and-concept exit test of `npcs_and_sem.md` §6.6, extended to the record.
- Say how the `write` kind relates to OD-A15's audit record.

This is contract (a format field and a leak rule), so it folds now. Records written later without the field would need a migration to become purgeable.

### TB-B2. A default bug report still ships guest speech, against O17
**Location:** `npc_inspector.md::§3 "Saves and bug reports"`.

**Defect.** By default a bug report "drops `thought` speech and `write` text", and that is all it drops. By TB-B1's list, guest text also sits in `receipt` prefixes, the `thought` triggering input, heard-speech `percept`s and authored `intent` labels. All of those stay in a default report. O17 is not a default: guests' speech "is … **never** shipped in a bug report". Phrasing the record's rule as "by default" also makes guest-derived `write` text shippable once someone opts in, which O17 forbids.

**Failure scenario.** A host files a bug report with the defaults after a co-op session. The record's receipts carry the spoken prefixes of NPC replies that quote a guest, and the thought entries carry the guest's triggering lines. The guest's words are now in a public issue.

**Fix (unverified).**
- State the rule over every text field the format declares, not over two kinds:
  - any span whose provenance or taint holds a guest is never included, with or without opt-in;
  - other speech and memory text is dropped by default, keeping lengths and ticks, as for `speak` in the log.
- Add a test: the format's text fields, enumerated from the schema, against the bug-report filter. A new text field that the filter doesn't cover goes red.

---

## SHOULD-FIX

### TB-S1. The record copies values from before the gates, not after them
**Location:** `npc_inspector.md::§1` ("values the host already holds because they crossed the membrane"), `::§2 intent`, `::§2 thought`, `::§2 write`.

**Defect.** "Crossed the membrane" covers values the codec decoded but the host's gates then refused or haven't checked:
- **`intent` with "its stage-1 result".** For an intent refused at stage 1 there is no typed canonical `params`. If the record keeps what arrived, it holds the raw worker payload, which `boundaries.md` §6.2 allows in the log only as "an optional audit field".
- **`write`.** The host's gate on memory-write content is a gate-to-be: OD-A18 is OPEN, with a strict red gate (`boundaries.md` §5.3). Until then a memory write's text is model output that only the codec has bounded. It can hold bidi overrides, line separators, terminal escapes or markup.
- **`thought` "as the host's continuation header sees it".** The header holds `held_reply`, the raw model reply text (`npcs_and_sem.md` §6.6). The sentence "never holds prompts or raw model text" contradicts that, but §2 doesn't exclude `held_reply` by name. The tail cut by `truncated(prefix, reason=validation)` is in `held_reply` too.

**Failure scenario.** A compromised or prompt-injected worker emits an intent built to be refused, plus a memory write whose text carries U+202E and `ESC[2J`. Neither ever reaches the world. Both land in the record and, from there, in saves and in a viewer (TB-S2).

**Fix (unverified).**
- Every entry records only post-gate values. A stage-1 refusal records its kind, its refusal code (`refusal.codes`) and its lengths, never the params.
- Text enters only after a named text gate (`player_text`'s rules, or a model-text gate that refuses at least Cc/Cf, bidi controls and the `splitlines` separators). Otherwise the entry keeps the length only.
- `write` text stays length-only while OD-A18 is open, so the record inherits the gate-to-be status instead of hiding it.
- §2 names `held_reply` and the agent-owned body as excluded.

### TB-S2. No rendering rule: a viewer can interpret record text as markup
**Location:** `npc_inspector.md::§7` (both candidate UIs; the live view).

**Defect.** The record will hold LLM and guest text even after TB-S1. `player_text` keeps punctuation by design, so markup passes it. *Verified* in the worktree's venv: `player_text("[img]user://x.png[/img] hi", …)`, `player_text("<img src=x onerror=alert(1)>", …)` and `player_text("[url=https://evil]click[/url]", …)` all return unchanged. Only `"\x1b[2J …"` was refused. The one rendering rule in the tree is the client's own speech rule: "The client renders speech as plain text, BBCode off" (`npcs_and_sem.md` §5.2). The inspector doesn't inherit it, and an inspector panel is exactly where someone turns on `RichTextLabel.bbcode_enabled` to colour the "readout" and "self-report" labels apart.

**Failure scenarios.**
- **(b) in Godot.** A record field containing `[img]user://…[/img]` makes the viewer load a file from the player's user directory. `[url]` makes a clickable link.
- **(b) as a static page, or (a) in pulse.** Text inserted via `innerHTML` (or React's `dangerouslySetInnerHTML`) runs script from a stranger's save in the viewer's origin.
- **A developer CLI.** It prints model-written memory text whose escapes rewrite the terminal. This needs TB-S1 to be unfixed.

**Fix (unverified).** Make it contract in §7:
- every text field from the record is drawn as plain text, with no BBCode, HTML or Markdown interpretation;
- a terminal view escapes C0, C1 and bidi controls;
- each view gets a test with a planted markup string, for every view built: a `RichTextLabel` with BBCode off, or a `Label`, in Godot; `textContent` in a browser.

### TB-S3. The read gate's placement and registry row are left conditional
**Location:** `npc_inspector.md::§3` ("A view reads it through a file gate (`adapters/loaders.py`'s pattern) … If the gate is in Python, it gets a row in the gate registry"), with `::§3` "Nothing in the engine reads it".

**Defects.**
1. **"If the gate is in Python" lets the gate leave the registry.** `scripts/lint_gates.py` (`GATE_MODULES`) and `scripts/lint_inputs.py` (`INPUT_GATES`) see only Python. A GDScript or TypeScript reader of a stranger's record gets no row, no 100% branch floor and no rejection-path module. The tree classes records like this as "Scene files, saves, intent logs, bug reports … strangers' machines … the strictest gate (world_model F14): no pickle, budget before allocation, all-or-nothing" (`boundaries.md` §5.3). The "if" lets the format a viewer depends on most skip that gate.
2. **"`adapters/loaders.py`'s pattern" conflicts with §3's own import rule**, which forbids any module under `simcore.adapters` from importing the record's reader. The gate's module is unnamed, so its registry row and its `INPUT_GATES` entry ("A new gate joins this list … in the change that makes it") have nowhere to go.
3. **No budgets are named.** §5.4 requires budgets before allocation. §2's size paragraph meters the writer's rate but doesn't bound what a reader accepts: bytes per line, entries per file, the length of each string, nesting.

**Failure scenario.** A shared save carries a 4 GB single-line `.jsonl`, or one line with 10⁶ repeated keys. A Godot `JSON.parse_string` viewer allocates it all, or keeps the last duplicate key (which the tree's strict decoder exists to refuse). No lint notices, because no row exists.

**Fix (unverified).**
- Name one Python gate module outside `simcore.core` and `simcore.adapters` (in the game package or a tool), reading through `simcore.core.schema` and `simcore.protocol.strict_json`'s rules. Give it a registry row and an `INPUT_GATES` entry.
- Any non-Python view reads only that gate's validated output, never the raw file.
- State the reader's budgets in §2 as contract, derived from the codec's size budgets ("measured at step N" is fine).

### TB-S4. What a refusal at write does is unstated, and a worker can trigger one
**Location:** `npc_inspector.md::§1` ("A planted wall-time field is refused at write"), `::§3` (written at the barrier).

**Defect.** The writer runs at the barrier on values a worker controls. Two outcomes are unsafe:
- if a value the codec accepts can be refused by the record's schema, a hostile worker can make the barrier raise;
- if the writer catches the refusal and drops the entry quietly, that is the silent swallow `CLAUDE.md` bans.

The design says neither what happens on a refusal nor that one can't happen.

**Failure scenario.** A worker sends a well-formed `step_output` whose field fits the codec but breaks a record bound. The writer raises in the barrier, the tick never completes, and every other NPC stalls. That is a worker-induced denial of service the codec was meant to rule out (`npcs_and_sem.md` §6.6: "A hung or dead worker never freezes the world").

**Fix (unverified).**
- Derive the record's per-field bounds from the codec's, so a value that passed the codec can't be refused at write (a test asserts the bounds are equal).
- Make an internal refusal a typed host record with a closed code that is counted, never an exception through the barrier.
- Add the world-digest on/off test with a planted oversized value.

### TB-S5. Host data is excluded by example, not by a closed list
**Location:** `npc_inspector.md::§1` (clock), `::§2 thought` ("cancel or failure"), `::§2 lifecycle`, `::§5 "Host data never enters the record"`.

**Defect.** §1 refuses wall time only. §5 lists three Maxim sources. The record is persisted in saves, and the save directory sits under the user's home. Several host values are close to entries and are not excluded by name:
- **Paths.** The agent home's path holds the account name.
- **Exception and stderr text** from a crashed worker.
- **OS process ids.**
- **Gateway detail on a failed thought.** Placement, endpoint, provider error text: `inference_gateway.md` §2 says "No other log, meter, manifest, cache entry or save may hold either".
- **The log header's environment block** (`platform.machine()`, CPU dispatch features), if "a header with the run's log root id" grows to copy more of it.

**Failure scenario.** A natural implementation of the `thought` failure entry copies the gateway's outcome (`failed(auth)` with its error text). A `lifecycle` entry for `agent_failed(crashed)` copies the worker's last stderr line, which holds `<home>/…/saves/<name>/agents/…`. The save is then shared.

**Fix (unverified).** In §2, state each kind's fields as a closed schema. Failures use only `thought_failed.reasons` and `agent_failed.reasons`, never outcome detail, placement or text. The header names exactly root id, segment and scene digest. A planted path, exception string or OS pid is refused at write, beside the wall-time plant.

### TB-S6. The audiences are display filters over a file that holds everything; saves shared between players aren't addressed
**Location:** `npc_inspector.md::§5 "Audiences"`, `::§5 "World truth through an NPC's senses"`, `::§7` (live view).

**Defect.** §5 separates developer, player and guest views, and §9 asks whether depth is "earned in the fiction". But §3 writes the full record, including every percept, into the save. Any player can open that file in a text editor, so the curated tiers are presentation, not confidentiality. The design doesn't say so, and it doesn't say whether the full record ever reaches a machine other than the host's. That matters in three places:
- once line of sight exists, percepts reveal what a player can't see;
- with co-op guests, when a save is handed to a guest or a third party;
- in the Phase 4 live view, whose "curated slice" must be cut on the server, or the guest's client holds the whole thing.

**Failure scenario.** In Phase 5 co-op, the host shares the save with guest B so B can host the next session. B opens the record and reads guest A's words held in an NPC's memory, which A never said within B's hearing. B also reads every percept that line of sight was meant to hide.

**Fix (unverified).**
- State that §5's tiers bind only what a view shows.
- State the confidentiality rule as contract: the full record never leaves the host's machine except in a save or bug report the host chooses, filtered by TB-B2; a guest's client receives only the server-cut slice; handing a save to another person is a disclosure covered by O54 and O55's consent.

The last part is the owner's ruling. Name it in §9.

### TB-S7. A browser viewer's transport is unspecified, and the nearest server follows a different Origin rule
**Location:** `npc_inspector.md::§7 (a)` and `::§7 (b)` "a static page".

**Defect.** A browser can read a local record without a server only through a file picker. Otherwise something listens on localhost. §7 rules out the world server, which is correct, but leaves open the obvious path for option (a): pulse's kit served by Maxim's console. In the Maxim clone at `70f0fa88` (not `b90800e`), `console/server.py`'s header says it accepts `/ws` upgrades from *trusted* origins, uses a token stored under the home directory, and "holds keys and can reconfigure Maxim". That is a different rule from Overdrive's, where any Origin is refused (`server.py:58-60`).

**Failure scenario.** The explorer ships as pulse plus a file-backed client served by `maxim serve`. Guest-text records are now readable by any origin on the console's trusted list, through a process that holds provider keys.

**Fix (unverified).** State as contract that an offline viewer opens the record only through a user-chosen file and starts no network listener. Any listener that serves the record follows `boundaries.md` §5.3's handshake (`127.0.0.1`, no `Origin`, a per-launch token), or is a design change reviewed on its own.

---

## NIT

- **TB-N1** `::§4 "Replay"`: nothing binds a foreign record to the world log beyond the header's root id and scene digest. A forged record can present "recorded" entries that contradict the log and diagnose the wrong cause in a bug report or rerun comparison. Have the gate check the entries that can be re-derived (intents, speech, receipts) against the log, and mark mismatches. *(unverified)*
- **TB-N2** `::§6 "It serves three consumers"` and the game-evidence link: if records (as opposed to the state readout) are ever handed upstream as evidence, that is a release of guest words beyond the machine (O18; O54, "only S may release S's words"). Say the records that go upstream come from single-player runs only, or follow §6 consent.
- **TB-N3** `::§7` live view: a purge can't recall what was already pushed to a guest's client. Note it as a known limit of the Phase 4 view, beside O26's replay boundary.
- **TB-N4** `::§2 percept`: "region, receptor, site and value, as the agent received them". A region name is an authored string (`visible_name`, IDNA), but an imagined object's label is a guest or NPC string with taint (O51). The percept carries the label's provenance (TB-B1) and passes TB-S2's rendering rule.
- **TB-N5** `::§1` "A planted wall-time field is refused at write": the record's own clock comes from the host, but the design should also say the writer reads no clock to *name* files (a dated filename is wall time on disk). Same plant.

---

## Summary

| Id | Severity | Location |
|---|---|---|
| TB-B1 | BLOCKER | §2, §3, §9.4: no provenance on text-bearing kinds; O26 already covers saves |
| TB-B2 | BLOCKER | §3: a default bug report keeps receipt prefixes, triggering inputs and percepts; O17 says never |
| TB-S1 | SHOULD-FIX | §1, §2: copies values from before the gates (refused intents, memory writes under OD-A18, `held_reply`) |
| TB-S2 | SHOULD-FIX | §7: no plain-text rendering rule; markup passes `player_text` (*verified*) |
| TB-S3 | SHOULD-FIX | §3: the gate's registry row is conditional; its module conflicts with §3's import rule; no read budgets |
| TB-S4 | SHOULD-FIX | §1, §3: a write refusal at the barrier is unspecified |
| TB-S5 | SHOULD-FIX | §1, §2, §5: host data excluded by example, not by a closed schema |
| TB-S6 | SHOULD-FIX | §5, §7: audiences aren't confidentiality; shared saves |
| TB-S7 | SHOULD-FIX | §7: a browser viewer's transport, and Maxim's console Origin rule |
| TB-N1–N5 | NIT | as listed |

No finding reopens the world server's `127.0.0.1`/`Origin`/token rule. §7 keeps it, and TB-S7 asks that any new listener inherit it.
