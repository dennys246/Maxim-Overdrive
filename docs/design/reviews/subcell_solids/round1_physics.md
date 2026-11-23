# Sub-cell solids design, round 1: Physics and resolution (2026-11-22)

The reader's report as handed back, saved by the author. Statuses are unset: a reviewer sets them after the fold. The
reader's arithmetic scripts were kept in the session scratchpad.

**Document:** `docs/design/subcell_solids.md` at 1c701aa.
**Inputs read:** the survey (`research/subcell_solids/survey.md`, on `phase6/specgen-spike`), D31–D35,
`world_model.md` §1.1–§7, `fire_solid.md` §1.2–§3.2 and the alley scene fixture.

**Summary:** 8 BLOCKER, 9 SHOULD-FIX, 4 NIT. The representation rule has the right intent: metric, per primitive,
never dx.
- As written, it still flips with where a part sits (B1).
- The thermal and strength laws break "decide at the point" at the object's scale (B2, B3).
- Glass cracking can never fire (B4).
- The contact scheme is neither conservative nor stable as stated (B5).
- The load graph can't produce the closed forms it names (B6).
- Support and zone blocking depend on grid and offset (B7).
- The claim that both sides of the threshold give the same outcome class is false by construction (B8).

## BLOCKER

**B1. `subcell_solids.md::§2.1` (the comparison runs "on the authored float64 values, exactly as written").**
- **Defect:** t(p) is `max_m − min_m` in float64, so a nominal 0.4 m box's representation depends on where it sits.
- **Measured:**
  - For a 0.4 m box with `min_m` at each 0.1 m step from 0 to 19.9 m, 81 of 200 positions compute t < 0.4 and become
    objects; the rest become cells. Example: `1.5 − 1.1 = 0.3999999999999999`.
  - Over 200,000 random offsets rounded to 1 µm, 34% become objects.
- **Consequence:** this brings back D34's defect class, where representation depends on where a part lands. S1's own
  red-first test (the same representation at every sub-cell offset) fails for any 0.4 m part.
- **Fix (verified, on the same 200,000 offsets, 0% flip):** compute t in integer micrometres after F13's
  quantization, `rint(max·1e6) − rint(min·1e6)`, and compare it with the threshold in integer µm. Do the same for
  `min_part_thickness_m`, the 1 mm tolerances and `breach_ligament_m`.

**B2. `§3.3` and `§3.1` (one profile per object, one segment per face).**
- **Defect:** a structural object's state is uniform along its two larger dimensions, however large it is.
- **Failure scenarios:**
  - A 3 m steel rail with a flame at one end heats evenly along all 3 m. Lateral diffusion in steel over 600 s
    reaches only about √(1.2×10⁻⁵·600) ≈ 8.5 cm, so the local temperature is underestimated by roughly the length
    ratio, and `thermal_degrade` never fires where it should.
  - A 0.39 m × 10 m × 10 m concrete floor slab is one profile, so a fire under one corner warms the whole slab.
  - A structural wood beam that burns through `fire_solid.md` §4 flashes whole. Fuel objects use 0.02 m strips
    (`fire_solid.md` §1.2) precisely so a front can move.
- **Why it matters:** this is averaging then thresholding at the object's scale. It is grid-free, but it is what
  `world_model.md` §3 forbids, and the error grows with authored size.
- **Fix (unverified):** split structural faces into segments sized in metres per material, each with its own profile
  and lateral conduction between them. The segment size is contract, because it sets the segment and node limits.

**B3. `§7.2::thermal_degrade` ("read at the profile's minimum-strength node").**
- **Defect:** this applies the weakest node's strength factor to the whole section. That is not "integrate upward".
- **Failure scenario:** a 4 cm pine leg under load in a fire. Within about a minute its exposed node passes about
  300 °C and its factor drops to about 0, so the leg's capacity is 0 while its core is cold.
- **Consequence:** S4's closed form (b = b0 − 2βt with β ≈ 0.65 mm/min, about half the width lost in 15 min) can't be
  met, and the table falls about an order of magnitude early.
- **Fix (unverified):** integrate the law over the remaining section, capacity = ∫σ(T(x)) dA, and take E(T) into I for
  buckling. A minimum-node read is right only for local events such as breach.

**B4. `§7.2`, glass cracking, read together with §3.3.**
- **Defect 1, wrong gradient:** the criterion in the cited sources (Pagni & Joshi; Keski-Rahkonen) is an in-plane ΔT,
  between the heated centre and the edge band the frame shades. The design has only a profile across the 6 mm
  thickness, so its "centre" and "edge" nodes can only be mid-thickness and faces.
