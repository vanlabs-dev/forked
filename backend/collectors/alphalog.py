"""AlphaLog — Continuous Synth API data collector.

Records prediction percentiles, Polymarket odds, and volatility data
every hour for all supported assets. Builds a historical dataset of
Synth predictions vs actual outcomes.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import (
    ASSETS,
    PERCENTILES_1H_ASSETS,
    POLYMARKET_DAILY_ASSETS,
    POLYMARKET_RANGE_ASSETS,
    POLYMARKET_SHORT_TERM_ASSETS,
    SUPABASE_KEY,
    SUPABASE_URL,
)
from backend.synth_client import SynthAPIError, SynthClient

logger = logging.getLogger("alphalog")

# Max retries and backoff for individual endpoint calls
_MAX_RETRIES = 3
_BACKOFF_SECONDS = [1, 2, 4]


class AlphaLogCollector:
    """Collects and stores Synth API snapshots."""

    def __init__(self, synth_client: SynthClient) -> None:
        self._client = synth_client
        self._auth_failed = False

    def _call_with_retry(self, method_name: str, **kwargs: Any) -> Any:
        """Call a SynthClient method with exponential backoff retries.

        Raises SynthAPIError with status 401/403 immediately (no retry on auth errors).
        """
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                method = getattr(self._client, method_name)
                return method(**kwargs)
            except SynthAPIError as exc:
                if exc.status_code in (401, 403):
                    raise
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BACKOFF_SECONDS[attempt])
            except Exception as exc:
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BACKOFF_SECONDS[attempt])

        raise last_error  # type: ignore[misc]

    def _fetch_endpoint(
        self,
        result: dict[str, Any],
        key: str,
        method: str,
        extract_price: bool = False,
        **kwargs: Any,
    ) -> None:
        """Fetch a single endpoint into result[key], recording errors."""
        try:
            data = self._call_with_retry(method, **kwargs)
            result[key] = data
            if extract_price and result["current_price"] is None and isinstance(data, dict):
                result["current_price"] = data.get("current_price")
        except SynthAPIError as exc:
            if exc.status_code in (401, 403):
                raise
            result["errors"].append(f"{key}: {exc}")
            logger.warning("  %s %s failed: %s", kwargs.get("asset", "?"), key, exc)
        except Exception as exc:
            result["errors"].append(f"{key}: {exc}")
            logger.warning("  %s %s failed: %s", kwargs.get("asset", "?"), key, exc)

    def _collect_asset(self, asset: str) -> dict[str, Any]:
        """Collect all supported endpoint data for a single asset."""
        result: dict[str, Any] = {
            "current_price": None,
            "percentiles_24h": {},
            "percentiles_1h": {},
            "polymarket_daily": {},
            "polymarket_hourly": {},
            "polymarket_range": {},
            "volatility_24h": {},
            "errors": [],
        }

        # Percentiles 24h — all assets
        self._fetch_endpoint(
            result, "percentiles_24h", "get_prediction_percentiles",
            extract_price=True, asset=asset, horizon="24h",
        )

        # Percentiles 1h — crypto + gold only
        if asset in PERCENTILES_1H_ASSETS:
            self._fetch_endpoint(
                result, "percentiles_1h", "get_prediction_percentiles",
                extract_price=True, asset=asset, horizon="1h",
            )
        else:
            logger.debug("  %s: skipping percentiles_1h (unsupported)", asset)

        # Polymarket daily up/down
        if asset in POLYMARKET_DAILY_ASSETS:
            self._fetch_endpoint(
                result, "polymarket_daily", "get_polymarket_updown_daily", asset=asset,
            )
        else:
            logger.debug("  %s: skipping polymarket_daily (unsupported)", asset)

        # Polymarket hourly up/down — crypto only
        if asset in POLYMARKET_SHORT_TERM_ASSETS:
            self._fetch_endpoint(
                result, "polymarket_hourly", "get_polymarket_updown_hourly", asset=asset,
            )
        else:
            logger.debug("  %s: skipping polymarket_hourly (unsupported)", asset)

        # Polymarket range
        if asset in POLYMARKET_RANGE_ASSETS:
            self._fetch_endpoint(
                result, "polymarket_range", "get_polymarket_range", asset=asset,
            )
        else:
            logger.debug("  %s: skipping polymarket_range (unsupported)", asset)

        # Volatility 24h — all assets
        self._fetch_endpoint(
            result, "volatility_24h", "get_volatility", asset=asset, horizon="24h",
        )

        return result

    def collect_snapshot(self) -> dict[str, Any]:
        """Collect one complete snapshot across all assets.

        Returns a dict with timestamp, assets data, errors, and partial flag.
        If auth fails on the first API call, aborts the entire cycle.
        """
        start = time.monotonic()
        ts = datetime.now(timezone.utc).isoformat()

        snapshot: dict[str, Any] = {
            "timestamp": ts,
            "collection_duration_ms": 0,
            "assets": {},
            "collection_errors": [],
            "partial": False,
        }

        for asset in ASSETS:
            try:
                logger.info("Collecting %s...", asset)
                asset_data = self._collect_asset(asset)
                snapshot["assets"][asset] = asset_data
                if asset_data["errors"]:
                    snapshot["partial"] = True
            except SynthAPIError as exc:
                if exc.status_code in (401, 403):
                    logger.error("Auth failed on %s — aborting cycle: %s", asset, exc)
                    snapshot["collection_errors"].append(f"AUTH_FAILED: {exc}")
                    snapshot["partial"] = True
                    break
                snapshot["collection_errors"].append(f"{asset}: {exc}")
                snapshot["partial"] = True
                logger.error("Asset %s failed entirely: %s", asset, exc)
            except Exception as exc:
                snapshot["collection_errors"].append(f"{asset}: {exc}")
                snapshot["partial"] = True
                logger.error("Asset %s failed entirely: %s", asset, exc)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        snapshot["collection_duration_ms"] = elapsed_ms

        asset_count = len(snapshot["assets"])
        error_count = sum(
            len(a.get("errors", [])) for a in snapshot["assets"].values()
        ) + len(snapshot["collection_errors"])
        logger.info(
            "Snapshot complete — %d/%d assets, %d errors, %.1fs",
            asset_count,
            len(ASSETS),
            error_count,
            elapsed_ms / 1000,
        )

        return snapshot

    def save_local(self, snapshot: dict[str, Any], base_dir: str = "data/snapshots") -> Path:
        """Save snapshot to local filesystem.

        File path: {base_dir}/YYYY-MM-DD/HH-MM-SS_snapshot.json
        """
        ts = datetime.fromisoformat(snapshot["timestamp"])
        day_dir = Path(base_dir) / ts.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)

        filename = ts.strftime("%H-%M-%S") + "_snapshot.json"
        filepath = day_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, default=str)

        logger.info("Saved local: %s (%.1f KB)", filepath, filepath.stat().st_size / 1024)
        return filepath

    def save_supabase(self, snapshot: dict[str, Any]) -> None:
        """Push snapshot to Supabase if configured. Fails silently on error."""
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.debug("Supabase not configured — skipping remote save")
            return

        try:
            from supabase import create_client

            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            client.table("alphalog_snapshots").insert({
                "timestamp": snapshot["timestamp"],
                "data": snapshot,
                "partial": snapshot["partial"],
                "asset_count": len(snapshot["assets"]),
                "duration_ms": snapshot["collection_duration_ms"],
            }).execute()
            logger.info("Saved to Supabase")
        except Exception as exc:
            logger.warning("Supabase save failed (non-fatal): %s", exc)

    def run_once(self) -> dict[str, Any]:
        """Execute a single collection cycle: collect, save local, save Supabase."""
        snapshot = self.collect_snapshot()
        self.save_local(snapshot)
        self.save_supabase(snapshot)
        return snapshot
