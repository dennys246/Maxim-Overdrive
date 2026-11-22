# Sub-cell solids: research survey (2026-11-22, for D31, D32 and D34)

This is the research that grounds the sub-cell solids design (D34), which isn't written yet. It is condensed from one
research pass, and the repo was read at `phase6/specgen-spike`. Each claim is tagged:
- **V:** the primary text was read in that pass;
- **S:** secondhand;
- **M:** from memory, to check before it reaches `data/`;
- **D:** derived by hand arithmetic.

## 0. What ruling 72 actually forbids

`world_model.md` §1.1 allows sub-cell geometry only as fuel objects, "never structure" (docs-contracts ruling 72). The
recorded reasons are about definition, not physics.

**The exemption had no definition.** In `reviews/fire_model/architecture.md` A-S4 (V), nothing said what may be authored
as an element rather than as cells. Breach and strike were undefined on elements, and so were `thermal_degrade`,
`crack`, `kindle`'s region, `place`'s "smaller than one cell", footprints and ownership. The fold left that **open**
for strike and breach (`reviews/fire_model/fold.md:49`). `fire_solid.md` §2 instead refuses every act on an
object-only region (`fuel_only_region`).

**Representation must never be chosen by dx.** `reviews/fire_model/delta1_wire_trust.md` N-B1 (V): when `place` picked
the representation by grid spacing, one spec gave two outcome classes across tiers. The fix was "the recipe decides".

So the store can be generalised, provided the design:
- defines strike, breach, integrity, degradation and load on objects;
- chooses the representation by an authored, metric rule, never by dx.

**Two conflicts the design must face.**
1. **`fire_solid.md` §3.1's ambient rule breaks for structure.** Every object surface loses heat to a fixed ambient,
   and "hot gas never preheats fuel". A steel sheet or a glass pane in a burning room would then never heat from the
   room's gas, which is the dominant load case. Structural objects need coupling to zone gas. Phase 1 zones are well
   mixed and have no dx, so the coupling would be grid-free, but it is a new law and revises §3.1.
2. **Zone topology is counted from cell faces** (`world_model.md` §2, §6). A sub-cell pane that isn't cells closes no
   gap between zones, so objects must enter the gap count. Otherwise a pane is decoration.

## 1. Representation options

The test cases are a 1 cm steel sheet, a 6 mm pane and a 4 cm wooden leg.

| Option | Heat | Breach and load | Cross-grid | Verdict |
|---|---|---|---|---|
| **A. Volume fraction per cell** | needs a mixture conductivity; series and parallel differ by orders of magnitude, and φ carries no orientation | the section is reconstructed, and reconstruction (PLIC) fails for one-cell sheets (M) | conserves mass, but geometric decisions depend on dx; about 7.7 MB per f32 channel at 1.92×10⁶ cells (D) | reject as primary |
| **B. An object store in metres, coupled to cells and zones** (the fuel-object pattern) | a 1-D profile or one lumped node by Biot number: steel 1 cm Bi ≈ 0.005, glass 6 mm Bi ≈ 0.1–0.3, pine 4 cm Bi ≈ 4 (D) | decided on the part's own state in metres; load from a member graph of authored parts | laws grid-free; dx enters only through contact rows, the skin's far boundary and zone membership | **recommended** |
| C. Cut cells / embedded boundary (Schwartz et al., JCP 2006, S) | second-order and conservative, but needs small-cell stabilisation and multi-valued cells for thin sheets (M) | capacity still needs geometry elsewhere | good | overkill for conduction-only cells (FDS moved to cut cells for flow, V) |
| D. Immersed boundary (Mittal & Iaccarino 2005, S) | smears the interface over about 2 cells, non-conservative (FDS lists "penetration errors", V) | | the smearing scales with dx | reject |
| E. Signed distance field or level set | loses volume below about 2 cells (M) | | | only for query geometry, evaluated analytically from the authored shapes |
| F. Shells (a surface plus a thickness) | a 1-D profile on the surface (FDS thin obstructions) | plate theory | | the same as B with kind `sheet` |
| **G. Hybrid: cells for thick parts, objects for thin** | | | **the switch must be a metric rule in data**, never "thinner than this run's cell" (N-B1) | the realistic answer: B within G |

**The consequence the owner should see.** A metric switch, say "any dimension under 0.4 m", makes most furniture,
panes, doors and pipes objects. The object store becomes the main path for imagined objects. The alternative, a
material class (sheet metal, glass and furniture timber always objects), makes a 0.5 m oak block behave oddly.

