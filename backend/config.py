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

# Polymarket subset: only these assets have hourly/15min contracts
POLYMARKET_SHORT_TERM_ASSETS: list[str] = ["BTC", "ETH", "SOL"]

# Option pricing excludes XAU and JITOSOL
OPTION_PRICING_ASSETS: list[str] = ["BTC", "ETH", "SOL", "SPY", "NVDA", "GOOGL", "TSLA", "AAPL"]

# Polymarket range contracts
POLYMARKET_RANGE_ASSETS: list[str] = ["BTC", "ETH", "SOL", "NVDA", "GOOGL", "TSLA", "AAPL"]

# Default parameters for leaderboard/prediction queries
DEFAULT_DAYS: int = 14
DEFAULT_MINER_LIMIT: int = 10

# AlphaLog collection interval in seconds
ALPHALOG_INTERVAL: int = int(os.getenv("ALPHALOG_INTERVAL", "3600"))
