"""
Chinese LLM providers fetcher.

Note: Most Chinese LLM APIs do NOT expose pricing via API endpoints.
This module uses web scraping with Playwright to extract pricing from provider websites.

If Playwright is not available, falls back to cached data.
"""
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult, FetcherConfig

logger = logging.getLogger(__name__)

# Try to import Playwright, but gracefully degrade if unavailable
try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Chinese providers will use cached data.")


@dataclass
class ScrapedPricing:
    """Scraped pricing data from a provider website."""
    model_id: str
    input_price: float
    output_price: float
    currency: str = "CNY"
    unit: str = "per_thousand_tokens"
    source_url: str = ""


class ChineseProviderScraper(ABC):
    """Base class for Chinese provider web scrapers."""

    def __init__(self, provider_name: str, pricing_url: str):
        self.provider_name = provider_name
        self.pricing_url = pricing_url

    @abstractmethod
    def scrape(self, page: "Page") -> List[ScrapedPricing]:
        """Scrape pricing data from the provider's pricing page."""
        pass


class ZhipuScraper(ChineseProviderScraper):
    """Zhipu GLM pricing scraper."""

    def __init__(self):
        super().__init__("zhipu", "https://open.bigmodel.cn/pricing")

    def scrape(self, page: "Page") -> List[ScrapedPricing]:
        """Scrape Zhipu pricing page."""
        results = []

        try:
            page.goto(self.pricing_url, wait_until="networkidle", timeout=30000)

            # Wait for pricing table to load
            page.wait_for_selector("table, .pricing-table, [class*='price']", timeout=10000)

            # Extract pricing data from the page
            # Note: Actual selectors depend on Zhipu's page structure
            # This is a template that needs adjustment based on real page structure

            pricing_elements = page.query_selector_all("tr, .pricing-row, [class*='model-row']")

            for element in pricing_elements:
                try:
                    text = element.inner_text()
                    # Parse model name and prices from text
                    # Example: "GLM-4 0.1 0.1" (model, input, output per 1K tokens)
                    match = re.search(r"(GLM-[\w-]+)\s+([\d.]+)\s+([\d.]+)", text)
                    if match:
                        results.append(ScrapedPricing(
                            model_id=match.group(1).lower(),
                            input_price=float(match.group(2)),
                            output_price=float(match.group(3)),
                            currency="CNY",
                            source_url=self.pricing_url,
                        ))
                except Exception as e:
                    logger.debug(f"Failed to parse element: {e}")
                    continue

        except Exception as e:
            logger.error(f"Zhipu scraping failed: {e}")

        return results


class AliyunScraper(ChineseProviderScraper):
    """Aliyun Qwen pricing scraper."""

    def __init__(self):
        super().__init__("aliyun", "https://help.aliyun.com/zh/dashscope/developer-reference/billing")

    def scrape(self, page: "Page") -> List[ScrapedPricing]:
        """Scrape Aliyun pricing page."""
        results = []

        try:
            page.goto(self.pricing_url, wait_until="networkidle", timeout=30000)
            page.wait_for_selector("table, .pricing, [class*='price']", timeout=10000)

            # Aliyun typically has tables with model names and prices
            tables = page.query_selector_all("table")

            for table in tables:
                rows = table.query_selector_all("tr")
                for row in rows[1:]:  # Skip header
                    try:
                        cells = row.query_selector_all("td")
                        if len(cells) >= 3:
                            model_text = cells[0].inner_text()
                            # Extract model name (qwen-max, qwen-plus, etc.)
                            model_match = re.search(r"(qwen-[\w-]+)", model_text, re.IGNORECASE)
                            if model_match:
                                # Prices are usually in format "¥X.XX/千tokens"
                                input_price = self._parse_price(cells[1].inner_text())
                                output_price = self._parse_price(cells[2].inner_text()) if len(cells) > 2 else input_price

                                if input_price:
                                    results.append(ScrapedPricing(
                                        model_id=model_match.group(1).lower(),
                                        input_price=input_price,
                                        output_price=output_price or input_price,
                                        currency="CNY",
                                        source_url=self.pricing_url,
                                    ))
                    except Exception as e:
                        logger.debug(f"Failed to parse row: {e}")
                        continue

        except Exception as e:
            logger.error(f"Aliyun scraping failed: {e}")

        return results

    def _parse_price(self, text: str) -> Optional[float]:
        """Parse price from text like '¥0.04/千tokens' or '0.04'. """
        match = re.search(r"[\d.]+", text.replace("¥", ""))
        if match:
            return float(match.group())
        return None


