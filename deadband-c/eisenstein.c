#include "deadband.h"
#include <math.h>

/*
 * Eisenstein integers Z[ω] where ω = e^(2πi/3) = -1/2 + i√3/2.
 * Basis: e1 = (1, 0),  e2 = (-1/2, √3/2).
 * Any lattice point is a*e1 + b*e2 = (a - b/2,  b*√3/2).
 *
 * To snap (x, y):
 *   From y = b*√3/2  →  b = round(2y/√3)
 *   From x = a - b/2  →  a = round(x + b/2)
 *
 * We try the rounded (a,b) and its immediate neighbours, pick the
 * one with smallest squared error (avoids sqrt, handles ties).
 */

static inline void lattice_to_cart(int64_t a, int64_t b,
                                   double* ox, double* oy)
{
    *ox = (double)a - 0.5 * (double)b;
    *oy = 0.86602540378443864676 * (double)b;   /* √3/2 */
}

SnapResult eisenstein_snap(double x, double y)
{
    static const double INV_SQRT3_2 = 1.1547005383792515;   /* 2/√3 */

    /* Initial guess */
    double bf = y * INV_SQRT3_2;
    int64_t b0 = (int64_t)llround(bf);
    int64_t a0 = (int64_t)llround(x + 0.5 * (double)b0);

    /* Check 9 candidates around the rounded lattice point */
    double best_d2 = 1e300;
    int64_t best_a = a0, best_b = b0;

    for (int da = -1; da <= 1; da++) {
        for (int db = -1; db <= 1; db++) {
            int64_t ca = a0 + da;
            int64_t cb = b0 + db;
            double lx, ly;
            lattice_to_cart(ca, cb, &lx, &ly);
            double dx = x - lx;
            double dy = y - ly;
            double d2 = dx*dx + dy*dy;
            if (d2 < best_d2) {
                best_d2 = d2;
                best_a = ca;
                best_b = cb;
            }
        }
    }

    SnapResult r;
    r.a   = best_a;
    r.b   = best_b;
    lattice_to_cart(best_a, best_b, &r.sx, &r.sy);
    r.err = sqrt(best_d2);
    return r;
}
