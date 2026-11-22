# Wire integrity delta review: client_objects.md (D-B2), delta 1, at bbebd69

Scope: `git diff 065f84d bbebd69`, plus every section that uses a contract the fold changes. I grepped the producers and consumers outside the diff: `encoding.py`, `frames.py`, `adapters/sem/bridge.py`, `client/addons/engine/render/*`, `client/tests/support/*`, `scripts/client_fixtures.py`, `tests/test_snapshot.py`, `tests/test_client_fixtures.py`, and the other design documents and plans. Read only. I changed nothing and ran no git command that writes.

**`scripts/lint_standards.py`:** `PASS (0 finding(s)); rules enforced by a check: 20, held only by review (backlog): 28`.

**Word budgets against origin/main 98e2342** (contract marker lines excluded):

| Document | origin/main | bbebd69 | Kept? |
|---|---|---|---|
| `client_rendering.md` | 3,774 | 3,765 | kept |
| `fire_solid.md` | 5,967 | 5,967 | kept, exactly |
| `fire_model.md` | 5,528 | 5,475 | kept |
| `tile_and_client.md` | 5,351 | 5,335 | kept |
| `client_objects.md` (new) | — | 5,078 | under 6,000 |

## 1. Round 1 fold status (set by this reviewer from the tree, O25)

| Finding | Status | Evidence |
|---|---|---|
| A-B1 | fixed (text). Exit holes deferred to owner question 4, trigger "before step 8 builds its goldens" | `client_objects.md::§1, §2, §5.3, §7.3, §9 q4` |
| A-S1 | fixed. Site residual, see N7 | `fire_solid.md::§5.6` ("Step 7 builds it with its caller") |
| A-S2 | **open**. Stale copies remain | N4, N5, N6 below |
| A-S3 | fixed. 36 K per kW/m² checks: 1000·0.05/1.4 = 35.7 | `client_objects.md::§5.1` |
| A-S4 | fixed | `standards_backlog.md::B42` trigger |
| A-S5 | fixed | `client_objects.md::§7.2` Burning row |
| A-S6 | fixed | `§7.5`; `checklists.md::Step 8` |
| A-N1 | fixed | `fire_solid.md::§5.6` |
| A-N2 | **open**. The misattribution moved from world_v2 §8 to client_rendering §4.1 | N3 |
| A-N3 | fixed. Delta frames are explicitly unscheduled | `client_objects.md::§10` |
| W F1 | fixed | `checklists.md::Step 7` |
| W F2 | (a) **open** (N3); (b)–(e) fixed. `rulings.md` exists after the merge | `client_rendering.md::§4.1` `welcome` row; `contracts.md` |
| W F3 | fixed | `client_objects.md::§5.1` |
| W F4 | clamp fixed. The fold's added recount check is **open** | N1 |
| W F5 | fixed. Σ a_p ≠ 0 holds because 6.1 flips a segment whole (`fire_solid.md::§1.2`) | `fire_solid.md::§5.6` |
| W F6 | fixed | `client_objects.md::§3.1` |
| W F7 | fixed (text) | `§7.1`; `checklists.md::Step 7` |
| W F8 | fixed (contract). Mechanism note in N9 | `client_objects.md::§4.1` |
| W F9 | **open**. Partially done | N4, N5, N6 |
| W F10 | fixed (send rule, leak rule). Site residual, see N7 | `client_rendering.md::§4.1`; `fire_solid.md::§5.6` |
| W F11 | deferred to owner question 4, trigger "before step 8 builds its goldens" | `client_objects.md::§7.3` |
| W F12, F13, F14 | fixed | `§7.2`, `§3.4`, `§3.1`/`§5.1` |
| E-B1 | fixed | `§4.1` per-instance RGBA8 texture |
| E-B2 | fixed (text). The measure was not rerun by the author | `§7.2` |
| E-S1, S2, S3, S5 | fixed | `§2`, `§6.1`, `§4.2`, `fire_solid §5.6` |
| E-S4 | clamp fixed. Recount check **open** | N1 |
| E-N1–N6 | fixed | `§7.2`, `§2`, `§7.1` |
| C B1 | fixed | `§4.1` |
| C S1–S6 | fixed | `§4.2`, `§7.2`, `§6.1`, `§5.2` |
| C S7 | fixed. The claim is removed; the head-on readout is a step 8 fixture mechanism | `§2` |
| C N1–N7 | fixed | `§4.2`, `§4.3`, `§2` |
| P-S1–S6, P-N1, P-N2 | fixed | `§3.2`, `§4.1`, `§7.4`, `client_rendering §4.3`, `fire_solid §5.6`, B5 |
| P-N3 | **open**. fold.md says "P-N1–N3 folded" and also "the probe itself wasn't changed". §2 states neither median nor exclusions. NIT, mechanism | `fold.md`; `client_objects.md::§2` |
| Bio S1–S4, N1, N2 | fixed | `fire_solid §5.6`; `§5.4`; `§4.3`; lesson 32; `§10` |

