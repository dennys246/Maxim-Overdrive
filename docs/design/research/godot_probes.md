# Godot 4.7.2 probes (step 2; client_rendering.md §9, EX-S14)

**Status:** measured 2026-11-19 on the owner's M2 with `/Applications/Godot.app` (4.7.2.stable.official.ed1daf0bf),
and in the golden image (`ci/godot-golden/Dockerfile`: Ubuntu 24.04, Mesa 25.2.8-0ubuntu0.24.04.4, LLVM 20.1.2)
under Docker Desktop's x86-64 emulation (`/proc/cpuinfo`: "VirtualApple @ 2.50GHz", AVX2 and FMA reported).
Nothing here ran on a GitHub runner; what only CI can show is listed at the end.

Each probe that can be rerun is committed under `client/tests/probes/` with its command in the header comment, so
the Godot upgrade branch reruns them. The gate loads them (they are typed like all client code) but doesn't run them:
most need a window.

## Results

| §9 item | What ran | Observed | Verdict |
|---|---|---|---|
| No `Origin` | `probe_ws_origin.gd` connecting to a Python socket on port 0 that printed the handshake | `GET /`, `Host`, `Upgrade`, `Connection`, `Sec-WebSocket-Key`, `Sec-WebSocket-Version`; no `Origin` | holds |
| Integers from `JSON.stringify` | `probe_json_ints.gd`, headless | `int(5500)` → `5500`; `5500.0` → `5500.0`; `parse_string` returns floats | holds, with a reader caveat |
| `FORMAT_RG8` + `texelFetch`, u16 ids | `probe_rg8.tscn`: all 65,536 ids, one pixel each | 0 wrong on Metal-backed GL and on llvmpipe; 65,280 wrong with the `g` term deleted | holds |
| `frame_post_draw` capture | `golden.tscn` under Xvfb in the image | the first frame is byte-identical to the tenth; under `--headless` the await never returns | holds under Xvfb; hangs headless |
| llvmpipe, fixed vector width | the golden at 256, 128 and unset | the renderer's name reports the width; all three frames byte-identical | width pin works; two CPU types not tested |
| GPU time | `probe_gpu_time.gd`, `--gpu-profile` | GPU meter 0.0 ms on the Mac; `--gpu-profile` prints `GPU PROFILE (total 0.0ms)` | fails on Compatibility |
| Keys on focus loss | `probe_focus.gd`, W pressed by event, Finder activated from a shell | W released at `FOCUS_OUT`; a spurious OUT/IN pair at launch | holds |
| `class_name` on a fresh checkout | a two-file project, `-s` before and after `--import` | before: `Could not find type "Foo"`; after: runs | needs `--import` |
| Partial texture update | `probe_texture_update.gd`: the API list, then 50 timed updates at 120 × 40 × 48 R8 | no partial 3-D update exists; whole update 294 µs (Mac), 69 µs (llvmpipe) | whole-texture |

## The probes in detail

### No `Origin`
`WebSocketPeer.connect_to_url("ws://127.0.0.1:<port>")` with `handshake_headers` never set sends no `Origin`. The
defaults the review recorded are confirmed: `inbound_buffer_size` 65,535 and `max_queued_packets` 4,096. The server
still refuses any `Origin` (realtime §5); step 7's listener test makes this a standing guard.

### Integers on the wire
`JSON.stringify` writes an `int` as `5500` and a `float` as `5500.0`, so §3's `int()` cast before stringify is
required, not cosmetic: a float that reaches the encoder becomes `5500.0`, which an integer-only validator must
refuse. The reverse direction is the caveat: `JSON.parse_string` turns every number into a float, so `9007199254740993`
comes back as `9.007199e+15`. Every integer the client reads from a `tick` message (ticks, mm, ids, versions) must be
cast back with `int()`, and nothing on the JSON path may exceed 2^53. Step 7's decoder tests should hold both.

### `FORMAT_RG8` and `texelFetch` for u16 region ids
The probe uploads the wire's own bytes (`PackedByteArray.encode_u16`, little-endian) as 16 slices of 256 × 16 RG8 in
an `ImageTexture3D`, and a spatial shader decodes `round(r·255) + 256·round(g·255)` with `texelFetch` at each
fragment's index. Every one of the 65,536 ids decodes to itself on the M2 (OpenGL 4.1 over Metal) and on llvmpipe.
Proved by deletion: dropping the `256·g` term leaves 65,280 pixels wrong, exactly the ids at or above 256. So
§4.2's upload stands, the fallback (two R8 textures) is not needed, and the bytes go up without reshuffling.

