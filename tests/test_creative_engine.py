import pytest
import numpy as np
from flux_tensor_midi.creative_engine import (
    Regime, QualityMetrics, CreativeSystem, 
    CreativeNetwork, CreativeThermostat, CouplingTopology
)


class TestRegime:
    def test_fixed_point(self):
        assert Regime.from_rho(1.0) == Regime.FIXED_POINT
    
    def test_periodic(self):
        assert Regime.from_rho(15.0) == Regime.PERIODIC
    
    def test_chaotic(self):
        assert Regime.from_rho(28.0) == Regime.CHAOTIC
    
    def test_boundary(self):
        assert Regime.from_rho(24.73) == Regime.PERIODIC
        assert Regime.from_rho(24.74) == Regime.CHAOTIC
    
    def test_epsilon_ordering(self):
        assert (Regime.FIXED_POINT.optimal_epsilon > 
                Regime.PERIODIC.optimal_epsilon > 
                Regime.CHAOTIC.optimal_epsilon)


class TestSoftSnap:
    def test_full_snap(self):
        assert CreativeSystem.soft_snap(2.7, 0.0) == 3.0
        assert CreativeSystem.soft_snap(2.3, 0.0) == 2.0
    
    def test_no_snap(self):
        assert abs(CreativeSystem.soft_snap(2.7, 1.0) - 2.7) < 1e-10
    
    def test_half_snap(self):
        assert abs(CreativeSystem.soft_snap(2.6, 0.5) - 2.8) < 1e-10


class TestSigmoid:
    def test_midpoint(self):
        assert abs(CreativeSystem.sigmoid(0.5, 1.0, 0.5) - 0.5) < 1e-10
    
    def test_extremes(self):
        assert CreativeSystem.sigmoid(-10, 1.0, 0.5) < 0.01
        assert CreativeSystem.sigmoid(10, 1.0, 0.5) > 0.99


class TestKuramoto:
    def test_synced(self):
        phases = np.zeros(10)
        assert CreativeSystem.kuramoto_order(phases) > 0.99
    
    def test_random(self):
        phases = np.linspace(0, 2*np.pi, 100)
        assert CreativeSystem.kuramoto_order(phases) < 0.3


class TestCreativeSystem:
    def test_step_changes_state(self):
        sys = CreativeSystem(28.0)
        initial = sys.state.copy()
        sys.step()
        assert not np.allclose(sys.state, initial)
    
    def test_chaotic_has_diversity(self):
        sys = CreativeSystem(28.0)
        sys.run(5000, 1000)
        assert sys.diversity() > 1.0
    
    def test_fixed_point_low_diversity(self):
        sys = CreativeSystem(1.0)
        sys.run(5000, 1000)
        assert sys.diversity() < 1.0
    
    def test_regime_detection(self):
        assert CreativeSystem(28.0).regime == Regime.CHAOTIC
        assert CreativeSystem(15.0).regime == Regime.PERIODIC
        assert CreativeSystem(1.0).regime == Regime.FIXED_POINT


class TestQuality:
    def test_constant_signal(self):
        outputs = np.ones(100)
        q = QualityMetrics.from_outputs(outputs)
        assert q.novelty == 0.0
        assert q.quality == 0.0
    
    def test_varying_signal(self):
        sys = CreativeSystem(28.0)
        sys.run(1000, 500)
        q = sys.quality()
        assert q.novelty > 0.0


class TestNetwork:
    def test_creation(self):
        net = CreativeNetwork([0.1, 0.5, 0.9])
        assert len(net.agents) == 3
    
    def test_hierarchical_coupling(self):
        net = CreativeNetwork([0.1, 0.5, 0.9], CouplingTopology.HIERARCHICAL)
        # Beginner receives from expert
        assert net.coupling_matrix[0, 2] > 0
        # Expert doesn't receive from beginner
        assert net.coupling_matrix[2, 0] == 0
    
    def test_network_runs(self):
        net = CreativeNetwork([0.1, 0.5, 0.9])
        net.run(500)
        assert all(len(a.outputs) == 500 for a in net.agents)
    
    def test_no_coupling(self):
        net = CreativeNetwork([0.1, 0.5], CouplingTopology.NONE)
        assert np.all(net.coupling_matrix == 0)


class TestThermostat:
    def test_adapts(self):
        thermo = CreativeThermostat(28.0, 5.0)
        initial = thermo.system.epsilon
        thermo.run_thermostat(20)
        assert len(thermo.history) == 20
    
    def test_converges(self):
        thermo = CreativeThermostat(28.0, 5.0)
        thermo.run_thermostat(50)
        eps = thermo.converged_epsilon()
        assert 0.01 <= eps <= 2.0
