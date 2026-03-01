"""ProbabilityEngine — Interpolates Synth percentile forecasts to compute
probabilities for arbitrary price ranges.

The Synth API returns price forecasts at 9 percentile levels (CDF values)
across ~289 timepoints per horizon. This module interpolates between those
levels to answer questions like "What's the probability BTC stays between
$85k-$92k in 24h?"
"""

from __future__ import annotations

from typing import Any

from backend.synth_client import SynthClient

# Percentile levels returned by the Synth API, in ascending order.
PERCENTILE_LEVELS: list[float] = [0.005, 0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95, 0.995]

# String keys as they appear in the API response.
PERCENTILE_KEYS: list[str] = ["0.005", "0.05", "0.2", "0.35", "0.5", "0.65", "0.8", "0.95", "0.995"]

# Horizon durations in seconds.
_HORIZON_SECONDS: dict[str, int] = {"1h": 3600, "24h": 86400}


class ProbabilityEngine:
    """Interpolates Synth percentile forecasts to compute probabilities
    for arbitrary price ranges."""

    def __init__(self, synth_client: SynthClient) -> None:
        self._client = synth_client

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def get_percentile_data(self, asset: str, horizon: str = "24h") -> dict[str, Any]:
        """Fetch raw percentile data from Synth API.

        Returns:
            {
                "asset": str,
                "horizon": str,
                "current_price": float,
                "timepoints": [
                    {
                        "seconds_ahead": int,
                        "prices": {0.005: float, ..., 0.995: float}
                    },
                    ...
                ]
            }
        """
        raw = self._client.get_prediction_percentiles(asset=asset, horizon=horizon)

        current_price: float = float(raw["current_price"])
        raw_timepoints: list[dict[str, Any]] = raw["forecast_future"]["percentiles"]

        n = len(raw_timepoints)
        total_seconds = _HORIZON_SECONDS[horizon]
        step = total_seconds / max(n - 1, 1)

        timepoints: list[dict[str, Any]] = []
        for i, tp in enumerate(raw_timepoints):
            prices = {level: float(tp[key]) for level, key in zip(PERCENTILE_LEVELS, PERCENTILE_KEYS)}
            timepoints.append({
                "seconds_ahead": round(step * i),
                "prices": prices,
            })

        return {
            "asset": asset,
            "horizon": horizon,
            "current_price": current_price,
            "timepoints": timepoints,
        }

    # ------------------------------------------------------------------
    # Probability queries
    # ------------------------------------------------------------------

    def probability_above(
        self,
        asset: str,
        target_price: float,
        horizon: str = "24h",
        timepoint_index: int = -1,
    ) -> dict[str, Any]:
        """Probability that the asset will be ABOVE *target_price* at a
        given timepoint."""
        data = self.get_percentile_data(asset, horizon)
        tp = data["timepoints"][timepoint_index]
        cdf = self._interpolate_probability(target_price, tp["prices"])
        prob_above = 1.0 - cdf
        confidence = self._confidence_label(target_price, tp["prices"])

        return {
            "asset": asset,
            "target_price": target_price,
            "current_price": data["current_price"],
            "probability": round(prob_above, 4),
            "horizon": horizon,
            "timepoint_seconds": tp["seconds_ahead"],
            "confidence": confidence,
        }

    def probability_below(
        self,
        asset: str,
        target_price: float,
        horizon: str = "24h",
        timepoint_index: int = -1,
    ) -> dict[str, Any]:
        """Probability that the asset will be BELOW *target_price* at a
        given timepoint."""
        data = self.get_percentile_data(asset, horizon)
        tp = data["timepoints"][timepoint_index]
        cdf = self._interpolate_probability(target_price, tp["prices"])
        confidence = self._confidence_label(target_price, tp["prices"])

        return {
            "asset": asset,
            "target_price": target_price,
            "current_price": data["current_price"],
            "probability": round(cdf, 4),
            "horizon": horizon,
            "timepoint_seconds": tp["seconds_ahead"],
            "confidence": confidence,
        }

    def probability_between(
        self,
        asset: str,
        lower: float,
        upper: float,
        horizon: str = "24h",
        timepoint_index: int = -1,
    ) -> dict[str, Any]:
        """Probability that the asset price lands between *lower* and
        *upper* at a given timepoint.

        P(lower < price < upper) = CDF(upper) - CDF(lower)
        """
        data = self.get_percentile_data(asset, horizon)
        tp = data["timepoints"][timepoint_index]

        cdf_upper = self._interpolate_probability(upper, tp["prices"])
        cdf_lower = self._interpolate_probability(lower, tp["prices"])
        prob_between = cdf_upper - cdf_lower

        conf_lower = self._confidence_label(lower, tp["prices"])
        conf_upper = self._confidence_label(upper, tp["prices"])
        confidence = self._worst_confidence(conf_lower, conf_upper)

        return {
            "asset": asset,
            "lower": lower,
            "upper": upper,
            "current_price": data["current_price"],
            "probability": round(prob_between, 4),
            "probability_below_lower": round(cdf_lower, 4),
            "probability_above_upper": round(1.0 - cdf_upper, 4),
            "horizon": horizon,
            "timepoint_seconds": tp["seconds_ahead"],
            "confidence": confidence,
        }

    # ------------------------------------------------------------------
    # Probability cone (for visualization)
    # ------------------------------------------------------------------

    def probability_cone(
        self,
        asset: str,
        horizon: str = "24h",
        num_points: int = 50,
    ) -> dict[str, Any]:
        """Generate the full probability cone for visualization.

        Samples evenly across all timepoints to produce *num_points* data
        points. Each point contains all 9 percentile levels — the fan/cone
        shape that widens over time.
        """
        data = self.get_percentile_data(asset, horizon)
        all_tp = data["timepoints"]
        n = len(all_tp)

        # Pick evenly-spaced indices (always include first and last).
        if num_points >= n:
            indices = list(range(n))
        else:
            indices = [round(i * (n - 1) / (num_points - 1)) for i in range(num_points)]

        points: list[dict[str, Any]] = []
        for idx in indices:
            tp = all_tp[idx]
            points.append({
                "seconds_ahead": tp["seconds_ahead"],
                "hours_ahead": round(tp["seconds_ahead"] / 3600, 3),
                "p005": tp["prices"][0.005],
                "p05": tp["prices"][0.05],
                "p20": tp["prices"][0.2],
                "p35": tp["prices"][0.35],
                "p50": tp["prices"][0.5],
                "p65": tp["prices"][0.65],
                "p80": tp["prices"][0.8],
                "p95": tp["prices"][0.95],
                "p995": tp["prices"][0.995],
            })

        return {
            "asset": asset,
            "current_price": data["current_price"],
            "horizon": horizon,
            "points": points,
        }

    # ------------------------------------------------------------------
    # Core interpolation
    # ------------------------------------------------------------------

    def _interpolate_probability(
        self,
        target_price: float,
        percentile_prices: dict[float, float],
    ) -> float:
        """Interpolate to find P(price < target_price) — the CDF value.

        Percentile levels are cumulative probabilities.  For example,
        ``percentile_prices[0.2] = 87000`` means "20% of outcomes are
        below $87 000".  If the target falls between the prices at P20
        and P35, we linearly interpolate to estimate the CDF.

        For targets beyond the outermost known percentiles (P0.5 / P99.5)
        we linearly extrapolate from the two nearest levels, clamped to
        [0.001, 0.999] to avoid asserting certainty.
        """
        # Build sorted list of (price, cdf_level) pairs.
        pairs = sorted(
            ((percentile_prices[level], level) for level in PERCENTILE_LEVELS),
            key=lambda x: x[0],
        )

        prices = [p for p, _ in pairs]
        cdfs = [c for _, c in pairs]

        # Below the lowest known percentile — extrapolate.
        if target_price <= prices[0]:
            slope = (cdfs[1] - cdfs[0]) / (prices[1] - prices[0]) if prices[1] != prices[0] else 0.0
            extrap = cdfs[0] + slope * (target_price - prices[0])
            return max(0.001, min(extrap, cdfs[0]))

        # Above the highest known percentile — extrapolate.
        if target_price >= prices[-1]:
            slope = (cdfs[-1] - cdfs[-2]) / (prices[-1] - prices[-2]) if prices[-1] != prices[-2] else 0.0
            extrap = cdfs[-1] + slope * (target_price - prices[-1])
            return max(cdfs[-1], min(extrap, 0.999))

        # Find the bracketing pair and interpolate.
        for i in range(len(prices) - 1):
            if prices[i] <= target_price <= prices[i + 1]:
                span = prices[i + 1] - prices[i]
                if span == 0:
                    return (cdfs[i] + cdfs[i + 1]) / 2
                t = (target_price - prices[i]) / span
                return cdfs[i] + t * (cdfs[i + 1] - cdfs[i])

        # Fallback (should never reach here).
        return 0.5

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_label(target_price: float, percentile_prices: dict[float, float]) -> str:
        """Classify confidence based on where the target sits relative to
        the known percentile range.

        HIGH:   between P5 and P95 (well within the distribution)
        MEDIUM: between P0.5–P5 or P95–P99.5 (in the tails)
        LOW:    beyond P0.5 or P99.5 (extrapolation territory)
        """
        p005 = percentile_prices[0.005]
        p05 = percentile_prices[0.05]
        p95 = percentile_prices[0.95]
        p995 = percentile_prices[0.995]

        if p05 <= target_price <= p95:
            return "HIGH"
        if p005 <= target_price <= p995:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _worst_confidence(a: str, b: str) -> str:
        """Return the lower of two confidence labels."""
        rank = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
        names = {2: "HIGH", 1: "MEDIUM", 0: "LOW"}
        return names[min(rank[a], rank[b])]
