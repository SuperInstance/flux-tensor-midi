"""
Creative Dynamics Engine — Lorenz-based creative system with:
- Regime detection (fixed-point, periodic, chaotic)
- Adaptive ε (creative thermostat)
- Quality metrics (novelty × coherence)
- Coupled networks (hierarchical, ring, etc.)
- Soft snap, sigmoid, Kuramoto sync
- Bayesian interpretation (constraints = priors)
"""

import numpy as np
from enum import Enum
from typing import List, Tuple, Optional, Dict


class Regime(Enum):
    """The three creative regimes."""
    FIXED_POINT = "fixed_point"  # ρ < 5: rigid, needs noise
    PERIODIC = "periodic"        # 5 < ρ < 24.74: SR active
    CHAOTIC = "chaotic"          # ρ > 24.74: strange attractor
    
    @classmethod
    def from_rho(cls, rho: float) -> 'Regime':
        if rho < 5.0:
            return cls.FIXED_POINT
        elif rho < 24.74:
            return cls.PERIODIC
        return cls.CHAOTIC
    
    @property
    def optimal_epsilon(self) -> float:
        return {
            Regime.FIXED_POINT: 1.5,
            Regime.PERIODIC: 0.5,
            Regime.CHAOTIC: 0.2,
        }[self]


class QualityMetrics:
    """Quality = novelty × coherence."""
    def __init__(self, novelty: float, coherence: float):
        self.novelty = novelty
        self.coherence = coherence
        self.quality = novelty * coherence
    
    @classmethod
    def from_outputs(cls, outputs: np.ndarray) -> 'QualityMetrics':
        if len(outputs) < 2:
            return cls(0.0, 0.0)
        
        novelty = float(np.std(outputs))
        
        # Spectral coherence
        fft = np.abs(np.fft.rfft(outputs))
        fft_norm = fft / (fft.sum() + 1e-10)
        log_fft = np.log(fft_norm + 1e-10)
        geo_mean = np.exp(np.mean(log_fft))
        arith_mean = np.mean(fft_norm)
        flatness = geo_mean / (arith_mean + 1e-10)
        coherence = 1.0 - flatness
        
        return cls(novelty, coherence)


class CreativeSystem:
    """A single Lorenz creative system."""
    
    def __init__(self, rho: float = 28.0, sigma: float = 10.0, 
                 beta: float = 8/3, dt: float = 0.01, epsilon: float = None):
        self.sigma = sigma
        self.rho = rho
        self.beta = beta
        self.dt = dt
        self.state = np.array([0.1, 0.1, 0.1])
        self.epsilon = epsilon if epsilon is not None else self.regime.optimal_epsilon
        self.outputs: List[float] = []
    
    @property
    def regime(self) -> Regime:
        return Regime.from_rho(self.rho)
    
    def step(self) -> float:
        """RK4 integration step."""
        x, y, z = self.state
        s, r, b, dt = self.sigma, self.rho, self.beta, self.dt
        
        def f(state):
            x, y, z = state
            return np.array([s*(y-x), x*(r-z)-y, x*y-b*z])
        
        k1 = f(self.state)
        k2 = f(self.state + 0.5*dt*k1)
        k3 = f(self.state + 0.5*dt*k2)
        k4 = f(self.state + dt*k3)
        
        self.state += (dt/6) * (k1 + 2*k2 + 2*k3 + k4)
        self.outputs.append(float(self.state[0]))
        return float(self.state[0])
    
    def run(self, n_steps: int, discard: int = 0) -> np.ndarray:
        """Run for n_steps, optionally discarding transient."""
        for _ in range(discard):
            self.step()
        self.outputs = []
        for _ in range(n_steps):
            self.step()
        return np.array(self.outputs)
    
    def diversity(self) -> float:
        return float(np.std(self.outputs)) if self.outputs else 0.0
    
    def quality(self) -> QualityMetrics:
        return QualityMetrics.from_outputs(np.array(self.outputs))
    
    @staticmethod
    def soft_snap(x: float, epsilon: float) -> float:
        snapped = round(x)
        return (1 - epsilon) * snapped + epsilon * x
    
    @staticmethod
    def sigmoid(x: float, k: float = 1.0, x0: float = 0.5) -> float:
        return 1.0 / (1.0 + np.exp(-k * (x - x0)))
    
    @staticmethod
    def kuramoto_order(phases: np.ndarray) -> float:
        z = np.mean(np.exp(1j * phases))
        return float(np.abs(z))


class CouplingTopology(Enum):
    NONE = "none"
    HIERARCHICAL = "hierarchical"
    FULLY_CONNECTED = "fully_connected"
    RING = "ring"
    SPARSE = "sparse"


class CreativeNetwork:
    """Network of coupled creative agents."""
    
    def __init__(self, expertises: List[float], 
                 topology: CouplingTopology = CouplingTopology.HIERARCHICAL,
                 coupling_strength: float = 0.01):
        self.agents = [CreativeSystem(rho=1 + e*49) for e in expertises]
        self.expertises = expertises
        self.topology = topology
        self.K = coupling_strength
        self.n = len(expertises)
        self.coupling_matrix = self._build_coupling()
    
    def _build_coupling(self) -> np.ndarray:
        n = self.n
        C = np.zeros((n, n))
        
        if self.topology == CouplingTopology.NONE:
            pass
        
        elif self.topology == CouplingTopology.HIERARCHICAL:
            for i in range(n):
                for j in range(n):
                    if i != j and self.expertises[j] > self.expertises[i]:
                        C[i, j] = self.K
        
        elif self.topology == CouplingTopology.FULLY_CONNECTED:
            C = np.ones((n, n)) * self.K
            np.fill_diagonal(C, 0)
        
        elif self.topology == CouplingTopology.RING:
            for i in range(n):
                C[i, (i+1)%n] = self.K
                C[i, (i-1)%n] = self.K
        
        elif self.topology == CouplingTopology.SPARSE:
            rng = np.random.RandomState(42)
            for i in range(n):
                targets = rng.choice([j for j in range(n) if j != i], min(3, n-1), replace=False)
                for j in targets:
                    C[i, j] = self.K
        
        return C
    
    def step(self) -> np.ndarray:
        outputs = np.array([a.step() for a in self.agents])
        for i in range(self.n):
            signal = sum(self.coupling_matrix[i,j] * (outputs[j] - outputs[i]) 
                        for j in range(self.n))
            self.agents[i].state[0] += signal * self.agents[i].dt
        return outputs
    
    def run(self, n_steps: int):
        for _ in range(n_steps):
            self.step()
    
    def total_quality(self) -> float:
        return sum(a.quality().quality for a in self.agents)
    
    def total_diversity(self) -> float:
        return sum(a.diversity() for a in self.agents)


class CreativeThermostat:
    """Adaptive ε that tracks regime — the creative thermostat."""
    
    def __init__(self, rho: float, target_diversity: float = 5.0, lr: float = 0.01):
        self.system = CreativeSystem(rho)
        self.target = target_diversity
        self.lr = lr
        self.history: List[Tuple[float, float]] = []
    
    def adapt(self) -> float:
        self.system.run(100, 50)
        div = self.system.diversity()
        error = self.target - div
        self.system.epsilon = np.clip(self.system.epsilon + self.lr * error, 0.01, 2.0)
        self.history.append((self.system.epsilon, div))
        return self.system.epsilon
    
    def run_thermostat(self, n_cycles: int):
        for _ in range(n_cycles):
            self.adapt()
    
    def converged_epsilon(self) -> float:
        if not self.history:
            return self.system.epsilon
        recent = [e for e, _ in self.history[-10:]]
        return float(np.mean(recent))
