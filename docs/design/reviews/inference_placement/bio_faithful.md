**Verdict: not ready to build. 2 BLOCKER, 6 SHOULD-FIX, 3 NIT.** The agent-facing seam itself is sound: a request names a role, the agent is never told the placement, and the landing tick is modelled. But the design never found Maxim's own shipped capability × placement split, so O46 overrides a recorded Maxim invariant without a filed pushback. It also leaves open where the role comes from, and Maxim derives it from hardware.

Lens: Bio-faithful integration. Reader: one independent agent. Sources: the diff `814dea9..04ab810` in `.worktrees/inference-placement`, and Maxim `origin/main` at 043eab8f (read with `git show` and `git grep` only, never the working tree).

## What I checked and found sound

- **The agent can't learn which placement served it.** §2.1 says it, and nothing about placement crosses `AgentPort`. The reply to `think` is `complete(text)` or the reserved variants (`npcs_and_sem.md` §6.6). The gateway's `reply(..., provenance)` stops at the host. Provenance holds no wall time or cost (§4.1).
- **Placement never moves world time.** The landing tick is modelled, so the O12 speed trait still scales modelled onset and never reads hardware (§6.1).
- **Spend can't reach fatigue.** §5.3 restates the `LLMEnergyTracker` exclusion (`npcs_and_sem.md` §4.6).
- **A prompt doesn't depend on placement.** The role envelope is rendered once, and every placement in the role must fit it (§2.1). The agent's prompt budget, and so how much memory it is shown, can't change with placement.
- **The guest consent rule fails closed** (§5.1, §2.6): with guests present, a request never falls through to a remote placement.
- **Maxim's hybrid plan wants the same record.** `hybrid_arbitration.md:97-98` wants run manifests to stamp "the serving box and the lane placement (local, peer or cloud)". §4.1's per-reply provenance agrees with it, though the design doesn't cite this (NIT-2).

## BLOCKER

### BF-1. Maxim already separated "capability" from "placement", and the design neither cites it nor files a pushback against the invariant it overrides

**Anchors:** `docs/design/inference_placement.md::§9` (the search), `::§0 O46`, `::§1`.

**Defect.** §9 lists its search terms: "empty content", `content=""`, "deadline", "gateway retries", "async router", "multi-peer". It did not search the design's own title word, "placement", nor `FunctionRouter`, "tier" or "lane". Maxim `origin/main` has:

- **A shipped plan.** `docs/plans/archive/lane_capability_placement_split.md` ("ALL PHASES SHIPPED (PRs #357–#360, #362)") makes the *capability tier* (`large`/`medium`/`small`) "a property of the **task**, assigned by `FunctionRouter`". It names a separate *placement axis*: `Origin{LOCAL, CLOUD, PEER}` and a frozen `ProviderPlacement(origin, model, url, api_key_ref, timeout_s)`.
  - That is this design's role × placement table under other names. `role` maps to the capability tier, `egress` to `Origin`, and `credential_ref` to `api_key_ref`.
- **A recorded decision.** The same plan's "Front-gate scope decision" reads: "placement is a first-class TYPE + a compile step, NOT a new resolver … A *second* resolver in `LaneBackendManager` would duplicate `_try_provider` and re-introduce the multi-call hazard".
- **An invariant.** `docs/agents/llm-routing.md:73` makes it `[engineering]`: "Placement rides on `LLMRouter`'s existing `provider_priority`/`_try_provider` failover — NOT a new resolver."

O46 builds exactly that second resolver, in the host. §1's evidence (silent failover, process-global state) may well justify it for a world of agents. But the push-back rule says to name the decision you're arguing against and propose the change in Maxim, never to work around it here. §9's "No ask on the router. Overdrive doesn't use it" is the quiet workaround that rule forbids. The search rule also says an ask that overlaps an existing plan becomes a question to that plan.

**Failure scenario.**
1. Maxim later freezes its tier names and `ProviderPlacement` at 1.0, or extends them (the plan names "per-placement hardware tuning" as a 1.1+ extension).
2. Overdrive's closed role vocabulary and `placement.yaml` schema then diverge from Maxim's on the same concepts.
3. Lesson 29 ("For any game hosting Maxim: let the agent ask for a kind of model, and let the host decide") goes into the engine's documentation contradicting a Maxim invariant it never mentions.

**Proposed fix (unverified).**
- Add "placement", `FunctionRouter`, "capability tier" and `ProviderPlacement` to §9's search, and cite `lane_capability_placement_split.md` and `llm-routing.md:73`.
- File a Phase 3 pushback against that invariant: an embedder that owns scheduling needs placement resolution outside `LLMRouter`. Carry §1's evidence.
- Reuse Maxim's vocabulary where it fits (§2.2's `egress` vs `Origin`), or say why it doesn't.

