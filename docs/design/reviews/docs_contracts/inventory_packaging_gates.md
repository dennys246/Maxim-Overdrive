## Contracts stated more than once: code structure, trust gates and enforcement

In every pair below where the copies disagree, I re-read both copies. The contradictions are listed first.

### Contradictions

1. **Layer order (the package and layer map).**
   - DEFINES: `boundaries.md:110` §2.2 has a 12-layer `engine.*` table, with layer 8 = `engine.host | engine.verify`.
   - DEFINES: `boundaries.md:55` O24 amends it to "the engine core, the adapters, the game and the client protocol", which leaves verify out.
   - REFERENCES/DEFINES: `tile_and_client.md:41` §0 and `:450` §7 say "`simcore` in four layers (core, adapters, game, client protocol)", also without verify.
   - DEFINES: `verify_harness.md:18` §2 says verify sits "under `maxim_overdrive` and above `simcore.protocol`".
   - REFERENCES: `inference_gateway.md:28` §1 still places modules at "7a, beside `engine.loaders`" and "7b".
   - **DIFFER.** None of the in-scope documents states the as-built five-layer order (core < adapters < protocol < verify < game); only CLAUDE.md does. O24 and tile both say four layers and omit verify. Tile §7 also puts `TimeAuthority` and sessions in "client protocol", while §2.2 puts them in `engine.host`, layer 8.
   - **Owner:** boundaries §2.2, rewritten to O24's real layers, because it is the only full map. O24 and tile §0/§7 should link to it.

2. **The write window: who enters it before `Simulation` exists.**
   - DEFINES: `boundaries.md:231` §4.1 says "the window's owners are `World.advance` and the intent applier", naming two.
   - DEFINES: `boundaries.md:740` §10 ("as built 3b(a)") says "`place` opens it too (marked for 5a)".
   - DEFINES: `roadmap.md` Phase 1 lists three marked owners, `place` among them.
   - REFERENCES: `checklists.md` 5a says "Retire `imagination.place`'s write window".
   - **DIFFER:** §4.1 leaves out the third owner.
   - A second tension sits inside the same document. §4.1 says "a write anywhere else raises" and that the window is "the guard". O8 (`boundaries.md:63`) says "correctness rests on structure" and the window is "a dev and test-build check". §10 says "The membrane gets an applier and a frame view, never the world: that is the guard."
   - **Owner:** boundaries §4.1, with O8 folded into it.

3. **The sealed core's banned list: `logging`.**
   - DEFINES: `boundaries.md:184` §3 says "**Explicitly allowed:** … `logging` (output only)".
   - DEFINES: `boundaries.md:740` §10 says "§3's ban covers `logging` too".
   - **DIFFER**, within one document. **Owner:** §3.

4. **The tripwire mechanism and its scope.**
   - DEFINES: `boundaries.md` §3 (~l.192) says "a test, not a runtime seal … profile hook … on the simulation and agent-lane threads" and "Patching module attributes can't work".
   - REFERENCES: `npcs_and_sem.md:102` §1 agrees.
   - REFERENCES: `world_model.md:184` §6 ("per-thread `sys.setprofile`") agrees.
   - DEFINES: `world_v2.md:265` §5 says "It raises only on the simulation thread inside `step`".
   - DEFINES: `realtime_lanes_coop.md:273` §4.4 says "A tripwire test makes `time`, `uuid` and the global `random` raise inside `Simulation.step`".
   - **DIFFER:** world_v2 limits it to the simulation thread, and realtime describes a raising patch.
   - **Owner:** boundaries §3.

