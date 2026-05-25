use spectral_conservation::*;
use nalgebra::{DMatrix, DVector};
use approx::assert_relative_eq;

#[test]
fn test_rank1_exact_conservation() {
    // Theorem 3.1: rank-1 coupling gives H=0, PR=1 exactly
    let x = DVector::from_vec(vec![1.0, 2.0, 3.0, 4.0, 5.0]);
    let n = x.len();
    let C = &x * &x.transpose() / n as f64;

    let state = spectral_state(&C).unwrap();
    assert_relative_eq!(state.entropy, 0.0, epsilon = 1e-10);
    assert_relative_eq!(state.participation_ratio, 1.0, epsilon = 1e-10);
    assert_eq!(state.eigenvalues.len(), 1); // rank-1 → one positive eigenvalue
}

#[test]
fn test_static_conservation() {
    // Theorem 3.2: static C → I is constant
    let C = random_coupling(10, 42);
    let state1 = spectral_state(&C).unwrap();
    let state2 = spectral_state(&C).unwrap();
    assert_relative_eq!(state1.invariant, state2.invariant, epsilon = 1e-15);
}

#[test]
fn test_spectral_state_symmetric() {
    let n = 5;
    let C = random_coupling(n, 123);
    let state = spectral_state(&C).unwrap();

    // Eigenvalues should be sorted descending
    for i in 1..state.eigenvalues.len() {
        assert!(state.eigenvalues[i] <= state.eigenvalues[i-1] + 1e-10);
    }

    // Entropy should be positive
    assert!(state.entropy > 0.0);

    // Participation ratio should be between 1 and n
    assert!(state.participation_ratio >= 0.99);
    assert!(state.participation_ratio <= n as f64 + 0.01);
}

#[test]
fn test_conservation_monitor() {
    let mut monitor = ConservationMonitor::new(0.03);

    // Simulate constant I values
    for _ in 0..20 {
        let C = random_coupling(5, 42); // Same coupling = same I
        let state = spectral_state(&C).unwrap();
        let status = monitor.step(&state);
        assert!(status.cv < 0.001); // Should be near-zero for static coupling
    }

    let status = monitor.step(&spectral_state(&random_coupling(5, 42)).unwrap());
    assert_eq!(status.alert, Alert::None);
}

#[test]
fn test_commutator_norm_identity() {
    // [I, C] = 0 for any C
    let n = 5;
    let diag = DVector::from_element(n, 1.0);
    let C = random_coupling(n, 99);
    let comm = commutator_norm(&diag, &C);
    assert_relative_eq!(comm, 0.0, epsilon = 1e-10);
}

#[test]
fn test_commutator_norm_nonzero() {
    // Non-uniform diagonal should give nonzero commutator
    let n = 5;
    let diag = DVector::from_vec(vec![1.0, 0.5, 0.1, 0.01, 0.001]);
    let C = random_coupling(n, 99);
    let comm = commutator_norm(&diag, &C);
    assert!(comm > 0.0);
}

#[test]
fn test_trajectory_static_coupling() {
    let x0 = DVector::from_vec(vec![0.5, -0.3, 0.8, -0.1, 0.6]);
    let C_static = random_coupling(5, 42);

    let result = run_trajectory(
        &x0,
        &|_| C_static.clone(),
        &tanh_activation,
        100,
    );

    // Static coupling → CV should be ~0
    assert!(result.cv < 0.001, "CV = {} should be ~0 for static coupling", result.cv);
}

#[test]
fn test_trajectory_hebbian_coupling() {
    let x0 = DVector::from_vec(vec![0.5, -0.3, 0.8, -0.1, 0.6, 0.2, -0.7, 0.4, 0.1, -0.5]);

    let result = run_trajectory(
        &x0,
        &|x| hebbian_coupling(x, x.len()),
        &tanh_activation,
        100,
    );

    // Hebbian converges to rank-1 fast → should have low CV
    println!("Hebbian CV: {}", result.cv);
    // Hebbian with tanh should converge quickly → low CV
    assert!(result.cv < 0.1, "Hebbian CV = {} should be low", result.cv);
}

#[test]
fn test_participation_entropy_bounds() {
    // Identity matrix: all eigenvalues equal → maximum entropy
    let n = 5;
    let I = DMatrix::identity(n, n);
    let state = spectral_state(&I).unwrap();
    let max_entropy = (n as f64).ln(); // Maximum entropy for n equal eigenvalues
    assert_relative_eq!(state.entropy, max_entropy, epsilon = 1e-10);

    // Rank-1: minimum entropy (0)
    let x = DVector::from_vec(vec![1.0, 2.0, 3.0]);
    let C = &x * &x.transpose() / 3.0;
    let state = spectral_state(&C).unwrap();
    assert_relative_eq!(state.entropy, 0.0, epsilon = 1e-10);
}

#[test]
fn test_regime_classification() {
    // Rank-1 → Structural
    let x = DVector::from_vec(vec![1.0, 2.0, 3.0]);
    let C_rank1 = &x * &x.transpose() / 3.0;
    let state = spectral_state(&C_rank1).unwrap();
    let mut monitor = ConservationMonitor::new(0.03);
    let status = monitor.step(&state);
    assert_eq!(status.regime, Regime::Structural);

    // Random full-rank → should be Dynamical (CV=0 for static)
    let C_full = random_coupling(10, 42);
    let state = spectral_state(&C_full).unwrap();
    let mut monitor2 = ConservationMonitor::new(0.03);
    for _ in 0..20 {
        let status = monitor2.step(&state);
    }
    let status = monitor2.step(&state);
    // Full rank with CV=0 → Dynamical (effective_rank > 1.5)
    assert!(status.spectral.effective_rank > 1.5, "full rank should have effective_rank > 1.5, got {}", status.spectral.effective_rank);
    assert!(matches!(status.regime, Regime::Dynamical));
}

#[test]
fn test_saturation_diagonal() {
    let z = DVector::from_vec(vec![0.0, 1.0, -1.0, 5.0, -5.0]);
    let d = saturation_diagonal(&z);

    // At z=0, sech²(0) = 1
    assert_relative_eq!(d[0], 1.0, epsilon = 1e-10);
    // At z=5, sech²(5) ≈ 0 (saturated)
    assert!(d[3] < 0.001);
    // Should be between 0 and 1
    for &di in d.iter() {
        assert!(di >= 0.0 && di <= 1.0);
    }
}

#[test]
fn test_attention_coupling() {
    let x = DVector::from_vec(vec![0.5, -0.3, 0.8, -0.1, 0.6]);
    let C = attention_coupling(&x, 1.0);

    // Should be symmetric
    for i in 0..5 {
        for j in 0..5 {
            assert_relative_eq!(C[(i,j)], C[(j,i)], epsilon = 1e-10);
        }
    }

    // Should have positive eigenvalues
    let state = spectral_state(&C).unwrap();
    assert!(state.eigenvalues.iter().all(|&e| e > 0.0));
}
