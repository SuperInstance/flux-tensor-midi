"""
Algorithmic Beta Testing Framework
- Generate musical ideas from the creative engine
- Create diverse tester personas (beginner, expert, different genres)
- A/B test different ε, ρ, coupling configurations
- Score and rank configurations
- Export results as JSON for analysis
"""

import numpy as np
import json
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from flux_tensor_midi.creative_engine import (
    CreativeSystem, CreativeNetwork, CreativeThermostat,
    QualityMetrics, Regime, CouplingTopology
)


class TesterPersona(Enum):
    """Different beta tester profiles."""
    BEGINNER_LISTENER = "beginner_listener"
    CLASSICAL_MUSICIAN = "classical_musician"
    JAZZ_MUSICIAN = "jazz_musician"
    ELECTRONIC_PRODUCER = "electronic_producer"
    MUSIC_THEORIST = "music_theorist"
    CASUAL_LISTENER = "casual_listener"
    AVANT_GARDE = "avant_garde"
    DANCER = "dancer"


@dataclass
class TesterPreferences:
    """What a tester values in music."""
    preferred_novelty: float  # 0-1, how much they want surprise
    preferred_coherence: float  # 0-1, how much structure they want
    preferred_tempo_range: Tuple[float, float]  # BPM range
    genre_familiarity: Dict[str, float]  # genre → familiarity 0-1
    tolerance_for_dissonance: float  # 0-1
    attention_span: int  # number of events they'll evaluate
    
    @classmethod
    def from_persona(cls, persona: TesterPersona) -> 'TesterPreferences':
        profiles = {
            TesterPersona.BEGINNER_LISTENER: cls(
                preferred_novelty=0.2, preferred_coherence=0.9,
                preferred_tempo_range=(80, 120), 
                genre_familiarity={'pop': 0.9, 'rock': 0.7},
                tolerance_for_dissonance=0.1, attention_span=50
            ),
            TesterPersona.CLASSICAL_MUSICIAN: cls(
                preferred_novelty=0.4, preferred_coherence=0.85,
                preferred_tempo_range=(40, 180),
                genre_familiarity={'classical': 0.95, 'jazz': 0.5, 'baroque': 0.9},
                tolerance_for_dissonance=0.3, attention_span=200
            ),
            TesterPersona.JAZZ_MUSICIAN: cls(
                preferred_novelty=0.7, preferred_coherence=0.6,
                preferred_tempo_range=(60, 250),
                genre_familiarity={'jazz': 0.95, 'blues': 0.9, 'bebop': 0.9},
                tolerance_for_dissonance=0.7, attention_span=300
            ),
            TesterPersona.ELECTRONIC_PRODUCER: cls(
                preferred_novelty=0.5, preferred_coherence=0.7,
                preferred_tempo_range=(120, 180),
                genre_familiarity={'electronic': 0.95, 'techno': 0.9, 'house': 0.85},
                tolerance_for_dissonance=0.5, attention_span=150
            ),
            TesterPersona.MUSIC_THEORIST: cls(
                preferred_novelty=0.6, preferred_coherence=0.8,
                preferred_tempo_range=(20, 300),
                genre_familiarity={'all': 0.8},
                tolerance_for_dissonance=0.9, attention_span=500
            ),
            TesterPersona.CASUAL_LISTENER: cls(
                preferred_novelty=0.15, preferred_coherence=0.95,
                preferred_tempo_range=(90, 130),
                genre_familiarity={'pop': 0.95, 'country': 0.7},
                tolerance_for_dissonance=0.05, attention_span=30
            ),
            TesterPersona.AVANT_GARDE: cls(
                preferred_novelty=0.9, preferred_coherence=0.3,
                preferred_tempo_range=(1, 500),
                genre_familiarity={'experimental': 0.95, 'noise': 0.8},
                tolerance_for_dissonance=0.95, attention_span=400
            ),
            TesterPersona.DANCER: cls(
                preferred_novelty=0.3, preferred_coherence=0.85,
                preferred_tempo_range=(115, 140),
                genre_familiarity={'electronic': 0.9, 'hiphop': 0.8},
                tolerance_for_dissonance=0.2, attention_span=100
            ),
        }
        return profiles[persona]


