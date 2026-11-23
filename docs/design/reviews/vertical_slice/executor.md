# Executor review: phase1/vertical-slice (`origin/main...HEAD`, spikes/slice/)

**Summary.** All 129 slice tests pass (51 s, and 74 s with coverage). Branch coverage of `slice_server` is 92%. The Godot scripts (`main.gd`, `net.gd`, `voxels.gd`) parse cleanly with `--check-only`. Most of the lane works on its shipped path: the wire refusals, the intent parsing, the config refusals, the fire's energy balance, the heat-debt closed form and replay all hold, and most of the mechanisms I broke turned their tests red. I found three ways to crash the server, each confirmed by a probe:
- the voice's fallback misses several real failure types, and the exception kills the server loop;
- a kindle and a vendor douse in the same tick crash the simulation;
- a peer that disconnects in the middle of a batch trips an assertion.

Two more are SHOULD-FIX:
- the voice's latency telemetry leaves out time spent queued;
- `Voice.ready` has a race that drops lines.

Three tests cannot fail for a rule they should guard. The entry point (`serve`, `main`) and the real Ollama call never run under a test, and that untested code is where the BLOCKER lives.

**Counts: 1 BLOCKER, 8 SHOULD-FIX, 6 NIT.**

All probes are in `<scratchpad>/probes/`. The mutation copies are in `<scratchpad>/mut/`. Nothing in the repository was modified.

---

## BLOCKER

### B1. `slice_server/voice.py::ollama.ask`: the fallback misses common failures, and the exception crashes the server
- **Defect.** `ask` catches only `URLError`, `TimeoutError` and `JSONDecodeError`. Several real failures get past it:
  - `urllib` wraps only errors raised while *sending* the request. Errors raised while reading the response escape: `http.client.RemoteDisconnected` and `ConnectionResetError`, which are `OSError`s, and `http.client.IncompleteRead`, which is an `HTTPException`.
  - A non-UTF-8 body raises `UnicodeDecodeError`, which `json.loads` does not turn into `JSONDecodeError`.
- **How it crashes.** `_speak` catches only `VoiceFailed`, so the exception is stored in the Future. `Voice.ready()` calls `f.result()`, which re-raises it inside `Server._deliver_lines`. Nothing in `Server.run` catches it, so the session ends.
- **The claim it breaks.** The docstring says: "Any failure (the server is down, the call times out, the reply is malformed or empty) falls back to a canned line." That is false on the shipped path.
- **Failure scenario.** Ollama restarts, is OOM-killed, or unloads the model mid-generation during a Mac mini playtest. The server dies with `RemoteDisconnected` at the next loop pass.
- **Verified.** `probes/voice_reset.py` runs a localhost fake that closes without replying, sends a truncated body, and sends a body that is not UTF-8. `ready()` raised `RemoteDisconnected`, `IncompleteRead` and `UnicodeDecodeError` respectively.
- **Coverage.** `ollama()`'s body (voice.py lines 54–67) is not covered by any test. The tests inject a fake `ask`.

## SHOULD-FIX

### S1. `slice_server/sim.py::Sim._vendor_step` and `Sim._apply`: a kindle and a douse in the same tick crash the simulation
- **Defect.** `_take(Kindle)` sets `fuel.burning = True`, but the world's source is added only later, in `fire.step`. `_vendor_step` runs in between. It sees a burning fire at 0 W, which counts as small. If the vendor is within `douse_reach_m` and has a charge, it calls `fire.douse` and then the applier's `Extinguish`. The applier refuses because there is no `fire:<region>` yet, and `_apply` raises `RuntimeError`.
- **Failure scenario.** With `vendor.charges: 2`, which is a week-4 tuning knob: the vendor douses the crate, and the player kindles the crate again while the vendor is still standing next to it. The result is `RuntimeError: the applier refused the fire's Decision(region='crate', power_w=0.0, out=True): nothing is burning on the crate`.
- **Shipped data.** With `charges: 1` I found no way to trigger it, because the only douse spends the only charge. One tuning change exposes it.
- **Second consequence.** The exception escapes mid-tick, after the kindle has changed the fire. `serve` then logs an `end` digest of that half-applied state, and `ticks_of` replays `range(end.tick)`, which drops the crashing tick's intents. So the crash cannot be replayed: the bug report loses the intent that caused it.
- **Verified.** I ran two inline probes. One put the vendor at (5.5, 3.3) and kindled. The other set `charges=2`, waited for the douse (tick 4), then kindled again. Both crashed.

