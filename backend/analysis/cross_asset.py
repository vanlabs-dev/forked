"""Cross-asset correlation analysis.

Compares distribution shapes across assets to detect macro regime
correlation, sector divergence, and asset-specific anomalies.
"""

from __future__ import annotations

import math
from typing import Any

from backend.analysis.distribution import CRYPTO_ASSETS, EQUITY_ASSETS

# Metric keys used for shape comparison vectors
_SHAPE_KEYS = [
    "directional_bias",
    "forecast_width",
    "tail_asymmetry",
    "tail_fatness",
    "density_concentration",
]

# Consensus thresholds
_HIGH_CONSENSUS = 0.80
_MEDIUM_CONSENSUS = 0.50

# Outlier detection: standard deviations below group mean
_OUTLIER_THRESHOLD = 1.5

# Regime classification thresholds
_BULLISH_BIAS = 0.002  # +0.2%
_BEARISH_BIAS = -0.002
_ELEVATED_WIDTH_CRYPTO = 0.06
_ELEVATED_WIDTH_EQUITY = 0.03


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _extract_shape_vector(metrics: dict) -> list[float] | None:
    """Extract the 5-element shape vector from distribution metrics."""
    values = []
    for key in _SHAPE_KEYS:
        val = metrics.get(key)
        if val is None:
            return None
        values.append(float(val))
    return values


