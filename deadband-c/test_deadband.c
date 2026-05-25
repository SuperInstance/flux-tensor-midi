#define _GNU_SOURCE
#include "deadband.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define PASS(name) printf("  ✅ PASS  %s\n", name)
#define FAIL(name, ...) do { printf("  ❌ FAIL  %s — ", name); printf(__VA_ARGS__); printf("\n"); fails++; } while(0)

static double now_sec(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* ─── 1. Eisenstein snap ──────────────────────────────────────── */

static int test_eisenstein(void)
{
    int fails = 0;

    /* Lattice point (a=1,b=0) → (1,0). Snap should give zero error. */
    SnapResult r = eisenstein_snap(1.0, 0.0);
    if (r.err > 1e-12 || r.a != 1 || r.b != 0)
        FAIL("snap(1,0)", "err=%.2e a=%ld b=%ld", r.err, (long)r.a, (long)r.b);
    else PASS("snap(1,0) = zero error");

    /* Lattice point (a=0,b=1) → (-0.5, √3/2) */
    r = eisenstein_snap(-0.5, 0.8660254037844386);
    if (r.err > 1e-10 || r.a != 0 || r.b != 1)
        FAIL("snap(-0.5,√3/2)", "err=%.2e a=%ld b=%ld", r.err, (long)r.a, (long)r.b);
    else PASS("snap(-0.5,√3/2) = zero error");

    /* Off-lattice point (0.3, 0.4) */
    r = eisenstein_snap(0.3, 0.4);
    if (r.err > 0.6)  /* rough upper bound */
        FAIL("snap(0.3,0.4) err too large", "err=%.4f", r.err);
    else PASS("snap(0.3,0.4) reasonable error");

    /* Origin */
    r = eisenstein_snap(0.0, 0.0);
    if (r.err > 1e-12 || r.a != 0 || r.b != 0)
        FAIL("snap(0,0)", "err=%.2e", r.err);
    else PASS("snap(0,0) = zero error");

    /* Many random snaps — verify error < max possible */
    srand(42);
    double max_err = 0.0;
    for (int i = 0; i < 10000; i++) {
        double x = (double)rand()/RAND_MAX * 10.0 - 5.0;
        double y = (double)rand()/RAND_MAX * 10.0 - 5.0;
        r = eisenstein_snap(x, y);
        if (r.err > max_err) max_err = r.err;
    }
    /* Max error should be < circumradius of hexagon ≈ 1/√3 ≈ 0.577 */
    if (max_err > 0.5774)
        FAIL("random snap max_err", "%.4f > 0.5774", max_err);
    else PASS("10000 random snaps max_err OK");

    return fails;
}

/* ─── 2. HPDF variance ────────────────────────────────────────── */

static int test_hpdf(void)
{
    int fails = 0;
    srand(12345);
    const int N = 100000;
    double sx = 0, sy = 0, sx2 = 0, sy2 = 0;

    double t0 = now_sec();
    for (int i = 0; i < N; i++) {
        Vec2 v = hpdf_sample();
        sx  += v.x;  sx2 += v.x * v.x;
        sy  += v.y;  sy2 += v.y * v.y;
    }
    double dt = now_sec() - t0;

    double mean_x = sx / N, mean_y = sy / N;
    double var_x  = sx2 / N - mean_x * mean_x;
    double var_y  = sy2 / N - mean_y * mean_y;

    /* Expected variance = 5/24 ≈ 0.208333 for regular hexagon with R=1 */
    double expected = 5.0 / 24.0;

    printf("  HPDF stats (%d samples, %.1f ms): mean=(%.4f,%.4f) var=(%.5f,%.5f) expected=%.5f\n",
           N, dt*1000, mean_x, mean_y, var_x, var_y, expected);

    if (fabs(mean_x) > 0.01)
        FAIL("HPDF mean_x not ~0", "%.4f", mean_x);
    else PASS("HPDF mean_x ≈ 0");

    if (fabs(mean_y) > 0.01)
        FAIL("HPDF mean_y not ~0", "%.4f", mean_y);
    else PASS("HPDF mean_y ≈ 0");

    if (fabs(var_x - expected) > 0.005)
        FAIL("HPDF var_x", "%.5f vs expected %.5f", var_x, expected);
    else PASS("HPDF var_x ≈ 5/24");

    if (fabs(var_y - expected) > 0.005)
        FAIL("HPDF var_y", "%.5f vs expected %.5f", var_y, expected);
    else PASS("HPDF var_y ≈ 5/24");

    return fails;
}

/* ─── 3. /360 arithmetic ──────────────────────────────────────── */

static int test_div360(void)
{
    int fails = 0;
    const int OPS = 100000;

    /* Zero-drift accumulator test */
    int64_t acc = 0;
    srand(999);
    double t0 = now_sec();
    for (int i = 0; i < OPS; i++) {
        int64_t v = rand() % 720 - 360;
        acc = div360_add(acc, v);
    }
    double dt = now_sec() - t0;
    printf("  /360: %d additions in %.1f ms, final acc = %ld\n",
           OPS, dt*1000, (long)acc);

    if (acc < 0 || acc >= 360)
        FAIL("div360 accumulator out of range", "%ld", (long)acc);
    else PASS("div360 accumulator in [0,359]");

    /* Specific edge cases */
    if (div360_add(350, 20) != 10)
        FAIL("div360_add(350,20)", "got %ld", (long)div360_add(350,20));
    else PASS("div360_add(350,20) = 10");

    if (div360_sub(10, 20) != 350)
        FAIL("div360_sub(10,20)", "got %ld", (long)div360_sub(10,20));
    else PASS("div360_sub(10,20) = 350");

    if (div360_mul(180, 2) != 0)
        FAIL("div360_mul(180,2)", "got %ld", (long)div360_mul(180,2));
    else PASS("div360_mul(180,2) = 0");

    if (div360_mul(-1, 180) != 180)
        FAIL("div360_mul(-1,180)", "got %ld", (long)div360_mul(-1,180));
    else PASS("div360_mul(-1,180) = 180");

    /* Batch drift test: repeated add-sub of same value must return 0 */
    int64_t val = 0;
    for (int i = 0; i < OPS; i++) {
        val = div360_add(val, 7);
        val = div360_sub(val, 7);
    }
    if (val != 0)
        FAIL("div360 drift test", "final=%ld", (long)val);
    else PASS("div360 100k add/sub pairs: zero drift");

    return fails;
}

/* ─── 4. Berlekamp-Massey ─────────────────────────────────────── */

static int test_bma(void)
{
    int fails = 0;

    /* All zeros → L = 0 */
    {
        uint8_t seq[20] = {0};
        int L = bma_detect(seq, 20);
        if (L != 0) FAIL("BMA all-zeros", "L=%d", L);
        else PASS("BMA all-zeros L=0");
    }

    /* Alternating 101010... → period 2, L=2 */
    {
        uint8_t seq[20];
        for (int i = 0; i < 20; i++) seq[i] = i & 1;
        int L = bma_detect(seq, 20);
        if (L != 2) FAIL("BMA alternating", "L=%d", L);
        else PASS("BMA alternating L=2");
    }

    /* All ones → L = 1 */
    {
        uint8_t seq[20];
        for (int i = 0; i < 20; i++) seq[i] = 1;
        int L = bma_detect(seq, 20);
        if (L != 1) FAIL("BMA all-ones", "L=%d", L);
        else PASS("BMA all-ones L=1");
    }

    /* Single 1 then zeros → L = 1 */
    {
        uint8_t seq[20] = {0};
        seq[0] = 1;
        int L = bma_detect(seq, 20);
        if (L > 1) FAIL("BMA 10000...", "L=%d", L);
        else PASS("BMA 10000... L<=1");
    }

    return fails;
}

/* ─── 5. Shell decompose ──────────────────────────────────────── */

static int test_shell(void)
{
    int fails = 0;

    /* Identity matrix → eigenvalues both 1.0, ratio 0.5 */
    {
        double cov[4] = {1, 0, 0, 1};
        ShellResult r = shell_decompose(cov);
        if (fabs(r.lam1 - 1.0) > 1e-10 || fabs(r.lam2 - 1.0) > 1e-10)
            FAIL("shell identity eigenvalues", "(%.4f, %.4f)", r.lam1, r.lam2);
        else PASS("shell identity eigenvalues = (1,1)");

        if (fabs(r.energy_ratio - 0.5) > 1e-10)
            FAIL("shell identity ratio", "%.4f", r.energy_ratio);
        else PASS("shell identity energy_ratio = 0.5");
    }

    /* Diagonal (3, 1) → eigenvalues 3 and 1, ratio 0.75 */
    {
        double cov[4] = {3, 0, 0, 1};
        ShellResult r = shell_decompose(cov);
        if (fabs(r.lam1 - 3.0) > 1e-10 || fabs(r.lam2 - 1.0) > 1e-10)
            FAIL("shell diag(3,1)", "(%.4f, %.4f)", r.lam1, r.lam2);
        else PASS("shell diag(3,1) eigenvalues correct");

        if (fabs(r.energy_ratio - 0.75) > 1e-10)
            FAIL("shell diag(3,1) ratio", "%.4f", r.energy_ratio);
        else PASS("shell diag(3,1) ratio = 0.75");
    }

    /* Non-diagonal with off-diagonal terms */
    {
        double cov[4] = {2, 1, 1, 2};
        ShellResult r = shell_decompose(cov);
        /* eigenvalues: 3 and 1 */
        if (fabs(r.lam1 - 3.0) > 1e-10 || fabs(r.lam2 - 1.0) > 1e-10)
            FAIL("shell [[2,1],[1,2]]", "(%.4f, %.4f)", r.lam1, r.lam2);
        else PASS("shell [[2,1],[1,2]] eigenvalues = (3,1)");
    }

    return fails;
}

/* ─── 6. Fibonacci-spline search ──────────────────────────────── */

static int test_fib_spline(void)
{
    int fails = 0;

    /* Build a small database of 2D unit vectors */
    const int N = 100;
    const int D = 2;
    const int K = 5;

    double* db = (double*)malloc(N * D * sizeof(double));
    srand(777);
    for (int i = 0; i < N; i++) {
        double angle = 2.0 * M_PI * i / N;
        db[i*D+0] = cos(angle);
        db[i*D+1] = sin(angle);
    }

    /* Query = first database vector → should find index 0 as top */
    double query[2] = { db[0], db[1] };
    SearchResult results[K];

    double t0 = now_sec();
    fib_spline_search(query, db, N, D, K, results);
    double dt = now_sec() - t0;

    printf("  fib_spline search: %d vectors, top-%d in %.2f ms\n", N, K, dt*1000);
    printf("    top result: idx=%d sim=%.6f\n", results[0].index, results[0].similarity);

    if (results[0].index != 0)
        FAIL("fib_spline top-1 recall", "expected 0, got %d", results[0].index);
    else PASS("fib_spline top-1 correct index");

    if (fabs(results[0].similarity - 1.0) > 1e-10)
        FAIL("fib_spline top-1 similarity", "%.6f", results[0].similarity);
    else PASS("fib_spline top-1 similarity = 1.0");

    /* Query near element 50 → should find 50 in top-K */
    double q50[2] = { db[50*D] + 0.01, db[50*D+1] + 0.01 };
    fib_spline_search(q50, db, N, D, K, results);

    int found50 = 0;
    for (int i = 0; i < K; i++) {
        if (results[i].index == 50) { found50 = 1; break; }
    }
    if (!found50)
        FAIL("fib_spline recall idx=50", "not in top-%d", K);
    else PASS("fib_spline recall idx=50 in top-K");

    free(db);
    return fails;
}

/* ─── Main ─────────────────────────────────────────────────────── */

int main(void)
{
    printf("═══ Deadband Framework C Library — Test Suite ═══\n\n");

    double t_total = now_sec();
    int total_fails = 0;

    printf("── 1. Eisenstein Snap ──\n");
    total_fails += test_eisenstein();

    printf("\n── 2. HPDF Sampling ──\n");
    total_fails += test_hpdf();

    printf("\n── 3. /360 Arithmetic ──\n");
    total_fails += test_div360();

    printf("\n── 4. Berlekamp-Massey ──\n");
    total_fails += test_bma();

    printf("\n── 5. Shell Decompose ──\n");
    total_fails += test_shell();

    printf("\n── 6. Fibonacci-Spline Search ──\n");
    total_fails += test_fib_spline();

    double elapsed = now_sec() - t_total;
    printf("\n═══ Results: %d failures | %.1f ms total ═══\n", total_fails, elapsed*1000);

    return total_fails;
}
