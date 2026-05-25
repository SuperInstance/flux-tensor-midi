#include "deadband.h"
#include <stdint.h>

/*
 * /360 arithmetic — exact modular operations.
 * All values live in [0, 359].  Zero drift by construction.
 * We use a helper that normalises any int64_t into [0,359].
 */

static inline int64_t mod360(int64_t v)
{
    /* C % can be negative for negative operands; fix that. */
    int64_t r = v % 360;
    return r < 0 ? r + 360 : r;
}

int64_t div360_add(int64_t a, int64_t b)
{
    return mod360(mod360(a) + mod360(b));
}

int64_t div360_sub(int64_t a, int64_t b)
{
    return mod360(mod360(a) - mod360(b));
}

int64_t div360_mul(int64_t a, int64_t b)
{
    return mod360(mod360(a) * mod360(b));
}