**A variant to decide inside B:** a per-object local voxel grid at a fixed metric resolution, say 1 cm, in the object's
own frame, Teardown-style. It is grid-independent from the world's side, supports bodies (D32) and fracture into new
objects, and costs (L / 1 cm)³ per object. It brings back "a scratch becomes a breach" at 1 cm.

## 2. How others do it

**FDS** (V, User Guide source on `firemodels/fds` master; check it against our 6.11.1).
- **Thin obstructions:** "approximated as an infinitely thin sheet … like window panes, form a flow and (partial)
  radiation barrier … allowed to have thermally-thick boundary conditions."
  - The sheet snaps to a cell face, and `THICKEN=T` forces it to a full cell.
  - Heat uses the surface's own `THICKNESS`, a 1-D solid independent of the obstruction's extent (S, forum).
- **Small things are dropped by grid:** "If at least two of the three obstruction dimensions are less than half of the
  corresponding cell dimensions, the obstruction is ignored." That is our `too_small` class of defect: a precedent for
  the defect, not for a fix.
- **`BULK_DENSITY`** takes mass from authored dimensions, "independent of the grid resolution": a precedent for mass
  from authored geometry.
- **HT3D:**
  - 3-D conduction for steel by splitting the 1-D solver, with obstructions snapped to the grid;
  - I-beams are modelled as collections of zero-cell-thick obstructions;
  - no burn-away.
  - FDS has no load model, and structural coupling to FE codes is external (M).
- **Lagrangian solid particles** "represent a wide variety of subgrid-scale objects … the same solid phase conduction
  and pyrolysis algorithm … as … solid walls". This is FDS's analogue of an object store.

