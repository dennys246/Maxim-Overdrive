# NPC inspector design: Wire integrity delta review, round 2

**Lens:** Wire integrity, delta round on a design (`docs/code_review.md`). **Read:** the fold diff `git diff bd0137d -- docs/design/npc_inspector.md` (v1 at `bd0137d`, v2 the working-tree blob `20b6cbb1`, 4,038 words) and every section outside the hunks that produces or consumes a contract the diff touches: `sem_stimuli.md` §4.1–§4.4, §5 and §6.1–§6.2; `boundaries.md` §5.3, §5.4 and §6.1–§6.3; `npcs_and_sem.md` §6.6 (codec, lifecycle, continuation header, determinism, provenance); `inference_placement.md` §4.2; `sim_core.md` §14; `tile_and_client.md` §3.2; `realtime_lanes_coop.md` §4.1 and its banner; `world_v2.md`'s banner; `src/simcore/core/schema.py` (`Format`, `_tick_fields`); `contracts.md`; `scripts/lint_contracts.py`; and the round-1 `wire.md` and the author's `fold.md` (blob `5791d71e`). **Ran** with the worktree's `.venv/bin/python`: `scripts/lint_contracts.py` (exit 0, no findings) and `scripts/lint_standards.py` (`PASS (0 finding(s))`). Both read the working tree through `git ls-files -co`, so they covered v2 and the untracked `fold.md`. The `mind_record.kinds` row in `contracts.md` didn't change (§2, vocabulary, restates at 3). Only its marker's members changed, and no block in scope holds three of the new spans.

**Fold-table accuracy (O25).** Two of the author's claims don't match the tree:
- **F3.** `fold.md` says the receipt is "(pid or (actor, seq), kind) as delivered". v2 says only "the receipts it carried". Those are `sem_stimuli.md` §6.2's `(pid, kind)`, and nothing in v2 adds `(actor, seq)`. This is why F5 stays open.
- **TB-N4.** `fold.md` says "no labels in the record". v2's `stimulus` row says the entry holds "the bindings' receptor and site resolved from the binding table it names" (N6).

**No new BLOCKER.** Five new SHOULD-FIX findings sit in text the fold added (N1–N5).

## Status of round-1 findings

