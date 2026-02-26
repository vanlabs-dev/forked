from typing import Any

import httpx

from backend.config import (
    DEFAULT_DAYS,
    DEFAULT_MINER_LIMIT,
    PREDICTION_ASSET_MAP,
    SYNTH_API_KEY,
    SYNTH_BASE_URL,
)


class SynthAPIError(Exception):
    """Raised when a Synth API request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Synth API error {status_code}: {message}")


class SynthClient:
    """Client for the Synth API (Bittensor Subnet 50).

    Provides typed access to all insight, prediction, and leaderboard endpoints.
    Uses httpx for HTTP with automatic retries on transient failures.
    """

    def __init__(
        self,
        api_key: str = SYNTH_API_KEY,
        base_url: str = SYNTH_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = httpx.HTTPTransport(retries=max_retries)
        self._headers = {
            "Authorization": f"Apikey {api_key}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a GET request with auth headers and error handling."""
        url = f"{self._base_url}{path}"
        with httpx.Client(transport=self._transport, timeout=self._timeout) as client:
            response = client.get(url, headers=self._headers, params=params)

        if response.status_code != 200:
            raise SynthAPIError(response.status_code, response.text)

        return response.json()

    # ── Insight Endpoints ──────────────────────────────────────────────

    def get_prediction_percentiles(
        self,
        asset: str,
        horizon: str = "24h",
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Price distribution percentiles at 9 levels over the forecast horizon."""
        return self._get(
            "/insights/prediction-percentiles",
            params={"asset": asset, "horizon": horizon, "days": days, "limit": limit},
        )

    def get_volatility(
        self,
        asset: str,
        horizon: str = "24h",
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Ensemble volatility forecast from top meta-leaderboard miners."""
        return self._get(
            "/insights/volatility",
            params={"asset": asset, "horizon": horizon, "days": days, "limit": limit},
        )

    def get_option_pricing(
        self,
        asset: str,
        horizon: str = "24h",
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Theoretical call/put prices across strike prices."""
        return self._get(
            "/insights/option-pricing",
            params={"asset": asset, "horizon": horizon, "days": days, "limit": limit},
        )

    def get_liquidation(
        self,
        asset: str,
        horizon: str = "24h",
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Long/short liquidation probabilities at various price levels."""
        return self._get(
            "/insights/liquidation",
            params={"asset": asset, "horizon": horizon, "days": days, "limit": limit},
        )

    def get_lp_bounds(
        self,
        asset: str,
        horizon: str = "24h",
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Price interval analysis with probability of staying in range and impermanent loss."""
        return self._get(
            "/insights/lp-bounds",
            params={"asset": asset, "horizon": horizon, "days": days, "limit": limit},
        )

    def get_lp_probabilities(
        self,
        asset: str,
        horizon: str = "24h",
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Probability of price being above/below specific targets over the forecast horizon."""
        return self._get(
            "/insights/lp-probabilities",
            params={"asset": asset, "horizon": horizon, "days": days, "limit": limit},
        )

    # ── Polymarket Endpoints ───────────────────────────────────────────

    def get_polymarket_updown_daily(
        self,
        asset: str,
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Synth fair probabilities vs live Polymarket odds for daily up/down contracts."""
        return self._get(
            "/insights/polymarket/up-down/daily",
            params={"asset": asset, "horizon": "24h", "days": days, "limit": limit},
        )

    def get_polymarket_updown_hourly(
        self,
        asset: str,
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Synth fair probabilities vs live Polymarket odds for hourly up/down contracts."""
        return self._get(
            "/insights/polymarket/up-down/hourly",
            params={"asset": asset, "horizon": "1h", "days": days, "limit": limit},
        )

    def get_polymarket_updown_15min(
        self,
        asset: str,
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> dict[str, Any]:
        """Synth fair probabilities vs live Polymarket odds for 15-minute up/down contracts."""
        return self._get(
            "/insights/polymarket/up-down/15min",
            params={"asset": asset, "horizon": "1h", "days": days, "limit": limit},
        )

    def get_polymarket_range(
        self,
        asset: str,
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_MINER_LIMIT,
    ) -> list[dict[str, Any]]:
        """Synth fair probabilities vs live Polymarket odds for daily price range contracts."""
        return self._get(
            "/insights/polymarket/range",
            params={"asset": asset, "horizon": "24h", "days": days, "limit": limit},
        )

    # ── Prediction Endpoints ───────────────────────────────────────────

    def get_best_prediction(
        self,
        asset: str,
        time_increment: int = 300,
        time_length: int = 86400,
    ) -> list[dict[str, Any]]:
        """Latest prediction rates from the current best-performing miner.

        Args:
            asset: Standard asset symbol (e.g. "BTC", "SPY"). Mapped internally.
            time_increment: Prediction interval in seconds (300 for 5min, 60 for 1min).
            time_length: Total forecast length in seconds (86400 for 24h, 3600 for 1h).
        """
        prediction_asset = PREDICTION_ASSET_MAP.get(asset, asset)
        return self._get(
            "/v2/prediction/best",
            params={
                "asset": prediction_asset,
                "time_increment": time_increment,
                "time_length": time_length,
            },
        )

    def get_latest_predictions(
        self,
        miner_ids: list[int],
        asset: str,
        time_increment: int = 300,
        time_length: int = 86400,
    ) -> list[dict[str, Any]]:
        """Latest valid prediction rates from specific miners.

        Args:
            miner_ids: List of miner UIDs to query.
            asset: Standard asset symbol. Mapped internally.
            time_increment: Prediction interval in seconds.
            time_length: Total forecast length in seconds.
        """
        prediction_asset = PREDICTION_ASSET_MAP.get(asset, asset)
        return self._get(
            "/v2/prediction/latest",
            params={
                "miner": ",".join(str(m) for m in miner_ids),
                "asset": prediction_asset,
                "time_increment": time_increment,
                "time_length": time_length,
            },
        )

    def get_historical_predictions(
        self,
        miner_ids: list[int],
        asset: str,
        start_time: str,
        time_increment: int = 300,
        time_length: int = 86400,
    ) -> list[dict[str, Any]]:
        """Historical prediction rates from specific miners.

        Args:
            miner_ids: List of miner UIDs to query.
            asset: Standard asset symbol. Mapped internally.
            start_time: ISO 8601 datetime string for the query start.
            time_increment: Prediction interval in seconds.
            time_length: Total forecast length in seconds.
        """
        prediction_asset = PREDICTION_ASSET_MAP.get(asset, asset)
        return self._get(
            "/v2/prediction/historical",
            params={
                "miner": ",".join(str(m) for m in miner_ids),
                "asset": prediction_asset,
                "start_time": start_time,
                "time_increment": time_increment,
                "time_length": time_length,
            },
        )

    # ── Leaderboard Endpoints ──────────────────────────────────────────

    def get_meta_leaderboard(
        self,
        days: int = DEFAULT_DAYS,
        prompt_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Current meta-leaderboard aggregating miner incentives over a rolling window.

        Args:
            days: Number of days to aggregate.
            prompt_name: "high" for 1h prompt, "low" for 24h prompt. None for default.
        """
        params: dict[str, Any] = {"days": days}
        if prompt_name is not None:
            params["prompt_name"] = prompt_name
        return self._get("/v2/meta-leaderboard/latest", params=params)

    def get_leaderboard_latest(
        self,
        prompt_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Current leaderboard snapshot.

        Args:
            prompt_name: "high" for 1h prompt, "low" for 24h prompt. None for default.
        """
        params: dict[str, Any] = {}
        if prompt_name is not None:
            params["prompt_name"] = prompt_name
        return self._get("/v2/leaderboard/latest", params=params)
