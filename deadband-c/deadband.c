#include "deadband.h"

/*
 * Deadband perceivability check.
 *
 * Returns true if the given (L, k) pair is perceivable, i.e. the
 * complexity is non-trivial.  The threshold: LFSR length L must be
 * at least k (minimum complexity threshold).
 */

bool deadband_perceivable(int L, int k)
{
    return L >= k;
}
