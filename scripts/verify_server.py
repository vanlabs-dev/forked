"""Verify the Prism API server — starts the app with synthetic Synth data
and tests every endpoint.

Usage: python -m scripts.verify_server
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any
from unittest.mock import MagicMock

import httpx
import uvicorn

# ── Synthetic data ────────────────────────────────────────────────────

_ASSET_CONFIGS: dict[str, dict[str, float]] = {
    "BTC": {"price": 88500.0, "spread": 0.065},
    "ETH": {"price": 3200.0, "spread": 0.080},
    "SOL": {"price": 145.0, "spread": 0.095},
    "XAU": {"price": 2650.0, "spread": 0.040},
    "SPY": {"price": 5800.0, "spread": 0.025},
    "NVDA": {"price": 880.0, "spread": 0.055},
    "GOOGL": {"price": 175.0, "spread": 0.035},
    "TSLA": {"price": 340.0, "spread": 0.070},
    "AAPL": {"price": 228.0, "spread": 0.030},
}

_OFFSETS: dict[str, float] = {
    "0.005": -1.00, "0.05": -0.646, "0.2": -0.308, "0.35": -0.154,
    "0.5": 0.015, "0.65": 0.185, "0.8": 0.354, "0.95": 0.692, "0.995": 1.077,
}


def _make_response(asset: str, horizon: str) -> dict[str, Any]:
    cfg = _ASSET_CONFIGS.get(asset, {"price": 100.0, "spread": 0.05})
    base = cfg["price"]
    spread = cfg["spread"]
    n = 289
    tps = []
    for i in range(n):
        f = i / (n - 1)
        tps.append({k: base * (1.0 + v * spread * f) for k, v in _OFFSETS.items()})
    return {"current_price": base, "forecast_future": {"percentiles": tps}}


def _patch_and_create_app() -> Any:
    """Patch the server to use synthetic data, return the ASGI app."""
    from backend.analysis.position_risk import PositionRiskAnalyzer
    from backend.analysis.probability import ProbabilityEngine
    import backend.api.server as srv

    mock = MagicMock()
    mock.get_prediction_percentiles.side_effect = (
        lambda asset="BTC", horizon="24h", **kw: _make_response(asset, horizon)
    )

    engine = ProbabilityEngine(mock)
    analyzer = PositionRiskAnalyzer(engine)

    srv._engine = engine
    srv._analyzer = analyzer

    return srv.create_app()


# ── Tests ─────────────────────────────────────────────────────────────

PORT = 18321
BASE = f"http://localhost:{PORT}"


def _pp(label: str, resp: httpx.Response) -> dict[str, Any]:
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"  Status: {resp.status_code}")
    cors = resp.headers.get("access-control-allow-origin", "MISSING")
    print(f"  CORS:   {cors}")
    print(f"{'='*65}")
    data = resp.json()
    # Truncate large cone arrays for readability.
    text = json.dumps(data, indent=2, default=str)
    if len(text) > 3000:
        text = text[:3000] + "\n  ... (truncated)"
    print(text)
    return data


def run_tests() -> None:
    c = httpx.Client(base_url=BASE, timeout=30)

    # 1) Health
    r = c.get("/api/health")
    data = _pp("GET /api/health", r)
    assert r.status_code == 200
    assert data["status"] == "ok"
    print(f"\n  synth_connected: {data['synth_connected']}  [OK]")

    # 2) Assets
    r = c.get("/api/assets")
    data = _pp("GET /api/assets", r)
    assert r.status_code == 200
    assert len(data["assets"]) == 9
    btc = next(a for a in data["assets"] if a["symbol"] == "BTC")
    assert btc["current_price"] == 88500.0
    print(f"\n  Assets: {len(data['assets'])}  BTC: ${btc['current_price']:,.2f}  [OK]")

    # 3) Probability (between)
    r = c.post("/api/probability", json={
        "asset": "BTC", "lower": 85000, "upper": 92000, "horizon": "24h",
    })
    data = _pp("POST /api/probability (BTC between $85k-$92k)", r)
    assert r.status_code == 200
    assert 0 < data["probability"] < 1
    assert "cone" in data
    assert len(data["cone"]["points"]) == 50
    print(f"\n  P(85k<BTC<92k): {data['probability']:.4f}  "
          f"Cone: {len(data['cone']['points'])} pts  [OK]")

    # 4) Probability (above)
    r = c.post("/api/probability", json={"asset": "ETH", "lower": 3300})
    data = _pp("POST /api/probability (ETH above $3300)", r)
    assert r.status_code == 200
    print(f"\n  P(ETH>$3300): {data['probability']:.4f}  [OK]")

    # 5) Probability (below)
    r = c.post("/api/probability", json={"asset": "SOL", "upper": 140})
    data = _pp("POST /api/probability (SOL below $140)", r)
    assert r.status_code == 200
    print(f"\n  P(SOL<$140): {data['probability']:.4f}  [OK]")

    # 6) Position risk
    r = c.post("/api/position-risk", json={
        "asset": "BTC", "entry_price": 88500, "leverage": 20,
        "direction": "LONG", "take_profit": 92000, "stop_loss": 87000,
        "horizon": "24h",
    })
    data = _pp("POST /api/position-risk (BTC LONG 20x)", r)
    assert r.status_code == 200
    liq = data["liquidation"]
    rs = data["risk_score"]
    print(f"\n  Liq: ${liq['price']:,.2f} ({liq['probability']*100:.1f}%)  "
          f"Risk: {rs['score']}/100 [{rs['label']}]  [OK]")

    # 7) Cone
    r = c.get("/api/cone/BTC?horizon=24h")
    data = _pp("GET /api/cone/BTC?horizon=24h", r)
    assert r.status_code == 200
    assert len(data["points"]) == 50
    print(f"\n  Cone: {len(data['points'])} pts  Asset: {data['asset']}  [OK]")

    # 8) Error cases
    print(f"\n{'='*65}")
    print("  Error handling")
    print(f"{'='*65}")

    r = c.post("/api/probability", json={"asset": "DOGE", "lower": 1.0})
    assert r.status_code == 422
    print(f"  Invalid asset:     {r.status_code}  [OK]")

    r = c.post("/api/probability", json={"asset": "BTC"})
    assert r.status_code == 400
    print(f"  Missing bounds:    {r.status_code}  [OK]")

    r = c.post("/api/position-risk", json={
        "asset": "BTC", "entry_price": 88500, "leverage": 5, "direction": "UP",
    })
    assert r.status_code == 422
    print(f"  Invalid direction: {r.status_code}  [OK]")

    r = c.get("/api/cone/SPY?horizon=1h")
    assert r.status_code == 400
    print(f"  SPY + 1h horizon:  {r.status_code}  [OK]")

    r = c.options("/api/health", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    })
    cors = r.headers.get("access-control-allow-origin", "MISSING")
    print(f"  CORS preflight:    {cors}  [{'OK' if cors != 'MISSING' else 'FAIL'}]")

    c.close()


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    print("Prism API Server Verification")
    print("=" * 65)

    app = _patch_and_create_app()

    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for startup.
    for _ in range(30):
        try:
            httpx.get(f"{BASE}/api/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        print("ERROR: Server failed to start")
        return

    print(f"  Server running on port {PORT}")

    try:
        run_tests()
    finally:
        server.should_exit = True
        thread.join(timeout=3)

    print(f"\n{'='*65}")
    print("  All tests passed.")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
