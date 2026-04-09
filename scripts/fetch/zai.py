"""
Z.AI international pricing fetcher.

Fetches official USD pricing from https://docs.z.ai/guides/overview/pricing.
This is Zhipu's international docs site (Mintlify-rendered static HTML).

Provides first-party USD pricing for GLM models, complementing the CNY
pricing from the Zhipu fetcher (open.bigmodel.cn). Priority 100.
"""
import logging
import re
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

# Price parsing pattern: "$1.4", "$0.015", "$3"
_PRICE_PAT = re.compile(r"\$(\d+(?:\.\d+)?)")


def _parse_price(cell_text: str) -> Optional[float]:
    """Parse a price cell like '$1.4', 'Free', '-'. Returns None if no price."""
    text = cell_text.strip()
    if text in ("Free", "-", "\\", "Limited-time Free", ""):
        return None
    m = _PRICE_PAT.search(text)
    if m:
        return float(m.group(1))
    return None


class ZAIFetcher(BaseFetcher):
    """
    Fetches USD pricing from Z.AI's international docs site.

    The page contains HTML tables with model pricing in USD.
    Uses requests + BeautifulSoup (no Playwright needed — Mintlify is SSR).
    """

    def __init__(self, config: Config):
        super().__init__(config, config.fetchers["zai"])

    # ------------------------------------------------------------------
    # BaseFetcher interface (we override fetch() for HTML scraping)
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
        logger.info(f"Fetching Z.AI pricing from {self.fetcher_config.url}")
        try:
            response = self.session.get(
                self.fetcher_config.url,
                headers={
                    "Accept": "text/html",
                    "User-Agent": "burncloud-pricing-data/1.0",
                },
                timeout=self.fetcher_config.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Z.AI fetch failed: {e}")
            return FetchResult.error_result("zai", f"HTTP error: {e}")

        try:
            models = self._parse_html(response.text)
        except Exception as e:
            logger.exception("Z.AI pricing parse failed")
            return FetchResult.error_result("zai", f"Parse error: {e}")

        if not models:
            logger.warning("Z.AI: no models extracted from page")
            return FetchResult.error_result("zai", "No models found in page")

        logger.info(f"Z.AI: extracted {len(models)} models")
        return FetchResult(
            source="zai",
            success=True,
            fetched_at=self._now_iso(),
            models=models,
            models_count=len(models),
            fetched_url=self.fetcher_config.url,
            http_status=response.status_code,
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_html(self, html: str) -> Dict[str, Any]:
        """Parse all pricing tables from the Z.AI pricing page."""
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        models: Dict[str, Any] = {}

        for table in tables:
            header_row = table.find("tr")
            if not header_row:
                continue
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th"])]
            if not headers:
                continue

            # Text/Vision models: Model | Input | Cached Input | ... | Output
            if "Input" in headers and "Output" in headers:
                input_col = headers.index("Input")
                cache_col = headers.index("Cached Input") if "Cached Input" in headers else None
                output_col = headers.index("Output")
                for row in table.find_all("tr")[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all(["td"])]
                    if not cells:
                        continue
                    model_name = cells[0]
                    model_id = model_name.lower()
                    if model_id in models:
                        continue

                    input_p = _parse_price(cells[input_col]) if input_col < len(cells) else None
                    output_p = _parse_price(cells[output_col]) if output_col < len(cells) else None

                    if input_p is None and output_p is None:
                        continue

                    # Free models: input=0, output=0
                    pricing = {
                        "in": input_p if input_p is not None else 0.0,
                        "out": output_p if output_p is not None else 0.0,
                    }

                    cache_pricing = None
                    if cache_col is not None and cache_col < len(cells):
                        cache_p = _parse_price(cells[cache_col])
                        if cache_p is not None:
                            cache_pricing = {"read": cache_p}

                    metadata = {"provider": "zhipu", "family": "glm"}
                    endpoint_entry = self._build_endpoint_entry(
                        pricing, cache_pricing=cache_pricing,
                    )
                    models[model_id] = self._build_model_entry(endpoint_entry, metadata)
                    logger.debug(f"Z.AI: {model_id} USD in={pricing['in']} out={pricing['out']}")

            # Per-item models (Image/Video/Audio): Model | Price
            elif len(headers) == 2 and headers[1] in ("Price", "Cost"):
                for row in table.find_all("tr")[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all(["td"])]
                    if len(cells) < 2:
                        continue
                    model_name = cells[0]
                    model_id = model_name.lower()
                    if model_id in models:
                        continue

                    price = _parse_price(cells[1])
                    if price is None:
                        continue

                    # Determine modality from model name
                    mid = model_id
                    if any(k in mid for k in ("video", "vidu", "cogvideo")):
                        modality = {"video": {"per": price}}
                    elif any(k in mid for k in ("image", "cogview")):
                        modality = {"image": {"per": price}}
                    elif any(k in mid for k in ("asr", "tts")):
                        # Audio: per-MTok pricing
                        modality = {"audio": {"in": price}}
                    else:
                        continue

                    metadata = {"provider": "zhipu", "family": "glm"}
                    endpoint_entry = self._build_endpoint_entry(modality)
                    models[model_id] = self._build_model_entry(endpoint_entry, metadata)
                    logger.debug(f"Z.AI: {model_id} USD per-item {price}")

        return models

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
