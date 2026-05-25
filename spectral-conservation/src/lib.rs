//! # Spectral Conservation
//!
//! Tracks the spectral first integral I(x) = γ(x) + H(x) in coupled nonlinear
//! dynamics of the form x_{t+1} = σ(C(x_t) · x_t).
//!
//! ## The Discovery
//!
//! The quantity I = spectral_gap + participation_entropy is approximately conserved
//! along trajectories with CV < 0.03 across thousands of configurations.
//! The commutator ||[D,C]|| predicts conservation quality with r = 0.965.
//!
//! ## Three Regimes
//!
//! - **Structural** (rank-1 coupling): I is exactly conserved (algebraic identity)
//! - **Dynamical** (full-rank, stable shape): CV < 0.015
//! - **Transitional** (near rank-1): CV 0.03-0.05
//!
//! ## Reference
//!
//! Forgemaster & Digennaro (2026). "Spectral Near-Conservation in Coupled Nonlinear
//! Dynamics: An Empirical Discovery with 18 Cycles of Automated Falsification."

use nalgebra::{DMatrix, DVector};
use serde::{Deserialize, Serialize};
use std::fmt;

// ---------------------------------------------------------------------------
// Core Types
// ---------------------------------------------------------------------------

/// Alert level for conservation monitoring.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Alert {
    /// CV well below threshold (< 0.01)
    None,
    /// CV approaching threshold (0.01 - 0.03)
    Warning,
    /// CV exceeded threshold (> 0.03) — spectral shape broke
    Chop,
}

/// Conservation regime classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Regime {
    /// Rank-1 coupling: exact algebraic conservation
    Structural,
    /// Full-rank with stable spectral shape: CV < 0.015
    Dynamical,
    /// Near rank-1 with shape conflict: CV 0.03-0.05
    Transitional,
    /// Conservation broken: CV > 0.05
    Degraded,
}

/// Spectral decomposition result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpectralState {
    /// Eigenvalues sorted descending
    pub eigenvalues: Vec<f64>,
    /// Spectral gap γ = λ₁ - λ₂
    pub gamma: f64,
    /// Participation entropy H = -Σ pᵢ ln(pᵢ)
    pub entropy: f64,
    /// Spectral first integral I = γ + H
    pub invariant: f64,
    /// Participation ratio PR = (Σλᵢ)²/(Σλᵢ²)
    pub participation_ratio: f64,
    /// Effective rank
    pub effective_rank: f64,
}

/// Conservation status snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConservationStatus {
    /// Current spectral state
    pub spectral: SpectralState,
    /// Running mean of I
    pub mean_i: f64,
    /// Running std of I
    pub std_i: f64,
    /// Coefficient of variation
    pub cv: f64,
    /// Number of steps tracked
    pub steps: usize,
    /// Current alert level
    pub alert: Alert,
    /// Current regime
    pub regime: Regime,
    /// Commutator ||[D,C]|| (diagnostic)
    pub commutator_norm: Option<f64>,
}

// ---------------------------------------------------------------------------
// Error Type
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub enum SpectralError {
    /// Matrix too small (need at least 2×2)
    MatrixTooSmall(usize),
    /// No positive eigenvalues
    NoPositiveEigenvalues,
    /// Eigenvalue decomposition failed
    EigenDecompositionFailed(String),
}

impl fmt::Display for SpectralError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MatrixTooSmall(n) => write!(f, "matrix too small: {}×{}", n, n),
            Self::NoPositiveEigenvalues => write!(f, "no positive eigenvalues"),
            Self::EigenDecompositionFailed(s) => write!(f, "eigenvalue decomposition failed: {}", s),
        }
    }
}

impl std::error::Error for SpectralError {}

// ---------------------------------------------------------------------------
// Core Computations
// ---------------------------------------------------------------------------

