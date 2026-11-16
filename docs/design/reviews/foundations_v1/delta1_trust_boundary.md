# Trust boundary lens, delta round 1: boundaries.md v3, npcs_and_sem.md v2, the Maxim drafts (at 18623ce)

Reader: Trust boundary. Commit: 18623ce. Date: 2026-11-16. **Counts: 1 BLOCKER, 7 SHOULD-FIX, 8 NIT.**

Inputs: `git diff 4f7a754 18623ce -- docs/`, focusing on `boundaries.md` §5–§7, §10, §13, `npcs_and_sem.md` §1, §4,
§5.2, §6, §12, `docs/maxim_upstream/embeddable_agent_DRAFT.md` and `issues_now_DRAFT.md`. The previous round is
`trust_boundary.md` (TB2-*). Maxim was read only through `git -C ../Maxim show origin/main:<path>` at `7084f561`; every
Maxim citation below is from that commit.

**Summary.** Round 1's three BLOCKERs are now addressed in principle: a closed roster, per-agent homes with a red
gate, thought budgets with a liveness rule. The gaps are in how those rules meet Maxim as it exists on `origin/main`:
1. Liveness is bounded per call, not per thought or over time, so a guest can still hold the host's world (B1).
2. The roster check ignores Maxim's other ways in, and ignores the effect and policy machinery Maxim already has
   (S1, S2).
3. The interim home guard covers `data_home()`, but other readers still reach the owner's files and LLM config (S3).
4. Player speech has a non-tool command channel into Maxim (S4).
5. The plain-text rule has no guard (S5).
6. The owner's question about refusing guests rests on an ambiguity the design should settle first (S7).

## BLOCKER

### DTB-B1. A guest can still hold the host's world: liveness is per call, the ceiling has no value, and nothing bounds dilation over time

