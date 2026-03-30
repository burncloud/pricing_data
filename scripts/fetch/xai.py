"""
xAI Grok official pricing fetcher.

Scrapes https://docs.x.ai/docs/models which embeds model pricing as escaped JSON
inside the Next.js page HTML. The format for each model looks like:

  LanguageModel\\",...\\"name\\":\\"grok-3\\",...
  \\"promptTextTokenPrice\\":\\"$n30000\\",...
  \\"cachedPromptTokenPrice\\":\\"$n7500\\",...
  \\"completionTextTokenPrice\\":\\"$n150000\\",...

Prices use nanocents/token: divide by 1000 to get USD/MTok.

Only text/language models (grok-*) with input+output pricing are captured.
"""
import logging
import re
from typing import Any, Dict, Optional

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Patterns for escaped JSON within the Next.js page source
_NAME_RE = re.compile(r'\\"name\\":\\"(grok-[\w.-]+)\\"')
_INPUT_RE = re.compile(r'\\"promptTextTokenPrice\\":\\"\$n(\d+)\\"')
_OUTPUT_RE = re.compile(r'\\"completionTextTokenPrice\\":\\"\$n(\d+)\\"')
_CACHE_RE = re.compile(r'\\"cachedPromptTokenPrice\\":\\"\$n(\d+)\\"')


def _nanocents_to_mtok(value: str) -> float:
    """Convert '$nXXXX' nanocents/token to USD/MTok. E.g. '3000' → 3.00."""
    return int(value) / 1000.0


class XAIFetcher(BaseFetcher):
    """
    Fetches xAI Grok model pricing from https://docs.x.ai/docs/models.

    Uses plain HTTP GET — no Playwright required. Priority 100.
    Captures text models only (grok-* with input+output token pricing).
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["xai"]
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
        if "grok-" not in response.text.lower():
            logger.error("xAI: no 'grok-' model names found on pricing page")
            return False
        if "promptTextTokenPrice" not in response.text:
            logger.error("xAI: no token pricing JSON found on page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text
        models: Dict[str, Any] = {}

        # Each LanguageModel block is ~800 chars. Scan 1500 chars from each marker.
        for m in re.finditer(r"LanguageModel", html):
            block = html[m.start(): m.start() + 1500]
            entry = self._parse_block(block)
            if entry is not None:
                model_id, model_data = entry
                if model_id not in models:
                    models[model_id] = model_data
                    logger.debug(f"xAI: parsed {model_id}")

        logger.info(f"xAI: scraped {len(models)} models")
        return models

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_block(self, block: str) -> Optional[tuple]:
        """Extract (model_id, model_entry) from one LanguageModel JSON block."""
        name_m = _NAME_RE.search(block)
        inp_m = _INPUT_RE.search(block)
        out_m = _OUTPUT_RE.search(block)

        if not name_m or not inp_m or not out_m:
            return None

        model_id = name_m.group(1).lower()
        input_price = _nanocents_to_mtok(inp_m.group(1))
        output_price = _nanocents_to_mtok(out_m.group(1))

        cache_m = _CACHE_RE.search(block)
        cache_price = _nanocents_to_mtok(cache_m.group(1)) if cache_m else None

        metadata = {"provider": "xai", "family": self._extract_family(model_id)}
        cache_pricing = {"read": cache_price} if cache_price is not None else None
        endpoint_entry = self._build_endpoint_entry(
            {"in": input_price, "out": output_price},
            cache_pricing=cache_pricing,
        )
        return model_id, self._build_model_entry(endpoint_entry, metadata)

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """'grok-4.20-0309-reasoning' → 'grok-4.20', 'grok-4-1-fast' → 'grok-4'"""
        base = re.sub(
            r"-(reasoning|non-reasoning|fast|multi-agent|thinking|turbo).*$",
            "",
            model_id,
        )
        return base
