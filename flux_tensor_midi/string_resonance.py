"""
Coupled string resonance simulator.
Physics-based model of guitar strings, bridge coupling, impedance, sustain, and sympathetic resonance.

Models:
- Individual string harmonics with impedance-dependent damping
- Bridge coupling via Kuramoto-like energy transfer
- Headstock impedance and mass loading effects
- Sustain vs resonance inversion at different bridge impedances

References:
- String impedance: Z = sqrt(T * mu) where T=tension, mu=linear density
- Kuramoto coupling: d(theta)/dt = omega + K * sum(sin(theta_j - theta_i))
- Sympathetic resonance driven by harmonic frequency matching
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum


class BoundaryType(Enum):
    FIXED = "fixed"        # perfect reflection (ideal nut/bridge)
    IMPEDANCE = "impedance" # finite impedance boundary


@dataclass
class GuitarString:
    """A single vibrating string with full harmonic content."""
    name: str
    fundamental_hz: float       # open string frequency
    length_m: float = 0.648     # scale length in meters
    linear_density: float = 0.001  # kg/m
    tension: float = 70.0       # Newtons
    damping: float = 0.01       # decay rate per second
    fret: int = 0               # 0 = open
    epsilon: float = 0.0        # vibrato/bend amount (0 = exact fret, 1 = slide)
    n_harmonics: int = 12       # number of harmonics to simulate

    def __post_init__(self):
        # Recalculate tension from fundamental frequency and string properties
        # f = (1 / 2L) * sqrt(T / mu)  =>  T = (2Lf)^2 * mu
        self.tension = (2 * self.length_m * self.fundamental_hz) ** 2 * self.linear_density

    @property
    def effective_length(self) -> float:
        """Length after fretting."""
        if self.fret == 0:
            return self.length_m
        return self.length_m / (2 ** (self.fret / 12))

    @property
    def fretted_frequency(self) -> float:
        """Frequency at current fret with epsilon applied."""
        base = self.fundamental_hz * (2 ** (self.fret / 12))
        # epsilon = vibrato/bend: adds frequency deviation
        return base * (1 + self.epsilon * 0.03)  # ±3% max deviation

    @property
    def harmonics(self) -> np.ndarray:
        """Angular frequencies of all harmonics."""
        return 2 * np.pi * self.fretted_frequency * np.arange(1, self.n_harmonics + 1)

    @property
    def harmonic_amplitudes(self) -> np.ndarray:
        """Amplitude of each harmonic (1/n for ideal pluck)."""
        return 1.0 / np.arange(1, self.n_harmonics + 1)

    @property
    def impedance(self) -> float:
        """Characteristic impedance of the string."""
        return np.sqrt(self.tension * self.linear_density)

    def energy(self, amplitudes: np.ndarray) -> float:
        """Total vibrational energy in the string."""
        return 0.5 * self.linear_density * self.length_m * np.sum(
            amplitudes ** 2 * self.harmonics ** 2
        )

    def sustain_time(self, boundary_impedance: float) -> float:
        """Time for amplitude to decay to 1/e of initial."""
        # Decay rate = string damping + energy leak through boundaries
        leak_rate = self.impedance / (boundary_impedance + self.impedance) * self.damping * 10
        total_damping = self.damping + leak_rate
        return 1.0 / total_damping if total_damping > 0 else float('inf')

    def pluck_amplitudes(self, position: float = 0.2, velocity: float = 1.0) -> np.ndarray:
        """Calculate harmonic amplitudes for a pluck at given position.

        Args:
            position: fraction of length (0=bridge, 1=nut)
            velocity: pluck strength (0-1)
        """
        amps = np.zeros(self.n_harmonics)
        for n in range(1, self.n_harmonics + 1):
            amps[n - 1] = abs(np.sin(n * np.pi * position)) / n
        return amps * velocity

    def wave_speed(self) -> float:
        """Transverse wave speed on the string."""
        return np.sqrt(self.tension / self.linear_density)

    def wavelength(self, harmonic_number: int = 1) -> float:
        """Wavelength of the nth harmonic."""
        return 2 * self.effective_length / harmonic_number


@dataclass
class Bridge:
    """Coupling medium between strings. Controls resonance vs sustain trade-off."""
    impedance: float = 100.0    # higher = more sustain, less resonance
    mass: float = 0.1           # kg
    resonance_freq: float = 200.0  # natural frequency of the bridge itself
    bridge_damping: float = 0.5

    @property
    def coupling_strength(self) -> float:
        """K parameter in Kuramoto model. Inverse of impedance."""
        return 1.0 / self.impedance

    def transfer_efficiency(self, source: GuitarString, target: GuitarString) -> float:
        """Fraction of energy that transfers from source to target through bridge."""
        # Impedance matching: max transfer when Z_bridge matches string impedances
        z_match = (4 * source.impedance * target.impedance /
                   (source.impedance + target.impedance + self.impedance) ** 2)
        # Frequency matching: harmonics of source near fundamentals of target
        freq_match = 0.0
        for sh in source.harmonics[:6]:
            for th in target.harmonics[:3]:
                delta = abs(sh - th)
                bandwidth = 2 * np.pi * 5  # 5 Hz bandwidth
                freq_match += np.exp(-delta ** 2 / (2 * bandwidth ** 2))
        freq_match = min(freq_match / 3, 1.0)  # normalize
        return z_match * freq_match

    def resonance_gain(self, frequency: float) -> float:
        """Gain at a given frequency from bridge resonance."""
        omega = 2 * np.pi * frequency
        omega_0 = 2 * np.pi * self.resonance_freq
        # Simple harmonic oscillator response
        denom = np.sqrt((omega_0 ** 2 - omega ** 2) ** 2 + (self.bridge_damping * omega) ** 2)
        if denom < 1e-10:
            return 1.0
        return omega_0 / denom


@dataclass
class Headstock:
    """Headstock with optional mass loading."""
    base_mass: float = 0.3      # kg
    added_mass: float = 0.0     # extra mass (the trick)
    stiffness: float = 1e6      # N/m

    @property
    def total_mass(self) -> float:
        return self.base_mass + self.added_mass

    @property
    def impedance(self) -> float:
        """Mechanical impedance of the headstock."""
        return np.sqrt(self.stiffness * self.total_mass)

    def resonance_frequency(self) -> float:
        """Natural frequency of the headstock assembly."""
        return np.sqrt(self.stiffness / self.total_mass) / (2 * np.pi)


class KuramotoCoupling:
    """Kuramoto model for phase synchronization of coupled oscillators."""

    def __init__(self, n_oscillators: int, coupling_strength: float = 0.1):
        self.n = n_oscillators
        self.K = coupling_strength
        self.phases = np.random.uniform(0, 2 * np.pi, n_oscillators)
        self.natural_frequencies = np.zeros(n_oscillators)

    def set_frequencies(self, frequencies: np.ndarray):
        """Set natural frequencies for all oscillators."""
        self.natural_frequencies = frequencies.copy()

    def order_parameter(self) -> float:
        """Kuramoto order parameter r in [0,1]. 1 = full sync."""
        return abs(np.mean(np.exp(1j * self.phases)))

    def step(self, dt: float):
        """Advance one timestep."""
        # d(theta_i)/dt = omega_i + (K/N) * sum_j sin(theta_j - theta_i)
        phase_diffs = self.phases[np.newaxis, :] - self.phases[:, np.newaxis]
        coupling = np.sum(np.sin(phase_diffs), axis=1) / self.n
        d_phase = self.natural_frequencies + self.K * coupling
        self.phases += d_phase * dt
        self.phases %= (2 * np.pi)

    def simulate(self, duration: float, dt: float = 0.001) -> Tuple[np.ndarray, np.ndarray]:
        """Run Kuramoto simulation, return times and order parameters."""
        steps = int(duration / dt)
        times = np.linspace(0, duration, steps)
        r_values = np.zeros(steps)

        for i in range(steps):
            self.step(dt)
            r_values[i] = self.order_parameter()

        return times, r_values


class Guitar:
    """Full guitar model with coupled strings."""

    def __init__(self, bridge: Optional[Bridge] = None, headstock: Optional[Headstock] = None):
        self.strings: Dict[str, GuitarString] = {}
        self.bridge = bridge or Bridge()
        self.headstock = headstock or Headstock()
        self.amplitudes: Dict[str, np.ndarray] = {}  # current harmonic amplitudes
        self.time: float = 0.0

        # Standard tuning by default
        self.add_string(GuitarString(name="E2", fundamental_hz=82.41))
        self.add_string(GuitarString(name="A2", fundamental_hz=110.00))
        self.add_string(GuitarString(name="D3", fundamental_hz=146.83))
        self.add_string(GuitarString(name="G3", fundamental_hz=196.00))
        self.add_string(GuitarString(name="B3", fundamental_hz=246.94))
        self.add_string(GuitarString(name="E4", fundamental_hz=329.63))

    def add_string(self, string: GuitarString):
        """Add or replace a string on the guitar."""
        self.strings[string.name] = string
        self.amplitudes[string.name] = string.harmonic_amplitudes.copy()
        self._coupling_cache = None

    def remove_string(self, name: str):
        """Remove a string by name."""
        if name in self.strings:
            del self.strings[name]
            del self.amplitudes[name]
            self._coupling_cache = None

    def pluck(self, name: str, velocity: float = 1.0, position: float = 0.2):
        """Pluck a string. position = fraction of length (0=bridge, 1=nut)."""
        if name not in self.strings:
            return
        s = self.strings[name]
        self.amplitudes[name] = s.pluck_amplitudes(position, velocity)
        self.time = 0.0

    def fret_string(self, name: str, fret: int):
        """Set the fret position for a string."""
        if name in self.strings:
            self.strings[name].fret = fret
            self.amplitudes[name] = self.strings[name].harmonic_amplitudes.copy()

    # Precomputed coupling matrices (rebuilt when strings change)
    _coupling_cache: dict = None

    def _rebuild_coupling_cache(self):
        """Precompute coupling efficiencies between all string pairs."""
        names = list(self.strings.keys())
        n = len(names)
        cache = {}
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                src = self.strings[names[i]]
                tgt = self.strings[names[j]]
                eff = self.bridge.transfer_efficiency(src, tgt)
                # Precompute harmonic match matrix (6x6)
                src_h = src.harmonics[:6]
                tgt_h = tgt.harmonics[:6]
                diff = src_h[:, None] - tgt_h[None, :]
                match = np.exp(-diff ** 2 / (2 * (2 * np.pi * 5) ** 2))
                match[np.abs(diff) > 2 * np.pi * 10] = 0
                cache[(names[i], names[j])] = (eff, match)
        self._coupling_cache = cache

    def step(self, dt: float = 0.001):
        """Advance simulation by dt seconds."""
        if self._coupling_cache is None:
            self._rebuild_coupling_cache()

        # 1. Natural decay of each string
        for name, s in self.strings.items():
            decay = np.exp(-s.damping * dt)
            boundary_leak = (s.impedance /
                             (s.impedance + self.headstock.impedance + self.bridge.impedance))
            total_decay = decay * (1 - boundary_leak * dt * 10)
            self.amplitudes[name] *= max(total_decay, 0)

        # 2. Coupling through bridge (vectorized)
        K = self.bridge.coupling_strength
        new_amps = {name: amps.copy() for name, amps in self.amplitudes.items()}

        for src_name, src in self.strings.items():
            src_amps = self.amplitudes[src_name]
            for tgt_name, tgt in self.strings.items():
                if src_name == tgt_name:
                    continue

                eff, match = self._coupling_cache[(src_name, tgt_name)]
                transfer = src_amps[:6] * eff * K * dt
                # Matrix multiply: (6,) @ (6,6) -> (6,)
                driving = match.T @ transfer * 0.1
                new_amps[tgt_name][:6] += driving

        self.amplitudes = new_amps
        self.time += dt

    def simulate(self, duration: float = 2.0, dt: float = 0.005) -> Dict:
        """Run full simulation and return results."""
        history = {name: [] for name in self.strings}
        times = []

        steps = int(duration / dt)
        for i in range(steps):
            self.step(dt)
            if i % 10 == 0:  # sample every 10ms
                times.append(self.time)
                for name in self.strings:
                    total_amp = np.sum(self.amplitudes[name] ** 2)
                    history[name].append(total_amp)

        return {
            'times': times,
            'amplitudes': history,
            'duration': duration
        }

    def measure_sustain(self, name: str) -> float:
        """Time for string to decay to 1/e of initial amplitude (theoretical)."""
        if name not in self.strings:
            return 0.0
        s = self.strings[name]
        return s.sustain_time(self.headstock.impedance + self.bridge.impedance)

    def measure_resonance(self, src_name: str, tgt_name: str) -> float:
        """How strongly does src drive tgt sympathetically?"""
        if src_name not in self.strings or tgt_name not in self.strings:
            return 0.0
        return self.bridge.transfer_efficiency(self.strings[src_name], self.strings[tgt_name])

    def sympathetic_response(self, pluck_name: str, duration: float = 2.0) -> Dict[str, float]:
        """Pluck one string, measure response of all others."""
        self.pluck(pluck_name)
        result = self.simulate(duration)

        response = {}
        for name in self.strings:
            if name == pluck_name:
                continue
            max_amp = max(result['amplitudes'][name]) if result['amplitudes'][name] else 0
            response[name] = max_amp

        return response

    def measure_sustain_empirical(self, name: str, duration: float = 10.0) -> float:
        """Measure sustain by simulation: time to reach 1/e of peak."""
        self.pluck(name, velocity=1.0)
        result = self.simulate(duration)

        amps = result['amplitudes'][name]
        if not amps:
            return 0.0

        peak = amps[0]
        threshold = peak / np.e
        for i, amp in enumerate(amps):
            if amp < threshold:
                return result['times'][i]
        return duration  # didn't decay enough

    def total_energy(self) -> float:
        """Total energy in all strings."""
        total = 0.0
        for name, s in self.strings.items():
            total += s.energy(self.amplitudes[name])
        return total

    def string_energy(self, name: str) -> float:
        """Energy in a specific string."""
        if name not in self.strings:
            return 0.0
        return self.strings[name].energy(self.amplitudes[name])

    def to_audio(self, duration: float = 2.0, sample_rate: int = 44100) -> np.ndarray:
        """Generate audio waveform from all strings."""
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.zeros_like(t)

        for name, s in self.strings.items():
            amps = self.amplitudes[name]
            for n, (amp, omega) in enumerate(zip(amps, s.harmonics)):
                if amp < 0.001:
                    continue
                decay = np.exp(-s.damping * t)
                audio += amp * np.sin(omega * t) * decay * 0.1

        # Normalize
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio /= peak
        return audio

    def frequency_response(self, freq_range: Tuple[float, float] = (50, 2000),
                           n_points: int = 500) -> Tuple[np.ndarray, np.ndarray]:
        """Compute frequency response showing resonance peaks of all strings."""
        freqs = np.linspace(freq_range[0], freq_range[1], n_points)
        response = np.zeros(n_points)

        for name, s in self.strings.items():
            amps = self.amplitudes[name]
            for n, (amp, omega) in enumerate(zip(amps, s.harmonics)):
                hz = omega / (2 * np.pi)
                # Each harmonic is a narrow peak
                sigma = 2.0  # Hz width
                response += amp * np.exp(-(freqs - hz) ** 2 / (2 * sigma ** 2))

        return freqs, response

    def reset(self):
        """Reset all string amplitudes to resting state."""
        for name, s in self.strings.items():
            self.amplitudes[name] = s.harmonic_amplitudes.copy()
        self.time = 0.0


def experiment_sustain_vs_resonance():
    """Run the key experiment: impedance sweep showing sustain-resonance inversion."""
    results = []

    for bridge_impedance in [10, 20, 50, 100, 200, 500, 1000]:
        bridge = Bridge(impedance=bridge_impedance)
        guitar = Guitar(bridge=bridge)
        guitar.pluck("E2", velocity=1.0)

        result = guitar.simulate(duration=5.0)

        # Measure sustain of plucked string
        e2_amps = result['amplitudes']['E2']
        sustain_time = 0
        for i, amp in enumerate(e2_amps):
            if amp < e2_amps[0] / np.e:
                sustain_time = result['times'][i]
                break

        # Measure resonance of sympathetic strings
        max_sympathetic = max(
            max(result['amplitudes'][name]) if result['amplitudes'][name] else 0
            for name in guitar.strings if name != 'E2'
        )

        results.append({
            'bridge_impedance': bridge_impedance,
            'sustain_seconds': sustain_time,
            'max_sympathetic': max_sympathetic
        })
        print(f"Z_bridge={bridge_impedance:4d}: sustain={sustain_time:.2f}s, "
              f"sympathetic={max_sympathetic:.6f}")

    return results


def experiment_headstock_mass():
    """Run the headstock mass experiment."""
    results = []

    for added_mass in [0, 0.1, 0.3, 0.5, 1.0, 2.0]:
        headstock = Headstock(added_mass=added_mass)
        guitar = Guitar(headstock=headstock)
        guitar.pluck("E2", velocity=1.0)

        result = guitar.simulate(duration=5.0)

        e2_amps = result['amplitudes']['E2']
        sustain_time = 0
        for i, amp in enumerate(e2_amps):
            if amp < e2_amps[0] / np.e:
                sustain_time = result['times'][i]
                break

        results.append({
            'added_mass_kg': added_mass,
            'headstock_impedance': headstock.impedance,
            'sustain_seconds': sustain_time
        })
        print(f"Mass={added_mass:.1f}kg: Z_head={headstock.impedance:.0f}, "
              f"sustain={sustain_time:.2f}s")

    return results


def experiment_kuramoto_sync(n_strings: int = 6, coupling: float = 0.5,
                             duration: float = 5.0) -> Dict:
    """Demonstrate Kuramoto synchronization of guitar string phases."""
    std_tuning = [82.41, 110.00, 146.83, 196.00, 246.94, 329.63]
    frequencies = np.array(std_tuning[:n_strings]) * 2 * np.pi

    kuramoto = KuramotoCoupling(n_strings, coupling_strength=coupling)
    kuramoto.set_frequencies(frequencies)

    times, r_values = kuramoto.simulate(duration)

    return {
        'times': times,
        'order_parameter': r_values,
        'mean_sync': np.mean(r_values),
        'final_sync': r_values[-1],
        'coupling': coupling
    }


def experiment_coupling_sweep() -> List[Dict]:
    """Sweep coupling strength and measure synchronization."""
    results = []
    for K in np.linspace(0.01, 2.0, 20):
        result = experiment_kuramoto_sync(coupling=K, duration=3.0)
        results.append({
            'coupling_K': K,
            'mean_sync': result['mean_sync'],
            'final_sync': result['final_sync']
        })
    return results


def experiment_fret_positions(string_name: str = "E2") -> Dict:
    """Analyze how fretting changes frequency, impedance, and sustain."""
    base_string = GuitarString(name=string_name, fundamental_hz=82.41)
    results = []

    for fret in range(0, 13):
        test_string = GuitarString(
            name=f"{string_name}_fret{fret}",
            fundamental_hz=82.41,
            fret=fret
        )
        results.append({
            'fret': fret,
            'frequency': test_string.fretted_frequency,
            'effective_length': test_string.effective_length,
            'impedance': test_string.impedance,
            'sustain': test_string.sustain_time(100.0)
        })

    return {'string': string_name, 'frets': results}


def experiment_pluck_position() -> Dict:
    """Analyze how pluck position affects harmonic content."""
    guitar = Guitar()
    results = []

    for pos in np.linspace(0.05, 0.95, 20):
        amps = guitar.strings["E2"].pluck_amplitudes(position=pos, velocity=1.0)
        results.append({
            'position': pos,
            'fundamental_amp': amps[0],
            'total_energy': np.sum(amps ** 2),
            'harmonic richness': np.sum(amps[1:] ** 2) / max(np.sum(amps ** 2), 1e-10),
            'n_active_harmonics': int(np.sum(amps > 0.01))
        })

    return {'positions': results}


def experiment_vibrato(epsilon_values: Optional[List[float]] = None) -> Dict:
    """Analyze vibrato/bend effect on frequency."""
    if epsilon_values is None:
        epsilon_values = np.linspace(0, 1, 20).tolist()

    results = []
    for eps in epsilon_values:
        s = GuitarString(name="E2", fundamental_hz=82.41, epsilon=eps)
        results.append({
            'epsilon': eps,
            'frequency': s.fretted_frequency,
            'deviation_cents': 1200 * np.log2(s.fretted_frequency / 82.41)
        })

    return {'vibrato': results}


def run_all_experiments(output_dir: str = ".") -> Dict:
    """Run all experiments and save results."""
    import json
    import os

    os.makedirs(output_dir, exist_ok=True)
    all_results = {}

    print("=" * 60)
    print("EXPERIMENT 1: Sustain vs Resonance (Bridge Impedance Sweep)")
    print("=" * 60)
    r1 = experiment_sustain_vs_resonance()
    all_results['sustain_vs_resonance'] = r1

    print("\n" + "=" * 60)
    print("EXPERIMENT 2: Headstock Mass Effect on Sustain")
    print("=" * 60)
    r2 = experiment_headstock_mass()
    all_results['headstock_mass'] = r2

    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Kuramoto Synchronization")
    print("=" * 60)
    r3 = experiment_kuramoto_sync()
    print(f"Mean sync: {r3['mean_sync']:.4f}, Final sync: {r3['final_sync']:.4f}")
    all_results['kuramoto_sync'] = {
        'mean_sync': r3['mean_sync'],
        'final_sync': r3['final_sync']
    }

    print("\n" + "=" * 60)
    print("EXPERIMENT 4: Fret Position Analysis")
    print("=" * 60)
    r4 = experiment_fret_positions()
    for f in r4['frets']:
        print(f"  Fret {f['fret']:2d}: {f['frequency']:7.2f} Hz, "
              f"L={f['effective_length']:.3f}m, sustain={f['sustain']:.2f}s")
    all_results['fret_positions'] = r4

    print("\n" + "=" * 60)
    print("EXPERIMENT 5: Pluck Position Analysis")
    print("=" * 60)
    r5 = experiment_pluck_position()
    all_results['pluck_position'] = r5

    print("\n" + "=" * 60)
    print("EXPERIMENT 6: Vibrato/Bend Analysis")
    print("=" * 60)
    r6 = experiment_vibrato()
    all_results['vibrato'] = r6

    # Save results
    results_path = os.path.join(output_dir, "experiment_results.json")
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nAll results saved to {results_path}")

    return all_results
