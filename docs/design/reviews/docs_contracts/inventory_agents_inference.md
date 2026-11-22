Inventory of contracts stated in more than one place, domain: agents, thought and inference. Branch `phase1/docs-contracts`, read-only. Every DIFFER below was confirmed by re-reading the line. Abbreviations: N = `docs/design/npcs_and_sem.md`, B = `boundaries.md`, IP = `inference_placement.md`, IG = `inference_gateway.md`, SS = `sem_stimuli.md`, RLC = `realtime_lanes_coop.md`, FP = `docs/plans/foundations_plan.md`, RM = `docs/roadmap.md`.

**Three contradictions matter most:**
1. Receipt kinds (item 6).
2. The worker's `HOME` (item 4).
3. Live play's default latency policy in N §11.2 (item 9).

## Resolved since PR #27
- **`thought_failed` reasons:** only one full list remains, IP §2.6 (`:227`), which declares itself owner. The other sites each name the one reason they trigger, which is fine:
  - N §4.4 `:413` (timeout), N §4.7 `:492` (budget), N §6.6 `:856` (parse);
  - `checklists.md:357` (reloaded), IP §2.5 `:187` (timeout);
  - B §6.1 `:381` refers to IP §2.6.
  - Gaps: IP §2.4 `:176` says a request ends "as `unavailable`" without writing `thought_failed(...)`. N §4.4 `:415` names "out-of-memory", which maps to no reason on the list.
- **`truncated` reasons:** only IP §2.6. N §6.6 `:818` defines when `validation` applies, which is consistent.
- **Response cache:** N §4.8 `:504` and B §5.3 now refer to IP §4.2. Leftover copies are listed in item 12.

## Contracts in more than one place

1. **`AgentPort` signature** (`step`/`think`/`settle`).
   - DEFINES: N §6.1 `:612` (table), N §6.6 `:778-780` ("in one signature"), B §7.1 `:500`.
   - REFERENCES: N §6.2, N §0 O39 `:70`, FP `:133`, `world_model.md:276`.
   - Wording differs slightly: N §6.6 has `Pending(request) | ThoughtOutput` and `settle(receipts, writes) -> ack`; B §7.1 has `Pending | ThoughtOutput` and `settle(receipts, writes)`, with no return.
   - Owner: N §6.6, which says it wins over earlier sections.

2. **The agent lane and the barrier.**
   - DEFINES: N §6.3 `:663-685`, B §7.1 `:516-537`.
   - DIFFER on what runs in the worker:
     - N `:675`: "Its `step`, `think`, `settle`, `consolidate` and any push into its body run serialised in its worker."
     - B `:520`: "Its `step`, `think`, `settle` and any push into its body run there". `consolidate` is missing.
   - Owner: N §6.3.

3. **The gateway meaning two things.** This is still split.
   - Meaning 1, a backend Maxim calls:
     - N O6 `:41` and B O6 `:49`: "a host-supplied LLM gateway with streaming and cancellation".
     - O6a `:42` withdraws it: "the gateway is not a backend Maxim calls".
   - Meaning 2, the gateway is the thinking lane:
     - The fold-table notes in B `:939,958,959` and N `:1207,1226,1227` say "the gateway is the host's thinking lane".
     - RM `:112` says "the gateway is the host's (O6a)".
   - Meaning 3, the current one:
     - IP O47 `:35`: calls run "in host-owned inference gateway processes, not in the world server", one per placement (O53).
     - Also N §6.3 `:671` ("in inference gateways (O47)"), N §6.6 `:770` and B §7.1 `:513` ("host-owned gateways make the calls").
   - Meaning 4, in the host:
     - N O13 `:52`: "The LLM gateway stays in the host".
     - IP O47 reinterprets that as "reads as host-side", but O13's text is unchanged.
   - Meaning 2 contradicts meaning 3: the lane dispatches to the gateways, it is not one.
   - Also, O6 in both copies still requires streaming, which O50 rules out.
   - Owner: IG §2 for "gateway". Fix O13's text and the fold notes.

4. **Worker process rules** (spawn, environment, home, latch, channel).
   - DEFINES: N §6.6 `:735-772`.
   - Restated in N O13 `:52`, N §6.3 `:668-674`, B §7.1 `:518-523`, B §5.3 rows (worker channel, agent homes), B O7a `:51`, FP O13 `:115`, FP `:44`, and N O19 `:59`.
   - DIFFER on `HOME`:
     - N §6.6 `:741`: "No keys, no `HOME`, no `MAXIM_*`".
     - N O13: "its home set to the agent's home under the save".
     - N O19: "the worker's home and `XDG_*` set with no read of the host's home".
     - FP `:44`: "the worker's `HOME`, `XDG_*`, `TMPDIR`, `HF_HOME` under the agent home".
     - IG §2 `:48` gives the reason for setting it: "An unset `HOME` falls back to the real one (*verified*)".
     - So §6.6, the owner, is the outlier, and probably wrong.
   - DIFFER on the environment:
     - O13 `:52` and N §6.3 `:669`: "scrubbed environment".
     - §6.6: "an allowlist, not a scrub".
     - B §7.1 `:519-521` says both in one bullet.
     - N §6.3 `:674` admits its own text is superseded but keeps it.
   - O13 says "a pipe opened before the latch"; §6.6 says `socketpair`. They are consistent in meaning.
   - Owner: N §6.6.

