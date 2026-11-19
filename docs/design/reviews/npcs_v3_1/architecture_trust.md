# Architecture and Trust boundary lenses (delta): the v3.1 fold (commit f839075)

Reviewer: one delta reader for the Architecture and Trust boundary lenses. Read: `npcs_and_sem.md` v3.1 §6.1-§6.6,
§5.2, §7.2-§7.3 and §12.1, the `boundaries.md` diff (§5.2-§5.4, §7.1), `embeddable_agent_DRAFT.md` v2.1 §2-§3,
roadmap Phase 4, and `reviews/npcs_v3/{architecture,trust_boundary}.md`. I checked Maxim claims with
`git show origin/main:<path>` (7084f561), and checked CPython behaviour against the installed interpreter. I edited
nothing except this file.

Scope: only the fold and what it opens. Every finding has an id `ATR-*`.

## Verdict

The fold does the right thing structurally. The worker channel is now a registered gate with a closed codec, the
host re-validates everything it decodes, `apply` and `settle` are the only writers, budgets sit in a host-owned
header, and there is no upward callback. On question (6) I found **no second door or callback running the wrong
way**: every message is a host-initiated request with a worker reply.

Two of the mechanics, though, don't do what the text says, and both are checkable today:

- the interpreter flag that isolates the worker throws away the pinned hash seed (B1);
- "no `HOME`" doesn't keep the worker out of the owner's home. That reaches the owner's model profiles, and
  through them a model backend. So "second doors fail closed" is not true as designed (B2, S4).

Below those sit several edges where something still crosses without validation, or without the host seeing it:

- the worker's stdio (S1);
- the model gateway's replies (S2);
- writes and threads inside the worker (S5);
- provenance that the worker reports about itself (S6).

The world half also still names an in-worker method as the gate for NPC tool calls (S7).

Counts: **2 BLOCKER, 10 SHOULD-FIX, 7 NIT.**

---

## BLOCKER

### ATR-B1. `python -I` ignores `PYTHONHASHSEED`, so the env allowlist's pinned hash seed is dead

**Where:** `npcs_and_sem.md` §6.6, "The process" and "The environment is an allowlist" (`Popen([sys.executable,
"-I", ...], env=<allowlist>)`, with "`PYTHONHASHSEED` (pinned per run and recorded in the log header)").

`-I` implies `-E`, and `-E` ignores **every** `PYTHON*` variable, `PYTHONHASHSEED` included. I checked it against the
installed CPython: with `PYTHONHASHSEED=0`, plain `python3` prints the same `hash("abc")` twice
(`sys.flags.hash_randomization == 0`), while `python3 -E` and `python3 -I` print different values each run (flag 1).

**Failure scenario:** two runs of the same scene, rig and intent log, with the same recorded seed. Each worker starts
with a fresh random hash seed. Any Maxim path that iterates a `set` or `frozenset` of strings diverges between the
runs: tool or candidate ordering, a set of entity names, a set-built prompt section. The log header records a seed
that was never in effect, so the record misleads whoever debugs the divergence. The [now] determinism tests with the
test double pass anyway, because the double doesn't depend on hash order. The gate is green, and the shipped path
breaks the day real Maxim arrives.

**Fix:**

- Keep the environment on, since the allowlist already controls every variable, and isolate `sys.path` another way.
  Either use `-s -P`, which needs Python 3.11 (`pyproject.toml` allows 3.10, so raise the floor and say so), or use a
  launcher that drops the script and working directory from `sys.path` before anything is imported. The agent home
  is model-writable, so it must never be on `sys.path`.
- Add a mechanical check: the worker's first frame reports `sys.flags.hash_randomization` and
  `hash("<fixed probe>")`, and the host refuses a value that doesn't match a reference child spawned with the same
  seed.
- Prove the guard: put `-I` back, and the check goes red.

### ATR-B2. "No `HOME`" falls back to the owner's real home, so the worker reads the owner's Maxim config

