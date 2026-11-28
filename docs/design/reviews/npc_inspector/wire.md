# NPC inspector design: Wire integrity review, round 1

**Lens:** Wire integrity (design review, `docs/code_review.md`, "Wire integrity: contracts in this codebase"). **Read:** the staged diff `git diff --cached origin/main` in the `phase3/npc-inspector` worktree (staged tree `00b97665`, base `origin/main` `e6d6a7f`): the new `docs/design/npc_inspector.md` and the new `mind_record.kinds` row in `docs/design/contracts.md`. Outside the hunks I read `npcs_and_sem.md` §3.4, §5.2, §6.1–§6.6, §7.1–§7.3 and §9; `boundaries.md` §5.3, §6.1–§6.3 and §7.2; `sem_stimuli.md` §0, §4.1–§4.5, §5 and §6.1–§6.2; `inference_placement.md` §2.6 and §4.1–§4.2; `client_rendering.md` §4.1; `tile_and_client.md`; `sim_core.md` §14; `decisions/npcs_and_sem.md` (O26); `contracts.md`; `scripts/lint_contracts.py`; `src/simcore/core/schema.py`; `src/simcore/host/server.py`; `pyproject.toml`'s import contracts; and `docs/maxim_upstream/embeddable_agent_DRAFT.md` (the `StepOutput` row). **Ran:** `lint_contracts.check_contracts` over the tracked files with the staged file included, which passes; a count of blocks outside the owner holding two or more `mind_record.kinds` spans, which found none; and a `Format` declaration with a `tick` field, which is refused (F4). I didn't read Maxim or pulse; the §6 citations at `b90800e` and `a1ba1d4` are left to the Executor and Bio-faithful lenses.

## The table

| Contract (owner) | Producers, before → after | Consumers, before → after | What each consumer gets, before → after |
|---|---|---|---|
| `mind_record.kinds` (new; `npc_inspector.md` §2) | none → the host's writer at the barrier | none → explorer, bug-report exporter, purge, `lint_contracts` | → a closed list of seven kinds, `state` reserved and refused. The lint passes with this row (*verified*). |
| Mind record file and header (new; §2 "The format") | none → host | none → the view's file gate, saves, bug reports | → "strict JSON lines through `simcore.core.schema`", with a header holding the log root id, segment and scene digest. The tick field can't be declared as a `Format` today (F4), and the record has no segment or branch rule (F6). |
| Percept source: `BoundFrame` (`sem_stimuli.md` §4.2; it supersedes `npcs_and_sem.md` §7.3 by name in §6.1) | core builds, host pump sends → unchanged | worker → worker plus mind record | → the design cites the superseded §7.3 pull model and names fields (region, receptor, site) that `BoundFrame` doesn't carry (F1). |
| Continuation header (`npcs_and_sem.md` §6.6) | host → unchanged | host lane → plus mind record | → kind, triggering input id, cycle index, landing ticks and cancel status all exist there. Failure comes from the `thought_failed` log record, not the header. `held_reply` holds raw text, which the design rightly excludes. |
| Gated writes and `retrieval` writes (`npcs_and_sem.md` §6.6; the audit record in `boundaries.md` §6.1) | worker → host gate → `settle`; unchanged | `settle`; the agent-side audit record (planned, after OD-A15) → plus the mind record `write` kind | → two records of the same writes, with opposite placement rules (F2). |
| Agent receipt (`sem_stimuli.md` §6.2, `receipt.kinds`) | host, delivered in `BoundFrame` → unchanged | agent → plus mind record | → `(pid, kind)` only. The design adds an "outcome" and "the valence the adapter reported", and neither crosses to the host (F3). |
| Intent record and intents in `step_output` (`boundaries.md` §6.2, `intent_record.fields`; codec `npcs_and_sem.md` §6.6) | worker → host stage 1 → log; unchanged | log, replay → plus a mind record copy | → a second copy of logged intents, with a "tick only" stamping rule that contradicts the record's own tick fields (F7). Pid is null until G17 (F5). |
| Lifecycle records `agent_ready` and `agent_failed` (`npcs_and_sem.md` §6.6, `record.kinds`) | host → unchanged | log → plus a mind record copy | → copied, plus "sleep calls", which have no codec kind or record (F12). |
| `speak`, `thought_cancelled`, `thought_failed` (`boundaries.md` §6.1–§6.2; reasons `inference_placement.md` §2.6) | host → unchanged | log, replay → plus a copy | → copied (F7). |
| `codec.kinds` and the `step_output` schema (`npcs_and_sem.md` §6.6; versions `sem_stimuli.md` §5) | unchanged now; the [later] `state` kind adds a `step_output` field | host | → the design says "no codec kind", but the ask changes `step_output`'s format, which has its own version and gate row (F8). |
| Saves (save v0/v1, gate in `boundaries.md` §5.3) | → carries the record | load path | → a new member of a format this design doesn't own, with no owner edit named (F9). |
| Bug reports (`boundaries.md` §6.2; `inference_placement.md` §4.2) | exporter → plus the record | strangers | → speech and write text dropped. Other guest-bearing fields are unstated (F10). |
| O26 purge reach (`decisions/npcs_and_sem.md` O26) | → purge reaches the record | — | → left as a ruling for the owner (§9 item 4). Entries carry no provenance to target, and append-only conflicts with redaction (F10). |
| Import contracts (`pyproject.toml` `[tool.importlinter]`) | → one new rule | — | → the rule conflicts with the gate's suggested home (F11). |
| Gate registry (`lint_gates.py`) | → a row "if the gate is in Python" | — | → a Godot or static-page reader gets no gate rule (F11). |
| Ownership scans (`tests/test_ownership.py`) | → "gain its writer" | — | → that scan covers world writers, and the record's writer isn't one (F13). |
| `server.messages` (`client_rendering.md` §4.1) | unchanged; [Phase 4] new message | client | → deferred, linked to its owner. Correct. |
| `Origin` refusal (`boundaries.md` §5.3) | `host/server.py` → unchanged | — | → cited by file, not by its owner section (F13). |
| Upstream ask shape (owned here until a draft takes it; consumer `embeddable_agent_DRAFT.md` `StepOutput` row) | → an optional readout beside intents | Maxim, pulse | → shape only. No owner for the codec change is named (F8). |

