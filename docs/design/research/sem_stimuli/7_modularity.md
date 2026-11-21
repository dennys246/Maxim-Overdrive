# SEM stimulus interface, lens 7: compartmentalization and modularity

Read at `phase1/sem-stimulus` 5ff1b7c (the worktree `.worktrees/sem-stimulus`). Repository claims are read from that tree; counts come
from an AST census that uses `scripts/lint_sizes.py`'s own rule, which counts every public `def` in a class body, a
property setter included. Tags: **V** checked here (for import-linter, against the installed 2.6 in another
worktree's venv), **S** secondhand, **M** from memory and not checked.

## 1. Where the code already strains

**Size tripwires (12 public methods per class, 500 lines per module, a 40-line function body).**

| Symbol | Count | Note |
|---|---|---|
| `core/grid.py::CellStore` | **11 of 12** by the lint | The reviews say 10 (fire_solid A-S3, fire_model A-N1), but the lint also counts the `time_s` setter as a `def`. So **one** more member trips the lint, not two. |
| `core/grid.py::MaterialGrid` | 7 in its own body, **25** with what it inherits | It inherits from both `GridGeometry` (7) and `CellStore` (11). The lint counts only the class's own body, so a god object made by inheritance gets past it. |
| `core/world.py::World` | 9 | It also holds `_power_field`, which deposits heat sources onto the grid (a law), and the module holds `sphere_overlap`, which is geometry (layer 2 in boundaries §2.2). |
| `core/frames.py::Frame`, `Observation` | 5 each | Every stimulus added as a method would raise both. |
| `core/grid.py` | 390 of 500 lines | The largest module. The fuel store is already kept out of it (`FuelStore`). |
| `core/imagination.py::_read` | 27-line body | The longest function body. `damage.strike` is 20. |

Beyond `CellStore`, the strain is **central switches**, which no size lint sees until large.

**Mixed concerns: one name known in many places.**

- **A region quantity is known in three places.** These are `frames.py::QUANTITIES` (4 names),
  `frames.py::Frame.reading` (an `if quantity == ...` chain with 3 branches) and
  `adapters/sem/bridge.py::RegionInstrument.reading_schema` (an `if self._quantity in ("integrity", "breached")`
  test). A fifth quantity means three edits in two layers, and if the schema edit is forgotten it fails silently: the
  quantity gets the temperature range. **This is the pattern the stimulus interface must not copy.**
- **A cell channel is spelled in at least eight places:**
  - `CellStore.__init__` (the dict) and its 4 properties;
  - `CellFrame`'s fields, the name tuple in `__post_init__`, and `CellFrame.of`;
  - `MaterialGrid.__init__`'s keyword arguments and `MaterialGrid.empty`;
  - in the tests, `tests/test_ownership.py::OWNED` and `_surfaces`.

  `CellStore.writing` is the only generic site. This is what O34's field registry exists to remove (world_v2 §2.5:
  "`MaterialGrid` holds fields from the registry instead of one attribute each").
- **`frames.py` imports `damage`,** a law module, for `region_integrity` and `region_breached`. So the publication
  mechanism (`FrameFeed`, `FrameView`, `CellFrame`) and a catalogue of reductions share one module. If stimulus
  reductions are added there too, `frames.py` comes to depend on every law.
- **Acts are switches too:** `intents.py::parse_action` (an `if affordance ==` chain), `Applier.apply` (an
  `isinstance` chain), `StructureModulator.affordances`. A new act touches 5 sites in 3 modules: not the template.
- **`World.advance` hard-wires its laws:** `heat.step(..., power=self._power_field,
  on_substep=damage.thermal_degrade)`. There is no ordered law list yet. It is marked `TEMPORARY(phase1/sim-clock)`,
  and O34 owns the list.
- **`bridge.py` holds two concerns** (the act gate, the lab instrument); receptor delivery is a third module.

## 2. A placement for the stimulus interface