@dataclass
class MusicalIdea:
    """A generated musical idea for testing."""
    pitches: List[int]  # MIDI pitch numbers
    velocities: List[int]  # 0-127
    durations: List[float]  # in beats
    onset_times: List[float]  # in beats
    source_config: Dict  # what generated this
    metadata: Dict = field(default_factory=dict)
    
    @classmethod
    def from_creative_system(cls, system: CreativeSystem, 
                            base_pitch: int = 60, 
                            scale: List[int] = None,
                            n_events: int = 32,
                            bpm: float = 120.0) -> 'MusicalIdea':
        """Generate a musical idea from a creative system's output."""
        if scale is None:
            scale = [0, 2, 4, 5, 7, 9, 11]  # major scale
        
        outputs = np.array(system.outputs[-n_events:])
        if len(outputs) == 0:
            system.run(n_events, n_events)
            outputs = np.array(system.outputs[-n_events:])
        
        # Normalize outputs to [0, 1]
        min_val, max_val = outputs.min(), outputs.max()
        if max_val - min_val < 1e-10:
            normalized = np.ones_like(outputs) * 0.5
        else:
            normalized = (outputs - min_val) / (max_val - min_val)
        
        pitches = []
        velocities = []
        durations = []
        onset_times = []
        
        beat_duration = 60.0 / bpm
        current_time = 0.0
        
        for i, val in enumerate(normalized):
            # Map to scale degree
            degree = int(val * len(scale)) % len(scale)
            octave = int(val * 3)  # 0-2 octaves
            pitch = base_pitch + scale[degree] + octave * 12
            pitches.append(max(0, min(127, pitch)))
            
            # Velocity from derivative
            if i > 0:
                vel_change = (normalized[i] - normalized[i-1]) * 50
            else:
                vel_change = 0
            velocity = int(80 + vel_change)
            velocities.append(max(20, min(127, velocity)))
            
            # Duration from spacing
            dur = beat_duration * (0.25 + 0.75 * np.random.random())
            durations.append(dur)
            
            onset_times.append(current_time)
            current_time += dur
        
        return cls(
            pitches=pitches, velocities=velocities,
            durations=durations, onset_times=onset_times,
            source_config={
                'rho': system.rho,
                'sigma': system.sigma,
                'epsilon': system.epsilon,
                'regime': system.regime.value,
            }
        )


@dataclass
class TestResult:
    """Result from a single tester evaluating a single idea."""
    persona: TesterPersona
    idea: MusicalIdea
    overall_score: float  # 0-10
    novelty_score: float
    coherence_score: float
    engagement_score: float
    would_listen_again: bool
    comments: str = ""


