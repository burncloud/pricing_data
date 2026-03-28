"""
Orchestrator: run all enabled fetchers and save results to sources/{date}/.

Usage:
    python scripts/fetch_all.py 2026-03-28
    python scripts/fetch_all.py          # defaults to today
"""
import logging
import sys
from datetime import date
from typing import Optional

from scripts.config import config
from scripts.fetch.litellm import LiteLLMFetcher
from scripts.fetch.openrouter import OpenRouterFetcher

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def fetch_all(date_str: Optional[str] = None) -> int:
    """
    Run all fetchers and save results.

    Returns:
        0 if all fetchers succeeded, 1 if any fetcher failed (but still saves others).
    """
    if date_str is None:
        date_str = date.today().isoformat()

    fetchers = [
        OpenRouterFetcher(config),
        LiteLLMFetcher(config),
    ]

    any_failed = False
    for fetcher in fetchers:
        name = fetcher.fetcher_config.name
        try:
            logger.info(f"Running {name} fetcher...")
            result = fetcher.fetch()
            fetcher.save_result(result, date_str)

            if result.success:
                print(f"✅ {name}: {result.models_count} models")
            else:
                print(f"⚠️  {name}: fetch failed — {result.error}")
                any_failed = True

        except Exception as e:
            logger.exception(f"Unexpected error running {name} fetcher")
            print(f"❌ {name}: unexpected error — {e}")
            any_failed = True

    return 1 if any_failed else 0


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(fetch_all(date_arg))
