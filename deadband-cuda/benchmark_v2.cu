/*
 * benchmark_v2.cu — Enhanced GPU benchmark with min/max/mean, warmup,
 *                   sustained throughput test, and warp-level reductions
 *
 * Improvements over benchmark.cu:
 * 1. Run each benchmark 10 times, report min/max/mean
 * 2. Cache warmup before timing
 * 3. Sustained throughput test: 10 seconds, report steady-state steps/sec
 * 4. Compare original vs shared-memory swarm sim
 * 5. Compare original vs batch HPDF
 */

#include "deadband_cuda.h"
#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

/* Shared-mem swarm and batch HPDF prototypes */
extern int cuda_swarm_sim_shared(int N, int steps, SwarmResult* result);
extern int cuda_hpdf_dither_fast(double* signal, int N, unsigned long long seed);

static void fill_random(double* arr, int N, double lo, double hi, unsigned seed) {
    srand(seed);
    for (int i = 0; i < N; i++) {
        arr[i] = lo + ((double)rand() / RAND_MAX) * (hi - lo);
    }
}

typedef struct {
    float min_ms, max_ms, mean_ms;
    float min_tput, max_tput, mean_tput;
    int runs;
} GpuBenchResult;

static void print_gpu_bench(const char* name, GpuBenchResult* r, const char* unit)
{
    printf("  %-40s %8.2f %8.2f %8.2f | %10.1f %10.1f %10.1f %s\n",
           name, r->min_ms, r->mean_ms, r->max_ms,
           r->min_tput, r->mean_tput, r->max_tput, unit);
}

#define GPU_BENCH_HEADER() \
    printf("  %-40s %9s %9s %9s | %10s %10s %10s\n", \
           "Benchmark", "min(ms)", "mean(ms)", "max(ms)", \
           "min", "mean", "max"); \
    printf("  %-40s %9s %9s %9s | %10s %10s %10s\n", \
           "────────", "────────", "─────────", "────────", \
           "──────────", "──────────", "──────────")

