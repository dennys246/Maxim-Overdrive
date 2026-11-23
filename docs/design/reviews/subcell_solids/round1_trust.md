# Sub-cell solids design, round 1: Trust boundary (2026-11-22)

The reader's report as handed back, saved by the author. Statuses are unset: a reviewer sets them after the fold. The
reader's check scripts were kept in the session scratchpad.

**Reviewed:** `docs/design/subcell_solids.md` at 1c701aa, against these sources:
- `src/simcore/core/{imagination,scene,refusals}.py` at that commit;
- `fire_solid.md` §1.1–§1.4 and §5.2–§5.3;
- on `phase6/specgen-spike` (91ebd0d), the survey, D31–D35, `research/specgen_spike/plan.md`, and
  `spikes/specgen/arms.yaml` with its prompt files.

**Summary:** 4 BLOCKER, 10 SHOULD-FIX, 4 NIT. Nothing in the design lets LLM output write cells around `place`, and
every new check is placed before allocation, as it should be. The problems are of four kinds:
- the new thresholds are compared on float arithmetic that the generator's own coordinates land on;
- the support rule's anchors and edges refuse correct objects;
- the elastic solve has no condition for existing, and the placement check doesn't enforce one;
- several new codes steer a generator toward the wrong fix.

## BLOCKER

**T-B1. `subcell_solids.md::§2.1`: the thinnest dimension is a float knife-edge, and it moves with the origin.** §2.1
computes t = `min(max_m − min_m)` "on the authored float64 values, exactly as written" and says a part exactly at the
threshold becomes cells. The spike's protocol converts whole centimetres with `v / 100`. Enumerating every 40 cm box
edge from 0–300 cm:
- 142 of 261 read below 0.4 m (for example [1, 41] cm gives 0.39999999999999997), so they become objects. §2.2's "a
  0.4 m one is cells" is false for most positions.
- §2.1 doesn't say whether t is taken before or after `_offset` adds `origin_m`. If after, 41 of the 261 flip
  representation between the spec's own frame and offset 0.503 m. That breaks §0(1): "the part's offset never enters
  it".
- At `min_part_thickness_m = 0.001`, 28 of 1,000 one-millimetre parts at whole-millimetre positions read under 1 mm
  and are refused `part_too_thin`. An agent is told its 1 mm part is too thin.

**Failure scenario:** an NPC imagines a 40 cm-thick plinth twice, at two origins. One copy is cells and one is a
structural object, with different thermal laws, load roles and codes. The S1 red-first test would find this only if
its offsets happen to hit a flipping position.

**Proposed fix, verified:** take t from the spec's own coordinates before the offset, quantized to integer
micrometres as cell edges already are (F13): `round(hi·10⁶) − round(lo·10⁶)`. Compare it against the thresholds, also
held in micrometres. With that, all 261 forty-centimetre edges give exactly 400,000 µm, and all 1,000 millimetre parts
give 1,000 µm, both relative and offset. The contract should say this in §2.1. It is an interface that `place`, the
scene builder, the scorer and any client tool must all compute the same way.

**T-B2. `subcell_solids.md::§8.1, §8.4`: the world's floor is not an anchor, so every spec in the spike's scene is
`unsupported`.**
- §8.1's anchors are "one anchor per cell region connected to the world's floor". The spike places every object "in an
  empty 4 × 4 × 4 m air scene at the offset (0.503, 0.503, 0.003) m" (plan §5). That scene has no floor region, so it
  has no anchor, and from S4 every part of every spec is loose.
- On top of that, z = 0.003 m puts every spec's base 3 mm above z = 0, beyond the 1 mm contact tolerance. Even with a
  floor anchor added, the origin the caller chose decides support.
- The plan's own M2 treats "the floor (z = 0)" as a node, so the design and the scorer disagree on what "supported"
  means.

**Failure scenario:** stage 2's reward, written against v1, scores 100% `unsupported`. In A3-style feedback, the
generator is told to fix a spec whose only fault is the caller's origin.

**Proposed fix, unverified:** the contract names the domain floor (and whatever else "anchored" covers) as anchor
vertices in metres. It states how a placement origin relates to contact: either no snapping, with `unsupported`
classed as a placement outcome, or a stated snap rule. The spike's scene offset is checked against that.

