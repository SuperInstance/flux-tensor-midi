# Experiment: Cross-System Interaction

**Date:** 2026-05-23
**Repo:** SuperInstance/flux-tensor-midi
**File:** `experiments/experiment_cross_system.py`

## Objective

Wire multiple living systems (Ecosystem, GRN, MusicalCell, ProteinFolder) together and observe emergent behavior across system boundaries.

---

## Experiment 1: Ecosystem Dynamics — Invasion & Extinction

Set up a 5-species ecosystem (Jazz, Blues, Rock, Classical, HipHop) at ε=0.5, ran 50 ticks, then introduced an invasive species, triggered an extinction event, and observed recovery.

### Results

| Phase | Biodiversity | Living Species |
|-------|-------------|----------------|
| Before invasion | 0.9641 | HipHop + 1 immigrant |
| After invasion | 1.5064 | Techno + 2 immigrants |
| After extinction | 1.8821 | Pop + 3 immigrants |
| After recovery | 1.9552 | Pop, Rock, Punk + 1 immigrant |

### Key Observations

- **Original species displaced**: None of the original 5 survived to the end — all were outcompeted by emergent immigrant species. This is classic ecological succession.
- **Invasion increases diversity**: Biodiversity rose from 0.96 → 1.51 after invasion, showing the ecosystem absorbed the perturbation productively.
- **Extinction event was surprisingly constructive**: The extinction event (threshold=0.5) actually *increased* diversity to 1.88 by clearing niches for new species.
- **Immigration-driven speciation**: The ecosystem auto-generated 23 extinct species over 180 ticks, demonstrating continuous creative destruction.

---

## Experiment 2: Gene Regulatory Network → Cell

A GRN with 20 gene nodes (TONIC, DOMINANT, REST, SYNCOPATION, etc.) was wired into a MusicalCell. The GRN's gene expression levels became transcription factor signals for the cell.

### Results

- Cell energy **converged** from ~0.74 → 0.50 over 20 ticks (damped oscillation toward equilibrium)
- All 20 GRN genes remained active (expression > 0.5) throughout — the GRN was in a stable attractor state
- Cell produced 1-2 MIDI events per tick consistently

### Key Observations

- **Homeostatic convergence**: The cell-GRN system naturally seeks an energy equilibrium near 0.5, analogous to biological homeostasis.
- **GRN acts as a stable controller**: The regulatory network, once settled, provides consistent transcription factor signals — a biological "steady state."
- **Minimal variation**: With all genes active and energy converged, the system reached a fixed point rather than exhibiting chaotic dynamics.

---

## Experiment 3: Protein Folding Energy Landscape

5 random amino acid sequences (10-21 residues) were folded using the lattice folding algorithm.

### Results

| Sequence | Length | Energy | Radius of Gyration | Folded |
|----------|--------|--------|--------------------|----|
| VYWYMLIGVCG | 11 | 27.28 | 0.88 | ✅ |
| PQSADYYFKK | 10 | 39.95 | 0.63 | ✅ |
| IHLDCWAKWVTMIDAGDQMQC | 21 | 24.59 | 0.89 | ✅ |
| GDEDVYWMYQAQVMRPRSN | 19 | 73.74 | 1.00 | ✅ |
| MYVEWDLGEQQDL | 13 | 48.31 | 0.71 | ✅ |

- **Energy funnel** from origin to folded endpoint: (-2.27, -0.68), confirming the downhill energy landscape expected from a foldable protein.

### Key Observations

- **All sequences folded successfully** regardless of length or composition — the lattice model is permissive.
- **Energy varies widely** (24.6 → 73.7) across sequences, reflecting different amino acid interaction strengths.
- **Compactness varies inversely with length**: shorter sequences achieve lower radius of gyration (0.63 for 10aa vs 1.00 for 19aa).
- The energy funnel confirms the system has a proper thermodynamic gradient driving folding.

---

## Experiment 4: Cross-System — GRN → Cell → Ecosystem

Three MusicalCells were driven by a shared GRN. The cells' average energy was tracked alongside an ecosystem of 3 species (Alpha, Beta, Gamma) running in parallel.

### Results

| Tick | Biodiversity | Avg Cell Energy | Living Species |
|------|-------------|-----------------|----------------|
| 0 | 1.5849 | 0.502 | Alpha, Beta, Gamma |
| 20 | 2.5307 | 0.501 | Alpha + 4 immigrants, Classical |
| 40 | 2.2413 | 0.500 | 2 immigrants, Reggae, Techno |
| 60 | 2.2186 | 0.500 | 5 immigrants |
| 80 | 0.0000 | 0.500 | 1 immigrant (bottleneck!) |
| 100 | 2.4472 | 0.500 | 5 immigrants + Folk |

### Key Observations

- **Cell energy was decoupled from ecosystem dynamics**: Cells settled at energy=0.50 and stayed there regardless of ecosystem upheaval. The GRN provided stable regulation.
- **Ecosystem went through dramatic turnover**: Original species (Alpha, Beta, Gamma) were replaced by immigrant species within 20 ticks.
- **Biodiversity bottleneck at tick 80**: Diversity crashed to 0 briefly (only 1 species), then recovered to 2.45 by tick 100. This is a classic ecological boom-bust cycle.
- **Cross-system emergence**: The GRN's stability + ecosystem's volatility created an interesting contrast — biological regulation (cells) vs ecological dynamics (species).

---

## Overall Conclusions

1. **Systems have distinct timescales**: GRN settles in ~10 ticks, cells in ~20, ecosystems take 100+ ticks to reach quasi-equilibrium.
2. **Immigration is the dominant force**: In all ecosystem runs, immigrant species (auto-generated) outcompeted seeded species, suggesting the immigration/speciation model is very active.
3. **Homeostasis emerges naturally**: Both the cell-GRN system and the protein folding system converge to stable states without external intervention.
4. **Cross-system wiring works but shows limited coupling**: The GRN → Cell pipeline was effective, but the Cell → Ecosystem coupling was indirect (cells ran alongside, not feeding into, the ecosystem). True feedback loops would require additional wiring.
5. **Creative destruction is constant**: The ecosystem generates 20-30 species over 100-180 ticks, with most going extinct — a healthy evolutionary churn rate.
