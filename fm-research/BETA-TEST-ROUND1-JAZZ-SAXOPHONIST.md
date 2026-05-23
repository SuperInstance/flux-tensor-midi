# BETA TEST — ROUND 1: Jazz Saxophonist Report

**Tester:** Professional jazz saxophonist, 15 years gigging, teaches at conservatory  
**Date:** 2026-05-23  
**Packages tested:** flux-tensor-midi 0.1.2, counterpoint-engine 0.1.0, constraint-theory-core 0.1.0  
**Environment:** Python 3.10, Linux (WSL2)

---

## Setup

Cloned all three repos. `pip install -e .` worked cleanly for all three — zero dependency conflicts, which is refreshing. The zero-dependency claim is real. That matters more than people think.

Total setup time from clone to first code running: ~2 minutes. That's good.

---

## TASK A: Jazz Solo over Dm7→G7→Cmaj7 via GenreBrain

**Did it work on first try?** No.

**Steps to success:**
1. `GenreBrain('jazz')` — OK, that's clean.
2. `brain.create_band(bpm=160, bars=8)` — returns a `(band, musicians)` tuple. Undocumented return type. I had to print it to figure out it was a tuple.
3. `band.members` — it's a `dict`, not a list. The README says `band.add_musician(bass)` and iterates members like they're objects, but `members` is `{id: RoomMusician}`. Had to discover this experimentally.
4. **Critical failure:** GenreBrain creates an *ensemble architecture* (who plays what role, what clock, what salience) but **does not generate actual notes over a chord progression**. There's nowhere to pass `Dm7→G7→Cmaj7`. The genre brain sets up *vibes* (salience profiles, tolerances, rhythmic roles) but doesn't compose.

**What I got:** 12 ticks of FluxVector states (arousal, valence, dominance values) and timestamps. No pitches. No MIDI notes. The "harmony" came back as "diminished" with consonance 0.273 — which is the system measuring its own internal vector similarity, not actual harmonic content.

**What was confusing:**
- The README uses `GenreBrain` in the context of "load a genre and the whole system adapts" — but adapts *to what*? There's no input.
- The "jazz" preset defaults to Bb, 180 BPM, 12-bar loop. That's... bebop, fine. But the 12-bar "loop" doesn't actually loop a blues form. It's just `loop_bars: 12` as a config number.
- `band.tick_all()` returns `{'name': (timestamp, FluxVector)}` — the timestamp is just accumulating linearly, the FluxVector values are static (the piano always has arousal=0.90). Nothing is actually *evolving*.

**What was delightful:**
- The *concept* of genre as a set of salience profiles and tolerance matrices is genuinely interesting. The idea that piano has "rubato tolerance" while bass is "tight" — that's real ensemble knowledge encoded in data.
- The naming: "RoomMusician," "conductor," "everyone_listens_to_everyone" — the vocabulary is musical, not just CS jargon.

**What would I change:**
- GenreBrain needs a `generate_solo(chords, bars, instrument)` method or it's just a config object pretending to be useful.
- The API needs to decide: is `create_band()` returning a tuple or just a band? Pick one.
- Members should be a list, not a dict keyed by UUIDs. Musicians have names, not hash IDs.

---

## TASK B: 4-Voice Counterpoint in the Style of Bach

**Did it work on first try?** No.

**Steps to success:**
1. Tried `CounterpointGenerator(species=Species.FIRST, n_voices=4, ...)` — wrong. `__init__` requires `cantus_firmus` as first positional arg. The README/example discrepancy.
2. Tried `Scale.MAJOR` — nope, `Scale` doesn't have `MAJOR`. It's a class with `tonic` and `mode`, not an enum. Had to dig into the source.
3. Called `gen.generate()` with just a cantus firmus — it worked! But only produced **2 voices** (the cantus firmus + one counterpoint). There's no parameter for `n_voices=4`. The system is first-species counterpoint, one voice against one cantus firmus.

