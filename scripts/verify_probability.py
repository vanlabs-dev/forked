"""Verify ProbabilityEngine interpolation logic and API integration.

Runs with synthetic data when no API key is configured, or with live data
when SYNTH_API_KEY is set.
"""

from __future__ import annotations

import json
import sys
from typing import Any
from unittest.mock import MagicMock

from backend.analysis.probability import ProbabilityEngine, PERCENTILE_LEVELS


# ── Synthetic percentile data (realistic BTC 24h forecast) ────────────

_CURRENT_PRICE = 88500.0

def _make_timepoint(seconds_ahead: int, spread_factor: float) -> dict[str, Any]:
    """Generate a realistic percentile spread that widens over time."""
    # Offsets as % of current price at maximum horizon.
    offsets = {
        "0.005": -0.065,
        "0.05":  -0.042,
        "0.2":   -0.020,
        "0.35":  -0.010,
        "0.5":    0.001,
        "0.65":   0.012,
        "0.8":    0.023,
        "0.95":   0.045,
        "0.995":  0.070,
    }
    return {k: _CURRENT_PRICE * (1.0 + v * spread_factor) for k, v in offsets.items()}


def _build_synthetic_response() -> dict[str, Any]:
    """Build a response matching the Synth API structure for 289 timepoints."""
    timepoints = []
    for i in range(289):
        spread = i / 288  # 0.0 at start → 1.0 at end
        timepoints.append(_make_timepoint(round(86400 * i / 288), spread))
    return {
        "current_price": _CURRENT_PRICE,
        "forecast_future": {"percentiles": timepoints},
    }


def _build_engine_with_synthetic() -> ProbabilityEngine:
    """Create a ProbabilityEngine backed by synthetic data."""
    mock_client = MagicMock()
    mock_client.get_prediction_percentiles.return_value = _build_synthetic_response()
    return ProbabilityEngine(mock_client)


def _build_engine_live() -> ProbabilityEngine | None:
    """Try to create a live ProbabilityEngine. Returns None if no API key."""
    from backend.config import SYNTH_API_KEY
    from backend.synth_client import SynthClient

    if not SYNTH_API_KEY:
        return None
    try:
        client = SynthClient(SYNTH_API_KEY)
        # Quick connectivity check.
        client.get_prediction_percentiles(asset="BTC", horizon="24h")
        return ProbabilityEngine(client)
    except Exception as exc:
        print(f"  Live API unavailable: {exc}")
        return None


# ── Test functions ────────────────────────────────────────────────────

def test_data_fetch(engine: ProbabilityEngine, label: str) -> dict[str, Any]:
    """Fetch percentile data and print summary."""
    print(f"\n{'='*60}")
    print(f"  {label}: Percentile Data (BTC 24h)")
    print(f"{'='*60}")

    data = engine.get_percentile_data("BTC", "24h")
    print(f"  Asset:         {data['asset']}")
    print(f"  Horizon:       {data['horizon']}")
    print(f"  Current price: ${data['current_price']:,.2f}")
    print(f"  Timepoints:    {len(data['timepoints'])}")

    final = data["timepoints"][-1]
    print(f"\n  Final timepoint ({final['seconds_ahead']}s = {final['seconds_ahead']/3600:.1f}h):")
    for level in PERCENTILE_LEVELS:
        price = final["prices"][level]
        pct_move = (price / data["current_price"] - 1) * 100
        print(f"    P{level*100:5.1f}: ${price:>12,.2f}  ({pct_move:+.2f}%)")

    return data


