/*
 * deadband_check.cu — Batched deadband perceivability via BMA on GF(2)
 *
 * Each thread runs an independent Berlekamp-Massey Algorithm on a
 * stream of n bits. If the LFSR length found is < n, the stream
 * is perceivable (reducible → information leaked).
 *
 * BMA over GF(2): pure XOR operations, no division needed.
 */

#include "deadband_cuda.h"
#include <cuda_runtime.h>
#include <string.h>

/* BMA over GF(2) — find shortest LFSR that generates the sequence */
__device__ int bma_gf2(const int* bits, int n)
{
    /* C = current connection polynomial (as bit array) */
    /* B = previous connection polynomial */
    /* L = current LFSR length */
    /* We use a simple iterative approach for small n */

    int C[128]; /* connection poly coefficients, C[i] = 1 means term i */
    int B[128];
    int L = 0;
    int m = 1; /* number of iterations since last update */
    int b = 1; /* previous discrepancy */

    /* Initialize: C(x) = 1, B(x) = 1 */
    for (int i = 0; i < 128 && i < n + 1; i++) { C[i] = 0; B[i] = 0; }
    C[0] = 1;
    B[0] = 1;

    for (int k = 0; k < n; k++) {
        /* Compute discrepancy d = sum_{i=0}^{L} C[i] * s[k-i] mod 2 */
        int d = 0;
        for (int i = 0; i <= L && i <= k; i++) {
            d ^= (C[i] & bits[k - i]);
        }

        if (d == 0) {
            m++;
        } else if (2 * L <= k) {
            /* Update: T = C, C = C - d*b^{-1}*x^m*B, B = T, L = k+1-L */
            int T[128];
            for (int i = 0; i < 128 && i <= L; i++) T[i] = C[i];

            /* C = C XOR x^m * B (since d=b=1 in GF(2) simplification) */
            for (int i = 0; i < 128 && i + m < 128; i++) {
                if (B[i]) C[i + m] ^= 1;
            }

            for (int i = 0; i < 128 && i <= k + 1 - L; i++) B[i] = T[i];
            L = k + 1 - L;
            b = d;
            m = 1;
        } else {
            /* C = C XOR x^m * B */
            for (int i = 0; i < 128 && i + m < 128; i++) {
                if (B[i]) C[i + m] ^= 1;
            }
            m++;
        }
    }

    return L;
}

__global__ void deadband_check_kernel(
    const double* __restrict__ data,
    int N_streams,
    int n,
    int receiver_bits,
    int* __restrict__ results)
{
    int s = blockIdx.x * blockDim.x + threadIdx.x;
    if (s >= N_streams) return;

    /* Convert doubles to bits */
    int bits[128]; /* max stream length 128 */
    int len = (n < 128) ? n : 128;
    for (int i = 0; i < len; i++) {
        bits[i] = (data[s * n + i] >= 0.5) ? 1 : 0;
    }

    /* Run BMA */
    int lfsr_len = bma_gf2(bits, len);

    /* Perceivable if LFSR length < n (stream is compressible) */
    results[s] = (lfsr_len < n) ? 1 : 0;
}

int cuda_deadband_check(const double* data, int N_streams, int n,
                        int receiver_bits, int** results)
{
    cudaError_t err;
    double* d_data;
    int* d_results;

    size_t data_bytes = (size_t)N_streams * n * sizeof(double);
    size_t res_bytes = N_streams * sizeof(int);

    err = cudaMalloc(&d_data, data_bytes);
    if (err != cudaSuccess) return -1;
    err = cudaMalloc(&d_results, res_bytes);
    if (err != cudaSuccess) { cudaFree(d_data); return -1; }

    cudaMemcpy(d_data, data, data_bytes, cudaMemcpyHostToDevice);

    int block = 256;
    int grid = (N_streams + block - 1) / block;
    deadband_check_kernel<<<grid, block>>>(d_data, N_streams, n, receiver_bits, d_results);

    *results = (int*)malloc(res_bytes);
    cudaMemcpy(*results, d_results, res_bytes, cudaMemcpyDeviceToHost);

    cudaFree(d_data);
    cudaFree(d_results);
    return 0;
}