### S2. `slice_server/server.py::Server._read`: a client dropped in the middle of a batch trips an `AssertionError`
- **Defect.** `_read` iterates `self._client.reader.feed(data)` as a generator. Any `_handle` can lead to `_drop`, for example an error reply whose `_flush` gets `BrokenPipeError`. When that happens, the generator still yields the next frame, and `_handle` runs `assert self._client is not None`.
- **Failure scenario.** The client sends several frames and closes. The first reply's send fails, and the second frame raises `AssertionError` out of `Server.run`, which crashes the server.
- **Verified.** `probes/drop_mid_batch.py` used a socketpair: two bad intents, then the peer closed. The output was "client dropped: send failed: Broken pipe" and then `CRASH AssertionError`.
- **Coverage.** The `recv`/`send` `ConnectionError` paths (server.py lines 194–196 and 255–259) are uncovered.

### S3. `slice_server/sim.py::Sim._check_fire_fits_the_limits` and `Sim._strike`: strike parameters are never checked against the action limits
- **Defect.** The comment at the strike reads "reach and limits were checked here: a refusal is a bug". Only the fire's radius and power are checked at startup. `strike.energy_j`, `overdrive_energy_j` and `sigma_m` are not.
- **Failure scenario.** `body.yaml` with `strike.sigma_m: 0.1` passes `config.parse_body`, which checks only that the value is positive, and `Sim()` constructs. The first strike then raises `RuntimeError: ... sigma_m must be between 0.2 and 2, got 0.1` mid-tick. That crashes the server, and the tick's replay is lost the same way as in S1.
- **Verified.** Inline probe.
- **Coverage.** The existing limit-refusal branches (sim.py lines 64 and 67) are also uncovered.

### S4. `slice_server/voice.py::Voice._speak`: the latency telemetry leaves out queue wait
- **Defect.** `start = time.monotonic()` is taken when the single worker *picks up* the request, not when `request` submits it. Every vendor state change submits a request. Under load each call can take up to 2.5 s, so requests queue up. The line the player sees arrives late, and its state can be stale, but `latency_s` records only the model call.
- **Failure scenario.** The vendor goes flee, then idle, then warn inside 2 s while each call takes 2.5 s. The third line reaches the client about 7 s after its state change, yet it is logged as 2.5 s. §7's "LLM p95 latency" read from session logs would understate what players experienced.
- **Verified.** By reading the code; not run.

### S5. `slice_server/voice.py::Voice.ready`: a race drops finished lines
- **Defect.** `ready()` calls `f.done()` twice, in two separate list comprehensions. A future that finishes between the two passes is in neither list, so it is removed from `_pending` and never returned.
- **Failure scenario.** A line completes in the microseconds between the two passes. It is never sent to the client and never logged, so the fallback-rate and latency numbers silently miss it.
- **Verified.** By reasoning; it is a small window per call, but it is real over a session.

### S6. `tests/`: an Overdrive strike while tripped is not guarded
- **What I broke.** I changed `Sim._strike` to use `self.command.overdrive` instead of `self._effective(self.command).overdrive`, so a tripped body still lands 120 kJ strikes and books heat.
- **Result.** `test_sim_vendor.py` and `test_sim_fire.py` stayed green (13 passed).
- **Why it matters.** The plan's rule "above T_trip, Overdrive cuts out" holds for strikes only by luck.

### S7. `tests/test_server.py`: the auth gate on `npc_line` is not guarded
- **What I broke.** I removed `and self._client.authed` from `Server._send_line`, so an unauthenticated peer receives the vendor's lines.
- **Result.** All 9 server tests stayed green.
- **Why.** `test_a_client_that_has_not_said_hello_is_sent_nothing` runs without a voice, so no line is ever produced. The per-launch-token rule is a standing rule this lane keeps, and for lines it is held only by the code.

### S8. `slice_server/__main__.py::serve` and `main`: the shipped entry point never runs under a test
- **What is uncovered.**
  - `__main__.py` lines 25–45 and 74–90: `serve`, argument parsing, signal wiring, the session log, the `meta` line;
  - `write_run_file`;
  - `ticks_of` for a log that did not end cleanly;
  - the overrun counter (`Server.run`, lines 101–102);
  - the second-client refusal (`_accept`, lines 184–185);
  - the `MAX_OUTBOX` drop.
- **Why it matters.** The tests drive the `Server` directly and write their own `meta` line. A regression in how `serve` writes the log header, or in `main`'s replay exit code, would ship unnoticed.

## NIT

