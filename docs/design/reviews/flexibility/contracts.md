# Future flexibility: contracts and formats

Scope: wire v0 (`tile_and_client.md` §3–§4, `client_rendering.md` §4, `origin/phase1/realtime-design:docs/design/realtime_lanes_coop.md` §7), the frame grammar and `world_model.md` §8, scene v0→v1, save v0, the intent log and header, the action vocabulary, and `AgentPort` and the worker codec (`npcs_and_sem.md` §6, `boundaries.md` §5–§7). Code read: `origin/phase1/act-validation` (`checks.py`, `config.py`, `scene.py`, `data/world/actions.yaml`, `tests/test_validation.py`).

**The main finding.** The wire is a cheap door to reverse. Server, Godot client and worker always ship from one commit, so v0 can be refused and rebuilt in lockstep. The expensive doors are the formats that outlive a build: saves, the log's identities and digests, content files, and (from Phase 4) agent memories. The design gives those the least concrete rules. Most of the flexibility effort goes into the wire and into migrating data files only the repo holds.

## Ranked table

| # | Door | Reversal cost | Likelihood | Action now | Action cost |
|---|---|---|---|---|---|
| 1 | Index-valued columns persisted without names (`archetype`, `held_item`, `material`, `actor_id`) | every save and log from before the change silently misreads | certain (step 6 and content add items and materials) | name dictionaries in every persisted header; `join` records carry `body_key` and names | ~40 lines, step 5 / 9 |
| 2 | Save load policy: refuse on any content mismatch; "the log is the save's backbone" | every save dies on every constant tweak | certain (§5.1's constants are all *from memory*) | write save v0's load rule now: state not replay, a region table instead of the scene file | one paragraph now; step 9 code |
| 3 | `format_version` is exact-match, with no migration chain | each migration is ad hoc, or old fixtures get deleted | certain (two migrations already planned) | `read_version` + a `(format, from) → fn` registry in 3b, used only for stranger-held formats | ~60 lines, 3b |
| 4 | Digest canonicaliser unversioned | a canonicaliser fix makes every log header and catalogue hash "mismatch" | medium (float canonical form is easy to get wrong) | prefix every stored digest: `sha256/c14n-1:` | trivial |
| 5 | The frame grammar's required/optional rule was dropped from the tile catalogue | every Phase 2 channel breaks the committed Godot fixtures and the save grammar | high (`loose`, `packing_fraction`, light, zones are planned) | `required` per channel, a `compression` field, an "unknown optional ignored" fixture | small, step 7 |
| 6 | Time stored in ticks inside content (`140 mm per tick`, `max_duration_ticks`, `restrike_ticks`) | a tick change rewrites every archetype and item file and their fixtures | medium (the tick changed once already; the barrier cost puts 20× at risk) | content in µs and mm/s; the core converts, checking that the division is exact | trivial now |
| 7 | `kind_rank` as dense integers 0–3 | inserting a kind between two ranks renumbers the ordering | medium (`speak`, `thought_*` and `douse` vs `strike` are coming) | space them: 0, 10, 20, 30; put the table in the header's vocabulary digest | trivial |
| 8 | Agent-facing names (verbs, refusal codes, `hold` levels) | NPC memories in agent homes refer to a retired verb | high (two of three verbs renamed in Phase 1) | an append-only code enum test; a `retired:` list in `actions.yaml` v1 | small |
| 9 | `region_id` u16, never reused | ids run out over a long save | low–medium | a defined `region_ids_exhausted` refusal; dtype from the registry in the save | trivial |
| 10 | The Maxim-owned continuation inside saves (Phase 4) | a pymaxim upgrade bricks saves that have thoughts in flight | high once real NPCs exist | load rule: unknown continuation version → `thought_failed(reloaded)` | a checklist line |
| 11 | Wire version handshake | low (lockstep) | — | exact match plus `build` in `welcome`/`error`; **no** capability negotiation | trivial |

## 1. Persisted indices and identity

- **The door.** Tile §2.2: `archetype` and `held_item` are "1-based index into `welcome`'s … list", and the order of those lists is unspecified. Step 9 saves "the actor and pilots tables" (plan §2, checklists step 9). `material` is a u8 id. Its ids are explicit and stable (`core.yaml`: "Ids must stay stable: saves store them"), but nothing stops an id being reused after a material is removed. `actor_id` is "session-scoped" (tile §2.1), and the log's `actor_id` is that id (boundaries §6.2).
- **Scenario.** A save from build N holds `held_item = 2` (torch). Build N+1 adds `content/items/lighter.yaml`, which sorts first. The save loads, and the player now holds a lighter, with no error. The same thing happens to a log replayed after a save/load boundary: actor 1 in the second segment is a different body.
- **Why now.** World_model F8 already says "keyed by name, never by position" for species, but no rule covers the actor table's columns.
- **Action.** Every persisted file with an index column carries its dictionary in the header: `{items: [names], archetypes: [...], materials: {id: name}}`. The loader remaps by name and refuses an unknown name with a closed code. In step 5, make `join` log records carry `body_key`, `archetype` by name and `holding` by name. Then the log and the save share one identity, and actor ids can be dense and session-scoped without harm. The wire keeps its indices: it's lockstep.

## 2. Save v0's load policy (BLOCKER-grade if step 9 lands as written)

- **The door.** Four rules, taken together:
  - world_model §8 F5: "embedded copies of the registry, scene and specs are compared against them";
  - boundaries §6.3: "a content mismatch is refused, loudly";
  - CLAUDE.md: the log is "the save format's backbone";
  - world_v2 §8: "the save embeds the registry, the material table, the scene…".
  
  Read together, a save from build N refuses to load after any change to a material constant, the scene or the vocabulary.
- **The rules contradict each other.** F5 says embedded scene and specs are "compared against them, never executed". F14 says they "go back through `Scene.from_dict`". So a save has to stay readable by the scene loader of every later build.
- **Likelihood: certain.** §5.1's nine constants are all *from memory*, and step 6 cites them one PR at a time. D28's heat-debt prototype will tune values. Every one of those commits invalidates every save, including committed golden saves.
- **Action, written into the step 9 checklist now:**
  1. A save is state: cells, the actor and pilots tables, RNG, tick. Loading never replays the log. A log segment only starts at the save's tick.
  2. The save stores a **region table** (names, authored boxes in integer mm, materials by name), not the scene file. A scene format bump is then never a save migration.
  3. Content digests in a save are *provenance*. A mismatch loads, sets `content_changed: true` in the save's lineage, and drops the bit-identical replay claim to "from this tick on". Refusal is kept for format versions and structural mismatch (shape, unknown names).
  4. Every grid carries its `cell_size` and origin (tests already run at 0.2, 0.1 and 0.05 m).
- **Conflict check.** These rules don't touch any owner decision (F5 and F14 are review-fold rules, not §0 rows). They do narrow CLAUDE.md's replay sentence, which boundaries §6.2 already plans to rescope (§11.2).

## 3. The migration mechanism, and where not to use it

- **The door.** `checks.format_version(raw, expected)` raises unless `version == expected`. There is no hook to read an older version. Two migrations are already specified, each in its own way: `actions_v0_to_v1` (tile §3.2) and scene v0 → `spawns: []` (tile §1.3, F12). The convention in `test_the_committed_v0_files_still_load` ("after a bump this compares with what migration gives") puts every format bump on the migration path.
- **Action (3b).** `read_version(raw) -> int`, a registry `migrations[(format, from_version)]` of pure functions, applied in a chain before the strict loader. Each step is tested from its committed v(n) fixture to an expected v(n+1) value. Defaults stay literals or registered names (F12).
- **YAGNI (the cost side).** Use the registry only for formats strangers hold: saves, logs, bug reports and, later, mods. `actions.yaml`, rigs and materials exist only in the repo. For those, a bump plus a refusal test on the old fixture satisfies CLAUDE.md ("a migration or a version bump"). `actions_v0_to_v1` maps a file nobody else holds. Scene v0 → `spawns: []` produces a scene that `join` refuses (tile §1.3), so it's a migration to an unusable value: drop it and refuse v0 scenes.

## 4. Versioned digests

- Boundaries §6.3 defines "one canonicaliser … sorted keys, fixed number format". The log header, the rerun manifest and `client_rendering.md` §4.1's catalogue hash all depend on it.
- The first canonical float format (repr, `-0.0`, numpy scalars, `1e-7`) is likely to need one fix. After that fix, every committed log's header digests stop matching, and boundaries §6.3 refuses on a mismatch.
- **Action:** store every digest as `sha256/c14n-1:<hex>`, and keep old canonicalisers registered. The cost is a string prefix.

## 5. The extension rule in the frame grammar

- **What was dropped.** world_v2 §8 decided: "old readers refuse an unknown required channel and ignore unknown optional channels", with fixtures for both cases, and `compression` reserved (realtime §7 also carries `axis_order` and `frame: "z-up"`). The tile catalogue (`client_rendering.md` §4.1) has unit, dtype, scale and offset but no `required` flag. Its header lists no `compression` and no `axis_order`.
- **Why it matters.** World_model §7 reserves `loose` and `packing_fraction`, and Phase 2 adds light and zones. On the wire, each addition is only a lockstep rebuild. But `client/tests/goldens/frames/*.bin` are B3 fixtures (WT-N6) that "stay committed", and the save "uses the same grammar". Without the optional rule, every new channel is a protocol bump plus a refusal fixture, and a save migration if the channel is persisted. Saves are 23–29 MB (tile §1.4), so compression will come, and adding the field later is a grammar bump.
- **Action (step 7):** restore `required` per channel and `compression: none`, and keep `axis_order`. Restore world_v2's two fixtures (an unknown optional channel ignored, an unknown required channel refused). `kind: delta` stays reserved (`client_rendering.md` §11).

## 6. Ticks in content

- **The door.** Tile §2.1 stores walk speed as "140 mm per tick". `content/items/torch.yaml` has `max_duration_ticks` and `restrike_ticks`, and `actions.yaml` v1 has `max_duration_ticks`.
- **Likelihood.** T3 isn't being questioned, but the tick has changed once already (6 s → 0.1 s). npcs §6.6 measures the agent barrier at "0.2–0.8 wall seconds per second" at 20× with 20 NPCs, and a longer tick is one of the obvious levers. A tick change today rewrites every content file and every fixture.
- **Action.** Content and data hold world units (`walk_speed_mm_s: 1400`, `max_duration_us`). The core converts once at load and refuses a value that doesn't divide exactly into `tick_us`. Logs and the wire stay in ticks, since the header records `tick_us`. This is CLAUDE.md's "author in metres" rule applied to time.

## 7. Spaced `kind_rank`

The ordering key `(apply_tick, kind_rank, apply_us, actor_id, seq)` (boundaries §6.2) gives ranks 0–3 (tile §3.1, `[engineering]`). Boundaries §6.1 already lists kinds with no rank yet: `speak`, `thought_cancelled`, `thought_failed`, `agent_failed`, host commands. **Action:** ranks 0/10/20/30, with the table folded into the vocabulary digest in the header. Cost: zero.

## 8. Agent-facing names are identities

- **The door.** F1 makes channel names identities, but verbs, refusal codes and `hold: brief | steady | long` (tile §3.2) are what NPCs remember. Agent homes are saved (boundaries §7.1, save v1), and Maxim's episodic memory and cerebellum key on affordance names. A rename after Phase 4 strands learned associations in every saved agent home.
- **Evidence.** `extinguish → douse` (F7) and `ignite → kindle` (T4) both happened in Phase 1, before any agent existed. That was the cheap moment; it won't be cheap again.
- **Action:** `actions.yaml` v1 carries `retired: [ignite, extinguish]`, and the loader refuses a retired name as a live kind. Add a test that the refusal-code enum (tile §3.4) is append-only against a committed list. T4 is not relitigated here.

## 9. Region id space

`region_id` is u16 and "never reused" (world_model §5, F10). Phase 4 NPCs `imagine` objects into one long-lived save, so 65,535 is a lifetime budget, not a budget for one scene. **Action:** a closed refusal code `region_ids_exhausted` at stage 2 now, and the save takes `region_id`'s dtype from the registry, so widening it later is a mechanical migration. The wire widening (`FORMAT_RG8` → two textures) is lockstep.

## 10. The worker codec and continuation

- **YAGNI first.** The host and its worker are spawned from one venv and one commit, so a codec version can only mismatch through a bug. Keep one exact version and the `hello` kind (ATR-N2) for diagnostics. Negotiation isn't needed.
- **The real door.** "The continuation as an opaque, versioned blob in the agent home" (npcs §6.2) is Maxim-owned, and saves will hold thoughts in flight (realtime §2.1). If a pymaxim upgrade changes that blob, every save with a thought in flight breaks.
- **Action:** a checklist line on the agent line's PR (O19 froze the v3.1 text, so this goes in as a red-first test, not an edit): an unknown continuation version loads as a logged `thought_failed(reason: reloaded)`, never as a refused save.

## 11. Wire version

`hello {protocol: 0}` with exact match is right for lockstep builds. **Action:** `welcome` and the version `error` carry the engine `build` (SHA), so a Phase 5 guest on a stale build gets a readable refusal. Don't build capability negotiation, per-message versions or a compatibility matrix: tile §9 Q3 ("freeze only sent kinds") already relies on lockstep, and that's correct.

## YAGNI and duplication, summarised

- `actions_v0_to_v1` and the scene `spawns: []` migration (§3): drop both, and use refusal tests instead.
- `energy` and `dose` as zero columns "with a `derivation_version`" (tile §2.2, DC-N2). In a save, `energy = 0` will mean "starving" once Phase 4 models it. Adding the column in Phase 4 with an F12 literal default is cheaper and doesn't need that caveat. Drop them from v0's tables.
- Capability negotiation on the wire or in the codec (§10, §11).
- **Duplication, not YAGNI.** The log header is specified in four places: realtime §7 (with the superseded `host_seq`), boundaries §6.3, world_model §8 and tile §3.5. Step 5 writes the first log fixtures. Merge the four into one table in boundaries §6.3 before then, or step 5 will build from whichever one it reads first (the DC-B2 pattern again).

## BLOCKER-level risk

No BLOCKER today, because no save exists. **§1 and §2 together become a BLOCKER the day step 9 commits a golden save as currently specified.** Saves would then be bound to exact content digests and to the positions of items in a list, and every step-6 constant citation and every new item would break them. The fix costs one paragraph in `checklists.md` step 9 and two fields on `join` in step 5. Waiting means a migration framework for indices that carry no names.
