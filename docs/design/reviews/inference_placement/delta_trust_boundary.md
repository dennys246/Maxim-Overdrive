**Verdict: one new contract BLOCKER (taint only travels through speech). Every round-1 finding is fixed in the contract, but four fixes leave a residue that the new findings below describe. New: 1 BLOCKER, 8 SHOULD-FIX, 7 NITs.**

Lens: Trust boundary, delta round. Design reviewed: `docs/design/inference_placement.md` v2 at caca211, fold diff `274f297..caca211`.

How I read Maxim: only `origin/main` 043eab8f, with `git show` and `git grep`. Anything marked *verified* is something I read there. I did not look into OD-I5.

---

## 1. Statuses of my round-1 findings (read from the tree at caca211)

| # | Status | Evidence |
|---|---|---|
| B1 system proxy | **fixed** (contract) | IP::§1.3 F9, ::§2.3 item 4 and ::§5.3 treat a proxied gateway as `third_party`. OD-I10 is in `roadmap.md`. The check runs at the wrong time: new D-S3. |
| B2 consent outlives session | **fixed** for speech | IP::§0 O51 and ::§5.1 key consent per speaker and per class, saved with the save, and taint is computed by the host. The rule doesn't cover non-speech channels (new D-B1), and its clearing rule is unsound (new D-S1). |
| S1 egress is only declared | **fixed** (contract) | IP::§5.2 adds the class promises, the `owner_lan` address ranges, the loopback first-hop gap, and says provenance can attest the provider only where the transport reports it. The claim it adds about rented machines is false: new D-S2. The promised Known gap is not written: D-N5. |
| S2 who holds an endpoint | **fixed** | IP::§2.2 has the three-file table, with `endpoints.yaml` read by the gateway only. IP::§5.4 says the host holds neither endpoints nor keys. IP::§3.5 pins the credential store as a gate read in the gateway. Its format waits for Phase 4, and that trigger is stated. |
| S3 gates unregistered; binding rules | **fixed** | IP::§3.5 adds the rows with golden rejection files. IP::§3.3 has the binding rules: unknown, finished, foreign or second `reply` kills the gateway, and attempt ids carry the generation. A gap in `seq` doesn't arise while O50 holds. `boundaries.md` §5.3 points to IP §3.5 rather than holding the rows itself; acceptable. |
| S4 import allowlist | **fixed** | IP::§3.2 records the transitive module set, including the peer transport's call-time import of `llm_worker`, and a test holds it. |
| S5 HOME fallback; no-effect test | **fixed** | IP::§3.2 sets `HOME` and `XDG_*` to the gateway's home, builds `LLMConfig` directly, adds a no-effect test and a planted `llm.json`. The test as written can't pass on the shipped path: new D-S5. |
| S6 cleartext on the LAN | **fixed** | IP::§2.2 `cleartext` and IP::§5.4: `http://` needs `cleartext: true`, and the disclosure says the traffic and key are readable. |
| S7 gateway output | **fixed** in the design | IP::§3.2: stdout and stderr go to a gateway log that is never bundled. `checklists.md` contradicts this: new D-S4. |
| S8 unbounded reported values | **fixed** as bounds | IP::§4.1: counts are whole numbers from 0 to 10⁷, strings at most 128 characters with no controls. What happens to a value outside the bounds is not stated: new D-S6. |
| N1 `X-Maxim-*` headers | **fixed** | IP::§3.2 passes `request_context=None` and sets no context variable. *Verified:* `llm_worker._normalize_request_context(None)` falls back to the context variable, then to an empty context, so no agent, session or lane id is sent. The test's wording is wrong: D-N3. |
| N2 "the redaction" | **fixed** | IP::§5.4 now says no redaction is applied and consent is the control. |
| N3 id | **fixed** | IP::§2.2 `id`: `[a-z0-9_-]{1,32}`, and players are told it is shared. |
| N4 unresolved credential | **fixed** | IP::§5.4 and ::§2.6: an unresolved reference fails at `open` as `failed(auth)`. |
| N5 soft cap; gateway memory | **fixed** | IP::§5.5 states the cap is soft. Gateway memory is a B5 row (IP::§8, `standards_backlog.md` B5). |

