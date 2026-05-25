#include "deadband.h"

/*
 * Berlekamp-Massey over GF(2).
 *
 * Input: binary sequence s[0..n-1].
 * Output: minimum LFSR length L that generates the sequence.
 *
 * Standard algorithm.  Convergence guarantee: converges at n = 2L.
 */

int bma_detect(const uint8_t* seq, int n)
{
    /* C arrays on the stack — L never exceeds n. */
    int C[4096], B[4096], T[4096];

    for (int i = 0; i < 4096; i++) C[i] = B[i] = T[i] = 0;
    C[0] = 1;
    B[0] = 1;

    int L = 0;
    int m = 1;      /* shift counter */
    int Nc = 1;     /* length of C (number of coefficients) */

    for (int i = 0; i < n; i++) {
        /* Compute discrepancy d */
        int d = (int)seq[i];
        for (int j = 1; j <= L && j < Nc; j++) {
            d ^= (C[j] & (int)seq[i - j]);
        }

        if (d == 0) {
            m++;
        } else {
            /* T ← C */
            for (int j = 0; j < Nc; j++) T[j] = C[j];
            int TNc = Nc;

            int shift = m;
            /* C ← C + x^m * B */
            int need = shift + /* Nb */ (L + 1 > n ? n : L + 1);
            if (need > Nc) Nc = need;
            for (int j = 0; j <= L && j + shift < 4096; j++) {
                C[j + shift] ^= B[j];
            }

            if (2 * L <= i) {
                L = i + 1 - L;
                /* B ← T */
                for (int j = 0; j < TNc; j++) B[j] = T[j];
                for (int j = TNc; j < 4096; j++) B[j] = 0;
                m = 1;
            } else {
                m++;
            }
        }
    }
    return L;
}