| Finding | Status | Evidence in v2 |
|---|---|---|
| F1 (BLOCKER) percept source superseded | **fixed** | `stimulus` is a delivery, not a §7.3 pull. The body frame is excluded by name. "A stimulus is not a percept" puts clamp, noise and transduction worker-side, and the view label is "delivered". The residual is N6: the entry drops `events` and `registry_digest`. |
| F2 (BLOCKER) second owner of memory writes | **fixed** | §2: the record holds no writes, and `write_ref` points at the OD-A15 audit record (`boundaries.md` §6.1). The pointer's key has no host-side minter (N3). |
| F3 (BLOCKER) receipt fields the host doesn't hold | **fixed** | The receipt is what the delivery carried. Valence is gone. Stage-2 truth can't enter, because `receipt.kinds` are stage-1 only and `refusal` is stage-1 only. The `fold.md` wording is overstated (above). |
| F4 `Format` refuses tick fields | **fixed** | §3 follows `sim_core.md` §14: c14n-1, held by others, migrates or refuses, gate row, goldens. The tick-rule amendment is a dependency in §8. *Verified:* `schema.py:423` still refuses, so the amendment really is needed. |
| F5 join key null under the double | **open** | §7 joins on `(actor_id, seq)`, "the intent id receipts carry (`boundaries.md` §6.1)". But the receipt the record stores is `sem_stimuli.md` §6.2's `(pid, kind)`, with pid null until G17, and `refusal` entries carry no seq either. The key the explorer joins on isn't in the data it joins. The inconsistency between the two owners that I flagged in round 1 isn't listed in §8. |
| F6 segments and branches | **fixed** | §3: one record per segment, with parent segment and truncation at the save. It links `inference_placement.md` §4.2, but then restates it in a different word (N8). |
| F7 copies of log records; stamp rule | **fixed** | §2: log facts are read from the log, joined on actor and tick. §1 "Its clock" gives a closed rule (delivery tick, barrier tick, modelled landing tick or `reply_landed`'s tick), and no µs or wall field is held. |
| F8 `state` changes `step_output` | **fixed** | §6 "On Overdrive's side" names `npcs_and_sem.md` §6.6 and `sem_stimuli.md` §5, the version bump, the gate row, golden rejection frames and a barrier-budget line, and §8 lists it. §1's "never adds a codec … field" now contradicts this (N8). |
| F9 owner edits unnamed | **open (narrowed)** | §8 names the log header, the gate table, save v1, the tick rule, the step output, the audit record and `pyproject.toml`. §5 still says the record leaves "in a save or a bug report", but no bug-report membership edit is named. The receipt-identity and stage-1-receipt dependencies are missing too (N1, N7). |
| F10 guest text, purge, append-only | **fixed** | §2: no free text in the record, so O26's existing reach is enough. A purged audit entry leaves a dangling `write_ref`, and v2 doesn't say how a view shows it (N7). |
| F11 gate home vs import rule; non-Python reader | **fixed** | §4: one Python gate in `simcore.host`, the only reader in any language, an import contract naming it, and an unconditional gate row. The handoff to a non-Python view is unspecified (N5), and the import rule now excludes replay's comparator (N2). |
| F12 "sleep calls" | **fixed** | `grep -i sleep` finds nothing in v2. |
| F13 citation and category points | **fixed** | Receipts are "re-derived", not "carried by the log". The ownership-scan line became a writing scan (§4). `Origin` is cited to `boundaries.md` §5.3 (§7). PR #81 is marked unmerged. No v2 kind collides with `record.kinds`. |

## Contract table, v2

| Contract (owner) | What v2 says the host holds or uses | Does it exist there with those fields? | Linked or restated |
|---|---|---|---|
| `mind_record.kinds` (`npc_inspector.md` §2; row in `contracts.md`) | `stimulus refusal thought_state write_ref gap tick_end readout` | Marker and table agree. The lint passes (*ran*). | Owned here. The gap reasons are a second closed vocabulary that isn't registered (N8). |
| `BoundFrame` (`sem_stimuli.md` §4.2) | tick, bindings digest, values in binding order, receipts | Yes. `BoundFrame` also carries `schema_version`, `registry_digest`, `npc_key` and `events`, which v2 leaves out without saying so (N6). | Restated as a field subset without a §4.2 link in the row. |
| Receipts (`sem_stimuli.md` §6.2, `receipt.kinds`) | "the receipts it carried", "re-derived" on replay | `(pid, kind)` exists. Re-derivation fails for `malformed` and `limit` (N1). The `(actor_id, seq)` join is absent (F5). | Linked through §7's citation of `boundaries.md` §6.1, which disagrees with §6.2. |
| Continuation header (`npcs_and_sem.md` §6.6) | thought id and kind, triggering input id, cycle index and `max_cycles`, each segment's landing tick, cancel status | Yes, all six are in the header. `held_reply` and the delivered prefix are rightly excluded. The tool names that "the thought counters name" have no header field (N8). | Linked. |
| Audit record (`boundaries.md` §6.1, OD-A15) | a per-write sequence number, write kind, count of trace ids | Not yet. §6.1 gives no fields, and §8 proposes the seq. The writer is the worker, so the host can't know the seq unless it mints it and `settle` carries it (N3). | Linked, with the edit proposed. |
| Log header (`boundaries.md` §6.3) | root id, segment, scene digest, plus a new "record on" field | Root id, segment and scene digest exist. The parent segment and the bindings digest are the record's own header fields, which is fine. The new field's class (metadata or refuse-on-mismatch) is unstated (N7). | Linked, with the edit proposed. |
| Segments and the response-cache rule (`inference_placement.md` §4.2) | per-segment record, child on load, truncation at the save | The rule exists. §4.2 cuts at "the save's header snapshot", and v2 says "the save's barrier" (N8). | "links rather than restates", then restates it. |
| Intent log format (`sim_core.md` §14) | the record follows its pattern | Yes: c14n-1 lines after a header, held by others, gate row, goldens. Not built (`grep intent_log src` finds nothing). | Linked. |
| Schema tick rule (`schema.py`; tile §3.2) | needs an amendment shared with the intent log | `Format.__post_init__` refuses (*read*, `schema.py:423`). Tile §3.2 states the rule only for the torch's seconds. It is still owned in two places, as in round 1. | Listed in §8. |
| Step output field (`npcs_and_sem.md` §6.6; `sem_stimuli.md` §5) | `readout` [later] | `step_output` has its own version and gate row (`sem_stimuli.md` §5). | Linked. The barrier figure "0.2–0.8 wall seconds per second" is copied from §6.6 (N8). |
| Saves (save v1, `boundaries.md` §7.1, roadmap Phase 4) | carry the records truncated at the barrier | §7.1:566 is the save v1 sentence. | Listed in §8. |
| Gate table (`boundaries.md` §5.3) | the record joins the strangers'-disk row | The row exists ("Scene files, saves, intent logs, bug reports"). | Listed in §8. |
| Record lane (`realtime_lanes_coop.md` §4.1) | "the pattern of … §4.1's record lane" | **No.** That document is superseded (by `world_v2.md`, itself superseded), and its record lane is the opposite: "the log is written synchronously by the simulation lane each tick; this lane only flushes and rotates" (N4). | Cited, wrongly. |
| Client rendering (`client_rendering.md` §4.1, §4.2; `npcs_and_sem.md` §5.2) | a Phase 4 message; display quantization; plain-text speech | Yes: §4.1 messages, §4.2 channels, §5.2:531 "BBCode off". | Linked. |
| Handshake (`boundaries.md` §5.3) | any listener follows it | Yes. | Linked, with a parenthetical copy of its three terms (N8). |
| Copy budget and lanes meters (B5; `phase1/lanes`) | the tier-3 bound and the stalled-writer test | No B5 row or number exists, and `phase1/lanes` comes after `phase1/agents` (roadmap:27) (N7). | Unowned. |

## New findings (all in text the fold added)

### N1: SHOULD-FIX. `stimulus` is "re-derived" on replay, but stage-1 receipts can't be

**Location:** `npc_inspector.md::§2` (the `stimulus` row's "On replay", and `refusal` "recorded only (the log holds stage-1-accepted intents)"), `§9` ("Replay against the record").

The pipeline is decode → stage 1 → log (`boundaries.md` §6.1). An NPC intent refused at stage 1 is never logged, and v2 says so in its own `refusal` row. But the receipts it produces (`malformed`, `limit`; `sem_stimuli.md` §6.2) ride in the next `BoundFrame`, and the `stimulus` entry stores them.

**Failure scenario:** an NPC under the double emits one over-limit intent. Replay recomputes that delivery without the `limit` receipt, and §9's byte-for-byte comparison goes red on every run with a refusal. The pressure is then to loosen the comparison to "values only". The same question applies to the delivery schedule: v2 names no log source for which ticks an agent was stepped on (divisor, idle coarsening; `npcs_and_sem.md` §6.6's levers).

**Fix (unverified):** either log stage-1 refusals of NPC intents as records (an edit to `boundaries.md` §6.1–§6.2 and `sem_stimuli.md` §5's bound lane), or mark the receipt part of `stimulus` as "recorded only" and compare only values on replay. Either way, list it in §8, and name where the delivery schedule comes from.

### N2: SHOULD-FIX. The import rule forbids the replay comparison §9 requires

**Location:** `npc_inspector.md::§4` ("Only the view's entry point and the save-copy path may import it"), against `§2` and `§9` (replay "compares them byte for byte with the recorded ones").

Replay has to read the record to compare it, and the gate module is the only reader in any language (§4). So replay's comparator must import a module the import contract refuses to it.

**Failure scenario:** the build step either drops the comparison, so a drifting writer stays green, or opens the contract for replay without saying so in the owner section.

**Fix (unverified):** name the replay check as a third permitted importer. §1's "never an input" still holds, because the comparison feeds nothing into the `Simulation`. Say that in §1.

### N3: SHOULD-FIX. `write_ref`'s sequence number has no host-side minter, and §8 leaves out the codec change it needs

**Location:** `npc_inspector.md::§2` (`write_ref`), `§8` (the audit record edit).

The audit record is agent-side and written in the worker (`boundaries.md` §6.1). The host sees writes only at gating, before `settle` (`npcs_and_sem.md` §6.6). For the host's pointer to name the worker's entry, one side must mint the seq and the other must be told it. If the worker mints it, the host is recording an untrusted value it never received. If the host mints it, `settle` must carry it, which is a codec field change owned by `npcs_and_sem.md` §6.6, and §8 doesn't list that. After a `rewound` restart the agent home's counter goes back, so pointers from the abandoned span collide with new writes. v2 covers this only in a view rule ("shown as lost").

**Failure scenario:** the explorer resolves a pointer to the wrong write after a restart, or to a seq that a buggy worker reused.

**Fix (unverified):** the host mints the seq in canonical gating order and passes it in `settle`. Add the §6.6 codec edit to §8, and key pointers by (segment, seq).

### N4: SHOULD-FIX. The lane cites a superseded section whose record lane is the opposite pattern

**Location:** `npc_inspector.md::§3` ("This is the pattern of `realtime_lanes_coop.md` §4.1's record lane").

`realtime_lanes_coop.md` carries a "Superseded 2026-11-16 by `world_v2.md`" banner, and `world_v2.md` is itself superseded. Its §4.1 record lane is "written synchronously by the simulation lane each tick (CP-6); this lane only flushes and rotates". That is exactly the simulation-lane IO that v2 forbids.

**Failure scenario:** a builder follows the link and writes the record synchronously from the simulation lane. That breaks the tier-3 cost bound (§1), and the link vouches for the mistake.

**Fix (unverified):** drop the citation. v2's queue-and-drain rule is self-contained, and this design is its owner.

### N5: SHOULD-FIX. A non-Python view reads "the gate's validated output", which is an unnamed second format

**Location:** `npc_inspector.md::§4` ("a Godot or web view reads only that gate's validated output, never the raw file"), `§7` ("An offline view opens a file the user chose, and starts no network listener"), `§10` item 6.

For pulse's kit, a Godot viewer or a static page to read the Python gate's output without a listener, that output must be serialised. That makes it a second format with no version, schema, golden or reader rules. Alternatively, the "file the user chose" is the raw record, which §4 forbids.

**Failure scenario:** the static-page viewer gets a JSON export that someone "just" dumps from the gate. Its consumers then parse it with `JSON.parse` and no budget, and the strangers'-disk gate is bypassed by one hop.

**Fix (unverified):** either every view is Python-hosted, or the gate's export is a declared `Format` owned here, with its version and a gate rule for each language's reader.

### N6: NIT. "One delivery as it crossed" drops fields, and the receptor and site storage is ambiguous

**Location:** `npc_inspector.md::§2` (the `stimulus` row).

The row omits `BoundFrame.events`, `registry_digest` and `schema_version`.
- `events` is empty in v1, but once sound lands it is the whole stimulus content of hearing. The record would silently miss it, and replay's comparison wouldn't cover it.
- "Resolved from the binding table it names" can be read as names stored per entry or resolved by the reader. `fold.md`'s TB-N4 assumes the second.

**Fix (unverified):** link §4.2 and list the exclusions, or include `events`. Say the reader resolves receptor and site, since the header already holds the bindings digest.

### N7: NIT. §8 and budget gaps

**Location:** `npc_inspector.md::§8`, `§1` (tier 3), `§9` ("A stalled writer").

- **Missing from §8:**
  - the bug-report exporter's membership (§5 says the record can ship in one);
  - settling receipt identity between `sem_stimuli.md` §6.2 and `boundaries.md` §6.1 (F5);
  - the stage-1 receipt rule (N1);
  - the `settle` seq field (N3);
  - a B5 row for the copy budget.
- **The log-header field's class is unstated.** §6.3 refuses a content mismatch, so "record on" must be declared metadata that the `Simulation` never reads (like "Dilation by cause"). Otherwise an on run and an off run refuse each other's replay.
- **The copy budget has no number and no owner.** `phase1/lanes` comes after `phase1/agents`, so the [agents] stalled-writer test has nothing to fail against until then.
- **A dangling `write_ref`.** After an O26 purge removes its audit entry, how a view shows the pointer is unstated.

### N8: NIT. Smaller contract-text points

**Location:** `npc_inspector.md::§1`, `§2`, `§3`, `§6`, `§7`.

- **§1's rule contradicts §6.** §1 says the inspector "never adds a codec kind or field", while §6 and §8 add the `readout` field. The rule is tagged [agents], but §1 is the owned rule, so scope it in words.
- **The gap reasons are unregistered.** `dropped`, `stopped`, `torn`, `rewound` and `off` form a closed vocabulary that views depend on, but `contracts.md` has no row for them (B36).
- **The truncation point is restated in different words.** §3 truncates "at the save's barrier", but `inference_placement.md` §4.2's cut is "the save's header snapshot". Cite one term.
- **Copied values.** §6's "0.2–0.8 wall seconds per second" and §7's handshake parenthetical are copies that will go stale. Link them instead.
- **"Segment" means two things:** a thought's segments (§2, `thought_state`) and log segments (§3).
- **No field for tool names.** "the thought counters name them" (§2) needs a field the host-owned header doesn't have. Mark it as a future header edit.
- **The tier-1 invariant is vacuous.** §1 holds "Tiers 1 and 2" to an on/off comparison, but replay never writes a record. Say tier 2, or "live runs under tier-2 conditions".
