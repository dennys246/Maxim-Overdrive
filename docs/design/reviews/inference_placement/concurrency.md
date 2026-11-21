**Verdict: not ready to build.** 6 BLOCKER, 6 SHOULD-FIX, 2 NIT. The contract promises "the world always moves again", but nothing bounds how long a slot is held. A full pinned placement blocks the whole queue. The gateway's hang rule is undefined. The channel's attempt lifecycle has races. And the `chunk` message has no producer in Maxim's backends.

Lens: Concurrency and lanes. Read: `docs/design/inference_placement.md` (whole); the diff `814dea9..04ab810` in `npcs_and_sem.md`, `boundaries.md`, `checklists.md` and `architecture.md`; `npcs_and_sem.md` §1, §4.2–§4.5, §6.3 and §6.6; `boundaries.md` §7.1; `realtime_lanes_coop.md` §4; `sem_stimuli.md` §4.3. On Maxim `origin/main` 043eab8f (via `git show`): `models/language/{cancellation,backend_protocol,anthropic_backend,openai_backend,maxim_peer_backend}.py`, `utils/http.py`, `utils/cancellation.py` and `router.py:185-200`.

---

## BLOCKER

### C1. `inference_placement.md::§2.5 Capacity` (with `§2.2` `timeout_s` and `§1` fact 3): nothing bounds how long a slot is held
§2.5 says a slot is held "until the backend call returns". §2.2 calls `timeout_s` "the wall ceiling per call". No layer under the gateway enforces a whole-call bound, so "until it returns" has no upper limit:
- **Maxim says so itself.** `utils/http.py::TimeoutPolicy` (*read at 043eab8f*): "`read_s` bounds each socket read … not the whole body. `pool_s` … is NOT a whole-request deadline, and nothing in httpx is (#1706)."
- **Peer backend.** `_MaximPeerBackend._get_timeout_policy` maps `timeout_s` (default 300) to `read_s`, "a per-read bound, not a whole-request one (#1715)".
- **Anthropic backend.** It builds `Anthropic(api_key=…, timeout=self._get_timeout())` (`:237`). The SDK applies that per phase, not per call. It doesn't pass `max_retries`, so the SDK's own default retries run under the backend's loop. The OpenAI client kwargs (`openai_backend.py:276-281`) also omit `max_retries`. That the SDK defaults to two retries is from my knowledge of the SDK; I didn't read it at a revision.
- **Backend retries on top.** `_AnthropicBackend` defaults to `max_retries=2` and `capacity_max_retries=6`, "≈ up to ~90s of backoff worst-case" (`:172-188`). §1 says these are "configurable to zero", but no contract line requires the gateway to set them to zero. `_OpenAIBackend` adds `max_gateway_retries = 4`, hard-coded.

**Failure scenario.** A loopback llama.cpp server under memory pressure streams one token every 40 s. No read ever exceeds `read_s`, so the call holds its slot and its gateway thread for as long as generation lasts: minutes, or until `max_tokens`. A second case: a 529 storm on the Anthropic placement. One attempt becomes up to 7 backend tries, each with SDK retries inside it, plus about 90 s of backoff. The slot is held throughout, and §2.5 counts it as one call.

§1 fact 3 also states the wrong thing. "The timeout belongs to the backend instance" implies the instance timeout bounds a call. It bounds reads.

*Fix direction (unverified):* the contract needs a whole-call bound owned by the gateway. That means a kill-able unit: a per-placement or per-call subprocess, or closing the call's HTTP client. It must also require retries to be zero at both the backend layer and the SDK layer.

### C2. `inference_placement.md::§2.4 Selection` and `§2.5`: a pinned placement full of abandoned calls is "full", never "failed"; the liveness ceiling may never start
- §2.5: a placement whose slots are all held by abandoned calls "is effectively down … selection treats it as full".
- §2.3: being full is not an eligibility condition.
- §2.4 `pinned`: "If its slots are full, the request waits for one."
- No outcome is produced, so §2.6 starts no cooldown, and no failover to the role's second placement ever happens. O48's "changes model only when that placement fails" makes this permanent, because "full" is not "failed".

Then the liveness question:
- `npcs_and_sem.md` §4.4 words the ceiling as "a call past the host's wall ceiling".
- The no-deadlock invariant's wait set "counts only" calls in flight.
- A request waiting for a slot is not a call.

