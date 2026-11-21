**Verdict: the folds hold. No new BLOCKER; 4 new SHOULD-FIX and 9 new NITs, all on contract. Statuses for 48 findings: 42 fixed, 2 deferred, 4 open, 0 rejected.**

Scope: `git diff 92f6c5f..ed55c2f` (14 files). I read IP v3 and IG v1 in full. I read every consumer section the fold touched: boundaries §2.2, §5.3, §6.1, §6.3, §7.1, §7.4, §8.1 and §8.4; npcs §1, §4.4, §4.5, §4.8, §5.2, §6.1, §6.2, §6.6 and §12.2; `architecture.md` Known gaps; roadmap OD-I9, OD-I10, OD-A14 and OD-A23–A25; checklists "The lane's model"; both upstream drafts; the B5 row; lesson 29.

Maxim was read only at `origin/main` 043eab8f. I checked `models/language/__init__.py:19` (`from maxim.models.language.router import LLMRouter`). Nothing was run, and every fix sketched below is unverified.

## 1. Statuses (read from the tree at ed55c2f)

### Wire integrity (`delta_wire_integrity.md`)

| Id | Status | Evidence |
|---|---|---|
| S3 (round 1) | fixed | boundaries §6.3 (`:455-457`) now says "the inference items of `inference_placement.md` §4.3". The "role" wording and "reported, never refused" are gone. |
| S12 (round 1) | fixed | npcs §6.1 row, boundaries §7.1 ("host-owned gateways") and `embeddable_agent_DRAFT.md:13` are plural. O13 is kept as a record, which is acceptable. |
| N4 (round 1) | **open** | `refused` and `cancelled` still collide with the receipt outcomes in `tile_and_client.md` §3.3. The author made no claim on it. |
| B-1 | fixed | IP §2.6's "Delivery under O50" makes `prefix` the delivered speech, and text beyond it never reaches cognition. One closed `truncated` list (`validation`, `length`, `transport` reserved) is owned there, npcs §6.6 (`:815`) points to it, and `stream_broken` is gone everywhere. Residual: NIT N-b. |
| S-1 | fixed | As S3. |
| S-2 | **open** (narrowed) | IP §4.2 now sets the read point at the landing tick, never looks up a request that ended before it, and assigns the index at creation. "Before its landing tick" is still undefined in two cases: a cancel in the landing tick itself, and a cancel under floor-holding, where a cancelled thought has no landing tick. See SHOULD-FIX C-S2. |
| S-3 | fixed | IG §3: an attempt is finished only by its one `reply` or its gateway's death. The host sends `cancel` on cancel and at the ceiling, the late `reply` is expected, and cancelling a finished attempt is a no-op. |
| S-4 | deferred (enumeration); the contract half is fixed | IG §5 normalises `None`, `"None"` and `""` to `absent` and names per-transport length and refusal values (*to verify*). The deferred part is per-transport stop reasons and refusal values. Trigger: Phase 4 fake-server tests; the deferral is listed in checklists, "Deferred from the delta round". The fold opened a new gap in the table (C-S1). |
| S-5 | **open** (narrowed) | Load no longer moves a pinned request: a load delay leaves the placement eligible (IP §2.7, §2.3). But "wait or end at once" now contradicts itself (C-S3). |
| S-6 | fixed | IP §2.2: the policy and the `health` block are in `placements.yaml` only, recorded and never refused. `functions.yaml` holds functions, tiers and envelopes. |
| S-7 | fixed | npcs §6.6 header (`:789`) gains `held_reply`. IP §4.2: the exporter strips held texts. |
| S-8 | fixed | IP §2.4 adds `single`. IP §4.3: the ledger pins that every experiment function uses `single`. The prereg draft `:76` names `single`. |
| S-9 | fixed | boundaries §7.4 (`:593`), npcs §5.2 (`:560`), §6.2 (`:646`) and §4.5 lever 3 (`:464`) now describe validation over the held reply. |
| N-1 | fixed | The entry holds provenance with the host-stamped outcome (IP §4.1, §4.2). Runs with a machine-decided failure are tier 3 (boundaries §6.3 tiers), so a rerun never needs that reason. |
| N-2 | fixed | IP §2.6 row: "placement: fault; host when collateral of a kill or a crash". |
| N-3 | fixed | IP §2.1: `thinking` is a budget, the host sends it, and the agent's per-call value is ignored. |
| N-4 | fixed | IP §2.1 and npcs §6.6 (`:742`): every spawn begins with `load`. |
| N-5 | fixed | IG §3 has the `error` code list and the `ready` fields. IG §4 puts the tunables in `health`. `credential_unresolved` means down at once. IG §8 gives the endpoints replace rule. |
| N-6 | fixed | npcs §4.4 (`:413`) reads "liveness ceiling, counted from enqueue". |
| N-7 | fixed | IG §8 and IP §10 target `client_rendering.md` §4. |
| N-8 | fixed | npcs §4.5 meters are "per placement and function". Prereg `:76`. |
| N-9 | fixed | As S12. |