---

## 2. New findings in the fold

### BLOCKER

**D-B1. `inference_placement.md::§5.1` ("Taint passes through speech"). Contract.**

O51's taint rule counts only speech. But guest text reaches prompts through other channels. `npcs_and_sem.md` §6.6 sends every guest string that can reach a prompt through `engine.text.player_text`, and lists them: "display names, imagined-object labels, written text in the world".

Those strings are world state. They persist in the save, and any NPC that perceives the object reads them, whether or not it ever heard the guest.

**Failure scenario.**
1. Monday, co-op: a guest imagines a sign with a personal message, then leaves.
2. Tuesday: the host plays alone with a Claude placement opted in.
3. An NPC that never heard the guest walks past the sign. The words enter its observation and its prompt.
4. The host's taint set is empty, because nobody spoke. So `third_party` is eligible, and the guest's words go to Anthropic without the disclosure O18 requires.

This is round-1 B2's defect again, through another channel. The host can compute the missing taint: it owns the world objects, their authors and who perceived them. So the fix is in the contract text: taint comes from perceiving any guest-supplied string, by any channel, and §6.6's list of such strings is the closed set. Under O28 the owner may choose to defer co-op as a whole, but the rule as recorded in O51 is wrong as written.

### SHOULD-FIX

**D-S1. `inference_placement.md::§5.1` ("ineligible … until O17's purge has removed that speaker's words"). Contract.**

The taint is computed by the host from perception, deliberately conservatively. The purge works differently:
- it removes records by the memory-write provenance sets (`npcs_and_sem.md` §6.6);
- those sets are the agent's own account, carried by OD-A18's generate vs apply;
- O26 calls the host's version only a "provenance lower bound".

So the design never says how a purge clears a host-computed taint. There are two readings, and both are bad:

1. **Taint never clears for an NPC that caught it second-hand.** Host taint marks NPC B for having heard A at all, and nothing in a purge of guest G clears that. Because taint passes through speech, one guest visit spreads to every NPC within a few conversations. Remote placements are then lost for the life of the save, and only a purge the guest asks for could change that. §6.2 counts consent among the reasons a placement changes but doesn't state this consequence.
2. **Clearing trusts the worker's provenance sets.** That contradicts "never relies on the worker's own account". It also misses paraphrases and summaries that O26's verbatim "quoted" test doesn't catch.

The contract needs a clearing rule, and the consequence named, as a Known gap or OPEN.

**D-S2. `inference_placement.md::§5.2` (`owner_lan`: "A rented cloud machine can't be labelled as the player's own"). Contract (the promise and the disclosure), plus mechanism.**

- **The claim is false.**
  - A cloud GPU joined to a Tailscale network has a 100.64.0.0/10 address, and one reached through a VPN subnet has a 10/8 address. Both pass the check.
  - On shared Wi-Fi (a LAN party, a hotel), other people's machines have private addresses too.
  - An address range proves the route isn't the public internet. It doesn't prove whose machine it is. O49's disclosure text ("another of the player's machines") inherits the overclaim.
- **"Dialled address" holds only for `http://`.** *Verified* at `utils/net.py:94-108` (`base_url_address_policy`): Maxim applies `"private"` at connect time only for `http://`, and `"any"` for `https://` when `allow_local` is set. Both `openai_backend.py:281-285` and `maxim_peer_backend.py:862` derive the policy that way, and the gateway can't pass its own.
- **So for an HTTPS `owner_lan` endpoint, the gateway's check can only be a lookup before the connect.** A DNS answer that changes between the lookup and the dial defeats it. Maxim's own docstring names that failure.

