"""Verify PositionRiskAnalyzer — tests liquidation math, P&L distribution,
risk scoring, and direction handling for LONG/SHORT positions.

Uses synthetic Synth data (no API key required).
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from backend.analysis.position_risk import PositionRiskAnalyzer
from backend.analysis.probability import ProbabilityEngine


# ── Synthetic data builders ───────────────────────────────────────────

_ASSET_CONFIGS: dict[str, dict[str, Any]] = {
    "BTC": {"price": 88500.0, "spread": 0.065},
    "ETH": {"price": 3200.0, "spread": 0.080},
    "SOL": {"price": 145.0, "spread": 0.095},
}

_OFFSETS_SHAPE: dict[str, float] = {
    "0.005": -1.00,
    "0.05":  -0.646,
    "0.2":   -0.308,
    "0.35":  -0.154,
    "0.5":    0.015,
    "0.65":   0.185,
    "0.8":    0.354,
    "0.95":   0.692,
    "0.995":  1.077,
}


def _make_response(asset: str, horizon: str) -> dict[str, Any]:
    """Build a synthetic Synth API response for the given asset."""
    cfg = _ASSET_CONFIGS[asset]
    base = cfg["price"]
    max_spread = cfg["spread"]

    n = 289
    total_sec = 3600 if horizon == "1h" else 86400
    timepoints = []

    for i in range(n):
        factor = i / (n - 1)  # 0 at start, 1 at end
        tp = {}
        for key, shape in _OFFSETS_SHAPE.items():
            tp[key] = base * (1.0 + shape * max_spread * factor)
        timepoints.append(tp)

    return {"current_price": base, "forecast_future": {"percentiles": timepoints}}


def _build_analyzer() -> tuple[PositionRiskAnalyzer, ProbabilityEngine]:
    """Build a PositionRiskAnalyzer backed by synthetic data for BTC/ETH/SOL."""
    mock_client = MagicMock()

    def mock_percentiles(asset: str = "BTC", horizon: str = "24h", **kwargs: Any) -> dict[str, Any]:
        return _make_response(asset, horizon)

    mock_client.get_prediction_percentiles.side_effect = mock_percentiles

    engine = ProbabilityEngine(mock_client)
    analyzer = PositionRiskAnalyzer(engine)
    return analyzer, engine


# ── Display helpers ───────────────────────────────────────────────────

def _print_section(title: str) -> None:
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")


def _print_analysis(result: dict[str, Any]) -> None:
    """Print analyze_position output in a readable format."""
    print(f"\n  {result['asset']} {result['direction']} @ ${result['entry_price']:,.2f}"
          f"  {result['leverage']:.0f}x  [{result['horizon']}]")
    print(f"  Current price: ${result['current_price']:,.2f}")

    # Liquidation
    liq = result["liquidation"]
    print(f"\n  Liquidation:")
    print(f"    Price:       ${liq['price']:,.2f}  ({liq['distance_pct']:+.2f}% from entry)")
    print(f"    Probability: {liq['probability']:.4f} ({liq['probability']*100:.1f}%)")
    print(f"    Risk level:  {liq['risk_level']}")

    # Take-profit
    if result["take_profit"]:
        tp = result["take_profit"]
        print(f"\n  Take-Profit:")
        print(f"    Price:       ${tp['price']:,.2f}  ({tp['distance_pct']:+.2f}%)")
        print(f"    Probability: {tp['probability']:.4f} ({tp['probability']*100:.1f}%)")

    # Stop-loss
    if result["stop_loss"]:
        sl = result["stop_loss"]
        print(f"\n  Stop-Loss:")
        print(f"    Price:       ${sl['price']:,.2f}  ({sl['distance_pct']:+.2f}%)")
        print(f"    Probability: {sl['probability']:.4f} ({sl['probability']*100:.1f}%)")

    # P&L distribution
    pnl = result["pnl_distribution"]
    print(f"\n  P&L Distribution:")
    for key, val in pnl["percentiles"].items():
        note = f"  ** {val['pnl_note']}" if "pnl_note" in val else ""
        print(f"    {key:>4}: ${val['price']:>10,.2f}  PnL: {val['pnl_pct']:>+8.1f}%{note}")
    print(f"    Expected PnL:        {pnl['expected_pnl_pct']:+.1f}%")
    print(f"    P(profitable):       {pnl['probability_profitable']:.4f} ({pnl['probability_profitable']*100:.1f}%)")

    # Risk score
    rs = result["risk_score"]
    print(f"\n  Risk Score: {rs['score']}/100 [{rs['label']}]")
    for f in rs["factors"]:
        print(f"    - {f}")

    # Cone summary
    cone = result["cone_with_levels"]
    print(f"\n  Cone: {len(cone['cone'])} points")
    print(f"    Liquidation line: ${cone['liquidation_line']:,.2f}")
    if cone["take_profit_line"]:
        print(f"    Take-profit line: ${cone['take_profit_line']:,.2f}")
    if cone["stop_loss_line"]:
        print(f"    Stop-loss line:   ${cone['stop_loss_line']:,.2f}")


# ── Test scenarios ────────────────────────────────────────────────────

def test_btc_long(analyzer: PositionRiskAnalyzer) -> None:
    """BTC LONG 20x with TP and SL."""
    _print_section("Test 1: BTC LONG 20x @ $88,500 | TP=$92,000 SL=$87,000")

    result = analyzer.analyze_position(
        asset="BTC", entry_price=88500.0, leverage=20.0,
        direction="LONG", take_profit=92000.0, stop_loss=87000.0,
        horizon="24h",
    )
    _print_analysis(result)

    # Verify liquidation math.
    expected_liq = 88500.0 * (1.0 - 1.0 / 20.0 + 0.005)
    actual_liq = result["liquidation"]["price"]
    match = abs(expected_liq - actual_liq) < 0.01
    print(f"\n  Liquidation math: expected=${expected_liq:,.2f}"
          f"  got=${actual_liq:,.2f}  [{'PASS' if match else 'FAIL'}]")

    # Verify P&L direction: higher percentiles should have higher PnL for a LONG.
    pnl_vals = [v["pnl_pct"] for v in result["pnl_distribution"]["percentiles"].values()]
    monotonic = all(a <= b for a, b in zip(pnl_vals, pnl_vals[1:]))
    print(f"  PnL monotonicity (higher percentile = more profit): [{'PASS' if monotonic else 'FAIL'}]")


def test_eth_short(analyzer: PositionRiskAnalyzer) -> None:
    """ETH SHORT 10x, no TP/SL."""
    _print_section("Test 2: ETH SHORT 10x @ $3,200 | No TP/SL")

    result = analyzer.analyze_position(
        asset="ETH", entry_price=3200.0, leverage=10.0,
        direction="SHORT", horizon="24h",
    )
    _print_analysis(result)

    # Verify liquidation is above entry for short.
    assert result["liquidation"]["price"] > 3200.0, "Short liq should be above entry"
    print(f"\n  Liq above entry (SHORT): [PASS]")

    # Verify P&L is inverted: higher percentiles should have LOWER PnL for SHORT.
    pnl_vals = [v["pnl_pct"] for v in result["pnl_distribution"]["percentiles"].values()]
    inverted = all(a >= b for a, b in zip(pnl_vals, pnl_vals[1:]))
    print(f"  PnL inverted (higher percentile = more loss for SHORT): [{'PASS' if inverted else 'FAIL'}]")


def test_sol_high_leverage(analyzer: PositionRiskAnalyzer) -> None:
    """SOL LONG 50x, 1h horizon — should show HIGH/CRITICAL risk."""
    _print_section("Test 3: SOL LONG 50x @ $145 | 1h horizon (high leverage)")

    result = analyzer.analyze_position(
        asset="SOL", entry_price=145.0, leverage=50.0,
        direction="LONG", horizon="1h",
    )
    _print_analysis(result)

    risk = result["risk_score"]
    high_risk = risk["label"] in ("HIGH", "CRITICAL")
    print(f"\n  Risk label is HIGH or CRITICAL: [{'PASS' if high_risk else 'FAIL: ' + risk['label']}]")


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    print("PositionRiskAnalyzer Verification")
    print("=" * 65)

    analyzer, _ = _build_analyzer()

    test_btc_long(analyzer)
    test_eth_short(analyzer)
    test_sol_high_leverage(analyzer)

    print(f"\n{'='*65}")
    print("  Verification complete.")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