5. **Who may import `maxim`.**
   - DEFINES: `boundaries.md:606` §8.1. Its adapters are `engine.adapters.sem` (`Entity`, `Modulator`, …), `adapters.agents`, `adapters.inference`, the game's NPC authoring and `maxim_experiments`.
   - DEFINES: `npcs_and_sem.md:770` §6.6 says "the host imports Maxim's types only through `_compat.py`, and `maxim` itself only in workers and inference gateways".
   - EXTENDS: `inference_gateway.md:36` §1 and `sem_stimuli.md:426` §7.3 each add an importer to the `maxim-through-adapters` contract.
   - **DIFFER:** npcs leaves out the membrane, NPC authoring and the experiments harness.
   - The import-linter version also differs. `boundaries.md:618` says "verified on 2.15", while `:738` and `sem_stimuli.md:415` say 2.6.
   - **Owner:** boundaries §8.1, with the other documents adding rows by link.

6. **Where the gates are.**
   - DEFINES: `boundaries.md:320` §5.3 has many gate modules: the protocol decoder, `engine.text.player_text`, the worker codec, the stage-1 parser and the loaders.
   - DEFINES: `fire_solid.md:340` §5.1 says "All loaders are in `adapters/loaders.py`, **the one input gate**".
   - DEFINES: `architecture.md:142` ("SEM for the environment") says "An NPC's tool call, an LLM's output and a client's intent **all reach the world through it** [the modulator]".
   - **DIFFER.** In boundaries §5.3 and tile §3.1, client frames go through the strict decoder and then stage 1, never through the modulator.
   - **Owner:** boundaries §5.3. Architecture should keep only a link.

7. **Two-stage validation: where stage 1 runs and where its caps come from.**
   - DEFINES: `boundaries.md:345` (under §5.3) says "stage 1 is typed parsing in `engine.intents` (shape, finiteness, ceilings)".
   - DEFINES: `boundaries.md:671` §9.1 says "Stage 1 stays the only server validator".
   - DEFINES: `realtime_lanes_coop.md:327` §7 says "The network lane checks the schema: types, finiteness, ranges, caps from `data/server/`".
   - DEFINES: `architecture.md:142` describes it as `parse_action` inside `ActionLimits`, from `data/world/actions.yaml`.
   - REFERENCES: `tile_and_client.md:192` §3.1 restates the pipeline. `tile_and_client.md:261` §3.4 says "`rate_limited` … stage 1 (client protocol layer)".
   - **DIFFER:** the caps are in `data/server/` according to realtime and in `data/world/` according to architecture. Rate limiting is called stage 1 in tile and pre-log in tile §3.5.
   - **Owner:** boundaries §5.3's two-stage paragraph.

8. **Buffer caps (a trust budget before decoding).**
   - DEFINES: `boundaries.md` §9.1 says "`max_size` applies before decoding".
   - DEFINES: `architecture.md:185` ("Transport") says "**Both ends** must raise their default caps".
   - DEFINES: `realtime_lanes_coop.md:385` ("Supersedes") says "TB-7: **only the client** raises its cap".
   - REFERENCES: `client_rendering.md` §12 ("buffers and the server's caps").
   - **DIFFER.** **Owner:** boundaries §9.1, or client_rendering §4.3 for the client side.

9. **Phase 3 upstream item lists.**
   - DEFINES: `roadmap.md:124–283` Phase 3.
   - RESTATES: `boundaries.md:688` §9.3, `npcs_and_sem.md:961` §8.1/§8.2 and `realtime_lanes_coop.md:294` §6.
   - REFERENCES: `inference_placement.md:414` §9 and `sem_stimuli.md:460` §9. These two only ask, amend or cite ids, and agree with the roadmap.
   - **DIFFER, three ways:**
     - OD-A16. Roadmap `:195` has "`stale`, `call_error` **and `wrong_target`** kinds". Boundaries `:700` and npcs `:975` have only "`stale` and `call_error`".
     - OD-A13. Roadmap says "*Moved to OD-I3*", and npcs says "OD-A13 moved to OD-I3". Boundaries `:699` still says "OD-A10–OD-A15", which includes A13.
     - Realtime §6. It uses the retired numbering (items 10–18) and keeps "13 Cancellable deliberation", which the roadmap retired as C9.
   - Boundaries §9.3 also lacks OD-I6–I10, OD-C12 and the B and H rows.
   - **Owner:** roadmap Phase 3 (the id index, O41). The other documents should cite ids only.

