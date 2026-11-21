# SEM stimulus interface, lens 1: receptor biology per modality

Research only. Read at Overdrive `phase1/sem-stimulus` `5ff1b7c` (the files the brief names).
Maxim was not re-read for this lens; Maxim claims are quoted from `6b_maxim_perception.md` (origin/main `437ec7b1`).

Tags: **V** read in the primary source or its abstract (named; "V-abs" means the abstract's text as quoted in a
search excerpt, not the page itself). **S** secondhand (a review, textbook or a citing paper). **M** memory, not
checked. **D** my derivation or design judgement.

## 0. In brief

1. **Receptors respond to tissue state at their own site, not to the environment.** The cleanest proof: C-fibre
   heat nociceptors fire at a fixed temperature *at receptor depth* (mean 40.4 °C, depth mean ~0.2 mm), while the
   *surface* temperature at threshold rises with heating rate (**V**, Tillman et al. 1995). A world that hands Maxim
   surface or air temperature forces the receptor to fake a rate-dependent threshold. The world must publish the
   temperature at a declared depth (D).
2. **Most quantities split cleanly by the two leak tests**: an instrument could measure each world quantity in §11;
   everything else is transduction.
3. **The hard problem is time, not ownership.** Physics runs every 0.5 s and ticks every 0.1 s
   (`tile_and_client.md` T3). Thermal, chemical and interoceptive stimuli live on seconds-to-minutes and can be
   sampled. Vestibular (thresholds flat at 1–5 Hz), flicker (fusion up to ~50–90 Hz) and sound (20 Hz–20 kHz) can't.
   For those the world must send **physical summary statistics** (spectra, band power, onset times, kinematics),
   and that pre-filtering is a named ANALOG, never a perceptual word (D).
4. **Body-region granularity differs by modality**: thermal is coarse and summing, touch fine only at the hands
   (§1, §3). One region list for every sense is wrong (D).
5. **Three things look like body physics but sit on the line:** receptor depth (anatomy), pupil size (an effector
   under neural control) and sniff flow (breathing). §10 proposes who owns each.

## 1. Thermoreception (warm, cool)

**Adequate stimulus.** Temperature of the tissue at the receptor ending, and its rate of change. Cool fibres
(TRPM8-class, threshold near 25–28 °C at the channel: **S**, reviews via search) end shallower than warm fibres;
one cool population is epidermal, another dermal (**S**, Filingeri 2016 summaries). I could not verify the classic
depth figures (cold ~0.15 mm, warm ~0.3–0.6 mm, Hensel et al. 1951): **M**.

**Range and resolution.** Detection thresholds differ ~100-fold across 13 regions (face, especially the mouth, most
sensitive; extremities least); cooling is detected better than warming everywhere; sensitivity falls with age
(**V-abs**, Stevens & Choo 1998, *Somatosens Mot Res* 15:13). Thresholds of a few tenths of a degree at sensitive
sites (**M**). The 32–34 °C neutral zone is assumed, its neurophysiology unsettled (**S**).

**Spatial.** Strong spatial summation (larger area, lower threshold) and poor localisation (**S**, Hardy & Oppel
1937 via `6b` §1.1). A coarse region list (hand, forearm, face, trunk...) is adequate; area matters, so the world
should say what fraction of a region is exposed (D).

