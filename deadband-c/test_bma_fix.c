#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

extern int bma_detect(const uint8_t* seq, int n);

int bma_detect_word_fixed(const uint8_t* seq, int n)
{
    int nwords = (n + 63) / 64 + 2;  /* extra word for safety */

    uint64_t* C = (uint64_t*)calloc(nwords, sizeof(uint64_t));
    uint64_t* B = (uint64_t*)calloc(nwords, sizeof(uint64_t));
    uint64_t* T = (uint64_t*)calloc(nwords, sizeof(uint64_t));

    C[0] = 1;
    B[0] = 1;

    int L = 0;
    int m = 1;
    int Nc_words = 1;  /* track C's effective word count */

    for (int i = 0; i < n; i++) {
        /* Compute discrepancy */
        int d = seq[i] & 1;
        for (int j = 1; j <= L; j++) {
            int w = j / 64;
            int b = j % 64;
            int cj = (w < nwords) ? (int)((C[w] >> b) & 1) : 0;
            d ^= (cj & (seq[i - j] & 1));
        }

        if (d == 0) {
            m++;
        } else {
            /* T ← C */
            memcpy(T, C, nwords * sizeof(uint64_t));
            int TNc = Nc_words;

            /* C ← C XOR x^m * B */
            int word_shift = m / 64;
            int bit_shift  = m % 64;
            int new_Nc = Nc_words;

            if (bit_shift == 0) {
                for (int w = 0; w < Nc_words; w++) {
                    int di = w + word_shift;
                    if (di < nwords) C[di] ^= B[w];
                    if (di + 1 > new_Nc) new_Nc = di + 1;
                }
            } else {
                for (int w = Nc_words - 1; w >= 0; w--) {
                    int di = w + word_shift;
                    if (di < nwords) {
                        C[di] ^= B[w] << bit_shift;
                        if (di + 1 > new_Nc) new_Nc = di + 1;
                    }
                    if (di + 1 < nwords) {
                        C[di + 1] ^= B[w] >> (64 - bit_shift);
                        if (di + 2 > new_Nc) new_Nc = di + 2;
                    }
                }
            }
            Nc_words = new_Nc < nwords ? new_Nc : nwords;

            if (2 * L <= i) {
                L = i + 1 - L;
                /* B ← T (copy exactly TNc words, zero the rest) */
                memcpy(B, T, TNc * sizeof(uint64_t));
                for (int w = TNc; w < nwords; w++) B[w] = 0;
                m = 1;
            } else {
                m++;
            }
        }
    }

    int result = L;
    free(C); free(B); free(T);
    return result;
}

static uint64_t splitmix64(uint64_t* state) {
    uint64_t z = (*state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main(void) {
    int match = 0, mismatch = 0;
    uint8_t seq[256];
    uint64_t rng = 12345;
    
    for (int t = 0; t < 10000; t++) {
        for (int i = 0; i < 256; i++) seq[i] = splitmix64(&rng) & 1;
        int L1 = bma_detect(seq, 256);
        int L2 = bma_detect_word_fixed(seq, 256);
        if (L1 == L2) match++;
        else {
            mismatch++;
            if (mismatch <= 3) {
                printf("Mismatch test %d: baseline=%d word=%d\n", t, L1, L2);
            }
        }
    }
    printf("Match: %d  Mismatch: %d\n", match, mismatch);
    return 0;
}