### `frame_post_draw` capture
Under Xvfb the frame captured after the first `await RenderingServer.frame_post_draw` is byte-identical to one
captured after ten, so waiting longer buys nothing. Two reruns of the golden in the image are byte-identical.

Under `--headless` the await never returns: the scene hung until the outer timeout, so §6.1's "asserts `get_image()
!= null`" is never reached there. `client/tests/golden.gd` refuses a headless display before awaiting, and
`ci/godot-golden/run.sh` wraps Godot in `timeout 120`.

### llvmpipe with a fixed vector width
`LP_NATIVE_VECTOR_WIDTH=256` takes effect: llvmpipe's device name says `llvmpipe (LLVM 20.1.2, 256 bits)`, and 128
gives `128 bits`. `scripts/golden_compare.py` reads that name from the run's log and refuses any width but 256, so a
runner where the variable is lost fails loudly instead of drawing subtly different goldens. Unset, the width defaulted
to 256 on this emulated AVX2 host.

What this did not show: the step-2 golden is flat and unshaded, and its frames at 128 and 256 bits are
byte-identical. It cannot tell the widths apart, so it doesn't yet prove the pin matters; step 8's shaded goldens are
where width and FMA differences can show. "One golden on two runner CPU types" needs GitHub's pool: `run.sh` prints
the CPU model of every run, so the job's history will show whether Intel and AMD runners agree.

### GPU time
On Compatibility (Mac), `viewport_get_measured_render_time_gpu` reads 0.0 ms over 120 frames, as the review found,
and `--gpu-profile` exists but prints `GPU PROFILE (total 0.0ms)` with no entries: it measures nothing on this
renderer. On llvmpipe the GPU meter returns numbers, but the maximum (1,232 ms) is the first frame's shader JIT, not
GPU work. The fallback works: the minimum uncapped frame interval with `--disable-vsync` reads 688 µs for one box on
the Mac. §8's frame-time rows stay "reported" and use the minimum frame interval.

### Keys on focus loss
With W held through `Input.parse_input_event`, activating Finder from a shell gave `FOCUS_OUT` at frame 128, and
`Input.is_physical_key_pressed(KEY_W)` was already false inside that notification. So the engine releases held keys
itself, and the client's own `move {dir: null}` on focus out (CR-N3) is belt and braces. Godot also sends a
`FOCUS_IN`, `FOCUS_OUT`, `FOCUS_IN` burst at frame 0, before any scene logic runs; the client's focus-out handler
will fire once at launch and must be harmless then (it is, if it sends only after `welcome`). An earlier attempt to
activate Finder from inside Godot (`OS.execute("osascript", ...)`) exited 1 and never moved focus; only the shell
could.

### `class_name` on a fresh checkout
Without `.godot/`, `-s run.gd` fails with `Could not find type "Foo" in the current scope` and keeps running, so the
gate imports first (`--headless --import`), after which it runs. The import cache is not committed.

### Partial texture update
The engine has no partial 3-D texture update: `ImageTexture3D.update` and `RenderingServer.texture_3d_update` both take
every slice (the API listing shows only `texture_2d_update`, `texture_3d_update` and `texture_proxy_update`). A whole
update at the tile's shape (120 × 40 × 48 R8, 230 KB) takes a minimum of 294 µs over 50 runs on the M2 (first run
322 µs), and 69 µs on llvmpipe (first 963 µs). Whole-texture stays the plan.

## What the gate's own construction measured

These came from building `scripts/godot_check.py` and its fixtures (`tests/test_godot_gate_fixtures.py`):

- **Warnings:** 4.7.2 has 49 integer warning levels. All twelve that §7.2 and CR-S7 name exist, and the five §7.2
  says default to Warn (`unsafe_void_return`, `narrowing_conversion`, `integer_division`, `unused_variable`,
  `shadowed_variable`) do. `return_value_discarded` fires on `PackedByteArray.resize`, `Image.save_png` and the
  `append` of packed arrays (which returns a bool).
- **`res://addons` is exempt by default:** `debug/gdscript/warnings/directory_rules` defaults to `{"res://addons": 0}`.
  An untyped `var` in `res://addons/` loads clean with every warning at Error, and fails once `directory_rules` is
  `{}`. The engine half of the client lives in `client/addons/engine/`, so without this every engine script would
  have escaped the typing rule. `project.godot` sets `{}`; a fixture deletes the line and watches the check go quiet.