## Findings

### F1: BLOCKER. A percept's source is a superseded contract, and the fields named aren't in the frame that replaced it

**Location:** `npc_inspector.md::§2` ("percept"), `§1` ("values the host already holds").

The `percept` kind is defined as "the frame values the agent's pulls read at its last `step` (`npcs_and_sem.md` §7.3): region, receptor, site and value, as the agent received them."
- **The source is superseded.** `sem_stimuli.md` §6.1 supersedes "the per-agent pinned frame (`boundaries.md` §4.2–§4.3, `npcs_and_sem.md` §7.2–§7.3)" by name.
- **Delivery is a push, not a pull.** It is a `BoundFrame` (`sem_stimuli.md` §4.2): `value` holds one float per binding, in binding order, and `world_set_axis` pushes it inside the worker (§4.4).
- **The named fields don't exist there.** `BoundFrame` has no region, receptor or site per value. Receptor and site come only from the binding table, through `bindings_digest`. "Region" belongs to today's omniscient region sensors, which §7.1 retires.
- **"As the agent received them" isn't host-observable.** The host knows what it encoded. Pulls and pushes happen in the worker, and transduction is Maxim's (`sem_stimuli.md` §0).
- **Noise placement is unresolved.** If percept noise (`npcs_and_sem.md` §3.4, handed to `engine.adapters.agents`) is applied worker-side, the host's value is the noise-free world value. That is exactly what §2 says a percept "never holds".

**Failure scenario:** a builder in `phase1/agents` implements percepts against the pinned-frame pull path that `sem_stimuli.md` deleted, or against `BodyFrame` (host-only, every tick). The record then shows ticks between deliveries under D14 (`sem_stimuli.md` §4.6) that the agent never received, labelled as readouts of what it perceived.

**Fix (unverified):** define `percept` as the delivered `BoundFrame`: its tick, `bindings_digest` and values, with receptor and site resolved through the binding table it names. Link `sem_stimuli.md` §4.2 rather than restating it. Call the channel "stimulus delivered", not "percept". State where noise is applied, or record that it is open.

### F2: BLOCKER. A second owner for the record of memory writes, with the opposite placement

**Location:** `npc_inspector.md::§2` ("write"), `§3` ("never inside an agent home").

`boundaries.md` §6.1 already says memory writes are "recorded in an agent-side audit record after OD-A15, and saved with the agent home." The inspector defines a host-side `write` kind written "beside the world log … never inside an agent home". It doesn't mention the audit record.

