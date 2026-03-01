"""Historical trend analysis for AlphaLog data.

Tracks how Synth-Index scores, distribution shapes, and edge accuracy
evolve over time across all collected snapshots.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from pathlib import Path

from backend.analysis.distribution import DistributionAnalyzer
from backend.analysis.synth_index import SynthIndex

logger = logging.getLogger("alphalog.trends")

SNAPSHOTS_DIR = Path("data/snapshots")
EDGES_DIR = Path("data/edges")
EXPORTS_DIR = Path("data/exports")


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _linear_slope(values: list[float]) -> float:
    """Simple linear regression slope over indices 0..n-1."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den > 0 else 0.0


class TrendAnalyzer:
    """Analyzes historical trends in distribution metrics, Synth-Index, and edge performance."""

    def __init__(self, data_dir: str = "data/snapshots") -> None:
        self._data_dir = Path(data_dir)
        self._dist_analyzer = DistributionAnalyzer()
        self._synth_index = SynthIndex()

    def load_all_snapshots(self) -> list[tuple[str, dict]]:
        """Walk data/snapshots/ directory, load all JSON files, sort by timestamp.

        Returns:
            List of (timestamp, snapshot) tuples sorted chronologically.
        """
        if not self._data_dir.exists():
            return []

        results: list[tuple[str, dict]] = []
        for path in sorted(self._data_dir.glob("*/*_snapshot.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    snapshot = json.load(f)
                ts = snapshot.get("timestamp", "")
                if ts:
                    results.append((ts, snapshot))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Skipping malformed snapshot %s: %s", path, exc)

        results.sort(key=lambda x: x[0])
        return results

    def compute_history(self) -> dict:
        """Run DistributionAnalyzer and SynthIndex on every snapshot, build time series."""
        snapshots = self.load_all_snapshots()
        if not snapshots:
            return {
                "period": {"start": None, "end": None, "snapshots": 0, "hours_covered": 0},
                "synth_index_history": {},
                "distribution_history": {},
            }

        synth_index_history: dict[str, list[dict]] = {}
        distribution_history: dict[str, list[dict]] = {}

        for ts, snapshot in snapshots:
            metrics = self._dist_analyzer.analyze_snapshot(snapshot)
            index_data = self._synth_index.compute(metrics)

            for key, m in metrics.items():
                distribution_history.setdefault(key, []).append({
                    "timestamp": ts,
                    "bias": m["directional_bias"],
                    "width": m["forecast_width"],
                    "skew": m["tail_asymmetry"],
                    "tail_fatness": m["tail_fatness"],
                    "upper_tail": m["upper_tail_risk"],
                    "lower_tail": m["lower_tail_risk"],
                    "density": m["density_concentration"],
                    "regime": m["regime"],
                })

            for key, idx in index_data.items():
                synth_index_history.setdefault(key, []).append({
                    "timestamp": ts,
                    "value": idx["synth_index"],
                    "level": idx["level"],
                })

        start_ts = snapshots[0][0]
        end_ts = snapshots[-1][0]
        try:
            hours = (
                _parse_ts(end_ts) - _parse_ts(start_ts)
            ).total_seconds() / 3600
        except (ValueError, TypeError):
            hours = 0

        return {
            "period": {
                "start": start_ts,
                "end": end_ts,
                "snapshots": len(snapshots),
                "hours_covered": round(hours, 1),
            },
            "synth_index_history": synth_index_history,
            "distribution_history": distribution_history,
        }

    def compute_summary_stats(self, history: dict) -> list[dict]:
        """Summary statistics across the full time period for each asset-horizon."""
        si_history = history.get("synth_index_history", {})
        dist_history = history.get("distribution_history", {})
        summaries: list[dict] = []

        all_keys = set(si_history.keys()) | set(dist_history.keys())

        for key in sorted(all_keys):
            parts = key.split("_", 1)
            asset = parts[0] if parts else key
            horizon = parts[1] if len(parts) > 1 else ""

            summary: dict = {"asset": asset, "horizon": horizon}

            # Synth-Index stats
            si_points = si_history.get(key, [])
            if si_points:
                values = [p["value"] for p in si_points]
                current = values[-1]
                mean_val = sum(values) / len(values)
                rank = sum(1 for v in values if v <= current) / len(values) * 100

                summary["synth_index"] = {
                    "mean": round(mean_val, 1),
                    "min": round(min(values), 1),
                    "max": round(max(values), 1),
                    "std": round(
                        (sum((v - mean_val) ** 2 for v in values) / max(len(values) - 1, 1)) ** 0.5,
                        1,
                    ),
                    "current": round(current, 1),
                    "percentile_rank": round(rank),
                }

            # Distribution stats
            dist_points = dist_history.get(key, [])
            if dist_points:
                bias_vals = [p["bias"] for p in dist_points]
                width_vals = [p["width"] for p in dist_points]
                skew_vals = [p["skew"] for p in dist_points]
                regimes = [p["regime"] for p in dist_points]

                # Trend detection on last 12 points
                recent_bias = bias_vals[-12:]
                recent_width = width_vals[-12:]

                bias_slope = _linear_slope(recent_bias)
                width_slope = _linear_slope(recent_width)

                # Thresholds for trend classification
                bias_threshold = 0.0001
                width_threshold = 0.0005

                if bias_slope > bias_threshold:
                    bias_trend = "BULLISH_SHIFT"
                elif bias_slope < -bias_threshold:
                    bias_trend = "BEARISH_SHIFT"
                else:
                    bias_trend = "STABLE"

                if width_slope > width_threshold:
                    width_trend = "EXPANDING"
                elif width_slope < -width_threshold:
                    width_trend = "COMPRESSING"
                else:
                    width_trend = "STABLE"

                # Count skew flips (crossing 1.0)
                skew_flips = 0
                for i in range(1, len(skew_vals)):
                    if (skew_vals[i - 1] < 1.0 and skew_vals[i] >= 1.0) or \
                       (skew_vals[i - 1] >= 1.0 and skew_vals[i] < 1.0):
                        skew_flips += 1

                # Regime breakdown
                total_regimes = len(regimes)
                regime_counts: dict[str, int] = {}
                for r in regimes:
                    regime_counts[r] = regime_counts.get(r, 0) + 1
                regime_breakdown = {
                    r: f"{count / total_regimes:.0%}"
                    for r, count in sorted(regime_counts.items())
                }

                summary["bias"] = {
                    "mean": round(sum(bias_vals) / len(bias_vals), 6),
                    "min": round(min(bias_vals), 6),
                    "max": round(max(bias_vals), 6),
                    "trend": bias_trend,
                }
                summary["width"] = {
                    "mean": round(sum(width_vals) / len(width_vals), 6),
                    "min": round(min(width_vals), 6),
                    "max": round(max(width_vals), 6),
                    "trend": width_trend,
                }
                summary["skew"] = {
                    "mean": round(sum(skew_vals) / len(skew_vals), 4),
                    "flips": skew_flips,
                }
                summary["regime_breakdown"] = regime_breakdown

            summaries.append(summary)

        return summaries

    def edge_performance_over_time(self) -> dict:
        """Load resolved edges and compute rolling performance metrics."""
        resolved_path = EDGES_DIR / "resolved_edges.json"
        if not resolved_path.exists():
            return {"insufficient_data": True, "resolved": 0}

        try:
            with open(resolved_path, encoding="utf-8") as f:
                resolved = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"insufficient_data": True, "resolved": 0}

        if len(resolved) < 5:
            return {"insufficient_data": True, "resolved": len(resolved)}

        # Sort by resolved_at
        resolved.sort(key=lambda e: e.get("resolved_at", ""))

        total = len(resolved)
        correct = sum(1 for e in resolved if e.get("resolution") == "CORRECT")
        pnls = [e.get("pnl", 0.0) for e in resolved]
        total_pnl = sum(pnls)
        mean_pnl = total_pnl / total

        # Sharpe ratio
        if total > 1:
            std_pnl = (sum((p - mean_pnl) ** 2 for p in pnls) / (total - 1)) ** 0.5
            sharpe = (mean_pnl / std_pnl * math.sqrt(365 * 24)) if std_pnl > 0 else 0.0
        else:
            sharpe = 0.0

        # Rolling hit rate (window of 10)
        rolling_hit_rate: list[dict] = []
        window = 10
        for i in range(window - 1, total):
            chunk = resolved[i - window + 1: i + 1]
            hits = sum(1 for e in chunk if e.get("resolution") == "CORRECT")
            rolling_hit_rate.append({
                "timestamp": chunk[-1].get("resolved_at", ""),
                "hit_rate_last_10": round(hits / window, 4),
            })

        # Cumulative PnL
        cumulative_pnl: list[dict] = []
        running = 0.0
        for e in resolved:
            running += e.get("pnl", 0.0)
            cumulative_pnl.append({
                "timestamp": e.get("resolved_at", ""),
                "cumulative": round(running, 4),
            })

        # Best/worst 10-edge windows
        best_hr = 0.0
        worst_hr = 1.0
        best_window: dict = {}
        worst_window: dict = {}
        for i in range(window - 1, total):
            chunk = resolved[i - window + 1: i + 1]
            hits = sum(1 for e in chunk if e.get("resolution") == "CORRECT")
            hr = hits / window
            if hr >= best_hr:
                best_hr = hr
                best_window = {
                    "start": chunk[0].get("resolved_at", ""),
                    "end": chunk[-1].get("resolved_at", ""),
                    "hit_rate": round(hr, 4),
                }
            if hr <= worst_hr:
                worst_hr = hr
                worst_window = {
                    "start": chunk[0].get("resolved_at", ""),
                    "end": chunk[-1].get("resolved_at", ""),
                    "hit_rate": round(hr, 4),
                }

        # By asset
        by_asset: dict[str, dict] = {}
        for e in resolved:
            a = e.get("asset", "unknown")
            by_asset.setdefault(a, {"correct": 0, "total": 0, "pnl": 0.0})
            by_asset[a]["total"] += 1
            by_asset[a]["pnl"] += e.get("pnl", 0.0)
            if e.get("resolution") == "CORRECT":
                by_asset[a]["correct"] += 1
        for a, s in by_asset.items():
            s["hit_rate"] = round(s["correct"] / s["total"], 4) if s["total"] else 0.0
            s["pnl"] = round(s["pnl"], 4)
            s["n"] = s["total"]

        # By edge type
        by_edge_type: dict[str, dict] = {}
        for e in resolved:
            et = e.get("edge_type", "unknown")
            by_edge_type.setdefault(et, {"correct": 0, "total": 0, "pnl": 0.0})
            by_edge_type[et]["total"] += 1
            by_edge_type[et]["pnl"] += e.get("pnl", 0.0)
            if e.get("resolution") == "CORRECT":
                by_edge_type[et]["correct"] += 1
        for et, s in by_edge_type.items():
            s["hit_rate"] = round(s["correct"] / s["total"], 4) if s["total"] else 0.0
            s["pnl"] = round(s["pnl"], 4)
            s["n"] = s["total"]

        # By confidence
        by_confidence: dict[str, dict] = {}
        for e in resolved:
            c = e.get("confidence", "unknown")
            by_confidence.setdefault(c, {"correct": 0, "total": 0, "pnl": 0.0})
            by_confidence[c]["total"] += 1
            by_confidence[c]["pnl"] += e.get("pnl", 0.0)
            if e.get("resolution") == "CORRECT":
                by_confidence[c]["correct"] += 1
        for c, s in by_confidence.items():
            s["hit_rate"] = round(s["correct"] / s["total"], 4) if s["total"] else 0.0
            s["pnl"] = round(s["pnl"], 4)
            s["n"] = s["total"]

        return {
            "insufficient_data": False,
            "total_resolved": total,
            "overall_hit_rate": round(correct / total, 4),
            "overall_pnl": round(total_pnl, 4),
            "overall_sharpe": round(sharpe, 4),
            "rolling_hit_rate": rolling_hit_rate,
            "cumulative_pnl": cumulative_pnl,
            "best_period": best_window,
            "worst_period": worst_window,
            "by_asset": by_asset,
            "by_edge_type": by_edge_type,
            "by_confidence": by_confidence,
        }

    def generate_report(self) -> dict:
        """Full trend report combining all analysis."""
        history = self.compute_history()
        summary = self.compute_summary_stats(history)
        edge_perf = self.edge_performance_over_time()
        return {
            "period": history["period"],
            "asset_summaries": summary,
            "edge_performance": edge_perf,
            "synth_index_history": history["synth_index_history"],
        }

    def export_for_frontend(self, output_path: str = "data/exports/trends.json") -> Path:
        """Export trend data as a single JSON file the frontend can consume."""
        report = self.generate_report()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        return out
