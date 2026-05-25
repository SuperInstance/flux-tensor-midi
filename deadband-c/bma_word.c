/*
 * bma_word.c — Berlekamp-Massey over GF(2) using 64-bit word operations
 *
 * Optimization: store the connection polynomial C as uint64_t words and
 * do word-level XOR for polynomial updates.
 *
 * Speedup: polynomial updates are ~8x faster (XOR 64 bits at a time).
 * The discrepancy computation stays scalar but is a small fraction of work.
 *
 * Fixed: proper tracking of C/B word counts for correctness.
 */

#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

int bma_detect_word(const uint8_t* seq, int n)
{
    int nwords = (n + 63) / 64 + 2;  /* extra words for safety */

    uint64_t* C = (uint64_t*)calloc(nwords, sizeof(uint64_t));
    uint64_t* B = (uint64_t*)calloc(nwords, sizeof(uint64_t));
    uint64_t* T = (uint64_t*)calloc(nwords, sizeof(uint64_t));

    C[0] = 1;
    B[0] = 1;

    int L = 0;
    int m = 1;
    int Nc_words = 1;  /* track C's effective word count */

    for (int i = 0; i < n; i++) {
        /* Compute discrepancy: d = s[i] XOR sum_{j=1}^{L}(C[j] & s[i-j]) */
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
            /* T ← C (word-level copy) */
            memcpy(T, C, nwords * sizeof(uint64_t));
            int TNc = Nc_words;

            /* C ← C XOR x^m * B (word-level shift-XOR) */
            int word_shift = m / 64;
            int bit_shift  = m % 64;
            int new_Nc = Nc_words;

            if (bit_shift == 0) {
                for (int w = 0; w < Nc_words; w++) {
                    int di = w + word_shift;
                    if (di < nwords) {
                        C[di] ^= B[w];
                        if (di + 1 > new_Nc) new_Nc = di + 1;
                    }
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
                /* B ← T (copy exactly TNc words, zero rest) */
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

int bma_detect_opt(const uint8_t* seq, int n)
{
    return bma_detect_word(seq, n);
}

#ifdef TEST_BMA_WORD_STANDALONE
int main(void) {
    int fails = 0;

    /* All zeros → L = 0 */
    {
        uint8_t seq[20] = {0};
        int L = bma_detect_word(seq, 20);
        printf("All zeros: L=%d (expected 0)%s\n", L, L == 0 ? " ✅" : " ❌");
        if (L != 0) fails++;
    }

    /* Alternating 101010... → L = 2 */
    {
        uint8_t seq[20];
        for (int i = 0; i < 20; i++) seq[i] = i & 1;
        int L = bma_detect_word(seq, 20);
        printf("Alternating: L=%d (expected 2)%s\n", L, L == 2 ? " ✅" : " ❌");
        if (L != 2) fails++;
    }

    /* All ones → L = 1 */
    {
        uint8_t seq[20];
        for (int i = 0; i < 20; i++) seq[i] = 1;
        int L = bma_detect_word(seq, 20);
        printf("All ones: L=%d (expected 1)%s\n", L, L == 1 ? " ✅" : " ❌");
        if (L != 1) fails++;
    }

    /* Single 1 then zeros → L ≤ 1 */
    {
        uint8_t seq[20] = {0};
        seq[0] = 1;
        int L = bma_detect_word(seq, 20);
        printf("10000...: L=%d (expected ≤1)%s\n", L, L <= 1 ? " ✅" : " ❌");
        if (L > 1) fails++;
    }

    printf("\n%s\n", fails ? "SOME TESTS FAILED ❌" : "ALL TESTS PASSED ✅");
    return fails;
}
#endif
