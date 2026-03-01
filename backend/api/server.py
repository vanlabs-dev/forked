"""FastAPI server for Prism probability and position risk endpoints."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from backend.analysis.position_risk import PositionRiskAnalyzer
from backend.analysis.probability import ProbabilityEngine
from backend.config import ASSETS, PERCENTILES_1H_ASSETS, SYNTH_API_KEY
from backend.synth_client import SynthAPIError, SynthClient

logger = logging.getLogger("prism.api")

# ── Asset metadata ────────────────────────────────────────────────────

ASSET_NAMES: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "XAU": "Gold",
    "SPY": "S&P 500",
    "NVDA": "NVIDIA",
    "GOOGL": "Google",
    "TSLA": "Tesla",
    "AAPL": "Apple",
}

ASSET_HORIZONS: dict[str, list[str]] = {
    asset: ["1h", "24h"] if asset in PERCENTILES_1H_ASSETS else ["24h"]
    for asset in ASSETS
}

VALID_HORIZONS: set[str] = {"1h", "24h"}


# ── Caching Synth client wrapper ─────────────────────────────────────

class _CachingSynthClient:
    """Wraps SynthClient with in-memory TTL cache for percentile data."""

    def __init__(self, client: SynthClient, ttl: int = 300) -> None:
        self._client = client
        self._ttl = ttl
        self._cache: dict[str, tuple[float, Any]] = {}

    def get_prediction_percentiles(
        self, asset: str = "BTC", horizon: str = "24h", **kwargs: Any,
    ) -> dict[str, Any]:
        key = f"pct:{asset}:{horizon}"
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached is not None:
            fetched_at, data = cached
            if now - fetched_at < self._ttl:
                return data
        data = self._client.get_prediction_percentiles(
            asset=asset, horizon=horizon, **kwargs,
        )
        self._cache[key] = (now, data)
        return data

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


# ── Request models ────────────────────────────────────────────────────

class ProbabilityRequest(BaseModel):
    asset: str
    lower: float | None = None
    upper: float | None = None
    horizon: str = "24h"

    @field_validator("asset")
    @classmethod
    def validate_asset(cls, v: str) -> str:
        v = v.upper()
        if v not in ASSETS:
            raise ValueError(f"Invalid asset '{v}'. Valid: {ASSETS}")
        return v

    @field_validator("horizon")
    @classmethod
    def validate_horizon(cls, v: str) -> str:
        if v not in VALID_HORIZONS:
            raise ValueError(f"Invalid horizon '{v}'. Valid: {sorted(VALID_HORIZONS)}")
        return v


class PositionRiskRequest(BaseModel):
    asset: str
    entry_price: float
    leverage: float
    direction: str
    take_profit: float | None = None
    stop_loss: float | None = None
    horizon: str = "24h"

    @field_validator("asset")
    @classmethod
    def validate_asset(cls, v: str) -> str:
        v = v.upper()
        if v not in ASSETS:
            raise ValueError(f"Invalid asset '{v}'. Valid: {ASSETS}")
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        v = v.upper()
        if v not in ("LONG", "SHORT"):
            raise ValueError("direction must be 'LONG' or 'SHORT'")
        return v

    @field_validator("leverage")
    @classmethod
    def validate_leverage(cls, v: float) -> float:
        if not 1.0 <= v <= 200.0:
            raise ValueError("leverage must be between 1 and 200")
        return v

    @field_validator("horizon")
    @classmethod
    def validate_horizon(cls, v: str) -> str:
        if v not in VALID_HORIZONS:
            raise ValueError(f"Invalid horizon '{v}'. Valid: {sorted(VALID_HORIZONS)}")
        return v


# ── App singletons ────────────────────────────────────────────────────

_engine: ProbabilityEngine | None = None
_analyzer: PositionRiskAnalyzer | None = None

# Assets list cache: (timestamp, data)
_assets_cache: tuple[float, list[dict[str, Any]]] | None = None
_ASSETS_CACHE_TTL = 60  # seconds


def _init_engine() -> ProbabilityEngine:
    global _engine
    if _engine is None:
        raw_client = SynthClient(SYNTH_API_KEY)
        caching_client = _CachingSynthClient(raw_client, ttl=300)
        _engine = ProbabilityEngine(caching_client)  # type: ignore[arg-type]
    return _engine


def _init_analyzer() -> PositionRiskAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = PositionRiskAnalyzer(_init_engine())
    return _analyzer


# ── Error helpers ─────────────────────────────────────────────────────

def _handle_synth_error(exc: SynthAPIError) -> HTTPException:
    logger.error("Synth API error: %s", exc)
    return HTTPException(
        status_code=503,
        detail={"error": "Synth API unavailable", "detail": str(exc)},
    )


def _validate_asset_horizon(asset: str, horizon: str) -> None:
    supported = ASSET_HORIZONS.get(asset, [])
    if horizon not in supported:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Asset '{asset}' does not support horizon '{horizon}'",
                "supported_horizons": supported,
            },
        )


# ── App factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(title="Prism API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health ────────────────────────────────────────────────────

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        synth_ok = False
        try:
            engine = _init_engine()
            engine.get_percentile_data("BTC", "24h")
            synth_ok = True
        except Exception:
            pass
        return {"status": "ok", "synth_connected": synth_ok}

    # ── Assets ────────────────────────────────────────────────────

    @app.get("/api/assets")
    def assets() -> dict[str, Any]:
        global _assets_cache
        now = time.monotonic()

        if _assets_cache is not None:
            cached_at, cached_data = _assets_cache
            if now - cached_at < _ASSETS_CACHE_TTL:
                return {"assets": cached_data}

        engine = _init_engine()
        result: list[dict[str, Any]] = []

        for symbol in ASSETS:
            try:
                data = engine.get_percentile_data(symbol, "24h")
                price = data["current_price"]
            except Exception:
                price = None

            result.append({
                "symbol": symbol,
                "name": ASSET_NAMES.get(symbol, symbol),
                "current_price": price,
                "horizons": ASSET_HORIZONS.get(symbol, ["24h"]),
            })

        _assets_cache = (now, result)
        return {"assets": result}

    # ── Probability ───────────────────────────────────────────────

    @app.post("/api/probability")
    def probability(req: ProbabilityRequest) -> dict[str, Any]:
        if req.lower is None and req.upper is None:
            raise HTTPException(
                status_code=400,
                detail={"error": "At least one of 'lower' or 'upper' is required"},
            )

        _validate_asset_horizon(req.asset, req.horizon)
        engine = _init_engine()

        try:
            if req.lower is not None and req.upper is not None:
                prob = engine.probability_between(
                    req.asset, req.lower, req.upper, req.horizon,
                )
            elif req.lower is not None:
                prob = engine.probability_above(
                    req.asset, req.lower, req.horizon,
                )
            else:
                prob = engine.probability_below(
                    req.asset, req.upper, req.horizon,  # type: ignore[arg-type]
                )

            cone = engine.probability_cone(req.asset, req.horizon)
            return {**prob, "cone": cone}

        except SynthAPIError as exc:
            raise _handle_synth_error(exc)

    # ── Position risk ─────────────────────────────────────────────

    @app.post("/api/position-risk")
    def position_risk(req: PositionRiskRequest) -> dict[str, Any]:
        _validate_asset_horizon(req.asset, req.horizon)
        analyzer = _init_analyzer()

        try:
            return analyzer.analyze_position(
                asset=req.asset,
                entry_price=req.entry_price,
                leverage=req.leverage,
                direction=req.direction,
                take_profit=req.take_profit,
                stop_loss=req.stop_loss,
                horizon=req.horizon,
            )
        except SynthAPIError as exc:
            raise _handle_synth_error(exc)

    # ── Cone ──────────────────────────────────────────────────────

    @app.get("/api/cone/{asset}")
    def cone(asset: str, horizon: str = "24h") -> dict[str, Any]:
        asset = asset.upper()
        if asset not in ASSETS:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Invalid asset '{asset}'", "valid_assets": ASSETS},
            )
        if horizon not in VALID_HORIZONS:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Invalid horizon '{horizon}'", "valid_horizons": sorted(VALID_HORIZONS)},
            )
        _validate_asset_horizon(asset, horizon)

        engine = _init_engine()
        try:
            return engine.probability_cone(asset, horizon)
        except SynthAPIError as exc:
            raise _handle_synth_error(exc)

    return app