/// Compute spectral state from a symmetric coupling matrix.
pub fn spectral_state(C: &DMatrix<f64>) -> Result<SpectralState, SpectralError> {
    let n = C.nrows();
    if n < 2 {
        return Err(SpectralError::MatrixTooSmall(n));
    }

    // Symmetrize (in case of numerical asymmetry)
    let C_sym = (C + C.transpose()) / 2.0;

    // Eigenvalue decomposition
    let eigen = C_sym.symmetric_eigen();
    let mut eigenvalues: Vec<f64> = eigen.eigenvalues.iter().copied().collect();
    eigenvalues.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));

    // Filter positive eigenvalues
    let pos_eigs: Vec<f64> = eigenvalues.iter().filter(|&&e| e > 1e-12).copied().collect();
    if pos_eigs.len() < 2 {
        // Check for rank-1 case
        if pos_eigs.len() == 1 {
            return Ok(SpectralState {
                eigenvalues: pos_eigs.clone(),
                gamma: 0.0,
                entropy: 0.0,
                invariant: pos_eigs[0],
                participation_ratio: 1.0,
                effective_rank: 1.0,
            });
        }
        return Err(SpectralError::NoPositiveEigenvalues);
    }

    // Spectral gap γ = λ₁ - λ₂
    let gamma = pos_eigs[0] - pos_eigs[1];

    // Participation entropy H = -Σ pᵢ ln(pᵢ)
    let total: f64 = pos_eigs.iter().sum();
    let probs: Vec<f64> = pos_eigs.iter().map(|&e| e / total).collect();
    let entropy: f64 = -probs.iter()
        .filter(|&&p| p > 1e-15)
        .map(|&p| p * p.ln())
        .sum::<f64>();

    // Spectral first integral
    let invariant = gamma + entropy;

    // Participation ratio PR = (Σλᵢ)²/(Σλᵢ²)
    let sum_lambda: f64 = pos_eigs.iter().sum();
    let sum_lambda_sq: f64 = pos_eigs.iter().map(|e| e * e).sum();
    let participation_ratio = if sum_lambda_sq > 1e-20 {
        (sum_lambda * sum_lambda) / sum_lambda_sq
    } else {
        1.0
    };

    // Effective rank
    let effective_rank = participation_ratio;

    Ok(SpectralState {
        eigenvalues: pos_eigs,
        gamma,
        entropy,
        invariant,
        participation_ratio,
        effective_rank,
    })
}

/// Compute commutator norm ||[D,C]||_F where D = diag(d).
pub fn commutator_norm(diag: &DVector<f64>, C: &DMatrix<f64>) -> f64 {
    // D·C - C·D = diag(d)·C - C·diag(d)
    let n = diag.len();
    let mut dc = C.clone();
    for i in 0..n {
        for j in 0..n {
            dc[(i, j)] *= diag[i];
        }
    }
    let mut cd = C.clone();
    for i in 0..n {
        for j in 0..n {
            cd[(i, j)] *= diag[j];
        }
    }
    let commutator = &dc - &cd;
    // Frobenius norm
    commutator.iter().map(|x| x * x).sum::<f64>().sqrt()
}

// ---------------------------------------------------------------------------
// Conservation Monitor
// ---------------------------------------------------------------------------

/// Tracks spectral conservation quality over a trajectory.
pub struct ConservationMonitor {
    /// History of I values
    i_history: Vec<f64>,
    /// CV alert threshold
    cv_threshold: f64,
    /// Warmup steps before computing CV
    warmup: usize,
    /// Baseline I (from first measurement)
    baseline_i: Option<f64>,
}

impl ConservationMonitor {
    /// Create a new monitor with given CV threshold.
    pub fn new(cv_threshold: f64) -> Self {
        Self {
            i_history: Vec::new(),
            cv_threshold,
            warmup: 5,
            baseline_i: None,
        }
    }

    /// Create a monitor with default threshold (0.03).
    pub fn default_threshold() -> Self {
        Self::new(0.03)
    }

    /// Record a new spectral state and return updated conservation status.
    pub fn step(&mut self, state: &SpectralState) -> ConservationStatus {
        if self.baseline_i.is_none() {
            self.baseline_i = Some(state.invariant);
        }
        self.i_history.push(state.invariant);

        let n = self.i_history.len();
        let slice_start = if n > self.warmup { self.warmup } else { 0 };
        let slice = &self.i_history[slice_start..];

        let mean_i = if slice.is_empty() { state.invariant } else { slice.iter().sum::<f64>() / slice.len() as f64 };
        let std_i = if slice.len() < 2 {
            0.0
        } else {
            let variance = slice.iter().map(|&x| (x - mean_i).powi(2)).sum::<f64>() / (slice.len() - 1) as f64;
            variance.sqrt()
        };
        let cv = if mean_i.abs() > 1e-12 { std_i / mean_i.abs() } else { f64::MAX };

        let alert = if cv < 0.01 { Alert::None }
                    else if cv < self.cv_threshold { Alert::Warning }
                    else { Alert::Chop };

        let regime = if state.effective_rank < 1.5 { Regime::Structural }
                     else if cv < 0.015 { Regime::Dynamical }
                     else if cv < 0.05 { Regime::Transitional }
                     else { Regime::Degraded };

        ConservationStatus {
            spectral: state.clone(),
            mean_i,
            std_i,
            cv,
            steps: n,
            alert,
            regime,
            commutator_norm: None,
        }
    }