## 2. Contract table (what the fold adds or changes)

| Contract | Owner | Producers | Consumers | Delta |
|---|---|---|---|---|
| `snapshot.channels` (`material region crack temperature_c`) | `client_rendering.md` §4.2 | `encoding.snapshot` (sends `glow`, no `region`); `client_fixtures.py` (sends `surface_glow`, `burning`) | `cell_snapshot.gd::CHANNEL_BYTES` (requires `surface_glow`, `burning`) | newly registered. Every shipped producer and consumer disagrees until steps 7 and 8 (N2) |
| fuel tables, columns, dtypes, units | `client_objects.md` §3 | step 7 encoder (none yet) | step 7 decoder, step 8 `Fuel` pass | new. Refusal rule defective (N1) |
| fuel view and `fuel_version` | `fire_solid.md` §5.6 | step 7 (with the encoder) | encoder; the send rule | new. No site, no plan dependency on 6.0b (N7, N8) |
| send rule | `client_rendering.md` §4.1 | server send loop | B5 | gains `fuel_version` |
| bump rule for tables and object kinds | claimed to be `client_rendering.md` §4.1's | — | every reader | §4.1 doesn't state it (N3) |
| crack-severity rule | `client_objects.md` §6.1, "replaces" §5.4's half | step 8 shader | `golden_measures` | §5.4's width rule is not removed (N4) |
| burning and flames in goldens | `client_objects.md` §5.2–§5.3, §7.2 | step 8 | §7.2 checks | contradicted by `client_rendering.md` §5.3 (N5) |
| tier flame knob | `client_rendering.md` §5.5 | tier resources | the flame pass | particle counts for a pass that no longer uses particles (N6) |
| join cap | `client_rendering.md` §4.3 | server | — | counts the fuel tables at the limits. Arithmetic checked: 356,000 B; 552,336 cells |
| frame bytes | §4.2 (6 B per cell), `client_objects` §3.5 (tables) | — | B5 | checked: 16/36/52/11 B per row; 1,738,400 B |

## 3. New findings (introduced by the fold's text)

**N1. BLOCKER (contract): `client_objects.md::§3.2`, the last decoder check, `segment_count ≠ ⌈L/ℓ − 10⁻⁶⌉` "computed in f64 from the f32 columns".**
- **Defect.** The tolerance is absolute, but the error is relative. Both f32 inputs carry about 6×10⁻⁸ of relative error, so the ratio's error grows with the segment count n, and 10⁻⁶ is too small once n is above about 10.
- **Measured** (numpy, ℓ = f32(0.02), L = f32(mm/1000), true count ⌈L/ℓ⌉ in exact decimal):
  - 42 of 1,981 lengths from 20 to 2,000 mm are refused.
  - That includes 0.36 m (ratio 18.0000011), 0.54 m and 0.60 m. Round 1 F4 already listed those three as examples.
  - At L = 2.0 m the ratio reads 100.0000022, so the check computes 101 against the true 100.
  - Up to 10 m, 326 lengths are refused.
- **The cited evidence is wrong.** The text says "`wire_integrity.md` F4 measured 19 of 1,981 lengths off without it". That number was the f32 recount. With this check, 42 valid lengths are refused. F4 had recommended "no f32 recount check".
- **Failure scenario.** A scene with a 0.36 m stick or a 2 m slab sends a valid frame. The decoder refuses every frame from then on, and the client draws nothing.
- **Fix** (verified only for 20–2,000 mm in 1 mm steps at ℓ = 0.02 m): a relative tolerance, ⌈r − r·2⁻²²⌉ with r = L/ℓ, gave 0 mismatches. Alternatively, drop the recount and keep the clamp, as F4 proposed. That alternative is unverified.