**Failure scenario.** C1's trickling server, under dilate, holds all `max_in_flight` slots of the role's pinned loopback placement. The next request, due at tick T, waits for a slot and is never dispatched. If the ceiling is measured from dispatch, the simulation lane waits at T without end: the world never moves again, which breaks the invariant §2.5 says "still holds". If the ceiling is measured from enqueue, every later thought of that role waits the full ceiling and ends as `thought_failed(timeout)`. Every such thought dilates the world by the ceiling, and failover never happens.

§2.5's "The ceiling is the lane's, not the slot's" doesn't say when its clock starts. *Unverified:* the contract must start the ceiling at the moment the simulation lane begins waiting (enqueue), and must give "full by abandoned calls past N" an outcome that health can act on.

### C3. `inference_placement.md::§3`, "A hung or dead gateway never freezes the world": the hang criterion is undefined, and either reading fails
"Past its wall ceiling it is killed" names no ceiling and no thing being measured. A gateway is many concurrent calls plus I/O threads, not one call. Unlike a worker's per-park ceiling, there is no single response whose lateness means the gateway is hung.
- **Reading A: a call past its ceiling means the gateway is hung.** One stuck cloud call kills the whole gateway. "Every attempt in flight ends as `transport_down`", and §2.6 starts a cooldown on every placement that had an attempt in flight. In the scenario, one third-party call hangs while ten loopback calls are healthy. All eleven fail. Loopback cools down, and with guests present it is the only eligible class, so every role has no eligible placement and every thought ends as `thought_failed(unavailable)`. The blast radius is every NPC.
- **Reading B: hung means the process stops answering, judged by a heartbeat.** It never fires on C1's stuck call, because the gateway's I/O thread is still alive. C1 and C2 remain unbounded.

The design has one gateway for all placements, so it has no fault isolation between placements. That is a contract-level choice (§3, "a second kind of host-owned child process"), so it belongs in the design, not in a build step.

### C4. `inference_placement.md::§2.4`, "Choosing a placement for the request at the head of the queue": head-of-line blocking across placements
Selection runs only for the head of the queue, and under `pinned` the head waits for a slot. As written, nothing behind it is dispatched in the meantime.

**Failure scenario.**
- Role `plan` is pinned to a cloud placement with `max_in_flight: 2`, both slots busy, and its request R1 is due at tick 100.
- Role `speech` is pinned to an idle loopback placement, and its request R2 is due at tick 101.
- R1 is the head and waits. R2 is never dispatched, though its placement is free.
- At tick 101 under dilate, the world waits for R2, which hasn't started. Every delay on the cloud placement passes to every role.

This is priority inversion caused by the queue's shape, not by load. It also defeats the purpose of §4.4's "dispatch by deadline", which exists so that "the host never waits on a request queued behind later-due ones". Here the host waits on a request queued behind an earlier-due one that can't run.

The opposite reading (skip a blocked head) is also not stated, and it needs its own rule. In both cases the contract has to say which. *Unverified:* earliest-deadline order per placement (or per role), with a slot granted to the earliest-due request that can use it.

### C5. `inference_placement.md::§3` channel (`dispatch`, `cancel`, `reply`) and `§2.6`: the attempt lifecycle has unspecified races, including a double slot release
The message kinds are closed, but their ordering semantics are not. Each case below is a concrete race:
1. **Cancel crosses a reply.** The host sends `cancel(a)` just as the gateway writes `reply(a, ok)`. The contract says that after a cancel the gateway "sends `reply(outcome=cancelled)` when the call returns". If the gateway sends it, attempt `a` gets two replies. "A reply frees its slot" then frees one slot twice, and the placement runs `max_in_flight + 1` calls from then on. If the gateway treats the cancel of a finished attempt as unknown, then by the codec's rules ("An unknown kind … ends", "an unmapped exception is a gateway protocol error") the gateway is killed, with C3's blast radius.
2. **The host's own `timeout`.** §2.6 lists `timeout` as an attempt outcome decided by the lane. The call keeps running (§2.5) and later produces the gateway's `reply(ok)`. One attempt then has two outcomes, against "Every attempt ends in one closed outcome". The contract doesn't say whether the host sends `cancel` on its own timeout, so the gateway may keep relaying `chunk`s for an attempt the lane has given up on.
3. **A retry after a timeout runs beside the original.** Under dilate, a timed-out attempt is dispatched again (§2.6) while the original is still in flight. If the retry goes to the same pinned placement after its cooldown, each round adds one abandoned slot. On a hung placement that converges on C2 after `max_in_flight` timeouts.
4. **Replies after a kill.** After a kill, frames from the dead gateway may already be in the host's receive buffer. If attempt ids are counters scoped to one gateway's lifetime, a buffered `reply(7)` from the old gateway can be matched to the new gateway's attempt 7.

