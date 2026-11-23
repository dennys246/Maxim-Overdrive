# Maxim's answers for 1.3.5 (received 2026-11-23)

Recorded from Maxim's 1.3.5 plan, `docs/plans/release_1_3_5.md` §Answers to Overdrive. That plan merged as Maxim
PR #1759 (`0c7c711a`) and was relayed under its owner decision D18. It answers the asks in
`docs/design/inference_placement.md` §9 and the open items from `maxim_response_1`. None of it is built yet, unless a
line says so. Each item below names the Maxim issue or plan item that carries it.

## Done

- **OD-I7** is fixed in pymaxim 1.3.4 (Maxim #1719, `DamageRefused`). `apply_damage` on a part with no sub-sensors
  no longer returns 1.0.

## Scheduled for 1.3.5

| Overdrive id | Answer | Maxim issue or plan item |
|---|---|---|
| OD-I6 (`rich<14`) | Filed. The cap is lifted, or narrowed to the versions that break, with the evidence recorded. | #1761 |
| OD-I1 (`x or time.time()`) | Five sites; a caller's 0.0 stays 0.0. | #1684 |
| OD-I3, cand. A5 (pickle-capable `.npz` load) | Fixed together with the atomic save. Labelled `security` on Maxim's side. | #1685, #1531 |
| OD-I4 (`ARCHITECTURE.md`, DM NPCs) | The doc is corrected. | #1686 |
| cand. A2, first half (seeded runs) | The global `random` / `np.random` draws. This is a 1.4.0 gate item, so it rides in 1.3.5. | #1305 |
| OD-A2 to OD-A6, cand. A3 (A-pre half) | `maxim_upstream/world_clock_release_DRAFT.md` becomes a Maxim plan, which gets a three-lens review and then one PR per site family. The A-post half, with #1361, waits until after 1.4.0. | plan owed |
| OD-A12, cand. A1 (`AgentHome`) | Carried together with #984. | #984 |
| OD-I10 (`NO_PROXY`) | **Confirmed** (Maxim decision D16). `NO_PROXY` is honoured on the backend call path, where an embedder makes the call. The 2026-09-28 "the proxy wins" rule still holds for Maxim's own operator commands. Tests pin both rules, and `strict_address_check` is exposed to backend callers. | #1764 |
| OD-A24, OD-A14 (placement outside `LLMRouter`) | **Not answered yet: a design pass first.** It starts from a front-gate question. Can a one-provider `LLMRouter` from `create.router` make one backend call per dispatch, once its router defects are fixed in the router? Those defects are the `_inference_lock` serialisation, per-read timeouts and no whole-call deadline. Only if not does a public factory get built, inside `models/language/`. Two Maxim invariants are in play: router-only LLM access, and "placement rides on `provider_priority`". Amending either needs a Maxim DECISIONS entry. | #1763 |
| OD-I9 (typed errors) | **Part of the ask.** 1.3.5 plans typed errors in place of empty content, and that item may slip while the Mac mini stays on `maxim_peer`. The configurable retry budgets and the complete usage counts (F4, F8) are **not scheduled yet**. The issue carries all three parts. | #1766 |
| OD-A23 (cancellation), transport half | It gets measured, not argued: N concurrent buffered and streamed calls against the mini's proxy, and what a client disconnect does to the upstream generation. The measurement runs before the #1609 fix reaches the mini. | 1.3.5 line 6, item 1 |

## Not in 1.3.5

- **OD-A25 (streaming tokens to the caller):** after 1.4.0, together with the stepped `think` (cand. B1).
- **The A-post half of the world clock** (with #1361 S3 to S6), **cand. B2** (#1150 with A6), and **A2's per-agent
  key:** all after the 1.4.0 cut.

## The peer mesh, for this repo's workflow

The workflow Maxim plans for: the model is served on the Mac mini, and the world server and the Maxim agents run on
the laptop, calling the mini over Tailscale (`http://<mini>:8099/v1`).

**What holds today:** the leader proxy admits `proxy.max_concurrent` requests (default 4). The upstream
`llama_cpp.server` generates one sequence at a time. Any request over the cap gets an instant 429, with no queue, and
no endpoint advertises capacity.

**Maxim's side, in 1.3.5:**
- `--interrupt_requests False` on the spawned server (#1609). Today any keyed request, even a `/v1/models` probe,
  truncates a reply that is still streaming.
- A queueing admission with a deadline, a cap matched to the upstream's real parallelism, and capacity advertised on
  `/v1/models` or `/v1/debug/status` (#1762). This is a gate on Maxim's side, so an approach note comes first.
- `peer connect` sets all three lanes, plus a "Tailscale peer" troubleshooting page (#1765).
- Key custody and rotation (#1632, #1633, #1478) and restart hygiene (#1627, #1613, #1498).

**Asked of Overdrive:**
- Set `max_in_flight` for `maxim_peer` to about 1, until #1762 advertises capacity; then read it from there.
- Classify a 429 as overloaded, not failed.
- Keep the `owner_lan` HTTPS check and the Phase 4 fake-server tests on your side.
- **Sharing the mini (Maxim D12):** game and playtest traffic never runs while a Maxim experiment holds the mini's
  leader. On Maxim's side, the refusal will come from the proxy: while an experiment holds it, #1762's admission
  refuses other clients and names the holder. A client-side check before a session starts is an ask to Overdrive.
  Until both exist, the rule is held by attention (Maxim backlog row M96).

## Maxim's use of Overdrive as a test world (D8, D13)

- Maxim will build its own harness to test Maxim in Overdrive's world. It runs under O10's strict red gates, stamps
  the Overdrive commit it ran against, does not go through the SEM adapter, and runs in a named CI cell that fails
  loudly when simcore is missing. Overdrive's `simcore` is a test-only install there, never a pymaxim dependency.
- **Game runs never go on Maxim's results ledger.** O6 (mode (a) dropped) and O10 (no developer mode with real
  Maxim before tier A, except inside strict red-gate tests) are respected as written.
- The flooded room is Overdrive's work, not Maxim's.

## On Maxim's release process

- **Maxim M97:** before each Maxim release cut, someone reads this repo's weekly drift job (`drift.yml`), as the
  canary for Maxim's embedder surface. A red or missing run will be listed in Maxim's release check once that row is
  built. Until then the read is on Maxim's checklist.