- **A script that fails to compile still loads:** `load()` returns a non-null `Script` whose `can_instantiate()` is
  false; `load()` is null only for a missing file. `load_all.gd` checks both, and counts an `@abstract` script as
  loaded.
- **The import is not a parse check:** `--headless --import` prints nothing for a script with a parse error, with or
  without `class_name`. Only loading every script finds them.
- **The import writes beside the sources:** a `.uid` file next to every script and shader, and a `.import` file next
  to every image it imports. The `.uid` files are committed (Godot's own advice); goldens sit under a `.gdignore` so
  they are not imported as game textures. The gate imports a copy and fails if the import created or rewrote any file
  outside `.godot/`.
- **The import costs 8–12 s** on the M2, warm or cold, most of it editor start-up. The fixtures import once per
  session and copy the result.
- **Errors in a method don't stop its caller:** a runtime error in a test method aborts that method, and the runner
  carries on and prints `client-tests: PASS`. Only the scan for `SCRIPT ERROR` catches it, so that scan is
  load-bearing, not a duplicate of the sentinel.
- **Per-user files:** Godot writes its log, editor settings, shader cache and `app_userdata` under `$HOME/Library` on
  macOS, and ignores `XDG_*` there; on Linux it reads `XDG_DATA_HOME`, `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` first.
  The gate and every test set all four inside their work directory or `tmp_path`, so nothing reaches the real home.
  The probes in this document ran the same way.
- **The golden image:** the Ubuntu archive drops a package version once it is superseded, so a version pin alone
  breaks within weeks; the image installs from `snapshot.ubuntu.com` at a fixed date. The base image has no CA
  bundle, so its first `apt-get update` skips TLS peer checks, which is safe because apt verifies every index against
  the archive key, and installs a pinned `ca-certificates` before anything else.

## Spec claims these probes refute or correct

1. **§7.3 "loads every `.gd` and fails on a null `load()` [ran]".** A script that fails to compile loads as non-null.
   The check must be `load() == null or not can_instantiate()` (abstract scripts excepted).
2. **§7.2 "every warning is set to Error".** Not enough on its own: 4.7.2 exempts `res://addons`, which is where §7.1
   puts the engine half. `directory_rules` must be emptied, and a test must hold it.
3. **§6.1 "asserts `get_image() != null`".** Under `--headless` the capture's await never returns, so the assert is
   never reached; the scene must refuse a headless display first, and every call needs an outer timeout.
4. **§9 "GPU time: `--gpu-profile` [ran: exists]".** It exists but reports nothing on Compatibility. The frame-time
   rows stay "reported" on the uncapped minimum frame interval.
5. **§7.3 fixtures in `client/tests/gate_fixtures/`.** A broken fixture inside the gated project fails the gate by
   design. The fixtures are built in `tmp_path` by `tests/test_godot_gate_fixtures.py` instead.
6. **§8 upload estimate.** "About 1.7 ms derived from the measured 160–230 µs per channel": this run measured 294 µs
   per R8 channel (minimum of 50) on the same M2, so seven uploads with `region` at two bytes are about 2.4 ms, still
   under the 3 ms target but with less room than §8 says.
7. **§6.5 "Mesa pinned by package version".** Necessary but not sufficient: without a dated snapshot the pinned
   version disappears from the archive.
8. **§6.5 golden paths `compat-llvmpipe-mesa<version>`.** Keyed as the flexibility review asked,
   `compat-llvmpipe-mesa25.2.8-godot4.7.2/`, and derived from the run's own log so the key can't lie.

## What is not verified until CI runs

- **The golden on a real x86 runner.** The committed golden was drawn under emulation on Apple silicon. llvmpipe's
  JIT reads CPU features, and Rosetta's report may differ from a GitHub runner's. For this flat scene the risk is
  small (the Mac's Metal frame passes against it at mean ΔE 0.009), but the first `golden` run is the real check;
  if it fails, take the golden from that run's artifact in a commit of its own.
- **Two runner CPU types agreeing** (above).
- **Godot on `ubuntu-latest` and `macos-latest`.** `ci/install_godot.sh` verified the macOS build locally; the Linux
  build ran only inside the image. Headless Godot on a bare runner, and the gate's fixture tests there, run for the
  first time on push.
