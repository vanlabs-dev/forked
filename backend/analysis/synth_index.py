"""Synth-Index: composite forward-looking uncertainty score.

Combines distribution shape metrics into a single 0-100 score
indicating the level of forecast uncertainty for each asset.
"""

from __future__ import annotations

from backend.analysis.distribution import _asset_class

# Score level labels
LEVELS: list[tuple[float, str]] = [
    (85, "EXTREME"),
    (70, "ELEVATED"),
    (50, "ABOVE_AVERAGE"),
    (30, "BELOW_AVERAGE"),
    (0, "CALM"),
]

# Component weights
W_WIDTH = 0.40
W_TAIL = 0.25
W_SKEW = 0.20
W_CONCENTRATION = 0.15


def _normalize(value: float, lo: float, hi: float) -> float:
    """Min-max normalize and clamp to [0, 1]."""
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _width_bounds(asset: str) -> tuple[float, float]:
    """Return (min, max) bounds for forecast_width normalization."""
    cls = _asset_class(asset)
    if cls == "crypto":
        return 0.0, 0.10
    if cls == "equity":
        return 0.0, 0.05
    # gold
    return 0.0, 0.06


def _level_label(score: float) -> str:
    for threshold, label in LEVELS:
        if score >= threshold:
            return label
    return "CALM"


class SynthIndex:
    """Computes a forward-looking uncertainty score from distribution shape metrics."""

    def compute(self, distribution_metrics: dict) -> dict:
        """Compute Synth-Index for all assets in the distribution metrics.

        Args:
            distribution_metrics: Output from DistributionAnalyzer.analyze_snapshot().

        Returns:
            Dict keyed by (asset_horizon) with Synth-Index scores.
        """
        results: dict[str, dict] = {}

        for key, metrics in distribution_metrics.items():
            score_data = self._compute_single(metrics)
            if score_data:
                results[key] = score_data

        return results

    def _compute_single(self, metrics: dict) -> dict | None:
        """Compute Synth-Index for a single asset/horizon pair."""
        asset = metrics.get("asset", "")
        horizon = metrics.get("horizon", "")
        forecast_width = metrics.get("forecast_width")
        tail_fatness = metrics.get("tail_fatness")
        tail_asymmetry = metrics.get("tail_asymmetry")
        density_concentration = metrics.get("density_concentration")

        if any(v is None for v in [forecast_width, tail_fatness, tail_asymmetry, density_concentration]):
            return None

        # Normalize each component
        w_lo, w_hi = _width_bounds(asset)
        norm_width = _normalize(forecast_width, w_lo, w_hi)
        norm_tail = _normalize(tail_fatness, 1.0, 5.0)
        norm_skew = _normalize(abs(tail_asymmetry - 1.0), 0.0, 2.0)
        norm_inv_density = _normalize(1.0 - density_concentration, 0.0, 1.0)

        # Weighted composite
        raw_score = (
            norm_width * W_WIDTH
            + norm_tail * W_TAIL
            + norm_skew * W_SKEW
            + norm_inv_density * W_CONCENTRATION
        ) * 100

        score = round(max(0.0, min(100.0, raw_score)), 1)

        return {
            "asset": asset,
            "horizon": horizon,
            "synth_index": score,
            "level": _level_label(score),
            "components": {
                "width_contribution": round(norm_width * W_WIDTH * 100, 1),
                "tail_contribution": round(norm_tail * W_TAIL * 100, 1),
                "skew_contribution": round(norm_skew * W_SKEW * 100, 1),
                "concentration_contribution": round(norm_inv_density * W_CONCENTRATION * 100, 1),
            },
        }
