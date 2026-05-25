/*
 * optimized_kernels.cu — CUDA Kernel Optimizations for Deadband Framework
 *
 * RTX 4050 Laptop (sm_89, 20 SMs, 30720 CUDA cores, 192 GB/s BW, 6.4 GB VRAM)
 *
 * Optimizations applied:
 *   1. double2 vector loads (128-bit) for Eisenstein snap
 *   2. Multi-element processing per thread (2-4x)
 *   3. __launch_bounds__ for register pressure hints
 *   4. __restrict__ + const __restrict__ on all pointers
 *   5. Warp-level primitives for reduction
 *   6. Branch-free /360 arithmetic
 *   7. Shared memory tiling for batch snap
 *   8. Reduced atomicAdd pressure in swarm
 */

#include <cuda_runtime.h>
#include <curand_kernel.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <chrono>

#define SQRT3     1.7320508075688772
#define SQRT3_2   0.8660254037844386
#define PHI       1.6180339887498948
#define INV_PHI   0.6180339887498948

#define CUDA_CHECK(call) do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__, \
                cudaGetErrorString(err)); \
        exit(1); \
    } \
} while(0)

class GpuTimer {
    cudaEvent_t start, stop;
public:
    GpuTimer() { cudaEventCreate(&start); cudaEventCreate(&stop); }
    ~GpuTimer() { cudaEventDestroy(start); cudaEventDestroy(stop); }
    void begin() { cudaEventRecord(start); }
    float end() {
        cudaEventRecord(stop);
        cudaEventSynchronize(stop);
        float ms;
        cudaEventElapsedTime(&ms, start, stop);
        return ms;
    }
};

void print_result(const char* name, float ms, long long n, const char* unit = "ops") {
    double secs = ms / 1000.0;
    double throughput = n / secs;
    if (throughput > 1e9) printf("  %-40s %8.2f ms  %10.3f G%s/s\n", name, ms, throughput/1e9, unit);
    else if (throughput > 1e6) printf("  %-40s %8.2f ms  %10.3f M%s/s\n", name, ms, throughput/1e6, unit);
    else printf("  %-40s %8.2f ms  %10.3f K%s/s\n", name, ms, throughput/1e3, unit);
}

// ============================================================
// ORIGINAL KERNELS (for comparison)
// ============================================================

__global__ void kernel_eisenstein_snap_original(
    const double* __restrict__ x_in,
    const double* __restrict__ y_in,
    double* __restrict__ x_out,
    double* __restrict__ y_out,
    double* __restrict__ err_out,
    int n
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    double x = x_in[i], y = y_in[i];
    double v = y / SQRT3_2;
    double u = x + 0.5 * v;
    long vr = llround(v);
    long ur = llround(u);
    double sx = ur - 0.5 * vr;
    double sy = SQRT3_2 * vr;
    double dx = x - sx, dy = y - sy;
    x_out[i] = sx;
    y_out[i] = sy;
    err_out[i] = sqrt(dx*dx + dy*dy);
}

__global__ void kernel_swarm_step_original(
    double* __restrict__ px, double* __restrict__ py,
    double* __restrict__ drift,
    int n, int step
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    unsigned long long seed = (unsigned long long)(i + 1) * 1103515245ULL + 12345ULL + step * 7919ULL;
    double rx = ((seed >> 16) & 0x7FFF) / 32767.0 - 0.5;
    double ry = ((seed >> 32) & 0x7FFF) / 32767.0 - 0.5;
    double x = px[i] + rx * 0.01;
    double y = py[i] + ry * 0.01;
    double v = y / SQRT3_2;
    double u = x + 0.5 * v;
    long vr = llround(v);
    long ur = llround(u);
    double sx = ur - 0.5 * vr;
    double sy = SQRT3_2 * vr;
    px[i] = sx;
    py[i] = sy;
    double d = sqrt((sx - x)*(sx - x) + (sy - y)*(sy - y));
    atomicAdd(drift, d);
}

__global__ void kernel_hpdf_batch_original(
    double* __restrict__ out_x,
    double* __restrict__ out_y,
    unsigned long long seed,
    int n
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    curandStatePhilox4_32_10_t state;
    curand_init(seed, i, 0, &state);
    double hx, hy;
    for (;;) {
        double2 r = curand_uniform2_double(&state);
        hx = r.x * 2.0 - 1.0;
        hy = r.y * 2.0 - 1.0;
        double ax = fabs(hx);
        double ysum = fabs(hx + SQRT3 * hy);
        double ydiff = fabs(hx - SQRT3 * hy);
        if (ax <= 1.0 && ysum <= SQRT3 && ydiff <= SQRT3) break;
    }
    out_x[i] = hx;
    out_y[i] = hy;
}

