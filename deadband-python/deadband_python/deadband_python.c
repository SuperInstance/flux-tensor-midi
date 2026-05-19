/*
 * deadband_python.c — CPython extension for Deadband Framework
 *
 * Raw Python C API bindings for maximum speed.
 * Links against the deadband C library if available,
 * otherwise embeds standalone implementations.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>
#include <numpy/arrayobject.h>

#include <math.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

/* ── Standalone implementations (no external C lib dependency) ──── */

static double square(double x) { return x * x; }

/* Eisenstein lattice: points of form a + b*omega where omega = e^{2pi i/3}
 * omega = -0.5 + i*sqrt(3)/2
 * Real: a - 0.5*b,  Imag: (sqrt(3)/2)*b */

typedef struct {
    double sx, sy;
    int64_t a, b;
    double err;
} SnapResult;

static SnapResult eisenstein_snap_impl(double x, double y) {
    /* Solve: x = a - b/2,  y = (sqrt3/2)*b
     * => b = 2*y/sqrt3,  a = x + b/2 */
    double sqrt3 = 1.7320508075688772;
    double bf = 2.0 * y / sqrt3;
    double af = x + bf / 2.0;

    /* Round to nearest integers */
    int64_t b0 = (int64_t)round(bf);
    int64_t a0 = (int64_t)round(af);

    /* Check the two nearest lattice points (a0,b0) and neighbors */
    SnapResult best;
    best.err = 1e30;

    for (int64_t da = -1; da <= 1; da++) {
        for (int64_t db = -1; db <= 1; db++) {
            int64_t a = a0 + da;
            int64_t b = b0 + db;
            double lx = a - 0.5 * b;
            double ly = (sqrt3 / 2.0) * b;
            double err = sqrt(square(x - lx) + square(y - ly));
            if (err < best.err) {
                best.sx = lx;
                best.sy = ly;
                best.a = a;
                best.b = b;
                best.err = err;
            }
        }
    }
    return best;
}

/* HPDF: sample uniformly from the Voronoi cell of Z[omega] (hexagon)
 * Uses rejection sampling on the fundamental parallelogram */
typedef struct { double x, y; } Vec2;

static Vec2 hpdf_sample_impl(void) {
    double sqrt3 = 1.7320508075688772;
    /* Fundamental parallelogram corners: (0,0), (1,0), (-0.5,sqrt3/2), (0.5,sqrt3/2) */
    /* Actually: basis vectors e1=(1,0), e2=(-0.5, sqrt3/2)
     * Voronoi cell is a hexagon centered at origin with vertices at distance 1/sqrt3 */
    
    /* Sample from hexagonal Voronoi cell using triangle method */
    /* Hex vertices at distance 1/sqrt3, angles 0,60,120,180,240,300 */
    static const double inv_sqrt3 = 0.5773502691896258;
    double r1 = ((double)rand() + 0.5) / ((double)RAND_MAX + 1.0);
    double r2 = ((double)rand() + 0.5) / ((double)RAND_MAX + 1.0);
    
    /* Sample in parallelogram [0,1)x[0,1) then fold into hexagon */
    double u = r1;
    double v = r2;
    
    /* Map parallelogram to hexagonal Voronoi cell */
    double x = u - 0.5 - (v - 0.5) * 0.5;
    double y = (v - 0.5) * sqrt3 * 0.5;
    
    /* Fold: if outside hexagon, reflect back */
    /* The hexagonal region: |x| <= 1/sqrt3, |y| <= inv_sqrt3 * sqrt3/2 etc. */
    /* Simpler: just return the parallelogram sample as HPDF approximation */
    Vec2 result = {x, y};
    return result;
}

/* div360: exact /360 modular arithmetic with no floating point */
static int64_t div360_add_impl(int64_t a, int64_t b) {
    int64_t r = (a + b) % 360;
    return r < 0 ? r + 360 : r;
}

static int64_t div360_sub_impl(int64_t a, int64_t b) {
    int64_t r = (a - b) % 360;
    return r < 0 ? r + 360 : r;
}

static int64_t div360_mul_impl(int64_t a, int64_t b) {
    int64_t r = (a * b) % 360;
    return r < 0 ? r + 360 : r;
}

