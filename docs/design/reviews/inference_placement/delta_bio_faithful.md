**Verdict: not ready to build. 1 BLOCKER (contract), 6 SHOULD-FIX, 4 NIT.** Of my round-1 findings, ten are fixed and BF-3 is still open. The owner's ruling that "load failures wait on the same placement" is not delivered by the v2 contract. Two other sections contradict it, and the real transports don't produce the outcomes it waits on.

Lens: Bio-faithful integration, delta round. Reader: one independent agent. Sources: `git diff 274f297..caca211` in `.worktrees/inference-placement`, and Maxim `origin/main` at 043eab8f, read with `git show` and `git grep` only. I ran nothing else, so every proposed fix below is unverified.

## 1. Status of round-1 findings (set from the tree at caca211)

| Finding | Status | Evidence |
|---|---|---|
| BF-1 placement rule not cited, no pushback | **fixed** | `inference_placement.md::§1.2` quotes the `llm-routing.md:73` invariant, which I verified word for word at 043eab8f. `::§9` searched "placement", `FunctionRouter`, "capability tier" and `ProviderPlacement`. OD-A24 is a pushback that names the invariant (`roadmap.md::OD-A24`). `::§2.2 egress` says why it is not Maxim's `Origin`. One citation in the evidence is wrong (N-1). |
| BF-2 the role comes from hardware | **fixed** | `::§2.1` uses the declared function, never `FunctionRouter.resolve`'s result. `roadmap.md::OD-A14` keeps hardware tier detection out of the worker. The premise behind the fix has a new defect (S-1). |
| BF-3 pinned follows load; fatigue | **open** | The text was added (`::§2.6`, last bullet) and fatigue is named OPEN (`::§6.2`). But `::§2.3`, `::§2.7` and the transports undo it (B-1). |
| BF-4 profile changes within one life | **fixed** | `::§6.2` lists health, budget and consent, tags them OPEN, and adds a per-NPC meter. The registration is thin (N-3). |
| BF-5 cut-off stream reported as `ok` | **fixed** | F3, `stream=False` (O50), and the `truncated(stream_broken)` row in `::§2.6`. Its reason value leaks to the agent (S-3). |
| BF-6 OD-I9 framed as a bug report | **fixed** | `roadmap.md::OD-I9` is now a pushback against `llm_path_fast_failover.md:43` and `:769`, which I verified at 043eab8f. It no longer cites its best ally (N-2). |
| BF-7 OD-A23 sent to the wrong owner | **fixed** | `roadmap.md::OD-A23` now goes to B1's "Ride on" clause, which I verified in `overdrive_refactor_candidates.md:271`. It says "not a backend capability", which matches OD-A14. |
| BF-8 transcript clause can't fail | **fixed** | `::§6.4`: canonical requests must be byte-identical under `dilate`, the test double echoes a digest of its input, and there is a negative control. |
| BF-9 lesson 29 | **fixed** | The serialisation argument is dropped. The lesson names the invariant and OD-A24, and records the search miss. The same wrong citation appears (N-1). |
| NIT-1 "role" | **fixed** | Renamed to "function" throughout, including `npcs_and_sem.md` and the upstream draft. |
| NIT-2 hybrid ally | **fixed** | `::§4.1` cites `hybrid_arbitration.md:97-98`. |
| NIT-3 latency and plan cross-references | **fixed** | `::§6.2` (observed latency) points to npcs §5.1. `::§9` lists the pecking-order and async-router plans as read. |

## 2. New findings in the fold

### BLOCKER

**B-1. Under `pinned`, a function still changes model when the host is under load. Three routes reach it, and the checklist test sees none of them.** Contract. Anchors: `inference_placement.md::§2.6` (last bullet), `::§2.3` item 2, `::§2.4`, `::§2.7`, `::§3.4`, `checklists.md::The lane's model`.

The owner's ruling (§11) is that `overloaded` and `call_timeout` wait on the same placement. Three routes defeat it.

1. **The contract contradicts itself.**
   - Both outcomes are attributed to the placement (`::§2.6` table).
   - "A placement-attributed outcome starts that placement's cooldown" (`::§2.7`).
   - A cooling placement is not eligible (`::§2.3` item 2).
   - `pinned` means "the first *eligible* placement" (`::§2.4`).

   So the first `call_timeout` cools the primary, and every pinned request, retried or new, goes to the second placement for the whole cooldown. That is exactly the move §2.6 forbids. A builder can't satisfy all four sentences.

