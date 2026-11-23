# Sub-cell solids design, round 1: Wire integrity (2026-11-22)

The reader's report as handed back, saved by the author. Statuses are unset: a reviewer sets them after the fold.

**Reviewed:** `docs/design/subcell_solids.md` at 1c701aa, read against:
- `origin/main` bfb12f8 (#44 and #45 merged after the draft's base, 703b745);
- PR #40's `client_objects.md`;
- PR #42's D31–D35, survey and spike files.

## The boundary table

| Value | Written by | Read by | Unit / encoding | Version | Owner in the design vs. existing owner |
|---|---|---|---|---|---|
| `objects`: `role`, `material_id`, `integrity`, `support`, `pose` | insertion (Topology batch), `damage.objects`, `load` | digest, save, snapshot, laws | enum u8 / id u8 / ratio f64 / enum u8 / m + quaternion f64×7 | none (save v0 is step 9's) | §3.1 extends `fire_solid.md` §1.1, which matches. Writers are not declared, and sim_core §6 owns them |
| `objects.state` (+`failed`, `removed`), `kind` (+`box`, `cylinder`) | laws, insertion | digest, save, client decoder | enum u8 | values not numbered | `client_objects.md` §3.2 fixes `state` to 0/1 and checks it every frame. **Mismatch** (B1, S1) |
| `segments` (face rows) | insertion | heat laws, snapshot | m², normal, node index | — | `fire_solid.md` §1.1: a segment is a 0.02 m strip with two parts. **Two row meanings** (S1) |
| `contact` (+ object–object rows), `contact_exchange` | contact law | solid law; save (`contact_exchange` is saved, sim_core §5.1) | m², W | derived | Two key forms (S1) |
| `members` | load law | load law, §8.4 | graph | derived, never saved | OK |
| `limits.yaml`: `object_threshold_m`, `min_part_thickness_m`, `lumped_biot_max`, `breach_ligament_m`, `bearing_angle_deg` | repo data | `load_world_limits`, header | m, m, 1, m, deg | "bump". The file is not on main; 6.0a creates it at v0 | `fire_solid.md` §5.1. No ranges given (S8) |
| `mechanics.yaml` | repo data | `load_mechanics`, `FuelCatalogue`, header | Pa, W/m²K, K, names; `h_contact` per pair | v0 | `fire_solid.md` §5.1 owns the data-file list, and no §12 row adds this file to it (S9) |
| Refusal codes (+9) | gates, applier | agents, intent log, per-tick digest (sim_core §9, member 5) | wire spelling | append-only | `refusals.py`. `overlaps_fuel` and `fuel_only_region` ship first (S4). `too_small` has 3 producers (S3) |
| Per-tick digest | `Simulation` (PR 4, not built) | replay | `sha256/raw-1` | header | sim_core §9. "Empty tables add no bytes" is not derivable from it (S5) |
| Content digests (`digest.py`) | header writer | replay | `sha256/c14n-1:` | prefix | `boundaries.md` §6.3. Matches |
| Save | step 9 | step 9 | name maps | save v0 | `fire_solid.md` §5.5 plus §11.4. Vocabularies are missing (S1) |
| Log header | log writer | replay | digests, versions | intent_log v0 | `boundaries.md` §6.3. Matches once S9 is fixed |
| Snapshot object columns | `encoding.snapshot` (step 7) | Godot decoder | f32 m, u8 1/255, f16 °C | protocol + registry | `client_objects.md` §3 (PR #40). **§10 is incompatible** (B1) |
| `QUANTITIES` → `RegionInstrument` → `SensorReading` | `Frame.reading` | Maxim via `region_parts` | ratio, °C, bool | SEM vocabulary | `frames.py`/`sem_stimuli.md`. The meaning changes at S3, but object-only regions exist from S1 (B2) |
| `is_solid`, `StructureModulator` gate | `Region.solid` | bridge | bool | — | not addressed (B2) |
| Structural spec v1 (`imagine`) | LLM/generator | `imagination.place` | m | `spec_version: 1` | Fuel spec v1 is `fire_solid.md` §5.2's, so there are two "v1"s. `spec_version` is not `Format`'s key (S6) |
| `SpecId` content | imagination | spec store, `welcome` | c14n-1 | — | `ip_and_licensing.md` §6.1. The version and `role` join the hash, and the design doesn't say so (S6) |
| `topology_version` | `Topology` (PR #44, `topology.py`) | the caches of §5.2, §6, §8 | int | — | sim_core §5.1 bumps it only when a cell or the region table changes. **Object rows don't move it** (S2) |
| t(p), the thinnest dimension | §2.1 | representation rule | float64 m | — | F13 quantizes in integer µm. **The float subtraction depends on position** (B3) |

## BLOCKER

**B1. `subcell_solids.md::§10` hands `client_objects.md` §3 columns that its accepted decoder refuses.**

What PR #40 fixes:
- §3.1 makes every column `required`.
- §3.2 refuses a frame on "an unknown kind, recipe or region".
- §3.2 checks `state` ∈ {0, 1} every frame.
- Geometry is "a table per kind … never a reinterpretation of old columns".
- `segments` requires `ignited_fraction`, `thickness_fraction` and `char_fraction`, and segment k spans [kℓ, (k+1)ℓ)
  along an axis.

What §10 and §3.1 hand it instead:
- structural rows with `recipe_id` = sentinel 0xFFFF;
- two new states, `failed` and `removed`;
- geometry "as f32 metres" with no per-kind tables;
- face rows in `segments` carrying only `surface_temperature_c`;
- no `material_id`, though the client needs it for albedo and survey item 9 lists it.

**Failure:**
- The first frame with a 2 cm steel rail is refused whole (unknown recipe 0xFFFF), so the client draws nothing.
- Or the check is dropped, and the rail is drawn as a rod strip. A load failure (state 2) then refuses the frame
  again.
- Frame bytes (§3.5) and the join cap (`client_rendering.md` §4.3) are sized for fuel rows at the fuel limits. §3.1
  makes the limits count every role, which breaks the 3.5 MiB derivation.

**Fix (unverified):** state the requirements in `client_objects.md`'s own grammar:
- `material_id`, or a structural objects table;
- `boxes` and `cylinders` geometry tables;
- numbered `state` values;
- a separate `faces` table;
- the protocol bump that §3.1 requires for a new kind;
- the join cap, re-derived.

Grow §12's `client_objects.md` row to match.

**B2. `§7`, `§13` S1–S3: withdrawing `fuel_only_region` leaves object-only regions unguarded for two steps.**

S1 lands §4: object-only regions, which aren't gone while they hold a live object. Object readings only arrive in S3
(§7.3). Until then, `Frame.reading` (origin/main) reduces over the region's cells, and there are none:
- `region_integrity` returns 0.0;
- `temperature_*` return NaN (`temps.size == 0`);
- `breached` returns 0.

`Region.solid` is True for an imagined region, so `region_parts` builds the modulator and the instruments.

**Failure:**
- After S1, an NPC imagines the 1 cm steel locker, which is entirely objects. Its `integrity` sensor reads 0.0
  ("destroyed"), and `temperature_max` puts NaN into a Maxim `SensorReading`.
- A `strike` hits `_check_region`'s `not cells.any()` and is refused `region_gone` for a region that isn't gone.
- No `is_solid` meaning is given for an object-only region.

**Fix (unverified):** move §7.3 and the `is_solid` rule into S1. Alternatively, keep an object-only refusal from S1 to
S3, knowing that an append-only code is permanent.

**B3. `§2.1`: t(p) = `max_m − min_m` in float64 depends on where a part is authored, against D35 (1).**

The design says the comparison runs "on the authored float64 values, exactly as written", but the subtraction rounds:
- `0.6 − 0.2 = 0.39999999999999997`, which makes the part an object;
- `9.6 − 9.2 = 0.40000000000000036`, which makes it cells.

For specs, `imagination._offset` adds the origin before any check runs. Measured with a scratch script, a 0.4 m part
becomes an object at 197 of 1,000 origins (0.0003 + k·0.001) and at 267 of 1,000 scene positions (k·0.01).

**Failure:** the same block is cells in one place and an object in another, with different fire, load and `ignite`
outcomes. S1's red-first test goes red or passes by luck, depending on which offsets it samples.

**Fix (verified in part):**
- Compute t on integer micrometres, F13's quantum: `round(hi·1e6) − round(lo·1e6)`, on the spec's relative
  coordinates, before `_offset`. Over 3×10⁵ (position, origin) cases the result was exactly 400,000 µm every time.
- A tolerance would only move the knife edge, so the reader ruled that out.
- Express both thresholds in whole µm.

## SHOULD-FIX

**S1. `§3.1`, `§5.1`, `§11.4`: enumerations without numbers, and tables with two row meanings.**
- `state` (`failed`, `removed`) and `kind` (`box`, `cylinder`) have no u8 values, although these columns are saved,
  digested and sent on the wire.
- `segments` mixes fuel strips (parts, node offsets per part) with faces. A burning structural leg (`burns_as`) would
  need fire_solid §4's per-part flash on a face that has no parts.
- `contact` gets a second key form, while `contact_exchange` is saved per coupling row.
- The save carries a name map for `material_id` only.

**Failure:** step 9 numbers `failed` 2 and the client uses 2 for something else.

**Fix (unverified):** number every value. Give faces and object–object contacts their own keyed tables (F1). List
every vocabulary in the save.

**S2. `§5.2`, `§6`, `§8` vs PR #44's Topology owner.** The caches are keyed on `topology_version` or "per topology
batch". `topology.py` has only `Destroy`, `Paint` and `NameRegion`, and sim_core §5.1 bumps the version only for a
cell or the region table.

**Failure:** a pane cracks (§7.2). That is a law outcome, not a topology request, so the version doesn't move. The
face-to-zone and blocked-area caches stay stale and the zones never join, which contradicts §6. The same happens on
`failed`, `removed` and a `pending` drain.

**Fix (unverified):** name the object requests in Topology's request set. Say which object changes bump
`topology_version`, or define an `objects_version`. Add a sim_core §5.1 row to §12.

**S3. `§11.3`: `too_small` has three producers, not the one meaning the design retires.** Besides the cell-centre
case, origin/main produces it in:
- `scene._check_volume`, for zero volume (3b review S4; `tests/test_scene_v1.py:229`);
- `_voxelize`, for "or outside the world".

**Failure:** the code isn't actually retired (a 1e-300 m radius still produces it), and an entirely-outside spec has
no code.

**Fix (unverified):**
- Zero volume becomes `part_too_thin`, and outside the world becomes `outside_extent`.
- Separately, the per-tick digest records refusal codes (sim_core §9, member 5). An `imagine` refused as `too_small`
  before S1 is accepted after it, so S1 must record a replay break.

**S4. `§7`, `§11.3`, `§12`: codes that ship before S1 can't be withdrawn.** S1 lands after 6.0b, and 6.0a/b append
`fuel_only_region` and `overlaps_fuel` (`fire_solid.md` §5.3). The enum is append-only (`tests/test_refusals.py`), and
the revisions are "proposed, not applied".

**Failure:** both codes ship, and `overlaps_object` becomes a permanent near-duplicate of `overlaps_fuel`.

**Fix (unverified):** land the `fire_solid.md` §2 and §5.3 revisions before 6.0a, with `overlaps_object` in place of
`overlaps_fuel`. Otherwise, accept the duplicates in writing.

**S5. `§2.3`, `§11.4`: two digest claims that don't follow from their owners.**
- **Voxelization:** §2.3 changes how every cell primitive voxelizes, from centre-inside (`scene.py`'s docstring and
  `mask`) to overlap ≥ ½. Grid-aligned boxes like alley_box don't change, but cylinders and off-grid boxes do: a
  corner cell at 0.7×0.7×1 holds its centre yet has 0.49 overlap. That is a sim_core §12 break, and it isn't
  recorded.
- **Empty tables:** "Empty tables add no bytes" doesn't hold under sim_core §9. Each digested field is a member with
  its name, dtype, ndim and shape, so any new member changes every tick's digest even when empty.

**Failure:** the goldens get regenerated silently.

**Fix (unverified):** record both as breaks, bump `derivation_version` (F15) for the voxelization rule, or state that
the new columns stay inside existing record members.

**S6. `§11.2`: spec v1.**
- **The version key:** `Format` reads the key `version` (`schema.read_version`), so `spec_version` would bypass the
  format gates.
- **v0 was persisted:** "Nothing persisted v0" is false. PR #42 commits v0 specs, in `spikes/specgen/arms.yaml` and in
  JSONL that is "never regenerated". S1's own red-first test reads arms.yaml's unversioned footstool, aquarium and
  locker, and that prompt says "Primitives may touch or overlap", which v1 refuses.
- **Two v1s:** the fuel spec v1 ships at 6.0b in a different shape.
- **SpecId:** it hashes every accepted key, so the version and `role` change identities, and the design doesn't say
  so.

**Failure:** S1's test gets `bad_version` on its own inputs, and rescoring the spike refuses every sample.

**Fix (unverified):**
- Use `version`.
- Add a v0→v1 migration, in which no `role` means `structure`.
- Settle the fuel and structural formats before 6.0b.
- Add the SpecId note to §12.

**S7. `§7.1`: the outcome changes across the threshold.**
- `ignite` on a 0.39 m concrete block (an object) is refused `not_flammable`, while a 0.40 m block (cells) is
  accepted, as any solid cell region is today.
- `not_on_object` duplicates `not_on_region`.

**Failure:** an NPC gets different codes and outcomes for the same act on near-identical blocks, against §2.2 and an
affordance §9 says is unchanged.

**Fix (unverified):** one rule for both representations, and reuse `not_on_region`.

**S8. `§11.1`: no ranges and no canonical pair key.**
- Nothing stops `object_threshold_m` from going below 0.4 m, which breaks the thin-feature rule.
- `h_contact` pairs have no key form.

**Failure:** `{steel, glass}: 50` and `{glass, steel}: 80` both load, and the value depends on lookup order.

**Fix (unverified):**
- Refuse `object_threshold_m < 2·ALIGNMENT_M`.
- Refuse `min_part_thickness_m ≥ object_threshold_m`.
- Require sorted pairs, and refuse reversed or duplicate ones, each with a gate row.

The Biot, ligament and bearing values are law parameters, not allocation limits, so consider moving them to
`mechanics.yaml`.

**S9. `§12` is incomplete.** It is missing rows for:
- `fire_solid.md` §5.1: the `mechanics.yaml` row, which feeds the header and the shipped-data test, where "an unowned
  file stays an error";
- `fire_solid.md` §5.4 and §5.5: the rename, and the digest and save lists;
- `sim_core.md` §5.1 and §9;
- `scene.py`'s docstring;
- `imagination.SPEC_KEYS` and `ip_and_licensing.md` §6;
- `client_objects.md` §3.1–§3.5 beyond its columns.

## NIT

- **N1. §7.1, §12:** the law `load` collides with sim_core §5.1's `Load` input kind (a strike).
- **N2. §11.4:** "`members` … must equal the stored digest", but `members` is not digested. Name what is compared
  (`support`, `state`).
- **N3. §11.3:** `dangling_reference` is already 6.0a's code.
- **N4. §8.2:** the "strength-factor version" has no owner, since sim_core §7 keys on write ticks.
- **N5. §3.1:** "`pose` and `support` need no format change" promises things about D32's needs (velocity, sleeping
  state).

## Summary

3 BLOCKERs, 9 SHOULD-FIXes and 5 NITs.
- **The headline invariant fails as written (B3).** Representation is not independent of position. The micrometre fix
  is verified.
- **Two live boundaries would get wrong or refused values.** The client hand-off (B1) and the S1–S3 interim (B2) each
  affect the client wire or the SEM readings.
- **The format items (S1, S3–S6) are mostly naming work.** They need values numbered and rows added to §12.

The reader found no other conflicts between the design's new codes, files or columns and an existing owner.