def test_probabilities(engine: ProbabilityEngine, label: str) -> None:
    """Test probability_above, probability_below, probability_between."""
    data = engine.get_percentile_data("BTC", "24h")
    cp = data["current_price"]

    print(f"\n{'='*60}")
    print(f"  {label}: Probability Queries")
    print(f"{'='*60}")

    # probability_above at +2%
    target_up = round(cp * 1.02, 2)
    res = engine.probability_above("BTC", target_up)
    print(f"\n  P(BTC > ${target_up:,.2f}) [+2%]:")
    print(f"    Probability: {res['probability']:.4f} ({res['probability']*100:.1f}%)")
    print(f"    Confidence:  {res['confidence']}")

    # probability_below at -2%
    target_down = round(cp * 0.98, 2)
    res = engine.probability_below("BTC", target_down)
    print(f"\n  P(BTC < ${target_down:,.2f}) [-2%]:")
    print(f"    Probability: {res['probability']:.4f} ({res['probability']*100:.1f}%)")
    print(f"    Confidence:  {res['confidence']}")

    # probability_between at ±5%
    lower = round(cp * 0.95, 2)
    upper = round(cp * 1.05, 2)
    res = engine.probability_between("BTC", lower, upper)
    print(f"\n  P(${lower:,.2f} < BTC < ${upper:,.2f}) [±5%]:")
    print(f"    Probability:           {res['probability']:.4f} ({res['probability']*100:.1f}%)")
    print(f"    P(below lower):        {res['probability_below_lower']:.4f}")
    print(f"    P(above upper):        {res['probability_above_upper']:.4f}")
    print(f"    Sum check:             {res['probability'] + res['probability_below_lower'] + res['probability_above_upper']:.4f} (should ~ 1.0)")
    print(f"    Confidence:            {res['confidence']}")


def test_cone(engine: ProbabilityEngine, label: str) -> None:
    """Test probability cone generation."""
    print(f"\n{'='*60}")
    print(f"  {label}: Probability Cone (BTC 24h, 50 points)")
    print(f"{'='*60}")

    cone = engine.probability_cone("BTC", "24h", num_points=50)
    print(f"  Asset:         {cone['asset']}")
    print(f"  Current price: ${cone['current_price']:,.2f}")
    print(f"  Points:        {len(cone['points'])}")

    print("\n  First 3 points:")
    for pt in cone["points"][:3]:
        print(f"    t={pt['hours_ahead']:6.2f}h  "
              f"P5=${pt['p05']:>10,.2f}  P50=${pt['p50']:>10,.2f}  P95=${pt['p95']:>10,.2f}  "
              f"spread={pt['p95']-pt['p05']:>8,.2f}")

    print("\n  Last 3 points:")
    for pt in cone["points"][-3:]:
        print(f"    t={pt['hours_ahead']:6.2f}h  "
              f"P5=${pt['p05']:>10,.2f}  P50=${pt['p50']:>10,.2f}  P95=${pt['p95']:>10,.2f}  "
              f"spread={pt['p95']-pt['p05']:>8,.2f}")


def test_monotonicity(engine: ProbabilityEngine, label: str) -> None:
    """Verify interpolation is monotonic: higher price → higher CDF."""
    print(f"\n{'='*60}")
    print(f"  {label}: Monotonicity Check")
    print(f"{'='*60}")

    data = engine.get_percentile_data("BTC", "24h")
    cp = data["current_price"]

    prices = [cp * (0.90 + i * 0.02) for i in range(11)]  # 90% to 110%
    prev_cdf = -1.0
    all_ok = True

    for p in prices:
        res = engine.probability_below("BTC", p)
        cdf = res["probability"]
        status = "OK" if cdf >= prev_cdf else "FAIL"
        if cdf < prev_cdf:
            all_ok = False
        pct = (p / cp - 1) * 100
        print(f"    ${p:>10,.2f} ({pct:+5.1f}%): CDF={cdf:.4f}  [{status}]")
        prev_cdf = cdf

    print(f"\n  Monotonicity: {'PASS' if all_ok else 'FAIL'}")


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    print("ProbabilityEngine Verification")
    print("=" * 60)

    # Try live first, fall back to synthetic.
    print("\nChecking for live API...")
    live = _build_engine_live()

    engines: list[tuple[str, ProbabilityEngine]] = []
    if live:
        print("  Live API connected!")
        engines.append(("LIVE", live))
    else:
        print("  No API key — using synthetic data")

    engines.append(("SYNTHETIC", _build_engine_with_synthetic()))

    for label, engine in engines:
        test_data_fetch(engine, label)
        test_probabilities(engine, label)
        test_cone(engine, label)
        test_monotonicity(engine, label)

    print(f"\n{'='*60}")
    print("  Verification complete.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