*Unverified:* the contract needs exactly one terminal `reply` per `attempt_id` that the gateway accepted, and `cancel` of a terminated attempt as a no-op that is not an error. The host must own the slot count and keep each attempt's outcome as the first one it decided; later replies are dropped and metered. Attempt ids must be unique across gateway generations, and the old channel closed before its attempts are declared `transport_down`.

### C6. `inference_placement.md::§3` `chunk(attempt_id, seq, text)`, with `§6.3` "time to first token": no Maxim backend can produce a chunk
At 043eab8f, `complete_with_usage(stream=True)` collects the whole stream and returns one `LLMResponse`:
- `anthropic_backend.py::_stream_response` builds `text_parts` and returns at the end;
- the OpenAI backend's `_stream_response` does the same;
- the peer backend's `_stream_response` (`:987+`) iterates `iter_lines` internally.

`LLMBackend` has no callback, iterator or yield; I searched for `on_chunk`, `on_token`, `callback`, `yield` and `Iterator` across the language backends and found none. So in Phase 4 the gateway has nothing to relay until the call returns.

The consequences reach the lanes:
- `npcs_and_sem.md` §4.5's lever 3 ("Streaming the first token … closes on time-to-first-token") is unavailable.
- §6.3's meter can't be measured.
- `cancelled(prefix)` semantics that depend on mid-stream chunks (§6.6) never get a prefix.
- A slot is held for the whole generation with nothing to show for it.

§9 lists no upstream ask for a streaming callback. This contract message has no producer on the shipped transport.

---

## SHOULD-FIX

### C7. `inference_placement.md::§1` and `§3`: the backends were written for serialised use, and the design calls them concurrently
Maxim's router takes `_inference_lock` on every call (`router.py:192`). Removing that lock is the point of O46, but nothing establishes that the backends are safe under concurrent calls on one instance, and the design never says whether a placement gets one instance or one per slot. Evidence at 043eab8f:
- **OpenAI backend.** `_OpenAIBackend._ensure_client` (`:292-302`) closes a retired HTTP client on the next auth reset, on the stated assumption that "a client retired two resets ago has no in-flight caller". That holds under the router's lock and is false with N calls in flight: a persistent 401 on one thread closes the client another thread is streaming on.
- **Anthropic backend.** An auth error sets `self._client = None` (`:384-385`), while `_stream_response` reads `self._client` (`:475-477`). A concurrent call that starts then returns `LLMResponse(content="")`, the `empty` outcome. That is a failure caused by a race, and it gets metered as the placement's health.
- **Peer backend.** `utils/http.py::_EndpointRegistry.register` "later calls replace earlier ones" and `close()`s the old client. The peer backend registers under `peer-{provider_key}`. Two `maxim_peer` placements whose backends share a `provider_key` in one gateway would send each other's calls to the wrong endpoint, and closing one would abort the other's in-flight streams.

*Unverified:* the contract should state the instance model and add a build-step test for N concurrent calls against a fake server that injects an auth failure.

### C8. `inference_placement.md::§2.6`, "A failure starts that placement's cooldown": the health law feeds back on load
- **A slow call trips a placement-wide cooldown.** `timeout` is usually a load symptom. Under load, timeouts cool placements, which pushes their traffic onto others (spill, or failover after a pinned failure), which raises their latency and their timeouts. That is a metastable retry storm.
- **A single placement turns one timeout into a burst of failures.** With guests present and a single loopback placement, one slow call makes every request in that role `thought_failed(unavailable)` for the whole cooldown: a burst of tier-3 failures across all NPCs.
- **Recovery is all or nothing.** When a cooldown ends, the placement takes full traffic again, with no single probe call first. A hard-down placement therefore costs a full ceiling-length stall once per cooldown period, indefinitely.
- **Per-request outcomes cool everyone.** `context_overflow` and `refused(policy)` are properties of one request, not of the placement, but as written they cool the placement for every NPC.

This is a law and can be swapped. But which outcomes count as placement health is contract, because the meters and the guest gate depend on it.