10. **Golden screenshots (method and exit).**
    - DEFINES: `client_rendering.md:211` §6 (method, tolerance, CI). It says "From frame fixtures, never a live server".
    - DEFINES: `world_v2.md:263` §5 says "B7's golden screenshots run as a log replay".
    - **DIFFER mildly:** world_v2 runs them as a log replay, client_rendering from frame fixtures.
    - The scenario goldens G1–G5 and "ID-mask areas (crate, …)" assume the crate. `roadmap.md:55` Phase 1 exit says "light a slab … The crate moves to Phase 2". `foundations_plan.md:16` §2 still says "set a crate on fire".
    - The tier comparison also differs. Client §6.3 compares laptop and max against rig, while the roadmap says "the same apart from detail at the laptop and rig profiles".
    - REFERENCES (agree): `checklists.md` step 8 ("five scenario goldens per tier, staleness digests, `update_goldens.sh`") and `foundations_plan.md` steps 2 and 8.
    - **Owner:** client_rendering §6. The exit itself is owned by roadmap Phase 1.

11. **Where the experiment harness lives.**
    - DEFINES: `boundaries.md:90` §2.1 and `:660` §8.4 put `maxim_experiments` in this repo, with "the experiment and ledger tooling" (`:616`).
    - DEFINES: `npcs_and_sem.md:1056` §10 says "Only through a **Maxim-owned** harness".
    - REFERENCES: `sem_stimuli.md:358` says "a Maxim harness".
    - Roadmap Open questions still asks whether the world server becomes a dependency of Maxim experiments.
    - **DIFFER/unresolved.** **Owner:** boundaries §8.4.

12. **The agent-facing receipt shape** (this crosses into another domain, but it is a closed vocabulary).
    - DEFINES: `tile_and_client.md:255` §3.3 says "`(actor_id, seq)`, outcome (`applied`, `refused`, `stale`, `cancelled`), refusal code, measured effect, before and after frame ids".
    - DEFINES: `sem_stimuli.md:314` §6.2 says "receipt is `(pid, kind)`", with kinds `malformed`, `limit` and `accepted`. It supersedes boundaries §2.2 and npcs §6.6 by name, but **not tile §3.3**.
    - **DIFFER.** **Owner:** sem_stimuli §6.2 for the agent-facing shape, and tile §3.3 for the wire `intent_result`.

13. **`kind_rank` values.**
    - DEFINES: `tile_and_client.md:206` §3.1 says "join/leave 0, `time` 1, moves 2, `kindle` … 3".
    - DEFINES: `checklists.md:113` 5a says "Intent kinds ranked 0/10/20/30".
    - REFERENCES: `boundaries.md:427` §6.2 has the ordering key.
    - **DIFFER.** **Owner:** boundaries §6.2.

### Restated but agreeing (should collapse to one owner)

- **The gate contract** (strict loader, version, closed keys, one exception type, bounded echo and closed codes, budgets before allocation).
  - DEFINES: `boundaries.md:348` §5.4.
  - Restated in part: `world_model.md:229–232` §8 ("versioned, closed keys, repeated keys refused"; F14 "budget … before anything is allocated … all-or-nothing"); `fire_solid.md:114, 352`; `ip_and_licensing.md:129` §6 item 3; `realtime_lanes_coop.md:341`; `npcs_and_sem.md:485` (links).
  - Agree. **Owner:** boundaries §5.4.
- **The gate list.**
  - `inference_gateway.md:265` §9 is linked from a row of `boundaries.md` §5.3, which is correct. Its text says "a row in §5.3's registry", but the registry is defined in §5.2 and `lint_gates.py`.
  - `sem_stimuli.md:325` §6.3 lists *test* gates (T1–T17), a different concept and not a restatement.
  - `tile_and_client.md:261` §3.4 and `fire_solid.md:380` §5.3 define refusal codes, which extend the closed vocabulary rather than repeat it.
  - One mismatch: tile §11 and checklists 3b create the refusal enum in 3b, while fire_solid says "Appended to 5a's list".
