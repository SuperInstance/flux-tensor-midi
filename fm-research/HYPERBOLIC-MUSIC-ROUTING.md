# Hyperbolic Music Routing

*Mapping constraint profiles into the Poincaré ball for infinite genre blending in the AI-Jam system.*

---

## The Problem

The AI-Jam system (`flux-tensor-midi/ai_jam`) currently ships with **5 hardcoded presets** (Parker/Miles, Bach/Vivaldi, Coltrane/Monk, Weather Report, Noise/Drone). Each preset pairs two agents with hand-tuned `AgentPersonality` profiles. Want a new blend? Write it by hand.

**What we want:** infinite, smooth genre blending in continuous hyperbolic space.

## Why Hyperbolic?

Musical genres form a **tree-like hierarchy** — jazz branches into bebop, cool, fusion, free. Blues is close to jazz (shared harmony, blue notes) but far from baroque. Hyperbolic space (negative curvature) is the natural geometry for tree-structured data:

- **Distances grow exponentially** near the boundary → fine-grained distinctions between closely related subgenres
- **The origin is general** → generalist agents live near the center
- **The boundary is specialist** → niche styles live near the edge
- **Curvature controls genre strictness** → a single parameter tunes how rigid the genre boundaries are

## Architecture

### Embedding Constraint Profiles as Points

Each `AgentPersonality` has ~12 parameters (preferred_intervals, note_density, velocity_range, rest_probability, snap_epsilon, direction_change_prob, sustain_factor, octave_range, consensus_weight). We embed these as a point in the Poincaré ball:

```
embed_genre(personality) → np.ndarray (8D Poincaré ball point)
```

The 8 embedding dimensions capture:

| Dim | Musical axis | Source fields |
|-----|-------------|---------------|
| 0 | **Chromatic density** | len(preferred_intervals) / 11 |
| 1 | **Rhythmic intensity** | note_density / max_density |
| 2 | **Dynamic range** | (vel_max - vel_min) / 127 |
| 3 | **Spaciousness** | rest_probability |
| 4 | **Timing tightness** | snap_epsilon |
| 5 | **Angularity** | direction_change_prob |
| 6 | **Sustain** | sustain_factor |
| 7 | **Consensus** | consensus_weight |

The **norm** of the point encodes specialization:
- `||v|| < 0.2` → generalist (plays in many contexts)
- `0.2 ≤ ||v|| < 0.7` → moderate specialist
- `||v|| ≥ 0.7` → extreme specialist (niche genre)

### Genre Space Topology

Nearby genres in hyperbolic space reflect harmonic/rhythmic similarity:

```
                    ┌── bebop (Parker) ──── sheets-of-sound (Coltrane)
         ┌── jazz ──┤
         │          ├── cool (Miles)
         │          └── fusion (Zawinul, Shorter)
         │
origin ──┤                    ┌── angular (Monk)
         │          └── blues ──┘
         │
         └── classical ───┬── baroque-counterpoint (Bach)
                          └── baroque-melody (Vivaldi)

         (far boundary) ─── noise, drone, experimental
```

Hyperbolic distance captures this:
- `dist(Parker, Miles) ≈ 1.2` — both jazz, different subgenres
- `dist(Parker, Bach) ≈ 3.5` — cross-genre, interesting tension
- `dist(Noise, Drone) ≈ 4.0` — both experimental, but extreme contrast

### Frechet Mean = Genre Blending

The **Frechet mean** in hyperbolic space is the natural way to blend genres. Given agents A, B with weights w_A, w_B:

```
blend = FrechetMean.compute([A.coords, B.coords], weights=[w_A, w_B])
```

This produces a **new point** in the Poincaré ball whose musical properties interpolate smoothly between the inputs. The result is a constraint profile that can be fed directly into `AgentPersonality` → `AIAgent`.

Key insight: the Frechet mean in hyperbolic space is **not** linear interpolation. It respects the curvature — blending two distant genres (e.g., jazz × baroque) produces something genuinely new, not an average.

### Fleet Consensus = Musical Agreement

The `flux-hyperbolic-py` consensus mechanism maps directly to musical consensus:

- **Fleet consensus**: agents agree on a shared operating point in hyperbolic space
- **Musical consensus**: agents agree on harmonic targets (chord tones at bar boundaries)

The `consensus_weight` parameter controls how strongly an agent follows the consensus point vs. its own style. High consensus → agents lock into shared harmony. Low consensus → agents diverge, creating tension.

### Curvature as Creativity Parameter

The Poincaré ball uses curvature `c = -1` by default. By adjusting curvature:

| Curvature | Musical effect |
|-----------|---------------|
| `c → 0` (flat) | Euclidean — genres blend freely, weak boundaries |
| `c = -1` (default) | Balanced — genres distinct but crossable |
| `c → -∞` (sharp) | Strict hierarchy — genres are rigid silos |

**Low curvature** (closer to Euclidean) → cross-genre exploration, genre-bending
**High curvature** (more negative) → strict genre boundaries, purist playing

## API Design

```python
from flux_hyperbolic.music_routing import (
    MusicRoutingSpace,
    embed_personality,
    genre_distance,
    blend_genres,
    find_collaborators,
)

# Create the routing space
space = MusicRoutingSpace()

# Embed existing presets
space.embed_preset("parker", PARKER)
space.embed_preset("miles", MILES)

# Distance between styles
d = genre_distance("parker", "miles")  # ~1.2

# Blend two genres (70% Parker, 30% Miles → cool bebop)
blended = blend_genres(["parker", "miles"], [0.7, 0.3])

# Find best collaborators for a target blend
collabs = find_collaborators(
    target=blended,
    agent_pool=[PARKER, MILES, BACH, COLTRANE, MONK, ...],
    n=3,
)
# → [Parker (0.15), Coltrane (1.8), Monk (2.1)]
```

## From Points Back to Personalities

The reverse mapping (Poincaré ball point → `AgentPersonality`) decodes each dimension:

```python
personality = decode_to_personality(point, name="blended_agent")
# → AgentPersonality with interpolated parameters
```

This closes the loop: embed → blend → decode → play.

## Vision: Infinite Jam Sessions

Instead of 5 presets, the system gains:

1. **Continuous genre space** — any blend, any ratio
2. **Data-driven pairing** — find which agents harmonize vs. create tension
3. **Dynamic curvature** — adjust creativity in real-time during a session
4. **Collaborator discovery** — given a target vibe, find the best agents
5. **Fleet consensus for music** — N-agent jams (not just duos) with hyperbolic agreement

The AI-Jam evolves from a set of presets to an **explorable musical universe**.

---

## Implementation

- `flux_hyperbolic/music_routing.py` — the routing module
- `tests/test_music_routing.py` — 15+ tests covering all operations
