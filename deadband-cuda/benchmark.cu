/*
 * benchmark.cu — Benchmark runner for Deadband CUDA kernels
 */

#include "deadband_cuda.h"
#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

static double get_time_sec(void) {
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    cudaEventRecord(start);
    cudaEventSynchronize(start);
    /* We'll use cudaEventElapsedTime directly in each benchmark */
    return 0;
}

/* Helper: create random doubles in range [lo, hi] */
static void fill_random(double* arr, int N, double lo, double hi, unsigned seed) {
    srand(seed);
    for (int i = 0; i < N; i++) {
        double r = (double)rand() / (double)RAND_MAX;
        arr[i] = lo + r * (hi - lo);
    }
}

int run_benchmarks(void) {
    cudaError_t err;
    printf("═══════════════════════════════════════════════════════════════\n");
    printf("  DEADBAND FRAMEWORK — GPU BENCHMARK\n");
    printf("  RTX 4050 Laptop GPU (sm_89, 6.4GB VRAM)\n");
    printf("═══════════════════════════════════════════════════════════════\n\n");

    /* Show GPU info */
    cudaDeviceProp prop;
    err = cudaGetDeviceProperties(&prop, 0);
    if (err != cudaSuccess) {
        fprintf(stderr, "ERROR: No CUDA device found (%s)\n", cudaGetErrorString(err));
        fprintf(stderr, "Running in COMPUTE-ONLY mode (no GPU available in WSL)\n\n");
    } else {
        printf("GPU: %s\n", prop.name);
        printf("Compute Capability: %d.%d\n", prop.major, prop.minor);
        printf("VRAM: %.1f GB\n", prop.totalGlobalMem / 1e9);
        printf("SM Count: %d\n", prop.multiProcessorCount);
        printf("\n");
    }

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    /* ── Benchmark 1: Eisenstein Snap ─────────────────────────── */
    printf("── Benchmark 1: Eisenstein Snap (200K agents, 1000 steps) ──\n");
    {
        const int N = 200000;
        const int STEPS = 1000;
        double *hx = (double*)malloc(N * sizeof(double));
        double *hy = (double*)malloc(N * sizeof(double));
        fill_random(hx, N, -100.0, 100.0, 42);
        fill_random(hy, N, -100.0, 100.0, 43);

        double *d_x, *d_y, *d_sx, *d_sy, *d_err;
        cudaMalloc(&d_x, N * sizeof(double));
        cudaMalloc(&d_y, N * sizeof(double));
        cudaMalloc(&d_sx, N * sizeof(double));
        cudaMalloc(&d_sy, N * sizeof(double));
        cudaMalloc(&d_err, N * sizeof(double));

        cudaMemcpy(d_x, hx, N * sizeof(double), cudaMemcpyHostToDevice);
        cudaMemcpy(d_y, hy, N * sizeof(double), cudaMemcpyHostToDevice);

        int block = 256;
        int grid = (N + block - 1) / block;

        /* Warmup */
        for (int w = 0; w < 5; w++) {
            /* Need the kernel inline — use the one from eisenstein_snap.cu */
        }

        /* We'll use the host API for simplicity */
        float total_ms = 0;
        cudaEventRecord(start);

        /* Run snap 1000 times, swapping buffers */
        double *cur_x = d_x, *cur_y = d_y;
        for (int s = 0; s < STEPS; s++) {
            cudaMemcpy(d_sx, cur_x, N * sizeof(double), cudaMemcpyDeviceToDevice);

            /* Inline snap kernel call — we need to include the kernel */
            /* For benchmark, just call the public API in a loop */
        }

        /* Actually, let's use the swarm sim which does exactly this */
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);

        /* Use swarm sim for accurate timing */
        SwarmResult sr;
        cuda_swarm_sim(N, STEPS, &sr);

        printf("  Steps/sec:     %.1f\n", sr.steps_per_sec);
        printf("  Snapped drift: %.15e (should be ~0)\n", sr.snapped_drift);
        printf("  Float64 drift: %.15e (grows with steps)\n", sr.float64_drift);
        printf("  Memory used:   %.1f MB\n\n", sr.memory_bytes / 1e6);

        cudaFree(d_x); cudaFree(d_y); cudaFree(d_sx); cudaFree(d_sy); cudaFree(d_err);
        free(hx); free(hy);
    }

    /* ── Benchmark 2: HPDF Dither ────────────────────────────── */
    printf("── Benchmark 2: HPDF Dither (200K points) ──\n");
    {
        const int N = 200000;
        const int RUNS = 100;
        double* signal = (double*)malloc(N * sizeof(double));
        fill_random(signal, N, -1.0, 1.0, 100);

        cudaEventRecord(start);
        for (int r = 0; r < RUNS; r++) {
            cuda_hpdf_dither(signal, N, r * 1000ULL + 42);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);

        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        double total_pts = (double)N * RUNS;
        double pts_per_sec = total_pts / (ms / 1000.0);

        printf("  Throughput:    %.2f M points/sec\n", pts_per_sec / 1e6);
        printf("  Total time:    %.2f ms (%d runs)\n\n", ms, RUNS);

        free(signal);
    }

    /* ── Benchmark 3: Batch Deadband Check ───────────────────── */
    printf("── Benchmark 3: Batch Deadband (1000 streams × 100 length) ──\n");
    {
        const int N_STREAMS = 1000;
        const int STREAM_LEN = 100;
        const int RUNS = 100;

        double* data = (double*)malloc((size_t)N_STREAMS * STREAM_LEN * sizeof(double));
        srand(200);
        for (int i = 0; i < N_STREAMS * STREAM_LEN; i++) {
            data[i] = (rand() % 2) ? 1.0 : 0.0;
        }

        int* results = NULL;

        cudaEventRecord(start);
        for (int r = 0; r < RUNS; r++) {
            if (results) free(results);
            cuda_deadband_check(data, N_STREAMS, STREAM_LEN, 8, &results);
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);

        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        double total_streams = (double)N_STREAMS * RUNS;
        double streams_per_sec = total_streams / (ms / 1000.0);

        /* Count perceivable */
        int perceivable = 0;
        for (int i = 0; i < N_STREAMS; i++) perceivable += results[i];

        printf("  Throughput:    %.0f streams/sec\n", streams_per_sec);
        printf("  Perceivable:   %d/%d (%.1f%%)\n",
               perceivable, N_STREAMS, 100.0 * perceivable / N_STREAMS);
        printf("  Total time:    %.2f ms (%d runs)\n\n", ms, RUNS);

        free(data);
        free(results);
    }

    /* ── Benchmark 4: Swarm Scaling ──────────────────────────── */
    printf("── Benchmark 4: Swarm Scaling (1000 steps) ──\n");
    {
        int sizes[] = {50000, 100000, 200000};
        const int STEPS = 1000;

        printf("  %-10s %12s %15s %15s %10s\n",
               "Agents", "Steps/sec", "Snapped Drift", "Float64 Drift", "Memory");
        printf("  %-10s %12s %15s %15s %10s\n",
               "──────", "─────────", "─────────────", "─────────────", "──────");

        for (int i = 0; i < 3; i++) {
            SwarmResult sr;
            cuda_swarm_sim(sizes[i], STEPS, &sr);
            printf("  %-10d %12.1f %15.2e %15.2e %7.1f MB\n",
                   sizes[i], sr.steps_per_sec, sr.snapped_drift, sr.float64_drift,
                   sr.memory_bytes / 1e6);
        }
        printf("\n");
    }

    printf("═══════════════════════════════════════════════════════════════\n");
    printf("  BENCHMARKS COMPLETE\n");
    printf("═══════════════════════════════════════════════════════════════\n");

    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    return 0;
}

int main(void) {
    return run_benchmarks();
}