**T-B3. `subcell_solids.md::§8.1` ("in v1 nothing else is a joint") with §8.4: correct objects with parts attached at
the side are refused `unsupported`.** Edges are only bearing contacts whose normal is within 30° of vertical. Since v1
has axis-aligned boxes and upright cylinders, that means only top and bottom faces. These are therefore loose:
- a ladder's rungs between rails;
- a door hung in its frame (unless it stands on the floor);
- a shelf on brackets;
- corner brackets on a crate.

The spike's prompt files ask for exactly these: "a steel ladder two metres tall", "a ladder with steel rails and
wooden rungs", "a glass shelf on steel brackets", "a wooden crate with steel corner brackets" and "a wooden door in its
frame". This repeats D34's lesson: a refusal that reflects the model's limits, fed back as a spec fault, teaches the
generator the wrong shapes. Here it would learn to stack rungs on blocks.

**Proposed fix, unverified:** the owner should pick one of these; it is a contract choice, not a mechanism.
- §8.4 refuses only parts with no contact at all to the supported set. Side contacts count as attachment until joints
  exist, and a Known gap records that they carry no load.
- The refusal is classed as a world outcome that is never fed back (see T-S1).

**T-B4. `subcell_solids.md::§8.2`: the solve has no condition for existing, and placement doesn't enforce one.** §8.2
says "a linear-elastic solve over the graph, with axial stiffness E·A/L per member edge". It never states the degrees
of freedom, and "per member edge" is confused, because members are vertices in §8.1.
- If the solve is a 3-D axial truss, almost every piece of furniture is a mechanism. Four pinned legs under a plate
  give a singular stiffness matrix.
- Even as a scalar vertical model, a component without an anchor is singular. §8.4 only checks that each part has a
  path to an anchor, and a member that fails later creates unanchored components.
- Nothing bounds E·A/L. A 1 mm plate 3 m × 3 m bearing on its face (L = 1 mm) has k ≈ 1.8×10¹⁵ N/m. A 1 cm × 3 m
  steel rod has about 5×10⁶. That is a ratio near 4×10⁸ in one factorization.

**Failure scenario:** a spec that passes §8.4 makes the step's factorization raise `LinAlgError`. Because the solve
reruns whenever the topology version changes, every later step raises too, so one accepted spec wedges the world. Or
the solver returns NaN or inf loads, and `load > capacity` is False for NaN, so nothing ever fails: a non-finite
number reaches the band gate without passing through `checks`.

**Proposed fix, unverified:**
- The contract states the model's degrees of freedom: a scalar vertical displacement per vertex, Dirichlet at
  anchors.
- It states the invariant that every anchored component, with every stiffness finite and positive, gives a symmetric
  positive-definite system.
- The solve runs only over anchored components, and placement refuses anything that would break the invariant.
- A solve result that isn't finite is a defined, tested outcome, never an exception inside the step.

## SHOULD-FIX