### BF-2. The contract doesn't say where the role comes from, and in Maxim the tier a function resolves to depends on hardware

**Anchors:** `inference_placement.md::§2.1` ("The role vocabulary is closed … measured at OD-A14"), `::§4.2` (the role is in the cache key).

**Defect.** In Maxim, a caller names a *function* (`agent_inference`, `fear_review`, …). `FunctionRouter.resolve` maps it to a tier and walks that function's fallback when the tier is unavailable (`runtime/function_router.py:73-113`, `:199-214`). For example, `fear_review` is `large` with fallback `("medium",)`.

Which tiers exist is decided by hardware. `runtime/lane_models.py::detect_tiers` is "Auto-detect available tiers based on hardware". It includes `large` only with a CUDA or MPS GPU of at least 4 GB, and `medium` on Mac MPS or CPU-only boxes with at least 8 GB of RAM.

The B1 cut is at `LLMRouter._complete_text` (cand. B1). That is *below* `FunctionRouter`, so the tier has already been resolved by the time the request value exists. Maxim's B1 and B3 texts don't define a "role" field at all (I found no "model role" anywhere in `docs/plans/`).

If the role on the request is whatever tier Maxim resolved in the worker, it carries the hardware, or the worker's lack of backends (OD-A17: "no model backend in the embedded agent"), into the request. That reverses §2.1's promise, and it enters the cache key (§4.2).

**Failure scenario.**
1. On a CPU-only host, the worker's `detect_tiers` has no `large`.
2. `fear_review` resolves to `medium`, and the request carries role `medium`.
3. On a GPU host, the same NPC in the same state sends role `large`. The canonical request differs, so the cached rerun misses and fails loudly on the other machine.
4. In live play, the NPC's safety review runs on a smaller model because of the player's VRAM, through a path that §2.1's table never sees.

**Proposed fix (unverified).**
- State in the contract that the role is the function's *declared* need (the `FunctionSpec` name or its primary tier), never `FunctionRouter.resolve`'s availability-dependent result.
- State that tier fallback is the lane's, through the table.
- Ask B1 (OD-A14) to make the request value carry that declared name and to keep hardware detection out of the embedded worker.

## SHOULD-FIX

### BF-3. "Pinned" doesn't stop capability, or fatigue, from following host load

**Anchors:** `inference_placement.md::§2.4` ("Why `pinned` is the default"), `::§2.6`, `::§2.5` (the last bullet).

**Defect.** §2.4 claims a pinned role "changes model only when that placement fails, and a failure is metered". But load causes failures:
- `timeout` is an outcome (§2.6), and a loopback server that batches more calls in flight answers each one slower.
- A timeout starts a wall-time cooldown, and selection then moves to the role's next placement.
- §2.5 adds that a placement whose slots are held by abandoned calls is "effectively down".

So a busy host, or a higher dial with more thoughts per wall second, moves NPCs onto the next placement. That can be a different model.

Placement also reaches the body. P1c deliberation cycles happen "when the first proposal isn't ready to act" (`npcs_and_sem.md` §4.2 table), and their modelled duration enters mental-fatigue load (`:923`). A weaker model that needs more cycles makes the NPC tire faster, which is the coupling §4.6 forbids ("an NPC would tire faster on a slower GPU"), arriving by another route.

**Failure scenario.**
1. 20 NPCs at 20× on a role pinned to `[local-14b, local-3b]`.
2. The 14B server's latency passes `timeout_s`. It cools down, and replies come from the 3B model.
3. The 3B model's first proposals are more often not ready, so there are more P1c cycles and more fatigue.
4. The same scene at 1× never fails over. The NPC's tiredness and decisions now depend on the dial.

§6.2's test can't see any of this (BF-7).

**Proposed fix (unverified).**
- Say in §2.4 that pinned bounds load-dependence to failure-driven failover, not that it removes it.
- Name the fatigue channel among the Known gaps.
- Consider whether only failures that aren't load-driven (`refused`, `transport_down`) should move a pinned role, while `timeout` waits or fails the thought.

### BF-4. The Known gap is understated: the model profile is now per reply and changes during one NPC's life

**Anchors:** `inference_placement.md::§4.3` ("the Known gap stands as before"), `npcs_and_sem.md::§4.1` (the edited "Model capability" bullet).

**Defect.** Before this design, the model profile was fixed per machine and session: one rig, one profile, like a rendering tier. Under placement it changes mid-session and per reply, for host reasons:
- **health:** cooldowns (BF-3);
- **budget:** reaching the spending cap removes every `third_party` placement mid-session (§5.3);
- **consent:** a guest joining makes remote classes ineligible (§5.1).

