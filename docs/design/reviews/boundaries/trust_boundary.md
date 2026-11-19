# Trust boundary lens: boundaries.md (draft, at 47add00)

Reader: Trust boundary. Date: 2026-11-16. **Counts: 3 BLOCKER, 8 SHOULD-FIX, 4 NIT.**

Inputs: CLAUDE.md ("The client is untrusted input", the imagination rule, "Every format is versioned"),
`docs/code_review.md` (Trust boundary lens, Design reviews), the design (B-4, B-5, B-9, B-11 in focus), and the
accepted designs it sits on: `realtime_lanes_coop.md` §4 and §5 (lanes, thought results, tokens, `TimeAuthority`) and
`world_model.md` §8 (F14, "saves, scene files and replay logs are untrusted input"). Checked against code in
`.worktrees/act-validation` at 2f200b5: `checks.py`, `config.py` (`RigProfile`, `Material`, `MaterialTable`,
`ActionLimits`, `_StrictLoader`), `world/scene.py` (`Box`, `Cylinder`, `Scene`, `Scene.from_dict`), `world/grid.py`
(`Region`, `MaterialGrid`), `world/world.py` (`World`, `HeatSource`, `snapshot`), `imagination/spec.py` (`Budget`,
`_read`, `place`), `sem_env/bridge.py` (`parse_action`, `StructureModulator.execute/apply/_is_this_region`, `_shown`),
`sem_env/_compat.py`, `data/world/actions.yaml`, `pyproject.toml` (licence, wheel `force-include`).

Probes run against that code (worktree `src/` on `PYTHONPATH`), results quoted below:

- `Scene.from_dict({})` raises `KeyError 'extent_m'`; `{"extent_m": 5}` raises `TypeError`; a box with no `min_m`
  raises `KeyError`.
- `json.loads('{"a":NaN,"b":1e400,"a":2}')` returns `{'a': 2, 'b': inf}`; `json.loads('NaN')` returns `nan`.
- `Budget(max_mass_kg=float("nan"))` and `RigProfile("x", 0.2, 1.5, -3.0)` both construct without complaint.
- On a frozen `Region`, `region.cells[:] = True` succeeds: the crate's mask grew to every cell of the grid (1000 cells).
- `spec.place` accepted an object whose name is 100,000 characters long. A spec whose material is a 1 MB string was
  refused with a message 1,000,037 characters long.

## BLOCKER

### TB-B1. B-4's lint rule cannot detect a new ungated door, so "there are no other doors" is not checkable