int main(void)
{
    cudaError_t err;
    printf("═══════════════════════════════════════════════════════════════\n");
    printf("  DEADBAND FRAMEWORK — GPU BENCHMARK V2\n");
    printf("  10 runs each, min/max/mean, sustained throughput\n");
    printf("═══════════════════════════════════════════════════════════════\n\n");

    /* GPU info */
    cudaDeviceProp prop;
    err = cudaGetDeviceProperties(&prop, 0);
    if (err != cudaSuccess) {
        fprintf(stderr, "No CUDA device: %s\n", cudaGetErrorString(err));
        fprintf(stderr, "Cannot run GPU benchmarks without a GPU.\n");
        return 1;
    }
    printf("GPU: %s (sm_%d%d, %.1f GB VRAM, %d SMs)\n\n",
           prop.name, prop.major, prop.minor,
           prop.totalGlobalMem / 1e9, prop.multiProcessorCount);

    const int RUNS = 10;

    /* ── Benchmark 1: Swarm Sim (original vs shared) ────────── */
    printf("── Benchmark 1: Swarm Simulation (200K agents, 1000 steps) ──\n");
    GPU_BENCH_HEADER();
    {
        const int N = 200000;
        const int STEPS = 1000;

        /* Original */
        {
            GpuBenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                SwarmResult sr;
                cuda_swarm_sim(N, STEPS, &sr);
                float ms = STEPS / sr.steps_per_sec * 1000.0f;
                if (r == 0 || ms < br.min_ms) br.min_ms = ms;
                if (r == 0 || ms > br.max_ms) br.max_ms = ms;
                if (r == 0 || sr.steps_per_sec > br.max_tput || br.max_tput == 0) br.max_tput = sr.steps_per_sec;
                if (r == 0 || sr.steps_per_sec < br.min_tput || br.min_tput == 0) br.min_tput = sr.steps_per_sec;
                br.mean_ms += ms;
                br.mean_tput += sr.steps_per_sec;
            }
            br.mean_ms /= RUNS;
            br.mean_tput /= RUNS;
            br.runs = RUNS;
            print_gpu_bench("swarm_sim (original)", &br, "steps/s");
        }

        /* Shared memory */
        {
            GpuBenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                SwarmResult sr;
                cuda_swarm_sim_shared(N, STEPS, &sr);
                float ms = STEPS / sr.steps_per_sec * 1000.0f;
                if (r == 0 || ms < br.min_ms) br.min_ms = ms;
                if (r == 0 || ms > br.max_ms) br.max_ms = ms;
                if (r == 0 || sr.steps_per_sec > br.max_tput || br.max_tput == 0) br.max_tput = sr.steps_per_sec;
                if (r == 0 || sr.steps_per_sec < br.min_tput || br.min_tput == 0) br.min_tput = sr.steps_per_sec;
                br.mean_ms += ms;
                br.mean_tput += sr.steps_per_sec;
            }
            br.mean_ms /= RUNS;
            br.mean_tput /= RUNS;
            br.runs = RUNS;
            print_gpu_bench("swarm_sim_shared (shared mem + warp)", &br, "steps/s");
        }
    }

    /* ── Benchmark 2: HPDF Dither ────────────────────────────── */
    printf("\n── Benchmark 2: HPDF Dither (200K points, 100 runs) ──\n");
    GPU_BENCH_HEADER();
    {
        const int N = 200000;
        const int RUNS_PER = 100;

        /* Original */
        {
            double* signal = (double*)malloc(N * sizeof(double));
            fill_random(signal, N, -1.0, 1.0, 100);

            cudaEvent_t start, stop;
            cudaEventCreate(&start);
            cudaEventCreate(&stop);

            /* Warmup */
            cuda_hpdf_dither(signal, N, 0);

            GpuBenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                fill_random(signal, N, -1.0, 1.0, 100 + r);
                cudaEventRecord(start);
                for (int j = 0; j < RUNS_PER; j++) {
                    cuda_hpdf_dither(signal, N, r * 1000ULL + j);
                }
                cudaEventRecord(stop);
                cudaEventSynchronize(stop);
                float ms;
                cudaEventElapsedTime(&ms, start, stop);
                double tput = (double)N * RUNS_PER / (ms / 1000.0) / 1e6;
                if (r == 0 || ms < br.min_ms) br.min_ms = ms;
                if (r == 0 || ms > br.max_ms) br.max_ms = ms;
                if (r == 0 || tput > br.max_tput || br.max_tput == 0) br.max_tput = tput;
                if (r == 0 || tput < br.min_tput || br.min_tput == 0) br.min_tput = tput;
                br.mean_ms += ms;
                br.mean_tput += tput;
            }
            br.mean_ms /= RUNS;
            br.mean_tput /= RUNS;
            br.runs = RUNS;
            print_gpu_bench("hpdf_dither (original)", &br, "Mpts/s");

            cudaEventDestroy(start);
            cudaEventDestroy(stop);
            free(signal);
        }

        /* Batch (fast) */
        {
            double* signal = (double*)malloc(N * sizeof(double));

            cudaEvent_t start, stop;
            cudaEventCreate(&start);
            cudaEventCreate(&stop);

            /* Warmup */
            cuda_hpdf_dither_fast(signal, N, 0);

            GpuBenchResult br = {0};
            for (int r = 0; r < RUNS; r++) {
                fill_random(signal, N, -1.0, 1.0, 200 + r);
                cudaEventRecord(start);
                for (int j = 0; j < RUNS_PER; j++) {
                    cuda_hpdf_dither_fast(signal, N, r * 1000ULL + j);
                }
                cudaEventRecord(stop);
                cudaEventSynchronize(stop);
                float ms;
                cudaEventElapsedTime(&ms, start, stop);
                double tput = (double)N * RUNS_PER / (ms / 1000.0) / 1e6;
                if (r == 0 || ms < br.min_ms) br.min_ms = ms;
                if (r == 0 || ms > br.max_ms) br.max_ms = ms;
                if (r == 0 || tput > br.max_tput || br.max_tput == 0) br.max_tput = tput;
                if (r == 0 || tput < br.min_tput || br.min_tput == 0) br.min_tput = tput;
                br.mean_ms += ms;
                br.mean_tput += tput;
            }
            br.mean_ms /= RUNS;
            br.mean_tput /= RUNS;
            br.runs = RUNS;
            print_gpu_bench("hpdf_dither_fast (batch CURAND)", &br, "Mpts/s");

            cudaEventDestroy(start);
            cudaEventDestroy(stop);
            free(signal);
        }
    }

    /* ── Benchmark 3: Scaling ────────────────────────────────── */
    printf("\n── Benchmark 3: Swarm Scaling (1000 steps, original vs shared) ──\n");
    {
        int sizes[] = {50000, 100000, 200000, 400000};
        const int STEPS = 1000;

        printf("  %-10s  %-15s %-15s  %-15s %-15s\n",
               "Agents", "Orig steps/s", "Shared steps/s", "Orig drift", "Shared drift");
        printf("  %-10s  %-15s %-15s  %-15s %-15s\n",
               "──────", "─────────────", "──────────────", "────────────", "─────────────");

        for (int i = 0; i < 4; i++) {
            SwarmResult sr_orig, sr_shared;
            cuda_swarm_sim(sizes[i], STEPS, &sr_orig);
            cuda_swarm_sim_shared(sizes[i], STEPS, &sr_shared);
            printf("  %-10d  %15.1f %15.1f  %15.2e %15.2e\n",
                   sizes[i], sr_orig.steps_per_sec, sr_shared.steps_per_sec,
                   sr_orig.snapped_drift, sr_shared.snapped_drift);
        }
    }

    /* ── Benchmark 4: Sustained Throughput (10 sec) ──────────── */
    printf("\n── Benchmark 4: Sustained Throughput Test ──\n");
    {
        const int N = 200000;
        const int STEPS_PER_BATCH = 100;
        const float TARGET_SEC = 5.0f; /* 5 sec to keep benchmark reasonable */

        SwarmResult sr;
        printf("  Running sustained test (target %.0f sec)...\n", TARGET_SEC);

        cudaEvent_t start, stop;
        cudaEventCreate(&start);
        cudaEventCreate(&stop);

        int total_steps = 0;
        cudaEventRecord(start);
        while (1) {
            cuda_swarm_sim(N, STEPS_PER_BATCH, &sr);
            total_steps += STEPS_PER_BATCH;

            cudaEventRecord(stop);
            cudaEventSynchronize(stop);
            float ms;
            cudaEventElapsedTime(&ms, start, stop);
            if (ms / 1000.0f >= TARGET_SEC) break;
        }
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float total_ms;
        cudaEventElapsedTime(&total_ms, start, stop);

        printf("  Completed %d steps in %.2f sec\n", total_steps, total_ms / 1000.0f);
        printf("  Steady-state throughput: %.1f steps/sec\n", total_steps / (total_ms / 1000.0f));
        printf("  Steady-state agents/sec: %.2e\n",
               (double)total_steps * N / (total_ms / 1000.0f));

        cudaEventDestroy(start);
        cudaEventDestroy(stop);
    }

    printf("\n═══════════════════════════════════════════════════════════════\n");
    printf("  GPU BENCHMARK V2 COMPLETE\n");
    printf("═══════════════════════════════════════════════════════════════\n");

    return 0;
}