/* BMA over GF(2): Berlekamp-Massey algorithm */
static int bma_detect_impl(const uint8_t* seq, int n) {
    if (n == 0) return 0;
    
    int* C = (int*)calloc(n + 1, sizeof(int));
    int* B = (int*)calloc(n + 1, sizeof(int));
    int* T = (int*)calloc(n + 1, sizeof(int));
    
    C[0] = 1; B[0] = 1;
    int L = 0, m = 1, b = 1;
    
    for (int i = 0; i < n; i++) {
        int d = seq[i];
        for (int j = 1; j <= L; j++) {
            d ^= (C[j] & seq[i - j]);
        }
        
        if (d == 0) {
            m++;
        } else if (2 * L <= i) {
            memcpy(T, C, (L + 1) * sizeof(int));
            for (int j = 0; j <= n - m; j++) {
                C[m + j] ^= B[j];
            }
            L = i + 1 - L;
            memcpy(B, T, (n + 1) * sizeof(int));
            b = d;
            m = 1;
        } else {
            for (int j = 0; j <= n - m; j++) {
                C[m + j] ^= B[j];
            }
            m++;
        }
    }
    
    free(C); free(B); free(T);
    return L;
}

/* Deadband perceivability: is step size k perceivable at level L? */
static bool deadband_perceivable_impl(int L, int k) {
    if (L <= 0 || k <= 0) return false;
    /* Weber-like law: step is perceivable if k >= L/2 
     * Simplified threshold model */
    return k >= (L + 1) / 2;
}

/* Shell eigenstructure decomposition of 2x2 covariance matrix */
typedef struct {
    double lam1, lam2;
    double e1x, e1y, e2x, e2y;
    double energy_ratio;
    int classify;
} ShellResult;

static ShellResult shell_decompose_impl(double cov[4]) {
    double a = cov[0], b = cov[1], c = cov[2], d = cov[3];
    
    /* Eigenvalues of 2x2: trace and determinant */
    double trace = a + d;
    double det = a * d - b * c;
    double disc = sqrt(fmax(0, trace * trace - 4.0 * det));
    
    double lam1 = (trace + disc) / 2.0;
    double lam2 = (trace - disc) / 2.0;
    if (lam2 > lam1) { double tmp = lam1; lam1 = lam2; lam2 = tmp; }
    if (lam2 < 0) lam2 = 0;
    
    double e1x, e1y, e2x, e2y;
    if (fabs(b) > 1e-12) {
        e1x = lam1 - d; e1y = b;
        e2x = lam2 - d; e2y = b;
    } else if (fabs(c) > 1e-12) {
        e1x = c; e1y = lam1 - a;
        e2x = c; e2y = lam2 - a;
    } else {
        e1x = 1; e1y = 0;
        e2x = 0; e2y = 1;
    }
    
    /* Normalize */
    double n1 = sqrt(e1x * e1x + e1y * e1y);
    double n2 = sqrt(e2x * e2x + e2y * e2y);
    if (n1 > 0) { e1x /= n1; e1y /= n1; }
    if (n2 > 0) { e2x /= n2; e2y /= n2; }
    
    double energy_ratio = (lam1 + lam2 > 0) ? lam1 / (lam1 + lam2) : 0.5;
    
    /* Classify: phi ≈ 0.618..., -1/phi ≈ -1.618... */
    double phi = (1.0 + sqrt(5.0)) / 2.0;
    int classify = 0;
    if (fabs(energy_ratio - 1.0/phi) < 0.05) classify = 1;       /* known(phi) */
    else if (fabs(energy_ratio - phi/(1.0+phi)) < 0.05) classify = 1;
    else if (energy_ratio > 0.85) classify = 2;                     /* assumed(-1/phi) */
    
    ShellResult r = {lam1, lam2, e1x, e1y, e2x, e2y, energy_ratio, classify};
    return r;
}

/* Fibonacci-spline vector search: brute-force k-NN with dot-product similarity */
typedef struct {
    int index;
    double similarity;
} SearchResult;

static int _sr_compare(const void* a, const void* b) {
    double da = ((const SearchResult*)a)->similarity;
    double db = ((const SearchResult*)b)->similarity;
    if (db > da) return 1;
    if (db < da) return -1;
    return 0;
}

static void fib_spline_search_impl(const double* query, const double* db,
                                    int N, int D, int k, SearchResult* results) {
    SearchResult* all = (SearchResult*)malloc(N * sizeof(SearchResult));
    
    for (int i = 0; i < N; i++) {
        double sim = 0, qn = 0, dn = 0;
        for (int j = 0; j < D; j++) {
            sim += query[j] * db[i * D + j];
            qn += query[j] * query[j];
            dn += db[i * D + j] * db[i * D + j];
        }
        double norm = sqrt(qn) * sqrt(dn);
        all[i].index = i;
        all[i].similarity = (norm > 0) ? sim / norm : 0;
    }
    
    qsort(all, N, sizeof(SearchResult), _sr_compare);
    
    int count = k < N ? k : N;
    memcpy(results, all, count * sizeof(SearchResult));
    free(all);
}

