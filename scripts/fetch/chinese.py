"""
Chinese LLM providers fetcher.

Most Chinese LLM APIs do not expose pricing via REST endpoints.
This module uses Playwright to scrape provider pricing pages.

Priority: each fetcher saves with its provider name so config.source_priority applies:
    zhipu=100, aliyun=100, baidu=100, moonshot=100
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult, FetcherConfig

logger = logging.getLogger(__name__)

# Per-million-token multiplier for prices given per thousand tokens
_PER_THOUSAND_TO_PER_MILLION = 1000

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available — Chinese provider fetchers will fail.")


def _run_playwright(url: str, timeout_ms: int = 45_000) -> Optional[str]:
    """
    Load a page with Playwright and return the rendered page text.
    Returns None if Playwright is unavailable or loading fails.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                locale="zh-CN",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            # Extra wait for React renders that happen after networkidle
            page.wait_for_timeout(2000)
            return page.inner_text("body")
        except Exception as e:
            logger.error(f"Playwright failed to load {url}: {e}")
            return None
        finally:
            browser.close()


class ZhipuFetcher(BaseFetcher):
    """
    Fetches Zhipu GLM pricing from https://open.bigmodel.cn/pricing.

    The page is a React SPA. We use Playwright to render it, then extract
    CNY prices from the visible text.

    Prices on the page are typically in CNY per thousand tokens — we convert
    to CNY per million tokens to match our standard format.
    """

    PRICING_URL = "https://open.bigmodel.cn/pricing"

    def __init__(self, config: Config):
        fetcher_config = FetcherConfig(
            name="zhipu",
            url=self.PRICING_URL,
            timeout=45.0,
            max_retries=2,
        )
        super().__init__(config, fetcher_config)

    # ------------------------------------------------------------------
    # BaseFetcher interface (not used — we override fetch() entirely)
    # ------------------------------------------------------------------

    def _make_request(self):
        return None

    def _validate_response(self, response) -> bool:
        return True

    def _parse_models(self, response) -> Dict[str, Any]:
        return {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def fetch(self) -> FetchResult:
        if not PLAYWRIGHT_AVAILABLE:
            return FetchResult.error_result("zhipu", "Playwright not available")

        logger.info(f"Scraping Zhipu pricing from {self.PRICING_URL}")
        page_text = _run_playwright(self.PRICING_URL)

        if page_text is None:
            return FetchResult.error_result("zhipu", "Playwright failed to load page")

        try:
            models = self._parse_page_text(page_text)
        except Exception as e:
            logger.exception("Zhipu pricing parse failed")
            return FetchResult.error_result("zhipu", f"Parse error: {e}")

        if not models:
            logger.warning("Zhipu: no models extracted from page")
            return FetchResult.error_result("zhipu", "No models found in page")

        logger.info(f"Zhipu: extracted {len(models)} models")
        return FetchResult(
            source="zhipu",
            success=True,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            models=models,
            models_count=len(models),
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_page_text(self, text: str) -> Dict[str, Any]:
        """
        Extract GLM model pricing from page text.

        bigmodel.cn shows a table with columns roughly:
            模型名称 | 输入价格 | 输出价格  (CNY per thousand tokens)

        We look for lines that contain a GLM model name followed by two prices.
        """
        models: Dict[str, Any] = {}

        # Patterns seen on bigmodel.cn pricing pages (flexible — tolerate whitespace):
        #   GLM-4-Flash   0.0001   0.0001
        #   GLM-4         0.1      0.1
        # Prices may be in formats: 0.1 / 0.0001 / 0.00001
        # Unit is CNY / thousand tokens on the page — multiply by 1000 for per-million.
        pattern = re.compile(
            r"(GLM[-\w]+)"           # model name
            r"[\s\S]{0,200}?"        # loose match for cells between name and prices
            r"([\d]+\.[\d]+)"        # input price (always has decimal)
            r"\s+"
            r"([\d]+\.[\d]+)",       # output price
            re.IGNORECASE,
        )

        seen_models = set()
        for m in pattern.finditer(text):
            raw_name = m.group(1).strip()
            input_per_k = float(m.group(2))
            output_per_k = float(m.group(3))

            model_id = raw_name.lower()
            if model_id in seen_models:
                continue
            seen_models.add(model_id)

            input_per_m = round(input_per_k * _PER_THOUSAND_TO_PER_MILLION, 6)
            output_per_m = round(output_per_k * _PER_THOUSAND_TO_PER_MILLION, 6)

            models[model_id] = {
                "pricing": {
                    "CNY": {
                        "input_price": input_per_m,
                        "output_price": output_per_m,
                    }
                },
                "metadata": {
                    "provider": "zhipu",
                    "family": "glm",
                },
            }
            logger.debug(
                f"Zhipu: {model_id} CNY input={input_per_m} output={output_per_m} /MTok"
            )

        return models
