#ifndef DEADBAND_H
#define DEADBAND_H

#include <stdint.h>
#include <stdbool.h>

/* ── Eisenstein snap ────────────────────────────────────────────── */

typedef struct {
    double sx;       /* snapped x */
    double sy;       /* snapped y */
    int64_t a;       /* lattice coordinate a  (a + bω) */
    int64_t b;       /* lattice coordinate b */
    double err;      /* Euclidean distance to snapped point */
} SnapResult;

SnapResult eisenstein_snap(double x, double y);

/* ── HPDF sample (hexagonal PDF on Voronoi cell of Z[ω]) ───────── */

typedef struct { double x, y; } Vec2;

Vec2 hpdf_sample(void);

/* ── /360 integer arithmetic (zero drift by construction) ──────── */

int64_t div360_add(int64_t a, int64_t b);
int64_t div360_sub(int64_t a, int64_t b);
int64_t div360_mul(int64_t a, int64_t b);

/* ── Berlekamp-Massey over GF(2) ───────────────────────────────── */

int bma_detect(const uint8_t* seq, int n);

/* ── Deadband perceivability ────────────────────────────────────── */

bool deadband_perceivable(int L, int k);

/* ── Shell eigenstructure ───────────────────────────────────────── */

typedef struct {
    double lam1, lam2;      /* eigenvalues (lam1 >= lam2) */
    double e1x, e1y;        /* first eigenvector */
    double e2x, e2y;        /* second eigenvector */
    double energy_ratio;    /* lam1 / (lam1 + lam2) */
    int    classify;        /* 0=unknown, 1=known(phi), 2=assumed(-1/phi) */
} ShellResult;

ShellResult shell_decompose(double cov[4]);   /* row-major [a,b,c,d] = [[a,b],[c,d]] */

/* ── Fibonacci-spline vector search ─────────────────────────────── */

typedef struct {
    int    index;
    double similarity;
} SearchResult;

void fib_spline_search(const double* query, const double* db,
                       int N, int D, int k, SearchResult* results);

#endif /* DEADBAND_H */
