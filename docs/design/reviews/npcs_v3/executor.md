# Executor lens: `npcs_and_sem.md` v3, the agent-half revision (3db82a8)

Read: `git show 3db82a8` (npcs_and_sem.md v3, boundaries.md, embeddable_agent_DRAFT.md v2, roadmap Phase 3,
hybrid_1_5_line_DRAFT.md), every file in `reviews/maxim_response_1/`, and Maxim `origin/main` 7084f561 via `git show`
and `git grep` only. Nothing in either repo was checked out, fetched or written, apart from this file.

**Counts:** 1 BLOCKER, 6 SHOULD-FIX, 10 NIT.

## What I checked and found true

- **`foldtable.py` works as claimed.** I ran it on a `git archive` copy of 3db82a8 in a scratch directory. It prints
  `93 {'folded': 87, 'partial': 5, 'not folded': 1}` and rewrites `npcs_and_sem.md` byte-identically, so the committed
  table is the generated one. Deleting the `BD-2` row exits 1 with `missing rows: ['BD-2']`. Appending `| BD-99 | x |`
  to `bio_determinism.md` exits 1 with `missing rows: ['BD-99']`. The id extraction is complete: 19 BD, 14 TBR,
  18 Arch plus `Arch §5`, and 41 Executor (32 lettered rows, 2 dash rows, N1–N7), which is 93.
- **Maxim citations that hold on 7084f561:** `agent_loop.py:521` (`_run_deliberation_cycles`), `:1571` (prefetch),
  `:2172`, `:2264` (the follow-up), `:3086-3125` (max_cycles is 2, or 3 with a percept source, counting cycle 1);
  `llm_worker.py:1355` (`next_actions`), `:1322-1338` (the fallback); `router.py:185`, `:1080`; `bio_stack.py:654`;
  `prompt_builder.py:237`, `:1125-1127`; `context_pool.py:468`, `:493`; `llm_fallback.py:290`;
  `memory_hub.py:719-727`; `semantic.py:662`; `tool_bridge.py:580-582`, `:864-892`; `tool_dispatch.py:370`,
  `:1290-1291`; `nac.py:1162` (wall `now`) and `:1163` (`time_ns` ids, OD-A7); `sem.py:113-116`;
  `loop_controller.py:157`; `cloud_redaction.py:205`, `:246` (`splitlines()`, OD-I5); `api.py:113` (`force=True`);
  `lane_backends.py:1246`; `hybrid_arbitration.md` `basis_seq` (`:91`, `:256`); and `test_no_effect` in
  `tests/integration/test_advisor_gate.py`.
- **Counts:** 608 `time.time()` lines in 178 files, 145 `time.monotonic()`, 36 `default_factory=time.time` in 19
  files, and the five `x or time.time()` sites of OD-I1 (`salience_map.py:227`, `salience_network.py:222`,
  `cost_tracker.py:376`, `:469`, `:480`). All reproduce.
- **The shortcut correction is right.** Maxim's second answer says it fires on any `triggering_input`, and it does
  (`prompt_builder.py:1104`, `:1131-1132`, for questions of 8 words or fewer). The "maxim" wake word gates only the
  `cli_inputs` branch (`:1108`), so the synthesis's "triggered by the word maxim" was the narrower case, and v3 is
  right to drop it.
- **The owner decision rows** O3, O6, O7, O11a, O13, O14 and O15a match `a893a1e` and `ea2c74b` apart from the edits
  listed under N9. O6a and O7a are new in this commit, and their text matches response.md, response_2.md and
  architecture.md §5.
- **The floor-holding citations** (O11a, §4.4): Stivers & Robinson is cited for the order only, Kendrick & Torreira
  for about 700 ms, and Jefferson 1989 for 1 s. Roberts et al. 2006, Clark & Fox Tree 2002, Smith & Clark 1993,
  Bögels 2015, Castellucci 2022 and Yagishita 2014 all trace to `bio_determinism.md`, where each is marked
  *verified*.

## BLOCKER

**B1. §6.3, O13, `boundaries.md` §7.3: "the process boundary is the trust boundary" isn't true as specified, because
nothing gates the worker-to-host channel.** O13 and §6.3 specify the worker side in detail (spawn, a scrubbed
environment, the latch after the pipe opens) but say nothing about how the host decodes what comes back. The pipe has
no row in `boundaries.md`'s gate table, no version, no codec and no rejection tests. Python's default for this,
`multiprocessing.Connection.send`/`recv`, unpickles.
*Failure scenario:* a leak path Maxim hasn't closed yet (which O13 exists to contain, and §12.2 relies on: "the worker
process contains them meanwhile") lets prompt-injected guest text get code running in the worker. The worker then
sends a crafted pickle as its `StepOutput`, and the host's `recv()` executes it in the world server, which holds the
keys, the saves and the network. The containment the design claims is gone.
*Fold:* add the worker channel as a registered gate with the strictest contract, the same as the response cache:
bytes only (`send_bytes`/`recv_bytes`), a versioned, pickle-free codec, size budgets, a strict decoder that refuses
unknown fields, golden rejection frames, and a test with a planted malicious frame. State that the host treats every
worker message (`StepOutput`, `Pending`, writes, the continuation blob) as untrusted input. The continuation is
"opaque" in §6.2, so say who validates it on load.