**N2. SHOULD-FIX (contract, interface): the decoder-to-renderer seam between step 7 and step 8 is broken by the fold's sequencing.**
- `cell_snapshot.gd`'s header says "step 7's decoder will fill the same object from a wire frame". Its `problems()` requires `surface_glow` and `burning` channels and a positive `glow_scale_c_per_count`.
- The fold makes v0 carry neither (FIELDS.md: "step 7 never sends them") and leaves their removal from the renderer to step 8 (B42's trigger). Step 7's checklist doesn't touch `CellSnapshot`.
- The interim channels have also lost their owner. §4.2 no longer lists them, yet:
  - `client_fixtures.py:41` says "surface_glow's calibration as client_rendering.md §4.2 gives it";
  - `cell_snapshot.gd:13` cites §4.2;
  - B42 says the renderer reads them "per `client_rendering.md` §4.2".
- **Failure scenario.** Step 7 wires its decoder into `CellSnapshot`, and every v0 frame fails `problems()` ("no surface_glow channel"). Or step 7 quietly edits `CHANNEL_BYTES` with no spec, and the fire fixture and the glow check break outside B42's ledger.
- **Fix (unverified).** Either step 7's checklist owns `CellSnapshot`'s required set for v0, or B42 and FIELDS.md become the interim owner and the code comments are relinked.

**N3. SHOULD-FIX (contract): `client_objects.md::§3.1` "Versioning" attributes to `client_rendering.md` §4.1 a rule §4.1 doesn't state.**
- §4.1's bump list is "a new encoding, dtype, `kind` or compression bumps the protocol", plus "an optional channel bumps the registry". It names neither tables nor object kinds.
- Its `kind` is the frame kind (`full`, `delta`), not the object-kind vocabulary in `welcome`.
- So "adding a required table or a new object kind is a protocol bump (§4.1's rule)" and "optional `flames` … bumps only the registry" are new contract stated only in the design, under a citation that points elsewhere. This is A-N2 and W F2(a) again.
- **Failure scenario.** 6.2 reads §4.1, finds no table rule, and adds `beds` (a required geometry table for a new kind) under a registry bump. The catalogue hash then differs from an old client's expectation only after connect, and it refuses every frame.
- **Fix (unverified).** State the table and object-kind rules in §4.1's "Extension and bumps", and link from §3.1.

**N4. SHOULD-FIX (contract, B36): the crack-severity rule now has two statements.**
- `client_objects.md::§6.1` "replaces the severity half of `client_rendering.md` §5.4".
- But §5.4 still states the old law: w = max(0.02 m × c, …), "~12 px polygons (cell × 2ⁿ, held)", and "At c = 1 the groove is 2.9 px".
- The fold only appended "Severity shows by edge density". §6.1 rule 4 also restates §5.4's floors (1.5 px, 12 px).
- **Failure scenario.** Step 8 builds §5.4's groove-width law with held polygon size, which is what its owner section says, and passes. §6.1's "coarser octaves for milder severity" is never built, and nobody can say which section is wrong.
- **Fix (unverified).** Cut §5.4's severity terms to a link, and state the floors in one place.

**N5. SHOULD-FIX (contract): `client_rendering.md::§5.3` now says "Burning and flames: `client_objects.md` §5.2–§5.3. Visual only, and off in goldens."**
- That contradicts `client_objects.md` §5.3 (only *flicker* is off in goldens) and §7.2, whose Burning and Flame-shape rows measure ignited brightness and flame-ID pixels in the renderer goldens.
- The old line made only the particles and flicker golden-off. The fold's rewrite widened it to burning.
- **Failure scenario.** Step 8 follows §5.3 and disables flames in golden runs. The Flame-shape row then can never pass, or it gets dropped.
- **Fix (unverified).** "Flicker off in goldens", with a link.

**N6. NIT (contract, stale copies; part of A-S2 and W F9):**
- `client_rendering.md::§5.5` still has a "Flame particles" column (64/256/1,024), and `§7`'s scene tree still has "Flames → GPUParticles3D" and no `Fuel` node. §5.3 of the design draws Phase 1 flames as camera-facing volumes, with no tier knob.
  - Failure: the laptop tier caps particles for a pass that has none, or step 8 builds particles to satisfy §5.5, and the tiers' flame masks diverge.
- `standards_backlog.md::B40` (2) still cites "Flame particles (§5.3)".
- `standards_backlog.md::B42` still restates wire dtypes ("`surface_temperature_c` f16, `ignited_fraction` u8") as `fire_solid.md` §5.6's. §5.6 no longer states them, so this is now a second, unowned copy of §3.3. B42 also still says "§4.2's rows take fire_solid's names", but the rows were removed.
- `boundaries.md::§8.3` still names a `glow` quantization.
- `client_objects.md::§3.2` cites "(question F2)" and `§8` claims fire_solid §5.6 holds "its site … and questions F1–F3". §5.6 holds neither, and the checklist's questions carry no labels.
- `client_objects.md::§5.1` says the glow "start and span become client constants". The curve has no span; `GLOW_FULL_C` was only the u8 encoding's.

**N7. SHOULD-FIX (contract): the fuel table geometry is frozen ahead of its owner's open questions, and those questions sit in the wrong step.**
- `checklists.md::Step 8` asks fire_solid's owner, "before the fuel tables freeze", three things: does the last segment take the remainder, which slab face carries the segments, and is a rod's origin its axis's start.
- But the tables freeze at **step 7**. Step 7's list doesn't carry these questions.
- `client_objects.md::§3.2` already answers two of them as contract:
  - "segment k spans [kℓ, min((k+1)ℓ, L))" with count ⌈L/ℓ⌉, which assumes the remainder is a short last segment;
  - "`origin` … the axis's start, where segment 0 begins".
- **Failure scenario.** fire_solid's owner answers "the last segment takes the remainder" after step 7 freezes v0. Then the count formula, the span rule, the decoder check (N1) and the shader's clamp are all wrong, and fixing them is a required-semantics change after freeze.
- Relatedly, `fire_solid.md::§5.6` names no site for the view (`Frame`, `CellFrame` or its own type). Under tile §4, where the cells part is "published when cells' version changes", that leaves `fuel_version`'s carrier unstated. The leak rule is still sound in practice: `bridge.py` types against `FrameSource.latest -> Observation`, so mypy refuses an attribute read.
- **Fix (unverified).** Move the questions to step 7's list (or 6.0b's), and mark §3.2's two answers as provisional until they are answered.