### Architecture (`delta_architecture.md`)

| Id | Status | Evidence |
|---|---|---|
| A1 / D1 | fixed | boundaries §2.2 rows 7a (`engine.inference_wire`) and 7b (`engine.adapters.inference`). IG §1 names the three import contracts. |
| D2 | fixed | IP §2.7: a load delay, not a cooldown, and the placement stays eligible. |
| D3 | fixed | IP §2.5: the call that passes `call_ceiling_s` is a placement load outcome, and the rest are host collateral. IG §4 and IP §2.7: only failed starts lead to "down". |
| D4 | fixed | IP §2.2 and §2.7: the `health` block is in `placements.yaml`, never refused. |
| D5 | fixed | As wire S-1. |
| D6 | fixed | As wire N-4. |
| D7 | fixed | IG §5: `absent` plus content is `ok`. IP §8 adds a missing `finish_reason` to the Phase 4 fake server. |
| D8 | fixed | IG §5 names `TEMPORARY(phase3)` and the Phase 3 listing. The marker lint fails loudly if Phase 3 finishes with the marker still in place. |
| D9 | fixed | IG §2's allowed set names the endpoints files, the credential store, site-packages and the CA bundle. The test itself is deferred (trust D-S5, in the checklist). |
| D10 | fixed | IP §2.2: the policy lives only in `placements.yaml`. IG §8: replaced whole, ids match. |
| D11 | fixed | IP §2.4: list order when several slots are free at once, and one queue per `server` group. |
| D12 | **open** (NIT) | Naming and tunables are fixed (`engine.*` throughout; `health` block). The registry half isn't: IG §9 says each gate "is a row in `boundaries.md` §5.3's registry". §5.3 has no such rows, only a pointer inside the response-cache row (`:333`). A reader of the registry still won't find the gateway channel. |

### Executor (`delta_executor.md`)

| Id | Status | Evidence |
|---|---|---|
| E-N7 (round 1) | fixed | As wire S-1. |
| D-S1 | fixed | As wire S-1. |
| D-S2 | fixed | F3 has been rewritten, `stream_broken` removed, and IG §5 normalises the stop reason. |
| D-S3 | fixed | IG §5 gives `failed(refused)` a producer (`refusal` on anthropic, `content_filter` on openai_compatible). Checking the values is deferred to Phase 4 (checklist). |
| D-S4 | fixed | IP §2.1: counters declare their tokenizer families, and an uncovered placement is refused at load. |
| D-S5 | fixed | `architecture.md:54` points to IP §6.3, which lists the four gaps. npcs §4.5 lever 3 is marked unavailable. Residual: NIT N-i. |
| D-S6 | deferred, half (b); half (a) fixed | (a) OD-I10 and F9 cite `strict_address_check`. (b) The HTTPS `owner_lan` address check is deferred to Phase 4 (checklist: "executor D-S6b, Phase 4") and kept as a Known gap (IP §6.3, IG §7). |
| D-N1 | fixed | IP §1.2 and lesson `:337` say `last_used_*`. |
| D-N2 | fixed | F8 cites `:416-422`. |
| D-N3 | fixed | F4 cites `openai_backend.py:450`. |
| D-N4 | fixed | F2 says a missing package raises. IG §5 maps it to `failed(unclassified)`. |
| D-N5 | fixed | boundaries §7.1 (`:511-513`) says "writing the response cache" and "gateways". |
| D-N6 | fixed | IP §4.1 makes the provider and model null where the transport only echoes them. IG §2: a request id may go out. The checklist no longer says "no `X-Maxim-*`". |

Round 1's E-N6 deferral stands: it is in the checklist list, triggered at Phase 4.

## 2. Contracts the fold changed, producer to consumer