## SHOULD-FIX

**S1. Fold table: at least three "folded" rows didn't fully land, so 87/5/1 overstates the fold. On my spot checks
the honest count is about 84/8/1.** The script proves that every id has a row. It can't prove that a "folded" status
is true, because the statuses are typed in by hand.
- **TBR-4** ("O13, §6.3: spawn, the latch after the pipe"). TBR-4's second hazard is that `import maxim` latches
  the **host** when `MAXIM_OFFLINE` is set (`__init__.py:25-31`, `trust_boundary.md:107-110`), which matters
  because this owner develops Maxim on the same machine. v3 never mentions it. With O13 the host should not import
  `maxim` at all, or should refuse to start with `MAXIM_OFFLINE` set. Say which.
- **Exec N5** ("§6.1: keyed substreams, `seed_all` banned"). N5's point was that `random.Random` conflicts with
  Overdrive's rule that randomness comes from a numpy `Generator`. v3 adopts `random.Random` per stream and doesn't
  reconcile the two (see S3).
- **Exec N7** ("§6.1 uses the corrected citations"). §6.1 still cites `agent_factory.py:1168-1172`,
  `memory_hub.py`, `semantic.py`, `tool_bridge.py`, `nac.py` and `tool_dispatch.py` without their directories, and
  N7 asked for exactly that fix. §1 still cites `prompt_builder.py:1104` for the host date and time. That line is the
  `triggering_input` check; the time is rendered at `:1125-1127`.
*Failure scenario:* the owner reads 87 of 93 folded and treats this round as closing the review, while a host-latch
hazard and an RNG contradiction stay open.

**S2. Roadmap Phase 4 wasn't updated, though O15a gives it as a location ("§6, roadmap Phase 4").**
`roadmap.md` Phase 4 still says it "starts on tier A ... (Phase 3, OD-A1 to OD-A16)". It doesn't mention the 1.4.0
cut or the decomposition slice, and it omits OD-A17 (the leak closure) and OD-A18 (dispatch/settle, which OD-A16 now
"rides on"). Phase 3's exit lists OD-WC1 and OD-EA5 but not OD-EA10 or OD-EA11.
*Failure scenario:* Phase 4 starts once OD-A1 to A16 ship. Both OD-A16 and OD-A15 depend on OD-A18 and on 1.4.0, so
either the entry criterion can be met while its own dependencies are missing, or it is unsatisfiable as written.
*Fold:* restate Phase 4's entry as OD-A1–OD-A18 plus Maxim 1.4.0 and the decomposition slice, and add OD-EA10 and
OD-EA11 to Phase 3's exit.

**S3. §3.4 and §6.1 give two incompatible keying schemes for agent randomness, and one names a function Maxim
doesn't have.**
- §3.4 derives agent streams as numpy `SeedSequence(root, spawn_key=(NS_AGENT, npc_key, stream_key))`, using Philox
  with counter layout rules.
- §6.1 (and OD-A7) uses `random.Random(stable_hash_64(seed, agent, stream))`. Maxim's `utils/seeding.py` has
  `stable_hash_32(text)` and `stable_hash_64_signed(text)`; there is no `stable_hash_64` and no three-argument form.
- §3.4's bullet "Maxim's proposed `Rng` is sequential ... Keyed substreams are an upstream ask (§8.2)" is stale,
  because Maxim accepted keyed substreams in its second answer.