**T-S1. `subcell_solids.md::§11.3`: the new codes aren't classed, and three of them expose the representation.**
- **Classify each code as a spec fault or a world/placement outcome, and say what `agent_text` carries.**
  - `arms.yaml` feeds back `agent_text` (a code, or a code and a field we wrote), and refuses to feed back
    `too_small` because it is a world outcome.
  - `overlaps_object` (the space is taken by someone else's object), `unsupported` (T-B2, T-B3) and the `world_limit_*`
    codes are outcomes of the world or the placement.
  - `part_too_thin`, `parts_overlap` and `unknown_role` are faults in the spec.
  - The design must give each code its class (tile §3.4 holds the classes) and its field, because stage 2's reward
    and A3's loop read them.
  - `parts_overlap` and `unsupported` can't name the part (a field is never input), so say whether an index within the
    budget is allowed.
- **Leaks.** Three pairs of codes describe the same physical situation, chosen only by whether the thing involved is
  0.39 or 0.41 m thick:
  - `overlaps_object` against `space_taken` (and `fire_solid.md`'s `overlaps_fuel`);
  - `not_flammable` against `not_solid`;
  - `not_on_object` against `not_on_region`.

  The enum is append-only, so the leak would be permanent. Reuse the existing code unless the agent's fix differs.

**T-S2. `subcell_solids.md::§4.1, §4.2, §11.1`: the overlap measure is undefined, and `min_part_thickness_m` equals
the tolerance, so a 1 mm part can be embedded.**
- "Overlap by more than 1 mm" isn't defined: it could mean penetration depth, per-axis intersection, or volume.
  Today's code judges cylinders by bounding box (`scene._check_no_solid_overlaps`).
- Under per-axis intersection, a part whose thickness is ≤ 1 mm lies wholly inside a wall's CSG or another object.
  Its depth along its thin axis is ≤ 1 mm, so it passes. Whether a 1 mm part reads as ≤ 1 mm depends on its position
  (36 of 1,000 do).
- That is the ownership breach `space_taken` exists to prevent: a strike on the wall reaches the embedded part.
- If bounding boxes are used for cylinders, the generator is told `parts_overlap` for parts that don't touch.

**Fix, unverified:** define the measure per pair of kinds (exact for boxes and cylinders), refuse containment, and
require in the loader that `min_part_thickness_m > 2 × contact tolerance`.

**T-S3. `subcell_solids.md::§11.1` (`limits.yaml`): the cross-constraints are contract and aren't stated.** The
constraints the loader must refuse:
- 0 < `min_part_thickness_m` < `object_threshold_m`;
- `breach_ligament_m` < `min_part_thickness_m`. Otherwise a 1 mm pane is breached at insertion, and §6 opens its gap
  the moment it exists;
- `bearing_angle_deg` in (0, 90);
- `lumped_biot_max` > 0.

Each one needs a refusal path and a test.

**T-S4. `subcell_solids.md::§11.1` (`mechanics.yaml`): its bounds are inputs to the solve and the gates, so they are
contract.**
- E, σ_c, σ_t and h_ref must be finite and positive.
- The strength-factor table needs temperatures that strictly increase, with factors in [0, 1].
- `h_contact` keys material pairs. The spelling needs to be canonical, and both (a, b) and (b, a) present must be
  refused as `duplicate_key`.
- `crack_delta_t_k` is "for glass" by name. Say whether its presence on any material enables cracking, so that code
  never keys on a material's name.

**Failure scenario:** E = 0 or a factor table out of order passes the loader, and T-B4's singular or non-finite solve
follows.

**T-S5. `subcell_solids.md::§3.1, §4.2` ("limits are shared"): object-to-object contacts are unbounded, and thin
structure can exhaust the fuel limits.**
- **Contacts:** `fire_solid.md` §1.3 bounds an object's contact rows by its own geometry at 0.05 m. That can't bound
  rows to other objects. Two crossed layers of thin bars make roughly (N/2)² rows: 10⁶ contact rows and graph edges at
  the 2,000-object limit. 63 imagines of 32 bars of 3 mm × 3 mm × 3 m steel (0.2 kg each) build that, all within
  `Budget`. A global object-to-object contact limit is needed, counted with `pending` before acceptance, with its code.
- **Shared fuel limits:** thin structure used to cost cells. Now it draws on the 2,000 objects and 4.8×10⁵ nodes that
  fire's budget was sized for, so 63 such imagines refuse every later fuel object and scene entry. Say whether roles
  get separate budgets.
- **Re-solves:** §8.2's re-solve fires whenever a strength factor changes, which happens every step during a fire.
  Give it a B5 budget at the limit, and state whether failure cascades iterate within a step or across steps.

**T-S6. `refusals.py::TOO_SMALL`, `scene.py::_check_volume`: the claim that "nothing produces it" is false.**
- `scene._check_volume` (lines 58–62) raises `TOO_SMALL` for zero volume, for example a 1e-300 m radius that
  underflows. That runs in `Box` and `Cylinder` construction, before §2.1 could apply.
- The retirement needs that path recoded. `part_too_thin` covers it if §2.1's check runs before construction or
  replaces `_check_volume`. Otherwise `too_small` keeps a second meaning.

**T-S7. `subcell_solids.md::§2.3, §4.3, §11.2` with `imagination.py::_voxelize`: a mixed spec is half-applied, and
its cell parts still judge occupancy on cells.**
- **Half-applied:** cell parts paint inside the `imagine` window, while object parts go to `pending` and appear at the
  batch (`fire_solid.md` §1.4). For up to one step, a region exists without its objects, and strikes and readings in
  that interval see half an object.
- **Occupancy on cells:** `_voxelize` refuses with `mask & grid.solid`, on cells. At sub-cell offsets next to a wall,
  a part of at least 0.4 m whose authored geometry only touches the wall gets `space_taken` depending on where it
  lands. That is D34's class of defect, surviving for the parts that become cells.

The contract should insert the whole region at drain and judge every part's occupancy in metres.

**T-S8. `subcell_solids.md::§11.2`: "spec v1" names two formats.**
- `fire_solid.md` §5.2's fuel spec v1 and this structural spec v1 "are one format, decided at S1". If 6.0b ships
  first, the version number is already taken by a different key set.
- Meanwhile `fire_solid.md` §5.2 still says that structural imagining keeps today's unversioned format, and §12
  doesn't list that edit.
- A reader that dispatches on `spec_version` can't tell the two formats apart. Decide the discriminator (one tagged
  format, or distinct versions) in this contract.

**T-S9. `subcell_solids.md::§3.2, §11.2`: `role` has silent and wrongly coded paths.**
- `role` on a part at or above the threshold has no meaning, since cells carry no role. Silently ignoring it lets a
  spec claim something the world doesn't honour. Refuse it, or define it.
- `role: fuel` in a structural spec is a known role in the wrong place, but it would get `unknown_role`.
  `fire_solid.md` has `kind_not_admitted` for that pattern.
- Scenes admit only `inert` and specs admit both. State why.
- §2.1 doesn't exempt `air` primitives, which scenes allow as carves. A 2 cm air slot would become an object of air, or
  be refused `part_too_thin`.

**T-S10. `subcell_solids.md::§13` (S1, S4): no never-crash property for the new gate.**
- Today `tests/test_imagination.py` has no Hypothesis test, and `lint_gates.py` lists `place` only as "meets".
- v1 adds overlap, contact, graph construction and the support check to the trust boundary.
- S1 and S4 should owe a property (B9): any v1 spec and origin either places or raises `SpecRejected` with a code from
  the enum, leaving the tables, `pending` and the cells unchanged on refusal.
- S1's "every §11.3 code at its gate" also names codes that land at S3 and S4.

## NIT

- **T-N1. `§7.1` (strike):** "within 1 mm of a live object's surface" matches both objects wherever two touch, as at
  every leg under a seat. Name the rule: a deterministic choice, or `ambiguous_point`.
- **T-N2. `§6` (blocked area):** the summed projection of every object within 1 mm of the gap plane counts two panes,
  one on each side of the plane, twice. The blocked area then exceeds the face area, and the open area goes negative.
  Use the union, or state an invariant that can't be broken. This is contract now, even though S5 builds it.
- **T-N3. `§11.4` (save):** the save reader is a gate. Each of these needs a refusal path:
  - until D32, `pose` must be identity (a unit quaternion and zero translation);
  - `support` and `state` must be in their enums;
  - `integrity` must be finite and in [0, 1];
  - if the saved `support` disagrees with the recomputed graph, the load is refused.
- **T-N4. Spike interface:** three things in the spike differ from v1:
  - the frozen instruction text ("Primitives may touch or overlap");
  - M2's touching-or-overlapping connectivity, with its floor node;
  - `a3_never_fed_back: [too_small]`.

  Record in §11.2 or §14.5 which of them stage 2 must replace, so a v1 reward isn't scored against v0's rules.

## What holds

- Every new decision (representation, overlap, support) is judged on authored geometry in metres, before allocation,
  with `pending` counted.
- Objects never write cells, and the only route in is `place`.
- `pose` is reserved at identity.
- The new data files come with gate rows and refusal tests for old versions.
- The `fuel_only_region` gap is closed without adding a code.
