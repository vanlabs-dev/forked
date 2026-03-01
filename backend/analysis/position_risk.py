"""PositionRiskAnalyzer — Maps trader positions onto Synth probability
forecasts to compute liquidation risk, take-profit probability, and
P&L distribution.

Layers position math on top of the ProbabilityEngine's percentile
interpolation to answer questions like "What's the chance my 20x BTC
long gets liquidated in the next 24 hours?"
"""

from __future__ import annotations

import math
from typing import Any

from backend.analysis.probability import PERCENTILE_LEVELS, ProbabilityEngine

# Weights for each percentile level, representing the probability mass
# around that level (midpoint-boundary method).  Sums to 1.0.
_PERCENTILE_WEIGHTS: dict[float, float] = {
    0.005: 0.0275,
    0.05:  0.0975,
    0.2:   0.15,
    0.35:  0.15,
    0.5:   0.15,
    0.65:  0.15,
    0.8:   0.15,
    0.95:  0.0975,
    0.995: 0.0275,
}

# Friendly display names for the 9 percentile levels.
_PERCENTILE_DISPLAY: dict[float, str] = {
    0.005: "p005", 0.05: "p05", 0.2: "p20", 0.35: "p35", 0.5: "p50",
    0.65: "p65", 0.8: "p80", 0.95: "p95", 0.995: "p995",
}


def _liquidation_risk_label(probability: float) -> str:
    """Classify liquidation risk based on probability."""
    if probability < 0.02:
        return "LOW"
    if probability < 0.10:
        return "MEDIUM"
    if probability < 0.25:
        return "HIGH"
    return "CRITICAL"