class CrossAssetAnalyzer:
    """Compares distribution shapes across assets to detect regime correlation and divergence."""

    def __init__(self) -> None:
        self._groups: dict[str, list[str]] = {
            "crypto": sorted(CRYPTO_ASSETS),
            "equities": sorted(EQUITY_ASSETS),
        }

    def analyze(
        self,
        distribution_metrics: dict,
        index_data: dict | None = None,
    ) -> dict:
        """Run full cross-asset analysis on 24h distribution metrics.

        Args:
            distribution_metrics: Output from DistributionAnalyzer.analyze_snapshot().
            index_data: Optional output from SynthIndex.compute() for avg scores.

        Returns:
            Cross-asset analysis dict with group stats, outliers, and regime.
        """
        result: dict[str, Any] = {}

        # Analyze each group on 24h horizon
        group_summaries: dict[str, dict] = {}
        similarity_matrices: dict[str, list[list[float]]] = {}

        for group_name, assets in self._groups.items():
            group_metrics = self._collect_group_metrics(assets, "24h", distribution_metrics)
            if len(group_metrics) < 2:
                continue

            sim_matrix, asset_order = self._compute_similarity_matrix(group_metrics)
            consensus = self._compute_consensus(sim_matrix)
            outlier = self._detect_outlier(sim_matrix, asset_order, group_metrics)
            avg_metrics = self._compute_group_averages(group_metrics)
            avg_index = self._compute_avg_synth_index(assets, "24h", index_data)

            consensus_level = (
                "HIGH" if consensus >= _HIGH_CONSENSUS
                else "MEDIUM" if consensus >= _MEDIUM_CONSENSUS
                else "LOW"
            )

            group_summaries[group_name] = {
                "assets": asset_order,
                "consensus": round(consensus, 4),
                "consensus_level": consensus_level,
                "avg_bias": f"{avg_metrics['directional_bias']:+.2%}",
                "avg_width": f"{avg_metrics['forecast_width']:.2%}",
                "avg_tail_fatness": round(avg_metrics["tail_fatness"], 2),
                "avg_skew": round(avg_metrics["tail_asymmetry"], 2),
                "avg_synth_index": avg_index,
                "outlier": outlier,
            }
            similarity_matrices[group_name] = [
                [round(v, 4) for v in row] for row in sim_matrix
            ]

        result.update(group_summaries)

        # Cross-group comparison
        if "crypto" in group_summaries and "equities" in group_summaries:
            result["cross_group"] = self._cross_group_comparison(
                group_summaries["crypto"],
                group_summaries["equities"],
                distribution_metrics,
            )
        else:
            result["cross_group"] = {
                "correlation": None,
                "regime": "INSUFFICIENT_DATA",
                "description": "Need both crypto and equities data for cross-group analysis",
            }

        result["similarity_matrices"] = similarity_matrices
        return result

    def _collect_group_metrics(
        self, assets: list[str], horizon: str, all_metrics: dict,
    ) -> dict[str, dict]:
        """Collect distribution metrics for assets in a group that have data."""
        group: dict[str, dict] = {}
        for asset in assets:
            key = f"{asset}_{horizon}"
            m = all_metrics.get(key)
            if m and _extract_shape_vector(m) is not None:
                group[asset] = m
        return group

    def _compute_similarity_matrix(
        self, group_metrics: dict[str, dict],
    ) -> tuple[list[list[float]], list[str]]:
        """Build NxN cosine similarity matrix for the group."""
        assets = sorted(group_metrics.keys())
        vectors = {a: _extract_shape_vector(group_metrics[a]) for a in assets}
        n = len(assets)
        matrix: list[list[float]] = []
        for i in range(n):
            row: list[float] = []
            for j in range(n):
                vi = vectors[assets[i]]
                vj = vectors[assets[j]]
                if vi is not None and vj is not None:
                    row.append(_cosine_similarity(vi, vj))
                else:
                    row.append(0.0)
            matrix.append(row)
        return matrix, assets

    def _compute_consensus(self, sim_matrix: list[list[float]]) -> float:
        """Average pairwise similarity (excluding self-comparisons)."""
        n = len(sim_matrix)
        if n < 2:
            return 0.0
        total = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total += sim_matrix[i][j]
                count += 1
        return total / count if count else 0.0

    def _detect_outlier(
        self,
        sim_matrix: list[list[float]],
        asset_order: list[str],
        group_metrics: dict[str, dict],
    ) -> dict | None:
        """Find the asset whose average similarity to others is anomalously low."""
        n = len(sim_matrix)
        if n < 3:
            return None

        # Average similarity of each asset to all others
        avg_sims: list[float] = []
        for i in range(n):
            others = [sim_matrix[i][j] for j in range(n) if j != i]
            avg_sims.append(sum(others) / len(others))

        mean_sim = sum(avg_sims) / len(avg_sims)
        if len(avg_sims) < 2:
            return None
        std_sim = (sum((s - mean_sim) ** 2 for s in avg_sims) / (len(avg_sims) - 1)) ** 0.5

        if std_sim == 0:
            return None

        # Find the asset furthest below the mean
        min_idx = min(range(n), key=lambda i: avg_sims[i])
        z_score = (mean_sim - avg_sims[min_idx]) / std_sim

        if z_score < _OUTLIER_THRESHOLD:
            return None

        outlier_asset = asset_order[min_idx]
        reason = self._describe_outlier(outlier_asset, group_metrics)

        return {
            "asset": outlier_asset,
            "avg_similarity": round(avg_sims[min_idx], 4),
            "group_mean_similarity": round(mean_sim, 4),
            "z_score": round(z_score, 2),
            "reason": reason,
        }

    def _describe_outlier(self, asset: str, group_metrics: dict[str, dict]) -> str:
        """Generate a human-readable reason for why an asset is an outlier."""
        outlier = group_metrics[asset]
        others = {k: v for k, v in group_metrics.items() if k != asset}

        # Compare each key metric against group averages
        differences: list[str] = []

        for key, label in [
            ("directional_bias", "bias"),
            ("tail_asymmetry", "skew"),
            ("tail_fatness", "tail fatness"),
            ("forecast_width", "width"),
        ]:
            o_val = outlier.get(key, 0)
            avg_val = sum(m.get(key, 0) for m in others.values()) / max(len(others), 1)

            if key == "directional_bias":
                if o_val > 0 and avg_val < 0:
                    differences.append("bullish while group is bearish")
                elif o_val < 0 and avg_val > 0:
                    differences.append("bearish while group is bullish")
            elif key == "tail_asymmetry":
                if o_val > 1.3 and avg_val < 1.0:
                    differences.append("bullish skew vs group bearish")
                elif o_val < 0.7 and avg_val > 1.0:
                    differences.append("bearish skew vs group bullish")
            elif key == "tail_fatness":
                if avg_val > 0 and o_val / max(avg_val, 0.01) > 1.5:
                    differences.append(f"tail fatness {o_val / avg_val:.1f}x group average")
            elif key == "forecast_width":
                if avg_val > 0 and o_val / max(avg_val, 0.0001) > 1.5:
                    differences.append(f"width {o_val / avg_val:.1f}x group average")
                elif avg_val > 0 and o_val / max(avg_val, 0.0001) < 0.5:
                    differences.append(f"width {o_val / avg_val:.1f}x group average (compressed)")

        if not differences:
            differences.append("shape vector diverges from group")

        return "; ".join(differences)

    def _compute_group_averages(self, group_metrics: dict[str, dict]) -> dict[str, float]:
        """Average each metric across the group."""
        averages: dict[str, float] = {}
        for key in _SHAPE_KEYS:
            values = [m.get(key, 0) for m in group_metrics.values()]
            averages[key] = sum(values) / len(values) if values else 0.0
        return averages

    def _compute_avg_synth_index(
        self, assets: list[str], horizon: str, index_data: dict | None,
    ) -> float | None:
        """Average Synth-Index for the group."""
        if not index_data:
            return None
        scores: list[float] = []
        for asset in assets:
            key = f"{asset}_{horizon}"
            entry = index_data.get(key)
            if entry:
                scores.append(entry["synth_index"])
        return round(sum(scores) / len(scores), 1) if scores else None

    def _cross_group_comparison(
        self,
        crypto_summary: dict,
        equity_summary: dict,
        distribution_metrics: dict,
    ) -> dict:
        """Compare crypto vs equity group averages to classify macro regime."""
        # Parse bias strings back to floats
        crypto_bias = self._parse_pct(crypto_summary.get("avg_bias", "0"))
        equity_bias = self._parse_pct(equity_summary.get("avg_bias", "0"))
        crypto_width = self._parse_pct(crypto_summary.get("avg_width", "0"))
        equity_width = self._parse_pct(equity_summary.get("avg_width", "0"))

        # Cross-group shape vector correlation
        crypto_vec = self._group_avg_vector(
            sorted(CRYPTO_ASSETS), "24h", distribution_metrics,
        )
        equity_vec = self._group_avg_vector(
            sorted(EQUITY_ASSETS), "24h", distribution_metrics,
        )

        if crypto_vec and equity_vec:
            cross_corr = _cosine_similarity(crypto_vec, equity_vec)
        else:
            cross_corr = 0.0

        # Regime classification
        crypto_bullish = crypto_bias > _BULLISH_BIAS
        crypto_bearish = crypto_bias < _BEARISH_BIAS
        equity_bullish = equity_bias > _BULLISH_BIAS
        equity_bearish = equity_bias < _BEARISH_BIAS
        crypto_stressed = crypto_width > _ELEVATED_WIDTH_CRYPTO
        equity_stressed = equity_width > _ELEVATED_WIDTH_EQUITY

        crypto_consensus = crypto_summary.get("consensus", 0)
        equity_consensus = equity_summary.get("consensus", 0)
        low_consensus = (
            crypto_consensus < _MEDIUM_CONSENSUS
            and equity_consensus < _MEDIUM_CONSENSUS
        )

        if low_consensus:
            regime = "DIVERGENT"
            desc = "Low consensus within both groups, no clear macro signal"
        elif (crypto_bullish and equity_bullish
              and not crypto_stressed and not equity_stressed):
            regime = "RISK_ON"
            desc = "Both crypto and equities showing bullish bias with contained uncertainty"
        elif (crypto_bearish or equity_bearish) and (crypto_stressed or equity_stressed):
            regime = "RISK_OFF"
            desc = "Bearish bias and/or elevated uncertainty across asset classes"
        elif (crypto_bullish and equity_bearish) or (crypto_bearish and equity_bullish):
            regime = "ROTATION"
            crypto_dir = "bullish" if crypto_bullish else "bearish" if crypto_bearish else "neutral"
            equity_dir = "bullish" if equity_bullish else "bearish" if equity_bearish else "neutral"
            desc = f"Crypto {crypto_dir}, equities {equity_dir} -- sector rotation signal"
        elif not crypto_stressed and not equity_stressed:
            regime = "CALM"
            desc = "Both groups showing contained distributions with no strong directional signal"
        else:
            regime = "MIXED"
            desc = "No clear regime classification"

        return {
            "correlation": round(cross_corr, 4),
            "regime": regime,
            "crypto_bias": f"{crypto_bias:+.2%}",
            "equity_bias": f"{equity_bias:+.2%}",
            "description": desc,
        }

    def _group_avg_vector(
        self, assets: list[str], horizon: str, distribution_metrics: dict,
    ) -> list[float] | None:
        """Compute the average shape vector for a group of assets."""
        vectors: list[list[float]] = []
        for asset in assets:
            key = f"{asset}_{horizon}"
            m = distribution_metrics.get(key)
            if m:
                vec = _extract_shape_vector(m)
                if vec:
                    vectors.append(vec)
        if not vectors:
            return None
        n = len(vectors)
        return [sum(v[i] for v in vectors) / n for i in range(len(vectors[0]))]

    @staticmethod
    def _parse_pct(s: str) -> float:
        """Parse a percentage string like '+1.23%' to 0.0123."""
        try:
            return float(s.rstrip("%")) / 100
        except (ValueError, AttributeError):
            return 0.0