| Contract | Owner | Consumers checked | Result |
|---|---|---|---|
| Outcome table, `thought_failed` reasons, `truncated` reasons | IP §2.6 | boundaries §6.1 `:380`; npcs §1 `:96`, §4.4 `:413`, §6.6 `:815`; checklists | One owner, and consumers point to it. Two dangling details: N-b and N-c. |
| Classification | IG §5 | IP §2.6 (Kind column), §2.7 | Every IG §5 output is an IP §2.6 outcome, and the reverse holds too. The table isn't closed over stop reasons (C-S1). |
| Cache | IP §4.2 | npcs §4.8 `:505` (pointer), §4.4 `:415-417`, boundaries §5.3 `:333`, §7.1 | Moved cleanly. The rerun read point is C-S2. Branch occurrence indices are N-h. |
| Manifest and ledger | IP §4.3 | boundaries §6.3 `:457`, §8.4 `:665`; prereg `:76` | Consistent; all three point to IP §4.3. |
| Three files and `health` | IP §2.2 (with IG §4 for the lifecycle values) | IG §4, §8; checklists | Consistent. `endpoints.yaml` is claimed by two owners (N-d). The `open` field sources aren't named (N-g). |
| `single`, `pinned`, `spill` | IP §2.4 | IP §2.7, §4.3; prereg | `single` and the cooldown wait contradict each other (C-S3). |
| Channel kinds and rules | IG §3 | IP §2.5, IG §4 | Consistent. "Finished" is now defined. |
| Taint and consent | IG §6 | IP §2.3, §6.2; npcs §6.6 | The speaker's identity contradicts O51 (C-S4). The guest-string list is restated (N-f). |
| Layer table | boundaries §2.2 | IG §1, boundaries §8.1 `:613` | The layers are consistent. The import wording disagrees (N-e). |
| `held_reply` | npcs §6.6 (field), IP §4.2 (semantics) | npcs §4.4 `:417` | Consistent. |

## 3. New findings

### SHOULD-FIX

**C-S1. `inference_gateway.md::§5`: the classification table is no longer closed over stop reasons. (contract)**
- v2 mapped "content with a non-empty `stop_reason` other than a length stop" to `ok`.
- v3's first row admits only `absent`, `end_turn` and `stop`.
- Content with any other stop reason has no row. From my knowledge of the provider APIs (not checked in this tree): Anthropic sends `stop_sequence`, `tool_use` and `pause_turn`, and OpenAI sends `tool_calls`.
- The canonical request carries `stops` (IP §4.2), so `stop_sequence` is a normal value on the `anthropic` transport, not a rare one.
- The "any other exception" row covers exceptions only, so a builder has to choose. Build A treats the reply as `ok`. Build B treats it as `failed(unclassified)`, a placement fault, so every reply that hits a stop string cools the placement down and moves a pinned function.
- The outcome is golden-fixtured, so the two builds also disagree on fixtures.
- What is missing: one closing row for content with any non-`absent` stop reason that is neither a length stop nor a refusal.

**C-S2. `inference_placement.md::§4.2` (rerun mode): "ended … before its landing tick" has no defined landing tick in two cases. (contract)** This is the residual of wire S-2.
- **(a) Same tick.** A `thought_cancelled` logged in the landing tick itself is neither "before" it nor clearly after it.
- **(b) Floor-holding.** Under floor-holding, a thought's landing tick is its logged `reply_landed` tick (npcs §6.6), and a cancelled thought has none. A builder who reads "landing tick" as the modelled landing tick looks up a request whose cancel came after the modelled tick but before any reply arrived.
- In both cases the request has no entry when the reply never arrived (the session saved or ended, or the gateway was killed). The result is a loud miss on a valid tier-2 run, because a cancel is a world event and keeps the run at tier 2.
- What is missing: a rule keyed to the log, not to ticks. For example: a request whose thought has a terminal log record (cancel or `thought_failed`) is never looked up.

**C-S3. `inference_placement.md::§2.4` vs `§2.3` and `§2.7`: wait or end at once. (contract)** This is the residual of wire S-5.
- §2.3 defines "Not down" to include "isn't in a placement cooldown". §2.7 says "a cooling placement is ineligible".
- §2.4 says three things:
  - `single`: "If it isn't eligible, the request ends at once as `unavailable`".
  - "No eligible placement at all (consent, budget, **down**) ends … at once".
  - "One whose only candidate is cooling down waits, bounded by the liveness ceiling".
- A `single` request whose one placement is cooling matches both the first and the third rule. So does a `pinned` one-entry list.
- The logged reason is `unavailable` in one build and `timeout` in the other, for the same condition. Both are in the closed `thought_failed` list and in golden fixtures.
- Failure scenario: an Exp 64 arm's placement takes one `failed(unreachable)`. Build A fails the next thought as `unavailable` at once. Build B waits up to the ceiling, the probe recovers, and the thought succeeds. The two arms' trajectories differ by build.

