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
from scripts.fetch.aliyun import AliyunFetcher
from scripts.fetch.anthropic import AnthropicFetcher
from scripts.fetch.baidu import BaiduFetcher
from scripts.fetch.chinese import ZhipuFetcher
from scripts.fetch.cohere import CohereFetcher
from scripts.fetch.deepseek import DeepSeekFetcher
from scripts.fetch.google import GoogleFetcher
from scripts.fetch.litellm import LiteLLMFetcher
from scripts.fetch.manual_overrides import ManualOverridesFetcher
from scripts.fetch.minimax import MiniMaxFetcher
from scripts.fetch.mistral import MistralFetcher
from scripts.fetch.moonshot import MoonshotFetcher
from scripts.fetch.openai import OpenAIFetcher
from scripts.fetch.openrouter import OpenRouterFetcher
from scripts.fetch.xai import XAIFetcher

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def fetch_all(date_str: Optional[str] = None) -> int:
    """
    Run all fetchers and save results.

    Returns:
        Always 0 — partial fetcher failures are acceptable (logged as ⚠️/❌).
        The merge step is the real quality gate. Individual fetcher errors
        should not block the pipeline when other fetchers succeeded.
    """
    if date_str is None:
        date_str = date.today().isoformat()

    fetchers = [
        ManualOverridesFetcher(config),  # priority 200, human-verified (local file)
        OpenAIFetcher(config),           # priority 100, curl_cffi
        AnthropicFetcher(config),        # priority 100, plain HTTP
        GoogleFetcher(config),           # priority 100, plain HTTP
        DeepSeekFetcher(config),         # priority 100, plain HTTP
        ZhipuFetcher(config),            # priority 100, Playwright (bigmodel.cn CNY)
        XAIFetcher(config),              # priority 100, plain HTTP
        AliyunFetcher(config),           # priority 100, plain HTTP (USD)
        MistralFetcher(config),          # priority 100, curl_cffi
        CohereFetcher(config),           # priority 100, plain HTTP
        MoonshotFetcher(config),         # priority 100, plain HTTP (CNY)
        BaiduFetcher(config),            # priority 100, plain HTTP (CNY)
        MiniMaxFetcher(config),          # priority 100, plain HTTP
        OpenRouterFetcher(config),       # priority 50
        LiteLLMFetcher(config),          # priority 70
    ]

    failed_fetchers = []
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
                failed_fetchers.append(name)

        except Exception as e:
            logger.exception(f"Unexpected error running {name} fetcher")
            print(f"❌ {name}: unexpected error — {e}")
            failed_fetchers.append(name)

    if failed_fetchers:
        print(f"\n⚠️  {len(failed_fetchers)} fetcher(s) failed: {', '.join(failed_fetchers)}")
        print("Continuing — merge step will use all available sources.")

    return 0


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(fetch_all(date_arg))
