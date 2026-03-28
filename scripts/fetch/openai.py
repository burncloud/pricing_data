"""
OpenAI official pricing page fetcher (Playwright).

Scrapes https://openai.com/api/pricing which is protected by Cloudflare
and requires a real browser to load. Falls back gracefully when Playwright
is not installed.

NOTE: This page shows flagship models only (~7 currently). It does NOT
cover the full OpenAI model catalog (gpt-4o, o1, o3-mini, etc.).
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

# Matches "Input:\n$2.50 / 1M tokens" or "Cached input:\n$0.25 / 1M tokens"
# <br> tags in the DOM render as \n in textContent.
# [^\n:]+ — any chars except newline and colon (prevents greedy cross-line capture)
_PRICE_RE = re.compile(
    r"^([^\n:]+):\s*\n\s*\$([0-9,]+(?:\.[0-9]+)?)\s*/\s*1M\s+tokens",
    re.MULTILINE | re.IGNORECASE,
)


class OpenAIFetcher(BaseFetcher):
    """
    Fetches pricing from https://openai.com/api/pricing using Playwright.

    Cloudflare blocks plain HTTP requests, so we launch a headless Chromium
    browser to execute JS and pass the bot challenge.

    Priority 100 — direct provider tier, same as other first-party fetchers.
    Only flagship models visible on the page are captured.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["openai"]
        super().__init__(config, fetcher_config)

    # ------------------------------------------------------------------
    # Override fetch() — Playwright doesn't fit the requests.Response interface
    # ------------------------------------------------------------------

    def fetch(self) -> FetchResult:
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            logger.warning("Playwright not installed — skipping OpenAI scraper")
            return FetchResult.error_result(
                self.fetcher_config.name,
                "Playwright not installed. Run: pip install playwright && playwright install chromium",
            )

        try:
            models = self._scrape_with_playwright()
        except Exception as e:
            logger.exception("OpenAI Playwright scrape failed")
            return FetchResult.error_result(self.fetcher_config.name, str(e))

        if not models:
            return FetchResult.error_result(
                self.fetcher_config.name,
                "No models parsed from OpenAI pricing page",
            )

        return FetchResult(
            source=self.fetcher_config.name,
            success=True,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            models=models,
            models_count=len(models),
        )

    def _scrape_with_playwright(self) -> Dict[str, Any]:
        """Launch Chromium, load pricing page, return parsed models dict."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(
                    self.fetcher_config.url,
                    wait_until="domcontentloaded",
                    timeout=int(self.fetcher_config.timeout * 1000),
                )
                # Wait for price content to render
                page.wait_for_selector("text=/1M tokens/", timeout=30_000)

                # Extract model cards via JS to avoid ElementHandle juggling
                raw_cards: List[Dict[str, str]] = page.evaluate(
                    """
                    () => {
                        const results = [];
                        const headings = document.querySelectorAll('h2.text-h4');
                        for (const h2 of headings) {
                            const card = h2.closest('[class*="border"]') || h2.parentElement;
                            if (!card) continue;
                            results.push({
                                name: h2.textContent.trim(),
                                cardText: card.textContent || '',
                            });
                        }
                        return results;
                    }
                    """
                )
            finally:
                browser.close()

        models: Dict[str, Any] = {}
        for card in raw_cards:
            display_name = card.get("name", "").strip()
            card_text = card.get("cardText", "")
            if not display_name:
                continue

            entry = self._parse_model_card(display_name, card_text)
            if entry is not None:
                model_id = self._normalize_display_name(display_name)
                models[model_id] = entry
                logger.debug(f"OpenAI: parsed {display_name!r} → {model_id!r}")

        logger.info(f"OpenAI: scraped {len(models)} models")
        return models

    # ------------------------------------------------------------------
    # Parsing helpers (pure functions, easy to unit-test)
    # ------------------------------------------------------------------

    def _parse_model_card(
        self, display_name: str, card_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract pricing from a model card's text content.

        Returns None if input/output prices cannot be found (e.g. image or
        audio-only models where pricing is not in $/1M token format).
        """
        prices: Dict[str, float] = {}
        for match in _PRICE_RE.finditer(card_text):
            label = match.group(1).strip().lower()
            value = float(match.group(2).replace(",", ""))
            prices[label] = value

        input_price = prices.get("input")
        output_price = prices.get("output")

        if input_price is None or output_price is None:
            logger.debug(
                f"OpenAI: no $/1M input+output for {display_name!r} — skipping "
                f"(found labels: {list(prices)})"
            )
            return None

        model: Dict[str, Any] = {
            "pricing": {
                "USD": {
                    "input_price": input_price,
                    "output_price": output_price,
                }
            },
            "metadata": {
                "provider": "openai",
                "family": self._extract_family(display_name),
            },
        }

        # Prompt caching
        cached_price = prices.get("cached input")
        if cached_price is not None:
            model["cache_pricing"] = {
                "USD": {
                    "cache_read_input_price": cached_price,
                }
            }

        return model

    @staticmethod
    def _normalize_display_name(display_name: str) -> str:
        """
        Convert OpenAI display name to a lowercase kebab-case model ID.

        'GPT-4o' → 'gpt-4o'
        'GPT-4o mini' → 'gpt-4o-mini'
        'o3-mini' → 'o3-mini'
        """
        name = display_name.lower().strip()
        # Collapse whitespace to hyphens
        name = re.sub(r"\s+", "-", name)
        # Strip leading/trailing hyphens
        name = name.strip("-")
        return name

    @staticmethod
    def _extract_family(display_name: str) -> str:
        """
        Best-effort model family from display name.

        'GPT-4o mini' → 'gpt-4o'
        'GPT-4o' → 'gpt-4o'
        'o3-mini' → 'o3'
        """
        name = display_name.lower().strip()
        # Split on spaces; keep hyphenated tokens whole
        parts = name.split()
        # Family = first token (e.g. "gpt-4o", "o3-mini" → "o3")
        if not parts:
            return "openai"
        first = parts[0]
        # Strip qualifier suffixes like "-mini", "-nano" from the family name
        family = re.sub(r"-(mini|nano|micro|small|large|pro|plus)$", "", first)
        return family

    # ------------------------------------------------------------------
    # BaseFetcher abstract stubs (not used — fetch() is overridden above)
    # ------------------------------------------------------------------

    def _make_request(self):  # type: ignore[override]
        raise NotImplementedError("OpenAIFetcher overrides fetch() directly")

    def _validate_response(self, response) -> bool:  # type: ignore[override]
        raise NotImplementedError("OpenAIFetcher overrides fetch() directly")

    def _parse_models(self, response) -> Dict[str, Any]:  # type: ignore[override]
        raise NotImplementedError("OpenAIFetcher overrides fetch() directly")
