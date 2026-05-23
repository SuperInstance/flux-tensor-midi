"""
Musical Immune System — the composition defends itself against "pathogens"
(bad ideas, clichés, unwanted patterns).

Operational transfer: immunology → music.

The composition DEFENDS itself against:
- Clichés (overused patterns)
- Excessive repetition
- Unwanted dissonance
- Dead spots (too much silence)
- Randomness (no structure)

And TOLERATES:
- Intentional repetition (ostinato)
- Intentional dissonance (tension)
- Intentional silence (ma)

NON-PRE-CALCULABLE: the immune response evolves during performance.
Like a real immune system: it adapts to what it encounters.
"""

from __future__ import annotations

import copy
import hashlib
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class AntigenType(str, Enum):
    """Categories of musical pathogens."""

    CLICHE = "cliche"
    REPETITION = "repetition"
    DISSONANCE = "dissonance"
    SILENCE = "silence"
    RANDOM = "random"
    RANGE_VIOLATION = "range_violation"
    RHYTHMIC_MONOTONY = "rhythmic_monotony"
    HARMONIC_STAGNATION = "harmonic_stagnation"


@dataclass
class MusicalAntigen:
    """A musical pattern that the immune system recognizes as 'foreign'.

    Like a biological antigen: a molecular pattern that triggers an
    immune response. Here the 'molecule' is a sequence of notes/events.
    """

    pattern: List[dict]
    antigen_type: AntigenType
    danger_score: float  # 0 = benign, 1 = must-eliminate
    position: int = 0  # where in the event stream it was found
    context: Optional[dict] = None  # surrounding musical context

    @property
    def is_dangerous(self) -> bool:
        return self.danger_score >= 0.6

    @property
    def fingerprint(self) -> str:
        """Unique hash for this antigen pattern (for memory lookup)."""
        raw = str([(e.get("note", 0), e.get("velocity", 0), e.get("duration", 0))
                    for e in self.pattern])
        return hashlib.md5(raw.encode()).hexdigest()[:12]


@dataclass
class MusicalAntibody:
    """A constraint modification that neutralises a specific antigen.

    Like a biological antibody: it has a paratope (target_pattern) that
    binds to an epitope (antigen pattern) and a constant region
    (neutralizer) that effects the change.
    """

    target_pattern: List[dict]
    neutralizer: Callable[[List[dict], int], List[dict]]
    affinity: float = 0.5  # binding strength 0-1
    memory: bool = False
    generation: int = 0  # how many rounds of mutation
    target_antigen_type: Optional[AntigenType] = None
    created_at: float = field(default_factory=time.time)

    def recognize(self, pattern: List[dict]) -> float:
        """How well does this antibody recognise the pattern? (0-1)

        Uses a fuzzy matching approach: compare note intervals,
        rhythmic ratios, and velocity contours.
        """
        if not pattern or not self.target_pattern:
            return 0.0
        if len(pattern) != len(self.target_pattern):
            # Allow slight length mismatches with penalty
            len_ratio = min(len(pattern), len(self.target_pattern)) / max(
                len(pattern), len(self.target_pattern)
            )
            if len_ratio < 0.5:
                return 0.0
        score = 0.0
        compare_len = min(len(pattern), len(self.target_pattern))
        for i in range(compare_len):
            p = pattern[i]
            t = self.target_pattern[i]
            # Note similarity
            p_note = p.get("note", 0)
            t_note = t.get("note", 0)
            if p_note == t_note:
                score += 0.4
            elif abs(p_note - t_note) <= 2:
                score += 0.25
            # Velocity similarity
            p_vel = p.get("velocity", 64)
            t_vel = t.get("velocity", 64)
            vel_diff = abs(p_vel - t_vel) / 127.0
            score += max(0, 0.3 * (1 - vel_diff))
            # Duration similarity
            p_dur = p.get("duration", 0.25)
            t_dur = t.get("duration", 0.25)
            dur_ratio = min(p_dur, t_dur) / max(p_dur, t_dur) if max(p_dur, t_dur) > 0 else 1.0
            score += 0.3 * dur_ratio
        return min(1.0, score / compare_len)

    def neutralize(self, events: List[dict], antigen_pos: int) -> List[dict]:
        """Transform the events to remove the antigen at *antigen_pos*."""
        return self.neutralizer(events, antigen_pos)


# ---------------------------------------------------------------------------
# Helper: event construction
# ---------------------------------------------------------------------------


def _note_event(note: int, velocity: int = 64, duration: float = 0.25, **kw) -> dict:
    return {"note": note, "velocity": velocity, "duration": duration, **kw}


# ---------------------------------------------------------------------------
# Innate Immunity — first line of defence
# ---------------------------------------------------------------------------

