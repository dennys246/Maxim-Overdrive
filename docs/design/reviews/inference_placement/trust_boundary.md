**Verdict: not ready to build. 2 BLOCKERs, 8 SHOULD-FIX, 5 NITs.** Both BLOCKERs are ways a guest's words can leave the machine without the disclosure O18 and O49 require.

Lens: Trust boundary. Design reviewed: `docs/design/inference_placement.md` (DRAFT v1), diff `814dea9..04ab810`. Maxim was read only at `origin/main` 043eab8f, with `git show` and `git grep`. Anything I ran is named. Everything else is marked unverified.

---

## BLOCKER

**B1. `inference_placement.md::§5.1` ("The loopback check") and `::§3` ("Spawned like a worker"): on macOS, a system proxy routes every call through itself. That bypasses the environment allowlist, the loopback-literal check and Maxim's address policy.**

The design keeps the gateway's egress contained with two things:
- an allowlisted environment (no proxy variables pass);
- a literal 127.0.0.1 or ::1 check that "the gateway checks again before connecting".

Neither one decides where the bytes actually go when a proxy is in play:
- **The openai-compatible and peer transports.** Maxim's `utils/http.py` builds its address-checked client's mounts from `httpx._utils.get_environment_proxies()` (around `:839-843`). Its own warning says proxied requests "bypass the connect-time address check (#921), because the proxy dials on Maxim's behalf". That comes from Maxim's owner decision of 2026-09-28: "the proxy wins for operator paths".
- **The Anthropic transport.** `_AnthropicBackend._ensure_client` builds `Anthropic(api_key=..., timeout=...)` with no `http_client` (`anthropic_backend.py`, around `:236-238`). So it gets the SDK's default httpx client, which trusts the environment.
- **The empty environment doesn't help.** `get_environment_proxies` calls `urllib.request.getproxies()`. On macOS that is `getproxies_environment() or getproxies_macosx_sysconf()`, so with an empty environment it falls back to the proxies set in System Settings.

*Verified:* I ran `env -i <worktree .venv>/bin/python -I` and printed the source of `getproxies`. It returned exactly that fallback. This Mac has no system proxy set, so the call itself returned `{}`.

*Not verified:* that httpx sends a literal `http://127.0.0.1:11434` URL through a system proxy. httpx doesn't read macOS's bypass list, so it may.

**Failure scenario.** The host runs on a Mac with a corporate proxy, an inspection tool such as Charles or mitmproxy, or a proxy planted by adware. Two guests join. Only `loopback` is eligible, so no disclosure is shown. Each prompt, guests' words included, goes to the proxy:
- Cloud calls go through a CONNECT tunnel.
- A plain `http://` call to loopback or `owner_lan` is readable in full, including the `Authorization: Bearer` cluster key.

O18's promise ("before their words leave the machine") breaks on the shipped path. The "checks again before connecting" line in §5.1 gives false confidence.

**What fixing it costs.** The gateway would need a way to turn proxies off on every transport. Maxim offers no such option today: the mounts come from `get_environment_proxies` unconditionally, and the Anthropic client is built inside the backend. So this is likely a Phase 3 ask, or a pushback against the 2026-09-28 "proxy wins" decision for embedders. The cheaper alternative is to make the design refuse or disclose when a system proxy is detected. That is unverified as a fix.

**B2. `inference_placement.md::§5.1` ("With guests present", and "Single-player"): consent depends on who is present in the session, but guests' words outlive the session.**

The rule is: "a guest who hasn't accepted makes the class ineligible for the whole session." Single-player then allows `owner_lan`, and `third_party` once opted in.

But guests' words persist after they leave:
- O17 says guest speech is held agent-side until a purge.
- O26 lists the stores that hold it: agent stores, continuation bodies, the response cache's requests, saves and the intent log.

**Failure scenario.**
1. Monday: a co-op session with one guest, loopback only. An NPC stores what the guest said.
2. Tuesday: the host plays alone and opts into a Claude placement with a spending cap.
3. The NPC recalls Monday's conversation. The worker renders the guest's words into a prompt.
4. The lane sees no guests present, so `third_party` is eligible. The guest's words go to Anthropic. The guest never saw a disclosure.

The host can't detect this. The request value is rendered text the worker produced. §6.6 keeps memory provenance by speaker inside the worker, and the host never sees which spans of a prompt came from whom. So whether a guest's words are in a request is not visible at the dispatch point.