`boundaries.md::B-4` (Enforcement row: "every public function taking a `Mapping` or `object` parameter is a listed
gate or its private helper").

The rule keys on parameter annotations. Untrusted data doesn't have to arrive in a parameter annotated `Mapping` or
`object`, and annotations are not enforced at run time. Each of these is a new door the rule passes:

- `def on_frame(text: str)` that calls `json.loads(text)` and builds a `HeatSource` from the result. The untrusted
  value arrives as `str` or `bytes` and becomes a mapping inside the function. That is how every protocol decoder,
  save loader and log reader will look.
- `def on_intent(msg: dict[str, Any])`. A `dict` is not a `Mapping` annotation. `StructureModulator.execute` itself
  takes `params: dict[str, Any]` today, so the one door Maxim actually calls would slip past a literal reading of
  the rule.
- `Any`, `list[Any]`, `Sequence[SupportsFloat]` (`spec.place`'s `origin_m`), `SupportsFloat`, or a bare `float`
  annotation that receives a string at run time. `Strike(energy_j: float)` exists to refuse exactly that case
  (`bridge._typed`), which shows the code already knows annotations prove nothing.
- Code that reads `os.environ`, `sys.argv`, `Path.read_text`, `np.load` or a socket and takes no parameter at all.

The rule also fires on things that aren't doors: `checks.finite_real(value: object)`, `whole_number`,
`finite_vector`, `MaterialTable.__contains__(name: object)`, and every `__eq__`. The usual fix is to list them as
"gates" until the list means nothing. "Its private helper" is undefined: by underscore? By call graph?

Failure scenario: the protocol PR adds `server/codec.py::decode(frame: bytes)` that calls `json.loads` and passes
`msg["params"]` to a new `ignite_at(point, power)` helper that builds a `HeatSource` directly, skipping
`parse_action` and so `ActionLimits`. The lint is green. A 5 GW fire passes, because `HeatSource.__post_init__`
checks only physical validity, by design. That is a guard that cannot fail on the case it exists for (charter:
BLOCKER).

Fix:
- Guard the sources, not the signatures. Allowlist the modules that may call input primitives (`yaml.*load*`,
  `json.load(s)`, `Path.read_text/read_bytes`, `open`, `np.load`, `os.environ`/`os.getenv`, `sys.argv`, the
  `websockets` receive calls). Every allowlisted module is a gate module.
- Forbid outright `pickle`, `marshal`, `yaml.load` without a `SafeLoader` subclass, `np.load(allow_pickle=True)`,
  `eval` and `exec`.
- Guard the sinks with B-9 and B-10 (below): where cells and `World.sources` may be written.
- Keep a gate registry: each gate is a named function with a test module that covers every rejection branch. The
  trust charter already asks for 100% branch coverage at trust boundaries, so measure it per gate module.
- Prove the lint as the charter requires: plant a `json.loads` in a non-gate module and watch the gate go red.

### TB-B2. "Inside the gate, only typed frozen objects" is false today, and the design states it as if it held

`boundaries.md::B-4` ("Inside a gate, code takes typed, frozen objects, never raw mappings"), against
`world/grid.py::Region`, `config.py::MaterialTable`, `config.py::RigProfile`, `config.py::Material`,
`imagination/spec.py::Budget`, and `sem_env/_compat.py::ModulatorResult`/`SensorReading`.

Two separate claims hide in the rule, and neither holds.

**Frozen is shallow.**
- `Region` is `frozen=True`, but its `cells` is a writable numpy mask. The probe rewrote the crate's mask to cover
  the whole grid through the "frozen" object. After that, `region_integrity`, `RegionSensor` and the strike reach
  all read a crate that fills the room.
- `MaterialTable` is not a dataclass at all. It exposes `by_name`, `by_id`, `rho_cp`, `conductivity`, `fracture`,
  `degrade_above` and `degrade_rate` as public mutable objects. `mt.rho_cp[:] = 0` succeeds and every heat step then
  divides by zero.
- Maxim's own `ModulatorResult` (`params`, `metadata`) and `SensorReading` (`extra`) are frozen dataclasses holding
  plain `dict`s. They are Maxim's frozen types, which CLAUDE.md forbids changing here, so the rule needs a named
  exception for them, or a Phase 3 pushback item.

**Typed is not validated.** A typed object is proof of validation only when the type's constructor validates.
- `ActionLimits`, `Box`, `Cylinder`, `Scene`, `HeatSource`, `Strike` and `Ignite` validate in `__post_init__`, so
  every path to them is a gate.
- `RigProfile` validates partly: the probe built `min_substeps_per_turn=1.5` and `full_res_radius_m=-3.0`. The
  coercion lives only in `RigProfile.load`.
- `Material` has no `__post_init__`, so `density_kg_m3=0` makes `diffusivity_m2_s` raise `ZeroDivisionError`.
- `Budget` has none either. `Budget(max_mass_kg=nan)` makes `mass > budget.max_mass_kg` always false, so the
  imagination mass limit disappears without anything going red. Budgets become per-actor or data-driven soon
  (Q3, B-9), and from then on they are not trusted code.

Failure scenario: a later phase loads per-NPC imagination budgets from a roster file with a typo that yields `.nan`.
Every LLM-imagined object then has unlimited mass, with no error.

Fix:
- Restate the rule as **validation lives in the type's constructor**. A gate is then only the decoder that turns
  bytes into constructor calls, and holding an instance is proof it is valid.
- Define frozen as deep: tuples, `frozenset`, `MappingProxyType`, and numpy arrays with `writeable=False` (this is
  B-10's mechanism, so tie the two together).
- List what violates the rule today and when each is fixed: `Region.cells`, `MaterialTable`, `RigProfile`,
  `Material` and `Budget`.
- List the Maxim-type exception explicitly.
- `World` and `MaterialGrid` are the mutable state, which is correct, but the rule must say they are the sink, not
  "inside the gate".

### TB-B3. B-9's "one door, same limits" has no notion of authority or identity, and contradicts the accepted lanes design

`boundaries.md::B-9`, against `realtime_lanes_coop.md` §4.3 and §5 (`TimeAuthority`, `HostOnly`, roles bound to
tokens, "actor ids are integers from the simulation lane's allocator"), and `config.py::ActionLimits` (its own
docstring: "an NPC's capability will come from its body and its energy").

"Players and NPCs act through the same intent gate" is right for validation and wrong as stated for authority.

- **Records that aren't actor actions.** The inbox carries intents, controls (dial, pause, presets), joins and
  leaves, thought results, and memory writes. If "one door" means one vocabulary open to every actor, an LLM that
  emits `{"type": "pause"}` or `{"type": "set_scale", "value": 100}` reaches the time controls. The design never
  says that controls are host-only and that NPCs can never emit them.
- **Identity.** The design doesn't say where an intent's actor comes from. It has to be stamped by the host from the
  channel: the session's token for a client, the thinking lane's request id `(tick, actor, n)` for an NPC. It must
  never be read from the payload. Failure scenario: a guest client sends `{"actor": 0, ...}` and acts as the host,
  or as an NPC whose actions the log then attributes to Maxim.
- **Limits.** "What an NPC can do, a player can do, and the reverse" ties two policies together that the roadmap
  separates. `ActionLimits` are shared physics-safety ceilings. Capability is per body (Phase 4 and 5). Imagination
  budgets will differ by actor. And the reverse direction has to fail: players have UI-only verbs (save, rig,
  dial), and NPCs have memory writes and speech that players don't.
- **Memory writes.** B-9's guard is "every cell write happens under `World.advance` or intent application". A
  memory write is LLM output that changes agent state, not cells, so the guard never sees it. Lanes §4.3 says memory
  writes pass "the same validators as client intents", but no current validator applies to a memory write.

Fix: split B-9 into three rules.
1. **One pipeline.** Every record from any source goes decode, stage-1 validation (`parse_action` and its
   siblings), log, then stage-2 validation against the world at apply.
2. **Authority per record kind,** decided from an actor role that the host stamps. For example: `intent` for any
   actor; `control` for host sessions only, via `TimeAuthority`; `memory_write` for an NPC's own memory only;
   `imagine` subject to the actor's budget.
3. **Limits are the shared ceiling intersected with the actor's capability.**

Cite lanes §5 and §4.3 instead of restating a weaker version.

## SHOULD-FIX

### TB-S1. The gate list is incomplete, and conflates validation, authentication and authorization

`boundaries.md::B-4` ("The gates"). Today's list is four loaders plus `parse_action` and `place`. "Later" adds
the protocol decoder and the save, scene-v1 and intent-log loaders. Missing:

| Input | Where it comes from | Gate it needs | Status in the design |
|---|---|---|---|
| Handshake, per-launch token, `Origin` | network lane | authentication: `hmac.compare_digest`, `Origin` refused, loopback bind (lanes §5) | absent from B-4 |
| Controls: dial, pause, presets | host session | authorization: `TimeAuthority` | absent |
| Thought results: intents and **memory writes** | thinking lane (LLM via Maxim) | the stage-1 validator plus a memory-write validator | absent |
| `target=<Entity>` and other Maxim objects in a call | Maxim's `OrchestratorActorTool` | `StructureModulator._is_this_region`/`_is_namesake` | not named. `execute` is the door Maxim calls, and `parse_action` sits inside it |
| Joins and leaves | network lane | session to actor id allocation | absent |
| Token delivery | environment variable or a 0600 file (lanes §5) | a host config reader; never echoed or logged | absent. B-3 forbids `os` and `secrets` in the core only, so say that the host owns both |
| Rig CLI flag | `RigProfile.load(name_or_path)` | a name from a closed set | the loader joins `data/rigs/<name>.yaml` for any suffix-less string, and reads any path with a suffix. Fine for a local CLI, but list it as an operator-surface gate |
| `MAXIM_OVERDRIVE_*` env vars | process environment | a config reader | the charter lists them as Gate contracts. B-4 doesn't |
| `data/sem/vocabulary.yaml`, `data/server/` presets, NPC rosters, cradle arcs, content files | data, later mods | a loader each | absent |
| Snapshot frames, as received by the client | server | a client-side decoder (defence in depth; the client must not crash on a bad frame) | absent. B-11 implies it |
| Imported bug-report logs and saves | **strangers' machines** | the strictest gate: no pickle, budget before allocation, all-or-nothing | covered by `world_model.md` F14. B-4 doesn't cite it |

Failure scenario: the thinking-lane PR adds `apply_memory_writes(result)`. It isn't on the B-4 list and isn't
caught by the lint (TB-B1). An LLM's memory write goes into Maxim state with no validation, and on replay it
re-injects the same text.

Fix: make B-4's list this table, with three columns for authentication, authorization and validation. Cite F14 and
lanes §5 for the rules already decided. Name both validation stages (world_v2 §7's "two-stage validation"):
`parse_action` is stage 1, and `StructureModulator.apply`'s world checks are stage 2.

### TB-S2. The listed gates are not equally strong; the list implies they are

`config.py::RigProfile.load`, `config.py::MaterialTable.load`, `world/scene.py::Scene.from_dict`, compared with
`config.py::ActionLimits.load`.

`ActionLimits.load` is the bar: `_StrictLoader` (refuses repeated keys), a version check, a closed key set, and
`ValueError` only. The other loaders fall short of it:

- `RigProfile.load` and `MaterialTable.load` use plain `yaml.safe_load`, so a repeated key silently keeps its last
  value. Neither format has a version, against CLAUDE.md's "Every format is versioned... readers refuse versions
  they don't know".
- Unknown keys are ignored. A material typo, `degrade_rate_per_s_per_100C`, falls through `v.get(..., 0.0)` and
  silently turns off wood's degradation.
- A non-mapping file raises `TypeError` or `KeyError`.
- `MaterialTable` has no physical sign checks. `density_kg_m3: 0` or a negative `conductivity_w_mk` is accepted;
  the first divides by zero in heat, and the second runs diffusion backwards and blows up.
- `Scene.from_dict`'s docstring promises "any malformed shape is a ValueError", but `{}` gives `KeyError`, and
  `{"extent_m": 5}` gives `TypeError` (probed). `spec._read` catches all three, which hides the gap for
  imagination. The scene-v1 loader (a listed gate, and untrusted under F14) will inherit it.

Failure scenario: a shared scene file with no `extent_m` reaches the server's scene-load path. A `KeyError`
escapes, where the gate contract promised `ValueError` with a reason. Under the lanes design, an exception in the
simulation lane is a crash of the whole host.

Fix: write a **gate contract** that every listed gate must meet, and test it per gate:
- one strict loader;
- a version field;
- a closed key set;
- one exception type;
- bounded echo;
- budgets (TB-S3).

### TB-S3. Gates check type and finiteness, not cost or size

`imagination/spec.py::place`, `imagination/spec.py::_read`, `world/scene.py::_check_labels`,
`world/scene.py::MAX_EXTENT_M`.

- `place` has no limit on primitive count, and `np.stack(masks)` allocates `n_prims × cells` bytes before any
  rejection. At the max profile's roughly 5×10⁶ cells, 1,000 one-centimetre primitives (each within the 3 m and
  500 kg budget) cost about 5 GB. This is LLM output, the one place the code assumes the input is adversarially
  shaped.
- Name length is unbounded: a 100,000-character name was accepted (probed). It becomes a region, an Entity name and
  part of every NPC prompt that lists the room.
- Echo is not bounded at this gate. A 1 MB material string came back as a 1,000,037-character `SpecRejected`.
  `bridge._shown` exists for exactly this, but spec and scene don't use it: two gates, two policies.
- `MAX_EXTENT_M = 1000` at 0.05 m is 8×10¹² cells. F14 says "memory budget checked before anything is allocated".
  B-4 doesn't carry that rule.

Fix: put budgets in the gate contract (counts, string lengths, nesting depth, total allocation, all checked before
allocating). Move `_shown` into `checks.py` as the one bounded-echo helper for every gate.

### TB-S4. B-11's schema gives one source of truth for shape, not for validation, and the design doesn't say so

`boundaries.md::B-11`, against `bridge.py::parse_action`, `config.py::ActionLimits`, and backlog B3.

- **Limits.** The limits (`max_energy_j`, `min_sigma_m`) live in `data/world/actions.yaml`, as world config the
  replay needs. If the schema embeds them, there are two sources of truth. If it doesn't, the schema is shape only.
  Either way, stage 1 (`parse_action`) stays the only server validator, and the client's schema check is advisory,
  because the client is untrusted. "Checked against it on both sides" must not read as "validated on both sides".
- **JSON traps the schema won't catch.** Python's `json.loads` accepts `NaN` and `Infinity`, turns `1e400` into
  `inf`, and keeps the last of a repeated key (probed: `{"a":NaN,"a":2}` gives `2`). That is the same repeated-key
  hole `_StrictLoader` closed for YAML. Common Python JSON-Schema validators accept `float("nan")` as a `number`.
- **Godot's JSON** parses every number as a 64-bit float, so integer fields arrive as `3.0`, and ids or counters
  above 2⁵³ lose precision.

Failure scenario: a decoder generated from the schema hands `{"energy_j": 1e400}` on as a valid `number`. Only
`finite_real` deep inside `parse_action` stops it. If a future intent kind bypasses `parse_action` "because the
schema already checked it", `inf` reaches the physics.

Fix:
- State that the schema is shape plus closed vocabulary.
- Put a strict decoder in front of it: `parse_constant` raises, `object_pairs_hook` refuses repeated keys, and
  `max_size` applies before decoding.
- Keep semantic validation in the stage-1 validators, referencing limits by name from `data/`. Send the limits to
  the client in the handshake for its UI only.
- Pin integers to at most 2⁵³ in the schema.
- Add golden rejection frames (`NaN`, `1e400`, a repeated key, an oversized frame, an unknown field) beside the
  valid ones, decoded by both sides.

### TB-S5. B-9's "`execute` becomes a producer of intents" breaks today's target check, which depends on object identity

`sem_env/bridge.py::StructureModulator._is_this_region` (`target.modulators.get("structure") is self`),
`_is_namesake`, `execute`.

The target check works by identity on a live Maxim `Entity`. An intent that goes into a log, across a lane, or into
a save can't carry a live object. A replayed log has no `Entity` to compare with `is`. The namesake protection (an
NPC called "crate" against the crate region) then has nothing left to stand on.

Failure scenario: the sim-clock PR serializes the target as `target.name`. The namesake check silently degrades to
a string compare, and a strike Maxim aimed at an NPC called "crate" lands on the crate region.

Fix: B-9 must specify an intent's target encoding, a stable region or actor id that the simulation allocates (lanes
§4.2), and move the namesake check to where Maxim's `Entity` is converted to that id, in the thinking lane, before
the intent is frozen.

### TB-S6. Imagination is a second door to the cells that B-9 doesn't route through intents

`imagination/spec.py::place` (writes `grid.paint` and `grid.name_region` directly), `boundaries.md::B-9`.

B-9 names `StructureModulator.apply` as the direct cell-writer to fix. `place` is the other one, and it is called
with LLM output (ImaginationDesigner). If it isn't an intent kind, imagined objects never enter the log, a replay
can't reproduce them, and B-9's guard test ("every cell write under advance or intent application") has to exempt
it.

Fix: `imagine` is an intent kind, carrying the spec and origin as data and the actor's budget (TB-B3). `place` is
its stage-2 apply.

### TB-S7. B-9's guard ("a test that every cell write happens under `World.advance` or intent application") can only see the paths a test exercises

`boundaries.md` Enforcement row B-9. `MaterialGrid.paint`, `MaterialGrid.material/integrity/temperature` and
`World.sources` are public and writable from anywhere. A test only proves the paths it runs. A new module that writes
`world.sources["x"] = HeatSource(...)` from a network handler is invisible to it.

Fix: make the restriction structural.
- Keep the cell arrays `writeable=False` outside an apply/advance context the simulation owns (B-10's mechanism,
  inverted).
- Make `sources` a read-only mapping with a method that only intent application calls.
- Add an `import-linter` rule that only the simulation and apply modules may import the mutators.

### TB-S8. B-5: an Apache-2.0 wheel would carry rights-reserved content, and the material split needs a closed key set per file

`pyproject.toml` (`license = "Apache-2.0"`; `[tool.hatch.build.targets.wheel.force-include] "data" =
"maxim_overdrive/_data"`), `boundaries.md::Migration` ("builds both packages from the one distribution"),
`boundaries.md::B-5`.

- **The wheel's licence.** With one distribution, `content/` either ships in a wheel whose metadata says Apache-2.0
  (a licence misstatement on rights-reserved work), or it doesn't ship and the game package can't load its content.
  The design picks neither.
- **The material merge.** Splitting the material table into engine data and content makes the loader merge two
  files. Unless each file has a closed key set, a content file (later, a mod) can set `density_kg_m3` for steel, and
  "physics is engine" is gone. That is also a trust question, because content becomes the first user-editable data
  that feeds physics.

Fix:
- Either exclude `content/` from the engine wheel, or build a second distribution with its own licence file. Add a
  check that lists the wheel's files against B8's manifest.
- In material table v1, give the engine file and the content file disjoint, closed key sets, and refuse an
  override.

## NIT

- **TB-N1.** `boundaries.md::B-4`: "Inside a gate" reads as the gate's own body. "Past a gate" or "downstream of a
  gate" says what's meant.
- **TB-N2.** `checks.py` module docstring: "`tests/test_validation.py` and `tests/test_act_validation.py` hold every
  loader to it". `RigProfile.load` and `MaterialTable.load` don't meet the bar (TB-S2), so either the claim or the
  loaders should change.
- **TB-N3.** `boundaries.md::B-4`: constructors that validate (`Box`, `Strike`, `HeatSource`) are gates too, under
  TB-B2's restated rule. The list should name the concept rather than only free functions.
- **TB-N4.** `boundaries.md::B-9`, "Why": "fairness: what an NPC can do, a player can do" is a game-design goal, not
  a trust property. Keeping it under the trust rule's rationale invites the coupling TB-B3 objects to.