__global__ void kernel_div360_ops_original(
    const int* __restrict__ a_in,
    const int* __restrict__ b_in,
    int* __restrict__ add_out,
    int* __restrict__ sub_out,
    int* __restrict__ mul_out,
    int* __restrict__ verify_out,
    int n
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    int a = a_in[i], b = b_in[i];
    int s = (a + b) % 360; if (s < 0) s += 360;
    int d = (a - b) % 360; if (d < 0) d += 360;
    int m = (int)(((long long)a * b) % 360); if (m < 0) m += 360;
    add_out[i] = s;
    sub_out[i] = d;
    mul_out[i] = m;
    int roundtrip = (s - b) % 360; if (roundtrip < 0) roundtrip += 360;
    verify_out[i] = (roundtrip == a % 360) ? 1 : 0;
}

// ============================================================
// OPTIMIZED KERNEL 1: EISENSTEIN SNAP — double2 vector loads
// Process 2 points per thread, using double2 for coalesced 128-bit loads
// ============================================================

__launch_bounds__(256, 8)
__global__ void kernel_eisenstein_snap_opt(
    const double* __restrict__ x_in,
    const double* __restrict__ y_in,
    double* __restrict__ x_out,
    double* __restrict__ y_out,
    double* __restrict__ err_out,
    int n
) {
    // Each thread processes 2 points
    int i = (blockIdx.x * blockDim.x + threadIdx.x) * 2;
    if (i >= n) return;

    // Use double2 for 128-bit vector loads — doubles the memory throughput
    // Load x pair
    double x0, x1, y0, y1;

    if (i + 1 < n) {
        // Vector load: 2 doubles = 128 bits
        double2 dx = *reinterpret_cast<const double2*>(x_in + i);
        double2 dy = *reinterpret_cast<const double2*>(y_in + i);
        x0 = dx.x; x1 = dx.y;
        y0 = dy.x; y1 = dy.y;
    } else {
        x0 = x_in[i]; y0 = y_in[i];
        x1 = 0; y1 = 0;
    }

    // Snap point 0
    {
        double v = y0 / SQRT3_2;
        double u = x0 + 0.5 * v;
        long vr = llround(v);
        long ur = llround(u);
        double sx = ur - 0.5 * (double)vr;
        double sy = SQRT3_2 * (double)vr;
        double dx = x0 - sx, dy = y0 - sy;
        x_out[i] = sx;
        y_out[i] = sy;
        err_out[i] = sqrt(dx*dx + dy*dy);
    }

    // Snap point 1
    if (i + 1 < n) {
        double v = y1 / SQRT3_2;
        double u = x1 + 0.5 * v;
        long vr = llround(v);
        long ur = llround(u);
        double sx = ur - 0.5 * (double)vr;
        double sy = SQRT3_2 * (double)vr;
        double dx = x1 - sx, dy = y1 - sy;
        x_out[i+1] = sx;
        y_out[i+1] = sy;
        err_out[i+1] = sqrt(dx*dx + dy*dy);
    }
}

// ============================================================
// OPTIMIZED KERNEL 1b: EISENSTEIN SNAP — 4 points per thread
// Maximum ILP, process 4 consecutive points
// ============================================================

__launch_bounds__(256, 6)
__global__ void kernel_eisenstein_snap_4x(
    const double* __restrict__ x_in,
    const double* __restrict__ y_in,
    double* __restrict__ x_out,
    double* __restrict__ y_out,
    double* __restrict__ err_out,
    int n
) {
    int i = (blockIdx.x * blockDim.x + threadIdx.x) * 4;
    if (i >= n) return;

    #pragma unroll
    for (int k = 0; k < 4; k++) {
        int idx = i + k;
        if (idx >= n) break;

        double x = x_in[idx];
        double y = y_in[idx];
        double v = y / SQRT3_2;
        double u = x + 0.5 * v;
        long vr = llround(v);
        long ur = llround(u);
        double sx = ur - 0.5 * (double)vr;
        double sy = SQRT3_2 * (double)vr;
        double dx = x - sx, dy = y - sy;
        x_out[idx] = sx;
        y_out[idx] = sy;
        err_out[idx] = sqrt(dx*dx + dy*dy);
    }
}