class BaiduScraper(ChineseProviderScraper):
    """Baidu ERNIE pricing scraper."""

    def __init__(self):
        super().__init__("baidu", "https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Blfmc9dlf")

    def scrape(self, page: "Page") -> List[ScrapedPricing]:
        """Scrape Baidu pricing page."""
        results = []

        try:
            page.goto(self.pricing_url, wait_until="networkidle", timeout=30000)
            page.wait_for_selector("table, .pricing-table", timeout=10000)

            tables = page.query_selector_all("table")

            for table in tables:
                rows = table.query_selector_all("tr")
                for row in rows[1:]:
                    try:
                        text = row.inner_text()
                        # Baidu format: "ERNIE-4.0-8K 0.12 0.12"
                        match = re.search(r"(ERNIE-[\w.-]+)\s+([\d.]+)\s+([\d.]+)", text)
                        if match:
                            results.append(ScrapedPricing(
                                model_id=match.group(1).lower().replace("ernie-", ""),
                                input_price=float(match.group(2)),
                                output_price=float(match.group(3)),
                                currency="CNY",
                                source_url=self.pricing_url,
                            ))
                    except Exception as e:
                        logger.debug(f"Failed to parse row: {e}")
                        continue

        except Exception as e:
            logger.error(f"Baidu scraping failed: {e}")

        return results


class MoonshotScraper(ChineseProviderScraper):
    """Moonshot Kimi pricing scraper."""

    def __init__(self):
        super().__init__("moonshot", "https://platform.moonshot.cn/docs/pricing")

    def scrape(self, page: "Page") -> List[ScrapedPricing]:
        """Scrape Moonshot pricing page."""
        results = []

        try:
            page.goto(self.pricing_url, wait_until="networkidle", timeout=30000)
            page.wait_for_selector("table, .pricing", timeout=10000)

            text = page.content()
            # Moonshot format: "moonshot-v1-8k: 0.012/千tokens"
            matches = re.findall(r"(moonshot-v1-\d+k).*?([\d.]+)/千", text)
            for model_id, price in matches:
                results.append(ScrapedPricing(
                    model_id=model_id.lower(),
                    input_price=float(price),
                    output_price=float(price),
                    currency="CNY",
                    source_url=self.pricing_url,
                ))

        except Exception as e:
            logger.error(f"Moonshot scraping failed: {e}")

        return results


class ChineseFetcher(BaseFetcher):
    """
    Fetches pricing data from Chinese LLM providers via web scraping.

    Falls back to cached data if Playwright is unavailable.
    """

    SCRAPERS = [
        ZhipuScraper,
        AliyunScraper,
        BaiduScraper,
        MoonshotScraper,
    ]

    def __init__(self, config: Config, provider: str = "all"):
        self.provider = provider
        fetcher_config = FetcherConfig(
            name=f"chinese-{provider}",
            url="",  # URL varies by scraper
            timeout=30.0,
            max_retries=2,
        )
        super().__init__(config, fetcher_config)

    def _make_request(self) -> Optional[requests.Response]:
        """Not used for web scraping fetchers."""
        return None

    def _validate_response(self, response: requests.Response) -> bool:
        """Not used for web scraping fetchers."""
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        """Not used for web scraping fetchers."""
        return {}

    def fetch(self) -> FetchResult:
        """Fetch pricing data from Chinese providers."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, returning cached data")
            return self._get_cached_result()

        all_models = {}
        errors = []

        for scraper_class in self.SCRAPERS:
            scraper = scraper_class()

            if self.provider != "all" and scraper.provider_name != self.provider:
                continue

            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()

                    # Set reasonable timeout and wait for page load
                    page.set_default_timeout(30000)

                    scraped = scraper.scrape(page)

                    browser.close()

                    for item in scraped:
                        all_models[item.model_id] = {
                            "pricing": {
                                item.currency: {
                                    "input_price": item.input_price,
                                    "output_price": item.output_price,
                                    "unit": item.unit,
                                    "source": scraper.provider_name,
                                }
                            },
                            "metadata": {
                                "provider": scraper.provider_name,
                                "family": self._extract_family(item.model_id),
                                "source_url": item.source_url,
                            }
                        }

                    logger.info(f"Scraped {len(scraped)} models from {scraper.provider_name}")

            except Exception as e:
                error_msg = f"{scraper.provider_name} scraping failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        if not all_models and errors:
            return FetchResult.error_result(
                "chinese",
                "; ".join(errors)
            )

        return FetchResult(
            source="chinese",
            success=True,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            models=all_models,
            models_count=len(all_models),
        )

    def _get_cached_result(self) -> FetchResult:
        """Get cached result when Playwright is unavailable."""
        # Look for the most recent cached data
        from datetime import date, timedelta

        for days_ago in range(7):
            check_date = (date.today() - timedelta(days=days_ago)).isoformat()
            cached = self.load_cached_result(check_date)
            if cached and cached.success:
                logger.info(f"Using cached Chinese data from {check_date}")
                return cached

        return FetchResult.error_result(
            "chinese",
            "Playwright unavailable and no cached data found"
        )

    def _extract_family(self, model_id: str) -> str:
        """Extract model family from ID."""
        if model_id.startswith("qwen"):
            return "qwen"
        elif model_id.startswith("glm"):
            return "glm"
        elif model_id.startswith("ernie"):
            return "ernie"
        elif model_id.startswith("moonshot"):
            return "moonshot"
        return model_id.split("-")[0]