# Known cliché patterns (scale degrees in C major as MIDI note offsets)
_CLICHE_PATTERNS: List[List[dict]] = [
    # "Heart and Soul" bass line  C-C-F-F-G-G-C-C
    [_note_event(48), _note_event(48), _note_event(53), _note_event(53),
     _note_event(55), _note_event(55), _note_event(48), _note_event(48)],
    # Endless ascending C major scale fragment
    [_note_event(60), _note_event(62), _note_event(64), _note_event(65),
     _note_event(67), _note_event(69), _note_event(71), _note_event(72)],
    # "Chopsticks"
    [_note_event(60), _note_event(64), _note_event(67),
     _note_event(64), _note_event(60)],
    # Triplet arpeggio repeated verbatim
    [_note_event(60), _note_event(64), _note_event(67)] * 3,
]


class InnateImmunity:
    """First line of defence — pattern recognition receptors.

    Like Toll-like receptors: recognises generic 'danger' patterns.
    Fast but imprecise.
    """

    def __init__(self, danger_patterns: Optional[List[List[dict]]] = None):
        self.danger_patterns: List[List[dict]] = danger_patterns or list(_CLICHE_PATTERNS)
        # Weights for each innate detector
        self.detector_weights: Dict[str, float] = {
            "cliche": 0.8,
            "repetition": 0.7,
            "dissonance": 0.6,
            "silence": 0.5,
            "random": 0.5,
            "range_violation": 0.6,
            "rhythmic_monotony": 0.65,
            "harmonic_stagnation": 0.6,
        }

    # -- individual detectors ------------------------------------------------

    def _detect_cliches(self, events: List[dict]) -> List[MusicalAntigen]:
        """Match known cliché patterns against the event stream."""
        antigens: List[MusicalAntigen] = []
        for cp in self.danger_patterns:
            cp_len = len(cp)
            for i in range(len(events) - cp_len + 1):
                window = events[i : i + cp_len]
                similarity = self._window_similarity(window, cp)
                if similarity >= 0.75:
                    antigens.append(MusicalAntigen(
                        pattern=window,
                        antigen_type=AntigenType.CLICHE,
                        danger_score=min(1.0, similarity * self.detector_weights["cliche"]),
                        position=i,
                    ))
        return antigens

    def _detect_repetition(self, events: List[dict], window: int = 4,
                            threshold: int = 5) -> List[MusicalAntigen]:
        """Detect excessive exact/near-exact repetition."""
        antigens: List[MusicalAntigen] = []
        if len(events) < window:
            return antigens
        patterns_seen: Dict[str, List[int]] = {}
        for i in range(len(events) - window + 1):
            pat = events[i : i + window]
            fp = self._fingerprint(pat)
            patterns_seen.setdefault(fp, []).append(i)
        for fp, positions in patterns_seen.items():
            if len(positions) >= threshold:
                antigens.append(MusicalAntigen(
                    pattern=events[positions[0] : positions[0] + window],
                    antigen_type=AntigenType.REPETITION,
                    danger_score=min(1.0, len(positions) / (threshold * 2)
                                     * self.detector_weights["repetition"]),
                    position=positions[0],
                ))
        return antigens

    def _detect_dissonance(self, events: List[dict],
                            max_interval: int = 6) -> List[MusicalAntigen]:
        """Detect clusters of harsh dissonant intervals (minor seconds, tritones
        everywhere) that lack musical justification."""
        antigens: List[MusicalAntigen] = []
        dissonant_intervals = {1, 2, 6, 10, 11}  # m2, M2, tritone, m7, M7
        ds_run = 0
        run_start = 0
        for i in range(1, len(events)):
            n1 = events[i - 1].get("note", 60)
            n2 = events[i].get("note", 60)
            interval = abs(n2 - n1) % 12
            if interval in dissonant_intervals:
                if ds_run == 0:
                    run_start = i - 1
                ds_run += 1
            else:
                if ds_run >= 4:
                    antigens.append(MusicalAntigen(
                        pattern=events[run_start : run_start + ds_run + 1],
                        antigen_type=AntigenType.DISSONANCE,
                        danger_score=min(1.0, ds_run / 8
                                         * self.detector_weights["dissonance"]),
                        position=run_start,
                    ))
                ds_run = 0
        # trailing run
        if ds_run >= 4:
            antigens.append(MusicalAntigen(
                pattern=events[run_start : run_start + ds_run + 1],
                antigen_type=AntigenType.DISSONANCE,
                danger_score=min(1.0, ds_run / 8
                                 * self.detector_weights["dissonance"]),
                position=run_start,
            ))
        return antigens

    def _detect_silence(self, events: List[dict],
                         threshold_ratio: float = 0.6) -> List[MusicalAntigen]:
        """Detect dead spots — stretches of silence/rest events."""
        antigens: List[MusicalAntigen] = []
        rest_run = 0
        run_start = 0
        for i, ev in enumerate(events):
            is_rest = ev.get("velocity", 64) == 0 or ev.get("note", -1) < 0
            if is_rest:
                if rest_run == 0:
                    run_start = i
                rest_run += 1
            else:
                if rest_run > 0:
                    ratio = rest_run / max(len(events), 1)
                    if ratio >= threshold_ratio or rest_run >= len(events) * 0.4:
                        antigens.append(MusicalAntigen(
                            pattern=events[run_start : run_start + rest_run],
                            antigen_type=AntigenType.SILENCE,
                            danger_score=min(1.0, ratio * 2
                                             * self.detector_weights["silence"]),
                            position=run_start,
                        ))
                rest_run = 0
        if rest_run > 0:
            ratio = rest_run / max(len(events), 1)
            if ratio >= threshold_ratio or rest_run >= len(events) * 0.4:
                antigens.append(MusicalAntigen(
                    pattern=events[run_start : run_start + rest_run],
                    antigen_type=AntigenType.SILENCE,
                    danger_score=min(1.0, ratio * 2
                                     * self.detector_weights["silence"]),
                    position=run_start,
                ))
        return antigens

    def _detect_random(self, events: List[dict], window: int = 8) -> List[MusicalAntigen]:
        """Detect structureless randomness — no intervallic or rhythmic coherence."""
        antigens: List[MusicalAntigen] = []
        if len(events) < window:
            return antigens
        for i in range(len(events) - window + 1):
            w = events[i : i + window]
            entropy = self._interval_entropy(w)
            if entropy > 3.2:  # very high entropy ⇒ random
                antigens.append(MusicalAntigen(
                    pattern=w,
                    antigen_type=AntigenType.RANDOM,
                    danger_score=min(1.0, (entropy - 3.2) / 1.0
                                     * self.detector_weights["random"]),
                    position=i,
                ))
        return antigens

    def _detect_range_violation(self, events: List[dict],
                                 low: int = 21, high: int = 108) -> List[MusicalAntigen]:
        """Detect notes outside acceptable MIDI range."""
        antigens: List[MusicalAntigen] = []
        for i, ev in enumerate(events):
            note = ev.get("note", 60)
            if note < low or note > high:
                antigens.append(MusicalAntigen(
                    pattern=[ev],
                    antigen_type=AntigenType.RANGE_VIOLATION,
                    danger_score=0.9 * self.detector_weights["range_violation"],
                    position=i,
                ))
        return antigens

    def _detect_rhythmic_monotony(self, events: List[dict],
                                   window: int = 16) -> List[MusicalAntigen]:
        """Detect stretches where all durations are identical."""
        antigens: List[MusicalAntigen] = []
        if len(events) < window:
            return antigens
        for i in range(len(events) - window + 1):
            w = events[i : i + window]
            durations = [e.get("duration", 0.25) for e in w]
            unique_durs = len(set(durations))
            if unique_durs <= 1:
                antigens.append(MusicalAntigen(
                    pattern=w,
                    antigen_type=AntigenType.RHYTHMIC_MONOTONY,
                    danger_score=0.7 * self.detector_weights["rhythmic_monotony"],
                    position=i,
                ))
        return antigens

    def _detect_harmonic_stagnation(self, events: List[dict],
                                     window: int = 12) -> List[MusicalAntigen]:
        """Detect harmonic stasis — same chord/pitch-class set for too long."""
        antigens: List[MusicalAntigen] = []
        if len(events) < window:
            return antigens
        for i in range(len(events) - window + 1):
            w = events[i : i + window]
            pcs = set(e.get("note", 60) % 12 for e in w)
            if len(pcs) <= 2:
                antigens.append(MusicalAntigen(
                    pattern=w,
                    antigen_type=AntigenType.HARMONIC_STAGNATION,
                    danger_score=0.65 * self.detector_weights["harmonic_stagnation"],
                    position=i,
                ))
        return antigens

    # -- orchestration -------------------------------------------------------

    def detect(self, events: List[dict]) -> List[MusicalAntigen]:
        """Scan for danger patterns. Fast but imprecise."""
        if not events:
            return []
        results: List[MusicalAntigen] = []
        results.extend(self._detect_cliches(events))
        results.extend(self._detect_repetition(events))
        results.extend(self._detect_dissonance(events))
        results.extend(self._detect_silence(events))
        results.extend(self._detect_random(events))
        results.extend(self._detect_range_violation(events))
        results.extend(self._detect_rhythmic_monotony(events))
        results.extend(self._detect_harmonic_stagnation(events))
        return results

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _fingerprint(pattern: List[dict]) -> str:
        notes = [e.get("note", 0) for e in pattern]
        durs = [e.get("duration", 0.25) for e in pattern]
        raw = str(list(zip(notes, durs)))
        return hashlib.md5(raw.encode()).hexdigest()[:10]

    @staticmethod
    def _window_similarity(a: List[dict], b: List[dict]) -> float:
        if len(a) != len(b):
            return 0.0
        if not a:
            return 1.0
        score = 0.0
        for x, y in zip(a, b):
            n1 = x.get("note", 0)
            n2 = y.get("note", 0)
            if n1 == n2:
                score += 0.5
            elif abs(n1 - n2) % 12 == 0:  # octave equivalence
                score += 0.35
            elif abs(n1 - n2) <= 2:
                score += 0.25
            d1 = x.get("duration", 0.25)
            d2 = y.get("duration", 0.25)
            dur_sim = min(d1, d2) / max(d1, d2) if max(d1, d2) > 0 else 1.0
            score += 0.3 * dur_sim
            v1 = x.get("velocity", 64)
            v2 = y.get("velocity", 64)
            vel_sim = 1 - abs(v1 - v2) / 127.0
            score += 0.2 * vel_sim
        return score / len(a)

    @staticmethod
    def _interval_entropy(events: List[dict]) -> float:
        """Shannon entropy of pitch intervals — higher ⇒ more random."""
        if len(events) < 2:
            return 0.0
        intervals = [abs(events[i + 1].get("note", 60) - events[i].get("note", 60))
                      for i in range(len(events) - 1)]
        # Discretise into buckets
        buckets: Dict[int, int] = {}
        for iv in intervals:
            b = min(iv, 24)
            buckets[b] = buckets.get(b, 0) + 1
        total = sum(buckets.values())
        if total == 0:
            return 0.0
        entropy = 0.0
        for count in buckets.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy


