"""
deadband_python — Python bindings for the Deadband Framework

Tries the C extension first for maximum speed.
Falls back to pure Python implementation if C is unavailable.
"""

# Try C extension first
_use_c = False
try:
    from . import _deadband_c as _impl
    _use_c = True
except ImportError:
    from . import deadband as _impl
    _use_c = False

# Re-export all public API
eisenstein_snap = _impl.eisenstein_snap
hpdf_sample = _impl.hpdf_sample
hpdf_dither = _impl.hpdf_dither
div360_add = _impl.div360_add
div360_sub = _impl.div360_sub
div360_mul = _impl.div360_mul
bma_detect = _impl.bma_detect
deadband_perceivable = _impl.deadband_perceivable
deadband_min_bits = _impl.deadband_min_bits
shell_decompose = _impl.shell_decompose
fib_spline_search = _impl.fib_spline_search

__all__ = [
    "eisenstein_snap",
    "hpdf_sample",
    "hpdf_dither",
    "div360_add",
    "div360_sub",
    "div360_mul",
    "bma_detect",
    "deadband_perceivable",
    "deadband_min_bits",
    "shell_decompose",
    "fib_spline_search",
    "using_c_extension",
]


def using_c_extension():
    """Return True if the C extension is loaded."""
    return _use_c


__version__ = "0.1.0"
