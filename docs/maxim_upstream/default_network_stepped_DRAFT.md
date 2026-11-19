# DRAFT for Maxim: a Default Network a host can step

**Status:** a proposal drafted in Maxim Overdrive on 2026-11-16, for Maxim's process as a **plan** (three-lens plan
review, three-lens code review). Nothing is built, run or claimed; `[engineering]` only. Read against `origin/main`
`7084f561`.

- **Overdrive id:** OD-A9 (tier A, A-post). Overdrive's earlier item 11.
- **Depends on:** the world clock A-pre plan (`AgentTime`). It is sequenced after 1.3.6, coordinated with #1263's
  remainder.

## 1. The claim

**An embedded agent's Default Network runs only when the host steps it, on the host's world time.** Robots keep the
thread and today's behaviour.

## 2. What exists, and what changes

- **The Default Network runs its own thread** (`default_network/network.py::DefaultNetwork.start`, `_run_loop`) at
  `DefaultNetworkConfig.update_hz = 30.0`. It reads `time.time()` for idle duration, its cadence and its stamps
  (`network.py`, around `:561`, `:836`, `:931`, `:1390`).
- **Already done upstream, and built on here:**
  - The DefaultNetwork stop (#1263's part, shipped by #1299).
  - Owned generators in `default_network/` (`1305.owned-rng`), so the DN no longer draws from the global `random`.
  - The `1263.thread-guard` conftest guard, with an empty allowlist.
- **New:** `DefaultNetwork.step(now)`, which runs exactly one pass of `_run_loop`'s body at a given clock time and
  returns. The thread becomes a caller of `step` on its own cadence, so robots are unchanged. An embedded agent never
  starts the thread; its host calls `step` from the embedded agent's `step`.
- **Every DN timer reads `AgentTime.clock`:** cooldowns, inhibition, idle duration, the arbiter. Under the host
  default, that's `time.time()` at call time, as today.

## 3. Coordination

- **#1263's remainder.** The plan review lists which of #1263's open parts touch `default_network/` and orders this
  plan after them.
- **`idle_dmn_coordinator.md`** (proposed, no `src/` before 1.4.0 under M89) will spend idle-time slices in the DN
  lane. A stepped DN must leave room for it: `step` is one pass, and the coordinator's slices are budgeted inside a
  pass. This plan doesn't build the coordinator.
- **HA-O4** (no LLM in the idle DN lane in the first build) holds for embedded agents too.

## 4. The build

| PR | What | Size |
|---|---|---|
| 0 | Red gates: an embedded agent steps its DN N times, and its state matches a reference; no DN thread starts under embedding | S |
| 1 | Extract `_run_loop`'s body into `step(now)`; the thread calls it | M (touch it, shrink it applies) |
| 2 | Timers on `AgentTime.clock`; flip the gates | M |

## 5. Exit tests

| # | Test | Passes when |
|---|---|---|
| OD-DN1 | **No thread under embedding.** Build and step an embedded agent 1,000 times | the DN thread never starts (the thread guard) |
| OD-DN2 | **Step equivalence.** The robot thread, driven by a fake clock, against `step` called with the same times | identical DN state |
| OD-DN3 | **Pause.** The fake wall advances with no steps | no DN timer fires |
