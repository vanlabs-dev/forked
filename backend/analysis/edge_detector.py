"""Edge detection between Synth distribution signals and Polymarket pricing.

Identifies mispricings where Synth's probabilistic forecasts diverge
from Polymarket's market-implied probabilities.
"""

from __future__ import annotations

from backend.config import (
    ASSETS,
    POLYMARKET_DAILY_ASSETS,
    POLYMARKET_SHORT_TERM_ASSETS,
)

# Thresholds
PROB_EDGE_THRESHOLD = 0.05
TAIL_RISK_THRESHOLD = 0.50
DISPERSION_THRESHOLD = 0.20
CONFIDENT_MARKET_THRESHOLD = 0.60
VERY_CONFIDENT_MARKET_THRESHOLD = 0.65
BULLISH_SKEW_THRESHOLD = 1.50
BEARISH_SKEW_THRESHOLD = 0.67


class EdgeDetector:
    """Detects mispricings between Synth distribution signals and Polymarket."""

    def detect_edges(
        self,
        snapshot: dict,
        distribution_metrics: dict,
    ) -> list[dict]:
        """Find all edges across assets.

        Args:
            snapshot: Raw AlphaLog snapshot.
            distribution_metrics: Output from DistributionAnalyzer.analyze_snapshot().

        Returns:
            List of detected edge dicts, sorted by confidence.
        """
        edges: list[dict] = []
        assets_data = snapshot.get("assets", {})

        for asset in ASSETS:
            asset_data = assets_data.get(asset)
            if not asset_data:
                continue

            # Get 24h metrics (primary horizon for edge detection)
            metrics = distribution_metrics.get(f"{asset}_24h")

            # Check each Polymarket timeframe
            for timeframe, pm_key in [
                ("daily", "polymarket_daily"),
                ("hourly", "polymarket_hourly"),
            ]:
                pm_data = asset_data.get(pm_key)
                if not pm_data:
                    continue

                synth_up = pm_data.get("synth_probability_up")
                pm_up = pm_data.get("polymarket_probability_up")
                if synth_up is None or pm_up is None:
                    continue

                # 1. Simple probability edge
                edge = self._check_probability_edge(asset, timeframe, synth_up, pm_up)
                if edge:
                    edges.append(edge)

                # Distribution-based edges require metrics
                if not metrics:
                    continue

                # 2. Tail risk underpriced
                edge = self._check_tail_risk_underpriced(asset, timeframe, metrics, pm_up)
                if edge:
                    edges.append(edge)

                # 3. Uncertainty underpriced
                edge = self._check_uncertainty_underpriced(asset, timeframe, metrics, pm_up)
                if edge:
                    edges.append(edge)

                # 4. Skew mismatch
                edge = self._check_skew_mismatch(asset, timeframe, metrics, pm_up)
                if edge:
                    edges.append(edge)

        # Sort by confidence: HIGH first, then MEDIUM, then LOW
        confidence_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        edges.sort(key=lambda e: confidence_order.get(e["confidence"], 3))
        return edges

    def _check_probability_edge(
        self,
        asset: str,
        timeframe: str,
        synth_up: float,
        pm_up: float,
    ) -> dict | None:
        """Detect simple probability divergence."""
        gap = synth_up - pm_up
        abs_gap = abs(gap)

        if abs_gap <= PROB_EDGE_THRESHOLD:
            return None

        direction = "UP" if gap > 0 else "DOWN"
        confidence = "HIGH" if abs_gap > PROB_EDGE_THRESHOLD * 2 else "MEDIUM"

        return {
            "asset": asset,
            "edge_type": "probability_divergence",
            "timeframe": timeframe,
            "direction": direction,
            "confidence": confidence,
            "synth_signal": {
                "synth_probability_up": round(synth_up, 4),
                "gap": round(gap, 4),
            },
            "polymarket_price": {"probability_up": round(pm_up, 4)},
            "description": (
                f"Synth prices {asset} Up at {synth_up:.1%} vs "
                f"Polymarket {pm_up:.1%} ({timeframe}, gap {abs_gap:.1%})"
            ),
        }

    def _check_tail_risk_underpriced(
        self,
        asset: str,
        timeframe: str,
        metrics: dict,
        pm_up: float,
    ) -> dict | None:
        """Detect heavy tails not reflected in Polymarket's confident pricing."""
        upper_tail = metrics.get("upper_tail_risk", 0)
        lower_tail = metrics.get("lower_tail_risk", 0)
        width = metrics.get("forecast_width", 0)

        has_upper_tail = upper_tail > TAIL_RISK_THRESHOLD
        has_lower_tail = lower_tail > TAIL_RISK_THRESHOLD

        if not (has_upper_tail or has_lower_tail):
            return None

        # Polymarket must be pricing confidently in the opposite direction
        if has_lower_tail and pm_up > VERY_CONFIDENT_MARKET_THRESHOLD:
            direction = "DOWN_RISK"
            tail_val = lower_tail
        elif has_upper_tail and pm_up < (1 - VERY_CONFIDENT_MARKET_THRESHOLD):
            direction = "UP_RISK"
            tail_val = upper_tail
        else:
            return None

        strength = max(upper_tail, lower_tail) / TAIL_RISK_THRESHOLD
        confidence = "HIGH" if strength > 2.0 else "MEDIUM"

        return {
            "asset": asset,
            "edge_type": "tail_risk_underpriced",
            "timeframe": timeframe,
            "direction": direction,
            "confidence": confidence,
            "synth_signal": {
                "lower_tail_risk": round(lower_tail, 4),
                "upper_tail_risk": round(upper_tail, 4),
                "forecast_width": f"{width:.2%}",
            },
            "polymarket_price": {"probability_up": round(pm_up, 4)},
            "description": (
                f"Synth sees significant {direction.lower().replace('_', ' ')} "
                f"(tail={tail_val:.2f}) but Polymarket prices Up at {pm_up:.1%}"
            ),
        }

    def _check_uncertainty_underpriced(
        self,
        asset: str,
        timeframe: str,
        metrics: dict,
        pm_up: float,
    ) -> dict | None:
        """Detect dispersed distributions vs confident market pricing."""
        density = metrics.get("density_concentration", 1.0)

        if density >= DISPERSION_THRESHOLD:
            return None

        # Market must be pricing one side confidently
        market_confidence = max(pm_up, 1 - pm_up)
        if market_confidence <= CONFIDENT_MARKET_THRESHOLD:
            return None

        direction = "UP" if pm_up > 0.5 else "DOWN"
        confidence = "HIGH" if density < 0.15 and market_confidence > 0.70 else "MEDIUM"

        return {
            "asset": asset,
            "edge_type": "uncertainty_underpriced",
            "timeframe": timeframe,
            "direction": f"AGAINST_{direction}",
            "confidence": confidence,
            "synth_signal": {
                "density_concentration": round(density, 4),
                "forecast_width": f"{metrics.get('forecast_width', 0):.2%}",
            },
            "polymarket_price": {"probability_up": round(pm_up, 4)},
            "description": (
                f"Synth shows dispersed distribution (density={density:.2f}) "
                f"but Polymarket confidently prices {direction} at {market_confidence:.1%}"
            ),
        }

    def _check_skew_mismatch(
        self,
        asset: str,
        timeframe: str,
        metrics: dict,
        pm_up: float,
    ) -> dict | None:
        """Detect skew direction contradicting Polymarket pricing."""
        asymmetry = metrics.get("tail_asymmetry", 1.0)

        bullish_skew = asymmetry > BULLISH_SKEW_THRESHOLD
        bearish_skew = asymmetry < BEARISH_SKEW_THRESHOLD

        if not (bullish_skew or bearish_skew):
            return None

        # Skew must contradict Polymarket's direction
        if bullish_skew and pm_up >= 0.50:
            return None  # Both agree on Up
        if bearish_skew and pm_up <= 0.50:
            return None  # Both agree on Down

        if bullish_skew:
            direction = "SKEW_BULLISH"
            desc = (
                f"Synth shows bullish skew (asymmetry={asymmetry:.2f}) "
                f"but Polymarket prices Down at {1 - pm_up:.1%}"
            )
        else:
            direction = "SKEW_BEARISH"
            desc = (
                f"Synth shows bearish skew (asymmetry={asymmetry:.2f}) "
                f"but Polymarket prices Up at {pm_up:.1%}"
            )

        strength = abs(asymmetry - 1.0) / (BULLISH_SKEW_THRESHOLD - 1.0)
        confidence = "HIGH" if strength > 2.0 else "MEDIUM" if strength > 1.0 else "LOW"

        return {
            "asset": asset,
            "edge_type": "skew_mismatch",
            "timeframe": timeframe,
            "direction": direction,
            "confidence": confidence,
            "synth_signal": {
                "tail_asymmetry": round(asymmetry, 4),
                "directional_bias": round(metrics.get("directional_bias", 0), 6),
            },
            "polymarket_price": {"probability_up": round(pm_up, 4)},
            "description": desc,
        }