class BetaTester:
    """An algorithmic beta tester."""
    
    def __init__(self, persona: TesterPersona):
        self.persona = persona
        self.preferences = TesterPreferences.from_persona(persona)
        self.results: List[TestResult] = []
    
    def evaluate(self, idea: MusicalIdea) -> TestResult:
        """Evaluate a musical idea based on preferences."""
        n_events = min(len(idea.pitches), self.preferences.attention_span)
        
        if n_events == 0:
            return TestResult(
                persona=self.persona, idea=idea,
                overall_score=0, novelty_score=0,
                coherence_score=0, engagement_score=0,
                would_listen_again=False, comments="Empty idea"
            )
        
        # Pitch variety (novelty proxy)
        unique_pitches = len(set(idea.pitches[:n_events]))
        pitch_variety = unique_pitches / 12.0  # normalize to pitch classes
        
        # Interval diversity
        intervals = [abs(idea.pitches[i+1] - idea.pitches[i]) 
                     for i in range(n_events - 1)]
        interval_variety = np.std(intervals) / 12.0 if intervals else 0
        
        novelty = min(1.0, (pitch_variety + interval_variety) / 2)
        
        # Pattern repetition (coherence proxy)
        pitch_seq = idea.pitches[:n_events]
        if len(pitch_seq) > 4:
            # Check for repeated subsequences of length 2-4
            repetitions = 0
            for length in [2, 3, 4]:
                for i in range(len(pitch_seq) - 2*length):
                    pattern = pitch_seq[i:i+length]
                    for j in range(i+length, len(pitch_seq) - length):
                        if pitch_seq[j:j+length] == pattern:
                            repetitions += 1
            coherence = min(1.0, repetitions / max(1, n_events))
        else:
            coherence = 0.5
        
        # Rhythmic consistency
        dur_arr = np.array(idea.durations[:n_events])
        rhythmic_consistency = 1.0 / (1.0 + np.std(dur_arr) / np.mean(dur_arr))
        
        # Velocity dynamics
        vel_arr = np.array(idea.velocities[:n_events])
        velocity_range = (vel_arr.max() - vel_arr.min()) / 127.0
        
        # Engagement: sustained interest
        # High if there's development (not monotonic)
        vel_changes = np.abs(np.diff(vel_arr))
        engagement = min(1.0, np.mean(vel_changes) / 20.0)
        
        # Score based on preferences
        novelty_score = novelty
        # How well does novelty match preference?
        novelty_fit = 1.0 - abs(novelty - self.preferences.preferred_novelty)
        
        coherence_score = (coherence + rhythmic_consistency) / 2
        coherence_fit = 1.0 - abs(coherence_score - self.preferences.preferred_coherence)
        
        engagement_score = engagement
        
        # Overall: weighted combination
        overall = (novelty_fit * 0.3 + coherence_fit * 0.3 + 
                  engagement_score * 0.2 + velocity_range * 0.1 +
                  rhythmic_consistency * 0.1) * 10
        
        # Dissonance penalty
        dissonant_intervals = sum(1 for i in intervals if i in [1, 6]) 
        dissonance_ratio = dissonant_intervals / max(1, len(intervals))
        if dissonance_ratio > self.preferences.tolerance_for_dissonance:
            penalty = (dissonance_ratio - self.preferences.tolerance_for_dissonance) * 5
            overall -= penalty
        
        overall = max(0, min(10, overall))
        would_listen = overall > 5.0
        
        # Generate comment
        if novelty > 0.7:
            comments = "Very creative and surprising"
        elif coherence > 0.7:
            comments = "Well-structured, predictable"
        else:
            comments = "Mixed qualities"
        
        result = TestResult(
            persona=self.persona, idea=idea,
            overall_score=overall,
            novelty_score=novelty_score,
            coherence_score=coherence_score,
            engagement_score=engagement_score,
            would_listen_again=would_listen,
            comments=comments
        )
        
        self.results.append(result)
        return result


