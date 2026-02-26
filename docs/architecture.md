# Forked — Architecture

## System Overview

Forked is a prediction markets intelligence platform that identifies mispriced contracts on Polymarket by comparing live market odds against Synth's ensemble probabilistic forecasts.

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
Analysis Engines (edge detection, signal scoring)
    │
    ▼
Dashboard (real-time visualization)
```

## Components

### Synth Client (`backend/synth_client.py`)
Typed wrapper around the Synth REST API. Handles authentication, retries, and response parsing for all insight, prediction, and leaderboard endpoints.

### Collectors (`backend/collectors/`)
Scheduled data collection jobs that poll Synth endpoints at configured intervals and persist results to Supabase. Each collector targets a specific data domain (predictions, polymarket odds, volatility, etc.).

### Analysis Engines (`backend/analysis/`)
Statistical analysis modules that process collected data to identify actionable edge:
- **Edge Detector**: Compares Synth fair probabilities against Polymarket odds to find divergences
- **Signal Scorer**: Ranks opportunities by expected value and confidence

### Models (`backend/models/`)
Pydantic data models for API responses, database schemas, and internal data structures.

### Frontend (`frontend/`)
Real-time dashboard for monitoring detected edges, market state, and system health.

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
| Best Prediction | `/v2/prediction/best` | All |
| Meta Leaderboard | `/v2/meta-leaderboard/latest` | N/A |
