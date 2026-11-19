# Wire integrity and Trust boundary review: world v2 (design draft, d596418)

Lenses: Wire integrity and Trust boundary (`docs/code_review.md`). Design: `docs/design/world_v2.md` at d596418,
building on v1 (`realtime_lanes_coop.md` §5, §7) and the research it cites (`research/states_of_matter/architecture.md`
§1.4, §1.5, §2, which holds the illustrative header, registry and material-table shapes the PRs will copy). Code
read for "before": `.worktrees/act-validation` at 02cd9e3 (`config.py`, `checks.py`, `world/scene.py`,
`world/world.py::snapshot`, `sem_env/bridge.py`, `data/`). Maxim read for N6: `embodiment/audio_localization.py::
world_set_axis`, `embodiment/backends/minecraft.py`.

No code exists for any v2 contract, so "after" is what the design (and the research it adopts) says.
Counts: **4 BLOCKER, 13 SHOULD-FIX, 4 NIT.**

## Contract tables

### Wire format: frames, welcome, act

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| Frame header (self-describing) | `world.py::snapshot` dict with fixed keys (`shape`, `cell_size_m`, `time_s`, four arrays) → codec over the registry: `format`, `version`, `kind`, `protocol`, `tick`, `world_time_us`, `registry {version, sha256}`, `materials {version, sha256}`, `grids{}`, `channels[]`, `tables[]` | `tests/test_snapshot.py` (asserts the fixed keys) → Python decoder (fixtures, save loader), GDScript decoder, `websocat` users | fixed keys → per-channel descriptors. **Missing from the design:** a rule for a *known* channel name whose meaning changed (F1), a rule for a known channel that is *absent* (F2), unknown *tables* and *grids* (F3), table layout (F4), which of `format.version` / `protocol` the reader checks (N1) |
| Channel descriptor `{name, grid, dtype, units, encoding, required, offset, stored_size, size, compression}` | registry `snapshot:` entries | both decoders | a closed dtype and encoding vocabulary is stated; `units` has no vocabulary and isn't part of a channel's identity (F1); `linear` scale is read from the header, but nothing proves a decoder doesn't hard-code it (F2 test) |
| `required` flag | writer, from `fields.yaml` | old readers | refuse unknown-required, ignore unknown-optional. Sound for the client. **Wrong for the save loader** if the same grammar rule is applied (F5) |
| Table `{name, rows, key, columns[{name, dtype, units}], offset, sizes}` | zones (PR 6/7), pools (Phase 2) | both decoders | row/column-major order, key-column presence, row order, string columns (the research's zone table has `name: str`) are unspecified (F4) |
| Grid `{shape, axis_order, frame, cell_size_m, origin_m}` | `cells` now; `topo` (fixed 0.2 m) reserved | both decoders | v1's asymmetric fixture carries over; "unknown grid kind bumps protocol" is in the research but not in design §8 (F3) |
| `zone` channel dtype | — → `u8`, or `u16` "if over 255 zones per tile" (research §1.2) | both decoders, SEM zone entities | a channel whose dtype depends on the scene; no zone cap (F9) |
| `welcome` | v1: session, actor, role, world config, rig, dx, shape, regions with affordances, material table, time state → plus channel catalogue, zone list (id, name, kind, footprint), material table v1 | client | catalogue and frame descriptors can disagree with no stated precedence (F6); region list still static although imagination adds regions and v2's region ids are an id array (F10); zone and region names share the `act.region` field (F11) |
| `act` `extinguish` | client / NPC → `parse_action` (`_ALLOWED_PARAMS["extinguish"] = {}`) → `StructureModulator.apply` (`sources.pop`) | `act_result` readers, NPC learning, intent log replay | before: no params, refuses "nothing is burning"; after: water mass per m² per s, an energy and O₂ sink. New params, new caps, new success semantics; §7 N3 lists `douse` for the same thing (F7) |

### Persisted state and loaders

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| Material table | `data/materials/core.yaml`, no version, open keys → material table v1: version, closed keys, solids / liquids / ordered species / reactions | `config.py::MaterialTable.load` (`yaml.safe_load`, `v["id"]` → bare `KeyError`, extra keys ignored, repeated keys keep the last value) → v1 loader, `welcome`, the log header hash, the save (embedded) | today's loader has none of the v1 refusals; species order is "index = position", which a save or log replays against (F8) |
| `data/world/fields.yaml` | none → hand-written YAML | none → registry loader, codec, save, digest, memory check, lints | `default_for_older_saves` is shown in the research as an expression (`material.fuel_kg_m3 * integrity`), with no grammar (F12) |
| Scene format | `Scene.from_dict` over a dict; no version; unknown keys ignored; `p["min_m"]` → `KeyError`; no primitive cap; `MAX_EXTENT_M = 1000` → scene v1 with zones, gaps (vents, doors) | today only `imagination.spec.place` calls `from_dict` (it catches KeyError) → a scene-file loader, the save (embedded), the log header | first real file loader; zone / vent / gap rejection rules unstated (F13); allocation can precede the memory check (F14) |
| Save v0 | none → same grammar, `kind: "save"`, lossless, embeds registry, material table, scene, placed specs, RNG state, checkpointed records | none → save loader | embedded copies have no stated authority (F5); cell values unchecked (F14); derived-digest vs old fixtures (F15) |
| Intent log header | v1: format, protocol, code SHA, versions, hashes of scene, rig, material table, world config, roster, seed → plus registry and material table hashes | replay loader (TB-15) | missing: SEM vocabulary version, scene format version, a canonical hash form (F16) |
| `data/world/actions.yaml` (`ACTION_LIMITS_VERSION = 0`) | strict loader, closed keys → bumped for `extinguish` | `ActionLimits.load`, bridge, generated descriptions (N8), log header via world config | the bump is stated; that an old log is refused, not reinterpreted, isn't (F7) |
| `data/sem/vocabulary.yaml` (N7) | none → versioned vocabulary + golden tool-surface fixture | bridge, NPC memories (keyed by name), agent homes (Phase 4) | no meaning-change rule; no consumer that refuses a mismatched version (F1, F17) |

### Maxim-facing contracts

| Contract | Maxim reads | What v2 gives it |
|---|---|---|
| `world_set_axis(embodiment, name, value, owner="overdrive_world")` (N6) | returns `False` fail-soft when the body doesn't declare the sensor or has no `vital_metrics`; clamps to the declared `reading_schema["range"]` (a NaN becomes the range's upper bound, since `min(hi, nan)` is `hi`), writes the raw float when there's no range; `owner` is a self-declaration, not an ACL | immersion, wetness, skin temperature "after each advance". The design doesn't say the sensors are declared as world-owned (so modelled `self_effect` deltas also write them), that `False` is checked, which lane writes, or the units and ranges (F18) |
| SEM `integrity` sensor | `SensorReading.value`, learned against by name | becomes mean strength (§3.2): same name, new meaning (F1) |
| `ModulatorResult` for `extinguish` | `success`, `error` → NAc / cerebellum credit | was success iff a fire existed; becomes a physics action whose effect arrives later (P3) (F7) |

