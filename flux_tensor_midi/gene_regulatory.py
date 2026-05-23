"""
Gene regulatory network simulator using musical consensus.

Maps biological gene regulation concepts to musical composition:
- Genes → musical parameters (pitch, rhythm, dynamics, timbre, form)
- Transcription factors → regulatory interactions between parameters
- Protein concentrations → musical expression levels
- Attractors → emergent genres/styles
- Horizontal gene transfer → cross-genre borrowing

NON-PRE-CALCULABLE: emergent patterns cannot be predicted from individual
genes alone. The network must be simulated to discover attractors, just as
biological networks produce phenotypes that can't be read off the genome.

Usage:
    from flux_tensor_midi.gene_regulatory import GeneRegulatoryNetwork
    grn = GeneRegulatoryNetwork()
    history = grn.simulate(steps=200)
    arrangement = grn.to_music(history)
"""

from __future__ import annotations

import math
import random
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set

from flux_tensor_midi.tracks import Arrangement, Track, MidiEvent


# ---------------------------------------------------------------------------
# Helper: sigmoid activation function (biological motif)
# ---------------------------------------------------------------------------

def _sigmoid(x: float, k: float = 1.0, midpoint: float = 0.5) -> float:
    """Sigmoid with adjustable steepness and midpoint."""
    arg = -k * (x - midpoint)
    # Clamp to avoid overflow
    arg = max(-50.0, min(50.0, arg))
    return 1.0 / (1.0 + math.exp(arg))


def _hill_function(concentration: float, n: float = 2.0, k: float = 0.5) -> float:
    """Hill equation — cooperative binding kinetics.

    Models how multiple transcription factors bind cooperatively.
    n > 1 gives ultrasensitive (switch-like) response.
    """
    cn = concentration ** n
    kn = k ** n
    return cn / (cn + kn) if (cn + kn) > 0 else 0.0


# ---------------------------------------------------------------------------
# MusicalGene
# ---------------------------------------------------------------------------

@dataclass
class MusicalGene:
    """A gene that produces musical output, regulated by other genes' outputs.

    Each gene has:
    - activators: gene names whose products increase this gene's expression
    - suppressors: gene names whose products decrease this gene's expression
    - threshold: activation threshold (like a promoter affinity)
    - output_type: what kind of musical parameter this gene controls
    - basal_rate: baseline expression level (leaky transcription)

    The expression function uses Hill-equation kinetics for activation
    and competitive inhibition for suppression — standard systems biology
    models, but the *outputs* are musical.
    """

    name: str
    activators: List[str] = field(default_factory=list)
    suppressors: List[str] = field(default_factory=list)
    threshold: float = 0.5
    output_type: str = "pitch"  # pitch, rhythm, dynamics, timbre, form
    basal_rate: float = 0.1
    hill_coefficient: float = 2.0
    decay_rate: float = 0.05
    max_expression: float = 1.0
    noise_amplitude: float = 0.02

    def express(self, protein_concentrations: Dict[str, float]) -> float:
        """Calculate expression level based on regulator concentrations.

        Models transcription factor binding using Hill functions for
        activators and competitive inhibition for suppressors. This is
        the core regulatory logic — like a promoter region with multiple
        transcription factor binding sites.

        Args:
            protein_concentrations: current concentration of each gene product

        Returns:
            New expression level (production rate) for this gene
        """
        # Activation: sum of Hill functions for each activator
        activation = 0.0
        for act_name in self.activators:
            conc = protein_concentrations.get(act_name, 0.0)
            activation += _hill_function(conc, n=self.hill_coefficient, k=self.threshold)

        # Normalize by number of activators (or cap at 1.0)
        if self.activators:
            activation = min(activation / max(len(self.activators) ** 0.5, 1.0), 1.5)

        # Suppression: multiplicative inhibition
        suppression = 1.0
        for sup_name in self.suppressors:
            conc = protein_concentrations.get(sup_name, 0.0)
            # Inhibition: higher concentration → more suppression
            inhibition = _hill_function(conc, n=self.hill_coefficient, k=self.threshold)
            suppression *= (1.0 - 0.8 * inhibition)

        suppression = max(suppression, 0.05)  # never fully silenced by suppression alone

        # Combined expression: basal + activation, modulated by suppression
        raw_expression = (self.basal_rate + activation) * suppression

        # Add biological noise (stochastic gene expression)
        noise = random.gauss(0, self.noise_amplitude)

        # Clamp to valid range
        expression = max(0.0, min(self.max_expression, raw_expression + noise))

        return expression


# ---------------------------------------------------------------------------
# GeneRegulatoryNetwork
# ---------------------------------------------------------------------------