An NPC can then write memories while served by a cloud model and reason over them later on a 3B local one, because the player hit $5 or a friend joined.

O12 rejected exactly this kind of host-driven change for speed ("that variation belongs to the person: stable, and independent of whose machine hosts the world"). The design names neither the divergence nor an EARN, ANALOG or OPEN intent for it. "Stands as before" is false: the gap has grown from across machines to within one life.

**Failure scenario.** A playtester sees an NPC visibly "get dumber" when the spend cap trips. Nothing in the Known gaps, the B5 meters or the manifest says a capability change happened inside one NPC's life. Per-placement counts exist, but no record ties a change of model to an NPC.

**Proposed fix (unverified).**
- Restate the gap: "not promised across model profiles, *which may change within a session, per reply, on health, budget and consent*".
- Tag it OPEN.
- Add a per-NPC meter for changes of placement within a role.

### BF-5. A cloud reply cut off mid-stream arrives as `ok`, so whether a thought is complete depends on the transport

**Anchors:** `inference_placement.md::§1` (the "Three facts" list), `::§2.6` (outcomes).

**Defect.** `docs/agents/llm-routing.md:7` and `:51` state that `_OpenAIBackend` uses "lenient streaming". It "silently collects partial output when a chunk iteration raises mid-stream" (`docs/lessons/peer-vs-cloud-streaming-contract.md`, recorded as intentional). `_MaximPeerBackend` raises `BackendDown` in the same case.

§1 lists three backend facts and misses this fourth. §2.6's closed outcomes have no case for a reply that is non-empty but cut off. So a cloud placement hands the agent a truncated thought as `complete(text)`, not as `truncated(prefix, reason)`. A peer placement fails over instead.

**Failure scenario.**
1. A cloud stream drops after 40 tokens of a JSON action reply.
2. The outcome is `ok`, and the agent gets half a reply as complete.
3. Either it is `thought_failed(reason=parse)` or, worse, it parses into a shorter `parallel_actions` list.
4. The same request on a peer placement fails over and returns a whole reply.

What the NPC does then depends on the transport, not on its state.

**Proposed fix (unverified).**
- Add the fact.
- Either map an incomplete cloud stream to `truncated` (if the gateway can detect it, for example from the stop reason) or name it as a gap.
- Add it to OD-I9's ask, against the recorded decision (BF-6).

### BF-6. OD-I9 is filed as a bug report, but it argues against two recorded Maxim decisions without naming them

**Anchors:** `inference_placement.md::§9 OD-I9`, `docs/roadmap.md::OD-I9`.

**Defect.** OD-I9 cites `llm_path_fast_failover.md:771` ("Backend failures raise typed exceptions"). The same quoted block, two lines earlier, reads: "Cloud backend intentionally has retry + cost tracking." The plan's table (`:43`) records `max_gateway_retries=4` as "Reasonable for billed retries | Wrong for peer tunnel". `llm_routing.md` keeps the empty-content signal deliberately, "so `_OpenAIBackend` continues to work for cloud providers".

So the hard-coded retries and the empty signal are recorded design choices, not bugs. The push-back rule requires the item to name the decision it argues against and bring evidence. Filed as a bug report, it will be answered "intended" and closed.

**Failure scenario.** Maxim triages OD-I9 as a bug, finds both behaviours documented as intentional, and declines it. The real argument (a host that owns deadlines needs one call to give one outcome, even on billed providers) is never made.

**Proposed fix (unverified).** Reframe it as a pushback against `llm_path_fast_failover.md:43` and `:769` and against `llm_routing.md`'s legacy empty path, with §1's evidence. Keep "a configurable retry budget, default unchanged" so Maxim's own loop isn't affected.

### BF-7. OD-A23 goes to the wrong place and contradicts OD-A14's own row

**Anchors:** `inference_placement.md::§9 OD-A23`, `docs/roadmap.md::OD-A23` and `::OD-A14`.

**Defect.** OD-A23 asks whether the *backends* honour a per-call deadline. But:
- cand. B3 is only "priority and a deadline … fields of B1's request value, which the host … schedules". It says nothing about backends.
- cand. B1 says "The gateway sits above the backend, not as a cancellable `LLMBackend`", and names the cancel path to build on: "`utils/cancellation` plus `LLMRouter._complete_text_abandonable` (`:985`). The plan says why that does or doesn't suffice."
- Overdrive's own OD-A14 row, unchanged here, ends "Not an `LLMBackend` capability".

So OD-A23 asks for the very backend capability that B1 and OD-A14 decline, and it goes to a candidate that doesn't own it.

**Failure scenario.** Maxim answers "B3 is a field on the request value; the host schedules". The slot-holding gap (§2.5) stays open with no plan owning it, and the roadmap carries two rows that contradict each other.

