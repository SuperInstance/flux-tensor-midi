"""
flux_check — Constraint checker: zero false negatives, uint8 error masks.

    from flux_check import ConstraintEngine, CheckResult, Severity
"""

from flux_check.core import ConstraintEngine, CheckResult, Severity, ConstraintDef, ViolationDetail
from flux_check.presets import PRESETS, available_presets, get_preset

__all__ = [
    "ConstraintEngine", "CheckResult", "Severity",
    "ConstraintDef", "ViolationDetail",
    "PRESETS", "available_presets", "get_preset",
]
__version__ = "0.1.0"