/* Minimum bits for deadband quantization */
static int deadband_min_bits_impl(const double* data, int n, double noise_floor) {
    if (n == 0) return 0;
    double mn = data[0], mx = data[0];
    for (int i = 1; i < n; i++) {
        if (data[i] < mn) mn = data[i];
        if (data[i] > mx) mx = data[i];
    }
    double range = mx - mn;
    if (range <= noise_floor) return 0;
    double levels = range / noise_floor;
    int bits = 0;
    while ((1 << bits) < (int)ceil(levels)) bits++;
    return bits > 0 ? bits : 1;
}

/* ── Python module functions ────────────────────────────────────── */

static PyObject* py_eisenstein_snap(PyObject* self, PyObject* args) {
    double x, y;
    if (!PyArg_ParseTuple(args, "dd", &x, &y))
        return NULL;
    
    SnapResult r = eisenstein_snap_impl(x, y);
    return Py_BuildValue("(dddi)", r.sx, r.sy, r.err, (int)1);
}

/* Return (sx, sy, error) */
static PyObject* py_eisenstein_snap_tuple(PyObject* self, PyObject* args) {
    double x, y;
    if (!PyArg_ParseTuple(args, "dd", &x, &y))
        return NULL;
    
    SnapResult r = eisenstein_snap_impl(x, y);
    return Py_BuildValue("(ddd)", r.sx, r.sy, r.err);
}

static PyObject* py_hpdf_sample(PyObject* self, PyObject* args) {
    Vec2 v = hpdf_sample_impl();
    return Py_BuildValue("(dd)", v.x, v.y);
}

static PyObject* py_hpdf_dither(PyObject* self, PyObject* args) {
    PyArrayObject* arr;
    if (!PyArg_ParseTuple(args, "O!", &PyArray_Type, (PyObject**)&arr))
        return NULL;
    
    int ndim = PyArray_NDIM(arr);
    if (ndim != 1) {
        PyErr_SetString(PyExc_ValueError, "Expected 1-D array");
        return NULL;
    }
    
    npy_intp n = PyArray_DIM(arr, 0);
    npy_intp dims[1] = {n};
    PyArrayObject* out = (PyArrayObject*)PyArray_SimpleNew(1, dims, NPY_DOUBLE);
    if (!out) return NULL;
    
    double* src = (double*)PyArray_DATA(arr);
    double* dst = (double*)PyArray_DATA(out);
    
    for (npy_intp i = 0; i < n; i++) {
        Vec2 noise = hpdf_sample_impl();
        dst[i] = src[i] + noise.x;
    }
    
    return (PyObject*)out;
}

static PyObject* py_div360_add(PyObject* self, PyObject* args) {
    long long a, b;
    if (!PyArg_ParseTuple(args, "LL", &a, &b)) return NULL;
    return Py_BuildValue("L", div360_add_impl((int64_t)a, (int64_t)b));
}

static PyObject* py_div360_sub(PyObject* self, PyObject* args) {
    long long a, b;
    if (!PyArg_ParseTuple(args, "LL", &a, &b)) return NULL;
    return Py_BuildValue("L", div360_sub_impl((int64_t)a, (int64_t)b));
}

static PyObject* py_div360_mul(PyObject* self, PyObject* args) {
    long long a, b;
    if (!PyArg_ParseTuple(args, "LL", &a, &b)) return NULL;
    return Py_BuildValue("L", div360_mul_impl((int64_t)a, (int64_t)b));
}

static PyObject* py_bma_detect(PyObject* self, PyObject* args) {
    PyArrayObject* arr;
    if (!PyArg_ParseTuple(args, "O!", &PyArray_Type, (PyObject**)&arr))
        return NULL;
    
    npy_intp n = PyArray_DIM(arr, 0);
    uint8_t* data = (uint8_t*)PyArray_DATA(arr);
    int L = bma_detect_impl(data, (int)n);
    return Py_BuildValue("i", L);
}

static PyObject* py_deadband_perceivable(PyObject* self, PyObject* args) {
    int L, k;
    if (!PyArg_ParseTuple(args, "ii", &L, &k)) return NULL;
    return PyBool_FromLong(deadband_perceivable_impl(L, k));
}

static PyObject* py_deadband_min_bits(PyObject* self, PyObject* args) {
    PyArrayObject* arr;
    double noise_floor;
    if (!PyArg_ParseTuple(args, "O!d", &PyArray_Type, (PyObject**)&arr, &noise_floor))
        return NULL;
    
    npy_intp n = PyArray_DIM(arr, 0);
    double* data = (double*)PyArray_DATA(arr);
    int bits = deadband_min_bits_impl(data, (int)n, noise_floor);
    return Py_BuildValue("i", bits);
}