## Findings

**F1. BLOCKER: there is no rule for a contract whose name stays and whose meaning changes, and the design makes three
such changes itself.**
Location: design §8 ("Old readers"), §3.2, §2.1, §7 N7; `world.py::snapshot` (`crack`), `bridge.py::RegionSensor`
(`integrity`), `bridge.py::StructureModulator.apply` (`extinguish`).
The grammar's safety net is "unknown channel → refuse or ignore". It says nothing about a *known* name. The design
then changes three known names:
- `crack` is `1 - integrity` today, and integrity becomes "mechanical damage only" while strength follows the
  remaining mass (§3.2). A v0 Godot client keeps drawing `crack` from the same bytes, and a crate that has burned
  to 30% strength with no strike shows no cracks. The same holds for the SEM `integrity` sensor, which "becomes mean
  strength": an NPC's learned links on `integrity` now refer to a different quantity.
- Air cells' `temperature_c` becomes the zone's temperature (§2.1): the field keeps its name and dtype and changes
  from a per-cell to a per-zone value.
- `extinguish` keeps its name and changes from "delete the fire" to "a water sink" (F7).
N7 itself says "a rename orphans what an NPC learned", which is true, but keeping the name with a new meaning is
worse: the memory is kept and is wrong.
Fix: state one rule for every vocabulary (channels, table columns, SEM sensors, affordances, intent types): **a name
is an identity: its name, units, grid, container and meaning are fixed for the life of the format.** A meaning change
gets a new name (`strength` beside `integrity`, `douse` replacing `extinguish`), and the old name is either still
produced with its old meaning or retired, with readers refusing it as unknown. Put `units` in the channel's identity
and give units a closed vocabulary. The registry lint checks that no shipped name changes units, grid or encoding
kind against the committed fixtures.