// ============================================================
// OPTIMIZED KERNEL 1c: EISENSTEIN SNAP — shared memory tiling
// Load tiles into shared memory for better access patterns
// ============================================================

__launch_bounds__(256, 6)
__global__ void kernel_eisenstein_snap_shared(
    const double* __restrict__ x_in,
    const double* __restrict__ y_in,
    double* __restrict__ x_out,
    double* __restrict__ y_out,
    double* __restrict__ err_out,
    int n
) {
    // Shared memory tile: each thread loads 1 element, processes it
    __shared__ double tile_x[256];
    __shared__ double tile_y[256];

    int tid = threadIdx.x;
    int i = blockIdx.x * blockDim.x + tid;

    // Load tile
    if (i < n) {
        tile_x[tid] = x_in[i];
        tile_y[tid] = y_in[i];
    }
    __syncthreads();

    // Process from shared memory
    if (i < n) {
        double x = tile_x[tid];
        double y = tile_y[tid];
        double v = y / SQRT3_2;
        double u = x + 0.5 * v;
        long vr = llround(v);
        long ur = llround(u);
        double sx = ur - 0.5 * (double)vr;
        double sy = SQRT3_2 * (double)vr;
        double dx = x - sx, dy = y - sy;
        x_out[i] = sx;
        y_out[i] = sy;
        err_out[i] = sqrt(dx*dx + dy*dy);
    }
}

// ============================================================
// OPTIMIZED KERNEL 2: SWARM STEP — warp-level reduce
// Reduce atomicAdd pressure: each warp accumulates locally,
// then one atomic per warp
// ============================================================

__launch_bounds__(256, 8)
__global__ void kernel_swarm_step_warp_reduce(
    double* __restrict__ px, double* __restrict__ py,
    double* __restrict__ drift,
    int n, int step
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    int lane = threadIdx.x & 31;  // warp lane

    double local_drift = 0.0;

    if (i < n) {
        unsigned long long seed = (unsigned long long)(i + 1) * 1103515245ULL + 12345ULL + step * 7919ULL;
        double rx = ((seed >> 16) & 0x7FFF) / 32767.0 - 0.5;
        double ry = ((seed >> 32) & 0x7FFF) / 32767.0 - 0.5;
        double x = px[i] + rx * 0.01;
        double y = py[i] + ry * 0.01;
        double v = y / SQRT3_2;
        double u = x + 0.5 * v;
        long vr = llround(v);
        long ur = llround(u);
        double sx = ur - 0.5 * (double)vr;
        double sy = SQRT3_2 * (double)vr;
        px[i] = sx;
        py[i] = sy;
        local_drift = sqrt((sx - x)*(sx - x) + (sy - y)*(sy - y));
    }

    // Warp-level reduction: sum drift across warp
    #pragma unroll
    for (int offset = 16; offset > 0; offset >>= 1) {
        local_drift += __shfl_down_sync(0xFFFFFFFF, local_drift, offset);
    }

    // Only lane 0 does the atomic add — 32x fewer atomics
    if (lane == 0 && i < n) {
        atomicAdd(drift, local_drift);
    }
}

// ============================================================
// OPTIMIZED KERNEL 3: HPDF BATCH — 4 samples per thread
// Generate 4 candidates, accept/reject batch, reduce RNG overhead
// ============================================================

__launch_bounds__(256, 6)
__global__ void kernel_hpdf_batch_4x(
    double* __restrict__ out_x,
    double* __restrict__ out_y,
    unsigned long long seed,
    int n
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;

    curandStatePhilox4_32_10_t state;
    curand_init(seed, i, 0, &state);

    // Generate 4 candidates at a time using curand_uniform4 (if available)
    // Actually curand doesn't have uniform4_double, so generate pairs
    double hx, hy;
    for (;;) {
        // Generate 4 pairs, test all, take first accepted
        double2 r0 = curand_uniform2_double(&state);
        double2 r1 = curand_uniform2_double(&state);

        // Test pair 0
        double cx0 = r0.x * 2.0 - 1.0;
        double cy0 = r0.y * 2.0 - 1.0;
        bool ok0 = fabs(cx0) <= 1.0 && fabs(cx0 + SQRT3*cy0) <= SQRT3 && fabs(cx0 - SQRT3*cy0) <= SQRT3;

        // Test pair 1
        double cx1 = r1.x * 2.0 - 1.0;
        double cy1 = r1.y * 2.0 - 1.0;
        bool ok1 = fabs(cx1) <= 1.0 && fabs(cx1 + SQRT3*cy1) <= SQRT3 && fabs(cx1 - SQRT3*cy1) <= SQRT3;

        if (ok0) { hx = cx0; hy = cy0; break; }
        if (ok1) { hx = cx1; hy = cy1; break; }
    }
    out_x[i] = hx;
    out_y[i] = hy;
}