**Where:** §6.6, "The environment is an allowlist" ("No keys, no `HOME`"), and "The worker is a container" ("It
contains the paths Maxim's code takes by default (working directory, home, ...)"). Also §12.1 item 1 ("which
`AgentHome` and the worker's environment allowlist close", TBR-13) and `boundaries.md` §5.3 "Agent homes".

When `HOME` is unset, `os.path.expanduser("~")` and `Path.home()` fall back to the password database. I checked it:
`env -i python3 -c 'import os; print(os.path.expanduser("~"))'` prints the real user directory. Maxim has 29 `src/`
files that call `expanduser` or `Path.home()`. Among them, on 7084f561:

- `models/language/profile_loader.py:133`: `profiles.yml` comes from `XDG_CONFIG_HOME`, otherwise
  `Path.home()/".config"`. That is the owner's model-profile file, and a profile can name a local model path for the
  in-process `models/language/llama_backend.py`;
- `api.py:179` (`Path.home()/".maxim"`);
- `console/health.py:82`.

Without `TMPDIR`, `tempfile` on macOS falls back to the shared `/tmp`. Without `HF_HOME` or `XDG_CACHE_HOME`, a cached
Hugging Face model under the real home loads even with `HF_HUB_OFFLINE=1`.

**Failure scenario:** the worker resolves `profiles.yml` from the owner's `~/.config/maxim/`, finds a local llama
profile, and builds an in-process backend. The offline latch doesn't stop this: it refuses sockets and spawns, not
file reads or native inference. `AdaptivePlanner` then calls a model outside `think`, with a guest's words in its
decomposition context. The call is unbudgeted, unlogged and nondeterministic, which is exactly what "second doors
fail closed" claims is impossible. Separately, any literal `~/.maxim` write lands in the owner's home, so TBR-13's
"closed" is false for those sites. The roadmap's no-effect test ("no file writes ... outside the agent home") misses
the profile read, because it watches writes only.

**Fix:**

- Set `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `TMPDIR` and `HF_HOME` explicitly, each to a
  directory under the agent home, and add them to the named allowlist.
- Add a worker-side test: `Path.home()`, `expanduser("~")`, `tempfile.gettempdir()` and `profiles_config_path()` all
  resolve under the agent home.
- Extend O14's no-effect test to **reads** outside the home. An `open` audit hook in the worker under test does it,
  the same mechanism the latch uses.
- Correct §12.1 item 1's TBR-13 claim.

---

## SHOULD-FIX

### ATR-S1. The worker's stdin, stdout and stderr are inherited: a second, unvalidated channel to the host

**Where:** §6.6 "The process" (`close_fds=True, pass_fds=(<child end>,)`); "Everything from the worker is untrusted
input".

`close_fds` doesn't close fds 0-2. Maxim's `configure_logging` always attaches a `logging.StreamHandler()`, which
writes to stderr (`utils/logging.py:150`). `ToolPainBridge` logs the failure text and context at debug
(`bridges/tool_pain_bridge.py:807`).

**Failure scenario:**

- A guest line holding an ANSI escape or OSC sequence, echoed in a Maxim log line, reaches the operator's terminal
  raw. The guest-text gate refuses C0 controls in `speak`, but the model can emit the escape itself, and the worker
  logs model output before any host gate sees it.
- If the host's stderr is captured to a log, guests' words land there, past bug-report redaction (§5.2).
- A worker inherits the host's stdin and can consume operator keystrokes.
- If the host's stderr is a pipe nobody drains, a chatty worker blocks on `write`, misses its park, and is killed as
  `hung`. The kill reason is then wrong.

**Fix:**

- Spawn with `stdin=DEVNULL` and `stdout=DEVNULL`.
- Send stderr either to `DEVNULL` or to a pipe the host drains into a bounded per-agent file under the agent home,
  never into the host's own log.
- Have the worker configure its logging to a file in its home. That is OD-A17's "no `force=True`" item, made
  concrete.
- Test: a worker that prints to all three streams leaves the host's streams unchanged.

### ATR-S2. The model gateway's replies are an input with no gate row

**Where:** `boundaries.md` §5.3. The rows "Thought budgets" and "The response cache" cover token counts and disk. No
row covers the reply bytes themselves. §6.6 adds that "A chunk the guest-text gate refuses mid-stream ends the reply
as `truncated`".

The host's thinking lane decodes bytes from a local model server or a remote provider. It also extracts the
top-level speech field from a partial JSON stream ("speech is a top-level field emitted first"). That decoder is a
transport receive in the host (§5.2), and it is unregistered.

**Failure scenario:**

- A local server returns an unbounded body, invalid UTF-8, or JSON with two `"speech"` keys. The host's streaming
  extractor takes the first, and the worker's parser of the `complete(text)` reply takes the last.
- Players hear one line. The NPC's `ThoughtOutput`, and so its memory, records another.
- Nothing says which is authoritative, and §6.6's "a worker reply that contradicts the header is a protocol error"
  only covers the header's delivered prefix if `ThoughtOutput.speech` is checked against it.

**Fix:**

- Add a §5.3 row, "Model replies (host thinking lane)", under the strictest contract: a byte budget before
  allocation, strict UTF-8, duplicate keys refused, and the streaming speech extractor as the registered gate with
  golden rejection streams.
- State that host-delivered speech is authoritative. A `ThoughtOutput` whose speech differs from the header's
  delivered speech is a protocol error.

### ATR-S3. "Sends a refused frame is killed" makes NPC death guest-triggerable

**Where:** §6.6 codec ("An unknown kind, field or version ends the agent") and the hung or dead bullet ("sends a
refused frame is killed"); `boundaries.md` §5.3 worker-channel row.

The text doesn't separate **protocol** violations (framing, kind, version, wrong actor, oversize frame) from
**value** refusals in a well-formed frame: an intent failing stage 1, speech failing `engine.text.player_text`, or a
memory write over budget or for another NPC.

**Failure scenario:** a guest coaxes the model into a line containing a tag character, or into an imagined object
over the primitive budget. The worker frames it faithfully, host stage 1 refuses it, and if that counts as "a refused
frame" the NPC is killed and stays inert until the host restarts it. Any guest can then switch off any NPC by talking
to it.

**Fix:**

- Only protocol violations end the agent.
- A value refusal becomes a `refused` receipt, or `thought_failed(reason=validation)`, through the normal path, and
  the agent lives.
- Test: an over-budget write and a Cf-bearing line from the double leave the NPC alive, with the refusal logged.

### ATR-S4. "Second model doors fail closed" can't be asserted: one door swallows the refusal, one never raises

**Where:** §6.6 "The model has more doors than `think`" ("each such call fails closed, and a test asserts the
refusal"); embeddable draft §3.

On 7084f561 the two doors behave like this:

- `ToolPainBridge`'s reflection catches `except Exception` and returns `None` with a debug log
  (`bridges/tool_pain_bridge.py:807`). `OfflineRefusal` is a `RuntimeError`, so it is swallowed too.
- `AdaptivePlanner._decompose` returns `None` when `self._llm` is falsy (`planning/adaptive_planner.py:483`). With no
  backend there is no refusal at all, only silently different planning.

A test has no refusal to observe from outside. With B2, a backend may exist anyway. A silently degraded planner also
means an NPC plans differently from a robot, which undercuts the parity claim ("one deliberation path").

**Failure scenario:** a Maxim release adds a fallback that builds a default router when `llm is None`. Nothing in the
host notices, and the "assert the refusal" test still passes because it asserts an absence.

**Fix:**

- Fill every model slot in the worker with a refusing sentinel that counts each call by door. Report the counters in
  every park ack, and have the host log `model_door_refused(npc, door)`.
- At each park, check that no backend module (`llama_backend`, `cloud_dispatch`, `lane_backends`) is in
  `sys.modules`.
- Test: drive each named door with the double plus a real-Maxim red gate, and assert the counters.
- Name the parity cost in §12.2 as an OPEN divergence until each door becomes a request through the cut.

### ATR-S5. "`apply` and `settle` are the only writers" is a promise about worker code the host can't see

**Where:** §6.6 "Who writes" ("Nothing writes agent stores from inside a call"); §6.3 "parked"; the embeddable draft
§2.

The worker owns the agent home and its filesystem, so the host's gate covers the writes the worker chooses to return.
On 7084f561 there are writes on the step and settle paths that aren't values:

- `adaptive_planner.py:492` calls `activate_after_use`, a retrieval strengthening;
- `ToolPainBridge._store_reflection` writes the hippocampus (`:549`, `:606`);
- the ConceptExtractor thread starts at construction (`runtime/bio_stack.py:654`, OD-A12).

A background thread also makes "parked" untrue: the worker has answered, but it is still mutating state.

**Failure scenario:** a guest's line is concept-extracted on the extractor thread, outside `apply`, with no
provenance and at a wall-clock-dependent moment. The barrier sees a parked agent. The digest differs between reruns,
and the purge (O14 gate 5) can't find the concept.

**Fix:**

- Add a mechanical worker-side assertion in tests and in real-Maxim runs: `threading.active_count() == 1` at every
  park, reported in the ack, plus an agent-home digest unchanged across `step` and `resume` (test mode).
- Make OD-A12's extractor and the A18 write census explicit preconditions for removing the real-Maxim red gate and
  for O14 gate 5.

### ATR-S6. Provenance is self-reported by the worker, and the purge has no message and no reach

**Where:** §6.6 "Memory provenance"; "Who writes" ("The host gates them (... provenance stamped ...)"); the closed
host-to-worker kinds (`step, resume, apply, settle, save, load, shutdown`); §12.1 item 7.

The host can't compute what a derived write derives from. Summaries, relays and extractions happen inside the model
and the worker, and retrieved memories are known only to the worker. So the "union of its sources' sets" is whatever
the worker claims. The purge also has nowhere to go:

- there is no `purge` kind on the channel;
- the opaque continuation body holds transcripts the host never decodes;
- the response cache stores the canonical request, guests' words included;
- the intent log stores `speak` text, because replay must reproduce who heard what.

**Failure scenario:** NPC A stores M1 with provenance {guest}. Later a thought recalls M1 and writes a summary M2
whose reported set omits the guest: a Maxim bug, or a write path that drops the field. After the purge, M2 still
carries the guest's injected instruction. The exit test passes only if it exercises the one path that propagates.

**Fix:**

- The host computes a **lower bound** for each thought's writes: the union over the triggering input, the percepts it
  sent for that thought, and every trace id the thought reports reactivating (BF3-6's `retrieval` writes), looked up
  in a host-side provenance index. A claimed set that lacks the bound is a protocol error.
- Add `purge(actor, session)` to the closed kinds, with an ack listing the purged ids.
- Name the purge's scope: agent stores, continuation bodies (purged by the worker), the response cache, and saves.
- Put the conflict between replay and the immutable log to the owner as a decision: redaction records, or replay of
  purged sessions refused.

### ATR-S7. `boundaries.md` §5.2 and §5.3 still put the NPC tool-call gate inside the worker

**Where:** §5.2 registry rule ("In-process objects from Maxim ... reach the engine only through those methods, so
they are covered without an input primitive"; "every method of a class implementing a Maxim protocol
(`Modulator`) ... is an entry point"); the §5.3 rows "NPC tool calls" (gate `StructureModulator.execute`) and
"`target=<Entity>`" ("resolved to a stable id at `execute`").

Under O13, `execute` runs in the worker, which is the untrusted process. The new §5.4 paragraph says the assumption
"no longer holds", but the rule it contradicts is unchanged and still mechanically enforced.

**Failure scenario:** the registry is green because `execute` has a row and its rejection tests pass, in-process. The
host-side entry point that matters, the channel decoder feeding stage 1, needs a row only because it is "a transport
receive". The planted-`Modulator` proof tests a boundary that no longer protects the host. A refactor that skips
stage 1 in the host on "already validated in `execute`" values passes the registry.

**Fix:**

- Rewrite the §5.2 bullet: for real agents, the entry points are the host-side `AgentPort` proxy (the channel
  decoder), and worker-side `execute` validation is defence in depth.
- Update both §5.3 rows to name the host gate.
- State where `engine.adapters.sem` and `to_maxim_entity` run, which is the worker, since they need `maxim`. That
  closes the "host imports Maxim only through `_compat.py`" loop (N5).

### ATR-S8. Dead-worker semantics contradict the process split, and "restart from last saved home" restarts from a torn home

**Where:** §6.6 hung or dead ("treats the NPC as parked and inert (its body processes go on ...)"; "Restarting it
from its last saved home"); §6.3 ("any push into its body run serialised in its worker").

The body (Maxim's substrate) runs in the worker, so after a kill nothing advances it. "Body processes go on" has no
process to run in. The agent home is also the worker's **live** working directory, so a worker killed mid-`apply` or
mid-`save` leaves it half-written, and that is the "last saved home". The text also doesn't say what happens to the
dead NPC's intents already emitted with a future `apply_us`, or to its requests in the thinking lane.

**Failure scenario:** a worker is killed mid-`apply`. The owner restarts it, and Maxim loads a store with half a
batch applied: a memory without its index entry, or traces without their counts. The NPC's queued strike from before
the hang still applies two ticks later, and a receipt goes to a dead channel.

**Fix:**

- The live home is a working copy, and `save` atomically snapshots it (write then rename), so a restart loads the
  last snapshot.
- On kill: cancel the NPC's pending intents (receipts `cancelled`, never settled) and its thinking-lane requests,
  each as a logged record.
- "Inert" means the body is frozen. Name any host-side body processes explicitly. There are none today.

### ATR-S9. The step frame's content across the channel is unspecified, and the obvious choice ships the whole world

**Where:** `npcs_and_sem.md` §7.2 ("the adapter does this on the agent's owner thread ... as a pure function of the
frame pinned for that agent"), §7.3; `boundaries.md` §4.4 (B-13); §6.6 codec (`step` frame kind, no schema named).

With the adapter in the worker, whatever the frame holds crosses to an untrusted process. If that is the published
frame, every worker holds omniscient state: every actor's position, guests' display names, other NPCs' speech, and
the lab instruments §7.1 says are never an NPC's input. B-13 then rests on Overdrive code inside the worker. It also
costs: frame bytes × 20 workers × 200 ticks per wall second, on top of §6.6's 0.2-0.8 s round-trip budget.

**Failure scenario:** a Maxim pull path that reads a frame field directly gives an NPC sight through walls. Nobody
sees it, because the host never sent a reduced view to compare against. Separately, one guest's display name reaches
every NPC's process, including NPCs that never met them, which widens the purge scope (S6).

**Fix:** the host performs the per-perceiver reduction (B-13 percepts) and the `step` frame carries only that, with a
schema in the codec. B-13 then holds by construction at the channel, and the delta lever in §6.6 shrinks to a
percept delta.

### ATR-S10. Budgets the worker still controls: disk, memory, fds and body bytes

**Where:** §6.6 "Who writes" (the body "reaches the host only as opaque bytes for saving"); §6.3 meters ("memory per
worker" measured, not limited); `boundaries.md` §5.4 ("budgets checked before allocation").

The host enforces budgets on cycles, chains, tokens and writes it can see. The worker controls:

- the size of the opaque body the host stores in saves, with no byte budget;
- the agent home's growth, since stores write directly;
- RSS and the count of open fds.

**Failure scenario:** a long guest conversation grows the transcript in the continuation body and Maxim's stores
without bound. Saves balloon, one worker's RSS takes the machine, and the barrier stalls on swap. The host kills
every NPC as `hung`, which is the wrong reason.

**Fix:**

- Add a body byte budget and a home-size budget to `thought_budget.yaml`, checked before the host stores bytes and at
  save.
- The worker sets `RLIMIT_AS`, `RLIMIT_NOFILE` and `RLIMIT_FSIZE` on itself before importing Maxim. Avoid
  `preexec_fn`, which isn't safe in a host that already runs threads.
- A breach is `agent_failed(reason=budget)`.

---

## NIT

- **ATR-N1** (§6.6 "The process"): the host must close its copy of the child end right after `Popen`. Otherwise
  worker death never shows as EOF on the channel, and "exits" is detected only at the wall ceiling. Reap with
  `wait()`, so no zombies are left.
- **ATR-N2** (§6.6 codec): the closed kinds have `resume` but no `think` start. Either say that `resume(handle,
  None)` starts a thought, or add the kind. Add a `hello` frame carrying versions, the pid and B1's hash probe. Add
  `purge` (S6).
- **ATR-N3** (`boundaries.md` §5.3 guest text): the order reads "length cap, NFC, then on the decoded text". It
  should be decode, then NFC, then the length cap, because NFC can lengthen text (U+FB2C becomes three code points).
  Refusing all Cf also refuses ZWNJ and ZWJ, which Persian and several Indic scripts need in ordinary spelling, plus
  emoji ZWJ sequences and U+00AD. Record that as an owner decision, or allow ZWNJ and ZWJ only between letters of a
  joining script.
- **ATR-N4** (`npcs_and_sem.md` §5.2): the stage-1 `speak` validator still lists no Cf refusal. §6.6 wins by its own
  rule, but §5.2 should point there, as the other superseded sections do.
- **ATR-N5** (§6.6 "The host never latches itself"): the `MAXIM_OFFLINE` start-up refusal is correct and sufficient,
  since the latch engages on any call that sees the variable (`_offline.py:100`). After the split, also add a test
  that `maxim` is not in the host's `sys.modules` after start-up. Otherwise "the host imports Maxim's types only
  through `_compat.py`" has no guard, and the bridge's `to_maxim_entity` (CLAUDE.md) needs a stated home (S7).
- **ATR-N6** (§6.6 hung or dead): a single per-park wall ceiling will kill a worker saving or loading a large home.
  Set the ceiling per message kind.
- **ATR-N7** (§6.6 "a container, not a sandbox"): the worker runs as the user, so it can read the per-install HMAC
  key that guards agent homes (`boundaries.md` §5.3). A compromised worker can forge a home that a later load
  trusts. Name this in the container caveat.

## On the six questions, briefly

1. **The worker channel as a gate:** yes in its codec, kinds, actor binding and host re-validation. Four things
   still cross unvalidated:
   - stdio (S1);
   - the filesystem, reads included (B2);
   - the model gateway's reply decoder (S2);
   - frame content going the other way (S9).

   A refused value must not kill the agent (S3).
2. **Port ownership:** the header and body split is sound, and budgets are host-held. "Only writers" holds for what
   the worker returns, but nothing yet guards it (S5). The worker still controls the body, disk and memory sizes
   (S10).
3. **Hung or dead workers:** the record and the inert-and-parked semantics are right, but the body claim, the torn
   home and orphaned intents are not pinned (S8). The `MAXIM_OFFLINE` refusal is sound (N5).
4. **Guest text:** one gate on decoded text is right, apart from the order and the ZWJ policy (N3). Provenance across
   relay and extraction is self-reported, and the purge has no channel message and no reach (S6).
5. **Second model doors:** not enforceable as written (B2, S4).
6. **The world half:** coherent apart from the stale gate rows and the registry rule (S7). There is no wrong-way
   callback.