**F2. SHOULD-FIX: a known channel that is missing, or a linear encoding a reader hard-codes, is silently misread.**
Location: design §8 ("Old readers refuse an unknown required channel and ignore unknown optional channels").
The rule covers channels the reader doesn't know. A reader that knows `glow` and gets a frame without it (the
registry dropped it, or marked it saved-only) either crashes on a missing key or draws zeros. v1 F6 had "refuses a
missing required array"; v2 drops it. Separately, `linear` scale and offset are self-described so they can change
without a bump, but a GDScript decoder that divides by 255 passes every fixture whose scale is 1/255.
Fix: each reader declares the channels it needs; a frame without one is refused, loudly. Add a golden fixture whose
linear channel uses a non-default scale and offset, and a fixture missing a channel the v0 reader needs.

**F3. SHOULD-FIX: unknown tables and unknown grids have no rule.**
Location: design §8; research §2.1 (which does say a new grid kind bumps the protocol).
Pools arrive in Phase 2 as a new table, and the `topo` grid is reserved. Design §8 lists channels and columns only.
An old reader meeting a `pools` table either crashes or, worse, treats it positionally. A channel on an unknown grid
can't be interpreted, even if optional.
Fix: an unknown table follows the channel rule (it carries its own `required`); a channel on an unknown grid name is
treated as unknown with its own `required`; a new grid *kind* (resolution rule) bumps the protocol. Add both to the
six fixtures, which become eight.