# ---------------------------------------------------------------------------
# Adaptive Immunity — learns from exposure
# ---------------------------------------------------------------------------

# Built-in neutraliser strategies (the "V(D)J library" of constraint parts)

def _neutralizer_transpose(events: List[dict], pos: int) -> List[dict]:
    """Transpose the offending pattern by a small interval."""
    result = list(events)
    shift = random.choice([-7, -5, -3, -2, 2, 3, 5, 7])
    end = min(pos + 4, len(result))
    for i in range(pos, end):
        result[i] = {**result[i], "note": result[i].get("note", 60) + shift}
    return result


def _neutralizer_invert(events: List[dict], pos: int) -> List[dict]:
    """Intervallic inversion around the first note of the pattern."""
    result = list(events)
    if pos >= len(result):
        return result
    axis = result[pos].get("note", 60)
    end = min(pos + 6, len(result))
    for i in range(pos + 1, end):
        n = result[i].get("note", 60)
        result[i] = {**result[i], "note": 2 * axis - n}
    return result


def _neutralizer_rhythmic_variation(events: List[dict], pos: int) -> List[dict]:
    """Vary the rhythm of the offending pattern."""
    result = list(events)
    end = min(pos + 4, len(result))
    for i in range(pos, end):
        factor = random.choice([0.5, 0.75, 1.0, 1.5, 2.0])
        result[i] = {**result[i], "duration": result[i].get("duration", 0.25) * factor}
    return result