class GeneRegulatoryNetwork:
    """Network of musical genes regulating each other.

    NON-PRE-CALCULABLE: emergent patterns cannot be predicted from
    individual genes. Must simulate to discover attractors.

    The network topology encodes musical logic:
    - TONIC activated by REST → rest creates space for the root
    - DOMINANT activated by TONIC → V follows I naturally
    - TENSION/RESOLUTION form a bistable switch → harmonic motion
    - COMPLEXITY/CONVENTION push-pull → genre determination

    Attractors in this network correspond to emergent musical styles
    that arise from the interaction of these regulatory relationships.
    """

    def __init__(self, seed: Optional[int] = None):
        """Create 20 musical genes with regulatory relationships."""
        if seed is not None:
            random.seed(seed)

        self.genes: Dict[str, MusicalGene] = {}
        self.concentrations: Dict[str, float] = {}
        self.history: List[Dict[str, float]] = []
        self._build_network()
        self._initialize_concentrations()

    def _build_network(self) -> None:
        """Build the 20-gene regulatory network.

        Gene regulatory logic mirrors biological transcription:
        - Activators bind promoter regions → increase expression
        - Suppressors bind operator regions → decrease expression
        - Some genes are auto-regulatory (feedback loops)
        - Threshold determines binding affinity
        """
        gene_defs = [
            # name, activators, suppressors, threshold, output_type, basal_rate
            ("TONIC", ["REST", "CADENCE"], ["DISSONANCE"], 0.4, "pitch", 0.3),
            ("DOMINANT", ["TONIC"], ["RESOLUTION"], 0.5, "pitch", 0.2),
            ("REST", ["CADENCE"], ["TENSION"], 0.45, "rhythm", 0.15),
            ("SYNCOPATION", ["GROOVE"], ["RIGIDITY"], 0.5, "rhythm", 0.1),
            ("GROOVE", ["RHYTHM"], ["RUBATO"], 0.4, "rhythm", 0.2),
            ("RHYTHM", ["TEMPO"], ["FREE"], 0.5, "rhythm", 0.25),
            ("DISSONANCE", ["TENSION"], ["RESOLUTION"], 0.5, "pitch", 0.1),
            ("TENSION", ["COMPLEXITY"], ["SIMPLICITY"], 0.45, "form", 0.15),
            ("CADENCE", ["DOMINANT", "TONIC"], [], 0.5, "form", 0.1),
            ("COMPLEXITY", ["INNOVATION"], ["CONVENTION"], 0.5, "form", 0.1),
            ("CONVENTION", ["TONIC", "RHYTHM"], [], 0.4, "form", 0.25),
            ("INNOVATION", ["SURPRISE"], [], 0.5, "form", 0.05),
            ("SURPRISE", ["DEVIATION"], [], 0.5, "dynamics", 0.05),
            ("DYNAMICS", ["ENERGY"], ["REST"], 0.4, "dynamics", 0.2),
            ("ENERGY", [], [], 0.5, "dynamics", 0.15),
            ("TIMBRE", ["HARMONICS"], [], 0.4, "timbre", 0.2),
            ("HARMONICS", [], [], 0.5, "timbre", 0.15),
            ("RUBATO", ["EXPRESSION"], ["TEMPO"], 0.5, "rhythm", 0.1),
            ("EXPRESSION", ["EMOTION"], [], 0.45, "dynamics", 0.15),
            ("EMOTION", ["TENSION"], ["RESOLUTION"], 0.5, "dynamics", 0.1),
        ]

        # Aliases for genes referenced but not in the main 20
        # These are modeled as derived states of existing genes
        self._aliases = {
            "RESOLUTION": "CADENCE",      # resolution is cadence's output
            "SIMPLICITY": "CONVENTION",    # simplicity is convention
            "FREE": "RUBATO",             # free time is extreme rubato
            "RIGIDITY": "RHYTHM",         # rigidity is rigid rhythm
            "DEVIATION": "SYNCOPATION",   # deviation from beat
            "TEMPO": "RHYTHM",            # tempo drives rhythm
            "PITCH": "TONIC",             # pitch is rooted in tonic
        }

        for name, activators, suppressors, threshold, output_type, basal in gene_defs:
            self.genes[name] = MusicalGene(
                name=name,
                activators=activators,
                suppressors=suppressors,
                threshold=threshold,
                output_type=output_type,
                basal_rate=basal,
            )

    def _resolve_gene(self, name: str) -> str:
        """Resolve gene aliases to their primary gene name."""
        return self._aliases.get(name, name)

    def _initialize_concentrations(self) -> None:
        """Set initial protein concentrations with small random perturbation."""
        for name in self.genes:
            self.concentrations[name] = random.uniform(0.05, 0.4)

    def _get_effective_concentrations(self) -> Dict[str, float]:
        """Build concentration dict including alias mappings."""
        eff = dict(self.concentrations)
        for alias, primary in self._aliases.items():
            if primary in eff:
                eff[alias] = eff[primary] * random.uniform(0.8, 1.2)
        return eff

    def step(self) -> Dict[str, float]:
        """One timestep: all genes update based on current concentrations.

        Uses Euler integration with decay. Each gene:
        1. Reads current regulator concentrations
        2. Calculates new expression level
        3. Updates its own concentration: dC/dt = expression - decay*C

        NON-PRE-CALCULABLE: the coupled nonlinear dynamics mean you must
        iterate to see what emerges. No closed-form solution.

        Returns:
            New concentrations after this timestep.
        """
        eff = self._get_effective_concentrations()
        new_concentrations = {}

        for name, gene in self.genes.items():
            # Expression rate (production)
            production = gene.express(eff)

            # Current concentration
            current = self.concentrations.get(name, 0.0)

            # Euler step: dC/dt = production - decay * C
            delta = production - gene.decay_rate * current
            new_conc = current + delta * 0.1  # dt = 0.1 for stability

            # Clamp
            new_conc = max(0.0, min(gene.max_expression, new_conc))
            new_concentrations[name] = new_conc

        # ENERGY is special: activated by sum of all active genes
        total_activity = sum(1.0 for c in new_concentrations.values() if c > 0.3)
        energy_gene = self.genes.get("ENERGY")
        if energy_gene:
            energy_production = _hill_function(total_activity / len(self.genes), n=2.0, k=0.3)
            current_energy = new_concentrations.get("ENERGY", 0.0)
            delta_e = energy_production - energy_gene.decay_rate * current_energy
            new_concentrations["ENERGY"] = max(0.0, min(1.0, current_energy + delta_e * 0.1))

        # HARMONICS follows from pitch-related gene activity
        pitch_activity = (new_concentrations.get("TONIC", 0.0) +
                          new_concentrations.get("DOMINANT", 0.0) +
                          new_concentrations.get("DISSONANCE", 0.0)) / 3.0
        harmonics_gene = self.genes.get("HARMONICS")
        if harmonics_gene:
            current_h = new_concentrations.get("HARMONICS", 0.0)
            delta_h = pitch_activity * 0.8 - harmonics_gene.decay_rate * current_h
            new_concentrations["HARMONICS"] = max(0.0, min(1.0, current_h + delta_h * 0.1))

        # EMOTION blends tension and resolution dynamics
        emotion_gene = self.genes.get("EMOTION")
        if emotion_gene:
            tension_val = new_concentrations.get("TENSION", 0.0)
            cadence_val = new_concentrations.get("CADENCE", 0.0)
            emotion_input = _hill_function(tension_val, n=2.0, k=0.4) * (1.0 - 0.5 * cadence_val)
            current_em = new_concentrations.get("EMOTION", 0.0)
            delta_em = emotion_input - emotion_gene.decay_rate * current_em
            new_concentrations["EMOTION"] = max(0.0, min(1.0, current_em + delta_em * 0.1))

        self.concentrations = new_concentrations
        self.history.append(dict(new_concentrations))
        return dict(new_concentrations)

    def simulate(self, steps: int = 100) -> List[Dict[str, float]]:
        """Run full simulation. Returns concentration time series.

        The network may exhibit:
        - Steady states (stable genre)
        - Oscillations (alternating tension/release)
        - Chaotic dynamics (free improvisation)
        - Multi-stability (genre switching)

        These behaviors emerge from the regulatory topology and cannot
        be predicted without simulation.

        Args:
            steps: number of timesteps to simulate

        Returns:
            List of concentration snapshots, one per timestep.
        """
        self.history = []
        for _ in range(steps):
            self.step()
        return list(self.history)

    def find_attractors(
        self,
        runs: int = 50,
        steps_per_run: int = 300,
        convergence_threshold: float = 0.05,
    ) -> List[Dict[str, float]]:
        """Find steady-state attractors in the network.

        Runs multiple simulations from different initial conditions and
        clusters the final states. Attractors correspond to the 'genres'
        the network converges to — different stable patterns of musical
        expression.

        In biology, attractors = cell types. Here, attractors = musical
        styles. Same mathematics, different substrate.

        Args:
            runs: number of simulation runs from random initial conditions
            steps_per_run: how long each simulation runs
            convergence_threshold: distance threshold for clustering

        Returns:
            List of attractor states (representative concentration dicts)
        """
        attractors: List[Dict[str, float]] = []
        final_states: List[Dict[str, float]] = []

        gene_names = list(self.genes.keys())

        for _ in range(runs):
            # Random initial conditions
            for name in gene_names:
                self.concentrations[name] = random.uniform(0.0, 1.0)

            # Simulate
            self.history = []
            for _ in range(steps_per_run):
                self.step()

            # Record final state
            if self.concentrations:
                final_states.append(dict(self.concentrations))

        # Cluster final states to find attractors
        for state in final_states:
            is_new_attractor = True
            for attractor in attractors:
                dist = self._state_distance(state, attractor)
                if dist < convergence_threshold:
                    is_new_attractor = False
                    break

            if is_new_attractor:
                attractors.append(dict(state))

        # Restore random initial conditions
        self._initialize_concentrations()
        self.history = []

        return attractors

    def _state_distance(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        """Euclidean distance between two concentration states."""
        genes = set(a.keys()) | set(b.keys())
        total = 0.0
        for g in genes:
            diff = a.get(g, 0.0) - b.get(g, 0.0)
            total += diff * diff
        return math.sqrt(total)

    def get_network_state_summary(self) -> Dict[str, Dict[str, float]]:
        """Summarize current network state by output type.

        Returns a dict mapping each output_type to a summary of
        the genes that produce it and their current concentrations.
        """
        summary: Dict[str, Dict[str, float]] = {}
        for name, gene in self.genes.items():
            otype = gene.output_type
            if otype not in summary:
                summary[otype] = {}
            summary[otype][name] = self.concentrations.get(name, 0.0)
        return summary

    def perturb(self, gene_name: str, amount: float) -> None:
        """Perturb a gene's concentration. Like a mutation or environmental signal."""
        if gene_name in self.concentrations:
            self.concentrations[gene_name] = max(
                0.0, min(1.0, self.concentrations[gene_name] + amount)
            )

    def knock_out(self, gene_name: str) -> None:
        """Knock out a gene (set concentration to zero). Like a knockout experiment."""
        if gene_name in self.concentrations:
            self.concentrations[gene_name] = 0.0

    def overexpress(self, gene_name: str, level: float = 1.0) -> None:
        """Overexpress a gene. Like adding an enhancer."""
        if gene_name in self.concentrations:
            self.concentrations[gene_name] = min(1.0, level)

    # -------------------------------------------------------------------
    # Musical mapping
    # -------------------------------------------------------------------

    def to_music(self, history: List[Dict[str, float]], bpm: float = 120.0) -> Arrangement:
        """Convert gene expression time series to musical arrangement.

        Maps concentration dynamics to musical parameters:
        - Pitch genes (TONIC, DOMINANT, DISSONANCE) → note choices
        - Rhythm genes (GROOVE, SYNCOPATION, RHYTHM) → timing
        - Dynamics genes (DYNAMICS, ENERGY, EMOTION) → velocity
        - Timbre genes (TIMBRE, HARMONICS) → voice selection
        - Form genes (TENSION, CADENCE, COMPLEXITY) → structure

        The mapping preserves the temporal dynamics: rising tension
        genes produce increasing harmonic complexity, groove concentrations
        affect swing feel, etc.
        """
        if not history:
            history = self.simulate(steps=64)

        arrangement = Arrangement(bpm=bpm, name="GRN Composition")

        # Determine active voices from timbre concentrations
        timbre_avg = self._avg_over_history(history, "TIMBRE")
        harmonics_avg = self._avg_over_history(history, "HARMONICS")

        # Create tracks based on which gene families are active
        tracks_to_create = []

        energy_avg = self._avg_over_history(history, "ENERGY")
        if energy_avg > 0.15:
            tracks_to_create.append(("GRN Bass", "bass"))
            tracks_to_create.append(("GRN Drums", "drums"))

        if timbre_avg > 0.1:
            tracks_to_create.append(("GRN Pad", "pad"))

        if harmonics_avg > 0.1:
            tracks_to_create.append(("GRN Lead", "lead"))

        # Always have at least one track
        if not tracks_to_create:
            tracks_to_create = [("GRN Piano", "piano")]

        for track_name, voice in tracks_to_create:
            track = Track(name=track_name, voice=voice, bpm=bpm)
            arrangement.add_track(track)

        # Generate events from gene expression patterns
        # Group timesteps into bars (4 beats per bar, ~4 timesteps per beat)
        events = self._history_to_events(history, bpm)

        # Distribute events across tracks
        if arrangement.tracks:
            for i, event in enumerate(events):
                track_idx = i % len(arrangement.tracks)
                arrangement.tracks[track_idx]._events.extend([event])

        return arrangement

    def _avg_over_history(self, history: List[Dict[str, float]], gene: str) -> float:
        """Average concentration of a gene over the history."""
        if not history:
            return 0.0
        total = sum(h.get(gene, 0.0) for h in history)
        return total / len(history)

    def _history_to_events(
        self, history: List[Dict[str, float]], bpm: float
    ) -> list:
        """Convert gene expression history to musical events.

        This is the core biology→music transfer function:
        - Concentration → velocity (dynamics)
        - Pitch gene ratio → MIDI note number
        - Rhythm gene activity → timing offset
        - Tension → harmonic interval choice
        """
        events = []
        tonic_notes = [60, 62, 64, 67, 69]  # C major pentatonic
        dominant_notes = [67, 69, 71, 72, 74]  # G-based
        dissonant_notes = [61, 63, 66, 68, 70]  # chromatic neighbors

        for t, state in enumerate(history):
            # Pitch selection from pitch genes
            tonic = state.get("TONIC", 0.0)
            dominant = state.get("DOMINANT", 0.0)
            dissonance = state.get("DISSONANCE", 0.0)
            pitch_total = tonic + dominant + dissonance + 0.001

            # Weighted pitch selection
            r = random.random() * pitch_total
            if r < tonic:
                note = random.choice(tonic_notes)
            elif r < tonic + dominant:
                note = random.choice(dominant_notes)
            else:
                note = random.choice(dissonant_notes)

            # Transpose based on complexity
            complexity = state.get("COMPLEXITY", 0.0)
            octave_shift = int(complexity * 2 - 0.5) * 12
            note = max(24, min(96, note + octave_shift))

            # Velocity from dynamics genes
            dynamics = state.get("DYNAMICS", 0.3)
            energy = state.get("ENERGY", 0.3)
            emotion = state.get("EMOTION", 0.2)
            velocity = int(40 + 80 * (dynamics * 0.4 + energy * 0.35 + emotion * 0.25))
            velocity = max(20, min(127, velocity))

            # Duration from rhythm genes
            groove = state.get("GROOVE", 0.3)
            syncopation = state.get("SYNCOPATION", 0.2)
            # Higher groove → shorter, more rhythmic notes
            # Higher syncopation → more varied durations
            base_dur = 0.5 - groove * 0.3
            dur_variation = syncopation * random.uniform(-0.2, 0.2)
            duration = max(0.1, base_dur + dur_variation)

            # Timing offset from rubato
            rubato = state.get("RUBATO", 0.1)
            time_offset = t * 0.25 + rubato * random.uniform(-0.05, 0.05)

            # Create MidiEvent for track compatibility
            beat_ms = 60000.0 / bpm
            events.append(MidiEvent(
                note=note,
                velocity=velocity,
                start_ms=time_offset * beat_ms,
                duration_ms=duration * beat_ms,
                channel=0,
            ))

        return events


# ---------------------------------------------------------------------------
# HorizontalTransfer
# ---------------------------------------------------------------------------

class HorizontalTransfer:
    """Bacteria swap genes → genres swap constraints.

    Horizontal gene transfer in bacteria allows rapid adaptation by
    importing foreign DNA. In music, this models cross-genre borrowing:
    jazz imports African rhythmic genes, classical imports folk melody genes,
    electronic imports dub production genes.

    The transferred gene may behave differently in the new regulatory
    context — just as a gene transferred between bacterial species
    interacts with a different transcriptional milieu.
    """

    def __init__(self, mutation_rate: float = 0.1):
        """Initialize transfer operator.

        Args:
            mutation_rate: probability of mutation during transfer
                         (like imperfect DNA replication)
        """
        self.mutation_rate = mutation_rate
        self.transfer_log: List[Dict] = []

    def transfer(
        self,
        donor: GeneRegulatoryNetwork,
        recipient: GeneRegulatoryNetwork,
        gene_name: str,
    ) -> bool:
        """Transfer a gene from donor network to recipient network.

        The receiving genre changes because the new gene interacts with
        existing regulatory connections. Like a bacterium acquiring antibiotic
        resistance — the whole phenotype shifts.

        Args:
            donor: network providing the gene
            recipient: network receiving the gene
            gene_name: name of gene to transfer

        Returns:
            True if transfer succeeded, False if gene not found
        """
        if gene_name not in donor.genes:
            return False

        source_gene = donor.genes[gene_name]

        # Deep copy with possible mutation
        transferred = copy.deepcopy(source_gene)

        # Mutation during transfer
        if random.random() < self.mutation_rate:
            # Mutate threshold (binding affinity change)
            transferred.threshold += random.gauss(0, 0.1)
            transferred.threshold = max(0.1, min(0.9, transferred.threshold))

        if random.random() < self.mutation_rate:
            # Mutate basal rate (promoter strength change)
            transferred.basal_rate += random.gauss(0, 0.05)
            transferred.basal_rate = max(0.0, min(0.5, transferred.basal_rate))

        if random.random() < self.mutation_rate:
            # Mutate hill coefficient (cooperativity change)
            transferred.hill_coefficient += random.gauss(0, 0.3)
            transferred.hill_coefficient = max(1.0, min(4.0, transferred.hill_coefficient))

        # Update activators/suppressors to point to genes that exist in recipient
        # Foreign regulators that don't exist → they bind but find no target
        # (like a transcription factor with no binding site)
        valid_activators = []
        for act in transferred.activators:
            if act in recipient.genes or act in recipient._aliases:
                valid_activators.append(act)
            # 30% chance of retaining orphan regulator (may find new interactions)
            elif random.random() < 0.3:
                valid_activators.append(act)

        valid_suppressors = []
        for sup in transferred.suppressors:
            if sup in recipient.genes or sup in recipient._aliases:
                valid_suppressors.append(sup)
            elif random.random() < 0.3:
                valid_suppressors.append(sup)

        transferred.activators = valid_activators
        transferred.suppressors = valid_suppressors

        # Install in recipient
        recipient.genes[gene_name] = transferred
        if gene_name not in recipient.concentrations:
            # Initial concentration from donor
            recipient.concentrations[gene_name] = donor.concentrations.get(gene_name, 0.2)

        # Log the transfer
        self.transfer_log.append({
            "gene": gene_name,
            "donor_genes": len(donor.genes),
            "recipient_genes": len(recipient.genes),
            "activators": transferred.activators,
            "suppressors": transferred.suppressors,
            "threshold": transferred.threshold,
            "basal_rate": transferred.basal_rate,
        })

        return True

    def batch_transfer(
        self,
        donor: GeneRegulatoryNetwork,
        recipient: GeneRegulatoryNetwork,
        gene_names: List[str],
    ) -> List[str]:
        """Transfer multiple genes at once.

        Like a genomic island transfer — multiple genes move together,
        preserving some of their co-regulation.

        Args:
            donor: source network
            recipient: target network
            gene_names: genes to transfer

        Returns:
            List of successfully transferred gene names
        """
        transferred = []
        for name in gene_names:
            if self.transfer(donor, recipient, name):
                transferred.append(name)
        return transferred

    def reciprocal_exchange(
        self,
        network_a: GeneRegulatoryNetwork,
        network_b: GeneRegulatoryNetwork,
        gene_a: str,
        gene_b: str,
    ) -> Tuple[bool, bool]:
        """Swap genes between two networks.

        Like bacterial conjugation — both parties exchange genetic material.

        Args:
            network_a: first network
            network_b: second network
            gene_a: gene from A to send to B
            gene_b: gene from B to send to A

        Returns:
            (success_a_to_b, success_b_to_a)
        """
        success_ab = self.transfer(network_a, network_b, gene_a)
        success_ba = self.transfer(network_b, network_a, gene_b)
        return success_ab, success_ba


# ---------------------------------------------------------------------------
# NetworkAnalyzer
# ---------------------------------------------------------------------------

class NetworkAnalyzer:
    """Analyze gene regulatory network dynamics and structure."""

    @staticmethod
    def correlation_matrix(
        history: List[Dict[str, float]]
    ) -> Dict[str, Dict[str, float]]:
        """Compute pairwise correlation between gene expression time series.

        Highly correlated genes may be co-regulated or form a module.
        Anti-correlated genes may be in a toggle-switch relationship.
        """
        if len(history) < 3:
            return {}

        genes = list(history[0].keys())
        n = len(history)

        # Compute means
        means = {}
        for g in genes:
            means[g] = sum(h.get(g, 0.0) for h in history) / n

        # Compute std devs
        stds = {}
        for g in genes:
            var = sum((h.get(g, 0.0) - means[g]) ** 2 for h in history) / n
            stds[g] = math.sqrt(var) if var > 0 else 1e-10

        # Compute correlations
        corr: Dict[str, Dict[str, float]] = {}
        for g1 in genes:
            corr[g1] = {}
            for g2 in genes:
                cov = sum(
                    (history[i].get(g1, 0.0) - means[g1]) *
                    (history[i].get(g2, 0.0) - means[g2])
                    for i in range(n)
                ) / n
                corr[g1][g2] = cov / (stds[g1] * stds[g2])

        return corr

    @staticmethod
    def find_oscillations(
        history: List[Dict[str, float]], gene_name: str, min_periods: int = 2
    ) -> bool:
        """Detect if a gene's expression oscillates.

        Counts zero-crossings of the detrended signal.
        Oscillating genes drive rhythmic musical output.
        """
        if len(history) < 10:
            return False

        values = [h.get(gene_name, 0.0) for h in history]

        # Detrend: subtract moving average
        window = max(3, len(values) // 10)
        detrended = []
        for i in range(len(values)):
            start = max(0, i - window // 2)
            end = min(len(values), i + window // 2 + 1)
            avg = sum(values[start:end]) / (end - start)
            detrended.append(values[i] - avg)

        # Count zero crossings
        crossings = 0
        for i in range(1, len(detrended)):
            if detrended[i] * detrended[i - 1] < 0:
                crossings += 1

        # Need at least min_periods * 2 crossings for min_periods oscillations
        return crossings >= min_periods * 2

    @staticmethod
    def influence_centrality(network: GeneRegulatoryNetwork) -> Dict[str, int]:
        """How many other genes does each gene regulate?

        High centrality = master regulator (like a key musical parameter
        that influences many aspects of the composition).
        """
        centrality: Dict[str, int] = {name: 0 for name in network.genes}
        for name, gene in network.genes.items():
            for act in gene.activators:
                resolved = network._resolve_gene(act)
                if resolved in centrality:
                    centrality[resolved] += 1
            for sup in gene.suppressors:
                resolved = network._resolve_gene(sup)
                if resolved in centrality:
                    centrality[resolved] += 1
        return centrality

    @staticmethod
    def detect_bifurcation(
        network: GeneRegulatoryNetwork,
        gene_name: str,
        param_range: Tuple[float, float] = (0.0, 1.0),
        steps: int = 50,
        sim_length: int = 200,
    ) -> List[Tuple[float, float]]:
        """Detect bifurcation points for a parameter gene.

        Slowly increases the basal rate of a gene and measures the steady-state
        of another gene. Bifurcation = sudden qualitative change in behavior.

        Returns list of (param_value, steady_state) pairs.
        """
        results = []
        original_basal = network.genes[gene_name].basal_rate

        for i in range(steps):
            param = param_range[0] + (param_range[1] - param_range[0]) * i / (steps - 1)
            network.genes[gene_name].basal_rate = param
            network._initialize_concentrations()
            network.history = []

            for _ in range(sim_length):
                network.step()

            # Average last 20% as steady state
            tail = network.history[-sim_length // 5:]
            avg = sum(h.get(gene_name, 0.0) for h in tail) / max(len(tail), 1)
            results.append((param, avg))

        # Restore
        network.genes[gene_name].basal_rate = original_basal
        return results


# ---------------------------------------------------------------------------
# RegulatoryMotif — reusable regulatory patterns
# ---------------------------------------------------------------------------

class RegulatoryMotif:
    """Common regulatory motifs found in both biology and music.

    Motifs are small sub-circuits that perform specific functions:
    - Toggle switch: bistable choice between two states (major/minor)
    - Feed-forward loop: filtered pulse (grace note detection)
    - Negative autoregulation: homeostatic control (tempo stability)
    - Oscillator: rhythmic output (beat generation)
    """

    @staticmethod
    def toggle_switch(
        gene_a: str = "MAJOR",
        gene_b: str = "MINOR",
    ) -> Tuple[MusicalGene, MusicalGene]:
        """Create a toggle switch: two mutually inhibiting genes.

        Like the lac/lambda phage decision circuit, or the choice
        between major and minor tonality.
        """
        a = MusicalGene(
            name=gene_a,
            suppressors=[gene_b],
            basal_rate=0.1,
            output_type="pitch",
            threshold=0.5,
        )
        b = MusicalGene(
            name=gene_b,
            suppressors=[gene_a],
            basal_rate=0.1,
            output_type="pitch",
            threshold=0.5,
        )
        return a, b

    @staticmethod
    def feed_forward_loop(
        input_gene: str = "THEME",
        intermediate: str = "DEVELOPMENT",
        output_gene: str = "VARIATION",
    ) -> Tuple[MusicalGene, MusicalGene, MusicalGene]:
        """Create a coherent feed-forward loop.

        Input activates both intermediate and output.
        Intermediate also activates output.
        This creates a persistence detector: only sustained inputs
        trigger the output. In music, this filters out brief
        variations and only develops sustained themes.
        """
        x = MusicalGene(
            name=input_gene,
            activators=[],
            basal_rate=0.2,
            output_type="form",
        )
        y = MusicalGene(
            name=intermediate,
            activators=[input_gene],
            basal_rate=0.05,
            output_type="form",
            threshold=0.4,
        )
        z = MusicalGene(
            name=output_gene,
            activators=[input_gene, intermediate],
            basal_rate=0.02,
            output_type="form",
            threshold=0.3,
        )
        return x, y, z

    @staticmethod
    def negative_autoregulation(
        gene_name: str = "TEMPO_KEEPER",
    ) -> MusicalGene:
        """Create a self-repressing gene.

        Negative autoregulation speeds response time and reduces noise.
        In music, this keeps a parameter (like tempo) stable around
        a set point while allowing fast recovery from perturbations.
        """
        return MusicalGene(
            name=gene_name,
            suppressors=[gene_name],
            basal_rate=0.8,
            decay_rate=0.15,
            output_type="rhythm",
            threshold=0.5,
            hill_coefficient=3.0,  # steep for tight control
        )

    @staticmethod
    def repressilator(
        genes: Tuple[str, str, str] = ("REP_A", "REP_B", "REP_C"),
    ) -> Tuple[MusicalGene, MusicalGene, MusicalGene]:
        """Create a repressilator: 3-gene oscillatory circuit.

        A →| B →| C →| A (each represses the next)
        This naturally oscillates, producing periodic output.
        In music, this generates rhythmic pulses from pure logic.
        """
        a, b, c = genes
        gene_a = MusicalGene(name=a, suppressors=[c], basal_rate=0.15, output_type="rhythm")
        gene_b = MusicalGene(name=b, suppressors=[a], basal_rate=0.15, output_type="rhythm")
        gene_c = MusicalGene(name=c, suppressors=[b], basal_rate=0.15, output_type="rhythm")
        return gene_a, gene_b, gene_c


# ---------------------------------------------------------------------------
# GeneExpressionVisualizer — text-based network visualization
# ---------------------------------------------------------------------------

class GeneExpressionVisualizer:
    """Text-based visualization of gene expression dynamics."""

    @staticmethod
    def concentration_bar(
        value: float, width: int = 20, filled: str = "█", empty: str = "░"
    ) -> str:
        """Create a bar chart of a concentration value."""
        n_filled = int(value * width)
        n_empty = width - n_filled
        return filled * n_filled + empty * n_empty

    @staticmethod
    def snapshot(network: GeneRegulatoryNetwork) -> str:
        """Create a text snapshot of the current network state."""
        lines = []
        lines.append("╔══════════════════════════════════════════════╗")
        lines.append("║        Gene Regulatory Network State         ║")
        lines.append("╠══════════════════════════════════════════════╣")

        summary = network.get_network_state_summary()
        for output_type in ["pitch", "rhythm", "dynamics", "timbre", "form"]:
            if output_type not in summary:
                continue
            lines.append(f"║  [{output_type.upper():>8s}]                         ║")
            for gene_name, conc in sorted(summary[output_type].items()):
                bar = GeneExpressionVisualizer.concentration_bar(conc)
                lines.append(f"║  {gene_name:>14s} {bar} {conc:.2f} ║")
            lines.append("║                                              ║")

        lines.append("╚══════════════════════════════════════════════╝")
        return "\n".join(lines)

    @staticmethod
    def timeseries_sparkline(
        history: List[Dict[str, float]],
        gene_name: str,
        width: int = 40,
    ) -> str:
        """Create a sparkline of a gene's expression over time."""
        if not history:
            return "No data"

        values = [h.get(gene_name, 0.0) for h in history]
        # Downsample if needed
        if len(values) > width:
            step = len(values) / width
            values = [values[int(i * step)] for i in range(width)]

        spark_chars = "▁▂▃▄▅▆▇█"
        max_val = max(values) if values else 1.0
        min_val = min(values) if values else 0.0
        rng = max_val - min_val if max_val != min_val else 1.0

        chars = []
        for v in values:
            idx = int((v - min_val) / rng * (len(spark_chars) - 1))
            chars.append(spark_chars[max(0, min(len(spark_chars) - 1, idx))])

        return f"{gene_name}: {''.join(chars)}"


# ---------------------------------------------------------------------------
# GeneRegulatoryEnsemble — multiple networks playing together
# ---------------------------------------------------------------------------

class GeneRegulatoryEnsemble:
    """Multiple GRNs interacting, like an ecosystem of musical organisms.

    Each network is a 'musician' with its own regulatory genome.
    Networks can influence each other through signaling molecules
    (like quorum sensing in bacteria).
    """

    def __init__(self, n_networks: int = 4, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

        self.networks: List[GeneRegulatoryNetwork] = []
        self.signal_molecules: Dict[str, float] = {}

        for i in range(n_networks):
            net = GeneRegulatoryNetwork(seed=random.randint(0, 100000))
            # Slightly different initial conditions for each
            for name in net.genes:
                net.concentrations[name] *= random.uniform(0.8, 1.2)
            self.networks.append(net)

    def step(self) -> List[Dict[str, float]]:
        """Advance all networks one timestep with cross-network signaling."""
        results = []

        # Compute signaling molecules (average of key genes across networks)
        signal_genes = ["TONIC", "TENSION", "ENERGY", "GROOVE"]
        for sg in signal_genes:
            vals = [
                net.concentrations.get(sg, 0.0)
                for net in self.networks
            ]
            self.signal_molecules[sg] = sum(vals) / len(vals) if vals else 0.0

        # Each network steps, with signaling as external input
        for net in self.networks:
            # Signaling modulates concentrations (quorum sensing)
            for sg in signal_genes:
                if sg in net.concentrations:
                    signal = self.signal_molecules.get(sg, 0.0)
                    # Weak attraction toward ensemble average
                    net.concentrations[sg] += 0.02 * (signal - net.concentrations[sg])

            result = net.step()
            results.append(result)

        return results

    def simulate(self, steps: int = 100) -> List[List[Dict[str, float]]]:
        """Simulate the full ensemble for given steps."""
        all_results: List[List[Dict[str, float]]] = []
        for _ in range(steps):
            step_results = self.step()
            all_results.append(step_results)
        return all_results

    def synchronize(self, strength: float = 0.1) -> None:
        """Increase coupling strength between networks.

        Like increasing cell-cell communication in a tissue.
        Higher synchronization → more ensemble cohesion.
        """
        signal_genes = ["TONIC", "TENSION", "ENERGY", "GROOVE"]
        for sg in signal_genes:
            if sg in self.signal_molecules:
                avg = self.signal_molecules[sg]
                for net in self.networks:
                    if sg in net.concentrations:
                        net.concentrations[sg] += strength * (avg - net.concentrations[sg])


# ---------------------------------------------------------------------------
# GeneMutator — evolutionary operations on GRNs
# ---------------------------------------------------------------------------

class GeneMutator:
    """Evolutionary operators for gene regulatory networks.

    Models the evolutionary processes that shape real gene networks:
    - Point mutations (parameter changes)
    - Gene duplication (new gene from existing)
    - Regulatory rewiring (new/lost connections)
    - Gene loss (deletion)
    """

    @staticmethod
    def point_mutate(network: GeneRegulatoryNetwork, gene_name: str) -> bool:
        """Mutate a random parameter of a gene."""
        if gene_name not in network.genes:
            return False

        gene = network.genes[gene_name]
        params = ["threshold", "basal_rate", "hill_coefficient", "decay_rate", "noise_amplitude"]
        param = random.choice(params)
        current = getattr(gene, param)
        delta = random.gauss(0, 0.1)

        if param == "hill_coefficient":
            new_val = max(1.0, min(4.0, current + delta))
        elif param in ("threshold", "basal_rate", "decay_rate", "noise_amplitude"):
            new_val = max(0.0, min(1.0, current + delta))
        else:
            new_val = current + delta

        setattr(gene, param, new_val)
        return True

    @staticmethod
    def duplicate_gene(
        network: GeneRegulatoryNetwork,
        gene_name: str,
        new_name: Optional[str] = None,
    ) -> bool:
        """Duplicate a gene with slight mutations.

        Gene duplication is the primary source of new genes in evolution.
        The duplicate initially has the same function but can diverge.
        """
        if gene_name not in network.genes:
            return False

        if new_name is None:
            new_name = f"{gene_name}_COPY_{random.randint(100, 999)}"

        original = network.genes[gene_name]
        duplicate = copy.deepcopy(original)
        duplicate.name = new_name

        # Slight mutation on duplication
        duplicate.threshold += random.gauss(0, 0.05)
        duplicate.basal_rate += random.gauss(0, 0.03)

        network.genes[new_name] = duplicate
        network.concentrations[new_name] = network.concentrations.get(gene_name, 0.2) * 0.5

        return True

    @staticmethod
    def rewire_connection(
        network: GeneRegulatoryNetwork,
        from_gene: str,
        to_gene: str,
        connection_type: str = "activation",
    ) -> bool:
        """Add or remove a regulatory connection.

        Like a promoter mutation that creates or destroys a transcription
        factor binding site.
        """
        if to_gene not in network.genes:
            return False

        gene = network.genes[to_gene]

        if connection_type == "activation":
            if from_gene not in gene.activators:
                gene.activators.append(from_gene)
            else:
                gene.activators.remove(from_gene)
        elif connection_type == "suppression":
            if from_gene not in gene.suppressors:
                gene.suppressors.append(from_gene)
            else:
                gene.suppressors.remove(from_gene)
        else:
            return False

        return True

    @staticmethod
    def delete_gene(network: GeneRegulatoryNetwork, gene_name: str) -> bool:
        """Delete a gene from the network.

        Models gene loss, which is common in evolution.
        Other genes that regulated it now have orphan connections.
        """
        if gene_name not in network.genes:
            return False

        del network.genes[gene_name]
        if gene_name in network.concentrations:
            del network.concentrations[gene_name]

        # Clean up references
        for gene in network.genes.values():
            if gene_name in gene.activators:
                gene.activators.remove(gene_name)
            if gene_name in gene.suppressors:
                gene.suppressors.remove(gene_name)

        return True

    @staticmethod
    def evolve(
        network: GeneRegulatoryNetwork,
        generations: int = 100,
        fitness_fn: Optional[callable] = None,
    ) -> GeneRegulatoryNetwork:
        """Evolve a network using random mutations.

        Without a fitness function, just applies random mutations.
        With a fitness function, keeps mutations that improve fitness.

        Args:
            network: starting network
            generations: number of evolutionary steps
            fitness_fn: optional function(history) -> float

        Returns:
            Evolved network
        """
        best = network
        best_fitness = -float("inf")

        if fitness_fn is not None:
            # Evaluate initial
            net_copy = copy.deepcopy(network)
            history = net_copy.simulate(steps=100)
            best_fitness = fitness_fn(history)
            best = network

        for _ in range(generations):
            mutant = copy.deepcopy(best)
            gene_name = random.choice(list(mutant.genes.keys()))

            # Random mutation type
            mutation = random.choice(["point", "rewire"])
            if mutation == "point":
                GeneMutator.point_mutate(mutant, gene_name)
            elif mutation == "rewire":
                target = random.choice(list(mutant.genes.keys()))
                ctype = random.choice(["activation", "suppression"])
                GeneMutator.rewire_connection(mutant, gene_name, target, ctype)

            if fitness_fn is not None:
                try:
                    history = mutant.simulate(steps=100)
                    fitness = fitness_fn(history)
                    if fitness > best_fitness:
                        best = mutant
                        best_fitness = fitness
                except Exception:
                    continue
            else:
                best = mutant

        return best