**Failure scenario.** A guide's hostname answers 192.168.x.x to the gateway's lookup, then a public address when the SDK dials. Or a Tailscale-joined cloud VM, behaving as configured. In both cases guests' words reach a third party under a disclosure that says "the player's machine".

**D-S3. `inference_placement.md::§5.3` ("At start, each gateway reads `urllib.request.getproxies()`"). Mechanism.**

Maxim reads proxies when it builds a client, not when the gateway starts. *Verified:*
- `_proxy_mounts` calls `get_environment_proxies()` inside `_checked_client` (`utils/http.py:839`, `:881`).
- Clients are built lazily on first use and cached (`HTTPClientRegistry.get_client`, `:496-529`).
- `_OpenAIBackend._ensure_client` builds a new checked client after an auth reset (`openai_backend.py:281-300`).
- The Anthropic SDK client is built lazily in `_ensure_client`.

**Failure scenario.** A system proxy is switched on between the gateway's start and its first call, or before a client is rebuilt after an auth reset. That is a corporate VPN profile, or a debugging proxy opened mid-session. The gateway reported `ready` with no proxy, so the placement stays `loopback` with guests present, and calls go through the proxy.

The check has to sit wherever a client is built and report each time; that is a build-step test. Also, Maxim already has `HTTPEndpoint.strict_address_check` (`utils/http.py:228`), which drops the proxy mounts. The peer backend registers its endpoint without it (`maxim_peer_backend.py:865`). See D-N7.

