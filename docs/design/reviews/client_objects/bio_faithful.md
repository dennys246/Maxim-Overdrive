# Bio-faithful integration review: client_objects.md (D-B2), round 1, at 51c9660

Reader: Bio-faithful integration lens. Scope: `git diff origin/main...HEAD` in `.worktrees/client-objects`, which is `docs/design/client_objects.md` (359 lines, 4,368 words, under the 6,000-word cap) plus the probe under `tools/godot_probes/`. The probe draws only hand-built data and has no NPC surface, so it isn't reviewed further here.

## Summary

The design hands no NPC a number. `QUANTITIES` is left alone, the bridge isn't touched, and the design doesn't depend on any Maxim mechanism. But it adds a new published quantity to the world's frame, a per-segment fuel view computed in the core in f64, and it states no leak rule for it. That frame is the one object observers read (`frames.py` docstring; boundaries §4.2). The design also leaves open whether SEM will read that view, when sem_stimuli already rules out the kind of input it would be. The design also creates two player/NPC parity divergences it doesn't name: burning and char shown from model fractions, and a pick snap that makes the player's `kindle` sharper than an NPC's would be. The proposed lesson doesn't follow the lessons file's format and teaches nothing about Maxim.

Counts: 0 BLOCKER, 4 SHOULD-FIX, 2 NIT.

## What I checked, and found consistent

- **`QUANTITIES` and the fire_solid §2 pin.** §3.1 says "`QUANTITIES` is untouched". fire_solid §2 pins `temperature_*` and the rest to cells, and says an object quantity becomes a lab instrument under `tests/`, never in `QUANTITIES` or on an NPC builder. The design adds no instrument, no `QUANTITIES` entry and no affordance. Consistent.
- **The NPC fire note's ownership.** fire_solid §7 gives the SEM read path for segment temperature to the NPC fire note. The design defers to it in §3.1 and again in §11 ("any NPC read of fuel"). It doesn't take the decision itself. Consistent, but see S1: deferring the read path isn't the same as stating what this view is.
- **The type guard that exists today.** The bridge imports `FrameSource` (`bridge.py:24`), whose `latest` is an `Observation`. `Observation` (`frames.py:85–99`) exposes only `sequence`, `time_s`, `region_names`, `is_solid` and `reading`. A `fuel` member on the concrete `Frame` or `CellFrame` therefore can't be reached from the bridge under mypy strict unless someone adds it to `Observation`. The protection exists, but it holds only by convention (S1).
- **Cell size.** The fuel tables carry `segment_length_m` (a fixed 0.02 m in metres), not `cell_size_m`. Boundaries §4.4's rule to drop `cell_size_m` from what the membrane sees isn't affected.
- **Structural face glow.** §5.1 draws structural glow from the cell mean as a Known gap. sem_stimuli §2.3 holds face emission to bodies behind a strict red gate in v1. So player and NPC are both missing face emission today, and neither gets a signal the other lacks. No finding.
- **The radiance-equivalent reduction itself.** (Σ a_p T_p⁴ / Σ a_p)^¼ evaluates the T⁴ law per part before it aggregates, as CLAUDE.md's "reconstruct, decide at the point, integrate" requires. That is right for display.
- **Maxim dependence.** The design names no Maxim plan, mechanism, decision or default (no OD-*, MP-* or GL* id), and proposes nothing upstream. "Search Maxim before proposing" doesn't apply. I fetched nothing and didn't read any Maxim checkout. No finding depends on Maxim's origin/main.
- **The "client never feeds back" rule.** The display reductions, textures, floor and flames are all one-way. The only flow from client to world is the pick point (S3).

## Findings

### S1. SHOULD-FIX (contract): the fuel view on the published frame has no leak rule, and the SEM question is left open where sem_stimuli has already closed it

