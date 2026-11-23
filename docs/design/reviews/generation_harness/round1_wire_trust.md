# Generation harness plan, round 1: Wire integrity and Trust boundary (2026-11-22)

Two readers' hand-backs, condensed and saved by the author. Statuses are unset until a reviewer sets them after the
fold. Both read the plan at 620b7a0 and the spike at 085c012. The Trust reader ran one probe, on Python 3.12.12 and
3.14.6.

## Wire integrity: the contract table, in brief

| Contract | Owner today → in the plan | Match |
|---|---|---|
| Run header | spike plan §7 → "a declared list per job type"; `version` is checked by no reader | no (S2) |
| Sample and attempt records | spike → H1's outcome-to-record mapping; no version of their own | no (S3) |
| Protocol config | `arms.yaml` → a job file; `schema.Format` is repo-only, so it can't migrate | partial |
| `placements.yaml` | IP §2.2; it has no build field, and `max_in_flight` sits on the `servers` entry when shared | no (S1) |
| `endpoints.yaml`, egress classes | IG §8, IP §2.2 and IG §6 | yes |
| Weights digest | IP §2.2 declares it and nothing checks it; its encoding is unspecified | no (S1) |
| Gateway outcome classes | IG §5 and IP §2.6, lane-internal names | partial (S3) |
| Request sampling and constraints | IP §4.2: no `min_p`, `repeat_penalty` or `response_format`; per F6, no backend takes seed, top-p or top-k; OD-I12 | no (B1) |
| Spec v0 and v1 | `subcell` §11.2 | yes, but the reader of the spike's v0 records is unnamed |
| SpecId | `ip_and_licensing` §6.1 as amended by `subcell` §11.2 → the spike's v0 float form, "as is" | no (B2) |
| Refusal codes, `agent_text` | `refusals.py`, `subcell` §11.3 | no (S4) |
| Model-reply decoding | `boundaries` §9.1's strict decoder → the spike's `json.loads` | no (S5) |
| Battery result records | undefined | undefined (S6) |
| Provenance of a pre-generated prop | `ip` §6.2 has no origin for offline generation | no (S7) |
| Harness file IO in `src/` | `INPUT_GATES` names only the loaders; the game's allowlist is empty | no (S8) |

## Wire integrity: findings

- **B1, BLOCKER, §4: the gateway's request contract can't carry the generation protocol.**
  - The spike sends a seed, pinned samplers, `response_format` (the grammar that defines A1–A3) and
    `enable_thinking: false`. IP §4.2 carries none of the grammar, `min_p` or `repeat_penalty`.
  - F6 says no backend takes a seed, top-p or top-k, and OD-I12 says the backend can't switch thinking off. The
    envelope's `thinking` is a token budget, not that switch.
  - *Failure:* a rerun through the gateway silently drops the grammar (A1–A3 behave as A0) and the seed, and thinking
    truncates every sample.
  - *Fix (unverified):* name these as contract additions with their owners (IP §4.2, IG §5, Phase 3 asks against F6
    and OD-I12) as H1's precondition, or rule that Q2's band-aid client is the path until they land.
- **B2, BLOCKER, §6 and U11: the plan moves a SpecId that contradicts its owner.** `subcell` §11.2 hashes the
  migrated v1 form (version and role included, µm geometry); the spike hashes v0 float metres. One object gets two
  ids, so IP's re-upload check misses it. *Fix:* one SpecId implementation in the engine, which the harness calls.
- **S1:** the engine proof has nothing to check against and no channel. A placement has no build field, the `ready`
  frame carries no props, and on `owner_lan` neither side can hash the remote file. Fix: Q3 names IP §2.2 (declared
  fields, digest encoding) and IG §3 (a reported-props field), and says how `owner_lan` weights are measured or that
  the digest is a declaration.
- **S2:** run-record versions aren't enforced, and the frozen v0 records need a named exception, as spec v0 has.
- **S3:** IG §5 already maps overflow to `failed(context_overflow)`, while the spike conflates overflow with a length
  stop. Records should store IP §4.1's provenance value plus a stated mapping.
- **S4:** the v1 changes break the moved protocol:
  - `outside_extent` is fed back, though it's a world outcome;
  - M1 counts `too_small`, which S1 retires;
  - part indices change `agent_text`.

  Fix: name tile §3.4's class column as a dependency, and rescore the baseline under the current engine.
- **S5:** model replies must go through `boundaries` §9.1's strict decoder. `json.loads` collapses repeated keys,
  which the game refuses as `duplicate_key`.
- **S6:** battery records need a key, versions, the engine identity, and `not_run` distinct from a failure.
- **S7:** provenance for offline-generated props is `ip` §6.2's to define, before H4.
- **S8:** the harness's file IO needs registered gates and allowlist entries.
- **NITs:**
  - N1: define the "harness version" and "config digest" encodings;
  - N2: envelopes are rows in `functions.yaml`;
  - N3: name U8's digest.

## Trust boundary: findings

- **T1, BLOCKER, §4: the gateway inherits OD-I11, and nothing stops it.** A placement of type `openai_compatible`
  under another key name, pointing at a local server without `allow_local_endpoints`, would send every prompt in a
  batch to OpenAI, each failing 401 only after leaving the machine. *Fix (unverified):* cite OD-I11 as H1's
  precondition, check the client's effective base URL against the placement before the first dispatch, and add a test
  that plants a blocked URL and expects a refusal with no socket opened.
- **T2, BLOCKER, §6: "the gateway's log replaces masking" drops the spike's only leak control.** IG §2's log may hold
  endpoints and provider errors, and a batch job has no session directory. If the log lands in a committed run
  directory, the Tailscale address is published in a public repository. *Fix (unverified):* gateway logs and
  `endpoints.yaml` live outside the worktree, a check refuses unexpected files in a committed run directory, and
  masking survives for anything written there.
- **T3:** "batch jobs never use a hosted model" has no mechanism. Fix: hard-code `egress ∈ {loopback, owner_lan}` with
  no consent path, refuse a reported proxy, and record honestly that `owner_lan` admits a Tailscale-joined cloud VM by
  design.
- **T4:** if Q2's band-aid is chosen, the spike's client needs `ProxyHandler({})` and an egress check.
- **T5:** battery outcomes need three classes: spec refused (`place`'s codes), world outcome (recorded, never a
  fault), and engine defect (stop loudly, file a Known gap).
- **T6:** what is fed back must be code, not configuration. Only `place`'s `agent_text` is fed back, and never a world
  outcome or a battery verdict, which would teach the generator the grid.
- **T7:** run records are input but not a file gate. `json.loads` accepts `NaN` and `1e999` (checked). Fix: gate
  rows, strict JSON, `known_keys`, a version, a line-size bound, and verdicts bound to the spec's digest.
- **T8:** a prop baked into a scene skips `place`'s budget and name rules. State which path it takes.
- **T9:** the battery's cost is unbounded (scene, `Budget`, turns). Fix: fix them in the versioned battery file, with
  a maximum-budget test.
- **N1 (crash verified):** Python 3.12's parser raises `RecursionError` on deep nesting, and `parse_reply` caught only
  `JSONDecodeError`. This was folded into the spike before its first run.
- **N2:** an uncaught `URLError` traceback names the endpoint.
- **N3:** the batch server binds the Tailscale address with no API key, so tailnet nodes can use it.

**Checked and fine:**
- `place`'s name and finiteness checks;
- `agent_text`'s closed vocabulary;
- `model_path` never recorded;
- nothing unpickles.
