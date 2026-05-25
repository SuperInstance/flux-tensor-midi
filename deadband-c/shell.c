#include "deadband.h"
#include <math.h>

/*
 * Analytic eigendecomposition of a 2×2 symmetric matrix:
 *
 *   A = | a  b |
 *       | b  d |
 *
 * Eigenvalues: λ = (a+d)/2 ± √(((a-d)/2)² + b²)
 * Eigenvectors from (A - λI)v = 0.
 *
 * Classify: λ near φ (golden ratio) → "known"
 *           λ near -1/φ             → "assumed"
 *           otherwise               → "unknown"
 */

ShellResult shell_decompose(double cov[4])
{
    double a = cov[0], b = cov[1], c = cov[2], d = cov[3];
    /* For symmetric input b==c; be robust anyway */
    double off = 0.5 * (b + c);

    double trace = a + d;
    double diff  = a - d;
    double disc  = sqrt(0.25 * diff * diff + off * off);

    double lam1 = 0.5 * trace + disc;   /* larger */
    double lam2 = 0.5 * trace - disc;   /* smaller */

    /* Eigenvector for lam1: (A - lam1*I) v = 0
     *   (a - lam1)*vx + off*vy = 0  →  vx/vy = -off/(a-lam1)
     * Handle degenerate case when a ≈ lam1.
     */
    double e1x, e1y, e2x, e2y;
    double denom = a - lam1;
    if (fabs(denom) > 1e-12) {
        e1x = -off;
        e1y =  denom;
    } else {
        e1x =  denom;   /* ≈ 0 */
        e1y = -off;
        if (fabs(off) < 1e-15) { e1x = 1.0; e1y = 0.0; }
    }
    /* Normalise */
    double n1 = sqrt(e1x*e1x + e1y*e1y);
    if (n1 > 1e-15) { e1x /= n1; e1y /= n1; }

    /* Second eigenvector is orthogonal */
    e2x = -e1y;
    e2y =  e1x;

    /* Energy ratio */
    double total = lam1 + lam2;
    double energy_ratio = (total > 1e-15) ? lam1 / total : 0.5;

    /* Classify */
    static const double PHI      = 1.6180339887498948;
    static const double NEG_PHI  = -0.6180339887498948;  /* -1/φ */
    static const double TOL      = 0.05;

    int classify = 0;
    /* Check both eigenvalues against φ and -1/φ */
    if (fabs(lam1 - PHI) < TOL || fabs(lam2 - PHI) < TOL)
        classify = 1;
    else if (fabs(lam1 - NEG_PHI) < TOL || fabs(lam2 - NEG_PHI) < TOL)
        classify = 2;
    /* Also check normalised eigenvalues */
    if (classify == 0 && total > 1e-12) {
        double nl1 = lam1 / total, nl2 = lam2 / total;
        if (fabs(nl1 - PHI/(1+PHI)) < TOL || fabs(nl2 - PHI/(1+PHI)) < TOL)
            classify = 1;
    }

    ShellResult r;
    r.lam1 = lam1;  r.lam2 = lam2;
    r.e1x = e1x;    r.e1y = e1y;
    r.e2x = e2x;    r.e2y = e2y;
    r.energy_ratio = energy_ratio;
    r.classify = classify;
    return r;
}
