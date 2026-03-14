"""Entry point: python -m backend.api.run

Starts the Prism API server on the configured port.
"""

from __future__ import annotations

import logging
import os
import sys

import uvicorn
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    port = int(os.getenv("API_PORT", "8000"))
    log_level = os.getenv("API_LOG_LEVEL", "info").lower()

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s  %(name)-18s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("prism.api")

    # Check for API key early.
    api_key = os.getenv("SYNTH_API_KEY", "")
    if not api_key:
        logger.warning("SYNTH_API_KEY is not set — Synth endpoints will fail")

    logger.info("Starting Prism API on port %d", port)
    logger.info("Docs: http://localhost:%d/docs", port)

    uvicorn.run(
        "backend.api.server:create_app",
        factory=True,
        host="0.0.0.0",
        port=port,
        log_level=log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()