- **N1. `sim.py::Sim.digest`.** It says it covers "every bit of state that replay must reproduce", but it omits `vendor_state`, each fuel's `burning_s` (the growth clock) and the world's source powers. `test_a_change_of_the_vendors_state_sends_a_line_and_logs_it` mutates `sim.vendor_state` from outside, and the session still replays MATCH because that state is not in the digest. A divergence in the final ticks' growth clock or sources would go undetected.
- **N2. `heat_debt.py::add_heat`.** The trip branch (line 83) is uncovered. Deleting it keeps all tests green. That mutant is almost equivalent, because `heat_debt.step` trips on the same tick.
- **N3. `fire.py::Fire.douse`.** Removing the skin reset to ambient keeps all 25 fire, npc and vendor tests green. The documented "doesn't relight at once" behaviour has no test.
- **N4. `server.py::Server._accept`.**
  - There is no hello timeout. A local peer that connects and never says hello holds the only slot, and the real client is closed on connect.
  - `godot/scripts/main.gd::_status` stays "connected" after the server drops the connection, so the HUD misreports.
- **N5. `__main__.py::serve`.** The session log name has one-second resolution and is opened with `"w"`, so two launches in the same second overwrite a session.
- **N6. `data/fuel.yaml` and the week-2 commit.** The comment "a 0.6 m crate burns about 3.5 minutes" and the commit's "crate burnt out at 213 s, pallet ignited at 69 s" predate the t-squared growth. My uncontrolled run (vendor charges 0, so no douse) measured the pallet igniting at 134 s, the crate out at 273 s and the pallet out at 450 s (`probes/burn.py`). Readers of the verdict should use the current numbers.

---

## Checked and clean

- **Wire** (`wire.py`):
  - frames split across reads;
  - HTTP refused at the first 4 bytes, even when they arrive across several reads;
  - frames over `MAX_FRAME` refused before buffering;
  - NaN and Infinity refused (`parse_constant`), non-objects refused, and `allow_nan=False` on encode.
  - Coverage is 100%.
- **Handshake:**
  - the token is compared in constant time;
  - a wrong token, a missing hello and an HTTP request with an `Origin` header are each refused, and the connection is closed;
  - the server binds 127.0.0.1;
  - no state goes to a peer that has not said hello.
  - The token-check mutant went red.
- **Intents** (`intents.py`): exact key sets, finite numbers, bools refused as numbers, effort range, the say length limit, unknown types. Coverage is 100%. The extra-keys mutant went red.
- **Config** (`config.py`): unknown and missing keys, non-positive values, whole-number fields, `warn_c` below `trip_c`, canned lines for every state. Coverage is 100%.
- **The "words change no act" rule** (`Sim._take(Say)`): a mutant where say kindles turned `test_words_change_no_act` red, so that test can fail. The voice is imported by no simulation module (a test parses for it).
- **Vendor mutants:** removing the charge check, never spending charges and removing the recoil impulse each went red.
- **Kindle filter:** a mutant allowing burnt-out fuel to kindle went red.
- **Writes go through the applier:** every world change in `sim.py` goes through `Applier.apply`: Ignite replaces the keyed source, Extinguish removes it, Strike is applied directly. No cell or source is written directly. `Ignite(0 W)` at the moment of lighting is accepted by the limits (minimum 0).
- **Strike destruction:** 400 Overdrive strikes on the crate destroyed nothing, because the craters stay at one nearest point. So the "region is gone, then Ignite is refused" crash I suspected is not reachable on the 0.2 m grid. A full crate-and-pallet burn at 0.2 m kept all 27 cells of each.
- **Tunnelling:** `check_no_tunnelling` refuses unsafe parameters as intended. Side effect: `serve --dx 0.1` is refused with the shipped substeps (6 m/s × 0.1 s / 8 = 0.075 m, more than half of 0.1 m). That is deliberate but worth knowing.
- **Server loop** (`Server.run`): stop is checked only between ticks, the deadline resets on overrun, and the `Server.run(55)` test runs past the stats report. `ticks_of` and `check_replay` replay real sessions in tests (MATCH).
- **Voice cap:** `voice.ollama` refuses non-local hosts. I checked a `127.0.0.1:80@host` trick: `http.client` raises `InvalidURL`, so it does not escape.
- **Godot client:**
  - `main.gd`, `net.gd` and `voxels.gd` load with `--check-only`, HOME redirected, rc 0, no errors;
  - the client sends only intents and computes nothing that feeds back;
  - the big-endian u32 framing matches `wire.py`;
  - cells are indexed in C order, matching the server's arrays;
  - crack changes cube size as well as shade;
  - the HUD states are in words, and colour only adds to them.
