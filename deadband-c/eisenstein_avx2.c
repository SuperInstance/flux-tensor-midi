/*
 * eisenstein_avx2.c — AVX2 SIMD batch Eisenstein lattice snap
 *
 * Processes 4 points at once using __m256d.
 * Also provides a scalar-optimized batch function with branchless
 * neighbour search and precomputed constants.
 *
 * Compiles with: gcc -O3 -mavx2 -std=c11
 */

#include <immintrin.h>
#include <math.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>

/*
 * AVX2 batch snap: process 4 points simultaneously.
 * Each __m256d holds {x0,x1,x2,x3} and {y0,y1,y2,y3}.
 *
 * The snap formula:
 *   b = round(2y/√3)
 *   a = round(x + b/2)
 *   sx = a - b/2
 *   sy = (√3/2)*b
 *   err = ||(x,y) - (sx,sy)||
 *
 * This uses the simple rounding (no 9-neighbour search).
 * For the full-precision version, use the scalar batch.
 */

typedef struct {
    double sx[4], sy[4], err[4];
    int64_t a[4], b[4];
} SnapResult4;

static inline __m256d mm256_round_pd(__m256d v) {
    return _mm256_round_pd(v, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
}

/* Snap 4 points using AVX2 — fast path (no neighbour search) */
static inline void eisenstein_snap4_avx2(
    const double* x, const double* y, SnapResult4* out)
{
    static const double INV_SQRT3_2 = 1.1547005383792515;   /* 2/√3 */
    static const double SQRT3_2     = 0.8660254037844386;   /* √3/2 */

    __m256d vx = _mm256_loadu_pd(x);
    __m256d vy = _mm256_loadu_pd(y);

    /* b_float = y * (2/√3) */
    __m256d inv_sqrt3_2 = _mm256_set1_pd(INV_SQRT3_2);
    __m256d bf = _mm256_mul_pd(vy, inv_sqrt3_2);

    /* rb = round(b_float) */
    __m256d rb = mm256_round_pd(bf);

    /* a_float = x + rb * 0.5 */
    __m256d half = _mm256_set1_pd(0.5);
    __m256d af = _mm256_add_pd(vx, _mm256_mul_pd(rb, half));

    /* ra = round(a_float) */
    __m256d ra = mm256_round_pd(af);

    /* sx = ra - 0.5 * rb */
    __m256d sx = _mm256_sub_pd(ra, _mm256_mul_pd(half, rb));

    /* sy = (√3/2) * rb */
    __m256d sqrt3_2 = _mm256_set1_pd(SQRT3_2);
    __m256d sy = _mm256_mul_pd(sqrt3_2, rb);

    /* error = sqrt((x-sx)² + (y-sy)²) */
    __m256d dx = _mm256_sub_pd(vx, sx);
    __m256d dy = _mm256_sub_pd(vy, sy);
    __m256d d2 = _mm256_add_pd(_mm256_mul_pd(dx, dx), _mm256_mul_pd(dy, dy));
    /* Approximate reciprocal sqrt + multiply for speed */
    __m256d err = _mm256_sqrt_pd(d2);

    /* Store results */
    _mm256_storeu_pd(out->sx, sx);
    _mm256_storeu_pd(out->sy, sy);
    _mm256_storeu_pd(out->err, err);

    /* Extract integer coordinates */
    __m256i ia = _mm256_cvttpd_epi32(ra);
    __m256i ib = _mm256_cvttpd_epi32(rb);
    /* cvttpd_epi32 gives 4x int32 in low lanes; extract */
    int32_t ta[4], tb[4];
    _mm_storeu_si128((__m128i*)ta, ia);
    _mm_storeu_si128((__m128i*)tb, ib);
    /* _mm256_cvttpd_epi32 packs results into 128-bit */
    /* Actually it returns __m128i, packed: {a0,a1,a2,a3} */
    for (int i = 0; i < 4; i++) {
        out->a[i] = ta[i];
        out->b[i] = tb[i];
    }
}

/*
 * Scalar batch with 9-neighbour search — optimized.
 * Processes an array of (x,y) points, writes snapped results.
 */

typedef struct {
    double sx, sy, err;
    int64_t a, b;
} SnapResultSingle;

/* LUT for the 9 offsets in the neighbour search */
static const int8_t DA[9] = {-1, -1, -1,  0, 0, 0,  1, 1, 1};
static const int8_t DB[9] = {-1,  0,  1, -1, 0, 1, -1, 0, 1};

static inline void snap_single_opt(double x, double y, SnapResultSingle* r)
{
    static const double INV_SQRT3_2 = 1.1547005383792515;
    static const double SQRT3_2     = 0.8660254037844386;

    double bf = y * INV_SQRT3_2;
    int64_t b0 = (int64_t)llround(bf);
    int64_t a0 = (int64_t)llround(x + 0.5 * (double)b0);

    double best_d2 = 1e300;
    int64_t best_a = a0, best_b = b0;

    /* Unrolled 9-neighbour search */
    for (int k = 0; k < 9; k++) {
        int64_t ca = a0 + DA[k];
        int64_t cb = b0 + DB[k];
        double lx = (double)ca - 0.5 * (double)cb;
        double ly = SQRT3_2 * (double)cb;
        double ddx = x - lx;
        double ddy = y - ly;
        double d2 = ddx*ddx + ddy*ddy;
        /* Branchless min using comparison */
        if (__builtin_expect(d2 < best_d2, 1)) {
            best_d2 = d2;
            best_a = ca;
            best_b = cb;
        }
    }

    r->a = best_a;
    r->b = best_b;
    r->sx = (double)best_a - 0.5 * (double)best_b;
    r->sy = SQRT3_2 * (double)best_b;
    r->err = sqrt(best_d2);
}

/* Batch API: snap N points with 9-neighbour search (scalar optimized) */
void eisenstein_snap_batch(const double* x, const double* y, int n,
                           SnapResultSingle* results)
{
    for (int i = 0; i < n; i++) {
        snap_single_opt(x[i], y[i], &results[i]);
    }
}

/* AVX2 batch: groups of 4, fallback scalar for remainder */
void eisenstein_snap_batch_avx2(const double* x, const double* y, int n,
                                SnapResultSingle* results)
{
    int i = 0;
    /* Process 4 at a time with AVX2 (fast path, no neighbour search) */
    for (; i + 3 < n; i += 4) {
        SnapResult4 r4;
        eisenstein_snap4_avx2(x + i, y + i, &r4);
        for (int j = 0; j < 4; j++) {
            results[i+j].sx  = r4.sx[j];
            results[i+j].sy  = r4.sy[j];
            results[i+j].err = r4.err[j];
            results[i+j].a   = r4.a[j];
            results[i+j].b   = r4.b[j];
        }
    }
    /* Scalar fallback for tail */
    for (; i < n; i++) {
        snap_single_opt(x[i], y[i], &results[i]);
    }
}

#ifdef TEST_AVX2_STANDALONE
int main(void) {
    /* Quick smoke test */
    double x[8] = {1.0, -0.5, 0.3, 0.0, 2.0, 3.7, -1.2, 0.8};
    double y[8] = {0.0, 0.8660254037844386, 0.4, 0.0, 1.7, -0.5, 2.1, -1.3};

    SnapResultSingle res[8];
    eisenstein_snap_batch_avx2(x, y, 8, res);

    printf("AVX2 Eisenstein Snap Results:\n");
    for (int i = 0; i < 8; i++) {
        printf("  (%.2f,%.2f) → (%.2f,%.2f) a=%ld b=%ld err=%.6f\n",
               x[i], y[i], res[i].sx, res[i].sy,
               (long)res[i].a, (long)res[i].b, res[i].err);
    }

    /* Verify lattice points have ~0 error */
    printf("\nLattice point check:\n");
    printf("  (1,0) err = %.2e (should be ~0)\n", res[0].err);
    printf("  (-0.5,√3/2) err = %.2e (should be ~0)\n", res[1].err);
    printf("  (0,0) err = %.2e (should be ~0)\n", res[3].err);

    return 0;
}
#endif