This is a contract gap: the consent rule is keyed on the wrong thing. Two possible fixes, both **unverified**:
- consent recorded per speaker and persisted with the save, with an agent holding a non-consenting speaker's spans ineligible for remote classes until those spans are purged;
- or an explicit owner ruling that a disclosure binds for the life of the save.

Either needs owner input. I am not designing it.

---

## SHOULD-FIX

**S1. `inference_placement.md::§2.2` (`egress`) and `::§5.1`: the egress class is whatever the file says. Only the loopback literal is checked, and consent is keyed on that class.**

- **`owner_lan` takes any public HTTPS host.** A LAN or loopback endpoint needs `allow_local_endpoints=True`. With that flag set, `utils/net.py::validate_base_url` accepts HTTPS to any public address too: its loop only rejects a non-public IP when `allow_local` is False (`:146-149`, *verified*). Nothing in the design ties `owner_lan` to a private or link-local address. A rented cloud GPU or a tunnel URL labelled `owner_lan` gets O49's "another of the player's machines" disclosure, while a third party can read the traffic.
- **`loopback` only describes the first hop.** A local proxy server such as LiteLLM forwards to cloud APIs, and Ollama has cloud-offloaded model tags. Either way, words "on loopback" leave the machine and no guest disclosure is shown. *Unverified as to current Ollama behaviour.*
- **The provenance can't attest either.** For `third_party`, the disclosure names "the provider", and that name comes from the file. On `_OpenAIBackend`, `LLMResponse.model` is the *requested* model (`model=model` in `_parse_response`), and `.provider` is the local provider key (`openai_backend.py`, around `:506-545`, *verified*). So §4.1's "**reported** model and provider" is not reported by the server on this transport.

**Failure scenario.** The player follows an online guide that sets up a "local" endpoint which forwards to a cloud API. Guests are present, no disclosure is shown, and their words leave the machine.

At minimum, the disclosure text and a Known gap should say what each class can and can't promise. Checking `owner_lan` against private address ranges is unverified as a fix.

**S2. `inference_placement.md::§2.2` (`endpoint_ref`), `::§5.1` and `::§5.2`: who holds an endpoint is self-contradictory.**

Four passages disagree:
- §2.2 says `endpoint_ref` is "resolved only in the gateway".
- §2.2 also says the digest is of "the merged table, without endpoints", which implies the host holds the endpoints and leaves them out of the digest.
- §5.1 says the gateway checks the loopback literal "again", which implies the host checks it first, and the host can't if endpoints are only references.
- The shipped default `loopback` placement sits in `data/agents/placement.yaml`, so for loopback the endpoint is host data.

As written, neither of the following is pinned:
- whether `open(table)` carries endpoints or only references;
- which file holds an `owner_lan` endpoint, which process reads it, and through which gate.

§5.2 defers how credentials are resolved to Phase 4 ("OS keychain or a user secrets file"). That deferral is fine as a mechanism. But the store's format, version and gate, and which process reads it, are contract, because the gateway is unlatched and holds the keys.

**Failure scenario.** The implementer puts `owner_lan` URLs in `placement.local.yaml`, which the host reads. The host's loader refuses a malformed entry, and the refusal echoes the URL through `shown` into the host log and a bug report. §5.2's "never appear in bug reports" is then false.

**S3. `inference_placement.md::§3` ("The channel uses the worker codec's rules") and `::§10`: the gateway's boundaries are not registered as gates.**

- §10 changes only the response-cache row of `boundaries.md` §5.3.
- No gate rows are added for:
  - the gateway-to-host channel, which §3 itself calls untrusted;
  - `placement.local.yaml`, which comes from the player's config directory, can be copied from strangers, and is not covered by `data/`'s row;
  - the credential or endpoint store the gateway reads.
- §8 says the placement loaders become registered gates, but the channel isn't named as one. The worker channel's equivalent row requires golden rejection frames, a planted pickle frame and kill-on-refusal.
- The binding rules are missing. The worker channel binds one actor per channel. The design doesn't say what happens on:
  - a `reply` or `chunk` for an `attempt_id` the host never sent, or already closed;
  - a second `reply` for the same attempt;
  - a `chunk` after its `reply`;
  - a gap in `seq`.

**Failure scenario.** A gateway bug, or a gateway compromised through its HTTP parsing, sends a `reply` for an attempt it doesn't own. The host frees a slot that is still busy, or attaches a reply to the wrong thought. Nothing in the rejection-path tests or the registry would catch it.

**S4. `inference_placement.md::§3` ("Its imports are an allowlist: `maxim.models.language` and the backend modules its transports name"): the allowlist can't hold as written.**