def _neutralizer_velocity_shaping(events: List[dict], pos: int) -> List[dict]:
    """Apply a velocity contour to break monotony."""
    result = list(events)
    end = min(pos + 6, len(result))
    shape_len = end - pos
    # Crescendo or decrescendo
    crescendo = random.choice([True, False])
    for i in range(pos, end):
        t = (i - pos) / max(shape_len - 1, 1)
        base_vel = result[i].get("velocity", 64)
        mod = int(30 * (t if crescendo else (1 - t)))
        result[i] = {**result[i], "velocity": max(1, min(127, base_vel + mod))}
    return result


def _neutralizer_substitute(events: List[dict], pos: int) -> List[dict]:
    """Replace the offending notes with consonant alternatives."""
    result = list(events)
    consonant_offsets = [0, 2, 4, 5, 7, 9, 11]  # major scale intervals
    end = min(pos + 4, len(result))
    for i in range(pos, end):
        base = result[i].get("note", 60)
        root = base - (base % 12)
        offset = random.choice(consonant_offsets)
        result[i] = {**result[i], "note": root + offset}
    return result


def _neutralizer_insert_rest(events: List[dict], pos: int) -> List[dict]:
    """Insert a rest to break up the offending pattern."""
    result = list(events)
    if pos < len(result):
        rest = {"note": -1, "velocity": 0, "duration": result[pos].get("duration", 0.25)}
        result.insert(pos, rest)
    return result