- **Defect 2, no gradient at all:** with h_ref = 25 (S2's h), a 6 mm pane has Bi = 25·0.003/1.0 = 0.075. That is under
  the 0.1 limit, so the pane is lumped, its ΔT is always 0, and it never cracks. The "Bi ≈ 0.1–0.3" in §3.3 needs
  h_ref ≈ 33–100.
- **Fix (unverified):** give a pane an exposed node set and an edge-band node set, with the band's width in metres
  taken from its frame contacts or authored. It cracks on the ΔT between them, and the closed form is the time to that
  ΔT under constant flux.

**B5. `§5.1` contact ("one antisymmetric transfer … as a Robin condition inside both objects' implicit solves").**
- **Defect:** the two claims can't both hold. When each side is solved implicitly against the other's temperature at
  the start of the step, the two gains differ whenever the capacities differ.
- **Measured** (Δt = 0.5 s, 600 K against 300 K):

| Case | C, side a (J/m²K) | C, side b (J/m²K) | H (W/m²K) | a loses | b gains | Error |
|---|---|---|---|---|---|---|
| Pine first node against 1 cm steel | 312 | 38,465 | 600 | 45.9 kJ/m² | 89.3 kJ/m² | 95% created |
| 1 mm glass node against pine | 2,100 | 312 | 1,000 | — | — | 52% destroyed |

- **Why `fire_solid.md` §3.2's fix doesn't carry over:** there the cell side receives the node's negated gain, which
  works because the cell side is large. Here both sides can be small: the receiving side's H·Δt/C reaches 1.6 in the
  second case, past the limit where it stops overshooting.
- **Fix (unverified):** a coupled implicit solve over each connected set of contacting objects, or a named donor order
  with a stated stability bound. This is contract, because the ledger's `object_contact` closure depends on it.

**B6. `§8.1–§8.2`, the member graph and its solve.** The graph holds neither positions nor rotations.
- **Eccentric load:** for a rigid top on four legs with the load over one leg, the correct split is
  0.75 / 0.25 / 0.25 / −0.25. A graph with one vertical degree of freedom per vertex gives 0.25 to each leg, a 3×
  error on the critical leg.
- **Tension:** the −0.25 is tension in a bearing contact. A linear solve returns it, but bearing can't carry tension,
  so that leg lifts off.
- **Bending:** "between two bearings" needs the positions of the load and of the bearings, and the graph has neither.
- **Misplaced stiffness:** "axial stiffness E·A/L per member edge" puts a member's stiffness on the contacts (edges),
  but members are vertices.
- **Fix (unverified):** give each vertex at least a vertical translation and two tilts; hold contact points in metres;
  solve compression-only contacts with an active set or complementarity method, in a deterministic order; say which
  axes give A, I, c and L for a box.

**B7. `§4.1`, `§8.1` (contacts and anchors against cells) and `§6` (gap blocking): the outcome class changes with
grid and offset.** All three read cell faces, and under §2.3's ½ rule a cell face lands up to dx/2 from the authored
surface.
- **Support:** take §2.1's own example, a 0.5 m plinth (cells) carrying a 2 cm rail, placed at D34's offset. The
  plinth's top cell face is up to ±0.1 m from its authored top at 0.2 m, and ±0.05 m at 0.1 m. The rail is then more
  than 1 mm from the face, so it gets no contact row and no bearing edge, and it is `loose`. So `unsupported` fires at
  some grids and offsets and not others, and the rail's heat contact vanishes with it.
- **Zones:** a pane authored at a zone boundary at 0.203 m is 3 mm from every grid's face, so it never blocks the gap.
  S5's test fails by construction.
- **Fix (unverified):** judge bearing and anchor edges against a cell region's authored CSG in metres, and map the heat
  exchange onto the cells under the authored face by area overlap. Count an object as blocking a gap when it spans the
  opening between the zones' authored volumes, with its projection taken in metres.

**B8. `§2.2` ("both representations must give the same outcome class" near the threshold).**
- **Burning:** wood cells have no fire law (`fire_solid.md` §1.3), but a wood object with `burns_as` burns. So a
  0.39 m post chars and a 0.40 m post never does.
- **Load:** cell regions are anchors with no capacity, so a 0.42 m post can never crush, while a 0.38 m post can.
- **Strike:** a strike lowers a whole object's integrity, but on cells it damages a metric radius.
- **Consequence:** S2's and S4's tests across the threshold will be red.
- **Fix (unverified):** state each law's outcome class on both sides of the threshold. Where they differ, the
  difference gets a strict red gate and a Known gap with its numbers, fixed in a named step (wood cells burning; cell
  capacity under D22).

## SHOULD-FIX

**S1. `§2.3`, ½-overlap voxelization.** A 0.4 m box becomes 0.4 or 0.6 m of cells at 0.2 m, 0.4 or 0.5 m at 0.1 m,
and 0.4 or 0.45 m at 0.05 m. Heat capacity lives in the cells, so it can be up to 1.5× the authored mass, while the
ledger counts the authored mass. The time for heat to cross a wall goes as L², so it can be up to 2.25× too long. The
exact-½ tie also flips on float rounding (B1). Fix: state the gap with these numbers, or weight each cell's capacity
by its overlap fraction.

**S2. `§2.1`, `min_part_thickness_m` = 0.001, the same as the 1 mm overlap tolerance.** A 1 mm sheet buried entirely
inside another solid overlaps it by exactly 1 mm, so it passes and its volume is counted twice, contrary to §3.1. Fix
(unverified): set the minimum to more than twice the tolerance, or judge overlap by intersection volume.

**S3. `§3.3`, `h_ref`.** h_ref decides lumped against 1-D, but fire exposure raises the effective h well above 25.
Linearized radiation alone gives 104 W/m²K at 800 K and 204 at 1,000 K (ε 0.9), so glass flips from lumped (Bi 0.075)
to 1-D (0.3). The contract needs what h_ref represents and the source of its value. Claims that hold: steel stays
lumped up to h = 200 (Bi 0.022), and pine is 1-D at any h (Bi 4.2 at h = 25).

**S4. `§3.3`, 1-D across one axis for a square section.** On a 4 cm × 4 cm leg, the side faces that exchange through
the mean are half the lateral area. Charring from one axis leaves A and I_min too large by 1.19×, 1.48× and 1.95× at
5, 10 and 15 min, and at Bi ≈ 4 the mean sits well below those faces' surface temperature, so their re-radiation is
under-predicted. Fix (unverified): a 2-D section profile, or two orthogonal 1-D profiles, when the two smallest
dimensions are close.

**S5. `§8.2`, Euler K = 1.** A free-standing leg under an unbraced top is a sway member: K ≥ 2 with a fixed base, and
with v1's lack of joints it is a mechanism. For the survey's 4 cm × 0.4 m pine leg:

| K | Euler buckling load | Crushing load | Governs |
|---|---|---|---|
| 1 | 132 kN | 56 kN | crushing |
| 2 | 33 kN | 56 kN | buckling |

The failure mode flips. Take K from the end conditions, or record a Known gap with these numbers.

**S6. `§8.2`, capacity "from authored geometry".** Geometry is immutable and char changes node thicknesses, so capacity
must use the remaining section, or D31's "weakened by fire" means only the strength factor. The solve's cadence key
must also include the section's version.

**S7. `§5.2`, zone radiation "in the same forms" with T∞ replaced by the gas temperature.** This treats the gas as a
blackbody. A 600 °C layer radiating onto 20 °C steel gives about 29 kW/m², about twice what a gas emissivity near 0.5
gives, which halves times to failure. Add a gas emissivity term, or record a Known gap.

**S8. `§6`, blocked area "summed".** Overlapping projections are counted twice: a pane plus its frame, or the two
panes of a double-glazed unit. The open area can then go negative. Use the union of the projections, clipped to the
gap faces, in integer µm².

**S9. `§13`, S2's closed forms.** τ ≈ 1,570 s holds only with one face exchanging and c = 500 (1,539 s at c = 490). A
lumped sheet exchanges through every face, which gives about 770 s, and §3.1 adds radiation. The test must state its
boundary conditions. S3 and S4 name no cross-grid test. B7's scenarios fit: a table on a cell floor, and the rail on
the plinth, at three grids and several offsets.

## NIT

- **N1. `§3.3`, cylinders.** A cylinder's Biot length is V/A ≈ r/2, not r, so its Bi is overstated 2×. The radial
  profile also needs cylindrical metrics, which `fire_solid.md` §1.2's node rule doesn't give.
- **N2. `§5.1`, lumped contact.** For a lumped node, h_a is undefined; state 1/h_a = 0.
- **N3. `§8.1`, contact tolerance.** A leg 0.5 mm short still counts as bearing, though elastic shortening under 250 N
  is about 6 µm. That is acceptable as an idealization; say so.
- **N4. `§7.3`, lumped readings.** For a lumped object, `temperature_max` equals `temperature_mean`; state it.

## Checked, nothing found

- **Reproduced numbers:** 1.30 K/s at 50 kW/m² on 1 cm steel; Bi for steel (0.003–0.006) and for pine (4.2); pine
  crushing at 56 kN against buckling at 132 kN (K = 1); the 1 m × 1 cm steel rod buckles at 969 N (round) or 1,645 N
  (square), against 25 kN yield, so it is a valid buckling case; D31's 6.25× (area) and 39× (I).
- **Grid-freedom:** object-to-object coupling is grid-free, and so are the rule's inputs once B1 is fixed.
- **Ledger:** §5.3's terms and their antisymmetry requirement are right. The scheme (B5) is what fails it.
- **Ambient rule:** extending §5.2's Phase 1 ambient rule to structure, as a Known gap, is consistent with
  `fire_solid.md` §3.1.
- **Breach and destruction:** breach by remaining thickness in metres matches `world_model.md` §3. Sending destroyed
  mass to fines is conservative.
- **Readings:** §7.3's bit-identical pin for cell-only regions is sound.
- **Shipped scene:** every primitive in the alley fixture is at least 0.4 m thick, so none changes representation.
  `wall_end`'s t is 0.40000000000000036, which shows B1's fragility.
- **Threshold:** 0.4 m as two coarse cells is consistent with `world_model.md` §1.1.