- §6.1 doesn't say where the agent's `seed` comes from (§3.4: the host, from the log header's root).
*Failure scenario:* the adapter author picks one scheme for percept noise and Maxim picks the other for internal
draws. The two trees then derive from the root differently with no overlap guarantee, and §3.4's test ("adding an
NPC leaves every other NPC's draws bit-identical") covers only one of them.
*Fold:* one derivation, stated once. Either the host hands Maxim an integer seed per `(npc_key, stream_key)` from
§3.4's tree, or §3.4 adopts Maxim's form. Name the real hash function, and update §3.4's stale bullet.

**S4. §6.3's barrier arithmetic is still in-process, while O13 puts a pipe round trip into every park.** The meter
line keeps "50 µs each is 10 ms per second per NPC" at 200 ticks per wall second. Under O13, every agent's `step` on
every tick is a cross-process round trip plus a frame serialised to each worker. That cost is "measured before
Phase 4 commits", but there's no estimate and no budget.
*Failure scenario:* 20 NPCs × 200 ticks/s × (pipe round trip plus frame encode and decode, plausibly 50–200 µs in
Python) is 0.2–0.8 wall seconds per second spent on the barrier alone. That is enough to make the dial unreachable at
20×, and §4.5's throughput table doesn't account for it.
*Fold:* state the order of magnitude now (round trips per tick × NPCs × dial), give it a B5 budget, and name the
fallback (step idle agents less often, batch frames, or step inline once inline stepping is decided).

**S5. §6.5 still says the membrane factory "takes a frame source and the intent sink (`boundaries.md` §7.2)", but
this same commit deleted the intent sink from boundaries.** Boundaries now says the factory "takes a frame source and
returns intents in `StepOutput`", and lists the sink among the deleted host-service handles. The older fold tables
still point their BLOCKER rows at mechanisms that are gone: Wire B2 says "§6.2 intent sink as a required port" in
`npcs_and_sem.md:1015` and "§7.1 (intent sink as a required port)" in `boundaries.md:942`. Arch B3 says "§6.2 port
split" and "§7.1 (port split, gateway)".
*Failure scenario:* the `phase1/agents` implementer follows §6.5 and builds a sink handed down to the adapter, which
reintroduces the upward reference that v3 deleted. A reader auditing the foundations BLOCKERs finds their fixes
pointing at removed text.
*Fold:* fix §6.5 and re-point those four rows, for example "superseded by O6a: intents return in `StepOutput`".

**S6. O14's five gates have no home: no exit test, no red gate and no roadmap row.** The no-effect test, the
dialogue-level bypass test, the line-separator refusal, and provenance with purge exist only as O14 and §12.1 item 1.
- The embeddable draft's exit tests cover Maxim's side (OD-EA10 is the advisor's closure tests), not a dialogue-level
  test driving guest speech through a real worker.
- Neither the roadmap nor `boundaries.md`'s gate table names a guest-session gate.
*Failure scenario:* co-op lands (`phase1/lanes`) with the test double. Real NPCs arrive in Phase 4, and nothing
mechanical stops a guest session from reaching them, because the decision has no check.
*Fold:* add a strict red gate, "guest sessions refuse real-Maxim NPCs until O14", owned by a named PR. List the five
tests under Phase 4, or under a co-op step.

## NIT

- **N1. §1 "Today's violation" vs §12.2.** §1 cites `prompt_builder.py:1104` and gives "about 880 host-clock reads in
  about 215 files". §12.2 gives 608 + 145 + 20 on 7084f561. Use one snapshot, or name which `main` each count was
  taken on.
- **N2. Citations missing their directories,** in §6.1 and §6.4 (`agent_factory.py`, `memory_hub.py`,
  `semantic.py`, `tool_bridge.py`, `nac.py`, `tool_dispatch.py`) and in the draft (`cloud_audit.py:49` and
  `response_config.py:65` are under `utils/`; `lane_backends.py:1246` is under `runtime/`). The facts behind them
  hold.
- **N3. §6.1's `AgentHome` row says "about nine families"** but then lists ten: embeddings, fear, escalation, DN
  thresholds, focus, bounds, energy, cost, provenance and lane decisions.
- **N4. §6.1's roster row says the CLI registers "file, shell and internet tools (`runtime/bootstrap.py:255-276`)".**
  That range registers only the internet tools (behind `internet_policy_getter`). The file tools are at `:132-135`
  in `build_tool_registry`, and `BashTool` is imported at `:27`.
- **N5. "Up to 3" PFC calls is Maxim's default, not a ceiling.** `llm.deliberation_max_cycles` and
  `MAXIM_LLM_DELIBERATION_MAX_CYCLES` (`runtime/config_loader.py:139`, `:551`) override it, with only `≥ 1` checked
  (`:1617`). The host cap in `thought_budget.yaml` covers this, and the worker's scrubbed environment removes the
  variable. Say "default" in §0, §4.2 and §4.5. §4.5's 0.11× row also leaves out the modelled P1c cycle cost that
  §4.2 adds to D.
- **N6. OD-H4 is folded into OD-H5** (the OD-H5 row and the hybrid draft both say so), yet roadmap row OD-H4 and
  §8.1 and §8.2 still list it on its own. §8.1's "OD-A10–OD-A15" includes OD-A13, which has moved to OD-I3.
- **N7. `step` has three signatures:** `step(now_tick, dt_ticks, frame)` in `boundaries.md` §7.1,
  `step(world_dt, frame)` in §6.1 and O6, and `step(agent, world_dt_us, frame)` in the draft. §9 says integer
  microseconds end to end. Pick one, or say which is Overdrive's port and which is Maxim's function.
- **N8. `foldtable.py` hygiene:**
  - its paths are relative, so it must run from the repo root, and nothing says so;
  - the two dash rows become ids cut at 40 characters ("Citations for the resumable-think cut po");
  - a finding written in prose without the expected pattern would be silently skipped;
  - no gate reruns it, so a later hand edit of the table goes unnoticed.
  None of these makes the current output wrong.
- **N9. Owner decision O14's text was edited in this commit** ("forge redaction headers" became "may forge prompt
  and redaction headers ... its own security issue, OD-I5"), and nothing marks the edit. The edit matches Maxim's
  answer, but an owner row should carry a dated note when it changes.
- **N10. The shortcut citations differ between the documents.** §6.1 cites only `llm_fallback.py:290-330` for "fires
  on any input". The gate that makes it fire is `prompt_builder.py:1102-1132`, which the draft cites. §12.1 item 1's
  "which trigger on 'maxim'" reads as applying to the shortcut, but only the phrase commands and the `cli_inputs`
  branch use the wake word.