**Principle.** The world computes a stimulus at the receptor, and Maxim transduces it (tracker, "Decided"). So the
models must run where the fields are, in the sealed core, on the simulation lane and in deterministic order. The
membrane only translates finished values into `SensorReading`s. The skip-layer rule already makes any other split
impossible: `simcore.adapters` may not import cells or laws (contract `skip-layer`).

**Proposed new code.** No existing module moves; boundaries O24's split trigger isn't reached.

| Piece | Owns | Layer (boundaries §2.2) | Module |
|---|---|---|---|
| Stimulus schema | `StimulusSpec`: name (an identity for the format's life, world_model F1), receptor (closed vocabulary, npcs_and_sem §7.4), unit, range, site set, the registry fields it reads, cadence, version | 1, declarations only; imports `checks` | `core/stimuli/schema.py` |
| Body geometry | The body grammar: receptor sites as patches in body-local metres, their areas and normals. No cells, no pose. | 2, geometry | `core/body/geometry.py` |
| Body store | Each NPC's pose (position, orientation, posture) and body instance, with its own write window, as `FuelStore` has (fire_solid A-S3) | 3 | `core/body/store.py` (step 5b) |
| Body frame | An immutable snapshot of each NPC's receptor sites in world metres at one publish, derived from the store and the geometry | 3, read side | `core/body/frame.py` |
| Stimulus models | One module per modality. Each reads registry fields and body frames and returns an array of shape `(npc, site)`. They write nothing. | 5c, above laws and geometry, below `sim` | `core/stimuli/models/<name>.py` |
| Registry and runner | The one list of models; a runner that hands each model a read capability, in registry order | 5c | `core/stimuli/registry.py`, `core/stimuli/run.py` |
| Stimulus frame | Values keyed by (NPC, stimulus name), published as one part of the frame beside `CellFrame` | 6 | `core/stimuli/frame.py`; `frames.Frame` gains one `stimuli` part, not a method per modality |
| SEM delivery | One generic `ReceptorSensor`, driven by `StimulusSpec`: `unit`, `reading_schema` and `value` are read from the spec, so there is never a per-modality class | 7b | `adapters/sem/receptors.py` |
| Push into bodies | `world_set_axis` writes from the pinned frame (boundaries §4.3) | 7c | `adapters/agents/` (phase1/agents) |
| Wire schema | Generated from the registry as a committed artifact, regenerated and compared (boundaries §9.1) | protocol | `protocol/` |

**The schema is its own module** because the membrane needs units and ranges but may not import the models;
`RegionInstrument.reading_schema` shows the failure, re-deriving a range from a name.

**Contracts in `pyproject.toml`'s style.** import-linter 2.6 has `independence` and `acyclic_siblings` contracts, and
its module fields accept `*` and `**` wildcards (V: `importlinter/contracts/independence.py`, `domain/fields.py`). The
models live in their own subpackage, `models`, so that the wildcard doesn't match the registry, which imports all of
them.

```toml
# Each modality is its own plug-in: no stimulus model imports another, so a new one never edits a sibling.
[[tool.importlinter.contracts]]
id = "stimuli-independent"
name = "stimulus models are independent of each other"
type = "independence"
modules = ["simcore.core.stimuli.models.*"]

# Stimuli read; they never act, write or step. No world, applier, intents, store windows, or laws' internals: they
# get fields through the registry's read capability and bodies through the body frame.
[[tool.importlinter.contracts]]
id = "stimuli-read-only"
name = "stimulus models reach only the schema, the field reader, body frames, geometry and checks"
type = "forbidden"
source_modules = ["simcore.core.stimuli.models"]
forbidden_modules = [
    "simcore.core.world", "simcore.core.applier", "simcore.core.intents", "simcore.core.imagination",
    "simcore.core.scene", "simcore.core.heat", "simcore.core.damage", "simcore.core.body.store",
    "simcore.core.fuel", "simcore.core.solid", "simcore.core.coupling",
]  # fmt: skip

# Laws never know who senses them: fire, plasma, light and sound write fields, and stimuli read those fields.
[[tool.importlinter.contracts]]
id = "laws-blind-to-senses"
name = "no law, store or geometry imports a stimulus or a body frame"
type = "forbidden"
source_modules = [
    "simcore.core.heat", "simcore.core.damage", "simcore.core.grid", "simcore.core.fuel", "simcore.core.solid",
    "simcore.core.coupling", "simcore.core.laws",
]  # fmt: skip
forbidden_modules = ["simcore.core.stimuli", "simcore.core.body"]

# The membrane takes the schema and the published stimulus frame, never a model.
[[tool.importlinter.contracts]]
id = "membrane-reads-stimulus-frames"
name = "the SEM membrane reads stimulus values and specs only (B-13)"
type = "forbidden"
source_modules = ["simcore.adapters.sem"]
forbidden_modules = ["simcore.core.stimuli.models", "simcore.core.stimuli.run", "simcore.core.body.store"]
allow_indirect_imports = true

# Plasma and fire meet only in shared fields, never in each other's code.
[[tool.importlinter.contracts]]
id = "phenomena-independent"
name = "fire, plasma, light and sound laws are independent"
type = "independence"
modules = ["simcore.core.laws.*"]
```

Entries naming unborn modules are inert until a planted import proves them (boundaries §10), hence check 1.
`phenomena-independent` presumes new phenomena under `simcore.core.laws.<name>`; fire_solid §7 places fire flat
(`core/solid.py`), so that is a ruling to make. The existing surface tests force every new core module to be
classified; `MEMBRANE_SURFACE` gains `stimuli.schema` and `stimuli.frame`.

## 3. A plug-in shape: a modality is a module plus one line

**A declaration registry, not a plugin framework.** This is world_v2 §2.5's wording, and the sealed core forces it:
`importlib` is banned from `simcore.core` (the contract `sealed-core`), so there is no entry-point discovery. That is
a feature: registration is a static tuple, its order is the run order, and the order is deterministic and digestible.

```python
# core/stimuli/schema.py
@dataclass(frozen=True)
class StimulusSpec:
    name: str                       # identity for the format's life (F1); a new meaning gets a new name
    receptor: str                   # closed vocabulary: "thermoreceptor_skin", "nociceptor_heat", "photoreceptor"...
    unit: str                       # closed unit vocabulary, the same one the field registry uses
    value_range: tuple[float, float]
    sites: str                      # a site set from body geometry: "skin_patches", "eyes", "ears"
    reads: frozenset[str]           # field-registry names; the only fields its reader will open
    version: int

# core/stimuli/models/_contract.py, the protocol every model meets (the "_" module is outside the independence wildcard)
class StimulusModel(Protocol):
    @property
    def spec(self) -> StimulusSpec: ...
    def prepare(self, fields: FieldReader, bodies: BodyFrame) -> Gathered: ...   # gather: decides nothing
    def kernel(self, gathered: Gathered) -> npt.NDArray[np.float64]: ...         # numbers only: shape (npc, site)

# core/stimuli/registry.py: the one place a modality is named
from simcore.core.stimuli.models import incident_flux, luminance, skin_temperature
STIMULI: tuple[StimulusModel, ...] = (skin_temperature.MODEL, incident_flux.MODEL, luminance.MODEL)
```

**The `prepare`/kernel split** (O34's per-law split, applied to sensing). `prepare` reconstructs the fields over
each site's patch in metres, never "a cell" (CLAUDE.md's reconstruct rule); `kernel` is pure arithmetic. So each
kernel's cost is a B5 row, each kernel meets a closed form without a world, and the gathered data, where a leak would
show, sits at one inspectable seam.

**Capability passing on the read side.** The runner hands each model a `FieldReader` scoped to `spec.reads`; any
other field raises. It is the membrane's move (an applier and a frame view, never the world) one level in, and it holds
"no flammability or φ as a sensor" structurally.

**How each phenomenon plugs in without knowing the others.** The coupling is N + M through registry fields, not
N × M through code.

| Writer (a law in O34's list) | Field it writes | Reader | Stimulus |
|---|---|---|---|
| `heat` | `temperature` (cells) | `skin_temperature` (contact and air at the skin patch) | skin temperature per region |
| fire 6.2: flames | rows in `radiant_emitters` (position, area, temperature, emissivity) | `incident_flux` | incident flux per skin patch |
| plasma (1): torches, welders | more rows in `radiant_emitters`; rows in `sound_sources` | `incident_flux`, via the light and sound laws | (no new stimulus) |
| light transport (Phase 2) | `luminance` after line of sight, from `radiant_emitters` plus lamps | `luminance` | luminance, angular size and flicker at the eye |
| sound propagation (Phase 2) | pressure at the listener, from `sound_sources` | `sound_pressure` | sound pressure and onsets at the ear |
| gas zones (Phase 2), plasma (3) | species in zones (ozone, CO₂) | `chemosensation`, `air_hunger` | concentrations, or air hunger (npcs_and_sem §7.4) |

- **A field with several writers declares itself a contributor table.** Fire and plasma each append rows to
  `radiant_emitters` and never read each other's rows. The registry declares each field's writers and readers, and
  the law list runs every writer before any reader. This is the blackboard pattern, kept honest by declaration
  instead of convention.
- **Plasma arcs:** a law module and its field rows; zero stimulus edits.
- **Hearing:** one model module, one line in `STIMULI`, an `ears` site set, a data file; zero edits elsewhere.
- **The membrane:** `ReceptorSensor(spec, npc, site)` reads `frame.stimuli.value(npc, spec.name, site)`; its schema
  is `spec.value_range`. Nothing new per modality.

Stimuli run after every law and before the frame publishes, so the stimulus at T is a pure function of post-step
state at T, as replay and pinned frames need (§4.2, npcs_and_sem §7.3).

## 4. Checks that keep it that way

**Already covering:** `lint_sizes.py::check_sizes` (blind to free functions and inherited members); ruff's caps
(`C90` 10, `PL` 12 branches), which see a switch only once grown; the four import contracts; the surface
classification tests; `test_ownership.py`'s writer, peek and re-export scans; `_imports.py`'s allowlists and gate
`__all__` rule.

**New checks, and what each one prevents:**

| # | Check | Prevents |
|---|---|---|
| 1 | **Registry completeness.** Every module under `core/stimuli/models/` except `_*` appears in `STIMULI` exactly once; names are unique; every `spec.reads` names a registered field; and the stimulus contracts' module lists equal the packages that exist, by the `CORE_PUBLIC_SURFACE` pattern | An orphan model, which is capability with no caller (CLAUDE.md "A fix ships with a caller"); a typo'd field read; a contract that drifts from the tree and turns inert |
| 2 | **Independence**, the `stimuli-independent` and `phenomena-independent` contracts, each proven by a planted import | One modality calling another ("flux reuses luminance's helper"), the first step to a sensing god module. A shared helper belongs in geometry or a reductions module, and the contract forces that choice |
| 3 | **Declared reads are honest:** a recording `FieldReader`, parametrized over `STIMULI`, asserts each model opened exactly `spec.reads` on a canonical scene | Hidden dependencies, and privileged-state leaks: a model peeking at `material` or `fuel_catalogue` to infer what is flammable |
| 4 | **No central switch on a registered name.** An AST lint that fails on a comparison, `match` case or dict key using a string literal equal to a registered stimulus or field name, outside that model's own module, its data file and the schema | `Frame.reading`'s and `reading_schema`'s pattern repeating for stimuli; a membrane that special-cases `"luminance"` |
| 5 | **Contract tests generated from the registry:** each `STIMULI` entry gets a closed-form test (from the kernel), a cross-tier test (the resolution rule: same outcome class at 0.2, 0.1 and 0.05 m) and a range test (values stay within `spec.value_range`) | A modality shipping without the physics tests CLAUDE.md requires. The registry makes forgetting impossible: the parametrization goes red with no test id |
| 6 | **Writer-before-reader order:** for each registry field, every declared writer comes before every declared reader in the law list, and stimuli come last | Stimuli sampling half a step; fire's emitter rows landing after the light law read them, which is a one-step lag that differs by tier |
| 7 | **Stimuli write nothing:** the writer scan's result has no entry under `simcore/core/stimuli/`, and the window-opener scan likewise | Sensing becoming a backdoor writer ("skin cools the cell it touches"). That coupling is a law, and it goes in the list |
| 8 | **Inherited-surface budget:** a runtime test counting public attributes over the MRO for core classes (`MaterialGrid`'s 25 today), with a budget and a ratchet | God objects assembled by mixins, the gap in `check_sizes` |
| 9 | **Module public-name budget:** top-level public functions and classes per module (today's largest: `checks`, `scene` and `grid`, 6–7) | A module that grows into 30 free functions, which no class count sees |
| 10 | **Fan-out and fan-in budgets** from grimp's graph: a stimulus model imports at most about 5 internal modules; only `registry` imports `models.*`; only `run` and `frame` import `registry` | Hub modules, and a registry consumed from many places, which recreates the switch |
| 11 | **A public-API allowlist:** `core/stimuli/__init__.py` and `adapters/sem/receptors.py` declare `__all__`, and outside code imports only those names (extending `_gate_all` beyond `GATES`) | Reaching into `_contract` or a model's internals from the membrane or the protocol |
| 12 | **Golden schema:** the wire and SEM vocabulary regenerated from `STIMULI` and compared byte for byte (boundaries §9.1) | Silent unit, range or name changes, which world_model F1 forbids |

Checks 2, 7, 11 reuse machinery; 4, 8, 9, 10 are new `scripts/lint_*.py` modules.

## 5. Anti-patterns, from game perception code

- **A central router that knows every sense.** Unreal's AI Perception has per-sense classes (`UAISense_Sight`,
  `_Hearing`) under one `UAIPerceptionSystem` that ticks and routes them all, with sight time-sliced by a shared
  budget, so one sense's cost moves another's latency (S). Per-sense classes are right; the scheduling singleton is the
  god object. Here the runner owns only order; each model's cost is its own row.
- **Omniscient defaults.** `bAutoRegisterAllPawnsAsSources` (S) and Unity NPCs raycasting to the player from
  `Update` (S) read game state ("who is a target"), not a physical channel: "the AI cheats". Check 3 keeps
  `RegionInstrument`-style sensing a lab tool.
- **A global stimulus pool with a silent cap.** Source's `CSoundEnt` holds every world sound in one fixed list that
  NPCs poll (S), dropping past its cap (M). `sound_sources` gets a declared capacity whose overflow is refused or
  counted, never dropped.
- **Awareness apart from senses works.** Thief: The Dark Project fed per-sense inputs into a separate per-agent
  awareness state (Leonard, "Building an AI Sensory System", GDC 1999, S). That is this split: salience and
  "noticed" are Maxim's, never a stimulus model's.
- **Blackboards as dumping grounds** (behaviour-tree blackboards, S): untyped keys anyone writes. The field registry
  is a blackboard with declared types, units, writers and readers (check 6).
- **ECS god systems and many-caller utilities** (Overwatch ECS, Ford, GDC 2017, S): hence check 10, and no
  `stimuli/common.py` that every model imports.
- **Unordered systems** (Bevy's ambiguity detection, Unity's `UpdateBefore`, S): shared data with no declared order
  gives frame-dependent results; check 6.

## Things to raise now

- **`CellStore` is one member from the tripwire, not two.** The reviews' count (10) misses the `time_s` setter that
  the lint counts. The registry PR should take channels out of named properties, which removes 4, before anything else
  is added.
- **`frames.py` depends on `damage`.** If stimulus reductions follow the same path, the frame module will import every
  law. Region reductions should move to their own module when the stimulus frame lands. This is review-held: no
  contract forbids it yet.
- **O34's registry form is undecided.** world_v2 says `data/world/fields.yaml`; boundaries §9.1 says "the in-code
  field registry is primary". The stimulus registry should follow the same form. Pick one before either is built.
- **Not verified:** the `independence` wildcard on a one-child package (plant an import), and §5's engine details.