**C-S4. `inference_gateway.md::§6` ("A speaker is an actor and its session, so a guest who rejoins accepts again") vs O51 ("Consent is per speaker and outlives the session") and O54 ("only the speaker may release"). (contract; needs the owner)**
- If the speaker includes the guest's session, then once a guest's session ends, no one can ever release that speaker's taint. The guest who rejoins is a different speaker, and the owner may only purge.
- So O54's release clause can't be reached for any departed guest, and "outlives the session" holds only for the saved record, not for the person.
- The saved consent and taint format (a registered gate, IG §9) depends on the key: actor alone, or actor plus session.
- Failure scenario: guest G talks to a fixer, leaves and rejoins the next evening, and accepts the cloud class. The fixer stays local-only for good, unless the owner erases G's earlier words, which G cannot release.

### NIT

- **N-b. `inference_placement.md::§2.6` ("Delivery under O50"):** `ok` resumes `think` with `complete(text)`, even when the speech field fails validation partway. npcs §6.6 (`:818`) says that case ends as `truncated(prefix, reason=validation)`. IP's own reason list contains `validation`, but its delivery bullet lists only `ok` and the length cut, so text no listener heard can reach cognition (TB3-S5).
- **N-c. `inference_placement.md::§2.6` (`failed(empty)` row)** cites IG §5 for "load on `openai_compatible` and `anthropic`, fault on `maxim_peer`". IG §5 doesn't state that split; only IP §2.7 does. The citation is dangling; ownership should sit in IP alone.
- **N-d. Ownership of `endpoints.yaml` is claimed twice.** IP's "What it owns" has "the three data files", and IG's has "proxies, credentials and endpoints". The replace-whole rule is stated in both IP §2.2 ("the same pairing") and IG §8.
- **N-e. `boundaries.md::§8.1` (`:613`) "never `LLMRouter`"** vs IG §1 "never `LLMRouter`'s methods" and IG §2's transitive import allowlist. `maxim/models/language/__init__.py:19` imports `LLMRouter` (043eab8f), so a module-level "never" can't hold. The same contract is stated twice, in two different ways.
- **N-f. `inference_gateway.md::§6`** restates the guest-string channels ("speech, display names, imagined-object labels and written text") and calls them "the closed list" of npcs §6.6. npcs §6.6 (`:859`) and boundaries §5.3 (`:332`) give that list as a parenthetical, not a closed list. Point to one owner and close the list there.
- **N-g. `inference_gateway.md::§3` (`open`):** "the endpoint and credential references" and "the transport timeout" have no named source. No IP §2.2 field or `health` value holds the timeout, and the placement id, which is what those references presumably are, isn't listed as a field.
- **N-h. `inference_placement.md::§4.2` (branches):** it doesn't say whether a child segment's occurrence index continues the parent's count per hash or restarts. A restart collides with the copied entries. "The saved high-water request id" is singular, but request ids are minted by each NPC's sequencer (O43).
- **N-i. Dangling until merge:**
  - IP and IG cite B36, which exists only on `phase1/doc-ownership-rule`.
  - IP §6.3's O50 gap takes its numbers from a lesson at `phase1/vertical-slice` 7eed0bc, which is not an ancestor of ed55c2f. In this tree, the `architecture.md` Known-gaps pointer leads to a gap with no numbers.
  - Merge order should be recorded in the hand-off.
- **N-j. Process, not contract:**
  - IP §0 keeps a decision table inside a design document. The worktree's CLAUDE.md now says decision tables live in `reviews/` and in indexes.
  - `checklists.md` grew from 6,791 to 6,990 words.
  - The roadmap's OD-A14 (`:193`) and `embeddable_agent_DRAFT.md:88` restate the envelope with three fields, dropping IP §2.1's `thinking`.

## 4. Checked and consistent

- The pointers to IP and IG sections from boundaries, npcs, the roadmap, `architecture.md`, `standards_backlog.md` and the drafts all resolve: §1.2, §1.3, §2.1, §2.5, §2.6, §4.2, §4.3, §6.2, §6.3 and §8 in IP; §1, §2 and §9 in IG.
- No live document still says `stream_broken`, "role envelopes", `last_served`, "per model and role" or "a host-owned gateway".
- Every IG §5 output is an IP §2.6 outcome, and every IP §2.6 outcome has a producer.
- IG §3's `cancel` and late-`reply` rules agree with IP §2.5's slot rule and its kill collateral.
- `health` relations: `call_ceiling_s` and `start_ceiling_s` are each below the liveness ceiling, and the backoff cap is too.
- Word counts: IP 4,711 (down from 5,988), IG 2,341 (new, ≤ 6,000), npcs 23,777 → 23,492, boundaries 13,982 → 13,978, `architecture.md` 2,827 → 2,824, foundations 2,500 → 2,499.

C-S1, C-S2 and C-S3 can each be folded with one rule. C-S4 needs the owner's ruling on what "speaker" means.
