# Time in the brain: rate limits, clocks and perceived time

Research note for the NPC time design. Question from the owner: the world has its own clock (pause, slow-mo, up to
~20x), wall-clock time must never reach an NPC, and the brain perceives time its own way, coarsely, with intrinsic
rate limits set by its physics. How do we make NPC time bio-faithful?

Status: research, not a decision. Numbers are given with units and a source. Where a number varies a lot between
preparations, the range is given and the reason. Where the evidence is contested, that is said in place.
Sources were checked against the primary paper where possible; a few numbers (marked "approx.") are from reviews
or from my reading of the literature and should be rechecked against the primary paper before any of them becomes a
tunable in `data/`.

Contents

1. Intrinsic rate limits and their timescales
2. Is there a brain "tick"?
3. The resolution ladder: how coarse is perceived time at each scale, and why
4. Interval timing
5. Subjective time distortion
6. Circadian, homeostatic and ultradian clocks
7. How the brain gets universal time at all
8. What this means for a simulated agent

---

## 1. Intrinsic rate limits and their timescales

### 1.1 The spike itself

| Quantity | Typical value | Notes / source |
|---|---|---|
| Action potential width | ~1 ms (pyramidal), 0.2–0.5 ms (fast-spiking interneurons) | Na+ channel kinetics, Kv3 channels make FS spikes narrow (Rudy & McBain 2001) |
| Absolute refractory period | ~1–2 ms | Na+ channel inactivation; no stimulus can fire the cell |
| Relative refractory period | ~2–10 ms, longer in some cells | K+ conductance still open; a stronger stimulus is needed |
| Membrane time constant | 10–30 ms at rest in cortex; ~5 ms or less in the high-conductance state in vivo | Destexhe, Rudolph & Paré 2003, *Nat Rev Neurosci* |
| Synaptic delay | ~0.5 ms | Katz & Miledi 1965 |
| Spike-timing precision under strong fluctuating input | ~1 ms, reproducible across trials | Mainen & Sejnowski 1995, *Science* |

The refractory period caps the instantaneous rate at roughly 500–1000 Hz. In practice, sustained rates are much
lower and depend on cell type:

| Cell type | Typical / maximal sustained rate |
|---|---|
| Fast-spiking PV+ interneurons | 200–400 Hz sustained in slices, bursts higher |
| Auditory brainstem (MNTB, calyx of Held relay) | can follow 300–800 Hz |
| Cerebellar Purkinje simple spikes | ~50–100 Hz spontaneous, >200 Hz when driven; complex spikes ~1 Hz |
| Neocortical pyramidal neurons | usually <10 Hz in vivo, median well below 1–2 Hz (Barth & Poulet 2012, *Trends Neurosci*); intraburst rates 100–300 Hz |
| Midbrain dopamine neurons | tonic pacemaking ~2–8 Hz, phasic bursts ~15–30 Hz for ~100–200 ms (Grace & Bunney 1984; Schultz 1998) |
| SCN neurons | ~5–10 Hz in subjective day, ~1 Hz or less at night |

The binding constraint in cortex is energy, not refractoriness. Attwell & Laughlin (2001, *J Cereb Blood Flow
Metab*) estimated that signalling costs cap the average cortical rate at a few Hz; Lennie (2003, *Curr Biol*)
estimated that the energy budget lets only about 1% of cortical neurons be substantially active at once, with a mean
rate below 1 Hz. **This is a rate limit with a computational consequence: sparse coding.**

**Spike-frequency adaptation.** Under a sustained step of input, most pyramidal cells fire fast and then slow down.
Ca2+-activated K+ currents (SK, BK) and the M-current produce afterhyperpolarizations on three timescales: fast
(~1–5 ms), medium (~50–100 ms) and slow (sAHP, ~1–several s) (Sah 1996; Benda & Herz 2003, *Neural Comput*).
Benda & Herz showed that adaptation of this kind acts as a high-pass filter on the input: the cell reports changes
more than levels.

### 1.2 Vesicle pools and their recycling

A presynaptic bouton holds vesicles in functionally defined pools (Rizzoli & Betz 2005, *Nat Rev Neurosci*):

| Pool | Share of vesicles | Behaviour |
|---|---|---|
| Readily releasable pool (RRP) | ~1–2% (e.g. ~5–10 vesicles at a small hippocampal bouton; thousands at the calyx of Held) | docked, primed, released within ms of a Ca2+ signal |
| Recycling pool | ~10–20% | refills the RRP during moderate activity |
| Reserve pool | ~80–90% | used only under intense stimulation, if at all |

**RRP refill.** Times vary with synapse and with residual Ca2+:

- Hippocampal synapses: refill time constant ~10 s at rest, accelerated by activity-dependent Ca2+ (Stevens &
  Wesseling 1998, *Neuron*; approx.).
- Calyx of Held: fast-releasing vesicles recover slowly, τ ≈ 4–6 s (single exponential ~6 s, or double exponential
  with ~0.4 s and ~6 s components). Slow-releasing vesicles recover in ~0.1 s. Ca2+/calmodulin speeds recovery
  (Wang & Kaczmarek 1998, *Nature*; Sakaba & Neher 2001, *Neuron*). Some calyx studies report a single ~1 s τ for
  the whole RRP. The spread comes from developmental stage, temperature and fitting method.