**Failure scenario:** two artifacts with independent schemas record the same gated writes, and they drift:
- a purge (O26) or a provenance change updates one and leaves the other;
- the explorer's "cause behind every line" disagrees with what the agent home's audit says was written.

This breaks "One owner per contract" (CLAUDE.md, B36).

**Fix (unverified):** either the mind record becomes the audit record, with `boundaries.md` §6.1's sentence moved to link here and its placement rule changed in the same branch, or the `write` kind links to the audit record's owner and holds only a reference.

### F3: BLOCKER. A receipt entry names fields the host doesn't hold, and mixes host-only truth into the "readout" channel

**Location:** `npc_inspector.md::§2` ("receipt"), "Two channels".

The agent's receipt is `(pid, kind)` with kinds `malformed`, `limit` and `accepted` (`sem_stimuli.md` §6.2, `receipt.kinds`). It is delivered in `BoundFrame.receipts`.
- **"Its outcome" is ambiguous** among three vocabularies: `receipt.kinds`, the wire's `intent_result.outcomes` (`tile_and_client.md` §3.3) and stage-2 results. D15 keeps the stage-2 results host-side on purpose ("Whether the target existed, was in reach or was hit is logged host-side only").
- **"The valence the adapter reported" has no producer on the host.** `execute` returns "a fixed `pending`: no name, no metadata" (`sem_stimuli.md` §4.4). D53's self-report and the valence booked at `settle` happen in the worker, and the codec's reply to `settle` is `ack`.

**Failure scenario:** a builder fills "outcome" from stage 2, because that is what the host has. The developer and player views then show, as the agent's receipt, the existence and footprint information D15 withholds from the agent. That breaks the design's own rule that a readout is "what crossed the membrane". The valence field has nothing to fill it, so it ships null or invented.

**Fix (unverified):** a receipt entry is `(pid or (actor_id, seq), kind)` as delivered, linking `sem_stimuli.md` §6.2. Stage-2 truth, if a developer view wants it, is a separately labelled host-truth channel, never a readout. Drop valence until a codec field carries it, and name that as a codec change.

### F4: SHOULD-FIX. "Through `simcore.core.schema` like every data format" fails on its first field

**Location:** `npc_inspector.md::§2` ("The format").

`Format.__post_init__` refuses any field named for ticks, at any depth ("content stores time in seconds, never ticks"). *Verified:* `Format('mind record', 1, Schema((Field('tick', Whole(0, 2**53)),)), held_by_others=True)` raises `TypeError: content stores time in seconds, never ticks: ['tick'] (tile §3.2)`. The record's core field is the integer tick.

Two more mismatches with how formats work here:
- **Migrations.** `Format` reserves migrations for formats "other people hold (saves, logs, bug reports)". The record travels in saves and bug reports, so the rule is migrate-or-refuse. The design says only "refuses a version it doesn't know".
- **Serialisation.** "Strict JSON" is the wire's integer-only parser (`boundaries.md` §9.1, O62). Percept values are float64, so the record needs the c14n-1 fixed float format, as the intent log has.

The nearest precedent is `sim_core.md` §14's intent log (a header record, one c14n-1 record per line, held by others, a gate row, golden fixtures). It has the same tick tension and isn't built yet.

**Failure scenario:** the build step discovers the format can't be declared. It then hand-rolls a reader outside `schema`, or carves a quiet exception into the tick rule. Either way it becomes a second format path.

**Fix (unverified):** cite `sim_core.md` §14 as the pattern and state c14n-1, held by others, with migrations. Name the tick-rule amendment (a log or record exemption, owned in `schema.py`'s docstring rule and tile §3.2) as a dependency shared with the intent log.

### F5: SHOULD-FIX. The explorer's intent-to-receipt join uses a key that is null for the whole [agents] build

**Location:** `npc_inspector.md::§7` ("each intent to its receipt by pid"), `§2` ("intent").

An intent's `invocation` is "null, never a stand-in … until Maxim's G17 stage builds `PhysicalEventId`; until then any non-null value is refused" (`boundaries.md` §6.2; codec in `npcs_and_sem.md` §6.6). The scripted double therefore emits null pids.

**Failure scenario:** every intent-to-receipt link in the explorer over the double's records is empty, or joins every null to every null.

**Fix (unverified):** join on `(actor_id, seq)`, which `boundaries.md` §6.1 names as "the intent id receipts carry". Use pid only once it exists. This also shows an existing inconsistency between `sem_stimuli.md` §6.2's `(pid, kind)` receipt and `boundaries.md` §6.1, which the owner of §6.2 should settle (not this design's to fix).