    /// Record a step with commutator diagnostic.
    pub fn step_with_commutator(
        &mut self,
        state: &SpectralState,
        diag: &DVector<f64>,
        coupling: &DMatrix<f64>,
    ) -> ConservationStatus {
        let comm = commutator_norm(diag, coupling);
        let mut status = self.step(state);
        status.commutator_norm = Some(comm);
        status
    }

    /// Get the history of I values.
    pub fn history(&self) -> &[f64] {
        &self.i_history
    }

    /// Reset the monitor.
    pub fn reset(&mut self) {
        self.i_history.clear();
        self.baseline_i = None;
    }
}

// ---------------------------------------------------------------------------
// Coupling Dynamics
// ---------------------------------------------------------------------------

/// Run a trajectory and track conservation.
pub fn run_trajectory(
    initial: &DVector<f64>,
    coupling_fn: &dyn Fn(&DVector<f64>) -> DMatrix<f64>,
    activation: &dyn Fn(&DVector<f64>) -> DVector<f64>,
    steps: usize,
) -> TrajectoryResult {
    let mut monitor = ConservationMonitor::default_threshold();
    let mut x = initial.clone();
    let mut states = Vec::new();

    for _t in 0..steps {
        let C = coupling_fn(&x);
        let state = spectral_state(&C).unwrap_or_else(|_| SpectralState {
            eigenvalues: vec![],
            gamma: 0.0,
            entropy: 0.0,
            invariant: 0.0,
            participation_ratio: 0.0,
            effective_rank: 0.0,
        });

        let status = monitor.step(&state);
        states.push(status);

        // Advance dynamics
        let z = &C * &x;
        x = activation(&z);
    }

    let history = monitor.history().to_vec();
    let mean = history.iter().sum::<f64>() / history.len() as f64;
    let std = if history.len() > 1 {
        let var = history.iter().map(|&x| (x - mean).powi(2)).sum::<f64>() / (history.len() - 1) as f64;
        var.sqrt()
    } else {
        0.0
    };
    let cv = if mean.abs() > 1e-12 { std / mean.abs() } else { f64::MAX };

    TrajectoryResult {
        states,
        i_history: history,
        final_state: x,
        cv,
        mean_i: mean,
        std_i: std,
    }
}

/// Result of a trajectory simulation.
#[derive(Debug)]
pub struct TrajectoryResult {
    pub states: Vec<ConservationStatus>,
    pub i_history: Vec<f64>,
    pub final_state: DVector<f64>,
    pub cv: f64,
    pub mean_i: f64,
    pub std_i: f64,
}

// ---------------------------------------------------------------------------
// Built-in Coupling Functions
// ---------------------------------------------------------------------------

/// Random static coupling matrix.
pub fn random_coupling(n: usize, seed: u64) -> DMatrix<f64> {
    // Simple deterministic random generation
    let mut state = seed;
    let mut data = Vec::with_capacity(n * n);
    for _ in 0..n * n {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let val = ((state >> 33) as f64) / (1u64 << 31) as f64 - 1.0;
        data.push(val / (n as f64).sqrt());
    }
    let mut C = DMatrix::from_row_slice(n, n, &data);
    // Symmetrize
    let Ct = C.transpose();
    C = (&C + &Ct) / 2.0;
    C
}

/// Hebbian coupling: C(x) = outer(x,x)/N + regularization.
pub fn hebbian_coupling(x: &DVector<f64>, n: usize) -> DMatrix<f64> {
    let mut C = x * x.transpose() / n as f64;
    // Add small diagonal for stability
    for i in 0..C.nrows() {
        C[(i, i)] += 0.01;
    }
    C
}

/// Attention coupling: softmax(x·xᵀ/√N).
pub fn attention_coupling(x: &DVector<f64>, temperature: f64) -> DMatrix<f64> {
    let n = x.len();
    let scale = 1.0 / (n as f64).sqrt() / temperature;
    let scores = x * x.transpose() * scale;

    // Softmax per row (simplified)
    let mut C = DMatrix::zeros(n, n);
    for i in 0..n {
        let row_max = (0..n).map(|j| scores[(i, j)]).fold(f64::NEG_INFINITY, f64::max);
        let exps: Vec<f64> = (0..n).map(|j| (scores[(i, j)] - row_max).exp()).collect();
        let sum: f64 = exps.iter().sum();
        for j in 0..n {
            C[(i, j)] = exps[j] / sum;
        }
    }

    // Symmetrize
    let Ct = C.transpose();
    (&C + &Ct) / 2.0
}

/// tanh activation function.
pub fn tanh_activation(z: &DVector<f64>) -> DVector<f64> {
    z.map(|x| x.tanh())
}

/// Compute the saturation diagonal D = diag(sech²(z)).
pub fn saturation_diagonal(z: &DVector<f64>) -> DVector<f64> {
    z.map(|x| 1.0 - x.tanh().powi(2))
}