**Games.**
- **Teardown** (V: Wittens' frame analysis; Gustafsson in 80.lv).
  - Each object is its own 3-D volume, one byte per voxel into a 256-entry palette, and moves freely off the world
    grid. Destruction splits disconnected chunks into new objects.
  - Multiplayer sends destruction as deterministic ordered commands, but "the physics still use[s] traditional state
    synchronization". That is evidence that a production engine didn't get deterministic rigid bodies.
  - The voxel size, about 10 cm, is M.
- **Minecraft** partial blocks (M): a per-state collision shape in a fixed sub-block frame, with the world grid kept
  at one id per cell.
- **Block-graph structural heuristics** (7 Days to Die, Red Faction Guerrilla, Medieval Engineers; M, unverified):
  not verifiable against closed forms, so not to copy.
- **Deterministic rigid bodies** (S): Jolt is deterministic on one binary and platform, and cross-platform with a
  flag at about 8% cost. Rapier and Box2D v3 make similar claims. Godot's Jolt makes no guarantee, which is one more
  reason D32's bodies stay on the server.

## 3. Generalising fuel objects

Fuel objects could become sub-cell objects with a `role` (fuel, structure, inert) and new kinds: `sheet`/`plate`,
`member` and `pane`. Then:
- `fire_solid.md` §1.3's "structural materials are cells" becomes the metric rule. A fuel `slab` and a structural
  `plate` must never be told apart by dx; that is N-B1's test.
- §2's `fuel_only_region` gives way to acts defined on objects, which closes A-S4.
- §3.1 gains zone coupling (conflict 1), and zone gaps count panes (conflict 2).
- `world_model.md` §1.1 and CLAUDE.md's thin-features line are revised.
- Mixed regions (cells plus objects, such as a steel-framed glass case) are needed now, not at 6.2.
- The digest, save, snapshot (§5.5–5.6, "no objects on the wire") and limits change.
- **Load needs joints and supports read from authored geometry,** with §1.3's 1 mm contact tolerance. D33's placement
  check reads the same graph.
- **The fuel store's sizing** (a 0.02 m segment strip, 2,000 objects) was set for fuel, and is re-measured at the
  build step.

## 4. Tests the design will need

Every closed form below is grid-free when the law runs on the object, so the cross-grid tests check coupling and
placement.

**The common red-first test:** place the 2026-11-22 footstool, aquarium and locker specs (`spikes/specgen/arms.yaml`)
at N sub-cell offsets × 0.2, 0.1 and 0.05 m. Require the same representation, the same refusal outcome and the same
mass.

- **A thin steel sheet, lumped (Bi ≪ 0.1):**
  - Under constant net flux, dT/dt = q″/(ρ·c·t): about 1.3 K/s at 50 kW/m² on 1 cm steel (D).
  - Convective only: T∞ + (T0 − T∞)·exp(−h·t/(ρ·c·δ)), with τ ≈ 1,570 s at h = 25 (D).
  - The Eurocode 3 unprotected-steel step is M.
- **A sheet between two solids:** q = ΔT / (R_skin1 + δ/k + R_skin2).
- **Glass breach:** cracking starts at a centre-to-edge ΔT of about 58 K (Pagni & Joshi, Fire Safety Science 3, 1991,
  S) or about 80 K (Keski-Rahkonen, S). The closed form is the time to that ΔT under constant flux. The band is gated
  in input flux with a margin (ruling 60), and the validation scatter is large.
- **A wooden leg:**
  - crushing P = σ_c·A, Euler buckling P_cr = π²·E·I/(K·L)², and char b(t) = b0 − 2βt with β ≈ 0.65 mm/min (EN
    1995-1-2, M);
  - a 4 cm × 0.4 m leg crushes first, at about 56 kN against about 130 kN for buckling (D). The buckling branch needs
    a slender member, such as a 1 m × 1 cm steel rod.
  - With cells at 0.1 m, a 4 cm leg's area is off by 6.25× and its I by about 39× (D): the size of D31's risk.
- **Zones:** a pane separates two zones at every grid and offset, and its breach joins them.
- **Margins:** option B keeps each decision variable (ΔT, remaining section, load against capacity) in metres, so its
  band comes from the law and its inputs. A and E carry a band in dx that can't clear a margin at 0.2 m.

## 5. Contract questions the design must answer

1. **The representation rule:**
   - a metric thickness or a material class, set in data, never dx;
   - the kinds;
   - analytic primitives or local voxels;
   - `too_small` defined in metres.
2. **The table:** its schema and version, with role, kinds, geometry, pose (D32), joints and supports. Is it one store
   with fuel, or a sibling? What replaces `fuel_only_region`?
3. **Ownership and overlap:** objects against cells, objects against objects, and mixed regions.
4. **Coupling:** contact skins, zone gas replacing §3.1 for structure, and radiation. Every ledger term is
   antisymmetric.
5. **Zone topology:** the integer counting rule for gaps an object closes.
6. **Acts and laws on objects:** strike, breach, `thermal_degrade`, `crack`, integrity and fines.
7. **Load:**
   - the member graph and its capacity;
   - the cadence: on events and as strength changes;
   - the hand-off to rubble (D22) or to bodies (D32);
   - D33's check.
8. **Sensors:** quantity names that reduce over a metric volume across cells and objects; what an NPC senses of
   weight, contact and motion.
9. **The snapshot:** an object-table channel (id, kind, pose, dimensions, material, temperature, integrity, crack
   shape), never shown by colour alone, and which tier draws what.
10. **Formats:** limits, refusal codes, the digest, the save, the replay header, and spec v1 for `imagine`.

**Owner questions before the design is drafted:**
- (1) metric threshold or material class;
- (2) analytic primitives or per-object local voxels;
- (3) one store with fuel, or a sibling.

**Answered (owner, 2026-11-22, D35):** a metric threshold in data, analytic primitives, and one store with a `role`.

## Sources

- **FDS:**
  - [User Guide source](https://raw.githubusercontent.com/firemodels/fds/master/Manuals/FDS_User_Guide/FDS_User_Guide.tex);
  - forum threads on [thin obstructions](https://groups.google.com/g/fds-smv/c/JwqQ2E9lcIc),
    [surface thickness](https://groups.google.com/g/fds-smv/c/zK8RI7AlPNs) and
    [1-D against HT3D](https://groups.google.com/g/fds-smv/c/WaUenZxDqaU).
- **Numerical methods:**
  - [Schwartz et al. 2006](https://escholarship.org/uc/item/0fp606kk);
  - [Mittal & Iaccarino 2005](https://www.annualreviews.org/doi/abs/10.1146/annurev.fluid.37.061903.175743).
- **Glass:**
  - [Pagni & Joshi 1991](https://publications.iafss.org/publications/fss/3/791);
  - [glass failure criteria, Frontiers 2024](https://www.frontiersin.org/articles/10.3389/fther.2024.1488206/full).
- **Teardown:**
  - [Wittens' frame teardown](https://acko.net/blog/teardown-frame-teardown/);
  - [80.lv on multiplayer and destruction](https://80.lv/articles/teardown-developer-breaks-down-multiplayer-and-voxel-destruction-tech).
- **Rigid-body determinism:**
  - [Jolt](https://jrouwe.github.io/JoltPhysics/md__build_2_r_e_a_d_m_e.html);
  - [Box2D](https://box2d.org/posts/2024/08/determinism/);
  - [Rapier](https://rapier.rs/docs/user_guides/rust/determinism/).

**Not verified:**
- Teardown's voxel size;
- Minecraft's shape system;
- the structural-integrity games;
- the Bi < 0.1 source text;
- the Eurocode 3 and 5 clauses;
- the Keski-Rahkonen venue;
- the multi-valued cut-cell claim;
- the level-set thin-feature loss;
- every material property value.
