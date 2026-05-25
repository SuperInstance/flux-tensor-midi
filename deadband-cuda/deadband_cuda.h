#ifndef DEADBAND_CUDA_H
#define DEADBAND_CUDA_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * deadband_cuda.h — GPU kernels for the Deadband Framework
 * Target: NVIDIA GeForce RTX 4050 Laptop GPU (sm_89, 6.4GB VRAM)
 *
 * Eisenstein lattice basis: e1 = (1, 0), e2 = (-0.5, sqrt(3)/2)
 */

/* ── Eisenstein Snap ─────────────────────────────────────────────── */

/*
 * Snap N (x,y) positions to the Eisenstein lattice in parallel.
 * Each thread handles one point.
 *
 * Returns device pointers sx, sy, error (caller must cudaFree).
 */
int cuda_eisenstein_snap(const double* x, const double* y, int N,
                         double** sx, double** sy, double** error);

/* ── HPDF Dither ─────────────────────────────────────────────────── */

/*
 * Add HPDF (Hexagonal Probability Density Function) dither noise
 * to N signal points using CURAND Philox generator.
 */
int cuda_hpdf_dither(double* signal, int N, unsigned long long seed);

/* ── Deadband Perceivability Check ───────────────────────────────── */

/*
 * Batch BMA (Berlekamp-Massey Algorithm) deadband perceivability check.
 * Runs N_streams independent BMA computations in parallel.
 *
 * data:    flattened [N_streams × n] row-major (0.0 or 1.0)
 * results: device array [N_streams], 1 = perceivable, 0 = not
 */
int cuda_deadband_check(const double* data, int N_streams, int n,
                        int receiver_bits, int** results);

/* ── Swarm Simulation ────────────────────────────────────────────── */

typedef struct {
    int N;                  /* number of agents */
    int steps;              /* number of simulation steps */
    double steps_per_sec;   /* measured throughput */
    double snapped_drift;   /* max drift on snapped positions (should be 0) */
    double float64_drift;   /* max drift on unsnapped float64 positions */
    size_t memory_bytes;    /* total GPU memory used */
} SwarmResult;

/*
 * Run full swarm simulation:
 * - N agents at random (x,y) positions
 * - Each step: snap to Eisenstein lattice
 * - Track drift for snapped vs. unsnapped positions
 * - Report timing and drift statistics
 */
int cuda_swarm_sim(int N, int steps, SwarmResult* result);

/* ── Benchmarks ──────────────────────────────────────────────────── */

int run_benchmarks(void);

#ifdef __cplusplus
}
#endif

#endif /* DEADBAND_CUDA_H */