`npcs_and_sem.md` §1 ("Under the dilate policy a timeout retries, and past a host ceiling the thought ends"), §4.4
("a **call** past the host's wall ceiling ends as `thought_failed(reason=timeout)`"), §4.7 (the budget list),
`boundaries.md` §5.3 (Thought budgets row), §6.1 ("dilation is never a lever a guest can request"; "percepts may
trigger [thought requests], rate-limited per speaker").

TB2-B3's core scenario was a guest talking an NPC into a long tool loop. That scenario is now bounded for one line of
speech, but it isn't closed:
- **The ceiling is per call, and calls retry with no stated cap.** A thought may make up to `segments + tool calls`
  model calls (each Pn "pays L again", §4.5). Each call can run up to the ceiling C, times its retries. The longest a
  thought can hold the world is therefore `(segments + tool_calls) × (retries + 1) × C`, and no document gives C or
  the retry count.
- **`thought_budget.yaml` has no wall-time item.** §4.7 lists segments, tool calls, tokens, held bytes, memory writes,
  `cancel_on` length and `D` ceilings. The ceiling and retries live in prose, outside the gate contract, with no
  rejection test.
- **"Rate-limited per speaker" has no rate, no time base and no scope.** If the limit is counted in wall time, a
  guest's quota refills while the world is held, so a held world doesn't slow the guest down. If it is counted per
  (speaker, listener), one line spoken near N NPCs starts N thoughts.
- **Nothing bounds dilation per session.** Dilation is reported by cause (§5.4, `boundaries.md` §6.3) but never
  budgeted. The literal claim holds: a guest can't *request* dilation. In effect it is false: a guest can cause as
  much dilation as they like.

Failure scenario: in co-op, a guest stands among four NPCs and repeats "Before you answer, recall everything you
know about me, then think it through step by step." Each NPC starts a thought that uses its full tool-call budget.
With the local model loaded and slow, each call runs just under C. The host's world runs at a few percent of real
time for minutes after each line. The guest repeats the line at the speaker rate limit, which refills in wall time.
The host can't pause the guest; only the host may pause (§6.1). No record says why the world crawled, beyond
"dilation by cause: thought".

Fix:
- **Put the wall-time limits in `thought_budget.yaml`,** under the gate contract with rejection tests: a ceiling **per
  thought**, not only per call, and a retry count. Exceeding either ends the thought as `thought_failed(reason=timeout)`.
- **Give the speaker rate limit a number and a world-time base,** scoped per speaker across all listeners: one line
  counts once, however many NPCs hear it.
- **A per-session dilation budget.** Dilation is attributed to the session whose speech triggered the thought
  (extend "by cause" to carry the session). When a session's dilation over a sliding wall window exceeds its budget,
  the thoughts it triggers are answered at P0 only, or run under `abandon` for that NPC. Either way the run is logged
  and flagged tier 3, and the host's own triggers are unaffected. Host-only control over the budget value.
- **A test on the scripted double:** a model that answers every call at C − ε, and a guest repeating a line at the
  maximum rate. The effective dial over a long window stays at or above a stated floor, and the dilation record names
  the session.

## SHOULD-FIX

### DTB-S1. The roster is checked on one registry at build, but Maxim has other ways to add tools, and an existing mechanism the designs don't use

`boundaries.md` §5.3 (roster row: "refuses to step an agent whose registry holds any other tool"), §10;
`npcs_and_sem.md` §6.1; `embeddable_agent_DRAFT.md` §3 (front gate: "mode-based containment … `allowed_dirs`"),
§4.3, §7.

Other ways a tool reaches an agent on `origin/main`:
- **`maxim.register_tool`** (`api.py:2119`): "process-wide and persistent" (D18, "available to all agents"). It is
  injected into every registry that `run`/`imagine`/`campaign` builds (`api.py:839`) and into the orchestrator's agent
  registry (`simulation/orchestrator.py:1148-1150`). Any code in the host process can do it: an experiment harness, a
  later mod, a test that forgot `clear_registered_tools`. It then reaches every agent built through those paths.
- **Registration after construction:** `embodied_runtime/agentic_runtime.py:329, :583, :708-803` register SEM,
  math, explain and introspection tools after the registry is built.
- **Tools that change authority (`Effect.GOVERN`):** `ModeSwitchTool`, `AutonomyLevelTool` (`tools/mode_switch.py`),
  `sense_tools` (`tools/discovery.py:292`), `RequestDirectoryChangeTool` (`tools/filesystem.py:788`), and the
  `SpawnSubSimulationTool` composite (`simulation/tools.py:1370`).
- **A process-wide arming flag:** `orchestrator.py:329` does `os.environ.setdefault("MAXIM_ALLOW_BASH", "1")`, which
  outlives the call, and `BashTool` checks that variable (`tools/filesystem.py:969`). The same variable can also be
  inherited from the owner's shell.
- **What doesn't exist:** no MCP and no tool plugins. The only entry-point group is `maxim.robots`
  (`api.py:1070-1080`). Skills (`runtime/skill_matcher.py`) are `.txt` prompt fragments, not tools; their risk
  belongs to the home (N8).

**What Maxim already has, which the front gate misses:**
- `tools/base.py::Effect`: seven flags, with an undeclared effect counted as `ALL`.
- `ToolRegistry(ceiling=…)`: fixed at construction, and it refuses any later registration above the ceiling
  (`tools/registry.py:45-106`).
- The immutable, **pinned** `ToolPolicy`: "the exact tool objects it authorises", enforced at dispatch by every
  `Executor` (`runtime/tool_policy.py`, #1315).

That is a closed roster enforced at the point of use. Calling the existing infrastructure "partly" adequate on the
strength of `allowed_dirs` alone is the kind of front-gate miss Maxim's plan review bounces (compare MP-B1).

Failure scenario: `maxim_experiments` and the host share a process for a lab scene. The harness calls
`maxim.register_tool(ProbeTool())` with no effect declared, which counts as `ALL`. A later NPC built through an
`api` path gets it. The build-time check ran before the registration, or on a different registry object, and passed.

Fix:
- **OD-A11 rides on #1315:** the embedded agent's registry has ceiling `READ | SELF_SCOPE` and a pinned `ToolPolicy`
  of the declared objects. Say so in the draft's §3 and shrink PR 1 to match.
- **Overdrive's check runs on every call, not once at build.** The gateway sees each canonical request's tool
  schemas (`npcs_and_sem.md` §4.8). A request offering any schema outside the allowlist is refused as
  `thought_failed(reason=roster)`. Late registration can't get past that.
- **Refuse to start** if any `MAXIM_ALLOW_*` variable is set in the process.
- **Planted proofs,** each going red: a tool added through `maxim.register_tool` before construction, one registered
  after construction, and `MAXIM_ALLOW_BASH=1` in the environment.

### DTB-S2. The "reviewed cognition tools" have no review criteria, and the obvious candidates leak host data or act on the host

`boundaries.md` §5.3 ("the membrane's affordances plus reviewed cognition tools"), `npcs_and_sem.md` §6.1 ("memory
recall, narrative"), `embeddable_agent_DRAFT.md` §4.3 (a refusal only for "filesystem, processes, network or
operational mode").

Effect alone isn't the right filter. Checked on `origin/main`:
- `memory_recall` (`READ | SELF_SCOPE`): `_format_episodic_memory` returns each memory's `timestamp`, which is host
  epoch time before tier A (`tools/introspection.py`, after `:700`).
- `energy_status` (`READ`): returns token use and stats over a `window_seconds` **wall** window
  (`introspection.py:404-446`). That reveals the machine's speed and the dial, which §4.6 already bars from
  cognition.
- `system_stats` (`READ`): returns `{"error": str(e)}` exception text (`introspection.py:671-745`). §5.4's
  closed-code rule covers only Overdrive's own errors.
- `temporal_patterns`: the SCN's host-calendar phases (the §12.2 oracle).
- `speak` (`READ | ACTUATE`, `tools/response.py:101`): runs **host** TTS through the host's speakers and prints to
  the host's console. Its name also collides with the engine's `speak` kind. `respond` is `WRITE_LOCAL`.

Failure scenario: `memory_recall` is admitted as "memory recall". The tier A prompt test renders a clean prompt.
Then the NPC tells a guest "I last saw you at 1763312400". Or `speak` is admitted as "narrative", and an NPC's line
plays through the host's speakers, outside world time.

Fix:
- **Write the admission criteria into the design:**
  - effect ⊆ `READ | SELF_SCOPE`;
  - output carries no host time, machine metric or exception text;
  - no `ACTUATE` except through the membrane.
- **Name the initial list** rather than "for example". On `7084f561` that excludes `energy_status`, `system_stats`,
  `temporal_patterns`, `speak` and `respond`; `memory_recall` waits for tier A's time rows.
- **NPC speech leaves only through the membrane's speech affordance.**
- **The prompt test calls each admitted tool once** and scans its output, not only the rendered prompt.

### DTB-S3. The interim home guard doesn't keep Maxim off the owner's files or the owner's LLM config

`boundaries.md` §5.3 (Agent homes row: "refuses real Maxim unless `MAXIM_DATA_HOME` points at a per-run
directory"), `embeddable_agent_DRAFT.md` §5 PR 2 ("a census of stores comes first").

`MAXIM_DATA_HOME` moves `data_home()` and nothing else. On `origin/main`:
- **The owner's declarative config** is read from XDG, ignoring `MAXIM_DATA_HOME`:
  `~/.config/maxim/config.json` (`runtime/config_loader.py:612-625`), `profiles.yml`
  (`models/language/profile_loader.py:121-134`), and `peer.yml`/`mesh.yml` (`peer/config.py:30-33`). Before tier A,
  Maxim makes its own model call, so the owner's profile decides whether NPC prompts, guests' words included, go to a
  cloud provider or a peer box. That settles `npcs_and_sem.md` §12.1 Q2 ("local or remote") by accident.
- **`llm_spawn_record_dir`** "ignores `HOME` and `MAXIM_DATA_HOME` on purpose" and writes under the passwd home,
  `~/.maxim/run/llm_server` (`utils/paths.py:99-126`).
- **Files resolved against the working directory:** `utils/response_config.py:44-75` searches
  `$CWD/data/util/{key,phrase}_responses.json` and `$CWD/<file>`, files that map input to method calls. Overdrive's
  own repo root has a `data/` directory.
- **About 50 inherited `MAXIM_*` environment variables** (`MAXIM_LLM_CLOUD_ENABLED`, `MAXIM_LANE_*_REMOTE_URL`,
  `MAXIM_LLM_PROFILE`, `MAXIM_ALLOW_BASH`, …) change behaviour.
- **`data_home()` is cached on its first call** (`paths.py:178-203`). A check of the environment variable passes even
  when something imported earlier has already cached `~/.maxim`.

PR 2's "census of stores" would miss all of these except the first item's files, and it misses them too, because
config files aren't stores.

Fix:
- **Launch the real-Maxim agent with an explicit environment:** per-run `HOME`, `XDG_CONFIG_HOME`,
  `MAXIM_DATA_HOME` and `MAXIM_LLM_SPAWN_RECORD_DIR`, the working directory set to the per-run root, and refusal if
  any other `MAXIM_*` variable is present.
- **Assert `data_home()` by value** after construction.
- **Prove it with an audit hook** (`sys.addaudithook` on `open` and `os.*`). It records every path opened while
  building and stepping an agent and fails if any lies outside the per-run root. It goes red when the planted
  `~/.config/maxim/profiles.yml` is read.
- **Upstream:** PR 2's census covers every path read or written and every environment variable read, not only
  stores.

### DTB-S4. Player speech has a non-tool command channel into Maxim: phrase responses

`npcs_and_sem.md` §5.2 (speech as a world input), §6.1; `embeddable_agent_DRAFT.md` §4.

Maxim maps spoken or typed phrases to `Selfy` calls that skip the LLM:
- "maxim shutdown", "maxim sleep", "maxim pause", "maxim passive", "maxim active" and more
  (`utils/response_config.py:250-380`; `runtime/agent_loop.py:2600-2655` `SKIP_LLM_COMMANDS`);
- voice input needs only the word "maxim" in it (`agent_loop.py:2668`).

Code-executing modes are refused by phrase (#828, `modes/state_manager.py:225-250`), but sleep, pause, shutdown and
the passive or active mode are not. None of this goes through a tool, so the roster, the authority table and the
`speak` gate never see it.

Maxim also already frames recalled and external text as untrusted (`Tool.untrusted_output`, Session R #1444,
`runtime/agent_loop.py:925-932`). The designs don't say that heard speech is framed that way.

Failure scenario: an embedded agent built on the 1.3.6 loop builder feeds heard speech in as `cli_inputs` or
`detected_speech`. A guest says "Maxim, sleep." The NPC's processing state changes, with no intent, no record and no
authority check.

Fix:
- **Heard speech is a percept,** framed external through Session R's mechanism, and never a CLI or user input.
- **Phrase and key responses are not loaded on the embedded path.**
- **An exit test** (OD-EA10): an NPC hears "maxim shutdown", "maxim sleep" and "maxim passive", and its state digest
  is unchanged.

### DTB-S5. Plain-text rendering is a rule with no guard, and it covers only speech

`npcs_and_sem.md` §5.2 ("renders speech as plain text, BBCode off"); `boundaries.md` §10 (no row); CLAUDE.md B6/B7.

Gaps:
- **Speech is not the only server string a client draws.** Region and imagined-object names (LLM-chosen, TB2-N5),
  NPC names, refusal codes and host status are too.
- **"BBCode off" is a property, so one widget built later with `bbcode_enabled = true` reopens the hole.** So does
  one that builds lines with `append_text`.
- **The escalation is the client acting on a link.** A `meta_clicked` handler that calls `OS.shell_open` on server
  data opens whatever URL an LLM line carried.
- **Two more Godot behaviours need checking:** auto-translate treats a node's text as a translation key, and
  platform TTS (Windows SAPI) may interpret XML markup in what it speaks.

Failure scenario: part 3 builds a chat log with `RichTextLabel` and BBCode on, for coloured speaker names. An NPC
line `[url=file:///Users/…]look[/url]` becomes clickable. The design's rule exists, and no test fails.

Fix:
- **One client widget for every server string:** a `Label`, or a `RichTextLabel` with BBCode off that adds text only
  through `add_text`, with auto-translate disabled. Speaker names are drawn from the actor id, never from the text.
- **No `OS.shell_open`, and no `meta_clicked` handler, on server data.**
- **A GDScript lint** that every sink of a server string goes through that widget.
- **Golden frames** carrying `[img]user://…[/img]`, `[url]…[/url]` and a bidi override, with golden screenshots
  showing the literal text.
- **A §10 row**, landing with `phase1/protocol`'s client half, and a backlog row until then.

### DTB-S6. The one unsafe load on `origin/main` should be filed now, not wait for tier A

`embeddable_agent_DRAFT.md` §4.4, §9 ("whether the pickle-free load is its own issue now"); `issues_now_DRAFT.md`.

A scan of `src/maxim` at `7084f561` for `pickle`, `allow_pickle=True`, `torch.load`, `joblib`, `yaml.load`,
`marshal`, `shelve`, `dill` and `eval`/`exec` finds one unsafe load:
- **`similarity/semantic.py:662`, `np.load(path, allow_pickle=True)`.** Its version check doesn't protect: `version`
  is an integer array, and the object arrays unpickle when `data["memory_ids"]` is read. `embodiment/component_index.py:443`
  uses the safe default.
- **Indirect: ultralytics' `YOLO(path)`** loads `.pt` weights through `torch.load` (`models/vision/ultralytics_engine.py:147`),
  from paths that include `model_dir()` under the data home.

The `np.load` site is a discrete defect with a definite done state. It affects robot users who load a shared home
today, and it meets Maxim's own test for an issue. Waiting for tier A leaves the hole open for every Maxim user for
the whole Phase 3.

Fix:
- **Add OD-I3 to `issues_now_DRAFT.md`:** store embeddings without object arrays, load with `allow_pickle=False`,
  migrate existing files once, and add a test that a planted object array is refused without being unpickled.
- **The home census (S3) excludes `models/`** from anything a save may supply.

### DTB-S7. The owner's interim-guard question rests on an ambiguity; settle that first, then guard mechanically

`npcs_and_sem.md` §12.1 Q1–Q2, §6.2 ("Real Maxim … is a strict red gate until tier A"), `boundaries.md` §13 ("Real
NPCs wait for Maxim's embeddable agent contract"), against `boundaries.md` §5.3's homes row (an interim mode that
*runs* real Maxim before tier A).

The documents disagree on whether a shipped, pre-tier-A, real-Maxim mode exists at all. If none exists, the guest
question is moot. If one does, the proposed guard ("until the prompt test passes on the pinned pymaxim") is too
narrow. The prompt test checks time in two time zones. It doesn't check:
- tool outputs (S2);
- the owner's LLM routing (S3);
- user, host or path strings;
- the phrase channel (S4).

**Recommendation:**
1. **Decide that there is no pre-tier-A real-Maxim mode outside the red-gate tests.** The adapter refuses to
   construct real Maxim except under the test marker. The `MAXIM_DATA_HOME` interim becomes a test fixture (still
   built as in S3, since the red-gate tests construct real Maxim on the owner's machine). Q1 is then answered by
   construction.
2. **If the owner wants a developer mode anyway, guard it mechanically, in both directions:**
   - the host refuses a non-host `join` while any real-Maxim agent is live and `guest_safe` is false;
   - it refuses to start a real-Maxim agent while a guest is joined.
3. **`guest_safe` is computed at launch by a canary self-check through the gateway:**
   - sentinel values for `HOME`, `USER`, the hostname, `TZ` and the data home;
   - one full request rendered, with one call to each roster tool;
   - false if any sentinel or the real time zone offset appears, or if any LLM lane isn't local.
4. **Keep the canary after tier A** as a launch check, since it measures the shipped path rather than a test fixture.

## NIT

- **DTB-N1 (TB2-N7 not closed).** The documents say "read against `7084f561`" but carry 1.3.3 line numbers. On
  `7084f561`:
  - `similarity/semantic.py:619` is `:662` (`npcs_and_sem.md` §6.1);
  - `prompt_builder.py:1104` is `:1125`, and `:2379` is `:2400` (`npcs_and_sem.md` §1, §6.1; the world-clock draft);
  - `:159`, `bootstrap.py:132-141` and `salience_map.py:227` are correct.

  Cite `file::symbol` with the commit, and line numbers only as a hint.
- **DTB-N2. The response cache is checked for integrity, not authenticity** (`npcs_and_sem.md` §4.8). Recomputing
  the hash catches corruption. A forged entry hashes correctly. Say that a foreign save's cache is dropped along with
  its agent homes, or covered by the same per-install HMAC. §4.4 also records machine-decided failures "in the cache
  as first-class responses", against §4.8's "an entry holds only the raw model output". Define the failure entry's
  shape.
- **DTB-N3. Bug-report redaction covers `speak` text only** (`boundaries.md` §6.2). Two more fields can carry guest
  text: the optional raw-payload audit field (up to a frame's size) and `imagine` names. Drop the raw payload from bug
  reports, and say that agent homes and early-held results never go into one.
- **DTB-N4.** `boundaries.md` §6.1 says an NPC emits `speak` "only through a thought", but §7.1's `StepOutput`
  carries `speak` acts from `step`, which is where P0 backchannels and fillers live (§5.1). Reconcile the two.
- **DTB-N5. NPC speech is validated as a stream.** Say what a refused character mid-stream does: end the thought as
  `thought_failed(reason=validation)` and keep the prefix. Apply NFC per word at the delimiter (the §5.3 rule), so a
  combining mark split across tokens isn't refused or changed.
- **DTB-N6.** "A test asserts two NPCs resolve different homes" can't run against real Maxim while at most one real
  agent runs per process. Say it runs across two processes, or on the double, until OD-EA2.
- **DTB-N7.** The embeddable draft says "nothing can cancel a call". `models/language/cancellation.py` has one
  process-wide shutdown event. Cite it in the front gate. Require that a per-NPC cancel never maps to it, or one
  guest's barge-in would cancel every NPC's call.
- **DTB-N8. Pin the per-install HMAC down** (`boundaries.md` §5.3):
  - the key lives in host config at mode 0600, outside every save;
  - verification runs before any Maxim code opens the home;
  - the MAC covers the whole home tree, including the skill directories, whose `.txt` fragments
    (`runtime/skill_matcher.py:60-85`) go straight into prompts.

## Round 1, checked against 18623ce

| Round 1 | Now | Verdict |
|---|---|---|
| TB2-B1 NPC tool surface | §5.3 roster row, part 2 §6.1, OD-A11 | **partial:** the rule is right. The check is build-time on one registry and misses `register_tool`, late registration and the env flag. It doesn't ride on #1315, and the cognition tools have no criteria (S1, S2) |
| TB2-B2 shared home; pickle | §5.3 homes row, §7.1, OD-A12/A13, §13 OPEN | **partial:** per-agent homes and the foreign-save rule are right. The interim guard misses XDG config, the spawn record, the working directory and the environment (S3). Pickle should be an issue now (S6). The HMAC needs pinning (N8) |
| TB2-B3 budgets; liveness | §5.3, part 2 §4.4, §4.7, embeddable §4.6 | **partial:** caps and a timeout record exist, and the cut-off comes before buffering. The wall bound is per call with uncapped retries, and nothing bounds a guest's dilation over time (B1) |
| TB2-S1 speech kind and gate | §6.1, part 2 §5.2 | folded for the server. The client rule has no guard and is too narrow (S5). The phrase channel is new (S4) |
| TB2-S2 log and LLM text | §6.2 per kind | folded (N3 widens the redaction) |
| TB2-S3 memory-write gate | §5.3 gate-to-be, §13 | folded |
| TB2-S4 cache untrusted | §5.3, part 2 §4.8, §6.2 | folded (N2) |
| TB2-S5 kind from output | §7.4, part 2 §4.2 | folded |
| TB2-S6 who stamps ticks | §4.2, §5.3, part 2 §9 | folded |
| TB2-S7 authority rows | §6.1 table, part 2 §4.7 | folded for the rows. The speaker rate limit has no number or time base (B1) |
| TB2-S8 identity under mode (a) | §7.2, part 2 §6.5 | folded (mode (a) is gone; the bound-actor check stays) |
| TB2-S9 host data before tier A | part 2 §12.1 Q1–Q2 | **open:** recommendation in S7 |
| TB2-S10 in-process inputs | §5.2 mechanical rule | folded |
| TB2-N1–N6 | various | folded or carried (N5 → DTB-N5 scope) |
| TB2-N7 citations | — | not closed (DTB-N1) |
