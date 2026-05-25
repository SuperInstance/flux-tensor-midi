"""
deadband.py — Pure Python fallback for Deadband Framework

Same API as the C extension. Uses numpy for array operations.
Slower but requires no C compilation.
"""

import math
import random
import numpy as np

# ── Constants ──────────────────────────────────────────────────────
SQRT3 = math.sqrt(3.0)
PHI = (1.0 + math.sqrt(5.0)) / 2.0


# ── Eisenstein snap ────────────────────────────────────────────────

def eisenstein_snap(x, y):
    """Snap (x, y) to nearest Eisenstein lattice point.
    Returns (sx, sy, error)."""
    bf = 2.0 * y / SQRT3
    af = x + bf / 2.0

    b0 = round(bf)
    a0 = round(af)

    best_err = float('inf')
    best = (0.0, 0.0)

    for da in range(-1, 2):
        for db in range(-1, 2):
            a = a0 + da
            b = b0 + db
            lx = a - 0.5 * b
            ly = (SQRT3 / 2.0) * b
            err = math.sqrt((x - lx) ** 2 + (y - ly) ** 2)
            if err < best_err:
                best_err = err
                best = (lx, ly)

    return (best[0], best[1], best_err)


# ── HPDF sample ────────────────────────────────────────────────────

def hpdf_sample():
    """Sample one point from HPDF (hexagonal Voronoi cell).
    Returns (x, y)."""
    u = random.random()
    v = random.random()
    x = u - 0.5 - (v - 0.5) * 0.5
    y = (v - 0.5) * SQRT3 * 0.5
    return (x, y)


def hpdf_dither(signal_array):
    """Apply HPDF dithering to numpy array."""
    signal = np.asarray(signal_array, dtype=np.float64)
    n = len(signal)
    noise = np.array([hpdf_sample()[0] for _ in range(n)])
    return signal + noise


# ── /360 arithmetic ────────────────────────────────────────────────

def div360_add(a, b):
    """Exact /360 modular addition."""
    r = (a + b) % 360
    return r if r >= 0 else r + 360

def div360_sub(a, b):
    """Exact /360 modular subtraction."""
    r = (a - b) % 360
    return r if r >= 0 else r + 360

def div360_mul(a, b):
    """Exact /360 modular multiplication."""
    r = (a * b) % 360
    return r if r >= 0 else r + 360


# ── BMA over GF(2) ─────────────────────────────────────────────────

def bma_detect(sequence):
    """Berlekamp-Massey complexity over GF(2). Returns linear complexity."""
    seq = np.asarray(sequence, dtype=np.uint8).tolist()
    n = len(seq)
    if n == 0:
        return 0

    C = [0] * (n + 1)
    B = [0] * (n + 1)
    C[0] = 1
    B[0] = 1
    L = 0
    m = 1

    for i in range(n):
        d = seq[i]
        for j in range(1, L + 1):
            d ^= (C[j] & seq[i - j])

        if d == 0:
            m += 1
        elif 2 * L <= i:
            T = C[:]
            for j in range(len(B)):
                if m + j < len(C):
                    C[m + j] ^= B[j]
            L = i + 1 - L
            B = T[:]
            m = 1
        else:
            for j in range(len(B)):
                if m + j < len(C):
                    C[m + j] ^= B[j]
            m += 1

    return L


# ── Deadband perceivability ────────────────────────────────────────

def deadband_perceivable(L, k):
    """Is deadband step size k perceivable at level L?"""
    if L <= 0 or k <= 0:
        return False
    return k >= (L + 1) // 2


# ── Minimum bits ───────────────────────────────────────────────────

def deadband_min_bits(data_array, noise_floor):
    """Minimum bits for deadband quantization given noise floor."""
    data = np.asarray(data_array, dtype=np.float64)
    if len(data) == 0:
        return 0
    mn, mx = data.min(), data.max()
    rng = mx - mn
    if rng <= noise_floor:
        return 0
    levels = math.ceil(rng / noise_floor)
    bits = 0
    while (1 << bits) < levels:
        bits += 1
    return max(bits, 1)


# ── Shell eigenstructure ───────────────────────────────────────────

def shell_decompose(cov_matrix):
    """Eigenstructure of 2x2 covariance matrix.
    Returns dict with lam1, lam2, e1, e2, energy_ratio, classify, status."""
    cov = np.asarray(cov_matrix, dtype=np.float64)
    a, b, c, d = cov[0, 0], cov[0, 1], cov[1, 0], cov[1, 1]

    trace = a + d
    det = a * d - b * c
    disc = math.sqrt(max(0, trace ** 2 - 4 * det))

    lam1 = (trace + disc) / 2.0
    lam2 = (trace - disc) / 2.0
    if lam2 > lam1:
        lam1, lam2 = lam2, lam1
    lam2 = max(lam2, 0)

    # Eigenvectors
    if abs(b) > 1e-12:
        e1 = np.array([lam1 - d, b])
        e2 = np.array([lam2 - d, b])
    elif abs(c) > 1e-12:
        e1 = np.array([c, lam1 - a])
        e2 = np.array([c, lam2 - a])
    else:
        e1 = np.array([1.0, 0.0])
        e2 = np.array([0.0, 1.0])

    n1 = np.linalg.norm(e1)
    n2 = np.linalg.norm(e2)
    if n1 > 0:
        e1 /= n1
    if n2 > 0:
        e2 /= n2

    energy_ratio = lam1 / (lam1 + lam2) if (lam1 + lam2) > 0 else 0.5

    # Classify
    classify = 0
    if abs(energy_ratio - 1.0 / PHI) < 0.05 or abs(energy_ratio - PHI / (1.0 + PHI)) < 0.05:
        classify = 1
    elif energy_ratio > 0.85:
        classify = 2

    status = {0: "unknown", 1: "known(phi)", 2: "assumed(-1/phi)"}

    return {
        "lam1": float(lam1),
        "lam2": float(lam2),
        "e1": (float(e1[0]), float(e1[1])),
        "e2": (float(e2[0]), float(e2[1])),
        "energy_ratio": float(energy_ratio),
        "classify": classify,
        "status": status.get(classify, "unknown"),
    }


# ── Fibonacci-spline search ────────────────────────────────────────

def fib_spline_search(query, database, k):
    """Fibonacci-spline k-NN search with cosine similarity.
    Returns list of (index, similarity)."""
    query = np.asarray(query, dtype=np.float64)
    db = np.asarray(database, dtype=np.float64)

    if db.ndim == 1:
        db = db.reshape(1, -1)

    N, D = db.shape

    # Normalize
    q_norm = query / (np.linalg.norm(query) + 1e-12)
    db_norm = db / (np.linalg.norm(db, axis=1, keepdims=True) + 1e-12)

    similarities = db_norm @ q_norm
    top_k = np.argsort(similarities)[::-1][:k]

    return [(int(idx), float(similarities[idx])) for idx in top_k]
