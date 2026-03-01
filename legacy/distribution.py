"""Distribution shape analysis for Synth prediction percentiles.

Extracts distribution shape metrics from the 9-level percentile forecasts
to detect market regimes, tail risk, and directional skew.
"""

from __future__ import annotations

from backend.config import ASSETS, HORIZONS, PERCENTILES_1H_ASSETS

# Asset classification for threshold scaling
CRYPTO_ASSETS: set[str] = {"BTC", "ETH", "SOL"}
EQUITY_ASSETS: set[str] = {"SPY", "NVDA", "GOOGL", "TSLA", "AAPL"}
GOLD_ASSETS: set[str] = {"XAU"}

# Percentile keys as they appear in the API response
P005 = "0.005"
P05 = "0.05"
P20 = "0.2"
P35 = "0.35"
P50 = "0.5"
P65 = "0.65"
P80 = "0.8"
P95 = "0.95"
P995 = "0.995"


def _asset_class(asset: str) -> str:
    if asset in CRYPTO_ASSETS:
        return "crypto"
    if asset in EQUITY_ASSETS:
        return "equity"
    if asset in GOLD_ASSETS:
        return "gold"
    return "crypto"


def _width_thresholds(asset: str) -> tuple[float, float]:
    """Return (compressed_upper, stressed_lower) width thresholds as fractions."""
    cls = _asset_class(asset)
    if cls == "crypto":
        return 0.02, 0.06
    if cls == "equity":
        return 0.01, 0.03
    # gold: 60% of crypto
    return 0.012, 0.036


class DistributionAnalyzer:
    """Analyzes Synth percentile data to extract distribution shape signals."""

    def analyze_snapshot(self, snapshot: dict) -> dict:
        """Analyze all assets in an AlphaLog snapshot.

        Returns a dict keyed by (asset, horizon) with distribution metrics.
        """
        results: dict[str, dict] = {}
        assets_data = snapshot.get("assets", {})

        for asset in ASSETS:
            asset_data = assets_data.get(asset)
            if not asset_data:
                continue

            current_price = asset_data.get("current_price")
            if not current_price:
                continue

            for horizon in HORIZONS:
                # 1h percentiles only available for certain assets
                if horizon == "1h" and asset not in PERCENTILES_1H_ASSETS:
                    continue

                key = f"percentiles_{horizon}"
                pct_data = asset_data.get(key)
                if not pct_data:
                    continue

                metrics = self.analyze_asset(pct_data, asset, horizon, current_price)
                if metrics:
                    results[f"{asset}_{horizon}"] = metrics

        return results

    def analyze_asset(
        self,
        pct_data: dict,
        asset: str,
        horizon: str,
        current_price: float,
    ) -> dict | None:
        """Analyze a single asset's percentile data for one horizon.

        Args:
            pct_data: The percentiles_Xh dict from the snapshot.
            asset: Asset symbol.
            horizon: "1h" or "24h".
            current_price: Current spot price from the snapshot.

        Returns:
            Dict of distribution metrics, or None if data is insufficient.
        """
        timepoints = (
            pct_data.get("forecast_future", {}).get("percentiles", [])
        )
        if not timepoints:
            return None

        # Use the final timepoint (end of forecast horizon)
        final = timepoints[-1]

        # Extract percentile values
        try:
            p005 = float(final[P005])
            p05 = float(final[P05])
            p20 = float(final[P20])
            p35 = float(final[P35])
            p50 = float(final[P50])
            p65 = float(final[P65])
            p80 = float(final[P80])
            p95 = float(final[P95])
            p995 = float(final[P995])
        except (KeyError, TypeError, ValueError):
            return None

        # Guard against degenerate data
        upper_spread = p95 - p05
        lower_half = p50 - p05
        upper_half = p95 - p50

        if upper_spread <= 0 or lower_half <= 0 or upper_half <= 0:
            return None

        # 1. Directional bias: how far the median forecast is from current price
        directional_bias = (p50 - current_price) / current_price

        # 2. Forecast width: overall uncertainty as fraction of price
        forecast_width = upper_spread / current_price

        # 3. Tail asymmetry (skew proxy): ratio of upside to downside spread
        tail_asymmetry = upper_half / lower_half

        # 4. Tail fatness (kurtosis proxy): extreme range vs main range
        tail_fatness = (p995 - p005) / upper_spread

        # 5. Upper tail risk: how extreme the right tail extends
        upper_tail_risk = (p995 - p95) / upper_half

        # 6. Lower tail risk: how extreme the left tail extends
        lower_tail_risk = (p05 - p005) / lower_half

        # 7. Density concentration: fraction of spread in the central band
        density_concentration = (p65 - p35) / upper_spread

        # Regime classification
        regime = self._classify_regime(asset, forecast_width, tail_fatness, density_concentration)

        return {
            "asset": asset,
            "horizon": horizon,
            "current_price": current_price,
            "median_forecast": p50,
            "directional_bias": round(directional_bias, 6),
            "forecast_width": round(forecast_width, 6),
            "tail_asymmetry": round(tail_asymmetry, 4),
            "tail_fatness": round(tail_fatness, 4),
            "upper_tail_risk": round(upper_tail_risk, 4),
            "lower_tail_risk": round(lower_tail_risk, 4),
            "density_concentration": round(density_concentration, 4),
            "regime": regime,
        }

    def _classify_regime(
        self,
        asset: str,
        forecast_width: float,
        tail_fatness: float,
        density_concentration: float,
    ) -> str:
        """Classify the distribution regime for an asset."""
        compressed_upper, stressed_lower = _width_thresholds(asset)

        is_wide = forecast_width > stressed_lower
        is_narrow = forecast_width < compressed_upper
        is_fat_tailed = tail_fatness > 2.5
        is_dispersed = density_concentration < 0.20
        is_concentrated = density_concentration > 0.40

        if is_wide or is_fat_tailed or is_dispersed:
            return "STRESSED"
        if is_narrow and is_concentrated:
            return "COMPRESSED"
        return "NORMAL"
