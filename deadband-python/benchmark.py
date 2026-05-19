#!/usr/bin/env python3
"""benchmark.py — Compare C extension vs pure Python speed."""

import time
import numpy as np
import sys
import os

# Add parent dir so we can import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import deadband_python as db
from deadband_python import deadband as pure

print(f"C extension loaded: {db.using_c_extension()}")
print()

functions = [
    ("eisenstein_snap", lambda m: m.eisenstein_snap(1.5, 2.3)),
    ("hpdf_sample", lambda m: m.hpdf_sample()),
    ("div360_add", lambda m: m.div360_add(12345, 67890)),
    ("div360_sub", lambda m: m.div360_sub(67890, 12345)),
    ("div360_mul", lambda m: m.div360_mul(123, 456)),
]

seq = np.random.randint(0, 2, size=100, dtype=np.uint8)
functions.append(("bma_detect(100)", lambda m: m.bma_detect(seq)))

cov = np.eye(2)
functions.append(("shell_decompose", lambda m: m.shell_decompose(cov)))

db_data = np.random.randn(100, 10)
query = np.random.randn(10)
functions.append(("fib_spline_search(100×10, k=5)", lambda m: m.fib_spline_search(query, db_data, 5)))

N = 5000

print(f"{'Function':<30} {'Pure Python':>14} {'C Extension':>14} {'Speedup':>10}")
print("=" * 72)

for name, fn in functions:
    # Pure Python
    t0 = time.perf_counter()
    for _ in range(N):
        fn(pure)
    dt_pure = time.perf_counter() - t0
    ops_pure = N / dt_pure

    # C extension (if available)
    if db.using_c_extension():
        t0 = time.perf_counter()
        for _ in range(N):
            fn(db)
        dt_c = time.perf_counter() - t0
        ops_c = N / dt_c
        speedup = dt_pure / dt_c
        print(f"{name:<30} {ops_pure:>12.0f}/s {ops_c:>12.0f}/s {speedup:>9.1f}x")
    else:
        print(f"{name:<30} {ops_pure:>12.0f}/s {'N/A':>14} {'N/A':>10}")

print("=" * 72)
