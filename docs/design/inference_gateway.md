# Inference gateways: the processes that make NPC model calls (design, v1, 2026-11-21)

**Status:** split out of `inference_placement.md` v2 (§3 and §5 there) when folding its delta round
(`reviews/inference_placement/delta_*.md`). The fold table is `reviews/inference_placement/fold_delta.md`. Under the
stop rule (CLAUDE.md, "Review finds; it doesn't design"; owner, 2026-11-21), no further full paper round follows: a
short delta check confirms the folds, and mechanism findings are in `phase1/agents`' checklist.

**What it owns** (one owner per contract, B36):
- the gateway's package and layer;
- its process and environment;
- the host–gateway channel and its rules;
- the gateway's lifecycle;
- `endpoints.yaml` and the credential store;
- per-transport classification of a backend result into an outcome;
- consent by egress class, and per-speaker taint;
- what each egress class can promise;
- proxies, credentials and endpoints;
- spend.

The lane, the outcome vocabulary and where each outcome goes, the cache and the manifest are
`inference_placement.md`'s (IP below).

**Sources:** Maxim `origin/main` 043eab8f, read with `git show`. *Verified* means the author or a round's reader read
the cited line there, or ran the stated command.

## 1. Where the code lives **[now]**

| Module | Layer (`boundaries.md` §2.2) | Imports | Imported by |
|---|---|---|---|
| `engine.inference_wire` | 7a, beside `engine.loaders` | `engine.checks` only | the host lane and the gateway |
| `engine.adapters.inference` | 7b, beside `engine.adapters.sem` | `engine.inference_wire`, `maxim.models.language` (backends and types, never `LLMRouter`'s methods) | nobody: it is spawned, never imported |

- **What `engine.inference_wire` holds:** the channel's frame types and codec, the outcome and classification
  values, and the provenance type. It holds no `maxim` import.
- **Three import contracts hold the layout:**
  - `maxim-through-adapters` gains `engine.adapters.inference` by name;
  - a new forbidden contract, `engine.host` ↛ `engine.adapters.inference`;
  - the layers contract.
- **The per-user directory** that holds the player's files is resolved by `maxim_overdrive.data` and injected.
  The engine has no default path, and tests pass `tmp_path`.

## 2. One gateway per placement (O47, O53) **[now]**

**Spawning.** A gateway is spawned like a worker (`npcs_and_sem.md` §6.6): `spawn`, `-I`, a working directory at its
home under the session directory, and an allowlisted environment. It is not latched, because it needs the network.

**Its environment holds:**
- `HOME` and `XDG_*` set to the gateway's home. An unset `HOME` falls back to the real one (*verified*, round 1).
- `NO_PROXY=*` and `no_proxy=*`. With these set and nothing else, `urllib.request.getproxies()` returns
  `{'no': '*'}`, so it skips macOS System Settings, and httpx 0.28.1's `get_environment_proxies()` returns `{}`, so it
  mounts no proxy. *Verified* by running both with `env -i`.
- No `MAXIM_*`, `*_API_KEY`, `*_BASE_URL` or proxy URL variable.

**What it builds and reads:**
- `LLMConfig` is built directly from the gateway's own files, never through `load_llm_config` or profiles.
- It passes `request_context=None` and sets no context variable, so it sends no agent, session, lane or parent id. A
  request id and the protocol version may still go out (`utils/http.py:1029-1031`).
- Its import allowlist is the **transitive** module set, recorded at the build step against the locked pymaxim,
  including call-time imports such as the peer backend's `llm_worker`.

**The no-effect test allows only:**
- **reads** of its home, its two `endpoints.yaml` files, the credential store, the standard library and
  site-packages, and the CA bundle;
- **sockets** to its placement's endpoint and the system resolver;
- **writes** under its home.

It forbids every spawn. A planted `~/.maxim/config/llm.json` under a test `HOME` is never read.

**Its log.** The gateway's stdout and stderr go to a size-bounded log under the session directory. That log is
outside every save, never in a bug report, and deleted by O26's purge. It may hold endpoints and provider error
text. No other log, meter, manifest, cache entry or save may hold either.

## 3. The channel **[now]**

The worker codec's rules apply (`npcs_and_sem.md` §6.6): length-prefixed, versioned, closed-schema JSON, budgets
before allocation, nothing pickled. Each side reads on its own thread, which never blocks on a write, and writes
through a bounded outbox. A full outbox counts as a hung peer (§4).

**Host to gateway:**

| Kind | Fields |
|---|---|
| `open` | the placement's `id` (whose endpoint and credential references the gateway looks up in `endpoints.yaml`), `transport`, `egress`, `cleartext`, and `transport_timeout_s` from the `health` block; no function data |
| `dispatch` | `attempt_id`, the request |
| `cancel` | `attempt_id` |
| `ping` | `n` |
| `shutdown` | none |

**Gateway to host:**

| Kind | Fields |
|---|---|
| `ready` | the proxy report and the pymaxim version; sent once, after `open` |
| `error` | `code`: `bad_settings`, `endpoint_refused`, `credential_unresolved` or `transport_unavailable`; sent once, instead of `ready` |
| `reply` | `attempt_id`, the classification (§5), `text`, the reported fields (IP §4.1) |
| `pong` | `n` |
| `chunk` | `attempt_id`, `seq`, `text`; **reserved**, never sent under O50 |

**Binding rules:**
- **`attempt_id` is `(gateway generation, sequence)`.**
- **An attempt is finished only by its one `reply`, or by its gateway's death.** A request ending first, by cancel or
  the liveness ceiling (IP §2.5), doesn't finish its attempt: the host sends `cancel` in both cases, and the later
  `reply` is expected. It frees the slot, and IP §4.2 says what happens to its text.
- **`cancel` of an attempt that is already finished is a no-op.**
- **Protocol errors** kill that gateway (§4). They are:
  - a `reply` or `chunk` for an attempt this generation never accepted;
  - a second `reply` for one attempt;
  - a frame over budget;
  - a malformed frame.
- **The gateway enforces the frame budget on the reply it builds.** Text over budget is cut, and the reply is
  classified `failed(oversized)` (§5). That is a placement fault, not a protocol error.
- **The host stamps provenance's host-known fields** (IP §4.1) and bounds the reported ones. A reported value out of
  bounds becomes null and is metered; it is not a protocol error.
- **The gateway checks `open` against what it can see.** An `egress: loopback` placement must resolve to a literal
  127.0.0.1 or ::1, and `http://` on `owner_lan` needs `cleartext: true`. A mismatch is `error(endpoint_refused)`.

## 4. Lifecycle **[now]**

**What kills a gateway.** These end a placement's gateway, and no other placement's:
- a call past `call_ceiling_s`, which IP §2.5 attributes;
- no `pong` within `ping_ceiling_s` while an attempt is in flight;
- a protocol error;
- a full outbox.

**After a kill.** The old channel is closed before its attempts are declared, so no late frame can be read.

**Starting.** A start fails if neither `ready` nor `error` arrives within `start_ceiling_s`, or if `error` arrives.
- `error(credential_unresolved)` or `error(endpoint_refused)` marks the placement **down for the session** at once,
  because retrying can't fix either.
- A process that exits before `ready` is a failed start, and `max_failed_starts` within the window marks the
  placement down for the session.
- A start that times out restarts with backoff but never counts, because a loaded machine starts slowly and load
  must never move a pinned function (O48).
- **Kills never count.**
- The client is told through `inference_status` (§8).

**Stopping.** `shutdown` is a bounded wait, then a kill. A gateway exits with `os._exit` on EOF from the host, so an
orphan never keeps spending.

**Tunables.** Every value in this section lives in `placements.yaml`'s `health` block (IP §2.2), with its range
checked at load. The rules: `ping_ceiling_s` above the ping interval, `start_ceiling_s` below the liveness ceiling,
the backoff cap below the liveness ceiling, and (1 + the retries the transport can't switch off) ×
`transport_timeout_s` at or below `call_ceiling_s`.

## 5. Classifying a backend result **[now: the table; Phase 4: each transport's fake-server tests]**

The gateway classifies; the lane decides (IP §2.6). The gateway normalises the stop reason first:
- `None`, `"None"` and `""` all become `absent`.
- The transports differ here: `openai_backend.py:542` and `anthropic_backend.py:467` turn `None` into `"None"`, while
  `maxim_peer_backend.py:958` turns it into `""`. *Verified*, delta round.

| Result | Classification |
|---|---|
| content, with stop reason `absent` or `end_turn` / `stop` | `ok` |
| empty content with a non-`absent` stop reason that is not a refusal | `ok` (the model chose silence) |
| length stop: `max_tokens` (anthropic), `length` (openai_compatible, maxim_peer) | `truncated(length)` |
| content with any other stop reason (`stop_sequence`, `tool_use`, `pause_turn`, `tool_calls`, …) | `ok` |
| refusal stop: `refusal` (anthropic), `content_filter` (openai_compatible) | `failed(refused)`. The values are *to verify* at Phase 4 against each transport. |
| empty content and an `absent` stop reason | `failed(empty)`, **a stand-in until OD-I9**, marked in code with `TEMPORARY(phase3)` and listed under Phase 3 |
| `BackendOverloaded` / `BackendTimeout` | `failed(overloaded)` / `failed(call_timeout)` |
| `BackendDown` after our `cancel` | `cancelled` |
| `BackendDown` otherwise | `failed(unreachable)` |
| `BackendAuthFailed` / `BackendModelMissing` / `BackendInferenceBroken` | `failed(auth)` / `failed(model_missing)` / `failed(inference_broken)` |
| `BackendContextOverflow` | `failed(context_overflow)` |
| reply text over the frame budget | `failed(oversized)` |
| any other exception at the call boundary | `failed(unclassified)`; its text is logged in the gateway log, never relayed |

**What the classification can tell apart.** On `openai_compatible` and `anthropic`, a read timeout or a 503 arrives as
empty content (F2 in IP §1.3), so until OD-I9 those transports can't tell load from failure. IP §2.7 says what the
lane does with that.

## 6. Consent and taint (O18, O49, O51, O54) **[now: the rule; Phase 4: the disclosure UI]**

**Recording consent.** Consent is recorded per speaker and per class, saved with the save, and versioned. A speaker is
an actor and its session (`npcs_and_sem.md` §6.6), so a guest who rejoins accepts again.

**With guests present:**
- only `loopback` is eligible unless every present guest has accepted the class (and, for `third_party`, the named
  provider);
- `owner_lan` counts as remote (O49).

**Taint** (O51). For each NPC, taint is the set of speakers whose words it may hold. It is the host's provenance
lower bound (O26) over:
- **every guest-supplied string the NPC perceived, by any channel:** whatever passes `engine.text.player_text`
  (`npcs_and_sem.md` §6.6 owns that list).
- **everything it perceived from NPCs that held them, by any channel,** transitively. A string an NPC authors into
  the world (an imagined-object label, written text) carries its author's taint when the intent applies, and
  perceiving it transfers that taint.

**What taint does.** An NPC whose taint holds a speaker who hasn't accepted a class is ineligible for that class.

**Clearing taint.** Taint for speaker S on an NPC clears only when `purge(S)` completes on that NPC.

**Who may purge (O54).** Either person may delete: S while connected (O17), or the save's owner. Only S may release
S's words to a remote class, by accepting its disclosure. So the owner can unlock a cloud model only by erasing what S
said, and the NPCs then lose those memories.

**Where taint lives.** Taint is saved with the save as versioned state, and consent and purges are logged.

**Single-player, with no foreign words held:**
- `owner_lan` is eligible once configured;
- `third_party` needs an explicit opt-in and a spending cap.

**OPEN divergences:**
- Taint spreads through conversation and persists until purged. One guest who declined can leave most of a talkative
  city local-only.
- Clearing rests on the agent's purge reach, a lower bound (O26), so a paraphrase or summary that escaped the
  provenance sets survives a purge.
- A guest's world text keeps re-tainting NPCs until the object is removed, which O26's purge doesn't reach.

## 7. What each class can promise **[now: the checks and the disclosure text]**

Each class promises only its **first hop**, and each disclosure says so.
- **`loopback`.** A literal 127.0.0.1 or ::1, checked in the gateway. A local server that forwards elsewhere, such as
  a cloud-backed proxy or a cloud model tag, is out of sight.
- **`owner_lan`.** "A machine on your private network or VPN, which the game can't verify is yours."
  - The gateway refuses an endpoint whose address is not private, link-local or CGNAT (100.64.0.0/10).
  - Over `http://`, Maxim checks the dialled address at connect time.
  - Over `https://`, Maxim applies no connect-time check (`utils/net.py:94-106`, *verified*), so the gateway can only
    look the address up first, and DNS rebinding can defeat that.
  - A Tailscale-joined cloud VM passes the check by design.
  - `http://` needs `cleartext: true`, and the disclosure then says the traffic and the cluster key are readable on
    the network.
- **`third_party`.** The provider is the one named in the file. Provenance can't attest it: both cloud backends echo
  the configured model and the provider key (`anthropic_backend.py:464`, `openai_backend.py` `_parse_response`).
- **A detected proxy.** The gateway reports the proxy state in `ready` and the lane re-reads it at each client build
  (`phase1/agents`' checklist). A gateway that reports a proxy despite `NO_PROXY=*` is treated as `third_party`.
  - With guests, it is refused.
  - Single-player, it needs a `third_party` opt-in with a price.
- **The Known gaps** recorded for these first-hop limits are listed in IP §6.3.
- **No redaction is applied; consent is the control.** Guest text still passes `engine.text.player_text`, which
  refuses controls and format characters but removes no names.

## 8. Credentials, endpoints, spend and status **[now: references, the meter and the cap; Phase 4: resolution and prices]**

**Endpoints and keys.**
- The host holds neither endpoints nor key material. Both live in `endpoints.yaml` and the credential store, which
  only the gateway reads, and both are registered gates (§9).
- The player's `endpoints.yaml` replaces the shipped one whole. Its ids must match the placements' ids exactly; a
  missing or extra id is refused.
- Keys reach Maxim's backends as already-resolved entries:
  - `types.py::resolved_entry_key` for `anthropic` and `openai_compatible`;
  - the entry's literal `api_key` for `maxim_peer` (`maxim_peer_backend.py:791-802`).

**Spend.**
- Spend is the provenance's four token counts times `price`'s four rates (IP §2.2).
- When a reported count is null or zero, spend uses the host's own count: the envelope's counter over the request,
  plus `response_reserve` for the output.
- Abandoned and killed calls count at dispatched input plus `response_reserve`.
- Until OD-I9, Anthropic cache writes are missing from `LLMResponse` (F8), so the host's floor is the bound. That is
  a Known gap, listed in IP §6.3.
- The cap is soft by at most `max_in_flight` calls per placement. Reaching it makes `third_party` ineligible.
- Spend never reaches cognition.

**`inference_status`.** A host status kind joining the server-to-client messages in `client_rendering.md` §4 at
`phase1/protocol`. It carries:
- the spend cap reached;
- a placement down for the session;
- a proxy found;
- the guest disclosure state.

## 9. Gates **[now]**

Each of these is a row in `boundaries.md` §5.3's registry, with golden rejection files:
- the gateway channel, in both directions;
- `functions.yaml`;
- both `placements.yaml` files;
- both `endpoints.yaml` files (read in the gateway);
- the credential store (read in the gateway; Phase 4 picks the OS keychain or a file);
- the saved consent and taint state.

Every refusal that names a placement carries its id, never an endpoint.