2. **The real transports never produce these outcomes on the default path.** At 043eab8f, only `maxim_peer_backend.py` raises `BackendOverloaded` (`:1225`) or `BackendTimeout` (`:1250`); `git grep` over `models/language/` finds no other raiser. `_OpenAIBackend` catches every exception and returns `LLMResponse(content="")` (`openai_backend.py:505`), after its own retry loop (`:384-420`).
   - So on `openai_compatible`, a read timeout or a 503 from a busy llama-server ends as `failed(empty)`.
   - Section 2.6 says `failed(empty)` moves the request.
   - `openai_compatible` is the transport §2.2 names for every local model.
   - So the rule holds only on `maxim_peer`, and the scripted-transport test in `checklists.md` ("`pinned` waiting on `overloaded` and `call_timeout`") passes without the real path ever reaching that rule.

3. **The host's own kill is triggered by load.** A call slowed by batching passes `call_ceiling_s`, and the host kills the gateway (`::§2.5`, `::§3.4`). Its attempts end as host-attributed `failed(unreachable)`, which is retried. While the gateway restarts it is not "up", so the next eligible placement serves. After `max_restarts`, the primary is down for the whole session.

**Failure scenario.** 20 NPCs at 20×, `agent_inference` pinned to `[local-14b, local-3b]` over `openai_compatible`. The 14B server slows past its read timeout, the backend returns empty, and the outcome is `failed(empty)`. The placement cools down, and every NPC thinks on the 3B model for the cooldown. At 1× none of this happens. Capability, and through P1c cycles fatigue, follow the dial: the coupling BF-3 named, still there.

**Proposed direction (unverified).**
- Make the pinned rule a selection rule: a load-attributed cooldown doesn't remove a pinned function's primary placement, and pinned requests queue behind it.
- Attribute a ceiling kill on a gateway with calls in flight as load, not as a host or placement failure.
- State that until OD-I9 gives typed errors, `openai_compatible` and `anthropic` can't tell load from failure. Then either treat their `empty` as load under `pinned`, or name this as a Known gap with a strict red gate on a fake server that times out.

### SHOULD-FIX

**S-1. "The declared function name" is a Maxim type, but no Maxim call site declares one, so B1 has nothing to carry yet.** Contract. Anchors: `::§2.1` (first two bullets), `roadmap.md::OD-A14`, `embeddable_agent_DRAFT.md` (the "Changed since v5" bullet).

`FunctionSpec.name` exists (`runtime/function_router.py:49-66`). But at 043eab8f:
- `submit_function` (`worker_pool.py:716`) and `get_backend_for_function` (`lane_backends.py:1034`) have no callers;
- `build_primary_router` returns `manager.get_backend("large")` (`lane_backends.py:2567`);
- `LLMRouter._complete_text` takes no function argument (`router.py:958-970`);
- B1's text (`overdrive_refactor_candidates.md:250-279`) never mentions a function on the request value.

So "in Maxim's own terms" and "whatever B1's request value ships" (§2.1) rest on a field that would have to be added at every model call site, including the three out-of-`think` sites B1 already lists (AdaptivePlanner, ToolPainBridge reflection, FearAgent).

**Failure scenario.** B1 ships without a function field. Every request then names one implicit function, so `functions.yaml` can't give FearAgent's review a different envelope or policy from the main loop. The likely workaround is that the worker infers the function from the call site, a game-side patch the push-back rule forbids.

**Direction (unverified).** OD-A14 says plainly that this is a new field, cites the absent callers, and asks B1 to tag each call site it already lists.

**S-2. The design takes Maxim's function names but drops what those specs declare about degrading.** Contract (a bio-faithful divergence nobody named). Anchors: `::§2.1`, `::§2.2` (each function's placement order), `::§2.6`.

`DEFAULT_FUNCTIONS["agent_inference"]` is `tier="large", fallback=()`, and the docstring says: "Empty tuple = hard-restricted to primary tier (never degrade)" (`function_router.py:57-58`, `:75-81`). So Maxim records that the main agent loop must never run on a smaller model. Overdrive's table lets any function list `[large-model, small-model]`, and failover, budget and consent then degrade it (§6.2 says so).

The design borrows the name as "Maxim's term" but neither honours that restriction nor argues against it. Placements carry no tier, so the loader can't check one either.

