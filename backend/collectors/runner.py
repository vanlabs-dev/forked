"""AlphaLog runner — entry point for continuous data collection.

Usage:
    python -m backend.collectors.runner          # Run continuously (default: every 3600s)
    python -m backend.collectors.runner --once    # Single collection then exit
    python -m backend.collectors.runner --interval 1800  # Custom interval
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.collectors.alphalog import AlphaLogCollector
from backend.config import ALPHALOG_INTERVAL, ASSETS, SYNTH_BASE_URL
from backend.synth_client import SynthClient

__version__ = "0.1.0"

_shutdown_requested = False


def _handle_signal(signum: int, _frame: object) -> None:
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logging.getLogger("alphalog").info("Received %s — finishing current cycle then exiting", sig_name)
    _shutdown_requested = True


def _setup_logging() -> logging.Logger:
    """Configure logging to both console and rotating file."""
    logger = logging.getLogger("alphalog")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "alphalog.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaLog — Synth API data collector")
    parser.add_argument("--once", action="store_true", help="Collect once and exit")
    parser.add_argument("--interval", type=int, default=ALPHALOG_INTERVAL, help="Seconds between collections")
    args = parser.parse_args()

    logger = _setup_logging()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    client = SynthClient()
    collector = AlphaLogCollector(client)

    logger.info(
        "AlphaLog v%s starting — interval=%ds, assets=%d, api=%s",
        __version__,
        args.interval,
        len(ASSETS),
        SYNTH_BASE_URL,
    )

    if args.once:
        collector.run_once()
        return

    # Continuous mode
    while not _shutdown_requested:
        try:
            collector.run_once()
        except Exception:
            logger.exception("Collection cycle failed — will retry next cycle")

        if _shutdown_requested:
            break

        logger.info("Next collection in %ds", args.interval)

        # Sleep in small increments to catch shutdown signals promptly
        slept = 0
        while slept < args.interval and not _shutdown_requested:
            time.sleep(min(5, args.interval - slept))
            slept += 5

    logger.info("AlphaLog stopped cleanly")


if __name__ == "__main__":
    main()
