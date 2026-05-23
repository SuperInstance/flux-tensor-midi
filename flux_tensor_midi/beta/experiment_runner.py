"""
A/B experiment runner for beta testing.

Defines experiments with control/treatment groups, randomly assigns
users, collects metrics, and performs statistical analysis (t-test,
effect size).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Experiment:
    """A single A/B experiment definition."""

    def __init__(
        self,
        name: str,
        control_params: dict[str, Any],
        treatment_params: dict[str, Any],
    ) -> None:
        self.name = name
        self.control_params = control_params
        self.treatment_params = treatment_params
        self.assignments: dict[str, str] = {}  # user_id -> "control" | "treatment"
        self.metrics: dict[str, list[dict[str, Any]]] = {
            "control": [],
            "treatment": [],
        }

    def assign_group(self, user_id: str) -> str:
        """Deterministically assign a user to control or treatment."""
        if user_id in self.assignments:
            return self.assignments[user_id]
        # Deterministic hash-based assignment (50/50 split)
        h = int(hashlib.sha256(f"{self.name}:{user_id}".encode()).hexdigest(), 16)
        group = "control" if h % 2 == 0 else "treatment"
        self.assignments[user_id] = group
        return group

    def record_metric(
        self,
        user_id: str,
        metric_name: str,
        value: float,
    ) -> None:
        """Record a metric value for a user (auto-determines group)."""
        group = self.assign_group(user_id)
        self.metrics[group].append({
            "user_id": user_id,
            "metric_name": metric_name,
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_params_for(self, user_id: str) -> dict[str, Any]:
        """Get the experiment parameters for a given user."""
        group = self.assign_group(user_id)
        return self.control_params if group == "control" else self.treatment_params

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "control_params": self.control_params,
            "treatment_params": self.treatment_params,
            "assignments": self.assignments,
            "metrics": self.metrics,
        }


class ExperimentRunner:
    """Manages multiple A/B experiments.

    Usage::

        runner = ExperimentRunner()
        runner.define_experiment(
            "goldilocks",
            control_params={"epsilon": 0.15},
            treatment_params={"epsilon": 0.30},
        )
        group = runner.assign_group("goldilocks", "user_42")
        runner.record_metric("goldilocks", "user_42", "composition_count", 5)
        results = runner.analyze_results("goldilocks")
    """

    def __init__(self, output_dir: str | Path = "beta_data/experiments") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.experiments: dict[str, Experiment] = {}

    # ── public API ──────────────────────────────────────────────────────

    def define_experiment(
        self,
        name: str,
        control_params: dict[str, Any],
        treatment_params: dict[str, Any],
    ) -> Experiment:
        """Define a new A/B experiment."""
        exp = Experiment(name, control_params, treatment_params)
        self.experiments[name] = exp
        return exp

    def assign_group(self, experiment_name: str, user_id: str) -> str:
        """Assign a user to a group in the given experiment."""
        return self._get_experiment(experiment_name).assign_group(user_id)

    def get_params(self, experiment_name: str, user_id: str) -> dict[str, Any]:
        """Get the parameters a user should receive."""
        return self._get_experiment(experiment_name).get_params_for(user_id)

    def record_metric(
        self,
        experiment_name: str,
        user_id: str,
        metric_name: str,
        value: float,
    ) -> None:
        """Record a metric for a user in an experiment."""
        self._get_experiment(experiment_name).record_metric(user_id, metric_name, value)

    def analyze_results(
        self,
        experiment_name: str,
        metric_name: str | None = None,
    ) -> dict[str, Any]:
        """Run statistical analysis on collected metrics.

        Returns dict with:
            - metric_name: which metric was analyzed
            - control_n, treatment_n: sample sizes
            - control_mean, treatment_mean
            - control_std, treatment_std
            - t_statistic: Welch's t-test statistic
            - p_value: approximate two-tailed p-value
            - cohens_d: effect size
            - significant_005: whether p < 0.05
        """
        exp = self._get_experiment(experiment_name)
        results = {}

        for group in ("control", "treatment"):
            values = [
                m["value"]
                for m in exp.metrics[group]
                if metric_name is None or m["metric_name"] == metric_name
            ]
            results[f"{group}_values"] = values
            results[f"{group}_n"] = len(values)
            results[f"{group}_mean"] = _mean(values)
            results[f"{group}_std"] = _std(values)

        ctrl_vals = results["control_values"]
        treat_vals = results["treatment_values"]

        if len(ctrl_vals) < 2 or len(treat_vals) < 2:
            return {
                "experiment": experiment_name,
                "metric_name": metric_name,
                "control_n": results["control_n"],
                "treatment_n": results["treatment_n"],
                "control_mean": results["control_mean"],
                "treatment_mean": results["treatment_mean"],
                "control_std": results["control_std"],
                "treatment_std": results["treatment_std"],
                "t_statistic": None,
                "p_value": None,
                "cohens_d": None,
                "significant_005": False,
                "note": "Insufficient data for statistical analysis (need >= 2 per group)",
            }

        t_stat, p_val = _welch_t_test(ctrl_vals, treat_vals)
        d = _cohens_d(ctrl_vals, treat_vals)

        return {
            "experiment": experiment_name,
            "metric_name": metric_name,
            "control_n": results["control_n"],
            "treatment_n": results["treatment_n"],
            "control_mean": round(results["control_mean"], 4),
            "treatment_mean": round(results["treatment_mean"], 4),
            "control_std": round(results["control_std"], 4),
            "treatment_std": round(results["treatment_std"], 4),
            "t_statistic": round(t_stat, 4),
            "p_value": round(p_val, 6),
            "cohens_d": round(d, 4),
            "significant_005": p_val < 0.05,
        }

    def save_experiment(self, experiment_name: str) -> Path:
        """Persist an experiment to disk."""
        exp = self._get_experiment(experiment_name)
        path = self.output_dir / f"{experiment_name}.json"
        path.write_text(json.dumps(exp.to_dict(), indent=2))
        return path

    def load_experiment(self, experiment_name: str) -> Experiment:
        """Load an experiment from disk."""
        path = self.output_dir / f"{experiment_name}.json"
        data = json.loads(path.read_text())
        exp = Experiment(data["name"], data["control_params"], data["treatment_params"])
        exp.assignments = data.get("assignments", {})
        exp.metrics = data.get("metrics", {"control": [], "treatment": []})
        self.experiments[experiment_name] = exp
        return exp

    # ── helpers ─────────────────────────────────────────────────────────

    def _get_experiment(self, name: str) -> Experiment:
        if name not in self.experiments:
            raise KeyError(f"Experiment '{name}' not defined. Call define_experiment() first.")
        return self.experiments[name]


# ── Statistics helpers (pure Python, no scipy dependency) ───────────────

def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def _welch_t_test(a: list[float], b: list[float]) -> tuple[float, float]:
    """Welch's t-test returning (t_statistic, approximate p_value)."""
    n1, n2 = len(a), len(b)
    m1, m2 = _mean(a), _mean(b)
    s1, s2 = _std(a), _std(b)

    se1 = (s1 ** 2) / n1
    se2 = (s2 ** 2) / n2
    se = math.sqrt(se1 + se2)

    if se == 0:
        return (0.0, 1.0)

    t = (m1 - m2) / se

    # Welch-Satterthwaite degrees of freedom
    df_num = (se1 + se2) ** 2
    df_den = (se1 ** 2) / (n1 - 1) + (se2 ** 2) / (n2 - 1)
    df = df_num / df_den if df_den > 0 else 1.0

    # Approximate two-tailed p-value using regularized incomplete beta function
    p = _two_tailed_p(abs(t), df)
    return t, p


