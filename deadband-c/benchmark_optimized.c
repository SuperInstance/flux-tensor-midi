/*
 * benchmark_optimized.c — Comprehensive baseline vs optimized benchmarks
 *
 * Tests:
 *   1. Eisenstein snap: 10M points, baseline vs AVX2 batch
 *   2. HPDF: 10M samples, baseline (rand) vs fast (xorshift128+)
 *   3. BMA: 100K streams (256-bit each), baseline vs word-level
 *   4. /360: 10M ops (baseline only — already optimal integer arithmetic)
 *
 * Compile:
 *   gcc -O3 -mavx2 -o bench_opt benchmark_optimized.c \
 *       eisenstein.c eisenstein_avx2.c hpdf.c hpdf_fast.c \
 *       bma.c bma_word.c div360.c deadband.c shell.c fib_spline.c -lm
 */

#define _POSIX_C_SOURCE 199309L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

/* ── Pull in baseline functions ─────────────────────────────────── */
#include "deadband.h"

/* ── Pull in optimized functions ────────────────────────────────── */

/* eisenstein_avx2.c provides: */
typedef struct { double x, y; } Vec2Fast;
extern void eisenstein_snap_batch(const double* x, const double* y, int n, void* results);
extern void eisenstein_snap_batch_avx2(const double* x, const double* y, int n, void* results);

/* hpdf_fast.c provides: */
extern void hpdf_sample_batch(Vec2Fast* out, int n, uint64_t seed);

/* bma_word.c provides: */
extern int bma_detect_word(const uint8_t* seq, int n);
extern int bma_detect_opt(const uint8_t* seq, int n);

/* ── Timing helpers ─────────────────────────────────────────────── */