**N8. SHOULD-FIX (contract, plan interface): step 7 now builds the fuel view, but the plan doesn't order step 7 after 6.0b.**
- `fire_solid.md::§5.6`: "Step 7 builds it with its caller, the encoder".
- `foundations_plan.md` row 7's dependencies are "5b, 2, 0d". Row 6 (6.0b, the FuelStore) depends on 5a and 5b. The two run in parallel.
- **Failure scenario.** Step 7 lands first. It must either build the view over a FuelStore that doesn't exist, or freeze v0 with required fuel tables that no producer fills. The view would then reach the shipped path only through fixtures, which breaks "a fix ships with a caller".
- **Fix (unverified).** Add 6.0b to row 7's dependencies, or say what step 7 encodes when 6.0b is absent.

**N9. NIT (mechanism; defer to step 8, trigger: the `Fuel` node's build): `client_objects.md::§4.1` "Transforms stay in the server's frame."**
- Godot computes a MultiMesh's AABB from the instance transforms. If the z-up to y-up mapping exists only in the vertex shader, the culling box is in the wrong frame, and visible objects may be frustum-culled.
- Either a custom AABB or the node transform resolves it. Running it will decide.

**N10. NIT (contract): `client_rendering.md::§4.3`'s join cap counts "the fuel tables at the world limits", but nothing says Phase 2's optional `flames` table joins that count when it lands.** P-S4 gave 425,669 cells with the flame bound. The trigger is 6.2's design.

## 4. Contract or mechanism, for "When the rounds stop"

- **Contract:** N1 (BLOCKER), N2, N3, N4, N5, N7 and N8 are about formats, interfaces, leak rules and plan ordering. They fold, or the owner overrules them.
- **Mechanism:** N9 and P-N3 can move to step 8 as deferred. N6 and N10 are stale text that only needs editing, plus one 6.2 trigger.
- **New blockers in fold-added text:** one, N1, and it is contract. Under the charter that triggers the stop rule for mechanism findings only.