5. **`agent_failed` reasons.**
   - DEFINES: N §6.6 `:760` (`hung | crashed | protocol`), SS §4.3–§4.5 `:204-239`.
   - REFERENCES: B §7.1 `:521`, `world_model.md:277`.
   - DIFFER: SS adds `agent_failed(build)` (`:120,237,238`) and an `agent_ready` record, which N's closed list lacks.
   - Owner: N §6.6. Add `build` there, or have SS own the lifecycle records.

6. **Receipt shape and kinds** (propose, receipt, settle).
   - DEFINES: B §7.2 `:543-545`, N §6.4 `:688`, `tile_and_client.md` §3.3 `:255`. All three give "(`applied`, `refused`, `stale`, `cancelled`)" with "the measured effect".
   - SS §6.2 `:314-320` DIFFERS and claims to supersede: "the **receipt is `(pid, kind)`**"; "v1 kinds ... `malformed`, `limit`; any stage-2 result is `accepted`"; "Superseding `npcs_and_sem.md` §6.6's 'measured effect'"; and "One home: `stimuli.wire`".
   - N §6.6 "Receipts have two projections" (`:871`) still gives `settle` "the measured effect".
   - IP §2.6 `:237` names `tile_and_client.md` §3.3 as owner of receipt kinds.
   - So three documents still state kinds that SS says it replaced, and IP points at a stale owner.
   - Owner: SS §6.2, which is the newest and declares it. The other three should link to it.
   - Restated beside the shape in B §7.2 and N §6.4/§6.1: exactly-once credit, valence per D53, "stale is context", per-actor binding. These agree.

7. **Credit kinds promoted by OD-A16.**
   - B §9.3 `:700` and N §8.1 `:975`: "`stale` and `call_error` kinds".
   - RM `:195` DIFFERS: "`stale`, `call_error` and `wrong_target` kinds".
   - The SEM-item table is copied three times (B §9.3, N §8.1, RM Phase 3).
   - OD-C3 also differs: RM `:244` gives `acts_on: str = "by"`; B `:703` and N `:982` give no default.
   - Owner: RM Phase 3 (the id registry). Cut B §9.3 and N §8.1 to links.

8. **The three clocks.**
   - DEFINES: N §1 `:83-87`, B §7.3 `:562-568`.
   - Decision rows: N O4 `:39`, B O4 `:46`, FP `:99`.
   - DIFFER:
     - World time: N "the integer tick × `tick_us`"; B "the integer tick".
     - Body time: N "drive drift, fatigue, …"; B "drive drift, mental fatigue, …".
     - N has a "Reaches cognition?" column that B lacks.
   - Owner: N §1. B O4 itself says "Details are part 2's".

9. **Latency policies** (dilate, floor-holding, abandon, silent late landing).
   - DEFINES: N O11 `:50`, N O11a `:51`, N O16 `:57`, N §4.4 `:399-433`, B §7.4 `:596-600`.
   - Decision rows: B O4 `:46` ("Abandoning … an explicit, logged host policy", with no floor-holding), N O4 ("late thoughts dilate the world"), FP `:99`.
   - DIFFER inside N:
     - §11.2 `:1088`: the world-time mode is "generalised as the default for live play".
     - §11.1 `:1073`: "dilate is the default".
     - Both contradict O11 ("Live play holds the floor; it doesn't dilate") and O16 (silent late landing in co-op).
   - DIFFER on floor-holding thresholds:
     - O11a and §4.4 `:429`: "an account ('let me think') at about 600–700 ms, then a yield at about 1 s".
     - §6.6 `:894-897`: "the account's onset is a parameter in 600–1000 ms", and the yield comes "after about 1 s of silence following the last filler or account, not 1 s from the turn's end".
   - The set of `latency_policy` values is never closed in one place.
   - Owner: N §4.4. Fold §6.6's thresholds into it.

10. **Thought budgets.**
    - DEFINES: N §4.7 `:485-492`, N §6.6 "Budgets" `:875-877`, B §5.3 row `:331`.
    - DIFFER:
      - Tokens: B "a frame budget before buffering"; N "a stream cut-off **before** buffering".
      - B has "memory writes"; N has "memory writes and their bytes".
      - B lacks the per-NPC-per-world-minute chain budget (§6.6) and the liveness and per-park ceilings (IP §2.5, N §6.6).
    - Owner: N §4.7. B's row should link to it.