- Release-site clearance (the site must be emptied of the previous vesicle's material before another can dock)
  adds a fast limit of ms to tens of ms (Neher 2010; Hosoi, Holt & Sakaba 2009, *Neuron*).

**Endocytosis (retrieving vesicle membrane):**

| Mode | Time | Source |
|---|---|---|
| Ultrafast endocytosis | 50–100 ms | Watanabe et al. 2013, *Nature* (flash-and-freeze) |
| Kiss-and-run (transient pore) | <1 s, reported down to hundreds of ms; how common it is remains contested | Aravanis, Pyle & Tsien 2003, *Nature*; Zhang, Li & Tsien 2009, *Science* |
| Clathrin-mediated endocytosis | τ ≈ 15 s at hippocampal synapses (dominant mode there) | Granseth et al. 2006, *Neuron* |
| Bulk endocytosis | seconds to tens of seconds, under heavy stimulation | Clayton & Cousin 2009 |

After retrieval, a vesicle must reacidify (τ of a few s; Atluri & Ryan 2006, *J Neurosci*) and refill with
transmitter before it is useful again. A full cycle is tens of seconds to about a minute.

**SNARE, Munc13 and Munc18 priming.** Fusion itself takes <0.5 ms after Ca2+ binds synaptotagmin-1. Before that,
Munc18 and Munc13 template assembly of the SNARE complex (syntaxin-1, SNAP-25, synaptobrevin) to make a vesicle
"primed" (Rizo & Südhof 2012, *Annu Rev Cell Dev Biol*). Priming is the rate-limiting step for RRP refill, so it
runs on the ~0.1–10 s timescales above. After fusion, NSF and α-SNAP use ATP to pull apart the spent cis-SNARE
complexes. Ca2+/calmodulin and DAG acting on Munc13 accelerate priming, which is one route by which recent activity
speeds recovery.

### 1.3 Short-term plasticity

Zucker & Regehr (2002, *Annu Rev Physiol*) list the classes:

| Process | Time constant |
|---|---|
| Paired-pulse facilitation | tens to ~100s of ms |
| Augmentation | ~5–10 s |
| Post-tetanic potentiation | ~30 s to minutes |
| Short-term depression (RRP depletion and other causes) | recovery ~0.1 s to ~10 s |

The Tsodyks–Markram model (Tsodyks & Markram 1997, *PNAS*; Markram, Wang & Tsodyks 1998, *PNAS*) has three
parameters: release fraction U, a recovery time constant τ_rec and a facilitation time constant τ_facil. Fits for
neocortical pyramid-to-pyramid connections give U ≈ 0.5 and τ_rec ≈ 0.5–1 s with little facilitation. Pyramid onto
some interneurons gives low U, τ_facil of ~0.5–1.5 s and a short τ_rec (approx.).

**Computational consequences** (the part that matters for us):

- **Gain control and change detection.** With strong depression, the steady-state response becomes roughly
  independent of input rate, so the synapse signals relative change in rate (Abbott, Varela, Sen & Nelson 1997,
  *Science*). This is a Weber-like normalization built from a resource that depletes and recovers.
- **Temporal filtering.** Depressing synapses act as low-pass filters and facilitating synapses as high-pass or
  burst detectors (Fortune & Rose 2001, *Trends Neurosci*; Lisman 1997, *Trends Neurosci*).
- **Short-term memory.** Facilitation on a ~1 s timescale can hold a working-memory item "silently" in synaptic
  state with no persistent firing (Mongillo, Barak & Tsodyks 2008, *Science*). This is contested as the main
  mechanism.
- **Fatigue and habituation.** A repeated stimulus drives a depleting pool down, so the response shrinks. Behavioural
  habituation over minutes to hours involves more than vesicle depletion (Thompson & Spencer 1966; Rankin et al.
  2009), but synaptic depression is the fastest part of it.

### 1.4 Transmitter clearance

| Transmitter | Clearance | Notes |
|---|---|---|
| Glutamate in the cleft | decays with τ ≈ 1–2 ms | Clements et al. 1992, *Science* (~1.2 ms). Astrocytic transporters (GLT-1/EAAT2) bind fast but cycle slowly (~tens of ms per transport), so they act as buffers (Wadiche et al. 1995) |
| GABA | a few ms in the cleft | GAT-1 transporters |
| Acetylcholine | <1 ms at the neuromuscular junction | AChE is one of the fastest enzymes known |
| Dopamine | volume transmission; striatal DAT clears a phasic release in ~tens to ~100s of ms | Cragg & Rice 2004, *Trends Neurosci*; in prefrontal cortex DAT is sparse and clearance is much slower (seconds), via NET and COMT |
| Neuropeptides | minutes, by diffusion and peptidases | |

### 1.5 Receptor kinetics

| Receptor | Rise | Decay | Notes |
|---|---|---|---|
| AMPA | ~0.2–0.6 ms | ~1–5 ms deactivation; desensitizes in ~5–10 ms, recovery from desensitization 10s–100s of ms | GluA subunits and TARPs set the values |
| NMDA | ~5–10 ms | ~50 ms to >1 s: GluN2A ~50–100 ms, GluN2B ~250–400 ms, GluN2C/D slower | Mg2+ block makes it a coincidence detector of pre and post activity; the long decay sets a ~100 ms integration window (Lester et al. 1990; Paoletti, Bellone & Zhou 2013) |
| GABA-A | ~0.5 ms | ~5–50 ms (α1 fast; extrasynaptic α5/δ tonic) | |
| GABA-B (metabotropic) | onset ~30–50 ms, peak ~100–150 ms | ~300–500 ms or more | G-protein via GIRK channels |
| Metabotropic modulatory receptors (mGluR, D1/D2, 5-HT, β-adrenergic) | 100s of ms | seconds to minutes | second messengers, PKA etc. |

The NMDA decay is the reason "integration windows" of ~100 ms appear repeatedly in cortex; slow recurrent NMDA
currents are one proposed basis of persistent activity and slow integration (Wang 1999, 2002, *Neuron*).

### 1.6 What the rate limits add up to

The rate limits form a **hierarchy of timescales**, roughly one order of magnitude per mechanism: spikes (~1 ms),
fast synapses (~1–10 ms), NMDA and membrane integration (~10–100 ms), short-term plasticity and adaptation
(~0.1–10 s), vesicle recycling (~10–60 s), neuromodulator tone (seconds to minutes), hormonal state (minutes to
hours), circadian (~24 h). Across primate cortex, intrinsic timescales measured from spike autocorrelation also grow
along the hierarchy: ~50–100 ms in sensory areas up to ~200–350 ms in prefrontal areas (Murray et al. 2014, *Nat
Neurosci*).

They do **not** add up to a clock. Every one of these processes runs continuously in physical time, each with its
own time constant and none synchronized to the others.

---

## 2. Is there a brain "tick"?

### 2.1 No global clock

The brain has no central oscillator that every process steps on. Cortex in vivo sits mostly in an
**asynchronous-irregular** state: spikes are irregular (close to Poisson) and only weakly correlated across cells
(van Vreeswijk & Sompolinsky 1996, *Science*; Brunel 2000, *J Comput Neurosci*; Renart et al. 2010, *Science*).
Rhythms do exist, but they emerge from local circuits and come and go with state (Buzsáki & Draguhn 2004,
*Science*; Buzsáki 2006, *Rhythms of the Brain*).

### 2.2 Oscillations as local, intermittent "frames"

- **Gamma (30–80 Hz, cycles of ~12–33 ms)** comes from PV interneurons in pyramidal–interneuron loops (Cardin et al.
  2009, *Nature*; Sohal et al. 2009, *Nature*). It has been proposed to package spikes for communication between
  areas ("communication through coherence"; Fries 2005, 2015). It is a poor clock: its frequency moves with stimulus
  contrast (Ray & Maunsell 2010, *Neuron*) and it appears in bursts.
- **Theta (4–8 Hz)** in the hippocampus organizes place-cell spikes (phase precession; O'Keefe & Recce 1993) into
  compressed sequences. The theta–gamma code is proposed to hold about 7 items, one per gamma cycle in each theta
  cycle (Lisman & Jensen 2013, *Neuron*).
- **Alpha (8–12 Hz)** is the main candidate for a perceptual frame rate.

### 2.3 Discrete perception: perceptual moments and rhythmic sampling

The **perceptual moment** idea is old: Stroud (1956) proposed ~100 ms moments. Pöppel (1997, *Trends Cogn Sci*)
proposed a hierarchy: ~30 ms "system states" and a ~2–3 s "subjective present".

Evidence **for** discrete or rhythmic sampling:

- Detection of a near-threshold flash depends on the phase of ongoing ~7–10 Hz oscillations before it (Busch,
  Dubois & VanRullen 2009, *J Neurosci*; Mathewson et al. 2009, *J Neurosci*).
- The individual's alpha frequency predicts the two-flash fusion threshold: faster alpha means finer resolution
  (Samaha & Postle 2015, *Curr Biol*). Changing alpha frequency with tACS shifts the sound-induced flash illusion
  window (Cecere, Rees & Romei 2015, *Curr Biol*).
- Attention samples objects rhythmically: ~4 Hz per object, ~8 Hz in total when attending two (Landau & Fries
  2012, *Curr Biol*; Fiebelkorn, Saalmann & Kastner 2013, *Curr Biol*; Fiebelkorn & Kastner 2019, *Trends Cogn
  Sci*).
- Wutz and Melcher: a temporal window of ~100 ms over which items are individuated and integrated (Wutz & Melcher
  2014, *Front Psychol*). Segregation and integration windows align with opposite phases of theta (3–5 Hz) after
  saccades (Wutz et al. 2016, *Curr Biol*). Alpha frequency shifts with task demand, faster for segregation and
  slower for integration (Wutz, Melcher & Samaha 2018, *PNAS*).
- A "continuous wagon-wheel illusion" at ~10–13 Hz under continuous light (Purves, Paydarfar & Andrews 1996;
  VanRullen, Reddy & Koch 2005).
- Review: VanRullen 2016, "Perceptual cycles", *Trends Cogn Sci*; VanRullen & Koch 2003.

Evidence **against**, or complicating:

- Buergers & Noppeney (2022, *Nat Hum Behav*, N = 20, EEG) found robust evidence that pre-stimulus alpha frequency,
  as a state or as a trait, does **not** predict two-flash discrimination, in vision, audition or audiovisual
  conditions. A later reanalysis with a different measure of the binding window reported a correlation again. The
  question is open.
- Brookshire (2022, *Nat Hum Behav*) showed that the shuffling-in-time statistics used in the behavioural-rhythm
  literature confuse aperiodic, autocorrelated structure with rhythms. Reanalysed with corrected methods, published
  datasets showed **no** evidence for 3–8 Hz rhythmic attentional switching.
- The continuous wagon-wheel effect behaves like perceptual rivalry rather than like a sampling artefact (Kline,
  Holcombe & Eagleman 2004, *Vision Res*).
- Postdiction: what is perceived at time t depends on input for ~80 ms *after* t (flash-lag; Eagleman & Sejnowski
  2000, *Science*). Perception is assembled over a window and then backdated, which neither simple continuous nor
  simple snapshot models capture. Dennett & Kinsbourne (1992) made the same point philosophically.
- A two-stage compromise has traction: quasi-continuous unconscious processing at high temporal resolution, feeding
  discrete conscious percepts that are each assembled over up to ~400 ms (Herzog, Kammer & Scharnowski 2016, *PLoS
  Biol*).

**Bottom line.** There is good evidence that some perceptual and attentional processes are periodically gated at
~4–10 Hz, at least sometimes. There is no evidence for a single global frame rate, and some of the most-cited
behavioural rhythm results have been challenged on statistical grounds.

---

## 3. The resolution ladder: how coarse is perceived time at each scale, and why

The owner's refined framing: humans perceive time only coarsely, much more coarsely than physical time really is, and
that coarseness comes from the physics of the brain. This section addresses that directly. The short answer: the
picture is **right for conscious perception** and **wrong as a description of the brain**. Conscious temporal
resolution is coarse, and coarse in different ways at each scale. Underneath, the brain computes with timing far finer
than anything it lets you perceive as time.

### 3.1 The numbers, from microseconds to days

| Scale | What is resolved | Human threshold | Source |
|---|---|---|---|
| µs | Interaural time difference (sound direction) | ~10–20 µs at best | Klumpp & Eady 1956; Brughera, Dunai & Hartmann 2013. **Not perceived as time at all; perceived as a place.** |
| µs–ms | Auditory phase locking | up to ~1–4 kHz in auditory nerve (cycles of 0.25–1 ms) | |
| ~2–3 ms | Auditory gap detection; two clicks heard as two | ~2–3 ms | Plomp 1964; Green 1985 |
| ~5–10 ms | Tactile gap / two taps felt as two | ~5–10 ms (approx.) | Gescheider et al. |
| ~20–40 ms | Visual two-flash fusion (simultaneity) | ~20–50 ms, depending on luminance and the person; tied to alpha in some studies (contested, §2.3) | Samaha & Postle 2015 |
| ~13–20 ms | Visual flicker fusion (CFF) | ~50–60 Hz in central vision at typical luminance; up to ~90 Hz in the periphery and bright light; edge artefacts visible to ~500 Hz during saccades | Davis, Hsieh & Lee 2015, *Sci Rep* |
| **~20–40 ms** | **Temporal order: which of two came first** | **~20 ms in Hirsh & Sherrick's classic study, similar across hearing, vision and touch; ~30–40 ms in most later work** | Hirsh & Sherrick 1961; Pöppel 1997 |
| ~50–200 ms | Audiovisual simultaneity window | sound can lag light by ~100–200 ms and still feel simultaneous, less tolerance for sound leading; shifts by tens of ms after adaptation to a lag | Vroomen & Keetels 2010; Fujisaki et al. 2004, *Nat Neurosci* |
| ~250 ms | Cross-modal binding of repetitive features | limit ~2–3 Hz across modalities vs ~10–20 Hz within one | Fujisaki & Nishida 2010 |
| ~100 ms | Perceptual moment / integration window | ~100 ms individuation window | Wutz & Melcher 2014 |
| ~150–250 ms | Simple reaction time | ~150–170 ms auditory, ~200–250 ms visual | |
| ~2–3 s | Subjective present (grouping into one "now") | ~2–3 s | Pöppel 1997, contested as a hard limit |
| 0.1 s–minutes | Interval discrimination and production | Weber fraction ~5–10% for trained listeners in the 0.1–1 s range; ~10–20% typical for seconds; ~20–35% in animals. Tapping CV ~3–5% at 0.5 s | Grondin 2010, *Atten Percept Psychophys*; Repp 2005 |
| minutes–hours | Duration judged retrospectively | errors of tens of %, biased by content (busy vs empty); much more variable than prospective | Block & Zakay 1997 meta-analysis |
| hours | "How long have I been awake" in isolation | subjects in temporal isolation produced "1 hour" intervals that lengthened as wake lengthened: they tracked their own subjective day, not physical hours | Aschoff 1985, *Hum Neurobiol* |
| time of day, no cues | circadian phase | the SCN is precise (period 24.18 ± 0.15 h across people, day-to-day jitter small) but phase is not read out as a clock time; ~0.2 h/day drift accumulates without light, and behavioural day length can stretch far further (§6) | Czeisler et al. 1999 |
| days | Date / day count in isolation | Siffre (1962, cave, 58 days) thought 33 days had passed: off by ~25 days | Siffre 1964 |

I could not find a well-powered study of how accurately people estimate *clock time of day* on waking without cues;
anecdotal and small-sample reports suggest errors of an hour or more. Treat any NPC number here as a tunable.

### 3.2 Where the coarseness comes from

The coarseness is not one limit seen at every scale. Each scale has its own origin:

- **Fusion thresholds come from the transducer.** Cone phototransduction runs a G-protein cascade that integrates
  light over ~20–50 ms (rods ~100–200 ms); Bloch's law says that visual detection trades intensity for duration up to
  ~40–100 ms. Hair cells are fast mechanical transducers, so hearing resolves ~2 ms gaps. Touch sits between them.
  So the ~10x difference between vision and hearing in *fusion* is mostly sensor physics, not neuron refractoriness.
- **Order judgments come from central processing.** The ~20–40 ms order threshold is similar across modalities even
  though fusion thresholds differ ~10x (Hirsh & Sherrick 1961; Pöppel 1997). That points to a central stage. The
  likely contributors are membrane and NMDA integration (~10–100 ms), the fact that different stimuli reach cortex
  with different latencies (visual cortex ~50–100 ms, auditory ~15–30 ms) so the brain has to compensate, and
  periodic gating if it exists (§2.3).
- **The ~100 ms window and reaction latency** come from stacked synaptic delays and integration through ~5–10
  processing stages, each adding ~10–20 ms, plus decision accumulation.
- **Interval Weber fractions come from noise in the timing process.** A simple Poisson pacemaker gives an error
  that grows with √t, not with t, so the observed scalar error (∝ t) needs something extra: variability in clock rate
  between trials, multiplicative memory noise, or a scale-invariant representation (Gibbon 1992; Shankar & Howard
  2012). See §4.
- **Coarse minutes and hours** come from the fact that there is no dedicated accumulator at those scales. Duration is
  reconstructed from memory contents, context change and bodily state (§5).
- **Coarse time of day** does *not* come from SCN imprecision. The molecular clock in each SCN cell is noisy: periods
  of isolated cells range ~20–28 h (Welsh et al. 1995, *Neuron*). Coupling among ~20,000 SCN neurons (rodent count)
  makes the ensemble precise to minutes per day. What is coarse is access: the SCN gates physiology (melatonin,
  temperature, alertness) and the conscious mind infers clock time from how those feel plus external cues.

### 3.3 Where "coarse sampling of a finer reality" is right and where it is wrong

Right:

- Conscious perception of time is coarse at every scale, and coarse by orders of magnitude compared with physical
  time. Events less than ~20–40 ms apart cannot be ordered; durations are known only to ~10–20%; time of day and date
  are inferred.
- The coarseness is set by physical rate limits: transduction cascades, membrane and receptor time constants,
  conduction and synaptic delays, metabolic cost.

Wrong, or misleading:

- **It is not sampling at one rate.** There is no frame clock (§2). Each scale has its own resolution and its own
  mechanism.
- **The brain uses much finer time than it perceives.** The auditory brainstem resolves ~10 µs interaural delays,
  about 1/100 of a spike width, using coincidence detectors with fast Kv1 and Kv3 channels and precisely timed
  inhibition (Grothe, Pecka & McAlpine 2010, *Physiol Rev*). Spike timing is reproducible to ~1 ms (Mainen &
  Sejnowski 1995). The cerebellum times motor events in the ~10–100 ms range. None of this is felt as time: it comes
  out as direction, smoothness or rhythm. "Perceiving time" is one output among many timing computations, not a window
  onto them.
- **Perceived time is constructed, not just low-pass filtered.** The brain reorders and backdates: postdiction
  (~80 ms), audiovisual recalibration (tens of ms after exposure to a lag), saccadic chronostasis (the first moment
  after a saccade feels longer; Yarrow et al. 2001, *Nature*), and memory-based distortions of minutes and hours
  (§5). A filter is lossy but honest; perception is lossy and *biased*, and the biases follow what is useful.
- **"The true resolution of time" is not the right reference.** Each resolution is matched to a task: ITD to sound
  localization, order thresholds to multisensory binding, Weber timing to foraging and conditioning, the SCN to the
  solar day. The better framing for design is **task-matched resolution with structured error**, not "a coarse
  sample of reality".
- **The SCN is fine-grained as an oscillator and coarse only as a readout.** It is one of the most precise clocks in
  the body.

---

## 4. Interval timing (hundreds of ms to minutes)

### 4.1 Scalar timing

Timing error grows in proportion to the interval: the coefficient of variation is roughly constant ("scalar
property", Weber's law for time; Gibbon 1977, *Psychol Rev*). Response distributions for different target
intervals superimpose when rescaled by the interval. Weber fractions: §3.1. The property holds roughly from ~0.1 s to
~100 s and breaks down below ~100 ms (where a fixed noise floor dominates) and for long intervals (Grondin 2010;
Lewis & Miall 2009). Estimates regress towards the mean of recently experienced intervals (Vierordt's law).
Jazayeri & Shadlen (2010, *Nat Neurosci*) showed this is close to Bayes-optimal given scalar noise and a prior
learned from the recent distribution.

### 4.2 Pacemaker–accumulator models

Scalar expectancy theory (Gibbon, Church & Meck 1984; Treisman 1963): a pacemaker emits pulses, a switch gated by
attention passes them to an accumulator, and the count is compared with a remembered count. The attentional gate
model (Zakay & Block 1997) adds that attention to time opens the gate wider. It is a good *computational* account
(it explains arousal and attention effects) but no pacemaker of this kind has been found.

### 4.3 Striatal beat frequency

Matell & Meck (2004, *Cogn Brain Res*), building on Miall (1989): many cortical neurons oscillate at different
frequencies (~5–15 Hz). At the start of an interval, dopamine resets them in phase. Striatal medium spiny neurons
learn, via a dopamine signal at reward, the pattern of oscillator phases that occurs at the target time, and fire
as coincidence detectors when it recurs. Scalar variance comes from noise in oscillator frequencies. Supported
broadly by striatal recordings and lesion and Parkinson's data. The specific oscillator mechanism is not
established.

### 4.4 Dopamine and clock speed: contested

- Classic result: dopamine agonists (methamphetamine, cocaine) shift timed responses earlier, as if the clock
  speeds up; antagonists (haloperidol) shift them later (Maricq, Roberts & Church 1981; Meck 1983, 1996; review
  Buhusi & Meck 2005, *Nat Rev Neurosci* "What makes us tick?"). Shifts are of the order of 10–20% (approx.).
- **Contradiction:** Soares, Atallah & Paton (2016, *Science*) optogenetically activated midbrain dopamine neurons
  while mice judged whether a tone interval was shorter or longer than 1.5 s. Activation made mice judge intervals
  as **shorter** (a slower clock), and silencing made them judge intervals as longer. That is the opposite of the
  classic dopamine-clock story. Simen & Matell's accompanying perspective said the dopamine clock hypothesis needs to
  be reassessed. One reconciliation: phasic dopamine signals reward expectation and engagement, which may change how
  time is weighted or attended rather than a pacemaker rate. **For design: dopamine modulates timing, but the sign
  depends on mechanism and is not settled.**

### 4.5 Time cells

Hippocampal and entorhinal neurons fire at successive moments of an empty delay, tiling it (Pastalkova et al. 2008,
*Science*; MacDonald, Lepage, Eden & Eichenbaum 2011, *Neuron*; review Eichenbaum 2014, *Nat Rev Neurosci*). Later
time cells have broader time fields and there are fewer of them, which is a log-compressed, roughly scalar timeline
(Cao et al. 2022, *eLife*). Howard and Shankar's model derives this from a bank of leaky integrators with a spectrum
of time constants plus an approximate inverse Laplace transform (Shankar & Howard 2012, *Neural Comput*; Howard et
al. 2014). Lateral entorhinal cortex carries a slowly drifting population signal that encodes time within an
experience over seconds to hours (Tsao et al. 2018, *Nature*). This is **time read out from drift**, not from ticks.

### 4.6 Population clocks and state-dependent networks

Buonomano and colleagues argue that timing is an intrinsic property of neural dynamics. Any recurrent network
moves along a trajectory after an input, so elapsed time can be read from where the network is (Buonomano &
Merzenich 1995, *Science*; Karmarkar & Buonomano 2007, *Neuron*; Laje & Buonomano 2013, *Nat Neurosci*; Goel &
Buonomano 2014; Paton & Buonomano 2018, *Neuron*). In monkey frontal cortex, producing a longer or shorter interval
corresponds to running the **same** trajectory slower or faster, with speed set by an input (Wang, Narain, Hosseini
& Jazayeri 2018, *Nat Neurosci*; Remington et al. 2018, *Neuron*). Striatal populations also rescale their dynamics
with the interval (Mello, Soares & Paton 2015, *Curr Biol*).

### 4.7 Multiple timing systems

Consensus view: there is no single clock but several systems, each for a range of durations (Buhusi & Meck 2005;
Mauk & Buonomano 2004, *Annu Rev Neurosci*):

- microseconds: brainstem ITD circuits
- ~10 ms to ~1 s: cerebellum (motor and sensory timing; Ivry & Keele 1989; Ivry & Spencer 2004) and cortical
  population dynamics
- ~1 s to minutes: cortico-striatal circuits and dopamine, hippocampal time cells
- minutes to hours: drifting representations (entorhinal), memory-based reconstruction
- ~24 h: SCN

---

## 5. Subjective time distortion

### 5.1 Fear and arousal: memory, not resolution

Stetson, Fiesta & Eagleman (2007, *PLoS ONE*): participants fell 31 m in free fall into a net (~2.5 s) while
reading a wrist "perceptual chronometer" that flashed digits just too fast to read at rest. If fear increased
temporal resolution, they should have read the digits. They did not, so there was **no increase in temporal
resolution**. But retrospectively they estimated their own fall as **36% longer** than others' falls
(2.17 ± 0.24 s to 2.96 ± 0.51 s; only 7 participants gave duration judgments). The authors concluded that "time
slowing" is a feature of recollection: fear lays down a denser memory, and a denser memory reads back as longer.
Caveat: the sample is small and the design tests one form of "slowing".

In ordinary lab tasks, arousing stimuli (angry faces, threat) are judged longer prospectively, which fits an arousal
speeding of the pacemaker in scalar expectancy theory (Droit-Volet & Meck 2007, *Trends Cogn Sci*). Fever and raised
body temperature speed counting rate (Hoagland 1933; meta-analysis Wearden & Penton-Voak 1995).

### 5.2 Oddball effect

A novel item in a repeated sequence seems to last longer: expansions of the order of tens of percent for items
lasting hundreds of ms (Tse, Intriligator, Rivest & Cavanagh 2004, *Percept Psychophys*). Repeated items seem
shorter. Pariyadath & Eagleman (2007) and Eagleman & Pariyadath (2009, *Phil Trans R Soc B*) proposed the
**coding-efficiency** account: perceived duration tracks the size of the neural response, and repetition suppression
shrinks the response to a predictable item. This links directly to §1.3: depleted, adapted synapses give smaller
responses and so less duration. Alternative accounts include attention and prediction error. Not settled.

### 5.3 Prospective vs retrospective judgments

- **Prospective** (you know you will be asked): judgments track attention to time. Attending to time makes it
  longer; a demanding task makes it shorter ("time flies").
- **Retrospective** (asked afterwards): judgments track the amount stored and the number of changes of context
  (Ornstein 1969; Block 1989).
- Meta-analysis: prospective judgments are longer and less variable than retrospective ones, and cognitive load
  affects them in opposite directions (Block & Zakay 1997, *Psychon Bull Rev*; Block, Hancock & Zakay 2010).
- The "holiday paradox": a novel holiday flies by while you are on it but looks long afterwards, and a dull week
  drags but leaves almost nothing in memory.
- **A model that works without a clock:** Roseboom et al. (2019, *Nat Commun*) accumulated salient changes in the
  activations of an image-classification network as it watched videos. The count, mapped to seconds, reproduced
  human duration estimates, including the finding that busy city scenes feel longer than quiet ones. Sherman et al.
  (2022, *PLoS Comput Biol*) found the same accumulation in human visual cortex fMRI predicting trial-by-trial
  estimates. **This is the most directly usable model for an NPC.**

### 5.4 Boredom, flow, age

- **Boredom:** time drags prospectively. Bored people attend to time and report it passing slowly (Wittmann &
  Paulus 2008; Danckert & Allman 2005).
- **Flow:** reported time distortion, usually "time flies". Evidence is mostly self-report; weak.
- **Age:** the folk claim that years speed up with age has thin support. Wittmann & Lehnhoff (2005) and Friedman &
  Janssen (2010) found little age effect on felt speed of days, weeks or months; only the past decade felt faster to
  older people. The "proportion of life" theory (Janet 1877) is not supported. Older adults show more variable and
  sometimes compressed interval production (approx.).
- **Interoception:** the insula has been proposed as accumulating body-state signals as a basis for felt duration
  (Craig 2009; Wittmann 2013, *Nat Rev Neurosci*). Plausible; not established.

---

## 6. Circadian, homeostatic and ultradian clocks

### 6.1 The SCN

- Location and size: the suprachiasmatic nucleus of the hypothalamus, ~20,000 neurons in rodents (both sides).
- Mechanism: a transcription–translation feedback loop. CLOCK/BMAL1 drive *Per* and *Cry*; PER/CRY proteins come
  back to repress CLOCK/BMAL1; delays of hours in transcription, translation, modification and nuclear entry set a
  ~24 h period (Takahashi 2017, *Nat Rev Genet*). Isolated cells are sloppy (~20–28 h; Welsh et al. 1995); coupling
  through VIP and other signals makes the network precise.
- **Free-running human period: 24.18 h** (SD ~0.13–0.15 h), the same in young and old (Czeisler et al. 1999,
  *Science*). Older bunker estimates of ~25 h (Aschoff, Wever) were inflated by self-selected room light.
- Without light, a 24.18 h period drifts ~11 min per day, ~1.3 h per week.

### 6.2 Entrainment by zeitgebers

- **Light** is the dominant zeitgeber. It reaches the SCN through intrinsically photosensitive retinal ganglion cells
  (ipRGCs; ~1–2% of RGCs) containing melanopsin, peak sensitivity ~480 nm (blue), via the retinohypothalamic tract
  with glutamate and PACAP (Berson, Dunn & Takao 2002, *Science*; Hattar et al. 2002, *Science*). Rods and cones also
  contribute.
- **Dose:** half-maximal phase shifting and melatonin suppression at ~100 lux, which is ordinary room light;
  saturation by a few thousand lux (Zeitzer et al. 2000, *J Physiol*). Daylight is 10,000–100,000 lux.
- **Phase response curve:** light in the early biological night delays the clock, in the late night advances it,
  little effect in the middle of the day. Maximum ~2–3 h per day from a strong stimulus, with crossover near the core
  body temperature minimum (~2 h before habitual waking) (Khalsa et al. 2003, *J Physiol*).
- **Range of entrainment:** humans entrain to roughly 23.5–24.6 h days (approx.). Outside that, the clock runs free:
  Kleitman's 28 h days in Mammoth Cave (1938) and the forced-desynchrony protocol both rest on this.
- **Jet lag:** re-entrainment ~1 day per time zone, slower going east (Waterhouse et al. 2007, *Lancet*).
- **Other zeitgebers:** meals, exercise, social schedule and temperature are weaker for the SCN but strong for
  peripheral clocks.

### 6.3 Peripheral clocks

Almost every cell has the same molecular clock (Balsalobre, Damiola & Schibler 1998, *Cell*). The SCN synchronizes
them through hormones, temperature, autonomic signals and feeding time. Restricting feeding to the wrong time of
day shifts the liver clock within days while the SCN stays put (Damiola et al. 2000, *Genes Dev*; Stokkan et al.
2001, *Science*). The result is internal misalignment, as in shift work.

### 6.4 Process S: homeostatic sleep pressure

The two-process model (Borbély 1982; Daan, Beersma & Borbély 1984; reappraisal Borbély et al. 2016, *J Sleep Res*):
sleep timing comes from a homeostatic pressure S interacting with circadian C.

- S rises during waking with time constant **~18.2 h** and falls during sleep with **~4.2 h**, both fit to slow-wave
  activity in sleep-deprivation experiments.
- Adenosine accumulates in the basal forebrain during prolonged waking (Porkka-Heiskanen et al. 1997, *Science*) and
  is one substrate of S. Caffeine blocks A1 and A2A receptors; its half-life is ~5 h (range ~2–10 h between people).
- Circadian C opposes S during the day. Alertness is highest in the "wake maintenance zone" a few hours before
  habitual sleep, and lowest near the temperature minimum around 04:00–06:00 (Dijk & Czeisler 1994).
- **Chronic restriction:** 6 h per night for 14 days impaired attention as much as 1–2 nights without sleep, while
  subjects rated their sleepiness as only slightly higher (Van Dongen et al. 2003, *Sleep*). People do not perceive
  their own deficit.

### 6.5 Ultradian and infradian rhythms

- NREM–REM cycle ~90 min in adults (~50–60 min in infants).
- Kleitman's "basic rest-activity cycle" of ~90 min continuing through waking: **weak and inconsistent evidence**.
- Pulsatile hormones: cortisol and GnRH pulses roughly every 60–90 min. Stress cortisol peaks ~20–40 min after a
  stressor begins and recovers ~40–60 min after it ends (Dickerson & Kemeny 2004, *Psychol Bull*).
- Infradian: the menstrual cycle (~28 d); seasonal, photoperiod-driven rhythms (melatonin duration tracks night
  length).

### 6.6 No zeitgebers

- The clock free-runs at its intrinsic period (§6.1).
- **Internal desynchronization:** in long isolation, the sleep–wake cycle can drift away from the temperature rhythm
  and lengthen to 30–50 h, while the temperature rhythm stays near 25 h (Wever 1979; Aschoff's Andechs bunker
  studies). Subjects did not notice: a 40 h "day" felt like a day.
- **Day count follows sleeps, not days.** Siffre (1962), 58 days in the Scarasson cave, believed it was 20 August
  when it was 14 September: ~25 days lost. In later experiments his sleep–wake cycles stretched to ~48 h.
- In the same isolation, judgments of seconds stay roughly accurate, while estimates of hours scale with the
  subjective day (Aschoff 1985). The scales really are separate systems.

---

## 7. How the brain gets universal time at all

The brain never reads physical time. It infers it by combining:

1. **External periodic cues.** Light (the strongest), meals, social schedules, temperature, clocks and calendars,
   other people's behaviour. Entrainment is literally phase-locking an internal oscillator to an external one.
2. **Internal oscillators** that run near the right period between cues: the SCN for the day, the menstrual cycle,
   ultradian pulses.
3. **Integrators that build up and decay:** sleep pressure (hours awake), hunger and satiety, fatigue, decay of
   neuromodulators and hormones. Their level reports elapsed time crudely.
4. **Drifting representations** (lateral entorhinal, hippocampal drift) and **memory density** (how much happened)
   for minutes to days.
5. **Counting salient episodes**: sleeps, meals, events. Day count is a count of sleeps.
6. **Short-interval timing systems** (§4) for seconds.

Every one of these is a physical process inside the body running in physical time. None of them reports physical
time directly. Accuracy depends on cue availability: with cues, time of day is known to minutes; without cues, it
drifts by hours and the day count can be off by weeks.

---

## 8. What this means for a simulated agent

### 8.1 Marr's levels: what matters for a cognitive architecture

**Computational and algorithmic level, which an NPC should have:**

1. **All internal processes run in world time, each with its own time constant.** There is no global brain tick.
   Each subsystem is a dynamical system integrated by `World.advance`. This is both bio-faithful and the only design
   compatible with the speed dial: if every internal update is a function of world-time Δt and not of wall time or
   step count, pause, slow-mo and 20x are just different Δt sequences.
2. **Resources that deplete and recover** (a Tsodyks–Markram-style variable): gain control, habituation, novelty
   detection, fatigue.
3. **Scalar-noise interval estimates** that can be biased by arousal, attention and prior experience (Vierordt).
4. **Retrospective duration from memory density**, separate from prospective timing.
5. **A circadian oscillator entrained by world light**, plus **homeostatic sleep pressure** and slow hormonal state.
6. **Inferred, fallible time-of-day and date beliefs.**
7. **Finite perceptual temporal resolution and latency**: order thresholds, integration windows, reaction times.

**Implementation detail, which an NPC should not simulate:** individual spikes, refractory periods, SNARE assembly,
receptor subunits, gamma cycles, vesicle pools as such. Their consequences matter; the mechanisms do not, at the
timescale of a game turn. The exception is where the substrate loop really is spiking or rate-based: then the
time constants in §1 are the right defaults for its synapses.

### 8.2 Engineering consequence: Δt invariance

The resolution rule has a direct analogue here. **The outcome class of NPC cognition must not depend on how world time
was chopped into steps.** 20x fast-forward may mean coarser world steps. If adaptation, sleep pressure or interval
timers are updated with forward-Euler on a step count, they will behave differently at 20x than at 1x. Use
closed-form exponential updates (`x ← x_∞ + (x − x_∞)·exp(−Δt/τ)`) and analytic phase advance for oscillators. Test a
cross-step invariance the way `tests/test_cross_tier.py` tests rigs.

A second consequence: **LLM deliberation takes wall time, but the bio-faithful cost is world time.** Thinking should
cost the NPC a world-time budget (seconds for a considered decision, ~0.2–0.5 s for a choice reaction), bound to the
world clock so replays stay deterministic. How long the LLM actually took in wall time must not leak into the outcome.
This is an architecture question for the design, flagged here, not answered.

### 8.3 Candidate mechanisms

| # | Mechanism | Biological basis | Timescale (world time) | Game behaviour |
|---|---|---|---|---|
| 1 | **Perceptual latency and integration window** | transduction, synaptic stacks, ~100 ms windows (§3) | ~100 ms window; reaction 150–250 ms simple, 300–600 ms choice | NPCs cannot react to events instantly; in slow-mo the player sees an NPC's reaction lag. Fast-burst attacks fall inside one window and are perceived as one event |
| 2 | **Order threshold** | ~20–40 ms central order threshold | events closer than ~30 ms are simultaneous to the NPC | an NPC cannot say which of two near-simultaneous shots came first; witnesses disagree |
| 3 | **Depleting salience per channel** (Tsodyks–Markram) | STD, adaptation, repetition suppression (§1.3, §5.2) | τ_rec ~0.5–10 s for sensory; minutes–hours for habituation | a car alarm stops being noticed; a new sound grabs attention; a repeated threat loses its startle; changes noticed more than levels |
| 4 | **Interval timer with scalar noise** | SET / population clocks (§4) | 0.1 s–minutes, CV ~0.1–0.2 | guards' patrol timing jitters in proportion to length; "I'll be back in five minutes" means 4–6 min |
| 5 | **Arousal modulation of the interval timer** | arousal and fear lengthening judged time; dopamine effect contested (§4.4, §5.1) | seconds–minutes | an anxious NPC waiting for a contact gets impatient early; a bored one checks the time more often. **The sign of a dopamine effect should be a tunable, not a claimed fact** |
| 6 | **Retrospective duration from event count** | Roseboom 2019; Ornstein; Stetson 2007 | minutes–days | "How long was I locked in there?" is underestimated if nothing happened; a fight is remembered as longer than it was (~+36%); interrogating witnesses gives distorted durations |
| 7 | **SCN phase oscillator entrained by world light** | §6.1–6.2 | period ~24.2 h; PRC ±2–3 h/day; ~100 lux half-max | NPCs in windowless arcologies drift ~11 min/day; night-shift workers have shifted phase; NPCs who travel get jet-lagged |
| 8 | **Process S sleep pressure plus caffeine** | two-process model; adenosine (§6.4) | rise τ ~18.2 h, decay ~4.2 h; caffeine half-life ~5 h | sleep-deprived NPCs lapse and misjudge, and do not know it (Van Dongen); stimulant use with crashes; alertness dip before dawn |
| 9 | **Peripheral meal clock** | liver clock shifts in days (§6.3) | days | NPCs on irregular meal schedules are internally misaligned: hungry and drowsy at the wrong times |
| 10 | **Stress-hormone half-life** | cortisol peak 20–40 min, recovery 40–60 min after (§6.5) | tens of minutes | fear lingers after the threat is gone; an NPC stays jumpy for an hour after a shootout |
| 11 | **Fallible time-of-day and date belief** | §6.6, §7 | hours–weeks | an NPC held captive loses track of days; their date belief is updated by sleeps, clocks, news; it can be wrong, and their dialogue can show it |
| 12 | **Deliberation costs world time** | decision accumulation, ~0.3 s to seconds | 0.3 s–seconds | a considered NPC answer takes time in the world; it can be interrupted |

Weak evidence; not recommended as mechanics: a waking 90 min "BRAC"; a literal perceptual frame rate (alpha
sampling); age-related acceleration of felt time.

### 8.4 What resolution of time an NPC should perceive at each scale

| Scale | Physical reality | NPC should perceive |
|---|---|---|
| <10 ms | the world resolves it | nothing as time. The world converts sub-ms physics (e.g. sound direction) into a feature, not a timestamp |
| ~10–40 ms | | events within ~30 ms are simultaneous; order unknown |
| ~40–100 ms | | one perceptual moment; flashes and sounds within ~100 ms bind as one event; sound may lag light by ~100 ms and still be "together" |
| 0.1–3 s | | a "now"; reaction latencies 150–600 ms |
| seconds–minutes | exact | prospective estimates with ~10–20% scalar noise, biased by arousal, attention and recent intervals |
| minutes–hours | exact | retrospective estimates from event density: errors of tens of % and biased by content; awake-hours known roughly from sleep pressure |
| time of day | exact | with light or clocks: minutes. Without: SCN phase drifts ~11 min/day, readout uncertain to an hour or more (tunable; weak evidence) |
| days | exact | a count of sleeps; in isolation can be off by days to weeks |

The NPC should never receive the world clock as such. It perceives world events; the world can show it a clock,
sunlight or a newsfeed as percepts, and it infers time from those, as people do.

### 8.5 Where the evidence is contested, in summary

- Whether perception is discretely sampled at alpha or theta rates (§2.3): contested, with null and statistical
  critiques since 2022.
- Dopamine's direction of effect on clock speed (§4.4): contradictory results.
- Whether pacemaker–accumulator, beat-frequency or population-clock models are right (§4): each fits some data; the
  field leans towards multiple distributed mechanisms.
- Mechanism of the oddball effect (§5.2): coding efficiency vs attention vs prediction error.
- Fear "slowing time" (§5.1): one small study (7 duration judgments) underlies the memory account, though it agrees
  with the broader retrospective-timing literature.
- Synaptic numbers (§1) vary several-fold between synapses, ages and temperatures. Use them as order-of-magnitude
  defaults.