**F4. SHOULD-FIX: the table layout is unspecified, so two decoders can disagree on the same bytes.**
Location: design §8 ("tables with typed columns"); research §2.1 table example (`rows`, `key`, one `offset` and size
for the whole table), §1.3 (`name` str column).
Row-major or column-major? Is the `key` column one of the listed columns, or implicit row order? What dtype is a
string? With one offset per table, ignoring an unknown column in row-major order requires knowing every column's
itemsize, so an unknown column with an unknown dtype makes the table unreadable, not ignorable.
Fix: tables are column-major, each column contiguous with its own `offset` and size; `key` names a listed integer
column; rows are in key order; strings never appear in frames (names live in `welcome`'s zone list, joined by id).
Unknown dtype in a column is refused only if that column is required.

**F5. BLOCKER: the save shares the frame grammar, and the frame's "ignore unknown optional" rule silently loses state;
the embedded copies have no stated authority.**
Location: design §8 ("The save uses the same grammar, losslessly … embeds the registry, the material table, the
scene … and the placed imagined specs").
Two failure scenarios:
- A save written after PR 8 adds `progress` (marked `required: false` for the client, since a renderer can ignore
  it) is loaded by a build from before PR 8. The grammar says ignore it. The world loads with every cell's
  phase-change progress at zero, cells mid-melt restart, and no error is raised. The heavy-mode test can't catch it,
  because it runs one build.
- The save embeds the registry, material table and scene "in full". If the loader *uses* the embedded registry
  (dtypes, grids, which fields exist) to allocate and decode, a crafted save declares a field on a 10⁶-cube grid or
  a process with `every_ticks: 0`, and the server allocates or loops on it. If it ignores the embedded copies, they
  are documentation and the "readable without the repo" claim needs a separate reader.
Fix: state that **a save has no optional fields**: every field in it must be known to the loading build, matched by
name, units and dtype, or the load is refused; a save from a newer registry version is refused. The code's registry,
material table and scene loader are authoritative. Embedded copies are compared (by canonical hash, F16) and, where
they differ, refused or migrated through a named migration, never executed. The `required` flag is a client
concept and doesn't apply to saves.

**F6. SHOULD-FIX: `welcome`'s channel catalogue and each frame's descriptors can disagree, with no precedence.**
Location: design §8 (`welcome` adds the channel catalogue; frames are self-describing).
If the frame is authoritative, the catalogue is redundant. If the catalogue is, a frame can carry a channel the
client was never told about. A guest that joined before a registry hot-swap (or a server bug) gets frames whose
`registry.sha256` differs from `welcome`'s.
Fix: the frame's descriptors are authoritative for decoding; the catalogue is for building textures and UI up front.
A frame whose `registry.sha256` or `materials.sha256` differs from `welcome`'s is refused (the session must
reconnect). Test it with a fixture pair.

**F7. SHOULD-FIX: `extinguish`'s new meaning breaks its params, its success semantics and old logs, and the design
names it twice.**
Location: design §8 ("`extinguish` changes meaning"), §7 N3 (affordances "heat, cool, pour, ignite, vent, douse");
`bridge.py::_ALLOWED_PARAMS`, `bridge.py::StructureModulator.apply`; `data/world/actions.yaml`.
- Today `extinguish` takes no params and succeeds only if a source was popped. As a water sink it needs a mass rate
  (and a point or face, and a duration), each a new refusal path with caps in `actions.yaml`. Without a cap on water
  mass, one valid intent puts unbounded vapour into an isobaric zone, displacing its O₂ and blowing the zone's
  species ledger far outside the ranges the combustion kernel was benchmarked in.
- An old intent log with `extinguish {}` either fails to parse (missing required param) or defaults, and replays a
  different physical action. Bumping `ACTION_LIMITS_VERSION` only helps if the replay loader refuses a log whose
  world-config hash or limits version differs, which the design doesn't say.
- Dousing a cold, wet or non-burning target is now valid physics, so `act_result.success` changes for the same
  request; N4's "a refused target names the call that works" test changes.
- N3 lists `douse`, §8 keeps `extinguish`. NPC memories on `extinguish` learned "fire stops now"; under F1 the new
  physics must not inherit them.
Fix: retire `extinguish` (refused as unknown after the bump, with a `retired` code that names `douse`) and add `douse`
with its own params, caps (`max_water_kg_s`, a duration or per-intent mass), and refusals. State that replay refuses
a log whose action-limits version or vocabulary version differs.

**F8. SHOULD-FIX: material table v1's loader inherits none of the v1 refusals from today's code, and species order is
positional.**
Location: design §2.5; `config.py::MaterialTable.load`; research §1.4 ("index = position; saves and the wire store
this order").
Today: `yaml.safe_load` (a repeated material key silently keeps the last one, which `ActionLimits.load`'s
`_StrictLoader` already fixed for actions), `v["id"]` raises a bare `KeyError` instead of a named refusal, unknown
keys are ignored (`degrade_abvoe_c` is silently a non-degrading material), no version. v1 adds species and reactions
with more ways to be wrong. If species are positional, inserting `nh3` between `co` and `h2o` makes every saved
`species_kg` column and every logged state digest mean a different gas.
Fix: v1 uses `_StrictLoader`, refuses unknown, missing and repeated keys in every section with the file and key in
the message, and validates: unique names across solids, liquids and species; ids unique per namespace, solid ids in
u8 with air = 0, ids stable (a lint against the committed fixture: an id never changes its material); species count
capped at what the zone table and save were sized for; every transition target exists in the right namespace (a
melt targets a liquid, a boil a species) with no cycle at the same temperature; every reaction's species exist,
coefficients finite and positive, mass and C/H/O/N balance to 1e-9; every number finite and in a physical range
(density > 0, latent ≥ 0, transition temperatures above absolute zero and ordered). Species and columns are keyed by
name on the wire and in saves, with position used only in memory; the list is append-only (lint).

**F9. SHOULD-FIX: zone ids have a scene-dependent dtype and no cap.**
Location: research §1.2 (`zone` "u8 (u16 if over 255 zones per tile)"); design §2.2, §8.
A channel whose dtype flips at 256 zones means a scene edit changes the wire format; a GDScript decoder written
against u8 fixtures misreads a u16 channel if it trusts its own expectation over the descriptor. There is also no cap,
so a scene with 10⁵ one-cell zones costs the zone step and the table, and feeds `welcome` a megabyte zone list.
Fix: fix the `zone` channel at `<u2` (or u8 with a hard cap of 255 including `outside`), and put `max_zones` and
`max_gaps` in world config, refused by the scene loader.

**F10. SHOULD-FIX: regions change at run time, and v2 makes them ids, but neither `welcome` nor the frame carries the
change.**
Location: design §2.4 (`region_id` u16), §8 (`welcome`); v1 W-F12 (asked for a `regions` message or a
`regions_version`).
An imagined object adds a region; a burnt one leaves. With an id array, a reader that sees `region_id` (if it is ever
a channel) or an `act_result` naming a new region has no table to resolve it. If ids are reused after a region is
destroyed, an NPC's SEM memory of entity 7 (a crate) attaches to the next object given 7.
Fix: region ids are never reused within a world or across its saves; the u16 space has a refusal when exhausted
(imagination gets "too many objects", never a wrap). Add `regions_version` to the frame header and a `regions`
message (or a table) on change.

**F11. SHOULD-FIX: zones become SEM entities and act targets, but share a namespace with regions.**
Location: design §7 N1 (`zone` entity kind; `vent` affordance), v1 §7 (`act {region, action, params}`).
A scene can name a zone `lab` and a region `lab`. `act {region: "lab", action: "vent"}` is then ambiguous, and a
later rename of either silently retargets old logs.
Fix: `act` targets `{kind, name}` (or one id space), and the scene loader refuses a name used by both a zone and a
region. Test the collision.

**F12. SHOULD-FIX: `fields.yaml`'s migration default is shown as an expression, which a loader must never evaluate.**
Location: design §2.5 ("with a default for older saves"); research §1.5 (`default_for_older_saves:
material.fuel_kg_m3 * integrity`).
The obvious implementation is `eval` or a mini-language, which makes a data file executable and gives a crafted
`fields.yaml` (or an embedded registry, F5) code execution or an unbounded computation. Even a safe mini-language is
a new trust boundary nobody has specified.
Fix: the default is a literal, `null` (refuse), or the *name* of a migration function registered in code
(`migrations.fuel_from_material_and_integrity`), refused if unknown. The loader also refuses: unknown keys; duplicate
field names or channel names; an unknown container, grid, dtype, encoding, law, unit or process; a cell field not
per unit volume or a zone field not extensive; `every_ticks` < 1; a snapshot clamp with `lo >= hi` or non-finite;
`required` not a bool; a `ledger` that isn't declared.

**F13. SHOULD-FIX: scene format v1 is the first scene *file* loader, and its zone and gap rules are unstated.**
Location: design §2.2, §8, §11 row 6; `scene.py::Scene.from_dict`.
Today's `from_dict` has no version, ignores unknown keys (`ambient: 900` instead of `ambient_c` is silently 20 °C),
and raises `KeyError` on a primitive without `min_m`, although its docstring says every malformed shape is a
`ValueError`; only `spec.place`'s `except KeyError` hides that. v1 adds zones, vents and doors.
Fix: scene v1 carries `version: 1`; a scene with no version is v0, accepted only if the design says so (and v0's
fixture stays committed). Refusals: unknown keys at every level; missing keys as named `ValueError`s; zone boxes not
on the 0.2 m grid (judged in integer decimetres, not by `x / 0.2` in floats, where `0.6 / 0.2 = 2.9999999999999996`);
overlapping zones; a duplicate zone name; an unknown zone kind; reservoir composition with an unknown species, a
non-finite or negative fraction, or fractions not summing to 1; a vent or door with non-positive or non-finite area,
an aperture outside [0, 1], or not on the boundary between its two named zones (or a zone and the reservoir); a wall
between zones thinner than two coarse cells (CLAUDE.md); more primitives, zones or gaps than the caps (F9).

**F14. BLOCKER: the save, the scene file and the replay log are untrusted inputs, and the design doesn't say they pass
the validators the live path uses, or that memory is checked before it is allocated.**
Location: design §8 (save), §2.5 (`memory_budget_mb` "checked against the registry when a world loads"), §11 row 9;
`scene.py::MAX_EXTENT_M`.
A save is shared as a bug report (CLAUDE.md: "the intent log … is the bug report … and the save format's
backbone"). Scenarios:
- A save whose `temperature` array holds NaN, or −500 °C, or whose `material` holds id 200 (not in the table, so
  the property arrays index past their length or read defaults). It loads, and TB-1's world corruption is back,
  through a file instead of a socket.
- Its embedded placed specs are written straight into cells, bypassing `imagination.spec.place` (CLAUDE.md: never
  write cells from unvalidated output).
- A scene of 1000 × 1000 × 1000 m (allowed by `MAX_EXTENT_M`) at the max rig is 8×10¹² cells. If the budget is
  checked "against the registry when a world loads" after `MaterialGrid.empty` allocates, the process dies of
  memory before it can refuse. A save header claiming `shape: [1e5, 1e5, 1e5]` does the same, as does a u32 header
  length near 4 GB.
Fix: say in §8 that every loader (save, scene, log, fields, materials, vocabulary) is a trust boundary under B3/B4,
and:
- the memory budget is computed from extent, cell size and the registry's bytes per cell **before** any allocation,
  and refuses;
- a save's grid shape must equal the shape its scene and rig produce; every `size` equals the product of shape and
  itemsize; offsets lie inside the payload and don't overlap; the header length has a cap; the RNG state is checked
  to be PCG64 with the right structure;
- every saved cell value is validated as the live path would leave it: material ids in the table, temperature finite
  and above absolute zero, integrity, progress and packing fraction in range, fuel ≥ 0 and finite, the loose flag 0/1;
  zone and pool tables finite and non-negative, with species matched by name;
- embedded scene and specs re-enter through `Scene.from_dict` and `imagination.spec.place`; checkpointed thought
  results and queued intents through the same stage-1 validator as live input (TB-15);
- a load either completes or leaves no world: decode and validate into new objects, swap only at the end.

**F15. SHOULD-FIX: a stored digest of derived fields conflicts with "old save fixtures must still load".**
Location: design §8 ("Derived fields are recomputed on load and checked against a stored digest"); research §2.3
fixture 5.
A legitimate change to derivation code (zone membership by volume overlap instead of cell centre, a new cached
property) changes the recomputed derived state. The derived digest then refuses every old save, including the
committed save v0 fixture, which "every later loader must still load". Either the fixture breaks or someone loosens
the check.
Fix: the derived digest is checked only when the save's code SHA (or a declared `derivation_version`) matches; a
change in derivation bumps `derivation_version`, and a load across versions recomputes without the check and says
so in the load report. State which.

**F16. SHOULD-FIX: the intent log header is missing versions it depends on, and "hash" has no canonical form.**
Location: design §8 ("The intent log header hashes the registry and the material table"); v1 §7.
- Thought results are tool calls named in the SEM vocabulary, so a log replayed after a vocabulary bump misparses
  them: the vocabulary version (N7) and the scene format version belong in the header.
- A hash of the raw YAML bytes makes a comment edit refuse every log; a hash of the parsed object needs a canonical
  serialization (sorted keys, floats as `repr`, no YAML anchors) or two machines disagree.
Fix: add the vocabulary, scene format, action limits and registry versions to the header, and define the hash as
SHA-256 over canonical JSON of the validated, loaded object. Replay refuses any mismatch, naming the field.

**F17. SHOULD-FIX: the SEM vocabulary has a version but no consumer that checks it.**
Location: design §7 N7, P6.
Maxim has no vocabulary version (P6 proposes one), so nothing on Maxim's side refuses. NPC memories persist across
sessions (agent homes, Phase 4). A home trained against vocabulary v1 loaded into a v2 world keeps its causal links
on names whose meaning changed (F1), or on retired names.
Fix: record the vocabulary version with each agent home and in the roster hash of the log header; the world refuses
(or runs a named migration for) a home from another vocabulary version. The golden tool-surface fixture covers
names, param schemas, units and ranges, not only names.

**F18. SHOULD-FIX: N6's world-owned body sensors go through a fail-soft Maxim call that hides every failure.**
Location: design §7 N6; Maxim `embodiment/audio_localization.py::world_set_axis`,
`embodiment/backends/minecraft.py::MinecraftWorldBackend`.
`world_set_axis` returns `False` when the body YAML doesn't declare the sensor, so a body without `skin_temperature`
never feels heat and nothing says so. It clamps to the declared range: a skin temperature in °C written to a sensor
declared with range `[0, 1]` reads 1.0 at 20 °C and at 900 °C alike, and a NaN becomes the upper bound. With no
declared range, NaN is written raw. The Minecraft path also declares `world_owned_sensors`, which `build_executor`
unions into `live_world_set_sensors` so the modelled `self_effect` on those keys is filtered; the design doesn't say
Overdrive does this, so a modelled wetness delta and the world's wetness would both write the sensor. And "after each
advance" has the simulation lane writing into an agent object that lives on the thinking lane.
Fix: Overdrive ships the body sensor declarations (name, units, range) in `vocabulary.yaml`; declares them as
world-owned through `build_executor`; checks at NPC spawn that each one is declared, refusing the spawn loudly if not;
treats a `False` from `world_set_axis` as an error, not a warning; writes only finite values in declared units,
reduced over the body's volume in metres; and hands the values across lanes as a frozen percept the thinking side
applies, never a direct write from the simulation lane. Rename "after each advance" to "after each physics step".

**N1. NIT:** the research header carries `format: "mo-frame"`, `version: 0` and `protocol: 0`. Say which one a
reader refuses on, or drop one. A save adds magic `MOSAVE\0` (research §2.2) that design §8 doesn't mention; a save fed
to the frame decoder, or a frame to the save loader, should be refused by magic and `kind`.

**N2. NIT:** "a new encoding, dtype, `kind` or compression bumps the protocol" should also list grid kind, table
layout and the units vocabulary (F1, F3, F4).

**N3. NIT:** the protocol freeze is PR 5, before zones exist (PR 6). Its fixtures must already include a synthetic
table and a second grid, or "the grammar is generic" is unproven at the freeze. Say so in §11 row 5.

**N4. NIT:** `welcome` grows with the material table, catalogue and zone list. Give its size a budget in B5 next to
the frame's, since Godot's inbound buffer must hold it in one message.

## Rejection paths the implementing PRs must test

Each refusal is loud (a named error or an `error` reply), leaves the world, the log and any half-built object
unchanged, and has a test. PR numbers are design §11's.

**Frame decoder, Python and GDScript (PR 5, B3):**
1. Unknown `format`, `version`, `protocol` or `kind` (`delta` included); unknown compression, dtype, encoding kind,
   grid kind.
2. Unknown required channel, table or column: refused. Unknown optional ones: decoded around and ignored.
3. A channel on an unknown grid name, with each `required` value.
4. A channel the reader needs, missing (F2).
5. A linear channel with non-default scale and offset decodes to the right values (F2).
6. `size` ≠ product of grid shape and itemsize; `stored_size` ≠ `size` with compression `none`; an offset outside
   the payload; overlapping ranges; trailing bytes; a header length beyond its cap or beyond the message; non-UTF-8
   or non-object header; NaN or Infinity in the header.
7. A table with `rows` ≠ the zone count, a key column missing or not integer, keys out of order or duplicated.
8. A frame whose registry or materials hash differs from `welcome`'s (F6).
9. The asymmetric grid fixture, unchanged from v1.

**Material table v1 (PR 4, B12):**
10. Missing `version`, unknown version; unknown, missing or repeated keys in every section.
11. Duplicate names across namespaces; duplicate or out-of-range ids; air not id 0; an id that changed material
    against the committed fixture (lint).
12. A transition with an unknown target, a target in the wrong namespace, or a cycle.
13. A reaction with an unknown species, a non-positive or non-finite coefficient, mass imbalance over 1e-9, or an
    atom imbalance in C, H, O or N.
14. Any non-finite, negative-where-positive or unphysical value (density ≤ 0, transition below absolute zero).
15. A species count over the cap; a species reordered or removed against the fixture (append-only lint).
16. The shipped table: 13.1 MJ per kg O₂ ± 10%.

**`fields.yaml` (PR 3, B12):**
17. Unknown version, unknown keys, duplicate field or channel names.
18. Unknown container, grid, dtype, encoding, law, unit, ledger or process; `every_ticks` < 1; bad clamp; `required`
    not a bool; a cell field not per unit volume.
19. A `default_for_older_saves` that isn't a literal, `null` or a registered migration name (F12).
20. A registry whose bytes per cell overflow the rig's `memory_budget_mb`.

**Scene v1 (PR 6):**
21. Missing or unknown version; unknown keys at every level; missing keys as named `ValueError`, never `KeyError`.
22. Zone boxes off the 0.2 m grid (integer test), overlapping zones, duplicate names, unknown kind.
23. Reservoir composition: unknown species, non-finite or negative fractions, sum ≠ 1.
24. Vents and doors: area ≤ 0 or non-finite, aperture outside [0, 1], not on the boundary between their zones.
25. A zone or region name used by both (F11); counts over `max_zones`, `max_gaps`, primitive cap.
26. An extent whose cell count overflows the memory budget, refused before allocation (F14).
27. The v0 scene fixture: accepted or refused as the design decides, with a message naming the version.

**`act` (PR 7 onward):**
28. `douse` (or the new `extinguish`): missing, non-finite, negative or over-cap water mass or rate; unknown params;
    a point not on the target.
29. Retired `extinguish` after the bump (F7), with a reply naming `douse`.
30. `vent` and the other zone affordances against a region, and region affordances against a zone.
31. Imagination past the region-id space: refused, ids never reused (F10).

**Save v0 (PR 9, B4):**
32. Wrong magic, unknown format or registry version, newer registry version, wrong `kind`.
33. A field unknown to this build, missing without a default, or with a different dtype or units (F5).
34. `cell_size_m` ≠ the rig's; shape ≠ the shape the scene and rig give; any size or offset inconsistency.
35. Cell values: NaN or infinite anywhere; temperature at or below absolute zero; integrity, progress or packing
    outside range; fuel < 0; a material id not in the table; a loose flag not 0 or 1.
36. Tables: species by name, a missing or unknown species, negative or non-finite moles or enthalpy.
37. Embedded scene and specs refused by `Scene.from_dict` or `spec.place`; checkpointed records refused by the
    stage-1 validator.
38. RNG state not PCG64, or malformed.
39. Derived digest mismatch under the same `derivation_version`; across versions, the load report says it
    recomputed (F15).
40. A refused load leaves no partial world; the heavy-mode test (save, load, continue, bit-identical).
41. The v0 save fixture still loads in every later build, or is refused with a message naming its version.

**Intent log (PR 5 and PR 10):**
42. A header whose registry, material table, scene format, vocabulary or action-limits version or hash differs.
43. An `extinguish {}` record from a pre-bump log is refused, not reinterpreted.

**SEM and body sensors (PR 7 onward, Phase 4):**
44. The golden tool-surface fixture: a renamed or re-unitted tool or sensor fails it.
45. An NPC body missing a world-owned sensor: the spawn is refused (F18).
46. A non-finite body sensor value never reaches `world_set_axis`.
47. An agent home from another vocabulary version is refused or migrated by name (F17).

## Checked and found consistent

- **Unknown-required refuse, unknown-optional ignore** is the right rule for a renderer, and it can be implemented
  safely because each channel carries its own offset and size; an old reader can skip an optional channel's bytes
  without knowing its dtype. The six fixtures in §8 test both halves.
- **"A new encoding, dtype, `kind` or compression bumps the protocol"** closes the v1 W-F6 hole where a zstd frame
  could be decoded as raw cells. `kind: delta` being reserved means a v0 reader refuses it rather than misreading it.
- **The asymmetric fixture and `axis_order: zyx` carry over from v1** (W-F4), and the grids block gives each grid
  its own shape, cell size and origin, so a future fixed gas grid needn't share the cell grid's shape.
- **Adding an optional channel bumps the registry version, not the protocol**: consistent, provided the client
  doesn't refuse on registry version and reads descriptors instead (which F6's precedence rule makes explicit).
- **Material table ids stable, saves storing ids**: today's `core.yaml` comment and v2 agree; `MaterialTable.__init__`
  already refuses duplicate ids, a missing air at 0 and ids outside u8.
- **`ActionLimits.load`** already has the strict-loader pattern (repeated keys, closed sections, exact version as a
  real `int`), which is the right model for every v2 loader.
- **The save is rig-bound and refused at another `cell_size_m`**, which avoids an ambiguous refinement path; co-op
  guests never load saves, so the save loader is not reachable from the socket.
- **Gas species in zones, never per-cell phase tags**, keeps the tables tiny (about 13 KB for 100 zones), so tables
  are not a memory or bandwidth risk once zone and species counts are capped (F8, F9).
- **`act` keeps one gate**: `parse_action` reads nothing from the world and refuses unknown params, so the v2
  affordances can be added as typed actions in the same validator for NPCs, LLM output and clients.
- **N3 (causes, never outcomes; no `target_effect`)** and **N2 (fractions, not labels)** add no wire field Maxim
  lacks, so the `_compat` mirror and `test_sem_compat.py` are unaffected.
- **`world_set_axis(owner=...)` exists as the design describes**, and the Minecraft backend is a working precedent
  for world-owned sensors (subject to F18's declarations and checks).