### F6: SHOULD-FIX. One record "per agent per run" ignores segments and branches

**Location:** `npc_inspector.md::§2` ("One record per agent per run"; "the header carries … segment").

Each restore and each restart opens a log segment (`boundaries.md` §6.3, O45; `npcs_and_sem.md` §6.6). A load opens a child segment, and the response cache, the sibling format, is "one cache per log segment … the parent's cache as it stood at the save's header snapshot" (`inference_placement.md` §4.2).

**Failure scenario:** a player saves, plays on, then loads the save. The record holds entries from the abandoned branch past the snapshot, interleaved by tick with the new branch's. The header's single segment number is wrong for all of them.

**Fix (unverified):** one record per agent per segment, with parent and snapshot rules linked to `inference_placement.md` §4.2's (not restated).

### F7: SHOULD-FIX. The record copies world-log records instead of referencing them, and its "tick and nothing else" rule contradicts what it copies

**Location:** `npc_inspector.md::§1` ("stamped with the integer tick … and nothing else"), `§2` (intent, thought, lifecycle).

The kinds `intent`, `lifecycle` and thought speech and failure copy records the world log already holds:
- intent records (`boundaries.md` §6.2);
- `speak`, `thought_cancelled` and `thought_failed` (§6.1–§6.2);
- `agent_ready` and `agent_failed` (`npcs_and_sem.md` §6.6).

Intent records carry `observed_tick`, `issued_tick`, `apply_tick` and `apply_us`, and `retrieval` writes are "stamped at the cycle's modelled time" (`npcs_and_sem.md` §6.6). So either those time fields are dropped, losing the causal timing the explorer needs, or the "nothing else" rule is false. And "a planted wall-time field is refused at write" has no definition that tells `apply_us` apart from wall time.

**Failure scenario:** the log's intent record format bumps a version and the mind record's copy doesn't. A purge redacts `speak` in the log but not the record's copy of the speech. A rerun comparison (§4) diffs two copies of the same fact.

**Fix (unverified):** for kinds the log carries, store a reference (`(actor_id, seq)`, a thought request id) and have views read the log. State the time rule as "world-time fields only (ticks and `apply_us`), no wall, epoch or Maxim `ts`", with a closed field list per kind.

### F8: SHOULD-FIX. The `state` kind changes the worker codec's format, and the design says it adds no codec kind

**Location:** `npc_inspector.md::§1` ("never adds a codec kind"), `§6`.

The ask puts a readout in `step`'s return, which is `step_output` on the codec (`npcs_and_sem.md` §6.6, the `codec.kinds` owner). `step_output` has its own version and gate row (`sem_stimuli.md` §5). It sits in the embeddable draft's `StepOutput` row too ("intents, proposed writes, thought requests").
- **It's true that no kind is added, but it is misleading.** The field is untrusted input from the worker. It needs the strict decoder, a size budget before allocation, a `step_output` version bump, golden rejection frames and a share of the per-park round-trip budget (`npcs_and_sem.md` §6.6, Exec S4).
- **No owner edit is named.** The design names neither §6.6 nor `sem_stimuli.md` §5 as sections the readout must amend.

**Failure scenario:** the readout lands upstream as an optional field. The host's strict decoder, as designed, ends the agent on an unknown field (`npcs_and_sem.md` §6.6: "an unknown kind, field or version ends the agent"), and every real NPC fails at its first `step`. Or someone loosens the decoder to let it through.

**Fix (unverified):** say the `state` kind is a `step_output` format change owned by `npcs_and_sem.md` §6.6, with its version bump and gate row, and list it in the ask.

### F9: SHOULD-FIX. The design changes formats and tables it doesn't own, without naming the owner edits

**Location:** `npc_inspector.md` header ("It owns no codec kind, log record or wire message"), `§3`.

The design adds a member to saves, to bug reports and to the untrusted-disk gate row ("Scene files, saves, intent logs, bug reports", `boundaries.md` §5.3). It extends the bug-report redaction rule (`boundaries.md` §6.2, `inference_placement.md` §4.2) and O26's reach list. It also bears on `boundaries.md` §6.1's audit record (F2). Each has an owner section, and the design edits none of them and lists none. Compare `inference_placement.md` §10, "What this changes elsewhere".