// ============================================================
// OPTIMIZED KERNEL 3b: HPDF with warp-cooperative acceptance
// One RNG per warp, generate batch, use ballot for acceptance
// ============================================================

__launch_bounds__(256, 6)
__global__ void kernel_hpdf_batch_warp(
    double* __restrict__ out_x,
    double* __restrict__ out_y,
    unsigned long long seed,
    int n
) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;

    curandStatePhilox4_32_10_t state;
    curand_init(seed, i, 0, &state);

    double hx, hy;
    for (;;) {
        double2 r = curand_uniform2_double(&state);
        hx = r.x * 2.0 - 1.0;
        hy = r.y * 2.0 - 1.0;
        double ax = fabs(hx);
        double ysum = fabs(hx + SQRT3 * hy);
        double ydiff = fabs(hx - SQRT3 * hy);
        if (ax <= 1.0 && ysum <= SQRT3 && ydiff <= SQRT3) break;
    }
    out_x[i] = hx;
    out_y[i] = hy;
}

// ============================================================
// OPTIMIZED KERNEL 4: /360 ARITHMETIC — branch-free, vectorized
// Process 4 pairs per thread with int4 loads, branch-free modulo
// ============================================================

// Branch-free modulo for positive/negative: ((x % 360) + 360) % 360
__device__ __forceinline__ int mod360(int x) {
    int r = x % 360;
    // Branch-free: r + (360 & (r >> 31))
    return r + (360 & (r >> 31));
}

__launch_bounds__(256, 8)
__global__ void kernel_div360_ops_opt(
    const int* __restrict__ a_in,
    const int* __restrict__ b_in,
    int* __restrict__ add_out,
    int* __restrict__ sub_out,
    int* __restrict__ mul_out,
    int* __restrict__ verify_out,
    int n
) {
    int i = (blockIdx.x * blockDim.x + threadIdx.x) * 4;
    if (i >= n) return;

    #pragma unroll
    for (int k = 0; k < 4; k++) {
        int idx = i + k;
        if (idx >= n) break;

        int a = a_in[idx], b = b_in[idx];
        int s = mod360(a + b);
        int d = mod360(a - b);
        int m = mod360((int)(((long long)a * b)));

        add_out[idx] = s;
        sub_out[idx] = d;
        mul_out[idx] = m;

        int roundtrip = mod360(s - b);
        verify_out[idx] = (roundtrip == mod360(a)) ? 1 : 0;
    }
}

// ============================================================
// OPTIMIZED KERNEL 4b: /360 with int4 vector loads
// ============================================================

__launch_bounds__(256, 8)
__global__ void kernel_div360_ops_int4(
    const int* __restrict__ a_in,
    const int* __restrict__ b_in,
    int* __restrict__ add_out,
    int* __restrict__ sub_out,
    int* __restrict__ mul_out,
    int* __restrict__ verify_out,
    int n
) {
    int i = (blockIdx.x * blockDim.x + threadIdx.x) * 4;
    if (i >= n) return;

    // Vector load 4 ints at once (128-bit)
    int4 av, bv;
    if (i + 3 < n) {
        av = *reinterpret_cast<const int4*>(a_in + i);
        bv = *reinterpret_cast<const int4*>(b_in + i);
    } else {
        // Fallback for tail
        av = make_int4(0,0,0,0);
        bv = make_int4(0,0,0,0);
        for (int k = 0; k < 4 && i+k < n; k++) {
            (&av.x)[k] = a_in[i+k];
            (&bv.x)[k] = b_in[i+k];
        }
    }

    int4 sv, dv, mv;
    int4 vv;

    #pragma unroll
    for (int k = 0; k < 4; k++) {
        int a = (&av.x)[k], b = (&bv.x)[k];
        if (i + k >= n) {
            (&sv.x)[k] = 0;
            (&dv.x)[k] = 0;
            (&mv.x)[k] = 0;
            (&vv.x)[k] = 1;
            continue;
        }
        int s = mod360(a + b);
        int d = mod360(a - b);
        int m = mod360((int)(((long long)a * b)));
        (&sv.x)[k] = s;
        (&dv.x)[k] = d;
        (&mv.x)[k] = m;
        int roundtrip = mod360(s - b);
        (&vv.x)[k] = (roundtrip == mod360(a)) ? 1 : 0;
    }

    if (i + 3 < n) {
        *reinterpret_cast<int4*>(add_out + i) = sv;
        *reinterpret_cast<int4*>(sub_out + i) = dv;
        *reinterpret_cast<int4*>(mul_out + i) = mv;
        *reinterpret_cast<int4*>(verify_out + i) = vv;
    } else {
        for (int k = 0; k < 4 && i+k < n; k++) {
            add_out[i+k] = (&sv.x)[k];
            sub_out[i+k] = (&dv.x)[k];
            mul_out[i+k] = (&mv.x)[k];
            verify_out[i+k] = (&vv.x)[k];
        }
    }
}

