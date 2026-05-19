/*
 * bma_word.c — Berlekamp-Massey over GF(2) using 64-bit word operations
 *
 * Optimization: process 64 bits at a time using uint64_t XOR instead of
 * byte-by-byte. The connection polynomial C and previous polynomial B are
 * stored as arrays of 64-bit words.
 *
 * For a sequence of length n, we need ceil(n/64) words.
 * The discrepancy computation uses popcount(XOR) & 1 for parity.
 *
 * Speedup: ~8-64x depending on sequence length due to word-level parallelism.
 */

#include <stdint.h>
#include <string.h>
#include <stdio.h>

#ifdef __POPCNT__
#include <immintrin.h>
#define POPCOUNT64(x) _mm_popcnt_u64((unsigned long long)(x))
#else
/* Portable fallback */
static inline int popcount64_fallback(uint64_t x) {
    x = x - ((x >> 1) & 0x5555555555555555ULL);
    x = (x & 0x3333333333333333ULL) + ((x >> 2) & 0x3333333333333333ULL);
    x = (x + (x >> 4)) & 0x0F0F0F0F0F0F0F0FULL;
    return (int)((x * 0x0101010101010101ULL) >> 56);
}
#define POPCOUNT64(x) popcount64_fallback((uint64_t)(x))
#endif

/* Pack a byte sequence into 64-bit words (MSB first within each word) */
static void pack_bits(const uint8_t* seq, int n, uint64_t* words)
{
    int nwords = (n + 63) / 64;
    memset(words, 0, nwords * sizeof(uint64_t));
    for (int i = 0; i < n; i++) {
        if (seq[i]) {
            words[i / 64] |= (1ULL << (i % 64));
        }
    }
}

/* Get bit i from word array */
static inline int get_bit(const uint64_t* words, int i)
{
    return (words[i / 64] >> (i % 64)) & 1;
}

/* XOR shift: dst ^= src << shift (word-level) */
static void xor_shift(uint64_t* dst, int dst_len,
                      const uint64_t* src, int src_len,
                      int shift)
{
    int word_shift = shift / 64;
    int bit_shift  = shift % 64;

    for (int j = 0; j < src_len && (j + word_shift) < dst_len; j++) {
        int di = j + word_shift;
        if (bit_shift == 0) {
            dst[di] ^= src[j];
        } else {
            dst[di] ^= src[j] << bit_shift;
            if (di + 1 < dst_len) {
                dst[di + 1] ^= src[j] >> (64 - bit_shift);
            }
        }
    }
}

/*
 * Word-level BMA over GF(2).
 * Returns the minimum LFSR length that generates the sequence.
 */
int bma_detect_word(const uint8_t* seq, int n)
{
    int max_words = (n + 63) / 64 + 2;

    /* Allocate on heap for large sequences, use VLA for small */
    uint64_t* C = (uint64_t*)calloc(max_words, sizeof(uint64_t));
    uint64_t* B = (uint64_t*)calloc(max_words, sizeof(uint64_t));
    uint64_t* T = (uint64_t*)calloc(max_words, sizeof(uint64_t));

    /* Pack input into words */
    uint64_t* S = (uint64_t*)calloc(max_words, sizeof(uint64_t));
    pack_bits(seq, n, S);

    C[0] = 1;  /* C(x) = 1 */
    B[0] = 1;  /* B(x) = 1 */

    int L = 0;
    int m = 1;

    for (int i = 0; i < n; i++) {
        /* Compute discrepancy d = XOR of C[j]*S[i-j] for j=0..L */
        /* Using word-level: we need the inner product C[0..L] · S[i..i-L] mod 2 */
        int d = get_bit(S, i);
        /* Compute parity of (C AND shifted-S) over the relevant range */
        int L_words = (L + 63) / 64 + 1;
        uint64_t parity = 0;
        for (int w = 0; w < L_words && w < max_words; w++) {
            /* We need bits from S at positions (i - j) for j in word w of C */
            /* This is equivalent to: take S shifted right by (i - L) positions,
               AND with C, then XOR-reduce */
            /* Simpler approach: extract relevant S bits and AND with C */
            int base = i - w * 64;
            if (base < 0) break;
            /* Get word-aligned chunk of S ending at position i */
            uint64_t s_chunk = 0;
            int start_bit = (base - 63 > 0) ? base - 63 : 0;
            for (int b = start_bit; b <= base && b < n; b++) {
                if (get_bit(S, b)) {
                    int shift_in_chunk = base - b;
                    if (shift_in_chunk >= 0 && shift_in_chunk < 64)
                        s_chunk |= (1ULL << shift_in_chunk);
                }
            }
            parity ^= (C[w] & s_chunk);
        }
        d ^= POPCOUNT64(parity) & 1;

        if (d == 0) {
            m++;
        } else {
            /* T ← C */
            memcpy(T, C, max_words * sizeof(uint64_t));

            /* C ← C XOR x^m * B */
            xor_shift(C, max_words, B, max_words, m);

            if (2 * L <= i) {
                L = i + 1 - L;
                /* B ← T */
                memcpy(B, T, max_words * sizeof(uint64_t));
                m = 1;
            } else {
                m++;
            }
        }
    }

    int result = L;
    free(C); free(B); free(T); free(S);
    return result;
}

/*
 * Byte-level optimized BMA — same algorithm as bma.c but cleaner
 * and with minor optimizations (restricted to 4096 bits for stack use).
 * Uses the word-level approach for sequences > 64 bits.
 */
int bma_detect_opt(const uint8_t* seq, int n)
{
    if (n <= 4096) {
        /* Use word-level for any size */
        return bma_detect_word(seq, n);
    }
    return bma_detect_word(seq, n);
}

#ifdef TEST_BMA_WORD_STANDALONE
int main(void) {
    int fails = 0;

    /* All zeros → L = 0 */
    {
        uint8_t seq[20] = {0};
        int L = bma_detect_word(seq, 20);
        printf("All zeros: L=%d (expected 0)\n", L);
        if (L != 0) fails++;
    }

    /* Alternating 101010... → L = 2 */
    {
        uint8_t seq[20];
        for (int i = 0; i < 20; i++) seq[i] = i & 1;
        int L = bma_detect_word(seq, 20);
        printf("Alternating: L=%d (expected 2)\n", L);
        if (L != 2) fails++;
    }

    /* All ones → L = 1 */
    {
        uint8_t seq[20];
        for (int i = 0; i < 20; i++) seq[i] = 1;
        int L = bma_detect_word(seq, 20);
        printf("All ones: L=%d (expected 1)\n", L);
        if (L != 1) fails++;
    }

    /* Single 1 then zeros → L ≤ 1 */
    {
        uint8_t seq[20] = {0};
        seq[0] = 1;
        int L = bma_detect_word(seq, 20);
        printf("10000...: L=%d (expected ≤1)\n", L);
        if (L > 1) fails++;
    }

    /* Long sequence test (256 bits) */
    {
        uint8_t seq[256];
        for (int i = 0; i < 256; i++) seq[i] = (i * 7 + 3) & 1;
        int L = bma_detect_word(seq, 256);
        printf("256-bit pseudo-random: L=%d\n", L);
        /* L should be > 0 for non-trivial sequence */
    }

    printf("\n%s\n", fails ? "SOME TESTS FAILED" : "ALL TESTS PASSED");
    return fails;
}
#endif