**Proposed fix (unverified).**
- Put the question to B1's "Ride on" clause instead: does the abandonable path free the transport, or only the caller?
- Reconcile it with OD-A14.
- Note that one backend instance per placement already gives a per-placement `timeout_s`. A per-call deadline matters only below that ceiling.

### BF-8. §6.2's transcript clause can't fail, and the test omits the latency policy it depends on

**Anchors:** `inference_placement.md::§6.2`.

**Defect.** "Under `pinned` the transcript is the same too, since the double answers by request." The double answers by request under `spill` too, so this test can't tell the two policies apart, or catch placement leaking into content. Per the charter, a check that cannot fail is no check.

The invariant that matters here is that the *canonical request* (rendered text, role, envelope version) is the same whatever the placement mix. A placement leaking into the render (BF-2) shows up there and nowhere else.

The test also names no latency policy. Under floor-holding, fillers and yields follow real lateness (`npcs_and_sem.md` §4.4), so "same percepts" across placement mixes would be false by design.

**Failure scenario.** A later change lets the envelope or the role vary with placement. The transcripts still match, because the double ignores the prompt, so the test stays green.

**Proposed fix (unverified).** Assert that the canonical requests are byte-identical across placement mixes. Run the test under `dilate`, and say so. Drop the transcript claim, or check it with a double that echoes a digest of the request.

## NIT

- **NIT-1.** `inference_placement.md::§2.1`: "role" already means leader, peer or solo in Maxim (`runtime/role.py`, `llm_routing.md`'s "role detection"). Using Maxim's "capability tier" or "function", or a distinct name, would avoid confusion in cross-repo threads.
- **NIT-2.** `inference_placement.md::§4.1`: cite `hybrid_arbitration.md:97-98`, Maxim's own ask to stamp the serving box and the lane placement. It is the upstream ally for per-reply provenance.
- **NIT-3.** `inference_placement.md::§6.1` and `§9`:
  - placement makes the "observed LLM latency" in `learned_hold_window.md`'s waiting cost (`:19`) vary per reply, not just per machine. That sharpens the pushback already raised in `npcs_and_sem.md` §5.1 (`:569`); a one-line cross-reference is enough;
  - also cite `deferred/pecking_order_graph_plan.md` (tier availability across machines, "graph-aware, including remote tiers") and `deferred/llm_path_async_router.md` as searched, since §9's "worth telling Maxim when it ranks those plans" applies to them.

## On lesson 29 (`docs/lessons_maxim_in_games.md`)

**SHOULD-FIX (BF-9): the lesson is partly supported, and incomplete in a way that matters.**
- **Supported:** the mesh deletion, the peer system sending a machine's calls to a leader, failover inside `_try_provider`, and empty-content failure on the cloud backends are all at the revision as cited. The remaining citations (`router.py:192`, `:77`, `:201`; `drained_nodes`) are the design's §1 *verified* claims, which the Executor reader checks.
- **Weakened by Maxim's own text:** the first piece of evidence, that every call on one router takes `_inference_lock`, is one Maxim has already answered. B3 was withdrawn because "`AgentFactory` builds no router, so routers are shared at the caller's choice". A host could build one router per placement slot.
- **What the lesson's case actually rests on:** silent failover and process-global state.
- **What it leaves out:** Maxim already split capability from placement and decided that placement "rides on" the router (BF-1). A lesson meant as "the evidence base for pushbacks" should state the decision it pushes against, or its generalisation ("For any game hosting Maxim…") reads as uncontested when it isn't.

**Proposed fix (unverified).** Drop the serialisation argument or answer B3's per-router reply, and name the invariant in `llm-routing.md:73` as the decision argued against.

## Upstream framing summary

| Item | Searched properly? | Duplicates a Maxim plan? | Framing |
|---|---|---|---|
| O46 (no Phase 3 item) | No: "placement", `FunctionRouter` and "tier" weren't searched | Overrides `lane_capability_placement_split.md` and `llm-routing.md:73` | Missing pushback (BF-1) |
| OD-I9 | Partly | No, but it argues against recorded decisions | Filed as a bug report; should be a pushback naming `llm_path_fast_failover.md:43` and `:769` (BF-6) |
| OD-A23 | Partly | Overlaps B1's "Ride on" cancel clause | Addressed to the wrong candidate; contradicts OD-A14 (BF-7) |
| OD-A14 rewording | — | B1 defines no role field | Must say where the role comes from (BF-2) |

Counts: **BLOCKER 2** (BF-1, BF-2), **SHOULD-FIX 6** (BF-3 to BF-8, plus BF-9 on the lesson, 7 in all), **NIT 3**. Every proposed fix above is unverified: I ran nothing beyond reading Maxim `origin/main` at 043eab8f.