**What I got:** Two voices. The cantus firmus `[60, 62, 64, 65, 67, 69, 67, 65, 64, 62, 60]` and a counterpoint line `[48, 53, 52, 50, 48, 48, 48, 50, 48, 50, 52]`. That's... fine? It follows the rules. But it's not 4-voice Bach chorale style.

**Laman graph:** `henneberg_construct(4)` gave me a graph with 5 edges, and the `CounterpointGraph` wrapper says it's rigid. Cool math. Unclear how this connects to actual counterpoint generation — the generator doesn't seem to use it internally for multi-voice coordination.

**What was confusing:**
- The module *says* "species counterpoint as constraint satisfaction = Laman rigidity" but the generator doesn't appear to use the Laman graph for anything during generation. It's there in the namespace but disconnected.
- No way to request 4 voices. The description says "4-voice counterpoint" but the tool only does 1v1.

**What was delightful:**
- The constraint SAT/UNSAT model is clean. Each rule returning SAT or UNSAT is exactly how I teach it. "Is this interval consonant? SAT. Are there parallel fifths? UNSAT." That's the right abstraction.
- `henneberg_construct` actually building a rigid graph is mathematically legit. The connection between rigid frameworks and contrapuntal constraints is real and underexplored.

**What would I change:**
- Add multi-voice support or at minimum document "currently supports 2-voice species counterpoint."
- The `Scale` API needs an enum or named presets (`Scale.major('C')` or just `Scale.MAJOR_C`).
- Connect the Laman machinery to the actual generation. Right now they're ships passing in the night.

---

## TASK C: Drum Rack — Swing Feel at 160 BPM

**Did it work on first try?** Partially.

**What happened:** `DrumRack()` is a name→MIDI-note mapping on channel 10. It maps `'kick'` → 36, `'snare'` → 38, `'ride'` → 51, `'hihat_closed'` → 42, etc. That's it. 39 instruments.

**What I needed:** A swing pattern generator. Something that gives me the ride cymbal pattern with triplet swing, kicks on 1 and 3, snare on the "and" of 2 and 4 (or ghost notes), hi-hat pedal on all four beats with a swing offset. At 160 BPM.

**What I got:** A dictionary. `{'kick': 36, 'snare': 38, ...}`.

**Also:** `hihat` → KeyError. It's `hihat_closed`, `hihat_open`, or `hihat_pedal`. Not discoverable without triggering the error and reading the message.

**What was delightful:**
- 39 instruments is comprehensive. It covers GM percussion plus some extras.
- The error message for unknown instruments *lists all 39 known instruments*. That's good UX in an API.

**What would I change:**
- This isn't a drum machine. It's a drum *map*. Rename it or add pattern generation.
- Add aliases: `'hh'` → `'hihat_closed'`, `'hat'` → `'hihat_closed'`, etc. Drummers don't type `hihat_closed`.
- A `DrumRack.swing_pattern(bpm=160, feel='ride_cymbal')` would make this actually useful.

---

## TASK D: AI Jam — parker_miles Preset, 32 Bars

**Did it work on first try?** No.

**Steps to success:**
1. `JamSession(preset='parker_miles')` — nope, doesn't take a `preset` kwarg.
2. `get_preset('parker_miles')` returns a dict with `agent1`, `agent2` as `AgentPersonality` objects, plus `bpm` and `progression`. Nice.
3. Had to manually unpack: `AIAgent(preset['agent1'])`, `AIAgent(preset['agent2'])`, then `JamSession(agent1=..., agent2=..., bpm=..., progression=...)`.
4. `session.run()` — **this worked beautifully.** 296 MIDI events, 47 seconds of music.

