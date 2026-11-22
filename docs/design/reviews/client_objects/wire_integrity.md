# Wire integrity review: client_objects.md (D-B2), round 1, at 51c9660

Scope: `git diff origin/main...HEAD` (the design plus the probe). I read every producer and consumer outside the document at the branch tree. I also read `origin/main` at 98e2342, because **PR #37 (`phase1/docs-contracts`) has already merged into main** and this branch is still based on 2e67af2. Read only; nothing was modified.

## Contract table

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| Cell channel `surface_glow` (u8, offset 525, 975/255) | `scripts/client_fixtures.py::fire_channels` (fixtures only). `encoding.snapshot` sends `glow`, a different name and quantity → none | `cell_snapshot.gd::CHANNEL_BYTES`, `cell_volume.gd` (`glow_tex`), `emission.gdshaderinc::glow_count`, `debug.gdshaderinc` (glow mask), `snapshot_fixture.gd`, `test_client_fixtures.py`, `test_cell_volume.gd`, `test_volume_textures.gd`, FIELDS.md, `client_rendering.md` §3.1, §4.2, §5.1, §5.3, `checklists.md` step 7 → retired | skin temperature, per spec (the cell mean in practice) → `temperature_c`, which is **not solid-masked** (F3 below) |
| Cell channel `burning` | `client_fixtures.py` → none (the name stays reserved) | `emission.gdshaderinc::flame_emission`, `cell_volume.gd`, unit tests, §4.2, §5.1, §5.3, **`fire_model.md` §9.2 (defines `burning` = ignited fraction)**, `checklists.md` step 7 → none | flicker from a cell fraction → nothing. Flames come from the `flames` table (6.2) |
| `welcome`'s `glow` calibration (`offset_c`, `scale_num`, `scale_den`) | `client_fixtures.py::content` → removed ("client constants", §5.1) | `snapshot_fixture.gd::_read_glow`, `CellSnapshot.glow_*` and `problems()`, `test_snapshot_fixture.gd` (975/255), FIELDS.md's Vocabularies row → client constants | a catalogue rational → a hard-coded 525/975. **The only non-default-scale channel disappears** (F7) |
| Cell channel `temperature_c` (f16) | `encoding.snapshot` (unchanged) | "a debug view kept by choice" (§4.2), read by no pass (`cell_snapshot.gd` comment) → the structural glow input, through both sampler variants (§5.5) | an unread debug channel → a load-bearing input whose `required` flag is never stated |
| `encoding.snapshot`'s `glow` key, `GLOW_START_C`, `GLOW_FULL_C` | `src/simcore/protocol/encoding.py` → **not addressed** | `tests/test_snapshot.py` (4 asserts), `architecture.md` l.160, `roadmap.md` l.19, `boundaries.md` §8.3, FIELDS.md | unchanged; the design never says whether `glow` is deleted (F9) |
| Cell channel `crack` | unchanged | §5.4 crack shader, `golden_measures.crack_findings`. `tile_and_client.md` §5.5's bed meaning → dropped | 1 − integrity, severity by groove width → severity by edge density (§6). The meaning is kept (F1 respected) |
| Tables `objects`, `rods`, `slabs`, `segments` (new) | `fire_solid.md` §5.6's list → this design §3.2–3.3; core fuel view at 6.0b; protocol quantization at step 7 | step 7 decoder; a new `Fuel` node and its shaders (step 8); FIELDS.md | new. Columns, dtypes and units are named. **Per-column `required`, encoding names and the dtype list are not** (F6) |
| Table `flames` (6.2) | 6.2 → design §3.4 | object pass (step 8) | a base box plus a height. The width that fire_model §4.1 computes is not sent (F13) |
| `welcome` recipe map; kind vocabulary | recipe map: already in main's §4.1 `welcome` row (#37) → also stated in design §3.1. Kind vocabulary: new, with ids fixed in the design (`rod` 0, `slab` 1) | decoder | the main §4.1 row lacks the kind vocabulary, and §8 doesn't add it (F2) |
| Frame send rule | main §4.1: "only on cells' version change … (2 Hz during any fire)" → plus "or any fuel table changes" | server send loop, B5 bytes | "changes" is never defined as a version (F10) |
| Published frame's fuel view | none → "per-segment reductions … on the frame, in f64" | `encoding` (protocol); the SEM membrane via `FrameView` | no type, field names or site are given (F10) |
| Extension and bump rule | main §4.1 (owner, after #37): only an *optional* addition is registry-only → design §3.1: required tables are also registry-only | every reader | two statements that disagree (F2) |
| Axis mapping z-up → y-up | main §4.1: "only the shader maps" | object transforms built in GDScript (§4.1) | a second mapping site (F8) |
| Frame size cap and gate | §4.2's Σ dtype × cells; §4.3's join-time 3.5 MiB check by shape → plus fuel tables up to world limits | server join check, B5 | the join check by shape no longer bounds the frame (F9) |
| Measured checks | `golden_measures.py`: crack, glow, speckle, ΔE agreement → plus severity, isolated, burn-through, stability, flame shape | `golden_run.py` FRAMES, `test_golden_measures.py`, §6.2–6.4 | the G2 crack check loses its subject on stick fuel (F11). The "kept" tier ID-mask check was never built (F12) |
| Scenario goldens G1–G5 and their beats | tile §6.3 → unchanged here, restated by D-S2 | §6.1 | unchanged |

## Findings

**F1. BLOCKER: `docs/plans/checklists.md::Step 7` still orders `surface_glow` and `burning` into the grammar, and §8 doesn't list the checklist.**
- `checklists.md` l.298 on main reads "`region` as u16 … `surface_glow` and `burning`".
- Design §8 has no checklists row, yet §8's B42 row says build items "moved to step 8's checklist", which is an edit to that file.
- Design §9 then restates step 7's content. That puts step 7's build list in two places (B36).
- Failure: step 7's author builds from the checklist and freezes v0 with both retired channels. Removing them later is a required-channel removal, which means a protocol bump on day one. That is exactly what this pass exists to prevent.
- Fix (unverified): list `checklists.md` steps 7 and 8 in §8, and keep step-7 content in one place.

**F2. SHOULD-FIX: `client_objects.md::§3.1` collides with #37, now on main.**
- (a) Main's `client_rendering.md` §4.1 owns "Extension and bumps": only an optional addition bumps the registry. Design §3.1 says adding *required* tables bumps "the registry version, not the protocol (world_v2 §8)". world_v2 §8 says that only for optional channels.
  - Failure: 6.2 adds the required `flames` table under a registry-only bump. The catalogue hash is compared frame against `welcome` from the same server, so an old client connects cleanly and then refuses every frame.
- (b) Main's §4.1 `welcome` row already carries "the recipe name↔id map". Design §3.1 restates it (B36), and the kind vocabulary isn't added to that row: §8 lists §4.1 only for "the send rule's fuel clause".
- (c) §4.1's send-rule text was rewritten by #37, so §8's planned edit must be redone against the new text.
- (d) `docs/design/contracts.md` exists now, so §8's "(after #37)" is stale.
  - The registry says "snapshot channels wait on #31's ruling". D-B2 *is* that ruling, yet §8 registers only the fuel tables, not §4.2's channels.
- (e) §1 says "read at main 2e67af2" but cites `reviews/docs_contracts/rulings.md`. That file does not exist at 2e67af2 or on this branch; I verified with `ls`.
- Fix: merge origin/main and redo §3.1 and §8 against it.

**F3. SHOULD-FIX: `client_objects.md::§5.1` changes what the glow input means.**
- Today's encoder zeros glow outside solids (`encoding.snapshot`: `* frame.solid`). `test_snapshot.py` asserts "hot air does not glow".
- `temperature_c` covers air cells too (world_model §8 F1: "Air cells' `temperature_c` stays cell temperature").
- The rig and max tiers read glow linearly filtered (`glow_count` samples at the cell's centre plane, blending with the tangential neighbours). Today's comment "never with the air cell in front of it" holds only because air was 0.
- Failure: flame gas at 900 °C beside a cold wall's edge lights that wall's edge cells, and lights the glow debug mask, so §6.4's glow check measures the wrong pixels.
- §3.5 also leaves `temperature_c`'s §4.2 meaning ("a debug view kept by choice") and its `required` flag unchanged, though the channel now drives a visual.
- Fix (unverified): state the solid mask (material ≠ air) as part of the glow rule, and mark `temperature_c` required.

**F4. SHOULD-FIX: `client_objects.md::§3.2` (`segment_length_m`) and `§4.1` (k = ⌊s/ℓ⌋) can index past an object's segments.**
- The half-open span [kℓ, min((k+1)ℓ, L)) excludes s = L. An end-cap fragment at s = L gets k = L/ℓ = `segment_count` whenever L is a whole multiple of ℓ.
- In f32, L/ℓ for L = 0.18, 0.30, 0.36, 0.54, 0.60 m gives 9.000001, 15.000001, … Measured: 19 of 1,981 lengths from 20 to 2,000 mm have ceil(f32 L / f32 ℓ) ≠ the true count (numpy, `float32`).
- Failure: the cap reads the next object's first segment row: wrong temperature, wrong burn-through.
- Adding the obvious decoder check (count = ⌈L/ℓ⌉) would refuse valid frames.
- Fix (unverified): state a clamp to `segment_count − 1` in the contract, and no f32 recount check. This also answers question F1 in §9.

**F5. SHOULD-FIX: `client_objects.md::§3.3` leaves its reduction denominators undefined.**
- `char_fraction` is "residue mass ÷ the segment's solid mass". Current or initial mass?
  - If initial: wood's char yield caps it near 0.2–0.3, so §6.1's severities 0.5–1.0 never draw.
  - If current: it is 0/0 at burn-through.
- `surface_temperature_c` is 0/0 when every part has zero area.
- Failure: the protocol layer gets NaN from the core. The f16 cast carries NaN, while u8 rounding is undefined, so one machine draws a value and the decoder on another refuses it.
- Fix: name the denominators and the empty-segment value.

**F6. SHOULD-FIX: `client_objects.md::§3.1–3.4` doesn't name what step 7 must freeze.**
- §3.1 says unknown optional columns are ignored but never gives any column's `required` flag.
- The encodings are written as "—", "1/255" and "clipped", with no names from main §4.1's closed encoding list.
- u32 and f32 are new dtypes in the binary frame (cells use u8, u16 and f16 today). Main §4.1 says "a new … dtype … bumps the protocol", and the design doesn't say v0's dtype list includes them.
- Unit tokens ("°C", "m", "1") aren't tied to the closed unit vocabulary.
- Every key column is named `object_id`, in five tables. The header is "per array name", and no table-qualified naming is given.
- Failure: step 7 either guesses, or ships v0 without u32/f32, and 6.0b's tables then bump the protocol.

**F7. SHOULD-FIX: world_model §8's non-default-scale fixture rule loses its only carrier.**
- §5.1 removes `surface_glow`'s 975/255 rational. Every remaining scaled column uses the default 1/255.
- world_model §8 ("Fixtures include a non-default linear scale, so a decoder that hard-codes 1/255 fails"), checklists step 7 and `test_snapshot_fixture.gd` ("glow scale 975/255") all depend on one existing.
- Failure: a decoder that hard-codes 1/255 passes every fixture.
- §8 doesn't mention it.

**F8. SHOULD-FIX: `client_objects.md::§4.1` (transforms from geometry rows) contradicts main §4.1 ("only the shader maps the server's z-up to Godot's y-up").**
- Instance transforms built in GDScript from world-metre rows are a second mapping site.
- Placing objects relative to cells also needs the grid origin. FIELDS.md lists that as unsettled ("origin … assumed"), and the design doesn't name which field it reads.
- Failure: one site maps z→y and the other doesn't, so sticks draw lying in a wall.
- The asymmetric-fixture rule covers cells only.

**F9. SHOULD-FIX: §8 ("What changes elsewhere") is incomplete.** Uses of a changed contract that it doesn't list:
- `fire_model.md` §9.2 still defines `segment_glow` and `burning` = "the ignited area fraction". That is a live second statement contradicting "`burning` reserved" (F1 meaning conflict).
- `client_rendering.md`:
  - §4.3: the join-time cap checks shape alone, and the header bound must include about 40 table columns.
  - §5.5: the tier table's glow sampler now reads `temperature_c`; flame particles.
  - §5.6: `dda.gd` picks "over `material` and `region`", while §4.3 now picks objects.
  - §6.1 and §6.2: the renderer golden list; "disabling the carving fails G2".
  - §6.3 and §6.4: the ID masks now include fuel.
  - §8: the budget rows of §7.4.
- FIELDS.md's `glow` calibration row and its `temperature_c` row ("not read"). §8 deletes only the two channel rows.
- `encoding.snapshot`'s `glow` key and its constants, with `tests/test_snapshot.py`; `architecture.md` l.160; `roadmap.md` l.19. They all still describe a `glow` channel the design neither keeps nor retires.
- Failure: each stale copy is the one an edit misses (B36).

**F10. SHOULD-FIX: `client_objects.md::§3.1` gives no contract for the send rule or the fuel view.**
- "When … any fuel table changes" has no defined trigger: core f64 state, quantized bytes, or a version?
- The cells use a version. No fuel version is named, and `frames.py::CellFrame` has no fuel fields.
- The fuel view's type, its field names and its site (CellFrame, Frame or a new type) are unstated. So is whether `FrameView` exposes it to the SEM membrane (only the NPC fire note's later decision is cited).
- Failure: 6.0b and step 7 pick different shapes. A byte-compare trigger stops sending once quantized values settle, while the design claims the 2 Hz cadence continues.

**F11. SHOULD-FIX: `client_objects.md::§7.2` (crack, "cracked cells and charred faces ≥ 12 px") and `§6.3` drop G2's subject.**
- G2 (§6.1) is "charred area reaches 4× the threshold", and its deletion proof (§6.2) is "disabling the carving fails G2".
- Per §6.3, char on sticks and on 20 mm slats under 12 px draws as darkening, never as carving.
- Failure: in the exit scene, the G2 crack mask holds no carved pixels, so `crack_findings` returns "the crack mask marks no pixels", or passes on unrelated concrete. Either way the carving deletion stops failing G2.
- §7.3 says G1–G5 "keep their names and beats" without reconciling this.

**F12. NIT: `client_objects.md::§7.2` calls tier agreement on ID-mask areas "(kept)".**
- `golden_measures.py`'s docstring says "§6.3's ID-mask areas are not measured yet", and B7 lists the check as missing.
- A deletion proof ("floor in rendered pixels") can't fail a check that doesn't exist.

**F13. NIT: `client_objects.md::§3.4`.** fire_model §4.1 has the server compute flame height *and width*. The table sends only the members' box, so a free flame wider than its fuel draws at the fuel's width.

**F14. NIT, two small items:**
- §3.1 fixes the kind ids (`rod` 0, `slab` 1) in the design while `welcome` also sends them. One of the two should own them.
- §5.1's "face temperature comes as a new channel" contradicts world_model §8's face table keyed by (cell, face).

## What I checked and found consistent

- The byte arithmetic: objects 16 B, rods 36, slabs 52, segments 11, flames 38 per row; 1,738,400 B at the limits, under 1,843,200 B and the 3.5 MiB cap. Checked by hand against the column lists.
- `region_id` u16 matches the `region` channel. `object_id` u32 and `recipe_id` u16 match `fire_solid.md` §1.1.
- `crack` keeps one meaning (docs-contracts row 79).
- `boundaries.md` §8.3 (quantization in the protocol layer) is respected.
- `QUANTITIES` is untouched.
- The probe adds no wire contract.