- **The worker channel codec.**
  - DEFINES: `boundaries.md:329` (a §5.3 row) and `npcs_and_sem.md:743` §6.6 both state length-prefixed, versioned, closed-schema JSON, closed kinds, budgets before allocation, and pickle banned in `engine.host`/`engine.adapters`.
  - REFERENCES: `inference_gateway.md:75` §3.
  - Agree, but npcs cites "strict decoder (`boundaries.md` §10)" and boundaries §5.3 cites "(§10)", while the decoder is defined in §9.1.
  - **Owner:** npcs §6.6; the boundaries row should link to it.
- **The strict JSON decoder and the integer pin at 2⁵³.**
  - DEFINES: `boundaries.md:671` §9.1.
  - Restated: `realtime_lanes_coop.md:315` §7 (NaN/Infinity refused, closed schemas) and `checklists.md` step 7 (2⁵³ fixtures).
  - Agree. **Owner:** boundaries §9.1.
- **Placement tables.**
  - `tile_and_client.md:450` §7, `sem_stimuli.md:363` §7.1 (says it "supersedes `boundaries.md` §2.2's map by name"), `inference_gateway.md:26` §1 and `verify_harness.md:16` §2 each place their own modules.
  - Apart from the layer naming in item 1, they don't contradict one another. They should be rows added to one map.
  - `client_rendering.md:275` §7.1 (the Godot tree) and `boundaries.md` §2.1's two `client/` rows agree.
- **The skip-layer contract.**
  - `boundaries.md` §2.2 and §10, and `checklists.md` 3b ("adapters, protocol ↛ grid, laws, geometry, scene build").
  - Agree, but the as-built `grid` replaces `cells`. **Owner:** §2.2.
- **The BLAS ban.**
  - `boundaries.md` §3 bans BLAS in the whole core. `sem_stimuli.md` §7.2 restates it for `core/stimuli` and `core/body`, which are inside the core.
  - Agree but redundant.
- **Game runs off Maxim's ledger.**
  - `boundaries.md:664` §8.4, `npcs_and_sem.md:1037` §10 and `roadmap.md:381` (standing rules).
  - Agree. The npcs heading "off the game ledger" is misworded. **Owner:** boundaries §8.4.
- **Content and licence.**
  - DEFINES: `boundaries.md:633` §8.2.
  - Restated: `architecture.md:214` ("Code: Apache-2.0 … lore, art and audio: all rights reserved") and `roadmap.md:382` ("Story, characters and assets").
  - REFERENCES: `tile_and_client.md:456` §7 and `client_rendering.md:278` §7.1.
  - Mostly agree. The architecture and roadmap wording doesn't cover §8.2's rights-reserved *data calibrations*.
  - `ip_and_licensing.md` §6 defines a separate per-placement licence value. Its gate target `imagination.spec.place` (§1, §6) is stale against `roadmap.md:329`'s `simcore.core.imagination.place`.
  - **Owner:** boundaries §8.2.
- **The token, `Origin` and loopback bind.**
  - `boundaries.md` §5.3 rows, `realtime_lanes_coop.md:280` §5, `client_rendering.md:336` §7.5 and `architecture.md` ("Transport").
  - Agree. **Owner:** realtime §5, or move it to boundaries.
- **Requirements by plan step.**
  - `tile_and_client.md:485` §11 and `client_rendering.md:383` §12 overlap with `checklists.md` steps 3b–9 and `foundations_plan.md:20` §2.
  - The contents agree. Tile §11 still uses a single "5", while foundations and checklists split it into 5a and 5b (O34).
  - **Owner:** checklists.md, with the design sections cited from it.
- **Performance budgets (B5).**
  - No duplicate definitions. Each meter is defined once: `client_rendering.md:344` §8, `sem_stimuli.md:443` §8, `tile_and_client.md:439` §6.5, `world_model.md:246` §9 and `fire_solid.md:118`.
  - realtime §2.3's cost table is older, and labelled "to be re-measured".