class PositionRiskAnalyzer:
    """Analyzes risk for leveraged trading positions using Synth
    probability forecasts."""

    def __init__(self, probability_engine: ProbabilityEngine) -> None:
        self._engine = probability_engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def compute_liquidation_price(
        entry_price: float,
        leverage: float,
        direction: str,
        maintenance_margin: float = 0.005,
    ) -> float:
        """Calculate the liquidation price for a leveraged position.

        LONG:  entry * (1 - 1/leverage + maintenance_margin)
        SHORT: entry * (1 + 1/leverage - maintenance_margin)
        """
        if direction.upper() == "LONG":
            return entry_price * (1.0 - 1.0 / leverage + maintenance_margin)
        return entry_price * (1.0 + 1.0 / leverage - maintenance_margin)

    def analyze_position(
        self,
        asset: str,
        entry_price: float,
        leverage: float,
        direction: str,
        take_profit: float | None = None,
        stop_loss: float | None = None,
        horizon: str = "24h",
    ) -> dict[str, Any]:
        """Full risk analysis for a leveraged position.

        Fetches Synth percentile data once, then computes liquidation
        probability, TP/SL probabilities, P&L distribution, probability
        cone with level overlays, and a composite risk score.
        """
        direction = direction.upper()
        data = self._engine.get_percentile_data(asset, horizon)
        current_price = data["current_price"]
        final_tp = data["timepoints"][-1]
        prices = final_tp["prices"]

        # ── Liquidation ──────────────────────────────────────────────
        liq_price = self.compute_liquidation_price(
            entry_price, leverage, direction,
        )
        liq_cdf = self._engine._interpolate_probability(liq_price, prices)

        if direction == "LONG":
            liq_prob = liq_cdf  # liquidated if price drops below liq
        else:
            liq_prob = 1.0 - liq_cdf  # liquidated if price rises above liq

        liq_distance_pct = (liq_price / entry_price - 1.0) * 100.0
        liq_risk = _liquidation_risk_label(liq_prob)

        liquidation = {
            "price": round(liq_price, 2),
            "probability": round(liq_prob, 4),
            "distance_pct": round(liq_distance_pct, 2),
            "risk_level": liq_risk,
        }

        # ── Take-profit ──────────────────────────────────────────────
        tp_result: dict[str, Any] | None = None
        if take_profit is not None:
            tp_cdf = self._engine._interpolate_probability(take_profit, prices)
            if direction == "LONG":
                tp_prob = 1.0 - tp_cdf  # TP hit if price rises above target
            else:
                tp_prob = tp_cdf  # TP hit if price drops below target
            tp_result = {
                "price": take_profit,
                "probability": round(tp_prob, 4),
                "distance_pct": round((take_profit / entry_price - 1.0) * 100.0, 2),
            }

        # ── Stop-loss ────────────────────────────────────────────────
        sl_result: dict[str, Any] | None = None
        if stop_loss is not None:
            sl_cdf = self._engine._interpolate_probability(stop_loss, prices)
            if direction == "LONG":
                sl_prob = sl_cdf  # SL hit if price drops below target
            else:
                sl_prob = 1.0 - sl_cdf  # SL hit if price rises above target
            sl_result = {
                "price": stop_loss,
                "probability": round(sl_prob, 4),
                "distance_pct": round((stop_loss / entry_price - 1.0) * 100.0, 2),
            }

        # ── P&L distribution ─────────────────────────────────────────
        pnl_dist = self._build_pnl_distribution(
            entry_price, leverage, direction, liq_price, prices, current_price,
        )

        # ── Cone with levels ─────────────────────────────────────────
        cone = self._build_cone_from_data(data, num_points=50)
        cone_with_levels = {
            "cone": cone,
            "liquidation_line": round(liq_price, 2),
            "take_profit_line": take_profit,
            "stop_loss_line": stop_loss,
        }

        # ── Risk score ───────────────────────────────────────────────
        risk_score = self._compute_risk_score(
            liq_prob, leverage, pnl_dist["probability_profitable"], direction,
        )

        return {
            "asset": asset,
            "direction": direction,
            "entry_price": entry_price,
            "leverage": leverage,
            "horizon": horizon,
            "current_price": current_price,
            "liquidation": liquidation,
            "take_profit": tp_result,
            "stop_loss": sl_result,
            "pnl_distribution": pnl_dist,
            "cone_with_levels": cone_with_levels,
            "risk_score": risk_score,
        }

    # ------------------------------------------------------------------
    # P&L helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_pnl_pct(
        entry_price: float,
        current_price: float,
        leverage: float,
        direction: str,
    ) -> float:
        """Compute P&L percentage for a leveraged position.

        Capped at -100% (total loss / liquidation).
        """
        if direction == "LONG":
            raw = ((current_price - entry_price) / entry_price) * leverage * 100.0
        else:
            raw = ((entry_price - current_price) / entry_price) * leverage * 100.0
        return max(raw, -100.0)

    def _build_pnl_distribution(
        self,
        entry_price: float,
        leverage: float,
        direction: str,
        liq_price: float,
        percentile_prices: dict[float, float],
        current_price: float,
    ) -> dict[str, Any]:
        """Build the P&L distribution across all 9 percentile levels."""
        percentiles: dict[str, dict[str, Any]] = {}
        weighted_pnl = 0.0

        for level in PERCENTILE_LEVELS:
            price = percentile_prices[level]
            pnl = self._compute_pnl_pct(entry_price, price, leverage, direction)

            is_liquidated = (
                (direction == "LONG" and price <= liq_price)
                or (direction == "SHORT" and price >= liq_price)
            )
            if is_liquidated:
                pnl = -100.0

            entry: dict[str, Any] = {
                "price": round(price, 2),
                "pnl_pct": round(pnl, 1),
            }
            if is_liquidated:
                entry["pnl_note"] = "LIQUIDATED"

            percentiles[_PERCENTILE_DISPLAY[level]] = entry
            weighted_pnl += pnl * _PERCENTILE_WEIGHTS[level]

        # Probability of profit: P(price > entry) for long, P(price < entry) for short.
        entry_cdf = self._engine._interpolate_probability(
            entry_price, percentile_prices,
        )
        if direction == "LONG":
            prob_profit = 1.0 - entry_cdf
        else:
            prob_profit = entry_cdf

        return {
            "percentiles": percentiles,
            "expected_pnl_pct": round(weighted_pnl, 1),
            "probability_profitable": round(prob_profit, 4),
        }

    # ------------------------------------------------------------------
    # Cone builder (reuses already-fetched data)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_cone_from_data(
        data: dict[str, Any],
        num_points: int = 50,
    ) -> list[dict[str, Any]]:
        """Build probability cone points from already-fetched percentile data."""
        all_tp = data["timepoints"]
        n = len(all_tp)

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

        return points

    # ------------------------------------------------------------------
    # Risk score
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_risk_score(
        liq_probability: float,
        leverage: float,
        probability_profitable: float,
        direction: str,
    ) -> dict[str, Any]:
        """Compute a composite 0-100 risk score.

        Weighted factors:
          - Liquidation probability (40%): 0-30% liq prob maps to 0-100
          - Leverage intensity   (30%): 1x-100x on log scale maps to 0-100
          - Loss probability     (30%): mapped linearly to 0-100
        """
        # Liquidation component: 0-30% probability → 0-100 score.
        liq_score = min(liq_probability / 0.30, 1.0) * 100.0

        # Leverage component: log scale, 1x → 0, 100x → 100.
        if leverage <= 1.0:
            lev_score = 0.0
        else:
            lev_score = min(math.log(leverage) / math.log(100), 1.0) * 100.0

        # Loss probability component.
        loss_prob = 1.0 - probability_profitable
        loss_score = loss_prob * 100.0

        composite = liq_score * 0.40 + lev_score * 0.30 + loss_score * 0.30
        score = round(min(max(composite, 0.0), 100.0))

        if score < 25:
            label = "LOW"
        elif score < 50:
            label = "MODERATE"
        elif score < 75:
            label = "HIGH"
        else:
            label = "CRITICAL"

        # Human-readable factors.
        factors: list[str] = []
        factors.append(f"Leverage {leverage:.0f}x amplifies moves by {leverage:.0f}x")
        factors.append(
            f"Liquidation probability {liq_probability * 100:.1f}% in horizon"
        )
        factors.append(
            f"{probability_profitable * 100:.0f}% chance of profit"
        )

        return {"score": score, "label": label, "factors": factors}
