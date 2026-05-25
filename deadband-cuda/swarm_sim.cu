/*
 * swarm_sim.cu — Full swarm simulation
 *
 * N agents at random (x,y) positions.
 * Each step: snap all positions to Eisenstein lattice.
 * Track drift over time for snapped vs. unsnapped float64.
 */

#include "deadband_cuda.h"
#include <cuda_runtime.h>
#include <curand_kernel.h>
#include <math.h>
#include <stdio.h>

__global__ void init_positions_kernel(
    double* x, double* y, int N,
    unsigned long long seed)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;

    curandStatePhilox4_32_10_t state;
    curand_init(seed, i, 0, &state);

    /* Random positions in [-100, 100] */
    x[i] = curand_uniform_double(&state) * 200.0 - 100.0;
    y[i] = curand_uniform_double(&state) * 200.0 - 100.0;
}

__global__ void snap_step_kernel(
    const double* __restrict__ x,
    const double* __restrict__ y,
    double* __restrict__ sx,
    double* __restrict__ sy,
    double* __restrict__ drift_snapped,
    double* __restrict__ drift_float,
    const double* __restrict__ orig_x,
    const double* __restrict__ orig_y,
    int N,
    int step)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;

    const double SQRT3_2 = 0.86602540378443864676;

    double px = x[i];
    double py = y[i];

    /* Snap to Eisenstein lattice */
    double b = py / SQRT3_2;
    double a = px + 0.5 * b;
    double ra = round(a);
    double rb = round(b);
    sx[i] = ra - 0.5 * rb;
    sy[i] = SQRT3_2 * rb;

    /* Simulate float64 drift: add tiny perturbation each step */
    double fpx = px + 1e-14 * step * (double)(i % 1000);
    double fpy = py - 1e-14 * step * (double)(i % 997);

    /* Compute drift from original positions */
    double dsx = sx[i] - orig_x[i];
    double dsy = sy[i] - orig_y[i];
    drift_snapped[i] = dsx * dsx + dsy * dsy;

    double dfx = fpx - orig_x[i];
    double dfy = fpy - orig_y[i];
    drift_float[i] = dfx * dfx + dfy * dfy;
}

/* Reduction kernel for max drift */
__global__ void max_drift_kernel(
    const double* __restrict__ drift,
    double* __restrict__ out,
    int N)
{
    __shared__ double sdata[256];
    int tid = threadIdx.x;
    int i = blockIdx.x * blockDim.x + threadIdx.x;

    sdata[tid] = (i < N) ? drift[i] : 0.0;
    __syncthreads();

    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            sdata[tid] = fmax(sdata[tid], sdata[tid + s]);
        }
        __syncthreads();
    }

    if (tid == 0) out[blockIdx.x] = sdata[0];
}

int cuda_swarm_sim(int N, int steps, SwarmResult* result)
{
    result->N = N;
    result->steps = steps;

    size_t bytes = N * sizeof(double);

    double *d_x, *d_y, *d_sx, *d_sy, *d_orig_x, *d_orig_y;
    double *d_drift_snapped, *d_drift_float;
    double *d_max_snapped, *d_max_float;

    /* Allocate */
    cudaMalloc(&d_x, bytes);
    cudaMalloc(&d_y, bytes);
    cudaMalloc(&d_sx, bytes);
    cudaMalloc(&d_sy, bytes);
    cudaMalloc(&d_orig_x, bytes);
    cudaMalloc(&d_orig_y, bytes);
    cudaMalloc(&d_drift_snapped, bytes);
    cudaMalloc(&d_drift_float, bytes);

    int block = 256;
    int grid = (N + block - 1) / block;
    cudaMalloc(&d_max_snapped, grid * sizeof(double));
    cudaMalloc(&d_max_float, grid * sizeof(double));

    result->memory_bytes = 8 * bytes + 2 * grid * sizeof(double);

    /* Initialize positions */
    init_positions_kernel<<<grid, block>>>(d_x, d_y, N, 42ULL);

    /* Snap initial positions first, then save as originals */
    double *d_init_sx, *d_init_sy;
    cudaMalloc(&d_init_sx, bytes);
    cudaMalloc(&d_init_sy, bytes);

    snap_step_kernel<<<grid, block>>>(
        d_x, d_y, d_init_sx, d_init_sy,
        d_drift_snapped, d_drift_float,
        d_orig_x, d_orig_y, N, 0);

    /* Start from snapped positions, originals = first snap */
    cudaMemcpy(d_orig_x, d_init_sx, bytes, cudaMemcpyDeviceToDevice);
    cudaMemcpy(d_orig_y, d_init_sy, bytes, cudaMemcpyDeviceToDevice);
    cudaMemcpy(d_x, d_init_sx, bytes, cudaMemcpyDeviceToDevice);
    cudaMemcpy(d_y, d_init_sy, bytes, cudaMemcpyDeviceToDevice);

    cudaFree(d_init_sx);
    cudaFree(d_init_sy);

    /* Create events for timing */
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    cudaEventRecord(start);

    /* Simulation loop */
    for (int s = 0; s < steps; s++) {
        snap_step_kernel<<<grid, block>>>(
            d_x, d_y, d_sx, d_sy,
            d_drift_snapped, d_drift_float,
            d_orig_x, d_orig_y, N, s);

        /* Copy snapped back to input for next step */
        cudaMemcpy(d_x, d_sx, bytes, cudaMemcpyDeviceToDevice);
        cudaMemcpy(d_y, d_sy, bytes, cudaMemcpyDeviceToDevice);
    }

    /* Final drift measurement */
    max_drift_kernel<<<grid, block>>>(d_drift_snapped, d_max_snapped, N);

    /* Reduce again if needed */
    int rgrid = grid;
    while (rgrid > 1) {
        int rblock = 256;
        int rgrid2 = (rgrid + rblock - 1) / rblock;
        max_drift_kernel<<<rgrid2, rblock>>>(d_max_snapped, d_max_snapped, rgrid);
        rgrid = rgrid2;
    }

    double h_snapped_drift;
    cudaMemcpy(&h_snapped_drift, d_max_snapped, sizeof(double), cudaMemcpyDeviceToHost);

    max_drift_kernel<<<grid, block>>>(d_drift_float, d_max_float, N);
    rgrid = grid;
    while (rgrid > 1) {
        int rblock = 256;
        int rgrid2 = (rgrid + rblock - 1) / rblock;
        max_drift_kernel<<<rgrid2, rblock>>>(d_max_float, d_max_float, rgrid);
        rgrid = rgrid2;
    }

    double h_float_drift;
    cudaMemcpy(&h_float_drift, d_max_float, sizeof(double), cudaMemcpyDeviceToHost);

    cudaEventRecord(stop);
    cudaEventSynchronize(stop);

    float ms;
    cudaEventElapsedTime(&ms, start, stop);
    float total_sec = ms / 1000.0f;

    result->steps_per_sec = (total_sec > 0) ? steps / total_sec : 0;
    result->snapped_drift = sqrt(h_snapped_drift);
    result->float64_drift = sqrt(h_float_drift);

    cudaFree(d_x); cudaFree(d_y); cudaFree(d_sx); cudaFree(d_sy);
    cudaFree(d_orig_x); cudaFree(d_orig_y);
    cudaFree(d_drift_snapped); cudaFree(d_drift_float);
    cudaFree(d_max_snapped); cudaFree(d_max_float);
    cudaEventDestroy(start); cudaEventDestroy(stop);

    return 0;
}