_NEUTRALIZER_LIBRARY = [
    _neutralizer_transpose,
    _neutralizer_invert,
    _neutralizer_rhythmic_variation,
    _neutralizer_velocity_shaping,
    _neutralizer_substitute,
    _neutralizer_insert_rest,
]


class AdaptiveImmunity:
    """Learns from exposure — generates specific antibodies.

    Like B cells and T cells: gets better with each exposure.
    """

    def __init__(self):
        self.antibodies: List[MusicalAntibody] = []
        self.memory_cells: List[MusicalAntibody] = []
        self.antigen_log: List[MusicalAntigen] = []

    # -- core operations -----------------------------------------------------

    def present_antigen(self, antigen: MusicalAntigen) -> None:
        """Antigen-presenting cell shows antigen to T cells.

        Logs the antigen and triggers antibody generation if it's novel.
        """
        self.antigen_log.append(antigen)

        # Check if we already have a memory cell for this
        for mem in self.memory_cells:
            if mem.recognize(antigen.pattern) >= 0.7:
                return  # already known — memory will handle it

        # Novel antigen → generate new antibody
        ab = self.generate_antibody(antigen)
        self.antibodies.append(ab)

    def generate_antibody(self, antigen: MusicalAntigen) -> MusicalAntibody:
        """Generate a NEW antibody that specifically targets this antigen.

        Like V(D)J recombination: mix-and-match constraint components from
        the neutraliser library.
        """
        # Select the best neutraliser strategy for this antigen type
        neutralizer = self._select_neutralizer(antigen)
        ab = MusicalAntibody(
            target_pattern=list(antigen.pattern),
            neutralizer=neutralizer,
            affinity=0.3 + random.random() * 0.4,  # initial affinity is modest
            memory=False,
            generation=0,
            target_antigen_type=antigen.antigen_type,
        )
        return ab

    def clonal_expansion(self, antibody: MusicalAntibody,
                          n: int = 10) -> List[MusicalAntibody]:
        """Expand a successful antibody with slight mutations.

        Like clonal selection: the best antibodies proliferate.
        """
        clones: List[MusicalAntibody] = [antibody]
        for _ in range(n - 1):
            clone = self.somatic_hypermutation(copy.deepcopy(antibody))
            clones.append(clone)
        return clones

    def somatic_hypermutation(self, antibody: MusicalAntibody) -> MusicalAntibody:
        """Mutate antibody to (potentially) increase affinity.

        Like affinity maturation: antibodies get better over time.
        Mutates the target pattern slightly so it can recognise
        variants of the original antigen.
        """
        mutated_pattern = []
        for event in antibody.target_pattern:
            new_ev = dict(event)
            # Mutate note by ±2 semitones
            if random.random() < 0.3:
                new_ev["note"] = new_ev.get("note", 60) + random.choice([-2, -1, 1, 2])
            # Mutate duration slightly
            if random.random() < 0.2:
                dur = new_ev.get("duration", 0.25)
                new_ev["duration"] = dur * random.choice([0.75, 1.0, 1.25, 1.5])
            mutated_pattern.append(new_ev)

        # Shift affinity randomly (may improve or degrade)
        delta_affinity = random.gauss(0, 0.1)
        new_affinity = max(0.1, min(1.0, antibody.affinity + delta_affinity))

        return MusicalAntibody(
            target_pattern=mutated_pattern,
            neutralizer=antibody.neutralizer,
            affinity=new_affinity,
            memory=antibody.memory,
            generation=antibody.generation + 1,
            target_antigen_type=antibody.target_antigen_type,
        )

    # -- memory management ---------------------------------------------------

    def promote_to_memory(self, antibody: MusicalAntibody) -> None:
        """Promote a high-affinity antibody to memory-cell status."""
        ab = copy.deepcopy(antibody)
        ab.memory = True
        ab.affinity = min(1.0, ab.affinity * 1.1)  # slight boost
        # Replace existing memory cell for same type if affinity is higher
        for i, mem in enumerate(self.memory_cells):
            if mem.target_antigen_type == ab.target_antigen_type:
                if ab.affinity > mem.affinity:
                    self.memory_cells[i] = ab
                return
        self.memory_cells.append(ab)

    # -- response speed ------------------------------------------------------

    def primary_response_delay(self) -> float:
        """Time cost for generating a brand-new antibody (simulated).
        Primary immune response: slow (days in biology)."""
        return 1.0 + random.random() * 0.5

    def secondary_response_delay(self) -> float:
        """Time cost for memory-cell response.
        Secondary immune response: fast (hours in biology)."""
        return 0.1 + random.random() * 0.1

    # -- helpers -------------------------------------------------------------

    def _select_neutralizer(self, antigen: MusicalAntigen) -> Callable:
        """Choose the best neutraliser strategy for the antigen type."""
        strategy_map: Dict[AntigenType, List[Callable]] = {
            AntigenType.CLICHE: [_neutralizer_transpose, _neutralizer_invert,
                                  _neutralizer_substitute],
            AntigenType.REPETITION: [_neutralizer_transpose, _neutralizer_rhythmic_variation,
                                      _neutralizer_invert],
            AntigenType.DISSONANCE: [_neutralizer_substitute, _neutralizer_transpose],
            AntigenType.SILENCE: [_neutralizer_substitute, _neutralizer_velocity_shaping],
            AntigenType.RANDOM: [_neutralizer_substitute, _neutralizer_velocity_shaping,
                                  _neutralizer_insert_rest],
            AntigenType.RANGE_VIOLATION: [_neutralizer_substitute, _neutralizer_transpose],
            AntigenType.RHYTHMIC_MONOTONY: [_neutralizer_rhythmic_variation,
                                             _neutralizer_insert_rest],
            AntigenType.HARMONIC_STAGNATION: [_neutralizer_transpose, _neutralizer_invert],
        }
        strategies = strategy_map.get(antigen.antigen_type, _NEUTRALIZER_LIBRARY)
        return random.choice(strategies)

    def find_best_antibody(self, antigen: MusicalAntigen) -> Optional[MusicalAntibody]:
        """Find the antibody with highest recognition score for this antigen."""
        best: Optional[MusicalAntibody] = None
        best_score = 0.0
        # Check memory cells first (faster)
        for mem in self.memory_cells:
            score = mem.recognize(antigen.pattern)
            if score > best_score:
                best_score = score
                best = mem
        # Then check general antibodies
        for ab in self.antibodies:
            score = ab.recognize(antigen.pattern)
            if score > best_score:
                best_score = score
                best = ab
        return best


