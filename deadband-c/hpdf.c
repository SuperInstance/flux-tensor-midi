#include "deadband.h"
#include <math.h>
#include <stdlib.h>

/*
 * Sample uniformly from the regular hexagon that is the Voronoi cell
 * of the origin in the Eisenstein lattice Z[ω].
 *
 * Hexagon vertices:
 *   (1,0), (0.5, √3/2), (-0.5, √3/2), (-1,0), (-0.5,-√3/2), (0.5,-√3/2)
 *
 * Strategy: rejection-sample from the axis-aligned bounding box.
 * A point (x,y) is inside the hexagon iff:
 *   |x| ≤ 1           and
 *   |y| ≤ √3/2        and
 *   |y| ≤ √3 * (1 - |x|)
 *
 * Acceptance ratio = area(hexagon)/area(bbox) = (3√3/2) / (2*√3) = 3/4
 * so rejection is cheap.
 */

static double uniform_neg1_pos1(void)
{
    return 2.0 * ((double)rand() / (double)RAND_MAX) - 1.0;
}

Vec2 hpdf_sample(void)
{
    static const double SQRT3      = 1.7320508075688772;
    static const double HALF_SQRT3 = 0.8660254037844386;

    for (;;) {
        double x = uniform_neg1_pos1();           /* in [-1, 1] */
        double y = uniform_neg1_pos1() * HALF_SQRT3; /* in [-√3/2, √3/2] */

        double ax = fabs(x);
        double bound = SQRT3 * (1.0 - ax);
        if (fabs(y) <= bound)
            return (Vec2){ .x = x, .y = y };
    }
}
