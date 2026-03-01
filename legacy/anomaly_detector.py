"""Anomaly detection for distribution shape changes between snapshots.

Compares distribution metrics from consecutive AlphaLog snapshots
to flag significant regime shifts and shape changes.
"""

from __future__ import annotations

# Change thresholds (as fractions)
SKEW_FLIP_BOUNDARY = 1.0
TAIL_CHANGE_THRESHOLD = 0.20
WIDTH_CHANGE_THRESHOLD = 0.20

SEVERITY_LEVELS: list[tuple[float, str]] = [
    (0.50, "HIGH"),
    (0.30, "MEDIUM"),
    (0.0, "LOW"),
]


def _severity(change_pct: float) -> str:
    """Map absolute percentage change to severity level."""
    for threshold, label in SEVERITY_LEVELS:
        if change_pct >= threshold:
            return label
    return "LOW"


class AnomalyDetector:
    """Detects significant changes in distribution shape between snapshots."""

    def detect_anomalies(
        self,
        current_metrics: dict,
        previous_metrics: dict,
    ) -> list[dict]:
        """Compare two sets of distribution metrics and flag significant changes.

        Args:
            current_metrics: Output from DistributionAnalyzer for the latest snapshot.
            previous_metrics: Output from DistributionAnalyzer for the previous snapshot.

        Returns:
            List of anomaly dicts.
        """
        anomalies: list[dict] = []

        # Only compare keys present in both
        common_keys = set(current_metrics.keys()) & set(previous_metrics.keys())

        for key in sorted(common_keys):
            curr = current_metrics[key]
            prev = previous_metrics[key]
            asset = curr.get("asset", key)

            anomalies.extend(self._check_skew_flip(asset, key, curr, prev))
            anomalies.extend(self._check_tail_fattening(asset, key, curr, prev))
            anomalies.extend(self._check_width_change(asset, key, curr, prev))
            anomalies.extend(self._check_regime_change(asset, key, curr, prev))

        return anomalies

    def _check_skew_flip(
        self, asset: str, key: str, curr: dict, prev: dict
    ) -> list[dict]:
        prev_asym = prev.get("tail_asymmetry")
        curr_asym = curr.get("tail_asymmetry")
        if prev_asym is None or curr_asym is None:
            return []

        # Check if tail_asymmetry crossed 1.0
        crossed = (prev_asym < SKEW_FLIP_BOUNDARY <= curr_asym) or (
            curr_asym < SKEW_FLIP_BOUNDARY <= prev_asym
        )
        if not crossed:
            return []

        if curr_asym > SKEW_FLIP_BOUNDARY:
            direction = "bearish to bullish"
        else:
            direction = "bullish to bearish"

        change = abs(curr_asym - prev_asym)
        return [
            {
                "asset": asset,
                "key": key,
                "anomaly_type": "skew_flip",
                "severity": _severity(change),
                "previous_value": prev_asym,
                "current_value": curr_asym,
                "description": f"{asset} skew flipped from {direction}",
            }
        ]

    def _check_tail_fattening(
        self, asset: str, key: str, curr: dict, prev: dict
    ) -> list[dict]:
        prev_tail = prev.get("tail_fatness")
        curr_tail = curr.get("tail_fatness")
        if not prev_tail or not curr_tail or prev_tail == 0:
            return []

        change_pct = (curr_tail - prev_tail) / prev_tail
        if change_pct <= TAIL_CHANGE_THRESHOLD:
            return []

        return [
            {
                "asset": asset,
                "key": key,
                "anomaly_type": "tail_fattening",
                "severity": _severity(change_pct),
                "previous_value": prev_tail,
                "current_value": curr_tail,
                "change_pct": round(change_pct, 4),
                "description": (
                    f"{asset} tails fattened by {change_pct:.0%} "
                    f"({prev_tail:.2f} -> {curr_tail:.2f})"
                ),
            }
        ]

    def _check_width_change(
        self, asset: str, key: str, curr: dict, prev: dict
    ) -> list[dict]:
        prev_width = prev.get("forecast_width")
        curr_width = curr.get("forecast_width")
        if not prev_width or not curr_width or prev_width == 0:
            return []

        change_pct = (curr_width - prev_width) / prev_width
        abs_change = abs(change_pct)

        if abs_change <= WIDTH_CHANGE_THRESHOLD:
            return []

        if change_pct > 0:
            anomaly_type = "volatility_expansion"
            description = (
                f"{asset} forecast width expanded by {abs_change:.0%} "
                f"({prev_width:.4%} -> {curr_width:.4%})"
            )
        else:
            anomaly_type = "volatility_compression"
            description = (
                f"{asset} forecast width compressed by {abs_change:.0%} "
                f"({prev_width:.4%} -> {curr_width:.4%})"
            )

        return [
            {
                "asset": asset,
                "key": key,
                "anomaly_type": anomaly_type,
                "severity": _severity(abs_change),
                "previous_value": prev_width,
                "current_value": curr_width,
                "change_pct": round(change_pct, 4),
                "description": description,
            }
        ]

    def _check_regime_change(
        self, asset: str, key: str, curr: dict, prev: dict
    ) -> list[dict]:
        prev_regime = prev.get("regime")
        curr_regime = curr.get("regime")
        if not prev_regime or not curr_regime or prev_regime == curr_regime:
            return []

        return [
            {
                "asset": asset,
                "key": key,
                "anomaly_type": "regime_change",
                "severity": "HIGH",
                "previous_value": prev_regime,
                "current_value": curr_regime,
                "description": (
                    f"{asset} regime changed from {prev_regime} to {curr_regime}"
                ),
            }
        ]