# ---------------------------------------------------------------------------
# Full Musical Immune System
# ---------------------------------------------------------------------------

class MusicalImmuneSystem:
    """Full immune system for a live composition.

    The composition DEFENDS ITSELF against pathogens (unwanted patterns)
    and TOLERATES intentional musical choices.

    NON-PRE-CALCULABLE: the immune response evolves during performance.
    Like a real immune system: it adapts to what it encounters.
    """

    def __init__(self):
        self.innate = InnateImmunity()
        self.adaptive = AdaptiveImmunity()
        self.tolerance: Dict[str, float] = {}  # pattern fingerprint → tolerance level
        self.vaccination_history: List[MusicalAntigen] = []
        self.response_log: List[dict] = []
        self._suppressed: bool = False  # immunotherapy flag
        self._suppression_level: float = 0.0  # 0 = full immune, 1 = fully suppressed

    # -- self-tolerance registration -----------------------------------------

    def register_self(self, pattern: List[dict], label: str = "",
                       tolerance: float = 1.0) -> None:
        """Register a pattern as 'self' — the immune system should not attack it.

        Like self-tolerance in biology: the thymus teaches T cells to
        recognise the body's own proteins.
        """
        fp = hashlib.md5(str(pattern).encode()).hexdigest()[:12]
        self.tolerance[fp] = tolerance
        if label:
            self.tolerance[f"label:{label}"] = tolerance

    def is_self(self, pattern: List[dict]) -> bool:
        """Check if a pattern is registered as 'self'."""
        fp = hashlib.md5(str(pattern).encode()).hexdigest()[:12]
        return fp in self.tolerance

    # -- scanning ------------------------------------------------------------

    def scan(self, events: List[dict]) -> List[MusicalAntigen]:
        """Innate + adaptive scan. Memory cells respond faster.

        Returns a list of detected antigens (potential threats).
        """
        if self._suppressed:
            # Suppressed immune system: reduced detection
            if random.random() < self._suppression_level:
                return []

        # Innate scan (fast, generic)
        antigens = self.innate.detect(events)

        # Filter out self-tolerated patterns
        antigens = [a for a in antigens if not self.is_self(a.pattern)]

        # Adaptive cross-check (see if adaptive has better matching)
        for ab in self.adaptive.antibodies:
            for i in range(len(events) - 3):
                window = events[i : i + len(ab.target_pattern)]
                if ab.recognize(window) >= 0.8:
                    # Check if already detected
                    already = any(a.position == i for a in antigens)
                    if not already and not self.is_self(window):
                        antigens.append(MusicalAntigen(
                            pattern=window,
                            antigen_type=ab.target_antigen_type or AntigenType.CLICHE,
                            danger_score=ab.affinity,
                            position=i,
                        ))
        return antigens

    # -- response ------------------------------------------------------------

    def respond(self, events: List[dict],
                antigens: Optional[List[MusicalAntigen]] = None) -> List[dict]:
        """Generate immune response: neutralise antigens.

        If novel antigen: generate new antibody (slow, primary response).
        If known antigen: use memory cells (fast, secondary response).
        """
        if self._suppressed and random.random() < self._suppression_level:
            return events

        if antigens is None:
            antigens = self.scan(events)

        if not antigens:
            return events

        result = list(events)
        # Sort by danger score (highest first) but process in reverse position
        # order to preserve indices
        sorted_antigens = sorted(antigens, key=lambda a: (-a.danger_score, -a.position))

        offset = 0  # track insertions/deletions
        for antigen in sorted_antigens:
            pos = antigen.position + offset
            if pos >= len(result):
                continue

            # Find or generate antibody
            ab = self.adaptive.find_best_antibody(antigen)

            if ab is None or ab.recognize(antigen.pattern) < 0.5:
                # Novel antigen → primary response
                self.adaptive.present_antigen(antigen)
                ab = self.adaptive.find_best_antibody(antigen)
                delay = self.adaptive.primary_response_delay()

                self.response_log.append({
                    "type": "primary",
                    "antigen": antigen.antigen_type.value,
                    "position": antigen.position,
                    "danger": antigen.danger_score,
                    "delay": delay,
                })
            else:
                # Known antigen → secondary (memory) response
                delay = self.adaptive.secondary_response_delay()
                self.response_log.append({
                    "type": "secondary",
                    "antigen": antigen.antigen_type.value,
                    "position": antigen.position,
                    "danger": antigen.danger_score,
                    "delay": delay,
                })

            if ab is not None and antigen.is_dangerous:
                old_len = len(result)
                result = ab.neutralize(result, pos)
                offset += len(result) - old_len

                # Promote high-affinity antibodies to memory
                if ab.affinity >= 0.7 and not ab.memory:
                    self.adaptive.promote_to_memory(ab)

                # Clonal expansion for very dangerous antigens
                if antigen.danger_score >= 0.8:
                    clones = self.adaptive.clonal_expansion(ab, n=5)
                    self.adaptive.antibodies.extend(clones)

        return result

    # -- vaccination ---------------------------------------------------------

    def vaccinate(self, antigens: List[MusicalAntigen]) -> None:
        """Pre-expose the system to known bad patterns.

        Like vaccination: generate memory cells without actual infection.
        """
        for antigen in antigens:
            ab = self.adaptive.generate_antibody(antigen)
            ab.memory = True
            ab.affinity = max(ab.affinity, 0.7)  # vaccination gives a head start
            self.adaptive.memory_cells.append(ab)
            self.vaccination_history.append(antigen)

    def vaccinate_against_cliches(self) -> None:
        """Convenience: vaccinate against the built-in cliché library."""
        for cp in _CLICHE_PATTERNS:
            ag = MusicalAntigen(
                pattern=cp,
                antigen_type=AntigenType.CLICHE,
                danger_score=0.8,
            )
            self.vaccinate([ag])

    # -- self-tolerance check ------------------------------------------------

    def autoimmune_check(self, events: List[dict]) -> List[MusicalAntigen]:
        """Make sure the immune system isn't attacking GOOD patterns.

        Like self-tolerance: distinguish self from non-self.
        Returns antigens that are FALSE POSITIVES (should be tolerated).
        """
        if not events:
            return []

        detected = self.scan(events)
        false_positives: List[MusicalAntigen] = []

        for antigen in detected:
            # Check if this pattern matches any registered 'self' pattern
            for fp, tol in self.tolerance.items():
                if fp.startswith("label:"):
                    continue
                # Reconstruct the self-pattern fingerprint
                if self.is_self(antigen.pattern):
                    false_positives.append(antigen)
                    break

            # Also check: is this an intentional ostinato / repetition?
            if antigen.antigen_type == AntigenType.REPETITION:
                # Count how many times this exact pattern occurs
                pat_len = len(antigen.pattern)
                occurrences = 0
                for i in range(len(events) - pat_len + 1):
                    window = events[i : i + pat_len]
                    if self._patterns_match(window, antigen.pattern):
                        occurrences += 1
                # If it appears regularly (ostinato), it's intentional
                if occurrences >= 3 and pat_len <= 8:
                    false_positives.append(antigen)

        return false_positives

    # -- immunotherapy -------------------------------------------------------

    def immunotherapy(self, stuck_composition: List[dict],
                       suppression_level: float = 0.7,
                       duration_steps: int = 4) -> List[List[dict]]:
        """When the composition is stuck (no ideas), use checkpoint inhibitors.

        Like cancer immunotherapy: temporarily suppress the immune system
        to allow more creative exploration. Returns a sequence of
        progressively less-suppressed compositions.
        """
        results: List[List[dict]] = []
        original_suppressed = self._suppressed
        original_level = self._suppression_level

        # Gradually suppress then restore
        for step in range(duration_steps):
            if step < duration_steps // 2:
                # Increasing suppression
                self._suppressed = True
                self._suppression_level = min(1.0,
                    suppression_level * ((step + 1) / (duration_steps // 2)))
            else:
                # Decreasing suppression (restoring immune function)
                remaining = duration_steps - step
                self._suppression_level = max(0.0,
                    suppression_level * (remaining / (duration_steps // 2)))
                if self._suppression_level < 0.1:
                    self._suppressed = False

            # Generate creative variation while suppressed
            variation = self._creative_mutation(
                stuck_composition,
                creativity=1.0 - self._suppression_level * 0.5
            )
            results.append(variation)

        # Restore original state
        self._suppressed = original_suppressed
        self._suppression_level = original_level
        return results

    # -- statistics ----------------------------------------------------------

    def immune_repertoire_summary(self) -> dict:
        """Summary of the current immune repertoire.

        Like a blood panel: tells you the state of immunity.
        """
        return {
            "total_antibodies": len(self.adaptive.antibodies),
            "memory_cells": len(self.adaptive.memory_cells),
            "antigen_exposures": len(self.adaptive.antigen_log),
            "vaccinations": len(self.vaccination_history),
            "tolerated_patterns": len(self.tolerance),
            "responses_logged": len(self.response_log),
            "primary_responses": sum(
                1 for r in self.response_log if r["type"] == "primary"
            ),
            "secondary_responses": sum(
                1 for r in self.response_log if r["type"] == "secondary"
            ),
            "is_suppressed": self._suppressed,
            "suppression_level": self._suppression_level,
            "antibody_affinity_avg": (
                sum(ab.affinity for ab in self.adaptive.antibodies)
                / max(len(self.adaptive.antibodies), 1)
            ),
        }

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _patterns_match(a: List[dict], b: List[dict], threshold: float = 0.8) -> bool:
        """Fuzzy match between two patterns."""
        if len(a) != len(b):
            return False
        if not a:
            return True
        score = 0.0
        for x, y in zip(a, b):
            if x.get("note", 0) == y.get("note", 0):
                score += 0.5
            if abs(x.get("duration", 0.25) - y.get("duration", 0.25)) < 0.01:
                score += 0.3
            if abs(x.get("velocity", 64) - y.get("velocity", 64)) < 10:
                score += 0.2
        return (score / len(a)) >= threshold

    @staticmethod
    def _creative_mutation(events: List[dict], creativity: float = 0.5) -> List[dict]:
        """Apply creative mutations to break out of a rut.

        creativity=0 ⇒ almost no change, creativity=1 ⇒ bold changes.
        """
        result = copy.deepcopy(events)
        if not result:
            return result

        n_mutations = max(1, int(len(result) * creativity * 0.3))
        for _ in range(n_mutations):
            i = random.randint(0, len(result) - 1)
            mutation_type = random.choice(["transpose", "duration", "velocity", "insert", "swap"])

            if mutation_type == "transpose":
                shift = random.choice([-12, -7, -5, -3, -2, 2, 3, 5, 7, 12])
                result[i]["note"] = result[i].get("note", 60) + shift
            elif mutation_type == "duration":
                result[i]["duration"] = result[i].get("duration", 0.25) * random.choice(
                    [0.5, 0.75, 1.5, 2.0]
                )
            elif mutation_type == "velocity":
                result[i]["velocity"] = max(
                    1, min(127, result[i].get("velocity", 64) + random.randint(-30, 30))
                )
            elif mutation_type == "insert" and i < len(result) - 1:
                # Duplicate and shift
                new_ev = dict(result[i])
                new_ev["note"] = new_ev.get("note", 60) + random.choice([3, 4, 5, 7, 12])
                result.insert(i + 1, new_ev)
            elif mutation_type == "swap" and i < len(result) - 1:
                result[i], result[i + 1] = result[i + 1], result[i]

        return result


# ---------------------------------------------------------------------------
# Exported API
# ---------------------------------------------------------------------------

__all__ = [
    "AntigenType",
    "MusicalAntigen",
    "MusicalAntibody",
    "InnateImmunity",
    "AdaptiveImmunity",
    "MusicalImmuneSystem",
    "_note_event",
    "_NEUTRALIZER_LIBRARY",
]