11. **The model request** (the request/reply cut).
    - DEFINES: N §6.1 `:613`, RM OD-A14 `:193`, IP §4.2 (the canonical request).
    - DIFFER:
      - N: "the host stamps priority and deadline from the kind, outside the cache key".
      - RM: "priority and deadline fields" belong to the request value.
      - N §6.6 `:794` stamps "priority", but no queue reads priority: IP §2.4 is deadline-only and N §4.4 `:408` says "not by priority then age".
    - Owner: IP §2.1/§4.2. The RM row can keep the upstream ask.

12. **Leftover copies of the response cache.**
    - N §6.6 `:820-821`: "Cache repeats are numbered in canonical order (by thought request id)" duplicates IP §4.2's occurrences rule. The two agree, but IP cites N §6.6 for it, so each points at the other.
    - N §4.4 `:415`: failures "recorded in the cache as first-class responses" duplicates IP §2.6's Cache column.
    - B §6.2 `:431-432`: "never the response cache … deleted or poisoned" duplicates IP §4.2 "Replay never opens the cache. Tested with the cache deleted, or poisoned". They agree.
    - Owner: IP §4.2. The N copies should become links.

13. **Guest-session gates** (O14 and O18).
    - DEFINES: N O14 `:53`, N §12.1 item 1 `:1100-1108`, RM Phase 4 `:290-299`.
    - Decision rows: FP `:116,121`.
    - DIFFER on gate 4:
      - O14: "line separators refused in `speak` (U+2028 and U+2029…)".
      - §12.1: "line separators refused in `speak`".
      - RM: "the guest-text gate refusing line separators and format characters on decoded text".
    - DIFFER on gate 1: O14 "the worker process (O13)"; RM "the worker process and its channel gate".
    - The OS sandbox: N §6.6 `:765-767` still says "Proposed for the owner", but O30 decided it was deferred by name.
    - Owner: RM Phase 4, since it lists them as flip conditions. Alternatively N §12.1. Either way O14 should become a pointer.

14. **The guest-text gate's character list.**
    - DEFINES: N §5.2 `:556-558`, N §6.6 `:860-864`, B §5.3 row.
    - DIFFER: §5.2 lacks the Cf, zero-width and tag characters that §6.6 and B include. O14 names only U+2028 and U+2029.
    - IG §6 `:186` says N §6.6 owns the list.
    - Owner: N §6.6.

15. **Consent and taint.**
    - Owner: IG §6.
    - Copies: IP §0 O51 `:38` and O55 `:42`, which agree; IP §6.2 `:346`; N O18 `:58` ("local model only, by default"), which agrees in substance.
    - Purge: N O17/O26 and IG §6 O54 complement each other.

16. **Thought request id and authority.**
    - B §6.1 `:377-393` (the authority table, and `(tick, actor, n)`), N §4.7 Authority `:494-498`, N §11.1 `:1070`. They agree.
    - Owner: B §6.1.

17. **Invocation pid exactly once.**
    - N §6.4 `:692-698`, RM Phase 3 exit `:268-272`, `checklists.md:373-376`. They agree.
    - Owner: N §6.4.

18. **Per-NPC seed derivation.**
    - N §3.4 `:294` and B §7.3 `:579`, with the same `SeedSequence` formula.
    - B omits that Maxim's streams derive through `make_agent_rng` (O40). That is incomplete rather than contradictory.
    - Owner: N §3.4.

## Superseded records that still state these contracts
- **RLC §4.3** has a supersession banner, but its text contradicts the current contract:
  - `:246`: "The model call's own wall-time timeout only frees its worker", against N §1 `:97`: "never silently 'frees a worker'".
  - `:261`: "priority, then age", against N §4.4's dispatch by deadline.
  - "One thought in flight per NPC" is stated only there; N §11.1 `:1079` keeps it "still standing" by pointing at it.
- **`world_v2.md` §6** `:273-296` has no banner of its own (`world_model.md` says it stays as a record):
  - "Inputs … thought results and worker failures", against B §6.2: "an NPC's thought is never a log input".
  - "the world never waits", against dilate.

## Proposed owners
- AgentPort, lane, worker and codec: N §6.6 and §6.3.
- Clocks: N §1.
- Latency: N §4.4.
- Budgets: N §4.7.
- Outcome vocabularies and cache: IP §2.6 and §4.2.
- Gateway processes, channel and consent: IG §2, §3 and §6.
- Receipts: SS §6.2.
- Authority and request ids: B §6.1.
- OD ids: RM Phase 3.