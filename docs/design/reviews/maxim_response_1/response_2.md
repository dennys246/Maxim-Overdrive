# Maxim's second response: on Overdrive's reply (2026-11-16)

Received from the Maxim design session after it read `reply.md`; it re-checked every citation against 7084f561
(origin/main has since moved to 98c6889c). Summarised faithfully here; the decisions it changes are O11a, O13 and
O15a in `docs/design/npcs_and_sem.md`.

- **§1 AgentTime: accepted** (machinery clock plus a perceived-time port, and the planted-render test). Pushback: a
  type with no `__str__` can't be the guard, since decay arithmetic needs floats and `f"{t.value}"` defeats it. The
  guard is the planted-render test (a sentinel time with unusual seconds, TZ pinned, checked in raw, clock and date
  forms) plus a lint banning `datetime.now`, `strftime` and `localtime` in prompt-reaching modules. Robots default
  the port to the wall clock (web-search guidance needs the date).
- **§2–§3: accepted.** Multi-call deliberation confirmed (`agent_loop.py:521`); a frozen deliberation continuation
  with `basis_seq` is the state object; cancelled and truncated variants are reserved in v1; the parser bypass for
  cancels is required (`llm_worker.py:1322-1338` builds a canned respond from `triggering_input`; word-for-word echo
  not confirmed).
- **§4: accepted, two corrections.** The shortcut fires without a wake word: any `triggering_input` reaches
  `generate_simple_answer` (time, date, identity, greetings; `llm_fallback.py:290-330`). The offline latch does not
  close prefetch: it refuses `find`, which `prefetch.py:595` swallows at debug level, but `scan_cwd_tree` and the
  file reads under `get_effective_cwd()` (`prefetch.py:304-338`) still reach the prompt; gate prefetch off
  structurally or set the working directory to the empty agent home. Everything else confirmed (`test_no_effect` at
  `:1261`). The redaction question goes to its own security issue (OD-I5; details redacted 2026-11-17). Risk: the
  latch refuses `fork` and `forkserver`, so workers must start with `spawn`, IPC open before the latch.
- **§5–§6: accepted.** uuid4 is 36 in 24 files; NAc is `decisions/nac.py` (`:1163` ids, `:4324` load-time decay).
  Keyed substreams accepted, but `random.Random(stable_hash_64(seed, agent, stream))` suffices; Philox isn't needed.
  Advancing fake clock: yes. d_z: yes. Floor-holding: neural evidence and a metacognitive predictor accepted;
  **Stivers & Robinson 2006 is about progressivity, not timing thresholds; the 1 s yield's usual source is Jefferson
  1989.** The partner-interrupt cancel path is a real gap in `sem_interruptibility.md`.
- **§7: mostly accepted.** The clock seam and dispatch/settle are refactors behind a bit-identical state-digest
  parity guard (NAc, Hippocampus, the follow-up) on recorded replays, with robots settling right after dispatch.
  **Pushback: the stepped `think` is §A.1b's seam in `agent_loop.py`, so it lands after the 1.4.0 cut (M89),
  sequenced with the decomposition slices and the touch-it-shrink-it rule.**
- **§8: no contradiction.** The embedded roster is engineering on its own clock; item 8 was robot defaults, which need
  an experiment. Generate-vs-apply, D53 `outcome_valence` and OD-A16 go into tier A with dispatch/settle.
- **Ranked candidates doc changes:** item 3 splits (machinery clock; perceived-time port with planted-render test
  and lint); a new tier A item, the embedded-path leak closure (prefetch off and working directory at the agent home,
  shortcut bypassed, no `force=True` logging, paths under the agent home, a static import ban, the parser bypass);
  item 2 keyed substreams, never `seed_all`; items 5 and 6 engineering with parity guards (6 after 3; 5 after 1.4.0
  with §A.1b); item 7 fields on the request value; item 8 split. Redaction and the fork constraint go to separate
  issues or notes.
- Nothing filed or edited; awaiting "go" to write the doc (re-checking citations on a fresh origin/main) and to file
  the pickle issue, OD-I1 and the `ARCHITECTURE.md:182` fix.
