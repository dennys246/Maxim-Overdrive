# Step 2 pre-push review: Client and rendering

Range `origin/main...aa5fcfa` (phase1/godot-skeleton). Reader: Client and rendering lens (`docs/code_review.md`).

**Counts:** 1 BLOCKER, 3 SHOULD-FIX, 4 NIT.

## What I ran

All Godot runs used 4.7.2.stable.official.ed1daf0bf on the M2, on a copy of `client/` under `build/s2c-review/`, with
`HOME` and `XDG_*` inside that directory. The copy was deleted afterwards.

- `--headless --import`, then `-s res://tests/run.gd`: `client-tests: PASS 6 tests`, rc 0.
- `.venv/bin/python scripts/godot_check.py`: `PASS`.
- **Warning inventory**, on a blank project with every setting at its default: 49 `TYPE_INT` keys under
  `debug/gdscript/warnings/`, plus `enable` (bool), `renamed_in_godot_4_hint` (bool) and `directory_rules` (a
  Dictionary, default `{"res://addons": 0}`). Diffed against `project.godot`: the same 49 names, all at 2.
  `rendering_method.web` defaults to `gl_compatibility`.
- **Probe re-runs:**
  - compile failure: a broken script loads non-null with `can_instantiate()` false, and a missing file loads null.
    Confirmed.
  - `res://addons` exemption: an untyped `var` under `addons/` loads and can be instantiated with
    `untyped_declaration=2`, and fails outside `addons/`. Confirmed.
  - JSON integers: the output matches `godot_probes.md`. Confirmed.
  - headless capture: with the headless guard removed, `golden.tscn` under `--headless` was still running after 15 s.
    The hang is confirmed, and with the guard in place the scene fails at once.
  - partial texture update: the API list matches. The timing does **not** match (S2C-S2).
- **Golden:** I rendered `golden.tscn` windowed on Metal-backed GL. Against the committed llvmpipe golden: mean ΔE
  0.009, p99.5 0.24, no blob (the claim in `godot_probes.md` reproduces). I then rendered seven mutations of
  `golden.tscn` and ran `golden_compare.compare` against the unmutated Mac frame (table in S2C-S3).
- **Sentinel:** I added a suite to the copy with an `await` test and a test that checks nothing (S2C-B1).
- **Not run:** the Docker image and the Linux golden job; the RG8, focus, Origin and GPU-time probes.

## BLOCKER

### S2C-B1: a test that awaits can fail without the sentinel changing

`client/tests/run.gd::_run_suite` (`suite.call(method_name, t)`).

**Scenario (ran):** this suite, added to the copy:

```gdscript
func test_awaits_then_fails(t: TestContext) -> void:
	var tree: SceneTree = Engine.get_main_loop() as SceneTree
	await tree.process_frame
	t.check(false, "after an await")
```

The run printed `client-tests: PASS 8 tests` and exited 0, with no `ERROR` line anywhere in the log. `call()`
returns at the first `await`, `_initialize` prints the summary and quits, and the check after the await never runs.
Neither the sentinel nor the `SCRIPT ERROR` scan can see the failure.

This matters soon. Step 7 (net) and step 8 (rendering) tests need frames, and the first of them to await becomes a
test that cannot fail, which CLAUDE.md makes a BLOCKER. Nothing in the gate stops anyone writing one, and no fixture
proves the gap is closed.

The same run shows a second hole: `test_checks_nothing(_t)` counts as a passing test.

**Fix:**
- Make `_initialize` drive the tests as a coroutine: `await` each `suite.call(...)` and print the summary only after
  the last one, or refuse any test whose `call()` returns a `GDScriptFunctionState`.
- Have `TestContext` count checks per test, and fail a test that made none.
- Add both cases as fixtures in `tests/test_godot_gate_fixtures.py`, and prove each by deleting the fix.

## SHOULD-FIX

### S2C-S1: the golden key drops the LLVM version and the Ubuntu package revision

`scripts/golden_compare.py::golden_key` / `RENDERER_LINE`.

llvmpipe's pixels come from LLVM's JIT, not only from Mesa's source version. The log line already names both:
`Mesa 25.2.8-0ubuntu0.24.04.4 ... llvmpipe (LLVM 20.1.2, 256 bits)`. The key keeps only `25.2.8`.

The Dockerfile does not pin `libllvm20` explicitly. Only the snapshot date fixes it. **Scenario:** a `SNAPSHOT` bump
brings a new LLVM point release or a new Ubuntu Mesa revision. The key stays `compat-llvmpipe-mesa25.2.8-godot4.7.2`,
so the new build is compared with goldens the old build drew. That is exactly what the module docstring says "can
never" happen.

**Fix:**
- Key on the full Mesa package version and the LLVM version, for example
  `compat-llvmpipe-mesa25.2.8-0ubuntu0.24.04.4-llvm20.1.2-godot4.7.2`, read from the same log line.
- Optionally pin `libllvm20` in the Dockerfile.

### S2C-S2: the §8 erratum's 294 µs upload does not reproduce

`docs/design/client_rendering.md` errata (§8 bullet); `docs/design/research/godot_probes.md` (Partial texture
update; "Spec claims", item 6).