**What I got:**
- **Parker (sax):** 236 events, notes 60-95 (C4-B6), average velocity ~94. Dense, bebop-range playing.
- **Miles (trumpet):** 60 events, notes 64-83 (E4-B5), sparser, more spacious.
- The ratio feels right — Parker plays 4x more than Miles. That's... actually kind of perfect for a bebop jam.
- First event at 5.9ms, last at 47,760ms. The timing feels natural, not quantized.

**What was confusing:**
- The preset system is disconnected from the session system. `get_preset()` returns a dict but `JamSession()` doesn't accept a preset. You have to manually wire them.
- The progression `Dm7(4) → Gm7(4) → Am7(4) → Dm7(4)` is D Dorian minor, which is fine, but it's not really a "Parker + Miles" jam. Parker played rhythm changes and blues. Miles played modal (So What is D Dorian, actually — so this checks out for Miles at least).

**What was delightful:**
- The personality encoding is *fascinating*. Parker has `note_density=4.0`, `rest_probability=0.05`, `direction_change_prob=0.55`. Miles has `note_density=1.2`, `rest_probability=0.35`, `sustain_factor=0.85`. You can *feel* the musical personality in these numbers. That's genuine insight.
- The event timing feels human — not quantized, not random.
- The note ranges make musical sense. Parker goes higher and wider. Miles stays in the mid-range with more space.

**What would I change:**
- `JamSession.from_preset('parker_miles', bars=32)` — one-liner. Come on.
- Export to actual MIDI file. I have 296 `MidiEvent` objects in memory with no clear path to a `.mid` file.
- Parker's going up to B6 — that's above the saxophone range. Tenor tops at F#5, alto at A5. B6 is flute/soprano sax territory. Range constraints per instrument would help.

---

## TASK E: Analyzer on Generated MIDI

**Did it work on first try?** No.

**Steps:**
1. `FluxAnalyzer()` — OK.
2. Tried `analyzer.analyze(events)` — no `analyze` method. It's `from_midi_events()`.
3. That worked. Got an `AnalysisReport` with real data.

