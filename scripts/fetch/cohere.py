"""
Cohere official pricing fetcher.

Scrapes https://cohere.com/pricing which lists Command R/R+ models with
per-million-token pricing in format "$X.XX/1M input tokens".

Only text models with explicit input+output pricing are captured.
Embed/Rerank models use per-hour billing and are skipped.
"""
import logging
import re
from typing import Any, Dict, Optional

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Matches model name heading and following input/output prices on same or adjacent lines.
# Page format: "Command R 03-2024\n$0.50/1M input tokens, $1.50/1M output tokens"
_PRICE_BLOCK_RE = re.compile(
    r"(command[\w\s.+-]*?)\s*\n.*?"
    r"\$([0-9]+(?:\.[0-9]+)?)/1M\s+input\s+tokens?.*?"
    r"\$([0-9]+(?:\.[0-9]+)?)/1M\s+output\s+tokens?",
    re.IGNORECASE | re.DOTALL,
)

# Matches Cohere model name headings (Command, Command R, Command R+, Command Light, etc.)
# Does NOT match mid-sentence phrases like "Command pricing is..."
_MODEL_NAME_RE = re.compile(
    r"\b(Command(?:\s+(?:R\+?|Light|Nightly|A))?(?:\s+\d{2}-\d{4})?)\b",
    re.IGNORECASE,
)
_DOLLAR_RE = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)")


def _normalize_model_id(name: str) -> str:
    """
    'Command R 03-2024' → 'command-r-03-2024'
    'Command R+ 04-2024' → 'command-r-plus-04-2024'
    'Command' → 'command'
    """
    name = name.strip().lower()
    name = re.sub(r"\s+", "-", name)
    name = name.replace("+", "-plus")
    name = re.sub(r"-{2,}", "-", name)
    return name.strip("-")


class CohereFetcher(BaseFetcher):
    """
    Fetches Cohere Command model pricing from https://cohere.com/pricing.

    Uses plain HTTP GET — no Playwright required. Priority 100.
    Captures Command text models only (token-priced, not hourly).
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["cohere"]
        super().__init__(config, fetcher_config)

    # ------------------------------------------------------------------
    # BaseFetcher interface
    # ------------------------------------------------------------------

    def _make_request(self) -> requests.Response:
        resp = self.session.get(
            self.fetcher_config.url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; burncloud-pricing-bot/1.0)",
                "Accept": "text/html",
            },
            timeout=self.fetcher_config.timeout,
        )
        resp.raise_for_status()
        return resp

    def _validate_response(self, response: requests.Response) -> bool:
        text = response.text.lower()
        if "command" not in text:
            logger.error("Cohere: 'command' not found on pricing page")
            return False
        if not _DOLLAR_RE.search(response.text):
            logger.error("Cohere: no dollar prices found on page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text
        # Strip HTML tags to get plain text for pattern matching
        plain = re.sub(r"<[^>]+>", " ", html)
        plain = re.sub(r"&nbsp;", " ", plain)
        plain = re.sub(r"&amp;", "&", plain)
        plain = re.sub(r"\s+", " ", plain)

        models = self._extract_from_text(plain)
        logger.info(f"Cohere: scraped {len(models)} models")
        return models

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Scan text for Command model pricing blocks.

        Looks for patterns near "Command" model names and extracts
        the first two dollar amounts as input/output prices.
        """
        models: Dict[str, Any] = {}

        # Find all Command model mention positions
        for name_match in _MODEL_NAME_RE.finditer(text):
            raw_name = name_match.group(1).strip()
            # Skip very short spurious matches
            if len(raw_name) < 5:
                continue

            model_id = _normalize_model_id(raw_name)
            if model_id in models:
                continue

            # Look for prices in the next 300 characters after the model name
            window = text[name_match.start(): name_match.start() + 300]
            prices = [float(m.group(1)) for m in _DOLLAR_RE.finditer(window)]

            if len(prices) < 2:
                continue

            input_price = prices[0]
            output_price = prices[1]

            metadata = {"provider": "cohere", "family": self._extract_family(model_id)}
            endpoint_entry = self._build_endpoint_entry(
                {"in": input_price, "out": output_price},
            )
            models[model_id] = self._build_model_entry(endpoint_entry, metadata)
            logger.debug(f"Cohere: parsed {model_id} in=${input_price} out=${output_price}")

        return models

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """'command-r-plus-04-2024' → 'command-r-plus', 'command' → 'command'"""
        # Remove date suffix (-MM-YYYY or -YYYY)
        base = re.sub(r"-\d{2}-\d{4}$", "", model_id)
        base = re.sub(r"-\d{4}$", "", base)
        return base