- **Importing any backend runs the package initialisers.** `maxim/models/__init__.py` imports `maxim.models.download`. `maxim/models/language/__init__.py` imports `config` and `router`, and `router` imports `cloud_redaction`, `cloud_audit`, `cost_tracker` and `llama_backend` (all *verified*). So "the router is not on the path" (O46) is true of calls, not of imports.
- **The peer transport imports more at call time.** `_MaximPeerBackend.complete_with_usage` does `from maxim.agents.llm_worker import _normalize_request_context` (`maxim_peer_backend.py`, around `:583`, *verified*). `llm_worker` pulls in `maxim.agents.*` modules (`autonomy`, `prompt_budgeter`, `llm_fallback`, `prompt_builder`, …).
- **A test holding the list will either fail on the peer transport or be widened** to most of Maxim's agent stack. Neither is what §3 claims.
- **Import-time side effects:** I didn't audit every newly pulled module (*unverified*). `config.py`'s profile merge is deliberately deferred to first use (`:1103-1108`, *verified*).

**S5. `inference_placement.md::§3` ("no `HOME`"): leaving HOME unset doesn't keep Maxim out of the user's real home directory, and the gateway has no no-effect test.**

- **The fallback.** With HOME unset, `Path.home()` falls back to the password database. *Verified:* I ran `env -i … python -I -c 'Path.home()'` and it printed `/Users/dennyschaedig`.
- **What that reaches.** `utils/paths.py::data_home` uses `Path.home() / ".maxim"` and runs `mkdir` on it (`:181-203`). `profile_loader` reads `~/.config/maxim/profiles.yml` on the first profile lookup. Both are reachable through Maxim accessors, for example `load_llm_config`, profile normalisation or `models.download`, if the gateway ever builds its `LLMConfig` through them rather than directly.
- **What is clean.** I found no call to `data_home` on the three backends' call paths (`git grep` over `models/language`, `utils/http.py`, `utils/net.py`, `utils/logging.py`, `agents/llm_worker.py`).
- **What else rests only on the allowlist.** The SDKs read `ANTHROPIC_BASE_URL`, `OPENAI_BASE_URL` and `OPENAI_API_KEY`, and the backends fall back to environment keys (`anthropic_backend.py:157`, `openai_backend.py:172`). The environment allowlist is the only thing stopping them.
- **The missing test.** The worker has O14's no-effect test (no file reads or writes, sockets or spawns outside its home). The gateway is unlatched, holds keys and parses hostile network bytes, and the design gives it none. The checklist tests only for leaks of a planted credential or endpoint.

**Failure scenario.** A later change builds the gateway's config with `load_llm_config()`. The gateway then reads the user's `~/.maxim/config/llm.json` and `profiles.yml`, which can carry their own base URLs and keys. Nothing fails, and the placement table is silently overridden.

**S6. `inference_placement.md::§5.1` and `::§2.2`: `owner_lan` traffic may be cleartext.**

`validate_base_url` accepts `http://` to private addresses when `allow_local=True` (`utils/net.py:112-137`, *verified*). Maxim's peer leader is "llama.cpp behind an auth proxy with one shared cluster key" (§1).

The design sets no transport-security requirement for `owner_lan`. So the guests' words, and the Bearer cluster key on every request (`utils/http.py::_build_headers`), can cross the LAN in the clear.

**Failure scenario.** A LAN party on shared Wi-Fi. A guest accepts the disclosure for "another of the player's machines". Anyone on that network reads the prompts and the key.

Either require HTTPS, or make the disclosure and a Known gap say it is cleartext.

**S7. `inference_placement.md::§5.2` ("never appear in … logs … or bug reports"): where the gateway's own output goes is undefined.**

Maxim's backends log to Python logging and to `warn()`:
- `anthropic_backend.py:408`: `warn("Anthropic call failed after %d attempt(s): %s", …, last_err)` logs the raw exception text, unsanitised.
- `openai_backend.py:308`: `warn("Failed to init OpenAI client: %s", e)`.
- `openai_backend.py:241`: the "Blocked base_url" warning.
- `mesh_trace.emit_trace` writes `base_url` into its record (`TraceRecord.to_dict`).

`emit_trace` and `MAXIM_LOG_FILE` are turned on only by `MAXIM_*` variables, which the gateway's environment excludes. That part is good, and *verified*.

