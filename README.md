# Forked

> Where probability paths diverge, edge emerges.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Synth API](https://img.shields.io/badge/Synth-SN50-purple)

**Prediction markets intelligence tool leveraging Synth's probabilistic price forecasts to find actionable edges in Polymarket.**

Built for the [Synth Predictive Intelligence Hackathon](https://www.synthdata.co/) (Feb–Mar 2026) in the **Best Prediction Markets Tool** category.

---

## Overview

Forked consumes ensemble probabilistic forecasts from the Synth API (Bittensor Subnet 50) and compares them against live Polymarket odds to surface mispriced contracts. The system continuously monitors price distributions, computes fair probabilities, and identifies statistically significant divergences that represent tradable edge.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/vanlabs-dev/forked.git
cd forked

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Verify API access
python scripts/verify_api.py
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full system design.

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Synth API   │────▶│  Collectors   │────▶│   Supabase   │
│  (SN50)      │     │              │     │   (Storage)  │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                    ┌──────────────┐             │
                    │   Analysis   │◀────────────┘
                    │   Engines    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Dashboard   │
                    │  (Frontend)  │
                    └──────────────┘
```

## Supported Assets

BTC, ETH, SOL, XAU, SPY, NVDA, GOOGL, TSLA, AAPL

## Links

- [Synth API Docs](https://docs.synthdata.co)
- [Synth Platform](https://www.synthdata.co/)
- [Bittensor Subnet 50](https://github.com/mode-network/synth-subnet)

## License

MIT — see [LICENSE](LICENSE) for details.