I ran `probe_texture_update.gd` four times on the same M2 and build. The minimum of 50 was 194, 194, 193 and 193 µs,
with first runs of 205–213 µs. That falls inside the 160–230 µs range the errata block says to override. The erratum
rests on one run, which was probably on a loaded machine (other sessions run concurrently).

**Scenario:** step 7 sizes its upload budget from a 2.4 ms figure, about 40% pessimistic. Worse, the errata block
now "overrides" a spec number that was right.

**Fix:**
- Report the measured spread across several runs, with the machine's load noted.
- Drop the §8 erratum, or reword it to "measured 193–294 µs".
- `godot_probes.md` item 6 needs the same correction.

### S2C-S3: the golden cannot see a whole-object colour change

`client/tests/golden.tscn` (composition) together with the §6.2 thresholds in `scripts/golden_compare.py`.

Of the Mac frame, 88.7% is the flat background. The crate is 3,220 px, 0.35% of the frame. I mutated the scene and
compared each frame with the unmutated one:

| Mutation | mean | p99.5 | largest blob (px) | Verdict |
|---|---|---|---|---|
| crate moved 5 cm | 0.016 | 0 | 167 | FAIL |
| crate moved 10 cm | 0.035 | 0 | 367 | FAIL |
| crate 0.6 → 0.5 m | 0.047 | 0 | 980 | FAIL |
| crate albedo r 0.62 → 0.58 (about ΔE 5 over the whole crate) | 0.017 | 0 | 0 | **PASS** |
| wall albedo b 0.6 → 0.5 | 0.48 | 15.6 | 28,155 | FAIL |
| `shading_mode` unshaded → per-pixel | 4.94 | 53.3 | 104,137 | FAIL |
| ortho size 10 → 10.5 | 0.50 | 45.9 | 11,812 | FAIL |

Geometry regressions are caught well. A colour or shading regression of ΔE below 10, confined to any object under
0.5% of the frame, passes. The percentile cannot see that much area, and the blob rule needs ΔE above 10. Step 8's
glow and crack colour work lives at exactly that scale. §6.4's L* checks cover only G2 and G3, not the renderer
goldens.

**Fix (design, not a loosening):**
- Frame the golden so the scene fills the view: a floor that covers the frustum, the camera centred on the crate as
  §1 says.
- Raise with the spec author a per-object mean-ΔE rule over the ID mask, the debug pass §6.4 already plans, so that
  small objects are judged on their own pixels.
- Record the blind spot in `golden_compare.py`'s docstring until the fix exists.

## NIT

- **S2C-N1** `client/tests/golden.gd::_place_camera`: the camera looks at `Vector3.ZERO`, but §1's golden camera is
  "centred on the crate" (0.9, 0.3, 0.5). The docstring cites §1 as if it matched. Either centre the camera on the
  crate or say this camera differs.
- **S2C-N2** `client/tests/unit/test_project_settings.gd::test_the_renderer_is_compatibility` and
  `tests/test_client_project.py::test_the_renderer_is_compatibility_on_every_platform`: `rendering_method.web` is
  neither set nor checked. It is `gl_compatibility` only by default, so an upgrade that changes the default goes
  unseen. Set it in `project.godot` and assert it in both tests. Separately,
  `rendering/gl_compatibility/fallback_to_angle=true` means Windows may draw through ANGLE/D3D11. That is still
  Compatibility, but say so in §7.4.
- **S2C-N3** `client/tests/run.gd::_initialize`: `DirAccess.get_files_at(UNIT_DIR)` is not recursive, so a suite in
  `unit/<subdir>/` never runs and nothing says so. The runner also pins no expected suite count, so a deleted suite
  only lowers `PASS <n>`. Recurse, or have `godot_check.py` refuse a `test_*.gd` file outside `unit/`'s top level.
- **S2C-N4** `ci/godot-golden/run.sh`: Godot runs the golden scene without `--headless --import` first. That works
  today only because `golden.tscn` uses no `class_name` and imports no assets. The first golden that uses a texture
  or `EnginePin` will fail with "Could not find type" or a missing import. Import first, as `godot_check.py` does.

## Checked with no finding

- `project.godot`: 49 of 49 warnings at Error (an exact match with the engine's list), `directory_rules={}`, and
  Compatibility on desktop and mobile.
- The live warnings test fails when an upgrade adds a warning: the new key would sit at its default.
- Every committed `.gd` file loads under `untyped_declaration=2` and `inferred_declaration=2` through the gate.
- `golden_compare`:
  - the CIE76 conversion is D65 and matches the reference values;
  - the thresholds are mean ≤ 1.0, p99.5 ≤ 4.0 and blob > 64 px at ΔE > 10, with 4-connectivity;
  - it refuses any width but 256 and any device but llvmpipe.
- Goldens are keyed by Godot and Mesa (subject to S2C-S1) and sit under `.gdignore`.
- Every errata item except §8 matches the code (§7.2, §7.3, §6.1, §6.5, §9). CR-B3 is correctly left open.
- No colour-alone state exists at step 2.