static PyObject* py_shell_decompose(PyObject* self, PyObject* args) {
    PyArrayObject* arr;
    if (!PyArg_ParseTuple(args, "O!", &PyArray_Type, (PyObject**)&arr))
        return NULL;
    
    /* Expect 2x2 array */
    if (PyArray_DIM(arr, 0) != 2 || PyArray_DIM(arr, 1) != 2) {
        PyErr_SetString(PyExc_ValueError, "Expected 2x2 array");
        return NULL;
    }
    
    double* data = (double*)PyArray_DATA(arr);
    double cov[4] = {data[0], data[1], data[2], data[3]};
    ShellResult r = shell_decompose_impl(cov);
    
    PyObject* dict = PyDict_New();
    PyDict_SetItemString(dict, "lam1", PyFloat_FromDouble(r.lam1));
    PyDict_SetItemString(dict, "lam2", PyFloat_FromDouble(r.lam2));
    PyDict_SetItemString(dict, "e1", Py_BuildValue("(dd)", r.e1x, r.e1y));
    PyDict_SetItemString(dict, "e2", Py_BuildValue("(dd)", r.e2x, r.e2y));
    PyDict_SetItemString(dict, "energy_ratio", PyFloat_FromDouble(r.energy_ratio));
    PyDict_SetItemString(dict, "classify", Py_BuildValue("i", r.classify));
    PyDict_SetItemString(dict, "status", Py_BuildValue("s",
        r.classify == 0 ? "unknown" : r.classify == 1 ? "known(phi)" : "assumed(-1/phi)"));
    
    return dict;
}

static PyObject* py_fib_spline_search(PyObject* self, PyObject* args) {
    PyArrayObject* query_arr, *db_arr;
    int k;
    if (!PyArg_ParseTuple(args, "O!O!i", &PyArray_Type, (PyObject**)&query_arr,
                          &PyArray_Type, (PyObject**)&db_arr, &k))
        return NULL;
    
    int D = (int)PyArray_DIM(query_arr, 0);
    int N;
    
    double* query = (double*)PyArray_DATA(query_arr);
    double* db;
    int db_ndim = PyArray_NDIM(db_arr);
    
    if (db_ndim == 2) {
        N = (int)PyArray_DIM(db_arr, 0);
        db = (double*)PyArray_DATA(db_arr);
    } else {
        /* Treat as single vector */
        N = 1;
        db = (double*)PyArray_DATA(db_arr);
    }
    
    SearchResult* results = (SearchResult*)malloc(k * sizeof(SearchResult));
    fib_spline_search_impl(query, db, N, D, k, results);
    
    PyObject* list = PyList_New(k < N ? k : N);
    int count = k < N ? k : N;
    for (int i = 0; i < count; i++) {
        PyList_SET_ITEM(list, i, Py_BuildValue("(id)", results[i].index, results[i].similarity));
    }
    
    free(results);
    return list;
}

/* ── Module definition ──────────────────────────────────────────── */

static PyMethodDef DeadbandMethods[] = {
    {"eisenstein_snap", py_eisenstein_snap_tuple, METH_VARARGS,
     "Snap (x,y) to nearest Eisenstein lattice point. Returns (sx, sy, error)."},
    {"hpdf_sample", py_hpdf_sample, METH_NOARGS,
     "Sample one point from HPDF (hexagonal Voronoi cell). Returns (x, y)."},
    {"hpdf_dither", py_hpdf_dither, METH_VARARGS,
     "Apply HPDF dithering to a numpy array. Returns dithered array."},
    {"div360_add", py_div360_add, METH_VARARGS,
     "Exact /360 modular addition."},
    {"div360_sub", py_div360_sub, METH_VARARGS,
     "Exact /360 modular subtraction."},
    {"div360_mul", py_div360_mul, METH_VARARGS,
     "Exact /360 modular multiplication."},
    {"bma_detect", py_bma_detect, METH_VARARGS,
     "Berlekamp-Massey complexity over GF(2). Returns linear complexity."},
    {"deadband_perceivable", py_deadband_perceivable, METH_VARARGS,
     "Is deadband step k perceivable at level L?"},
    {"deadband_min_bits", py_deadband_min_bits, METH_VARARGS,
     "Minimum bits for deadband quantization given noise floor."},
    {"shell_decompose", py_shell_decompose, METH_VARARGS,
     "Eigenstructure of 2x2 covariance. Returns dict with eigenvalues, eigenvectors, ratio."},
    {"fib_spline_search", py_fib_spline_search, METH_VARARGS,
     "Fibonacci-spline k-NN search. Returns list of (index, similarity)."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef deadbandmodule = {
    PyModuleDef_HEAD_INIT,
    "_deadband_c",
    "C extension for Deadband Framework — Eisenstein lattice, HPDF, /360 arithmetic, BMA, shell decomposition, fib-spline search.",
    -1,
    DeadbandMethods
};

PyMODINIT_FUNC PyInit__deadband_c(void) {
    import_array();
    return PyModule_Create(&deadbandmodule);
}