**Failure scenario:** the save design (save v1, Phase 4) is written from `boundaries.md` §5.3 and never learns the record exists. A save then ships without it, or with an ungated copy.

**Fix (unverified):** add a short "changes elsewhere" list naming each owner section, and fold the one-line links into those sections in this branch, or mark them as owner rulings.

### F10: SHOULD-FIX. Guest text in the record: no provenance to purge by, and append-only against redaction

**Location:** `npc_inspector.md::§3` ("Guest text", "Saves and bug reports").

O26 purges by actor and session, through memory provenance (`npcs_and_sem.md` §6.6, "Memory provenance"). The record says a purge "redacts the record's spans", but:
- **Only `write` entries are said to carry provenance.** Thought speech, the triggering input (if more than an id), intent `params` (imagined names) and, once sound lands, percepts of heard speech can all hold a guest's words.
- **Append-only conflicts with in-place redaction.** The record is append-only. The bug-report rule names only "thought speech and write text", while `inference_placement.md` §4.2 also strips held texts.

**Failure scenario:** a guest's line, quoted in an NPC's speech, survives in the record after the purge, because that entry had no actor set to match on.

**Fix (unverified):** every entry that can hold text carries the provenance set from `npcs_and_sem.md` §6.6, linked not restated. State whether redaction rewrites entries or appends redaction entries, matching whatever O26's log mechanism does.

### F11: SHOULD-FIX. Where the reader gate lives contradicts the import rule, and a non-Python reader has no gate rule

**Location:** `npc_inspector.md::§3`.

- **The gate's home contradicts the import rule.** The rule says no module under `simcore.adapters` imports the record's reader, yet the reader is a file gate "in `adapters/loaders.py`'s pattern", and the file gates live in `simcore.adapters`. If the writer is in `simcore.host`, the layers contract (`game > host | verify > protocol > adapters > core`) already forbids core and adapters importing it. The new rule is then redundant, and it leaves uncovered the one layer that could feed the record back: the host's own lane code.
- **The gate rule is conditional.** "If the gate is in Python, it gets a row" leaves option (b) in §7, a Godot or static-page reader of a stranger's save, with no gate rule. `boundaries.md` §5.3 gives saves "the strictest gate".

**Failure scenario:** the explorer ships as a static page that parses an untrusted record with `JSON.parse`, with no size budget or strict decoding, because the design exempted it.

**Fix (unverified):** name the reader's layer, state the import rule as "no module except the view and the save path imports the reader, the host lane included", and require the gate contract (`boundaries.md` §5.4) for every reader, in any language.

### F12: NIT. "Consolidation and sleep calls"

**Location:** `npc_inspector.md::§2` ("lifecycle").

`consolidate` is a codec kind. There is no sleep call: world time decides when consolidation runs (`npcs_and_sem.md` §2.4, §6.1). The fix is to drop "sleep calls" or say what produces them.

### F13: NIT. Smaller citation and category points

**Location:** `npc_inspector.md::§1`, `§3`, `§4`, `§7`.

- **§4, "the world log carries … receipts":** receipts are "derived, never input" (`boundaries.md` §6.2). Replay recomputes them; the log doesn't carry them.
- **§3, "the ownership scans gain its writer":** `tests/test_ownership.py` scans writers of the world. The record's writer writes no field, so the on/off digest test (§1) is its guard. A new scan, if one is wanted, should say so.
- **§7 cites `src/simcore/host/server.py` for the `Origin` refusal.** Its owner is `boundaries.md` §5.3 (CLAUDE.md), so the citation should be to that section.
- **Unmerged sources:** §2 and §6 cite contracts on the unmerged `phase3/joint-plan` (PR #81). They should say they are unmerged, so the design doesn't depend on that text being stable.
- **Overlapping kind names:** the vocabulary reuses `intent` and `thought`, which `record.kinds` and the log already use for different shapes. A view reading both files has to disambiguate. A prefix or a note would help.

### What passes

- The `mind_record.kinds` marker, row and threshold pass `lint_contracts` (*verified*). No other block in scope holds two or more of its spans (*verified*), so restates-at 3 is safe today.
- The continuation-header fields the `thought` kind names exist in `npcs_and_sem.md` §6.6, and excluding `held_reply`'s raw text is consistent with `boundaries.md` §6.2 and `inference_placement.md` §4.2.
- The live view correctly defers to `server.messages`' owner (`client_rendering.md` §4.1).
- The log header does carry the root id, segment and scene digest the record's header names (`boundaries.md` §6.3).
