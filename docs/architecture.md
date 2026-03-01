# Prism — Architecture

## System Overview

Prism is a personal risk intelligence tool that uses Synth's ensemble probabilistic forecasts (Bittensor Subnet 50) for probability exploration and position risk scanning.

## Data Flow

```
Synth API (SN50)
    │
    ▼
Collectors (scheduled jobs)
    │
    ▼
Supabase (persistent storage)
    │
    ▼
Risk Engine (probability explorer, position scanner)
    │
    ▼
Dashboard (visualization)
```

## Components

### Synth Client (`backend/synth_client.py`)
Typed wrapper around the Synth REST API. Handles authentication, retries, and response parsing for all insight, prediction, and leaderboard endpoints.

### Collectors (`backend/collectors/`)
Scheduled data collection jobs that poll Synth endpoints at configured intervals and persist results to Supabase. Each collector targets a specific data domain (predictions, polymarket odds, volatility, etc.).

### Models (`backend/models/`)
Pydantic data models for API responses, database schemas, and internal data structures.

## Supported Synth Endpoints

| Category | Endpoint | Assets |
|----------|----------|--------|
| Prediction Percentiles | `/insights/prediction-percentiles` | All |
| Polymarket Daily Up/Down | `/insights/polymarket/up-down/daily` | All |
| Polymarket Hourly Up/Down | `/insights/polymarket/up-down/hourly` | BTC, ETH, SOL |
| Polymarket 15min Up/Down | `/insights/polymarket/up-down/15min` | BTC, ETH, SOL |
| Polymarket Price Range | `/insights/polymarket/range` | BTC, ETH, SOL, NVDA, GOOGL, TSLA, AAPL |
| Volatility | `/insights/volatility` | All |
| Option Pricing | `/insights/option-pricing` | All except XAU |
| Liquidation | `/insights/liquidation` | All |
| LP Bounds | `/insights/lp-bounds` | All |
| LP Probabilities | `/insights/lp-probabilities` | All |
| Best Prediction | `/v2/prediction/best` | All (requires elevated API access) |
| Meta Leaderboard | `/v2/meta-leaderboard/latest` | N/A (requires elevated API access) |

> **Note:** The `/v2/prediction/*` and `/v2/meta-leaderboard/*` endpoints return 401 on the Pro API plan. They are retained in the client for completeness but are not used by the collector.