The design doesn't say whether the gateway's stdout and stderr are inherited, captured into the host log, or dropped. If they are captured and later bundled into a bug report, endpoint hostnames and provider error text leak.

**Failure scenario.** An `owner_lan` endpoint with a bad hostname. The SDK's exception text names the host. It lands on the gateway's stderr, the host captures it, and a bug report carries it.

The checklist's planted-endpoint test should cover the gateway's stderr explicitly.

**S8. `inference_placement.md::§4.1` and `::§5.3`: the provenance and spend values decoded from a server have no bounds.**

`_OpenAIBackend._parse_response` takes `prompt_tokens` and `completion_tokens` straight from the server and applies `int(...)` without clamping (*verified*). §5.3 multiplies those counts by `price`.

A hostile or broken `openai_compatible` server can:
- report negative counts, which lowers spend and can keep the cap from ever tripping;
- report absurd counts;
- on the peer transport, return a served model name from `/v1/models` of any length and content.

All of these go into provenance, then into the response cache, the rerun manifest and bug reports, which reach strangers' machines (`boundaries.md` §5.3).

Under `boundaries.md` §5.1, the provenance constructor must validate: whole numbers at or above zero with a ceiling, and bounded strings with no control characters. The design names neither.

---

## NIT

- **N1. `::§3`, the `X-Maxim-*` headers.** For an internal endpoint, `utils/http.py::_build_headers` sends `X-Maxim-Agent-Id`, `-Session-Id` and `-Lane` taken from `request_context` or the context variable (*verified*). `_OpenAIBackend` sends `X-Maxim-Request-Id` (a random uuid4) to every endpoint, cloud included. The contract should say that the gateway passes `request_context=None`, sets no context variable, and so sends no NPC, actor or session id. A header test would hold that.
- **N2. `::§5.2`, "The host's text gates are the redaction."** `engine.text.player_text` refuses controls and format characters. It removes no names or personal details. The words "the redaction" overclaim. It would be accurate to say no redaction is applied and consent is the control.
- **N3. `::§2.2`, `id`.** The placement id comes from a user file and is the only form that reaches bug reports. Players will name ids after hosts. Bound its length and character set, and note in the documentation that it is shared.
- **N4. `::§5.2`.** A credential reference that doesn't resolve should be refused at `open(table)` as `refused(auth)`. Otherwise Anthropic's `warn("export ANTHROPIC_API_KEY")` path runs and the call ends as `empty`, which is a misleading outcome.
- **N5. `::§5.3`.** Eligibility is checked when a slot is granted, so calls already in flight overshoot the cap. Each placement can overshoot by up to `max_in_flight × (envelope tokens × price)`. Say that the cap is soft by that bound. Also, a non-streaming call buffers the whole response body inside the gateway, and no memory budget is stated for the gateway process.

---

## What I checked and found sound

- **Keys never cross into the host:** only references do. `error(code)` is a closed vocabulary, and unmapped exceptions become protocol errors rather than relayed text (§2.6, §3).
- **No key reaches the environment:** the gateway gets no keys in its environment and is handed already-resolved entries. `resolved_entry_key` requires `api_key_resolved is True` and then consults no environment variable (`types.py:299-315`, *verified*).
- **Maxim's tracing and log-file paths stay off:** `MAXIM_LANE_TRACE`, `MAXIM_PEER_LOG_REQUESTS`, `MAXIM_LOG_FILE`, `MAXIM_BACKEND_TRACE` and `MAXIM_HTTP_TRACE` are all excluded, because no `MAXIM_*` variable passes. `fetch_leader_debug_status`, which sends the key, is also gated by `MAXIM_LANE_TRACE` (`mesh_trace.py:240`, *verified*).
- **The latch:** `maxim/__init__.py::_self_engage_offline` latches only when `MAXIM_OFFLINE` is set. The gateway's environment excludes it, so the gateway being unlatched is consistent. The host's own start-up refusal (§6.6) is unaffected.
- **DNS rebinding:** owner hostnames are covered by Maxim's address policy, which checks the address actually dialled (#921). The exception is the proxy case, B1.
- **The loopback literal:** a literal address needs no DNS (`getaddrinfo` on a literal), as claimed.
- **What workers can reach:** workers still reach no model endpoint. The host is the only route to the gateway.
- **Maxim's cloud redaction:** the design relies on it nowhere, and doesn't describe OD-I5.
- **The cache and manifest:** they gain only placement ids and provenance, with no endpoints. The manifest's "reported, not refused" rule loosens no integrity check, because the cache's hash check still refuses a mismatch.