**Failure scenario.** A player's `placements.yaml` lists a 3B fallback for `agent_inference`. Maxim's mechanism runs on a model class its own spec forbids for it, and no Known gap, pushback or loader check says so.

**Direction (unverified).** Choose one:
- carry the spec's restriction into `functions.yaml`, with a declared tier per placement that the loader checks;
- or record the divergence as OPEN, and fold it into OD-A24's argument.

**S-3. Some outcome reasons that reach `think` depend on placement, and no invariant test covers them.** Contract. Anchors: `::§2.6` (the "Reaches `think`" column), `::§6.4` (the schema test), `npcs_and_sem.md::§6.6`.

The agent receives `truncated(text, reason=stream_broken)`. That outcome is attributed to the placement, comes from a server leaving `stop_reason` empty, and is not retried. A loopback server that leaves out `finish_reason` therefore hands the agent "stream broken" on every long reply, while a cloud placement never does.

The design also doesn't say whether `thought_failed` reasons reach the agent's next step. `unavailable` (consent, budget, health) and `refused` (provider policy) are host and placement facts. The §6.4 schema test checks only provenance fields, so a placement fact crossing `AgentPort` as a reason passes it.

**Failure scenario.** An NPC's next deliberation treats "my thought was cut off" differently from "I finished". It does so only on one server, so its behaviour depends on placement, not on its state.

**Direction (unverified).**
- Name which reasons cross `AgentPort`.
- Collapse the placement-attributed ones to one reason that doesn't depend on placement, or retry them.
- Widen §6.4's schema test to the outcome and reason values.

**S-4. OD-A25 is filed as a new ask, but B1 already plans the token iterator.** Upstream framing (search rule). Anchors: `::§9 OD-A25`, `roadmap.md::OD-A25`.

B1's reply type reserves "a speech field the host can read before the JSON closes … Otherwise barge-in and first-token latency are designed out. The token iterator itself can come later" (`overdrive_refactor_candidates.md:268-270`). The design's "Searched: none exists (F1)" is true of the backends but not of Maxim's plans. Under the search rule, an ask that overlaps a plan becomes a question to that plan.

**Failure scenario.** Maxim opens a parallel streaming item, or closes OD-A25 as a duplicate of B1. O50's lift then has no owner it is waiting on.

**Direction (unverified).** Reframe it as a question to B1: when does the token iterator come, and at which layer? A chunk sink on `complete_with_usage` is the layer it needs.

**S-5. OD-I10 doesn't engage the decision's own per-hop opt-out (`NO_PROXY`).** Upstream framing. Anchors: `::§5.3`, `::§3.2` ("No … proxy variable passes"), `roadmap.md::OD-I10`.

The 2026-09-28 decision (`DECISIONS.md:1150-1192`) says checked clients use "httpx's OWN per-URL proxy mounts … so httpx's `NO_PROXY` semantics decide per hop". So a per-hop way to switch proxies off already exists: the gateway could set `NO_PROXY=*` explicitly.

I believe that this also stops stdlib `getproxies()` from consulting macOS System Settings, because an environment holding `no_proxy` is non-empty. That is unverified: it depends on the httpx version, and on the Anthropic SDK client honouring the environment.

The design forbids every proxy variable, so it shuts out the existing mechanism. OD-I10 asks for a new one without saying why `NO_PROXY` doesn't suffice.

**Failure scenario.** Maxim answers "set `NO_PROXY`", and the pushback is closed. Meanwhile §5.3 keeps reclassifying a guest's loopback placement as `third_party` for a reason the gateway could have removed itself.

**Direction (unverified).** Test `NO_PROXY=*` in the gateway against both transports. Then either adopt it and keep OD-I10 to the Anthropic `http_client` part, or cite why it fails.

**S-6. Per-speaker taint has no defined state or clearing event, and the coarse spread rule never clears on its own.** Contract. Anchors: `::§5.1` ("Words outlive sessions"), `npcs_and_sem.md::§6.6` (memory provenance), O17, O26.

The provenance model matches the rule in principle. A repeated write carries "the union of its sources' sets" (`npcs_and_sem.md`, "Memory provenance"), and O26's host-computed lower bound is the right source. But §5.1's rule is coarser than that model, and the design never connects the two:
- "an NPC that hears an NPC holding such words holds them too", whether or not what it heard derives from them;
- it is not defined as a per-NPC set of speakers computed from O26's lower bound;
- it never says what clears it.

