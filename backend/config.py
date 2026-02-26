import os
from dotenv import load_dotenv

load_dotenv()

SYNTH_BASE_URL: str = "https://api.synthdata.co"
SYNTH_API_KEY: str = os.getenv("SYNTH_API_KEY", "")

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

ASSETS: list[str] = ["BTC", "ETH", "SOL", "XAU", "SPY", "NVDA", "GOOGL", "TSLA", "AAPL"]

# Assets that use suffixed symbols in prediction endpoints (equities/indices)
PREDICTION_ASSET_MAP: dict[str, str] = {
    "BTC": "BTC",
    "ETH": "ETH",
    "XAU": "XAU",
    "SOL": "SOL",
    "SPY": "SPYX",
    "NVDA": "NVDAX",
    "GOOGL": "GOOGLX",
    "TSLA": "TSLAX",
    "AAPL": "AAPLX",
}

HORIZONS: list[str] = ["1h", "24h"]

# ── Per-endpoint asset support ────────────────────────────────────────
# Only call endpoints for assets that actually support them.

# 1h percentiles: crypto + gold only (equities return 400 "Invalid asset")
PERCENTILES_1H_ASSETS: list[str] = ["BTC", "ETH", "SOL", "XAU"]

# Polymarket daily up/down: all except XAU and TSLA (404 "no polymarket data")
POLYMARKET_DAILY_ASSETS: list[str] = ["BTC", "ETH", "SOL", "SPY", "NVDA", "GOOGL", "AAPL"]

# Polymarket hourly/15min: crypto only
POLYMARKET_SHORT_TERM_ASSETS: list[str] = ["BTC", "ETH", "SOL"]

# Polymarket range contracts
POLYMARKET_RANGE_ASSETS: list[str] = ["BTC", "ETH", "SOL", "NVDA", "GOOGL", "TSLA", "AAPL"]

# Option pricing excludes XAU and JITOSOL
OPTION_PRICING_ASSETS: list[str] = ["BTC", "ETH", "SOL", "SPY", "NVDA", "GOOGL", "TSLA", "AAPL"]

# Default parameters for leaderboard/prediction queries
DEFAULT_DAYS: int = 14
DEFAULT_MINER_LIMIT: int = 10

# AlphaLog collection interval in seconds
ALPHALOG_INTERVAL: int = int(os.getenv("ALPHALOG_INTERVAL", "3600"))