class BetaTestSuite:
    """Run a full beta test suite across configurations and personas."""
    
    def __init__(self):
        self.testers = {p: BetaTester(p) for p in TesterPersona}
        self.all_results: List[TestResult] = []
    
    def test_configuration(self, rho: float, sigma: float = 10.0, 
                          epsilon: float = None, 
                          n_ideas: int = 5,
                          scales: Dict[str, List[int]] = None) -> Dict:
        """Test a specific creative configuration against all personas."""
        
        if scales is None:
            scales = {
                'major': [0, 2, 4, 5, 7, 9, 11],
                'minor': [0, 2, 3, 5, 7, 8, 10],
                'pentatonic': [0, 2, 4, 7, 9],
                'chromatic': list(range(12)),
                'blues': [0, 3, 5, 6, 7, 10],
            }
        
        results = {}
        
        for persona, tester in self.testers.items():
            persona_scores = []
            
            for i in range(n_ideas):
                # Create system with this config
                system = CreativeSystem(rho=rho, sigma=sigma, epsilon=epsilon)
                
                # Use different scales for variety
                scale_name = list(scales.keys())[i % len(scales)]
                scale = scales[scale_name]
                
                idea = MusicalIdea.from_creative_system(system, scale=scale)
                result = tester.evaluate(idea)
                persona_scores.append(result.overall_score)
                self.all_results.append(result)
            
            results[persona.value] = {
                'mean_score': float(np.mean(persona_scores)),
                'std_score': float(np.std(persona_scores)),
                'would_listen_pct': sum(1 for s in persona_scores if s > 5) / len(persona_scores) * 100,
            }
        
        return results
    
    def ab_test(self, config_a: Dict, config_b: Dict, 
                n_ideas: int = 10) -> Dict:
        """A/B test two configurations."""
        
        results_a = self.test_configuration(**config_a, n_ideas=n_ideas)
        results_b = self.test_configuration(**config_b, n_ideas=n_ideas)
        
        comparison = {}
        for persona in results_a:
            score_a = results_a[persona]['mean_score']
            score_b = results_b[persona]['mean_score']
            comparison[persona] = {
                'config_a_score': score_a,
                'config_b_score': score_b,
                'winner': 'A' if score_a > score_b else 'B',
                'delta': abs(score_a - score_b),
            }
        
        a_wins = sum(1 for c in comparison.values() if c['winner'] == 'A')
        b_wins = sum(1 for c in comparison.values() if c['winner'] == 'B')
        
        return {
            'config_a': config_a,
            'config_b': config_b,
            'results_a': results_a,
            'results_b': results_b,
            'comparison': comparison,
            'summary': f"A wins {a_wins}/{a_wins+b_wins}, B wins {b_wins}/{a_wins+b_wins}",
            'overall_winner': 'A' if a_wins > b_wins else 'B',
        }
    
    def sweep_rho(self, rho_values: List[float] = None, 
                  sigma: float = 10.0) -> Dict:
        """Sweep ρ values and find optimal per persona."""
        
        if rho_values is None:
            rho_values = [1, 3, 5, 10, 15, 20, 25, 28, 35, 45, 55]
        
        sweep = {}
        
        for rho in rho_values:
            sweep[rho] = self.test_configuration(rho=rho, sigma=sigma, n_ideas=3)
        
        # Find optimal rho per persona
        optimal = {}
        for persona in TesterPersona:
            best_rho = max(rho_values, 
                         key=lambda r: sweep[r][persona.value]['mean_score'])
            optimal[persona.value] = best_rho
        
        return {'sweep': sweep, 'optimal_rho': optimal}
    
    def sweep_epsilon(self, rho: float = 28.0,
                      eps_values: List[float] = None) -> Dict:
        """Sweep ε values for a given ρ."""
        
        if eps_values is None:
            eps_values = [0.01, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]
        
        sweep = {}
        for eps in eps_values:
            sweep[eps] = self.test_configuration(rho=rho, epsilon=eps, n_ideas=3)
        
        optimal = {}
        for persona in TesterPersona:
            best_eps = max(eps_values,
                         key=lambda e: sweep[e][persona.value]['mean_score'])
            optimal[persona.value] = best_eps
        
        return {'sweep': sweep, 'optimal_epsilon': optimal}
    
    def generate_report(self) -> str:
        """Generate a summary report of all tests."""
        lines = ["=" * 60, "BETA TEST REPORT", "=" * 60]
        
        # Per-persona summary
        lines.append("\nTester Persona Scores:")
        for persona, tester in self.testers.items():
            if tester.results:
                scores = [r.overall_score for r in tester.results]
                lines.append(f"  {persona.value:25s}: "
                           f"mean={np.mean(scores):.2f}, "
                           f"std={np.std(scores):.2f}, "
                           f"n={len(scores)}")
        
        # Best/worst ideas
        if self.all_results:
            best = max(self.all_results, key=lambda r: r.overall_score)
            worst = min(self.all_results, key=lambda r: r.overall_score)
            lines.append(f"\n  Best:  {best.overall_score:.2f} by {best.persona.value}")
            lines.append(f"         config: {best.idea.source_config}")
            lines.append(f"  Worst: {worst.overall_score:.2f} by {worst.persona.value}")
            lines.append(f"         config: {worst.idea.source_config}")
        
        return "\n".join(lines)