O17's purge runs "on request". A coarse taint that spreads through every conversation reaches most of a talkative city after one declined guest visit, and nothing in the contract says whether the owner can purge without the guest.

**Failure scenario.**
1. A guest who declined `third_party` speaks to one NPC for ten minutes.
2. Weeks of gossip later, most NPCs are loopback-only in every single-player session.
3. Either the taint can never clear, or it clears on a purge that never matched the coarse flag.

Section 6.2 names the capability change. It doesn't name that it is permanent and spreads to nearly every NPC.

**Direction (unverified).**
- Define the taint as the host's provenance lower bound per NPC (O26).
- Define clearing as the `purge(actor)` reply.
- Say who may request a purge.
- Add "spreads and persists" to §6.2.

### NIT

- **N-1.** `inference_placement.md::§1.2` and lesson 29 cite `router.py` `last_served_*`. No `last_served` exists anywhere in `src/` at 043eab8f. The router has `last_used_model`, `last_used_provider`, `last_used_backend_class` and `last_used_endpoint` (`router.py:286-312`). `call_accounting.ServedCall` (`:39`) does exist. A pushback's evidence must cite real names.
- **N-2.** `roadmap.md::OD-I9` dropped `llm_path_fast_failover.md:771`, Maxim's own lesson: "Backend failures raise typed exceptions, not return empty content." For the empty-content half, the cloud backends break Maxim's own recorded rule. Citing it makes that half a request for consistency rather than an argument with a decision.
- **N-3.** The three OPEN divergences in `::§6.2` (capability within a life, fatigue, observed latency) are not in `npcs_and_sem.md::§12.2`, Overdrive's list of OPEN divergences ("each with a red gate when there is code"). They have no gate or trigger. The per-NPC meter for changes of placement is in neither §8's B5 rows nor the `checklists.md` tests. A one-line pointer in §12.2 and a meter row would make them visible.
- **N-4.** `::§6.1` says a placement changes "only dilation, or lateness under floor-holding". In co-op's interim late landing (O16), lateness is heard by other NPCs (O27, `npcs_and_sem.md::§12.2`). Placement now makes it vary per reply rather than per machine, so cite O27 there.

## 3. The questions asked

- **Upstream framing.**
  - OD-A24 and OD-I9 are correctly framed pushbacks that name verified decisions.
  - OD-A23 now goes to the right owner.
  - OD-A25 duplicates B1's planned token iterator (S-4).
  - OD-I10 ignores its own decision's `NO_PROXY` clause (S-5).
  - OD-A14's function field is a new ask presented as an existing term (S-1).
  - No item duplicates `lane_capability_placement_split.md`; OD-A24 argues with it in the open.
- **Is "the declared function name" carried by Maxim?** It is a Maxim type (`FunctionSpec.name`), but not a value on any shipped call path (S-1). The spec's restriction against degrading is dropped (S-2).
- **Does O51 fit O17 and provenance?** In principle yes, through union provenance and O26's lower bound. As written, the rule doesn't define its state or its clearing event (S-6).
- **Does pinned-waits-on-load hold?** No (B-1).
- **Are the OPEN divergences in §6.2 honest?** The content is, and BF-4's understatement is corrected. They are unregistered, have no gates, and their meter has no test (N-3). The spread of consent taint is missing (S-6).
- **Can an NPC sense placement, latency or cost?** Provenance and spend can't reach it, and §6.4 holds that for provenance. Placement can reach it through outcome reasons (S-3), and through capability and fatigue under load (B-1). Latency reaches it through `learned_hold_window`'s observed latency, which §6.2 states, and through co-op late landing (N-4). Cost reaches it only indirectly: a spend cap changes the model. That is stated.
- **Is lesson 29 supported?** Yes, apart from the `last_served_*` citation (N-1). Its claims about empty replies, retries inside the call, the whole-call timeout, streaming and the router's process state match 043eab8f or the design's verified facts.

**Counts:** BLOCKER 1 (B-1, contract). SHOULD-FIX 6: four contract (S-1, S-2, S-3, S-6) and two upstream framing (S-4, S-5). NIT 4. Round-1 statuses: 11 fixed, 1 open (BF-3). Under the stop rule, B-1 is a contract blocker and still folds. S-1 to S-3 and S-6 are contract findings and should fold too. S-4, S-5 and the NITs are roadmap and text edits.