**Location:** `docs/design/client_objects.md::§3.1` ("Presentation only"), with `§9` (step 6.0b's row).

**Defect.** §3.1 says "The core publishes the per-segment reductions of §3.3 on the frame, in f64", and calls this "Presentation only (boundaries §8.3)". Boundaries §8.3 is about *display quantization* living in the protocol layer, and it forbids the core from importing it. It doesn't cover a quantity the core itself computes and publishes. Once the reductions are core-computed members of the frame, they sit in the one object that `frames.py` describes as "what observers read instead of the world". Three of the four columns (`ignited_fraction`, `char_fraction`, `thickness_fraction`) are exactly the fractions fire_model §5.1 says "stay lab instruments until a percept channel exists (OD-C8). They never reach an NPC through a region instrument." The design doesn't state the contract that keeps them out of the membrane:
- the fuel view isn't added to `Observation`;
- it isn't registered as a field;
- it is never `perceivable` (sem_stimuli §7.4).

It names no check for any of the three. CLAUDE.md lists leak rules as contract ("A design document holds the contract: … leak rules"), so this has to fold into the design rather than move to a build step.

Second, §3.1's "Whether SEM ever reads the frame's fuel view is the NPC fire note's decision" leaves a door open that sem_stimuli already shuts:
- §2.3 says stimuli read "through field interfaces over volumes in metres", and that carried state is "never rebuilt from a coarser published state".
- §7.4 says every stimulus `reads` a *perceivable registered field* through a `FieldReader`.

A per-segment area aggregate published on the frame is a coarser published state, not a registered field. The NPC fire note owns *which* source carries segment temperature to SEM (fire_solid §7). It shouldn't have to un-decide whether a presentation view may be that source.

**Failure scenario.** Step 6.0b adds a `fuel` attribute to `Frame`, as §9 requires. Later, the OD-C8 sight percept or the NPC fire note's radiance row needs "is this burning" or "how hot is that stick". The cheapest route is to widen `Observation` with `fuel`, or to read `frame.fuel.ignited_fraction` in an adapter. Either compiles, no test refuses it, and §3.1's sentence reads as permission. The NPC then gets a latch-derived ignited fraction: an oracle of the kind lesson 24 warns about, true but not something a receptor senses. It also gets surface temperatures averaged over 0.02 m strips, against sem_stimuli §2.3's per-point rule.

**Fix (unverified).** In §3.1, state as contract that the fuel view is presentation only:
- it isn't on `Observation`;
- it isn't a registered or perceivable field;
- SEM never reads it, and any SEM read of fuel state goes through the field registry, as the NPC fire note decides.

Then name the guard step 6.0b ships: a test that `Observation`'s members are exactly today's five, or an import or AST rule that `adapters.sem` doesn't touch the fuel view. Delete the guard and confirm the test goes red.

### S2. SHOULD-FIX: player/NPC parity in what fire looks like is changed and not named

**Location:** `docs/design/client_objects.md::§5.2` (Burning), `§6.3` (char as darkening), `§5.3` (no flame before 6.2).

**Defect.** The player sees two cues an NPC's sight row couldn't produce from the same world:
- **Burning.** `ignited_fraction` "adds an emissive flame-lit term on the surface, so a flaming surface is brighter than a merely hot one". That fraction comes from the solid model's ignition latch (fire_solid §1.2, `ignited`), not from a radiating quantity. Before 6.2's flames there is no flame body whose radiance would justify the extra brightness.
- **Char.** Char "shows as darkening, a luminance change measured in L*" from `char_fraction`.

sem_stimuli §2.2 defines the NPC's future sight row as "radiance after line of sight from **surface** temperatures only", with `luminance` the EARN stopgap and fire_model §5.1's in-view luminance tagged ANALOG. So a cold charred stick looks charred to the player and like cold wood to an NPC. A stick that has just ignited at the same surface temperature as an unignited hot one looks brighter to the player and the same to an NPC.

A player seeing more than an NPC isn't wrong in itself, since the player isn't a Maxim agent. But the game's premise is NPCs who live in the same world the player sees. The charter asks that every divergence be named. The design names neither, and §11's "Not settled" doesn't list them.

**Failure scenario.** A playtest or a Phase 4 learning bar asks whether an NPC "notices the crate is burning" or "sees the charred sticks" as early as the player does. It fails, and the cause looks like Maxim when it is really the game's own split between presentation and stimulus. That is the "our bug or Maxim's" ambiguity the future-bar rule exists to prevent: the evidence that isolates the cause would be missing.

**Fix (unverified).** Name both as divergences, either in §5 or in the Known gaps the design already sends to `docs/architecture.md`:
- burning shown by a model fraction, and char shown by darkening, both visible to the player but not part of any stimulus row;
- tagged ANALOG or OPEN against OD-C8.

The NPC fire note can then decide whether sight needs an albedo or char channel.

### S3. SHOULD-FIX: the client's pick snap does part of `kindle`'s target derivation, which an NPC's `kindle` won't share

**Location:** `docs/design/client_objects.md::§4.3` (`F` on a fuel surface).

**Defect.** The pick tests the *drawn, floored* geometry and "returns the point on the true surface nearest the hit". fire_model §5.4 makes `kindle`'s target derivation a server rule:
- the fuel object or solid whose surface is nearest the point, within 50 mm;
- a tie within 1 mm is refused as `ambiguous_point`;
- an NPC's `kindle` is "the same kindle intent from a body, sharing its validators and log".

When the client picks one object and snaps onto its surface, the intent's point is at distance 0 from that object. The server's nearest-surface rule then sees no ambiguity. In effect the client has decided the target, and the player gets a precision aid that an NPC's body intent, which carries no snap, doesn't. This is an input to the world computed by the client. The server re-validates, so the rule against client feedback isn't broken, but the act differs between the two kinds of actor. Rough numbers (derived): at 30 px/m a 2 px floor is 67 mm wide, so a 7.5 mm stick's drawn edge is about 30 mm from its surface. The snap moves the point those 30 mm onto the stick.

**Failure scenario.** Two crossed or touching sticks in R3's starter. The player clicks where their floored drawings overlap. The client's "nearest drawn hit" picks one and snaps onto it. Without the snap, the server would have answered `ambiguous_point`. An NPC aiming at the same spot gets `ambiguous_point`, or a different target, so player and NPC replays of the same intended act diverge.

**Fix (unverified).** Either send the raw hit point and leave derivation entirely to the server's shared validator, or name the snap as a player-only aid and say where an NPC body gets the equivalent. Choosing between them is design work, so this finding stops at the defect.

### S4. SHOULD-FIX: the proposed lesson lacks the file's evidence and consequence and isn't a lesson about Maxim

**Location:** `docs/design/client_objects.md::§8` ("Lesson.").

**Defect.** `docs/lessons_maxim_in_games.md` requires "**the lesson**, then *Evidence* (… with numbers) and *Consequence*", plus the Phase 3 item or design section that acts on it. The proposed text has no numbers, no consequence for Maxim or for a game built with Maxim, and no pointer to what acts on it.

Its stated cause, "a contract with two owners", is the one-owner rule that B36 and CLAUDE.md already record, so the entry would repeat a rule rather than add a lesson. The part that would matter for Maxim is missing: when the world represents something below its grid, NPC sensors are also consumers that must follow the representation (CLAUDE.md: "NPC sensors as reductions over volumes in metres"). So the presentation path and the stimulus path end up as two separate producers of "what the fire looks like", with the divergences S2 names.

**Failure scenario.** The entry goes in as written. The file is "the evidence base for pushbacks to Maxim", and this entry gives a later pushback nothing to cite: no numbers, no consequence. Meanwhile the lesson about presentation versus stimulus parity goes unrecorded, which is exactly what B18 guards against.

**Fix (unverified).** Rewrite in the file's format. Evidence could be:
- B42: `surface_glow` and `burning` built as cell channels;
- the cell-mean glow gap in §5.1;
- the measured 0.23–1.8 px stick width.

The consequence should cover both the renderer and the stimulus path. Or file it as a process note rather than a Maxim lesson.

### N1. NIT: "Presentation only (boundaries §8.3)" cites a section that doesn't cover core-side reductions

**Location:** `docs/design/client_objects.md::§3.1`.

Boundaries §8.3 puts *display quantization* in the protocol layer and forbids the core from importing it. The f64 reductions are computed in the core, so §8.3 covers only the later quantization step. The label promises more than the citation supports. Fixed along with S1.

### N2. NIT: §11 leaves out the parity items

**Location:** `docs/design/client_objects.md::§11`.

"Not settled here" lists "any NPC read of fuel (the NPC fire note)" but not the sight-parity divergences (S2) or the actor parity of the pick (S3). If they are deferred rather than settled, this is where they belong.

## Pushback to Maxim?

None warranted. Nothing in the design argues against a Maxim plan, default or decision. The parity questions in S2 belong to the NPC fire note and OD-C8 on this repo's side, not to Maxim.

## Fold status

All findings `open` (reviewer, round 1).