**D-S4. `checklists.md` (the lane's model: "a planted credential and endpoint found in no log, gateway log, …") against `inference_placement.md::§3.2` (gateway log). Contract (the leak rule).**

- **The design implies the gateway log may hold endpoints.** That is the point of "never bundled".
- **The checklist demands it holds none.** On the Phase 4 path, Maxim writes endpoints into that log: the "Blocked base_url" warning, `warn("Failed to init OpenAI client: %s", e)`, and SDK exception text through `anthropic_backend.py:408`. So the test either fails, or gets met by scrubbing stderr, which is a band-aid.
- **Pick one rule.** Two of its terms are also unpinned:
  - where "under the session" sits: inside the save directory or not, since saves travel (`boundaries.md` §5.3);
  - whether the gateway home and log are in O26's purge reach, in case provider error text ever echoes the prompt (*unverified*).
- **The log has no size bound.**

**D-S5. `inference_placement.md::§3.2` (no-effect test: "no file reads or writes outside the gateway's home, and no socket except to its placement's endpoint"). Mechanism.**

As written, the test forbids things the gateway must do:
- read `endpoints.yaml` from the player's config directory, and the credential store (a file or the OS keychain);
- import the standard library and site-packages;
- read the CA bundle;
- look up hostnames, which uses a socket to the resolver.

It also leaves out spawns, which O14's worker test includes, and the gateway is the process that isn't latched. The test needs a stated allowed set, with spawns forbidden, or it gets widened at build time without review.

**D-S6. `inference_placement.md::§4.1` (bounds) and `::§5.5` (spend). Contract.**

Two things are missing.

1. **What happens to a value outside the bounds.** It could refuse the frame, a protocol error that kills the gateway, blamed on the host, so no cooldown and a loop of restarts. It could clamp. It could become null.
2. **What spend counts when the reported counts are zero, absent or refused.** Worst-case accounting covers only abandoned and killed calls. So an `openai_compatible` `third_party` server that reports `prompt_tokens: 0, completion_tokens: 0` records zero spend, and the cap single-player depends on never trips. The host could put a floor under the counts with the envelope's own token counter; that fix is *unverified*.

**D-S7. `boundaries.md::§5.3` (response cache row). Contract.**

The fold replaced "the strictest contract: versioned, strict decoder, size budgets; an entry holds only raw output, the canonical request and its provenance" with a pointer to IP §4.2. §4.2 says what an entry holds, but says nothing about a version, a strict decoder or size budgets.

The cache reaches strangers' machines. A builder reading the registry no longer finds those three requirements anywhere. Restore them in the row, or state them in §4.2.

**D-S8. `inference_placement.md::§3.3` ("The largest frame is bounded by the largest envelope") and `::§2.6`. Contract.**

The envelope is in tokens, but bytes per token have no bound, and a hostile server can ignore `max_tokens`. No outcome maps a reply larger than the frame budget.

**Failure scenario.** The gateway emits an oversized frame, the host refuses it as a protocol error and kills the gateway, blamed on the host, with no cooldown. It restarts and the next call does the same, until `max_restarts`. The gateway also buffers the whole body; B5 now meters that, but nothing bounds it.

### NIT

- **D-N1. `::§3.3` `open(placement)`: "transport settings only". Contract.** The gateway's §5.2 checks need `egress` and `cleartext`. Say that `open` carries them, so a `loopback` id mapped to a cloud URL in `endpoints.yaml` is refused.
- **D-N2. `::§2.2`, the player's `endpoints.yaml`. Contract.** Two things are unstated:
  - whether it replaces the shipped file whole, as `placements.yaml` does;
  - what is refused when the two files' ids don't match: a placement with no endpoint, or an endpoint with no placement.
- **D-N3. `checklists.md`, "no `X-Maxim-*` ids". Mechanism.** The peer endpoint is `internal=True`, so `_build_headers` always sends `X-Maxim-Request-Id` (a fresh uuid) and `X-Maxim-Protocol-Version` (*verified*, `utils/http.py:1029-1031`). Word the test as no agent, session, lane or parent ids, or it can't pass.
- **D-N4. `::§5.3` and `::§5.1`, a proxied gateway in single-player. Contract.** §5.3 says it is "disclosed in single-player". §5.1 says `third_party` needs an opt-in and a cap. A proxied loopback placement has no `price`. Say which rule applies.
- **D-N5. `::§5.2` and `::§5.4`.** Both promise a Known gap (the loopback first hop; the cleartext LAN). Neither is in `architecture.md`, and no step names when they are written.
- **D-N6. `::§5.2`, `owner_lan`.** Like loopback, it promises only the first hop: an SSH port forward or a proxy on the LAN can sit behind it. Maxim's `"private"` includes loopback too. The disclosure should say this.
- **D-N7. `roadmap.md` OD-I10 (B22).** The ask is "a per-backend way to switch proxies off". Maxim has `HTTPEndpoint.strict_address_check` (`utils/http.py:228`, `:881`), which drops the proxy mounts. The ask should cite it and become "let the backends' callers set it", not a new mechanism.

---

## 3. What I checked and found sound

- **Speaker identity.** A speaker is an actor and its session (`npcs_and_sem.md` §6.6), so a guest who rejoins must accept again. That is the conservative direction.
- **When consent is read.** Eligibility is checked when the slot is granted, which is after the render. So the taint at dispatch includes every word the prompt holds. Retries pick their placement again (§2.4), so they are checked again.
- **Reruns.** A rerun never dispatches (§4.2), so no egress decision arises on a rerun.
- **The gateway's environment.** Setting `HOME` and XDG to the gateway's home closes the password-database fallback. Building `LLMConfig` directly keeps `load_llm_config` and profiles off the path.
- **No audit or cost files.** The three backends call no `cloud_audit`, `CostTracker` or `data_home` (*verified* by `git grep`).
- **Provenance.** The host stamps placement, egress and model, and the gateway supplies only the bounded reported fields (§3.3). Provenance carries no endpoint, credential or cost, and it never reaches cognition.
- **Endpoints in the host's echoes.** Refusals carry the placement id, never an endpoint (§3.5). The host never reads `endpoints.yaml`, so its `shown` echo can't leak one.

Severity summary: D-B1 is a contract blocker and must fold, or the owner rules on it. D-S1, D-S2, D-S4, D-S6, D-S7 and D-S8 are contract. D-S3 and D-S5 are mechanism, deferred to `phase1/agents`' checklist, which is the trigger.
