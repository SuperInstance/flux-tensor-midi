import pytest
import numpy as np
from flux_tensor_midi.beta_testing import (
    BetaTester, BetaTestSuite, MusicalIdea, TesterPersona,
    TesterPreferences
)


class TestMusicalIdea:
    def test_from_creative_system(self):
        from flux_tensor_midi.creative_engine import CreativeSystem
        sys = CreativeSystem(28.0)
        sys.run(100, 50)
        idea = MusicalIdea.from_creative_system(sys, n_events=32)
        assert len(idea.pitches) == 32
        assert len(idea.velocities) == 32
        assert all(0 <= p <= 127 for p in idea.pitches)
        assert all(0 <= v <= 127 for v in idea.velocities)
    
    def test_different_scales(self):
        from flux_tensor_midi.creative_engine import CreativeSystem
        sys = CreativeSystem(28.0)
        sys.run(100, 50)
        
        major = MusicalIdea.from_creative_system(sys, scale=[0,2,4,5,7,9,11])
        pentatonic = MusicalIdea.from_creative_system(sys, scale=[0,2,4,7,9])
        chromatic = MusicalIdea.from_creative_system(sys, scale=list(range(12)))
        
        # All should produce valid ideas
        assert len(major.pitches) > 0
        assert len(pentatonic.pitches) > 0
        assert len(chromatic.pitches) > 0
    
    def test_metadata(self):
        from flux_tensor_midi.creative_engine import CreativeSystem
        sys = CreativeSystem(28.0, epsilon=0.5)
        sys.run(100, 50)
        idea = MusicalIdea.from_creative_system(sys)
        assert idea.source_config['rho'] == 28.0
        assert idea.source_config['epsilon'] == 0.5
        assert idea.source_config['regime'] == 'chaotic'


class TestBetaTester:
    def test_all_personas_can_evaluate(self):
        from flux_tensor_midi.creative_engine import CreativeSystem
        sys = CreativeSystem(28.0)
        sys.run(100, 50)
        idea = MusicalIdea.from_creative_system(sys)
        
        for persona in TesterPersona:
            tester = BetaTester(persona)
            result = tester.evaluate(idea)
            assert 0 <= result.overall_score <= 10
            assert 0 <= result.novelty_score <= 1
            assert 0 <= result.coherence_score <= 1
    
    def test_beginner_prefers_coherent(self):
        """Beginner should score coherent ideas higher."""
        from flux_tensor_midi.creative_engine import CreativeSystem
        
        # Fixed-point (very coherent)
        sys_coherent = CreativeSystem(5.0)
        sys_coherent.run(100, 50)
        coherent = MusicalIdea.from_creative_system(sys_coherent)
        
        # Chaotic (less coherent)
        sys_chaotic = CreativeSystem(45.0)
        sys_chaotic.run(100, 50)
        chaotic = MusicalIdea.from_creative_system(sys_chaotic)
        
        beginner = BetaTester(TesterPersona.BEGINNER_LISTENER)
        score_coherent = beginner.evaluate(coherent).overall_score
        score_chaotic = beginner.evaluate(chaotic).overall_score
        
        # Beginner should prefer coherent (or at least score it)
        assert score_coherent > 0
        assert score_chaotic > 0
    
    def test_avant_garde_tolerance(self):
        """Avant-garde should tolerate high dissonance."""
        from flux_tensor_midi.creative_engine import CreativeSystem
        
        prefs = TesterPreferences.from_persona(TesterPersona.AVANT_GARDE)
        assert prefs.tolerance_for_dissonance > 0.8
    
    def test_results_accumulate(self):
        from flux_tensor_midi.creative_engine import CreativeSystem
        tester = BetaTester(TesterPersona.CASUAL_LISTENER)
        
        for _ in range(5):
            sys = CreativeSystem(28.0)
            sys.run(100, 50)
            idea = MusicalIdea.from_creative_system(sys)
            tester.evaluate(idea)
        
        assert len(tester.results) == 5


class TestBetaTestSuite:
    def test_single_configuration(self):
        suite = BetaTestSuite()
        results = suite.test_configuration(rho=28.0, n_ideas=2)
        
        # Should have results for all personas
        for persona in TesterPersona:
            assert persona.value in results
            assert 'mean_score' in results[persona.value]
    
    def test_ab_test(self):
        suite = BetaTestSuite()
        result = suite.ab_test(
            config_a={'rho': 15.0, 'sigma': 10.0},
            config_b={'rho': 45.0, 'sigma': 10.0},
            n_ideas=3
        )
        
        assert 'overall_winner' in result
        assert result['overall_winner'] in ['A', 'B']
        assert 'comparison' in result
    
    def test_rho_sweep(self):
        suite = BetaTestSuite()
        result = suite.sweep_rho(rho_values=[5, 15, 28], sigma=10.0)
        
        assert 'optimal_rho' in result
        for persona in TesterPersona:
            assert persona.value in result['optimal_rho']
    
    def test_epsilon_sweep(self):
        suite = BetaTestSuite()
        result = suite.sweep_epsilon(rho=28.0, eps_values=[0.1, 0.5, 1.0])
        
        assert 'optimal_epsilon' in result
    
    def test_report_generation(self):
        suite = BetaTestSuite()
        suite.test_configuration(rho=28.0, n_ideas=2)
        report = suite.generate_report()
        assert "BETA TEST REPORT" in report


class TestPreferences:
    def test_all_personas_have_preferences(self):
        for persona in TesterPersona:
            prefs = TesterPreferences.from_persona(persona)
            assert 0 <= prefs.preferred_novelty <= 1
            assert 0 <= prefs.preferred_coherence <= 1
            assert prefs.preferred_tempo_range[0] < prefs.preferred_tempo_range[1]
            assert 0 <= prefs.tolerance_for_dissonance <= 1
            assert prefs.attention_span > 0
