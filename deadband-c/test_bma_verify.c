#define _POSIX_C_SOURCE 199309L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

extern int bma_detect(const uint8_t* seq, int n);
extern int bma_detect_word(const uint8_t* seq, int n);

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
    
    for (int t = 0; t < 1000; t++) {
        for (int i = 0; i < 256; i++) seq[i] = splitmix64(&rng) & 1;
        int L1 = bma_detect(seq, 256);
        int L2 = bma_detect_word(seq, 256);
        if (L1 == L2) match++;
        else {
            mismatch++;
            if (mismatch <= 5) {
                printf("Mismatch test %d: baseline=%d word=%d  seq[0..16]=", t, L1, L2);
                for (int i = 0; i < 16; i++) printf("%d", seq[i]);
                printf("\n");
            }
        }
    }
    printf("Match: %d  Mismatch: %d\n", match, mismatch);
    
    /* Test known sequences */
    uint8_t zeros[20] = {0};
    printf("zeros: base=%d word=%d\n", bma_detect(zeros,20), bma_detect_word(zeros,20));
    
    uint8_t ones[20];
    for (int i=0;i<20;i++) ones[i]=1;
    printf("ones: base=%d word=%d\n", bma_detect(ones,20), bma_detect_word(ones,20));
    
    uint8_t alt[20];
    for (int i=0;i<20;i++) alt[i]=i&1;
    printf("alt: base=%d word=%d\n", bma_detect(alt,20), bma_detect_word(alt,20));
    
    return 0;
}