**Temporal.** Dynamic firing to change, partial adaptation to steady temperature inside the neutral zone (**M**).
Rate matters, but one review reports rates as low as 0.1 °C/s did not raise either threshold (**S**,
Filingeri 2016 excerpt). Contact with copper cools skin ~5 °C in 10 s versus under 2 °C for
plastic (**S**, Ho & Jones 2006 via Jones's Scholarpedia entry): the material effect is entirely tissue/contact
physics.

**World vs receptor (D).** World: a 1D skin conduction profile per region (epidermis, dermis, blood perfusion) driven
by radiant flux, convection and contact (effusivity), publishing temperature at the declared receptor depths in °C.
Receptor: thresholds, dynamic/static coding, adaptation, spatial summation over the region's exposed area.

## 2. Nociception

### 2.1 Heat

**Adequate stimulus.** Temperature at receptor depth. Monkey C mechano-heat nociceptors: receptor depth 20–570 µm,
mean 201 µm (ramps), ~150 µm (steps); threshold at depth 40.4 ± 2.2 °C; surface threshold rose as the ramp went from
0.095 to 5.8 °C/s, "suggest[ing] that the heat threshold for CMHs is determined by the temperature at the depth of
the receptor" (**V**, Tillman, Treede, Meyer & Campbell 1995, *J Physiol* 485:753, abstract read on PMC).

**Two fibre classes, two kinetics.** Type II A-fibre nociceptors (hairy skin): median threshold 46 °C, latency
~120 ms, peak within 1–3 s; type I: median above 53 °C, latency up to seconds; glabrous skin has only type I, which
fits the absence of first heat pain there (**V-abs**, Treede et al. 1995, *J Physiol* 483:747). So *which* fibre
class exists depends on body region (D: a body-YAML fact, not a world fact).

**Consequence for the existing docs (correction).** `6_biofaithful_sem.md` and `fire_model.md` §5.1 say "basal
layer, ~0.1 mm". Tillman's mean is ~0.15–0.2 mm with a spread of over an order of magnitude. At 10 kW/m² the rise
at 0.1 mm vs 0.2 mm is 7.2 vs 5.2 °C at 1 s and 19.0 vs 16.6 °C at 5 s (D: semi-infinite solid, constant flux,
k = 0.37 W/m·K and α = 10⁻⁷ m²/s from memory, no perfusion). That ~2 °C shifts the noxious crossing by about a
second. The depth must be declared, not hard-coded.

**Temporal.** Sensitises rather than adapts (**S**, `6b` §1.1). Damage (Henriques) is the world's.

### 2.2 Cold

Cold pain thresholds disagree by source: near 20 °C, near 12 °C, with pain reported anywhere from 0 to 28 °C;
TRPA1's role in cold pain is contested (**S**, reviews via search). The stimulus is still tissue temperature at
depth; one world quantity feeds warm, cool, heat-pain and cold-pain receptors (D).

### 2.3 Mechanical

**Adequate stimulus.** Tissue stress or strain at the ending (high-threshold Aδ and C). QST measures it as force
through a defined area: pinprick 8–512 mN; algometry through ~1 cm² at 50 kPa/s, where faster loading lowers the
threshold (**S**, QST protocols). No normative kPa threshold found (searched).

**World vs receptor (D).** World: contact normal pressure (Pa) and shear over each patch, contact area, indentation,
and rate. Damage (laceration, crush) is the world's. Receptor: threshold, sharpness (probe area), sensitisation.

### 2.4 Chemical (skin)

Agonist concentration or pH at the ending (**M**); the world owns the surface deposit and its diffusion into skin.
Not needed in Phase 1.

## 3. Touch and pressure

**Four afferent types in glabrous skin:** FA I (RA), FA II (PC), SA I, SA II (**V-abs**, Johansson & Vallbo 1979,
*J Physiol* 286:283). RA and SA I fields are small (medians 12.6 and 11.0 mm²); SA II ~5× and PC ~10× larger
(**V-abs**, Johansson & Vallbo 1980). Density rises proximal to distal, through RA and SA I (**V-abs**, 1979).

**Adequate stimuli** (**M** for the mapping, standard textbook): SA I sustained indentation and edges; SA II skin
stretch; FA I skin velocity and low-frequency flutter (~5–50 Hz); FA II high-frequency vibration (~40–400 Hz, peak
~250 Hz). Hairy skin adds hair-follicle and C-tactile afferents (**M**).

**World vs receptor (D).** World: per contact patch, normal and shear stress, indentation depth, slip velocity, and a
vibration spectrum of the contacted surface (band power above 40 Hz cannot be sampled at 0.1 s; send band power).
Receptor: the four channels, their adaptation, receptive-field pooling. Fine patches on fingertips and palms only;
one patch per region elsewhere.

## 4. Proprioception and vestibular

### 4.1 Proprioception

Muscle spindle primaries signal length change and its speed; secondaries mainly length; Ia differ from II by
dynamic sensitivity, lower threshold and faster conduction; tendon organs signal muscle force (**S**, Proske &
Gandevia 2009/2012 abstracts; Prochazka 2021). Spindle gain is set by fusimotor drive (**M**), i.e. by the nervous
system.

**World vs receptor (D).** World: joint angles and velocities, muscle length and velocity, joint torque under load.
Receptor: spindle and tendon-organ coding, fusimotor gain. Kinematic bodies give "heaviness" no source: ANALOG.

### 4.2 Vestibular

**Adequate stimuli.** Canals: angular acceleration of the head, integrated by cupula mechanics into a velocity
signal above ~0.1 Hz, cupula time constant ~4–7 s, extended centrally ("velocity storage") to ~15–20 s (**S**,
several modelling papers; the central share is disputed). Otoliths: **specific force** (gravity minus linear
acceleration) in the head frame. They cannot tell tilt from translation (**M**, equivalence principle), so the
world must not send "tilt"; it sends specific force and lets the receptor's fusion resolve it (D).

**Thresholds** (direction recognition, 14 healthy subjects, geometric means): yaw 0.74–0.84 °/s at 1–5 Hz, 2.26 °/s
at 0.2 Hz; roll tilt 0.18 °/s at 0.05 Hz to 0.75 °/s at 1 Hz; vertical translation 0.61 cm/s at 5 Hz, 1.67 at
1 Hz, 9.7 at 0.3 Hz (**V**, Valko et al. 2012, *J Neurosci* 32:13537, read on PMC).

**Temporal (D).** The useful band is 0.1–5 Hz; a 0.1 s tick resolves at most 5 Hz (Nyquist), with no margin. Send
angular velocity and specific force each tick, and impacts as peak plus duration.

## 5. Vision

**Adequate stimulus.** Spectral radiance arriving at the cornea from each direction (W·sr⁻¹·m⁻²·nm⁻¹), after line of
sight and attenuation (smoke). Luminance (cd/m²) is its photopic-weighted scalar; retinal illuminance (trolands) is
luminance × pupil area (**M**, definition), so the pupil sits between world and receptor (§10).

**Range.** About 14 log units of luminance through adaptation, a single neural unit only ~1.5 (**S**, Ferwerda et al.
1996). Dark-adapted absolute threshold ~10⁻⁵ cd/m² after ~40 min (**S**, Webvision). The pupil (7 → 2 mm) changes
retinal illuminance by about one log unit (**S**, Webvision): adaptation is mostly neural and photochemical, the
receptor's. The world must therefore send absolute radiance, never a pre-normalised brightness (D).

**Colour.** Three cone classes sample the spectrum (**M**). RGB is a display space, not cone space (D). The
world should send radiance in a few physical bands (or a source spectrum class, such as blackbody temperature for
flames), and the receptor projects onto cone fundamentals. Sending a colour name is an oracle.

**Flicker.** Critical flicker fusion rises with log retinal illuminance (Ferry-Porter) to ~90 Hz at 10⁴ trolands in
some data (**S**, Fernandez-Alonso et al. 2023); at high luminance it plateaus near 50 Hz around 4000 cd/m² (**S**,
Chapiro et al. 2023). Flame puffing at ~1.5 D^−½ Hz (**S**, via `6_biofaithful_sem.md`) is well inside the visible
band but above a 0.1 s tick's 5 Hz for small flames (D: D = 0.05 m gives ~6.7 Hz). So send modulation depth and
dominant frequency per luminous source, not frames.

**Motion, depth, space.** The world sends entity positions and velocities in the eye frame; the receptor detects
motion (D). Disparity works best near the body (**M**), so an exact distance at range is a shortcut: ANALOG, with
noise growing with distance (D). Acuity falls steeply from the fovea (**M**); the receptor applies it to per-entity
angular position and size. Latency ~100 ms (**M**).

## 6. Audition

**Adequate stimulus.** Sound pressure p(t) at each eardrum (Pa), after the head, pinna and canal have filtered it.
Range roughly 0 dB SPL to a pain threshold given as 115–140 dB (**S**, EU SCENIHR table, HyperPhysics);
~20 Hz–20 kHz, thresholds near 80–100 dB SPL at 20 kHz (**S**). Level discrimination ~0.5–1.5 dB (**S**, weak). Interaural time differences
of ~10–20 µs are discriminable (**M**; not found in this search).

**World vs receptor (D).** A waveform at 0.1 s is impossible, so per sound event the world sends arrival time,
band levels at each ear, onset rise time (the frogs' fire cue, `6_biofaithful_sem.md`) and interaural delay. Head
shadow and pinna filtering are acoustics of the body's matter, the world's under lesson 24's tissue rule. Cochlear
filtering, loudness, adaptation and localisation are the receptor's. Maxim's azimuth today takes direction of
arrival directly (`maxim_senses.md` §1): the world localising, an ANALOG to name.

## 7. Olfaction

**Adequate stimulus.** Odorant reaching receptors through the mucus during inhalation. Flow rate, mucus-surface
length and solubility in mucus set perceived intensity (**S**, Hahn, Scherer & Mozell 1994 model); the sorption
account is still debated (**S**). Thresholds span orders of magnitude between odorants (**M**; no table found).

**Temporal.** More than 50% adaptation and recovery often within 2 min, recovery faster than adaptation (**S**,
threshold-scaling study). Continuous exposure of 20 min
elevates thresholds; exposures up to 7 h recover only partly (**S**, Dalton & Wysocki 1996 abstract via search).
Smell rarely wakes a sleeper (**S** here; **V** in `6_biofaithful_sem.md`, Carskadon & Herz 2004).

**World vs receptor (D).** World: gas-phase concentration per species at the nostril (mol/m³), integrated over each
inhalation, and the inhaled volume. Receptor: sorption (per-species solubility is a receptor-side parameter, §10),
per-species threshold, power-law intensity, fast adaptation, sleep gating. No "smells of smoke".

## 8. Airway chemesthesis

**Adequate stimulus.** Irritant concentration at trigeminal and airway endings (TRPA1, activated by acrolein: **V**
in `6b`). Rodent RD50 is the standard measure (**S**). Acrolein RD50 is 0.056 ppm (mouse) in one table and ~1.68 ppm
(rat) in another, a 30× disagreement, so neither is a calibration (**S**). Human formaldehyde eye-irritation
no-effect level 0.5 ppm (**S**). The eyes are a chemesthetic surface too (**S**).

**World vs receptor (D).** World: irritant concentration per species in inhaled air at nose and mouth (ppm), and at
the eye surface. Receptor: thresholds, intensity, sensitisation, cough and blink reflexes.

## 9. Interoception

### 9.1 Core temperature

Thermoregulation takes skin thermoreceptor input as **feedforward** to the preoptic area, and local and core
thermosensitive signals as **feedback**; heat defence can be evoked by skin warming that doesn't change
hypothalamic temperature (**S**, Morrison & Nakamura reviews via search). I found no quantitative skin/core weighting
(searched).

**World vs receptor (D).** World: core (and brain) temperature in °C from a body heat balance (metabolism,
exchange, perfusion). This is tissue physics, and `fire_model.md` §5.1 already says core temperature has one
owner. Receptor: set point, skin-core integration, needs. Skin feedforward means the thermal drive should read
skin *and* core.

### 9.2 Air hunger

Air hunger tracks the mismatch between drive to breathe and achieved ventilation; arterial chemoreceptors respond to
PO₂, PCO₂ and pH; slowly adapting stretch receptors relieve it as ventilation rises (**V**, PMC2834174). Small PCO₂
changes are sensed mainly centrally via brain pH (**S**). Paralysed subjects still felt it when PCO₂ rose (**S**,
Banzett et al. 1990). It lags end-tidal PCO₂ (**S**) and adapts to chronic hypercapnia in ~2 days (**S**, weak).

**World vs receptor (D).** World: arterial PCO₂, PO₂ and pH (kPa or mmHg), lung volume, from a lung and blood
gas-exchange model. Receptor: chemoreflex gain, the drive–ventilation mismatch, lung-stretch relief, adaptation.
Low O₂ at normal CO₂ is weakly felt (`maxim_senses.md` §2; **M** here), so no "oxygen pain".

## 10. Boundary cases and recommendations (D)

- **Receptor depth.** Anatomy, not physics, but the world must compute at it. Proposal: the body declares sampling
  depths per region (e.g. 0.1, 0.2, 0.5 mm) and receptor classes per region; the world computes temperature at
  those depths. That keeps one skin model and avoids hard-coding 0.1 mm.
- **Pupil.** A neurally controlled effector: the world sends radiance, the receptor applies pupil and adaptation.
- **Breathing flow.** The body declares its breathing state; the world integrates concentration over the inhaled
  volume. Mucus sorption stays receptor-side (first transduction stage, and contested).
- **Fast modalities** (vestibular above 5 Hz, flicker, vibration, sound) go as physical descriptors, each a declared
  ANALOG with a cross-tier test.
- **Granularity.** Thermal and nociceptive: a coarse region list with exposed-area fraction. Touch: fine patches on
  hands and face. Vision and audition: per eye and ear. Chemical: per orifice. Interoception: whole body.
- **Existing docs.** `fire_model.md` §5.1's "~0.1 mm" should become a declared depth; its "luminance, angular
  size and flicker" needs spectral bands for colour.

## 11. Table for the design

| Modality | World-computed stimulus (quantity, unit) | Location | Sampling | Receptor side (Maxim) |
|---|---|---|---|---|
| Warm / cool | tissue temperature, °C (rate is derived by the receptor) | declared depths per body region; plus exposed-area fraction | region list (coarse); every tick | static and dynamic coding, adaptation, neutral zone, spatial summation, per-region sensitivity (~100×) |
| Heat pain | same tissue temperature, °C; damage integral to integrity | receptor depth (~0.02–0.57 mm, mean ~0.2 mm) | as above | two fibre classes (~46 °C fast, ~40–53 °C slow; present by region), sensitisation, first/second pain latency |
| Cold pain | same tissue temperature, °C | as above | as above | threshold (12–20 °C, contested), latency |
| Mechanical pain | normal and shear stress, Pa; contact area, m²; loading rate | contact patch on skin | patches; every tick | high threshold, probe-area dependence, sensitisation |
| Touch / pressure | stress, indentation, slip velocity; vibration band power | contact patch | fine at hands and face; vibration as band power (>5 Hz) | SA I, SA II, FA I, FA II channels; receptive-field pooling; adaptation |
| Proprioception | joint angle, rad; angular velocity, rad/s; muscle length and velocity; joint torque, N·m | each joint or muscle | every tick | spindle and tendon-organ coding, fusimotor gain |
| Vestibular | head angular velocity, rad/s; specific force, m/s² (never "tilt") | head frame | every tick (≤5 Hz); impacts as peak plus duration | cupula dynamics (τ ~4–7 s), velocity storage, tilt/translation fusion, thresholds |
| Vision: luminance, colour | radiance in a few spectral bands (or source spectrum class), after line of sight and attenuation; luminance, cd/m² | per eye, per visible entity: angular position, angular size | per tick | pupil, adaptation (~14 log units), cone projection, opponency, eccentricity |
| Vision: flicker | modulation depth and dominant frequency per luminous source | per entity | descriptor | fusion threshold vs luminance (Ferry-Porter) |
| Vision: motion, depth | entity position and velocity in the eye frame; distance (noisy, ANALOG) | per eye | per tick | motion detection, disparity and other depth cues |
| Audition | per event: arrival time, band levels (dB SPL) at each ear, onset rise time, interaural delay; after head and pinna filtering | each eardrum | event-driven | cochlear filterbank, loudness, adaptation, localisation |
| Olfaction | gas-phase concentration per species, mol/m³, integrated over each inhalation; inhaled volume | nostril | per breath | mucus sorption, per-species threshold, power-law intensity, fast adaptation (minutes), sleep gating |
| Airway chemesthesis | irritant concentration per species, ppm | nose, mouth, eye surface | per breath or tick | TRPA1-class threshold, sensitisation, cough and blink |
| Core temperature | core and brain temperature, °C, from body heat balance | body | every tick | set point; skin feedforward plus core feedback |
| Air hunger | arterial PCO₂, PO₂ (kPa), pH; lung volume | blood and lungs | every tick | chemoreflex gain, drive-vs-ventilation mismatch, stretch relief, adaptation |

Primary pages read: PMC1158041, PMC3467969, PMC2834174.