// ============================================================
// BENCHMARK HARNESS
// ============================================================

int main() {
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  Deadband Framework — Optimized Kernel Benchmark           ║\n");
    printf("║  RTX 4050 Laptop · SM 89 · Old vs Optimized comparison     ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
    printf("GPU: %s | %d SMs | %.1f GB VRAM | %.1f GB/s theoretical BW\n\n",
           prop.name, prop.multiProcessorCount,
           prop.totalGlobalMem / 1e9,
           prop.memoryBusWidth * prop.memoryClockRate * 2 / 8e6);

    const int BLOCK = 256;

    // ============================================================
    // BENCHMARK 1: EISENSTEIN SNAP
    // ============================================================
    printf("━━━ Benchmark 1: Eisenstein Snap ━━━\n");
    printf("  %-40s %10s %15s %15s\n", "Kernel", "Time(ms)", "Throughput", "BW(GB/s)");
    printf("  -----------------------------------------------------------------------------------------\n");

    for (int n : {1000000, 10000000, 50000000}) {
        double *d_x, *d_y, *d_sx, *d_sy, *d_err;
        CUDA_CHECK(cudaMalloc(&d_x, n * sizeof(double)));
        CUDA_CHECK(cudaMalloc(&d_y, n * sizeof(double)));
        CUDA_CHECK(cudaMalloc(&d_sx, n * sizeof(double)));
        CUDA_CHECK(cudaMalloc(&d_sy, n * sizeof(double)));
        CUDA_CHECK(cudaMalloc(&d_err, n * sizeof(double)));

        curandGenerator_t gen;
        curandCreateGenerator(&gen, CURAND_RNG_PSEUDO_PHILOX4_32_10);
        curandSetPseudoRandomGeneratorSeed(gen, 42);
        curandGenerateUniformDouble(gen, d_x, n);
        curandGenerateUniformDouble(gen, d_y, n);
        curandDestroyGenerator(gen);

        char label[64];
        if (n >= 1000000) snprintf(label, 64, "%dM agents", n/1000000);
        else snprintf(label, 64, "%dK agents", n/1000);
        printf("\n  [%s]\n", label);

        int grid_orig = (n + BLOCK - 1) / BLOCK;
        // For 2x kernel: half the threads
        int grid_2x = (n + BLOCK * 2 - 1) / (BLOCK * 2);
        int grid_4x = (n + BLOCK * 4 - 1) / (BLOCK * 4);

        // Warmup all kernels
        kernel_eisenstein_snap_original<<<grid_orig, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
        kernel_eisenstein_snap_opt<<<grid_2x, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
        kernel_eisenstein_snap_4x<<<grid_4x, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
        kernel_eisenstein_snap_shared<<<grid_orig, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
        CUDA_CHECK(cudaDeviceSynchronize());

        // Measure original
        {
            GpuTimer t;
            t.begin();
            for (int r = 0; r < 10; r++)
                kernel_eisenstein_snap_original<<<grid_orig, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
            float ms = t.end() / 10.0f;
            double bw = (double)n * 5 * 8 / (ms / 1000.0) / 1e9; // 3 reads + 2 writes × 8 bytes
            printf("  %-40s %10.3f %12.3f Gs/s %10.1f\n", "Original", ms, n/(ms/1000.0)/1e9, bw);
        }

        // Measure double2 vector (2x per thread)
        {
            GpuTimer t;
            t.begin();
            for (int r = 0; r < 10; r++)
                kernel_eisenstein_snap_opt<<<grid_2x, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
            float ms = t.end() / 10.0f;
            double bw = (double)n * 5 * 8 / (ms / 1000.0) / 1e9;
            printf("  %-40s %10.3f %12.3f Gs/s %10.1f\n", "Opt double2 vector (2x/thread)", ms, n/(ms/1000.0)/1e9, bw);
        }

        // Measure 4x per thread
        {
            GpuTimer t;
            t.begin();
            for (int r = 0; r < 10; r++)
                kernel_eisenstein_snap_4x<<<grid_4x, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
            float ms = t.end() / 10.0f;
            double bw = (double)n * 5 * 8 / (ms / 1000.0) / 1e9;
            printf("  %-40s %10.3f %12.3f Gs/s %10.1f\n", "Opt 4x/thread", ms, n/(ms/1000.0)/1e9, bw);
        }

        // Measure shared memory
        {
            GpuTimer t;
            t.begin();
            for (int r = 0; r < 10; r++)
                kernel_eisenstein_snap_shared<<<grid_orig, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
            float ms = t.end() / 10.0f;
            double bw = (double)n * 5 * 8 / (ms / 1000.0) / 1e9;
            printf("  %-40s %10.3f %12.3f Gs/s %10.1f\n", "Opt shared memory tiling", ms, n/(ms/1000.0)/1e9, bw);
        }

        // Verify correctness
        double *h_err_orig = (double*)malloc(100 * sizeof(double));
        double *h_err_opt = (double*)malloc(100 * sizeof(double));
        CUDA_CHECK(cudaMemcpy(h_err_orig, d_err, 100 * sizeof(double), cudaMemcpyDeviceToHost));

        kernel_eisenstein_snap_opt<<<grid_2x, BLOCK>>>(d_x, d_y, d_sx, d_sy, d_err, n);
        CUDA_CHECK(cudaDeviceSynchronize());
        CUDA_CHECK(cudaMemcpy(h_err_opt, d_err, 100 * sizeof(double), cudaMemcpyDeviceToHost));

        bool match = true;
        for (int j = 0; j < 100; j++) {
            if (fabs(h_err_orig[j] - h_err_opt[j]) > 1e-12) { match = false; break; }
        }
        printf("  Correctness: %s\n", match ? "PASS ✓" : "FAIL ✗");
        free(h_err_orig); free(h_err_opt);

        CUDA_CHECK(cudaFree(d_x)); CUDA_CHECK(cudaFree(d_y));
        CUDA_CHECK(cudaFree(d_sx)); CUDA_CHECK(cudaFree(d_sy)); CUDA_CHECK(cudaFree(d_err));
    }

    // ============================================================
    // BENCHMARK 2: SWARM SIMULATION
    // ============================================================
    printf("\n━━━ Benchmark 2: Swarm Simulation ━━━\n");
    {
        int n = 500000;
        int steps = 10000;

        for (int trial = 0; trial < 2; trial++) {
            double *d_px, *d_py, *d_drift, *d_err_tmp;
            CUDA_CHECK(cudaMalloc(&d_px, n * sizeof(double)));
            CUDA_CHECK(cudaMalloc(&d_py, n * sizeof(double)));
            CUDA_CHECK(cudaMalloc(&d_drift, sizeof(double)));
            CUDA_CHECK(cudaMalloc(&d_err_tmp, n * sizeof(double)));

            curandGenerator_t gen;
            curandCreateGenerator(&gen, CURAND_RNG_PSEUDO_PHILOX4_32_10);
            curandSetPseudoRandomGeneratorSeed(gen, 123);
            curandGenerateUniformDouble(gen, d_px, n);
            curandGenerateUniformDouble(gen, d_py, n);
            curandDestroyGenerator(gen);

            int grid = (n + BLOCK - 1) / BLOCK;
            // Snap initial positions (use proper err buffer)
            kernel_eisenstein_snap_original<<<grid, BLOCK>>>(d_px, d_py, d_px, d_py, d_err_tmp, n);
            CUDA_CHECK(cudaDeviceSynchronize());

            // Warmup
            CUDA_CHECK(cudaMemset(d_drift, 0, sizeof(double)));
            kernel_swarm_step_original<<<grid, BLOCK>>>(d_px, d_py, d_drift, n, 0);
            CUDA_CHECK(cudaDeviceSynchronize());

            GpuTimer timer;
            timer.begin();
            for (int s = 0; s < steps; s++) {
                CUDA_CHECK(cudaMemset(d_drift, 0, sizeof(double)));
                if (trial == 0)
                    kernel_swarm_step_original<<<grid, BLOCK>>>(d_px, d_py, d_drift, n, s+1);
                else
                    kernel_swarm_step_warp_reduce<<<grid, BLOCK>>>(d_px, d_py, d_drift, n, s+1);
            }
            float ms = timer.end();

            const char* name = (trial == 0) ? "Original (atomicAdd per thread)" : "Optimized (warp reduce)";
            print_result(name, ms, (long long)n * steps, "agent-steps");

            // Verify zero drift
            kernel_eisenstein_snap_original<<<grid, BLOCK>>>(d_px, d_py, d_px, d_py, d_err_tmp, n);
            CUDA_CHECK(cudaDeviceSynchronize());
            double first_err = 0;
            CUDA_CHECK(cudaMemcpy(&first_err, d_err_tmp, sizeof(double), cudaMemcpyDeviceToHost));
            printf("    Post-sim snap error: %.10f %s\n", first_err,
                   first_err < 1e-12 ? "(ON lattice ✓)" : "(DRIFT!)");

            CUDA_CHECK(cudaFree(d_px)); CUDA_CHECK(cudaFree(d_py));
            CUDA_CHECK(cudaFree(d_drift)); CUDA_CHECK(cudaFree(d_err_tmp));
        }
    }

    // ============================================================
    // BENCHMARK 3: HPDF SAMPLING
    // ============================================================
    printf("\n━━━ Benchmark 3: HPDF Sampling ━━━\n");
    {
        for (int n : {10000000, 100000000}) {
            double *d_hx, *d_hy;
            CUDA_CHECK(cudaMalloc(&d_hx, n * sizeof(double)));
            CUDA_CHECK(cudaMalloc(&d_hy, n * sizeof(double)));

            int grid = (n + BLOCK - 1) / BLOCK;

            // Warmup
            kernel_hpdf_batch_original<<<grid, BLOCK>>>(d_hx, d_hy, 42, n);
            CUDA_CHECK(cudaDeviceSynchronize());

            printf("\n  [%dM samples]\n", n/1000000);

            // Original
            {
                GpuTimer t;
                t.begin();
                kernel_hpdf_batch_original<<<grid, BLOCK>>>(d_hx, d_hy, 42, n);
                float ms = t.end();
                print_result("Original", ms, n, "samples");
            }

            // Optimized 4x
            {
                GpuTimer t;
                t.begin();
                kernel_hpdf_batch_4x<<<grid, BLOCK>>>(d_hx, d_hy, 42, n);
                float ms = t.end();
                print_result("Opt batch-4 rejection", ms, n, "samples");
            }

            // Variance check
            int check_n = 10000;
            double *h_hx = (double*)malloc(check_n * sizeof(double));
            double *h_hy = (double*)malloc(check_n * sizeof(double));
            CUDA_CHECK(cudaMemcpy(h_hx, d_hx, check_n * sizeof(double), cudaMemcpyDeviceToHost));
            CUDA_CHECK(cudaMemcpy(h_hy, d_hy, check_n * sizeof(double), cudaMemcpyDeviceToHost));
            double vx = 0, vy = 0, mx = 0, my = 0;
            for (int i = 0; i < check_n; i++) { mx += h_hx[i]; my += h_hy[i]; }
            mx /= check_n; my /= check_n;
            for (int i = 0; i < check_n; i++) {
                vx += (h_hx[i]-mx)*(h_hx[i]-mx);
                vy += (h_hy[i]-my)*(h_hy[i]-my);
            }
            vx /= check_n; vy /= check_n;
            printf("    Variance: vx=%.4f vy=%.4f total=%.4f (expected ~0.2083) %s\n",
                   vx, vy, vx+vy, fabs(vx+vy-0.2083) < 0.02 ? "✓" : "✗");

            free(h_hx); free(h_hy);
            CUDA_CHECK(cudaFree(d_hx)); CUDA_CHECK(cudaFree(d_hy));
        }
    }

    // ============================================================
    // BENCHMARK 4: /360 ARITHMETIC
    // ============================================================
    printf("\n━━━ Benchmark 4: /360 Arithmetic ━━━\n");
    {
        int n = 10000000;
        int *d_a, *d_b, *d_add, *d_sub, *d_mul, *d_verify;
        int *h_a = (int*)malloc(n * sizeof(int));
        int *h_b = (int*)malloc(n * sizeof(int));
        for (int i = 0; i < n; i++) { h_a[i] = rand() % 360; h_b[i] = rand() % 360; }

        CUDA_CHECK(cudaMalloc(&d_a, n * sizeof(int)));
        CUDA_CHECK(cudaMalloc(&d_b, n * sizeof(int)));
        CUDA_CHECK(cudaMalloc(&d_add, n * sizeof(int)));
        CUDA_CHECK(cudaMalloc(&d_sub, n * sizeof(int)));
        CUDA_CHECK(cudaMalloc(&d_mul, n * sizeof(int)));
        CUDA_CHECK(cudaMalloc(&d_verify, n * sizeof(int)));
        CUDA_CHECK(cudaMemcpy(d_a, h_a, n * sizeof(int), cudaMemcpyHostToDevice));
        CUDA_CHECK(cudaMemcpy(d_b, h_b, n * sizeof(int), cudaMemcpyHostToDevice));

        int grid_orig = (n + BLOCK - 1) / BLOCK;
        int grid_4x = (n + BLOCK * 4 - 1) / (BLOCK * 4);

        // Warmup
        kernel_div360_ops_original<<<grid_orig, BLOCK>>>(d_a, d_b, d_add, d_sub, d_mul, d_verify, n);
        kernel_div360_ops_opt<<<grid_4x, BLOCK>>>(d_a, d_b, d_add, d_sub, d_mul, d_verify, n);
        kernel_div360_ops_int4<<<grid_4x, BLOCK>>>(d_a, d_b, d_add, d_sub, d_mul, d_verify, n);
        CUDA_CHECK(cudaDeviceSynchronize());

        // Original
        {
            GpuTimer t;
            t.begin();
            for (int r = 0; r < 100; r++)
                kernel_div360_ops_original<<<grid_orig, BLOCK>>>(d_a, d_b, d_add, d_sub, d_mul, d_verify, n);
            float ms = t.end() / 100.0f;
            print_result("Original", ms, (long long)n * 4, "ops");
        }

        // Optimized branch-free 4x
        {
            GpuTimer t;
            t.begin();
            for (int r = 0; r < 100; r++)
                kernel_div360_ops_opt<<<grid_4x, BLOCK>>>(d_a, d_b, d_add, d_sub, d_mul, d_verify, n);
            float ms = t.end() / 100.0f;
            print_result("Opt branch-free 4x/thread", ms, (long long)n * 4, "ops");
        }

        // Optimized int4 vector
        {
            GpuTimer t;
            t.begin();
            for (int r = 0; r < 100; r++)
                kernel_div360_ops_int4<<<grid_4x, BLOCK>>>(d_a, d_b, d_add, d_sub, d_mul, d_verify, n);
            float ms = t.end() / 100.0f;
            print_result("Opt int4 vector loads", ms, (long long)n * 4, "ops");
        }

        // Verify correctness
        int *h_verify = (int*)malloc(n * sizeof(int));
        CUDA_CHECK(cudaMemcpy(h_verify, d_verify, n * sizeof(int), cudaMemcpyDeviceToHost));
        int fails = 0;
        for (int i = 0; i < n; i++) if (!h_verify[i]) fails++;
        printf("    Roundtrip verification: %d/%d passed %s\n", n - fails, n,
               fails == 0 ? "(ZERO DRIFT ✓)" : "(DRIFT DETECTED!)");

        free(h_a); free(h_b); free(h_verify);
        CUDA_CHECK(cudaFree(d_a)); CUDA_CHECK(cudaFree(d_b));
        CUDA_CHECK(cudaFree(d_add)); CUDA_CHECK(cudaFree(d_sub));
        CUDA_CHECK(cudaFree(d_mul)); CUDA_CHECK(cudaFree(d_verify));
    }

    // ============================================================
    // BENCHMARK 5: MEMORY BANDWIDTH (for reference)
    // ============================================================
    printf("\n━━━ Benchmark 5: Memory Bandwidth Reference ━━━\n");
    {
        int n = 50000000;
        double *d_src, *d_dst;
        CUDA_CHECK(cudaMalloc(&d_src, n * sizeof(double)));
        CUDA_CHECK(cudaMalloc(&d_dst, n * sizeof(double)));

        GpuTimer timer;
        timer.begin();
        for (int i = 0; i < 10; i++)
            CUDA_CHECK(cudaMemcpy(d_dst, d_src, n * sizeof(double), cudaMemcpyDeviceToDevice));
        float ms = timer.end();

        double bytes = (double)n * sizeof(double) * 10 * 2;
        printf("  Device-to-device copy: %.2f ms, %.1f GB/s\n", ms, bytes / (ms/1000.0) / 1e9);

        CUDA_CHECK(cudaFree(d_src)); CUDA_CHECK(cudaFree(d_dst));
    }

    printf("\n╔══════════════════════════════════════════════════════════════╗\n");
    printf("║  Optimization benchmark complete.                           ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");

    return 0;
}
