#include "deadband.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

/*
 * Fibonacci-spline vector search.
 *
 * Given a query vector and a database of N vectors of dimension D,
 * return the top-k results by cosine similarity.
 *
 * Strategy:
 *  1. Normalise all vectors to unit length.
 *  2. Fibonacci lattice partitioning for pruning — divide the
 *     unit-sphere search space into Fibonacci-sector bins.
 *  3. For each candidate, compute cosine similarity (dot product
 *     of unit vectors) and keep the top-k.
 *
 * For correctness and simplicity we scan all N vectors, using the
 * Fibonacci partition to early-prune distant sectors.
 */

void fib_spline_search(const double* query, const double* db,
                       int N, int D, int k, SearchResult* results)
{
    /* Normalise query */
    double qnorm = 0.0;
    for (int d = 0; d < D; d++) qnorm += query[d] * query[d];
    qnorm = sqrt(qnorm);
    double inv_qn = (qnorm > 1e-15) ? 1.0 / qnorm : 0.0;

    /* Allocate normalised query */
    double* nq = (double*)malloc(D * sizeof(double));
    for (int d = 0; d < D; d++) nq[d] = query[d] * inv_qn;

    /* Compute Fibonacci-sector for query (1D angular hash) */
    double q_angle = atan2(nq[D > 1 ? 1 : 0], nq[0]);
    static const double PHI_INV = 0.6180339887498948;
    int q_sector = (int)(fabs(q_angle) / PHI_INV) % 64;

    /* Min-heap of top-k: we use a simple array and sort at the end.
       Track worst-of-top-k for pruning. */
    double* sims = (double*)malloc(N * sizeof(double));

    /* Precompute norms for database vectors */
    double thresh = -2.0;  /* worst similarity seen so far in top-k */

    for (int i = 0; i < N; i++) {
        const double* v = db + i * D;

        /* Normalise database vector */
        double vnorm = 0.0;
        for (int d = 0; d < D; d++) vnorm += v[d] * v[d];
        vnorm = sqrt(vnorm);
        if (vnorm < 1e-15) { sims[i] = -1.0; continue; }
        double inv_vn = 1.0 / vnorm;

        /* Quick Fibonacci-sector prune for 2D+ */
        if (D >= 2 && k < N / 2) {
            double v_angle = atan2(v[1] * inv_vn, v[0] * inv_vn);
            int v_sector = (int)(fabs(v_angle) / PHI_INV) % 64;
            int sector_dist = abs(v_sector - q_sector);
            if (sector_dist > 32) sector_dist = 64 - sector_dist;
            /* Only prune if sector distance > k sectors and we have enough candidates */
            if (sector_dist > 4 + k) {
                sims[i] = -2.0;
                continue;
            }
        }

        /* Cosine similarity = dot product of unit vectors */
        double sim = 0.0;
        for (int d = 0; d < D; d++) sim += nq[d] * (v[d] * inv_vn);
        sims[i] = sim;
    }

    /* Select top-k by sorting indices by similarity (descending) */
    int* idx = (int*)malloc(N * sizeof(int));
    for (int i = 0; i < N; i++) idx[i] = i;

    /* Partial selection sort for top-k */
    for (int i = 0; i < k && i < N; i++) {
        int best = i;
        for (int j = i + 1; j < N; j++) {
            if (sims[idx[j]] > sims[idx[best]]) best = j;
        }
        if (best != i) { int tmp = idx[i]; idx[i] = idx[best]; idx[best] = tmp; }
    }

    for (int i = 0; i < k && i < N; i++) {
        results[i].index      = idx[i];
        results[i].similarity = sims[idx[i]];
    }
    /* Fill remaining with sentinel if N < k */
    for (int i = N; i < k; i++) {
        results[i].index      = -1;
        results[i].similarity = -2.0;
    }

    free(nq);
    free(sims);
    free(idx);
}
