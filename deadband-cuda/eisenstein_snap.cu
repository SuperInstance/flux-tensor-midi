/*
 * eisenstein_snap.cu — Parallel Eisenstein lattice snap kernel
 *
 * Basis: e1 = (1, 0), e2 = (-0.5, sqrt(3)/2)
 * For a point p = (x, y), solve for lattice coords (a, b):
 *   x = a - 0.5*b
 *   y = (sqrt(3)/2)*b
 * => b = 2*y / sqrt(3), a = x + 0.5*b
 * Then round (a, b) to nearest integers and reconstruct.
 */

#include "deadband_cuda.h"
#include <cuda_runtime.h>
#include <math.h>

__global__ void eisenstein_snap_kernel(
    const double* __restrict__ x,
    const double* __restrict__ y,
    double* __restrict__ sx,
    double* __restrict__ sy,
    double* __restrict__ err,
    int N)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= N) return;

    const double SQRT3_2 = 0.86602540378443864676; /* sqrt(3)/2 */

    double px = x[i];
    double py = y[i];

    /* Solve for lattice coordinates */
    double b = py / SQRT3_2;          /* = 2y/sqrt(3) */
    double a = px + 0.5 * b;

    /* Round to nearest lattice point */
    double ra = round(a);
    double rb = round(b);

    /* Reconstruct snapped position */
    sx[i] = ra - 0.5 * rb;
    sy[i] = SQRT3_2 * rb;

    /* Error: Euclidean distance */
    double dx = px - sx[i];
    double dy = py - sy[i];
    err[i] = sqrt(dx * dx + dy * dy);
}

int cuda_eisenstein_snap(const double* x, const double* y, int N,
                         double** sx, double** sy, double** error)
{
    cudaError_t err;

    /* Allocate device memory */
    double *d_x, *d_y, *d_sx, *d_sy, *d_err;
    size_t bytes = N * sizeof(double);

    err = cudaMalloc(&d_x, bytes);
    if (err != cudaSuccess) return -1;
    err = cudaMalloc(&d_y, bytes);
    if (err != cudaSuccess) { cudaFree(d_x); return -1; }
    err = cudaMalloc(&d_sx, bytes);
    if (err != cudaSuccess) { cudaFree(d_x); cudaFree(d_y); return -1; }
    err = cudaMalloc(&d_sy, bytes);
    if (err != cudaSuccess) { cudaFree(d_x); cudaFree(d_y); cudaFree(d_sx); return -1; }
    err = cudaMalloc(&d_err, bytes);
    if (err != cudaSuccess) { cudaFree(d_x); cudaFree(d_y); cudaFree(d_sx); cudaFree(d_sy); return -1; }

    /* Copy input */
    cudaMemcpy(d_x, x, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_y, y, bytes, cudaMemcpyHostToDevice);

    /* Launch kernel */
    int block = 256;
    int grid = (N + block - 1) / block;
    eisenstein_snap_kernel<<<grid, block>>>(d_x, d_y, d_sx, d_sy, d_err, N);

    /* Allocate host output */
    *sx = (double*)malloc(bytes);
    *sy = (double*)malloc(bytes);
    *error = (double*)malloc(bytes);

    /* Copy results */
    cudaMemcpy(*sx, d_sx, bytes, cudaMemcpyDeviceToHost);
    cudaMemcpy(*sy, d_sy, bytes, cudaMemcpyDeviceToHost);
    cudaMemcpy(*error, d_err, bytes, cudaMemcpyDeviceToHost);

    cudaFree(d_x); cudaFree(d_y); cudaFree(d_sx); cudaFree(d_sy); cudaFree(d_err);
    return 0;
}