### C9. `inference_placement.md::§2.5` and `§3` restart: a slot models client concurrency, not server capacity
- **Abandoned work keeps the server busy.** An abandoned or killed call keeps running on the server: llama.cpp's parallel slots, or the provider. After a gateway restart, the host's slot accounting resets (every attempt is `transport_down`, every slot free), while the loopback server is still generating the orphaned requests. The new gateway dispatches `max_in_flight` fresh calls onto a saturated server. Time to first token spikes, more calls time out, and with C3 reading A that loops.
- **Killed calls escape the spending cap.** A killed third-party call's tokens are spent but never reported. §5.3 computes spend from the provenance of replies, so repeated kills undercount spend and the cap can be overrun.
- **The peer transport has a hidden queue.** The peer backend's pooled client has `DEFAULT_POOL_PER_ENDPOINT = 10` (`utils/http.py:67`) and `pool_s = timeout_s + 60` s. A `maxim_peer` placement with `max_in_flight > 10` queues calls inside httpx for up to 360 s by default. That queue is invisible to the lane's slot meters and to its earliest-deadline order.

### C10. `inference_placement.md::§3`, "The channel uses the worker codec's rules": the codec is reused, but not the I/O model
The worker channel is lock-step (request, then park), and still `sem_stimuli.md` §4.3 needs a per-channel outbox, a "partial send is normal" rule and a socket-buffer bound checked at start. The gateway channel is fully asynchronous in both directions: `dispatch` frames can be as large as a role's envelope, and `chunk`s stream continuously.

**Failure scenario.**
- The host's thinking-lane thread blocks writing a 100 KB `dispatch` into a full socket buffer.
- The gateway's single I/O thread blocks writing `chunk`s back to the host, which isn't reading.
- Neither side reads, so they deadlock. The gateway looks hung and is killed (C3).

A single writer thread in the gateway also blocks every attempt's reply behind one large frame. §7 says "each transport checks its own properties", but the gateway channel's properties aren't stated.

### C11. `inference_placement.md::§3` lifecycle (`shutdown`, kill, "starts a new gateway"): not every start has a bounded stop
- **Shutdown can't interrupt calls in flight.** Maxim's abort is `cancellation.request_shutdown()`, which is process-wide and checked only between retries (`anthropic_backend.py:375`), and before the peer call (`:555-566`). An HTTP read in progress runs to its per-read timeout (60–300 s). §4.4's "`stop` … joins every thread" needs the host's gateway reader to be joinable while the gateway is stuck: shutdown, then a bounded wait, then a kill. The design states none of these.
- **The gateway may not exit when the host dies.** On a host crash, the gateway sees EOF. If its call threads are non-daemon, Python waits for them at exit, so the orphaned gateway keeps spending cloud tokens until its reads time out.
- **Restarts are unbounded.** A gateway that crashes at `open(table)`, for example on credential resolution, restarts in a loop, with no cap, no backoff and no record.

### C12. `inference_placement.md::§2.4`: non-preemptive slots shared across roles
Two roles may list the same placement. A conversation request (earliest deadline) waits behind `max_in_flight` long `plan` calls already dispatched, which can't be pre-empted (C1). §4.5's lever 2 ("a faster model for speech turns") assumes they are separate, but the contract allows sharing and gives no reserved capacity or bound. §6.3 meters the wait but doesn't limit it.

---

## NIT

- **N1. `inference_placement.md::§2.2` `max_in_flight`.** There is no upper bound. Gateway threads are bounded by the sum of `max_in_flight`, plus the I/O threads, plus the number of outstanding requests, and `placement.local.yaml` is user-written. The thread model and its bound are a mechanism to state in the build step.
- **N2. `inference_placement.md::§3`, "After a `cancel`, the gateway stops relaying chunks".** Chunks already in the socket arrive after the host decides to cancel. The guarantee has to be the host's (drop chunks for a cancelled attempt), not the gateway's.

---

## Checked, no finding

- **No thread held by an agent.** An outstanding request is a `Pending` value (§2.5; `npcs_and_sem.md` §4.4, §6.3). Gateway threads are held only by calls. Neither selection nor retries reintroduce an agent-held thread.
- **The barrier never waits on the gateway.** Agents with a `Pending` are parked. Only the simulation lane's dilate wait depends on a reply, and that depends on C2's ceiling.
- **Earliest-deadline starvation.** Under dilate, a request due later becomes the earliest as ticks advance, and the world waits for it there, so it self-corrects. Under `abandon` the ceiling bounds it.
- **Choosing the placement at slot grant.** This re-evaluates health and consent at dispatch, so a request queued before a cooldown doesn't go to a placement now in cooldown. Consistent.