def _two_tailed_p(t_abs: float, df: float) -> float:
    """Approximate two-tailed p-value from |t| and df using a series expansion."""
    x = df / (df + t_abs ** 2)
    # Regularized incomplete beta function I_x(df/2, 1/2)
    try:
        p = _regularized_incomplete_beta(x, df / 2.0, 0.5)
    except (ValueError, OverflowError):
        p = 1.0
    return max(0.0, min(1.0, p))


def _regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """Regularized incomplete beta function via continued fraction."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    # Use symmetry: I_x(a,b) = 1 - I_{1-x}(b,a)
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _regularized_incomplete_beta(1 - x, b, a)

    lbeta = _log_beta(a, b)
    prefix = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) / a

    # Lentz's continued fraction
    f = 1.0
    c = 1.0
    d = 1.0 - (a + 1) * x / (a + 1)

    if abs(d) < 1e-30:
        d = 1e-30

    d = 1.0 / d
    f = d

    for m in range(1, 101):
        # Even step
        numerator = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + numerator * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + numerator / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        f *= c * d

        # Odd step
        numerator = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + numerator * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + numerator / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = c * d
        f *= delta

        if abs(delta - 1.0) < 1e-10:
            break

    return prefix * f


def _log_beta(a: float, b: float) -> float:
    """Log Beta function via Stirling/LogGamma."""
    return _log_gamma(a) + _log_gamma(b) - _log_gamma(a + b)


def _log_gamma(x: float) -> float:
    """Log Gamma function (Lanczos approximation)."""
    if x < 0.5:
        return math.log(math.pi / math.sin(math.pi * x)) - _log_gamma(1 - x)
    x -= 1.0
    g = 7
    coef = [
        0.99999999999980993,
        676.5203681218851,
        -1259.1392167224028,
        771.32342877765313,
        -176.61502916214059,
        12.507343278686905,
        -0.13857109526572012,
        9.9843695780195716e-6,
        1.5056327351493116e-7,
    ]
    s = coef[0]
    for i in range(1, g + 2):
        s += coef[i] / (x + i)
    t = x + g + 0.5
    return 0.5 * math.log(2 * math.pi) + (x + 0.5) * math.log(t) - t + math.log(s)


def _cohens_d(a: list[float], b: list[float]) -> float:
    """Cohen's d effect size."""
    n1, n2 = len(a), len(b)
    m1, m2 = _mean(a), _mean(b)
    s1, s2 = _std(a), _std(b)
    # Pooled std
    pooled = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2)) if (n1 + n2 > 2) else 0.0
    if pooled == 0:
        return 0.0
    return (m1 - m2) / pooled