static double now_sec(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* ── Random helpers ─────────────────────────────────────────────── */

static uint64_t splitmix64(uint64_t* state)
{
    uint64_t z = (*state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static double rand_double(uint64_t* state)
{
    return (splitmix64(state) >> 11) * (1.0 / 9007199254740992.0);  /* [0,1) */
}

/* ════════════════════════════════════════════════════════════════════
 * 1. Eisenstein Snap Benchmark
 * ════════════════════════════════════════════════════════════════════ */

typedef struct {
    double sx, sy, err;
    int64_t a, b;
} SnapResultSingle;

/* External from eisenstein_avx2.c */
/* Already declared above via extern void* */

static void bench_eisenstein(int N)
{
    printf("═══ Eisenstein Snap: %d points ═══\n", N);

    /* Generate test data in [-10, 10] x [-10, 10] */
    double* xs = (double*)malloc(N * sizeof(double));
    double* ys = (double*)malloc(N * sizeof(double));
    SnapResultSingle* res_base = (SnapResultSingle*)malloc(N * sizeof(SnapResultSingle));
    SnapResultSingle* res_avx2 = (SnapResultSingle*)malloc(N * sizeof(SnapResultSingle));

    uint64_t rng = 42;
    for (int i = 0; i < N; i++) {
        xs[i] = rand_double(&rng) * 20.0 - 10.0;
        ys[i] = rand_double(&rng) * 20.0 - 10.0;
    }

    /* ── Baseline: scalar eisenstein_snap() one at a time ── */
    double t0 = now_sec();
    for (int i = 0; i < N; i++) {
        SnapResult r = eisenstein_snap(xs[i], ys[i]);
        res_base[i].sx  = r.sx;
        res_base[i].sy  = r.sy;
        res_base[i].err = r.err;
        res_base[i].a   = r.a;
        res_base[i].b   = r.b;
    }
    double t_base = now_sec() - t0;

    /* ── Scalar batch (optimized with LUT) ── */
    t0 = now_sec();
    eisenstein_snap_batch(xs, ys, N, res_avx2);
    double t_batch = now_sec() - t0;

    /* ── AVX2 batch (4-wide SIMD) ── */
    t0 = now_sec();
    eisenstein_snap_batch_avx2(xs, ys, N, res_avx2);
    double t_avx2 = now_sec() - t0;

    /* ── Accuracy verification: compare AVX2 vs baseline ── */
    int mismatches = 0;
    double max_err_diff = 0;
    for (int i = 0; i < N; i++) {
        /* AVX2 uses simple rounding (no neighbour search), so some
           results may differ from the 9-neighbour baseline */
        double dx = res_base[i].sx - res_avx2[i].sx;
        double dy = res_base[i].sy - res_avx2[i].sy;
        double dist = sqrt(dx*dx + dy*dy);
        if (dist > 0.01) mismatches++;
        double err_diff = fabs(res_base[i].err - res_avx2[i].err);
        if (err_diff > max_err_diff) max_err_diff = err_diff;
    }

    printf("  Baseline (scalar, 9-neighbour):  %.3f ms  (%.0f ops/sec)\n",
           t_base * 1000, N / t_base);
    printf("  Scalar batch (LUT optimized):    %.3f ms  (%.0f ops/sec)  %.2fx\n",
           t_batch * 1000, N / t_batch, t_base / t_batch);
    printf("  AVX2 batch (4-wide SIMD):        %.3f ms  (%.0f ops/sec)  %.2fx\n",
           t_avx2 * 1000, N / t_avx2, t_base / t_avx2);
    printf("  Accuracy: %d/%d exact matches (AVX2 uses fast-path rounding)\n",
           N - mismatches, N);
    printf("  Max error difference: %.6f\n", max_err_diff);

    free(xs); free(ys); free(res_base); free(res_avx2);
}

/* ════════════════════════════════════════════════════════════════════
 * 2. HPDF Benchmark
 * ════════════════════════════════════════════════════════════════════ */

static void bench_hpdf(int N)
{
    printf("\n═══ HPDF Sampling: %d samples ═══\n", N);

    Vec2*       res_base = (Vec2*)malloc(N * sizeof(Vec2));
    Vec2Fast*   res_fast = (Vec2Fast*)malloc(N * sizeof(Vec2Fast));

    /* ── Baseline: hpdf_sample() one at a time (uses rand()) ── */
    srand(42);
    double t0 = now_sec();
    for (int i = 0; i < N; i++) {
        res_base[i] = hpdf_sample();
    }
    double t_base = now_sec() - t0;

    /* ── Fast: xorshift128+ batch ── */
    t0 = now_sec();
    hpdf_sample_batch(res_fast, N, 42);
    double t_fast = now_sec() - t0;

    /* ── Verify statistics ── */
    double sx = 0, sy = 0, sx2 = 0, sy2 = 0;
    for (int i = 0; i < N; i++) {
        sx  += res_fast[i].x;  sx2 += res_fast[i].x * res_fast[i].x;
        sy  += res_fast[i].y;  sy2 += res_fast[i].y * res_fast[i].y;
    }
    double mean_x = sx / N, mean_y = sy / N;
    double var_x  = sx2 / N - mean_x * mean_x;
    double var_y  = sy2 / N - mean_y * mean_y;
    double expected_var = 5.0 / 24.0;

    printf("  Baseline (rand + rejection):     %.3f ms  (%.0f samples/sec)\n",
           t_base * 1000, N / t_base);
    printf("  Fast (xorshift128+ batch):       %.3f ms  (%.0f samples/sec)  %.2fx\n",
           t_fast * 1000, N / t_fast, t_base / t_fast);
    printf("  Fast stats: mean=(%.6f, %.6f) var=(%.6f, %.6f)\n",
           mean_x, mean_y, var_x, var_y);
    printf("  Expected variance: %.6f  (error: %.2f%%)\n",
           expected_var, fabs(var_x - expected_var) / expected_var * 100);

    free(res_base); free(res_fast);
}

/* ════════════════════════════════════════════════════════════════════
 * 3. BMA Benchmark
 * ════════════════════════════════════════════════════════════════════ */

static void bench_bma(int num_streams, int seq_len)
{
    printf("\n═══ BMA: %d streams × %d bits ═══\n", num_streams, seq_len);

    /* Generate random binary sequences */
    uint8_t** streams = (uint8_t**)malloc(num_streams * sizeof(uint8_t*));
    uint64_t rng = 12345;
    for (int s = 0; s < num_streams; s++) {
        streams[s] = (uint8_t*)malloc(seq_len);
        for (int i = 0; i < seq_len; i++) {
            streams[s][i] = splitmix64(&rng) & 1;
        }
    }

    int* results_base = (int*)malloc(num_streams * sizeof(int));
    int* results_word = (int*)malloc(num_streams * sizeof(int));

    /* ── Baseline: bma_detect() ── */
    double t0 = now_sec();
    for (int s = 0; s < num_streams; s++) {
        results_base[s] = bma_detect(streams[s], seq_len);
    }
    double t_base = now_sec() - t0;

    /* ── Word-level: bma_detect_word() ── */
    t0 = now_sec();
    for (int s = 0; s < num_streams; s++) {
        results_word[s] = bma_detect_word(streams[s], seq_len);
    }
    double t_word = now_sec() - t0;

    /* ── Verify correctness ── */
    int mismatches = 0;
    for (int s = 0; s < num_streams; s++) {
        if (results_base[s] != results_word[s]) mismatches++;
    }

    long long total_bits = (long long)num_streams * seq_len;
    printf("  Baseline (scalar int arrays):    %.3f ms  (%.0f bits/sec)\n",
           t_base * 1000, total_bits / t_base);
    printf("  Word-level (uint64_t XOR):       %.3f ms  (%.0f bits/sec)  %.2fx\n",
           t_word * 1000, total_bits / t_word, t_base / t_word);
    printf("  Correctness: %d/%d match\n", num_streams - mismatches, num_streams);

    /* Sample results */
    printf("  Sample LFSR lengths:");
    for (int s = 0; s < 5 && s < num_streams; s++) {
        printf(" [%d]=%d", s, results_base[s]);
    }
    printf("\n");

    for (int s = 0; s < num_streams; s++) free(streams[s]);
    free(streams); free(results_base); free(results_word);
}

/* ════════════════════════════════════════════════════════════════════
 * 4. /360 Benchmark
 * ════════════════════════════════════════════════════════════════════ */

static void bench_div360(int N)
{
    printf("\n═══ /360 Arithmetic: %d ops ═══\n", N);

    /* Generate random values in [0, 359] */
    int64_t* va = (int64_t*)malloc(N * sizeof(int64_t));
    int64_t* vb = (int64_t*)malloc(N * sizeof(int64_t));
    uint64_t rng = 999;
    for (int i = 0; i < N; i++) {
        va[i] = (int64_t)(splitmix64(&rng) % 360);
        vb[i] = (int64_t)(splitmix64(&rng) % 360);
    }

    int64_t acc = 0;

    /* ── Add ── */
    double t0 = now_sec();
    for (int i = 0; i < N; i++) {
        acc ^= div360_add(va[i], vb[i]);
    }
    double t_add = now_sec() - t0;

    /* ── Sub ── */
    t0 = now_sec();
    for (int i = 0; i < N; i++) {
        acc ^= div360_sub(va[i], vb[i]);
    }
    double t_sub = now_sec() - t0;

    /* ── Mul ── */
    t0 = now_sec();
    for (int i = 0; i < N; i++) {
        acc ^= div360_mul(va[i], vb[i]);
    }
    double t_mul = now_sec() - t0;

    printf("  div360_add: %.3f ms  (%.0f ops/sec)\n", t_add * 1000, N / t_add);
    printf("  div360_sub: %.3f ms  (%.0f ops/sec)\n", t_sub * 1000, N / t_sub);
    printf("  div360_mul: %.3f ms  (%.0f ops/sec)\n", t_mul * 1000, N / t_mul);
    printf("  (Already optimal — pure integer arithmetic, zero drift)\n");
    /* Prevent optimizer from removing the loop */
    printf("  Checksum: %lld\n", (long long)acc);

    free(va); free(vb);
}

/* ════════════════════════════════════════════════════════════════════
 * Main
 * ════════════════════════════════════════════════════════════════════ */

int main(void)
{
    printf("╔══════════════════════════════════════════════════════════╗\n");
    printf("║  Deadband C Library — Optimized Benchmark Suite         ║\n");
    printf("║  Compiler: gcc -O3 -mavx2                               ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n\n");

    bench_eisenstein(10000000);
    bench_hpdf(10000000);
    bench_bma(100000, 256);
    bench_div360(10000000);

    printf("\n╔══════════════════════════════════════════════════════════╗\n");
    printf("║  Benchmark complete.                                     ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n");
    return 0;
}
