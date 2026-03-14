"""Synth Prediction Accuracy Report — Calibration analysis using AlphaLog data.

Loads historical snapshots from Supabase (or local JSON fallback), pairs each
24h forecast with the actual price 24 hours later, and checks whether the
predicted percentile bands are well-calibrated.

Usage (run from VPS where data lives):
    python scripts/accuracy_report.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ── Percentile levels Synth provides ─────────────────────────────────────────
PERCENTILE_LEVELS: list[float] = [0.005, 0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95, 0.995]

# Assets to analyse (crypto have 1h+24h; we only use 24h here)
ANALYSIS_ASSETS: list[str] = ["BTC", "ETH", "SOL"]

# How close (in hours) a "24h later" snapshot can be to count as a match
MATCH_WINDOW_HOURS: float = 2.0


# ── Data loading ─────────────────────────────────────────────────────────────

def load_from_supabase() -> list[dict[str, Any]]:
    """Fetch all snapshots from Supabase, ordered by timestamp."""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")

    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY not set")

    from supabase import create_client

    client = create_client(url, key)

    rows: list[dict[str, Any]] = []
    page_size = 1000
    offset = 0

    while True:
        resp = (
            client.table("alphalog_snapshots")
            .select("timestamp, data")
            .order("timestamp", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    return rows


def load_from_local(base_dir: str = "data/snapshots") -> list[dict[str, Any]]:
    """Load all snapshot JSON files from local filesystem."""
    base = Path(base_dir)
    if not base.exists():
        raise RuntimeError(f"Local snapshot directory not found: {base}")

    rows: list[dict[str, Any]] = []
    for json_file in sorted(base.rglob("*_snapshot.json")):
        with open(json_file, encoding="utf-8") as f:
            snapshot = json.load(f)
        rows.append({"timestamp": snapshot["timestamp"], "data": snapshot})

    return rows


def load_snapshots() -> list[dict[str, Any]]:
    """Try Supabase first, fall back to local JSON files."""
    try:
        rows = load_from_supabase()
        if rows:
            print(f"Loaded {len(rows)} snapshots from Supabase")
            return rows
    except Exception as exc:
        print(f"Supabase unavailable ({exc}), trying local files...")

    rows = load_from_local()
    print(f"Loaded {len(rows)} snapshots from local files")
    return rows


# ── Snapshot parsing ─────────────────────────────────────────────────────────

def parse_timestamp(ts: str) -> datetime:
    """Parse ISO timestamp, handling both offset-aware and naive formats."""
    ts = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def extract_forecast(
    snapshot_data: dict[str, Any],
    asset: str,
) -> dict[str, Any] | None:
    """Extract current price and final-timepoint percentile prices for 24h horizon.

    Returns dict with keys: current_price, percentiles (dict level -> price).
    """
    assets = snapshot_data.get("assets", {})
    asset_data = assets.get(asset)
    if not asset_data:
        return None

    current_price = asset_data.get("current_price")
    if current_price is None:
        return None

    pct_data = asset_data.get("percentiles_24h", {})
    if not pct_data:
        return None

    # Synth response: {"current_price": float, "forecast_future": {"percentiles": [...]}}
    forecast = pct_data.get("forecast_future", {})
    percentiles_list = forecast.get("percentiles", [])

    if not percentiles_list:
        return None

    # Take the FINAL timepoint (end of 24h horizon)
    final_tp = percentiles_list[-1]

    percentiles: dict[float, float] = {}
    for level in PERCENTILE_LEVELS:
        key = str(level)
        if key in final_tp:
            percentiles[level] = float(final_tp[key])

    if not percentiles:
        return None

    return {"current_price": float(current_price), "percentiles": percentiles}


# ── Pairing forecasts with outcomes ──────────────────────────────────────────

def find_outcome_price(
    target_time: datetime,
    snapshots_by_time: list[tuple[datetime, dict[str, Any]]],
    asset: str,
) -> float | None:
    """Find the actual price of `asset` at the snapshot closest to `target_time`."""
    best_dt: datetime | None = None
    best_price: float | None = None
    max_delta = timedelta(hours=MATCH_WINDOW_HOURS)

    for ts, data in snapshots_by_time:
        delta = abs(ts - target_time)
        if delta > max_delta:
            if ts > target_time + max_delta:
                break  # sorted, no point continuing
            continue

        asset_data = data.get("assets", {}).get(asset)
        if not asset_data:
            continue

        price = asset_data.get("current_price")
        if price is None:
            continue

        if best_dt is None or delta < abs(best_dt - target_time):
            best_dt = ts
            best_price = float(price)

    return best_price


def build_pairs(
    rows: list[dict[str, Any]],
    asset: str,
) -> list[dict[str, Any]]:
    """Build forecast-outcome pairs for a single asset.

    Each pair: {timestamp, current_price, percentiles, actual_price, outcome_time}
    """
    # Pre-parse all timestamps and data
    parsed: list[tuple[datetime, dict[str, Any]]] = []
    for row in rows:
        ts = parse_timestamp(row["timestamp"])
        data = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
        parsed.append((ts, data))

    parsed.sort(key=lambda x: x[0])

    pairs: list[dict[str, Any]] = []
    for ts, data in parsed:
        forecast = extract_forecast(data, asset)
        if forecast is None:
            continue

        target_time = ts + timedelta(hours=24)
        actual_price = find_outcome_price(target_time, parsed, asset)
        if actual_price is None:
            continue

        pairs.append({
            "timestamp": ts.isoformat(),
            "current_price": forecast["current_price"],
            "percentiles": forecast["percentiles"],
            "actual_price": actual_price,
        })

    return pairs


# ── Calibration analysis ─────────────────────────────────────────────────────

def compute_calibration(
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute calibration statistics from forecast-outcome pairs."""
    n = len(pairs)
    if n == 0:
        return {"n": 0, "levels": {}, "bands": {}, "mae_pct": None}

    # For each percentile level, count how often actual < predicted
    below_counts: dict[float, int] = {level: 0 for level in PERCENTILE_LEVELS}

    p50_errors: list[float] = []

    for pair in pairs:
        actual = pair["actual_price"]
        pcts = pair["percentiles"]

        for level in PERCENTILE_LEVELS:
            if level in pcts and actual < pcts[level]:
                below_counts[level] += 1

        # P50 forecast error
        if 0.5 in pcts:
            p50 = pcts[0.5]
            error_pct = abs(actual - p50) / pair["current_price"] * 100
            p50_errors.append(error_pct)

    # Calibration per level
    levels: dict[str, dict[str, float]] = {}
    for level in PERCENTILE_LEVELS:
        expected = level * 100
        actual_pct = below_counts[level] / n * 100
        levels[f"P{level*100:g}"] = {
            "expected_pct": round(expected, 1),
            "actual_pct": round(actual_pct, 1),
            "deviation": round(actual_pct - expected, 1),
        }

    # Band containment
    bands: dict[str, dict[str, float]] = {}
    for label, lo_level, hi_level, expected in [
        ("P5-P95", 0.05, 0.95, 90.0),
        ("P20-P80", 0.2, 0.8, 60.0),
        ("P0.5-P99.5", 0.005, 0.995, 99.0),
    ]:
        inside = 0
        for pair in pairs:
            pcts = pair["percentiles"]
            if lo_level in pcts and hi_level in pcts:
                if pcts[lo_level] <= pair["actual_price"] <= pcts[hi_level]:
                    inside += 1
        actual_pct = inside / n * 100
        bands[label] = {
            "expected_pct": expected,
            "actual_pct": round(actual_pct, 1),
            "deviation": round(actual_pct - expected, 1),
        }

    # MAE
    mae_pct = sum(p50_errors) / len(p50_errors) if p50_errors else None
    median_error = sorted(p50_errors)[len(p50_errors) // 2] if p50_errors else None

    return {
        "n": n,
        "levels": levels,
        "bands": bands,
        "mae_pct": round(mae_pct, 3) if mae_pct is not None else None,
        "median_error_pct": round(median_error, 3) if median_error is not None else None,
    }


# ── Report output ────────────────────────────────────────────────────────────

def calibration_symbol(deviation: float) -> str:
    """Return a calibration quality symbol."""
    abs_dev = abs(deviation)
    if abs_dev <= 5.0:
        return "✓"
    if abs_dev <= 10.0:
        return "~"
    return "✗"


def print_report(results: dict[str, dict[str, Any]]) -> None:
    """Print a formatted calibration report to terminal."""
    total_pairs = sum(r["n"] for r in results.values())

    print()
    print("=" * 72)
    print("  SYNTH PREDICTION ACCURACY REPORT")
    print("  Calibration analysis from AlphaLog historical data")
    print("=" * 72)

    for asset, cal in results.items():
        n = cal["n"]
        if n == 0:
            print(f"\n  {asset}: No forecast-outcome pairs found\n")
            continue

        print(f"\n  {asset} — {n} forecast-outcome pairs")
        print("-" * 72)

        # Calibration table
        print(f"  {'Percentile':<12} {'Expected %':<12} {'Actual %':<12} {'Dev':<8} {'Cal'}")
        print(f"  {'─'*12} {'─'*12} {'─'*12} {'─'*8} {'─'*3}")

        for label, data in cal["levels"].items():
            sym = calibration_symbol(data["deviation"])
            dev_str = f"{data['deviation']:+.1f}pp"
            print(f"  {label:<12} {data['expected_pct']:<12.1f} {data['actual_pct']:<12.1f} {dev_str:<8} {sym}")

        # Band containment
        print()
        print(f"  {'Band':<12} {'Expected':<12} {'Actual':<12} {'Dev':<8} {'Cal'}")
        print(f"  {'─'*12} {'─'*12} {'─'*12} {'─'*8} {'─'*3}")

        for label, data in cal["bands"].items():
            sym = calibration_symbol(data["deviation"])
            dev_str = f"{data['deviation']:+.1f}pp"
            print(f"  {label:<12} {data['expected_pct']:<12.1f} {data['actual_pct']:<12.1f} {dev_str:<8} {sym}")

        # Forecast error
        if cal["mae_pct"] is not None:
            print()
            print(f"  P50 Mean Absolute Error:   {cal['mae_pct']:.2f}% of price")
            print(f"  P50 Median Absolute Error: {cal['median_error_pct']:.2f}% of price")

    print()
    print("=" * 72)
    print(f"  Total forecast-outcome pairs analysed: {total_pairs}")
    print(f"  Assets: {', '.join(results.keys())}")
    print()
    print("  Legend: ✓ within 5pp | ~ within 10pp | ✗ >10pp deviation")
    print("=" * 72)
    print()


def generate_chart(results: dict[str, dict[str, Any]], output_dir: Path) -> None:
    """Generate calibration chart (predicted percentile vs observed frequency)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed — skipping chart generation")
        return

    fig, ax = plt.subplots(figsize=(8, 6))

    # Diagonal (perfect calibration)
    ax.plot([0, 100], [0, 100], "k--", alpha=0.4, linewidth=1, label="Perfect calibration")

    colors = {"BTC": "#F7931A", "ETH": "#627EEA", "SOL": "#9945FF"}

    for asset, cal in results.items():
        if cal["n"] == 0:
            continue

        xs: list[float] = []
        ys: list[float] = []

        for data in cal["levels"].values():
            xs.append(data["expected_pct"])
            ys.append(data["actual_pct"])

        color = colors.get(asset, "#888888")
        ax.plot(xs, ys, "o-", color=color, linewidth=2, markersize=6, label=f"{asset} (n={cal['n']})")

    ax.set_xlabel("Predicted Percentile (%)", fontsize=11)
    ax.set_ylabel("Observed Frequency Below (%)", fontsize=11)
    ax.set_title("Synth Forecast Calibration — AlphaLog 24h Horizon", fontsize=13)
    ax.legend(loc="upper left", fontsize=10)
    ax.set_xlim(-2, 102)
    ax.set_ylim(-2, 102)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2)

    chart_path = output_dir / "calibration_chart.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Chart saved: {chart_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    rows = load_snapshots()
    if not rows:
        print("No snapshots found. Nothing to analyse.")
        sys.exit(1)

    # Date range
    timestamps = [parse_timestamp(r["timestamp"]) for r in rows]
    date_min = min(timestamps).strftime("%Y-%m-%d %H:%M")
    date_max = max(timestamps).strftime("%Y-%m-%d %H:%M")
    print(f"Date range: {date_min} → {date_max}")

    # Build pairs and compute calibration per asset
    results: dict[str, dict[str, Any]] = {}
    for asset in ANALYSIS_ASSETS:
        print(f"Processing {asset}...")
        pairs = build_pairs(rows, asset)
        results[asset] = compute_calibration(pairs)

    # Print report
    print_report(results)

    # Save JSON
    output_dir = Path("data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "accuracy_report.json"

    export = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_count": len(rows),
        "date_range": {"start": date_min, "end": date_max},
        "assets": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2)
    print(f"  Results saved: {output_path}")

    # Generate chart
    generate_chart(results, output_dir)


if __name__ == "__main__":
    main()
