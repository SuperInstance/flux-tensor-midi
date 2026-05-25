/*
 * benchmark_v2.c — Enhanced benchmark with min/max/mean, cache warmup,
 *                  cycles-per-op via __rdtsc, and comparison reporting
 *
 * Tests: eisenstein_snap, eisenstein_snap_avx2, hpdf_sample,
 *        hpdf_sample_fast, bma_detect, bma_detect_word,
 *        div360 arithmetic, shell_decompose, fib_spline_search
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include <stdint.h>

#include "deadband.h"

/* Include optimized headers */
typedef struct { double x, y; } Vec2Fast;
extern void hpdf_sample_batch(Vec2Fast* out, int n, uint64_t seed);
extern int bma_detect_word(const uint8_t* seq, int n);
extern int bma_detect_opt(const uint8_t* seq, int n);

typedef struct {
    double sx, sy, err;
    int64_t a, b;
} SnapResultSingle;
extern void eisenstein_snap_batch(const double* x, const double* y, int n,
                                  SnapResultSingle* results);
extern void eisenstein_snap_batch_avx2(const double* x, const double* y, int n,
                                       SnapResultSingle* results);

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static inline double now_sec(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static inline uint64_t rdtsc_start(void)
{
    unsigned int lo, hi;
    __asm__ __volatile__ ("cpuid" : : : "%rax", "%rbx", "%rcx", "%rdx");
    __asm__ __volatile__ ("rdtsc" : "=a" (lo), "=d" (hi));
    return ((uint64_t)hi << 32) | lo;
}

static inline uint64_t rdtsc_end(void)
{
    unsigned int lo, hi;
    __asm__ __volatile__ ("rdtscp" : "=a" (lo), "=d" (hi));
    __asm__ __volatile__ ("cpuid" : : : "%rax", "%rbx", "%rcx", "%rdx");
    return ((uint64_t)hi << 32) | lo;
}

typedef struct {
    double min_ns, max_ns, mean_ns;
    double min_cyc, max_cyc, mean_cyc;
    double total_ms;
    int runs;
} BenchResult;

/* Run a benchmark function multiple times, report stats */
static void print_bench(const char* name, BenchResult* r)
{
    printf("  %-35s %8.1f %8.1f %8.1f | %7.0f %7.0f %7.0f | %7.2f\n",
           name, r->min_ns, r->mean_ns, r->max_ns,
           r->min_cyc, r->mean_cyc, r->max_cyc,
           r->total_ms);
}

#define BENCH_HEADER() \
    printf("  %-35s %9s %9s %9s | %7s %7s %7s | %7s\n", \
           "Benchmark", "min(ns)", "mean(ns)", "max(ns)", \
           "min(cyc)", "mean(cyc)", "max(cyc)", "total(ms)"); \
    printf("  %-35s %9s %9s %9s | %7s %7s %7s | %7s\n", \
           "───────", "───────", "────────", "───────", \
           "───────", "────────", "───────", "───────")

/* ── Fill helpers ── */
static void fill_random_double(double* arr, int n, double lo, double hi, unsigned seed)
{
    srand(seed);
    for (int i = 0; i < n; i++) {
        arr[i] = lo + ((double)rand() / RAND_MAX) * (hi - lo);
    }
}

static void fill_random_bits(uint8_t* arr, int n, unsigned seed)
{
    srand(seed);
    for (int i = 0; i < n; i++) {
        arr[i] = rand() & 1;
    }
}

/* Cache warmup: touch all memory */
static void warmup(void* p, size_t sz)
{
    volatile char* cp = (volatile char*)p;
    for (size_t i = 0; i < sz; i += 64) cp[i];
}

/* ════════════════════════════════════════════════════════════════ */
int main(void)
{
    printf("═══════════════════════════════════════════════════════════════\n");
    printf("  DEADBAND FRAMEWORK — BENCHMARK V2\n");
    printf("  10 runs each, cache warmup, ns/op + cycles/op\n");
    printf("═══════════════════════════════════════════════════════════════\n\n");

    const int RUNS = 10;

    /* ── 1. Eisenstein Snap ─────────────────────────────────── */
    printf("── 1. Eisenstein Snap ──\n");
    {
        const int N = 100000;
        double* x = malloc(N * sizeof(double));
        double* y = malloc(N * sizeof(double));
        SnapResultSingle* res = malloc(N * sizeof(SnapResultSingle));
        fill_random_double(x, N, -10.0, 10.0, 42);
        fill_random_double(y, N, -10.0, 10.0, 43);
        warmup(x, N * sizeof(double));
        warmup(y, N * sizeof(double));

        BENCH_HEADER();

        /* Original scalar (single snap, N times) */
        {
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                for (int i = 0; i < N; i++) {
                    SnapResult sr = eisenstein_snap(x[i], y[i]);
                    (void)sr;
                }
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / N * 1e9;
                double cyc = (double)(t3 - t0) / N;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("eisenstein_snap (scalar, original)", &br);
        }

        /* Batch scalar optimized */
        {
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                eisenstein_snap_batch(x, y, N, res);
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / N * 1e9;
                double cyc = (double)(t3 - t0) / N;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("eisenstein_snap_batch (scalar opt)", &br);
        }

        /* Batch AVX2 */
        {
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                eisenstein_snap_batch_avx2(x, y, N, res);
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / N * 1e9;
                double cyc = (double)(t3 - t0) / N;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("eisenstein_snap_batch_avx2 (4-wide)", &br);
        }

        free(x); free(y); free(res);
    }

    /* ── 2. HPDF Sampling ────────────────────────────────────── */
    printf("\n── 2. HPDF Sampling ──\n");
    {
        const int N = 1000000;
        BENCH_HEADER();

        /* Original hpdf_sample */
        {
            srand(12345);
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                volatile double dummy = 0;
                for (int i = 0; i < N; i++) {
                    Vec2 v = hpdf_sample();
                    dummy += v.x + v.y;
                }
                (void)dummy;
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / N * 1e9;
                double cyc = (double)(t3 - t0) / N;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("hpdf_sample (original, rand())", &br);
        }

        /* Fast xorshift batch */
        {
            Vec2Fast* out = malloc(N * sizeof(Vec2Fast));
            warmup(out, N * sizeof(Vec2Fast));
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                hpdf_sample_batch(out, N, r + 1);
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / N * 1e9;
                double cyc = (double)(t3 - t0) / N;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("hpdf_sample_batch (xorshift128+)", &br);
            free(out);
        }
    }

    /* ── 3. BMA ─────────────────────────────────────────────── */
    printf("\n── 3. Berlekamp-Massey ──\n");
    {
        const int N = 1000; /* sequences */
        const int SEQ_LEN = 256;
        uint8_t** seqs = malloc(N * sizeof(uint8_t*));
        for (int i = 0; i < N; i++) {
            seqs[i] = malloc(SEQ_LEN);
            fill_random_bits(seqs[i], SEQ_LEN, i);
        }
        BENCH_HEADER();

        /* Original byte-level */
        {
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                volatile int dummy = 0;
                for (int i = 0; i < N; i++) {
                    dummy += bma_detect(seqs[i], SEQ_LEN);
                }
                (void)dummy;
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / N * 1e9;
                double cyc = (double)(t3 - t0) / N;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("bma_detect (original, byte-level)", &br);
        }

        /* Word-level optimized */
        {
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                volatile int dummy = 0;
                for (int i = 0; i < N; i++) {
                    dummy += bma_detect_word(seqs[i], SEQ_LEN);
                }
                (void)dummy;
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / N * 1e9;
                double cyc = (double)(t3 - t0) / N;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("bma_detect_word (64-bit words)", &br);
        }

        for (int i = 0; i < N; i++) free(seqs[i]);
        free(seqs);
    }

    /* ── 4. div360 Arithmetic ────────────────────────────────── */
    printf("\n── 4. /360 Arithmetic ──\n");
    {
        const int OPS = 1000000;
        int64_t* vals = malloc(OPS * sizeof(int64_t));
        srand(999);
        for (int i = 0; i < OPS; i++) vals[i] = rand() % 720 - 360;
        warmup(vals, OPS * sizeof(int64_t));
        BENCH_HEADER();

        {
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                int64_t acc = 0;
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                for (int i = 0; i < OPS; i++) {
                    acc = div360_add(acc, vals[i]);
                }
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / OPS * 1e9;
                double cyc = (double)(t3 - t0) / OPS;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
                (void)acc;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("div360_add (1M ops)", &br);
        }
        free(vals);
    }

    /* ── 5. Shell Decompose ─────────────────────────────────── */
    printf("\n── 5. Shell Decompose ──\n");
    {
        const int N = 100000;
        double(*covs)[4] = malloc(N * sizeof(*covs));
        srand(555);
        for (int i = 0; i < N; i++) {
            covs[i][0] = (double)rand() / RAND_MAX * 10;
            covs[i][1] = covs[i][2] = (double)rand() / RAND_MAX * 5 - 2.5;
            covs[i][3] = (double)rand() / RAND_MAX * 10;
        }
        warmup(covs, N * sizeof(*covs));
        BENCH_HEADER();

        {
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                volatile double dummy = 0;
                for (int i = 0; i < N; i++) {
                    ShellResult sr = shell_decompose(covs[i]);
                    dummy += sr.lam1;
                }
                (void)dummy;
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) / N * 1e9;
                double cyc = (double)(t3 - t0) / N;
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("shell_decompose (100K)", &br);
        }
        free(covs);
    }

    /* ── 6. Fib Spline Search ────────────────────────────────── */
    printf("\n── 6. Fibonacci-Spline Search ──\n");
    {
        const int N = 10000;
        const int D = 2;
        double* db = malloc(N * D * sizeof(double));
        for (int i = 0; i < N; i++) {
            double angle = 2.0 * M_PI * i / N;
            db[i*D+0] = cos(angle);
            db[i*D+1] = sin(angle);
        }
        double query[2] = {0.707, 0.707};
        SearchResult results[10];
        warmup(db, N * D * sizeof(double));
        BENCH_HEADER();

        {
            BenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                uint64_t t0 = rdtsc_start();
                double t1 = now_sec();
                fib_spline_search(query, db, N, D, 10, results);
                double t2 = now_sec();
                uint64_t t3 = rdtsc_end();
                double ns = (t2 - t1) * 1e6; /* single search → microseconds */
                double cyc = (double)(t3 - t0);
                if (r == 0 || ns < br.min_ns) br.min_ns = ns;
                if (r == 0 || ns > br.max_ns) br.max_ns = ns;
                if (r == 0 || cyc < br.min_cyc) br.min_cyc = cyc;
                if (r == 0 || cyc > br.max_cyc) br.max_cyc = cyc;
                br.mean_ns += ns;
                br.mean_cyc += cyc;
                br.total_ms += (t2 - t1) * 1000;
            }
            br.mean_ns /= RUNS;
            br.mean_cyc /= RUNS;
            br.runs = RUNS;
            print_bench("fib_spline_search (10K db, μs/op)", &br);
        }
        free(db);
    }

    printf("\n═══════════════════════════════════════════════════════════════\n");
    printf("  BENCHMARK V2 COMPLETE\n");
    printf("═══════════════════════════════════════════════════════════════\n");
    return 0;
}