**What I got:**
- Key detection: A minor, confidence 0.538. (The jam was over Dm7→Gm7→Am7→Dm7, so A minor is a reasonable interpretation — it's the relative major's relative minor, or just the III chord's key center.)
- **Terrain: "bebop"** with 0.7 confidence. The analyzer correctly identified the style! That's genuinely impressive.
- Density: 5.99 events per second. Velocity mean: 94, std: 19.5. Pitch range: C4-B6. Mean interval: 4.8 semitones. Interval entropy: 3.08.
- Flux: 1.06 — whatever that means exactly, it's there.

**What was confusing:**
- `from_midi_events` is a weird name for the main analysis method. `analyze()` would be obvious.
- What is "flux"? What is "terrain"? These terms aren't defined in the analyzer output. I can guess, but I shouldn't have to.

**What was delightful:**
- The terrain classification returned "bebop" on a Parker/Miles jam. **That's the correct answer.** If this is actually doing spectral/profile matching rather than just keyword matching, it's genuinely useful.
- Interval entropy as a metric is smart. High entropy = unpredictable intervals = more interesting melodic content.

**What would I change:**
- Rename `from_midi_events` → `analyze`.
- Add human-readable descriptions to the report. "Terrain: bebop" should come with "Characterized by high note density, wide interval leaps, and chromaticism."
- Add a `to_text()` or `summary()` method.

---

## TASK F: Exercise Generator — Would I Use It With Students?

**Did it work on first try?** Yes! This is the most polished piece.

**What I got:**
- 4 topics: species_counterpoint, voice_leading, harmonic_constraints, rhythmic_constraints
- 3 levels: beginner, intermediate, advanced
- All 12 combinations work and produce structured exercises.
- Each exercise has: instructions, constraints, starting notes, solution, scoring rubric (summing to 100).
- Seed reproducibility ✓

**Sample exercise (species_counterpoint/intermediate):**
> "Compose a fourth-species counterpoint (suspension chain) above the cantus firmus. Each suspension must resolve down by step. Verify the resolution interval snaps cleanly on the A₂ lattice."

**Would I use it with students?**

Yes, with caveats:
1. The instructions are well-written and musically accurate. A second-year theory student could follow them.
2. The scoring rubric is useful — it gives students a clear breakdown of what matters.
3. **The A₂ lattice stuff is too academic for most students.** "Verify the resolution interval snaps cleanly on the A₂ lattice" — my students would have no idea what that means. This needs a "musician mode" that says "ensure all suspensions resolve to consonant intervals."
4. I'd want to customize: my own cantus firmi, my own difficulty gradations, integration with notation software.
5. The solutions are just dicts of pitch lists. No notation output, no MIDI, no visual. For teaching, I need to *show* students the result, not hand them JSON.

**What would my students think?**
- The motivated ones would be intrigued. "The computer is checking my voice leading? Cool."
- The less motivated ones would be confused by the terminology. "What's a Laman graph?"
- None of them could use this without a front-end. The CLI/API is for developers, not 19-year-old music students.

**What would Coltrane think?**
He'd want to know about the interval entropy. He'd play the exercise, then immediately break every rule in the most beautiful way possible, and ask if the system could analyze *why* his rule-breaking sounded good. It couldn't. That's the next frontier.

---

## IDEATION SESSION: Unfiltered Feedback

### What does this ecosystem WANT to be?

It wants to be the mathematical backbone of a new kind of music software. Not a DAW, not a notation program, but something underneath — the "music theory engine" that other tools call into. The way that physics engines (Havok, PhysX) sit under game engines, this wants to be the "music theory engine" that sits under composition tools, teaching platforms, and generative music systems.

The three repos form a coherent stack: `constraint-theory-core` provides the mathematical primitives (lattice snapping, Laman rigidity, safety checks), `counterpoint-engine` uses those to solve actual music theory problems, and `flux-tensor-midi` provides the real-time performance layer with ensemble coordination and timing.

That's a legitimate vision. The question is whether the vision outpaces the execution by too wide a margin.

### What's the killer feature?

**The AI Jam system.** Specifically, the `AgentPersonality` encoding. Being able to define a musician's style as a set of parameters (density, velocity range, rest probability, direction change, snap epsilon) and then have them interact in real-time — that's genuinely new. Not "AI generates music" but "AI agents with defined personalities jam together." The Parker/Miles session producing 296 events where Parker plays 4x more than Miles, with appropriate ranges and timing — that's not random generation, that's *characterization*.

The terrain detection ("bebop" with 0.7 confidence) is the second killer feature. If that's robust, it means the system can listen to music and understand what it's hearing in genre terms.

### What's missing that would make me pay money?

1. **MIDI file output.** I can generate 296 events but can't save them as a `.mid` file. This is table stakes. Without it, the AI jam is a demo, not a tool.

2. **Notation output.** For the exercise generator especially — I need MusicXML or LilyPond output so students can see the exercises in proper notation. JSON pitch lists are useless in a classroom.

3. **Chord progression input.** The genre brain and AI jam should accept a chord progression and generate music *over it*. Right now the jam has a hardcoded progression and the genre brain has none. Let me pass `[('Dm7', 4), ('G7', 4), ('Cmaj7', 4)]` and get a solo.

4. **Instrument range validation.** Parker going to B6 (above sax range) shows the system doesn't know what instruments can actually play. A simple range constraint per instrument would fix this.

5. **A front-end.** Any front-end. A web UI, a Jupyter widget, a DAW plugin, a command-line tool with `--output midifile.mid`. The API is only useful if I can get results out of it.

### What would my students think?

They'd be impressed by the concepts and frustrated by the UX. The exercise generator is the most accessible piece, but even that requires Python knowledge to use. For a conservatory setting, I need something where a student opens a browser, selects "species counterpoint / intermediate," and gets a formatted exercise with notation.

The mathematical framework (Eisenstein lattice, Laman rigidity, constraint satisfaction) is intellectually exciting but practically opaque. Students don't think in "A₂ lattice snap safety." They think in "does this suspension resolve correctly?" The system needs a translation layer between its mathematical truth and musical language.

### What would Coltrane think?

He'd spend 10 minutes with the interval entropy metric, play something that maximizes entropy while remaining beautiful, then ask why the system can't distinguish between "random high entropy" and "meaningful high entropy." He'd be right. Entropy alone doesn't capture musical intelligence — it captures unpredictability. Giant Steps is unpredictable *and* meaningful. Random chromatic wandering is unpredictable *and* meaningless. The system can't tell the difference yet.

He'd also appreciate the Eisenstein lattice as a rhythmic concept. Coltrane's playing had a deeply mathematical underpinning that he might not have articulated in these terms, but the idea of rhythmic quantization via hexagonal tiling would resonate (pun intended) with his approach to time.

### Three features that don't exist yet but should

**1. "Play Along" Mode — Real-time AI Accompaniment**
The `RoomMusician` / `Band` architecture is begging for real-time input. Let me plug in my sax via MIDI, and have the system's AI agents react to what I play in real-time. The FluxVector system already has the vocabulary (arousal, valence, dominance) — if I play something with high arousal (loud, high register), the drums should respond. If I play something with low valence (minor, tension), the piano should adjust. The side-channel concept (nod, smile, frown) is literally designed for this. Make it work with a real MIDI input.

**2. "Style Transfer" — Play Bebop in the Style of Bach**
The terrain detection identifies style. The AI agents generate in style. The counterpoint engine enforces rules. Combine them: play me a bebop solo but with species counterpoint constraints. Or generate Bach chorale harmonizations but with jazz voicings. The mathematical framework (constraint satisfaction) is exactly right for this — you just need to swap constraint sets mid-generation.

**3. "Lesson Plan Generator" — Full Teaching Curriculum**
The exercise generator is a seed. But what I need as a teacher is a *sequence*: Week 1, species counterpoint beginner. Week 2, voice leading. Week 3, combine them. Each exercise builds on the last. The system should track student progress (which constraints they violate most) and adapt subsequent exercises. The `constraint-theory-core` already has the constraint vocabulary — extend it to a curriculum engine with student modeling.

---

## Summary Scorecard

| Component | Works? | UX (1-5) | Musicality (1-5) | Potential (1-5) |
|-----------|--------|----------|-------------------|-----------------|
| GenreBrain | Partial | 2 | 2 | 4 |
| Counterpoint Engine | Yes (2-voice) | 2 | 4 | 5 |
| Drum Rack | Yes (map only) | 3 | 1 | 2 |
| AI Jam | Yes | 3 | 4 | 5 |
| Analyzer | Yes | 3 | 4 | 4 |
| Exercise Generator | Yes | 4 | 3 | 5 |
| Constraint Theory Core | Yes | 3 | N/A | 5 |

**Overall impression:** This is a research project with a product-shaped hole. The math is sound, the musical concepts are genuinely insightful (I mean that — the salience/tolerance model of ensemble dynamics is better than anything I've seen in academic music computing), but the "last mile" to usable output is missing across the board. No MIDI files, no notation, no real-time input, no front-end.

The vision is clear: a mathematical foundation for computational music theory that treats music the way physics engines treat collisions — as constraint satisfaction over structured representations. That's valuable. The execution is about 40% of the way there. The most complete piece (exercise generator) proves the concept works. The most exciting piece (AI jam) proves the potential is real.

Ship MIDI file output and a one-line `JamSession.from_preset('parker_miles').export('jam.mid')` and you've got something musicians would actually use. Everything else is polish on a solid foundation.

---

*"The code doesn't have feelings."* — True. But it has potential. And right now, potential is all it has. Time to ship the last mile.
