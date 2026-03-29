"""
Moonshot AI (Kimi) official pricing fetcher.

Scrapes https://platform.moonshot.ai/docs/pricing/chat which lists
kimi model pricing in CNY per million tokens.

Note: Prices shown are tax-inclusive (含税), which is the official billing price.
"""
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Matches CNY price patterns: "¥0.1", "¥ 0.1", "0.12元", "0.012"
# We look for numeric values near model names in the page text
_PRICE_RE = re.compile(r"[¥￥]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:元|CNY)?")

# Matches kimi/moonshot model IDs
_MODEL_RE = re.compile(r"((?:kimi|moonshot-v\d)[\w.-]*)", re.IGNORECASE)


def _parse_cny_price(text: str) -> Optional[float]:
    """Extract CNY price from cell text. Returns None if not parseable."""
    # Remove thousands separators and strip non-numeric except decimal point
    text = text.strip()
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if m:
        return float(m.group(1))
    return None


class MoonshotFetcher(BaseFetcher):
    """
    Fetches Moonshot/Kimi model pricing from https://platform.moonshot.ai/docs/pricing/chat.

    Uses plain HTTP GET — no Playwright. Priority 100. Currency: CNY.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["moonshot"]
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
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=self.fetcher_config.timeout,
        )
        resp.raise_for_status()
        return resp

    def _validate_response(self, response: requests.Response) -> bool:
        text = response.text.lower()
        if "kimi" not in text and "moonshot" not in text:
            logger.error("Moonshot: no 'kimi' or 'moonshot' found on pricing page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text
        rows = self._extract_table_rows(html)
        if not rows:
            # Fallback: try regex on plain text
            plain = re.sub(r"<[^>]+>", " ", html)
            plain = re.sub(r"\s+", " ", plain)
            models = self._extract_from_text(plain)
        else:
            models = self._extract_from_rows(rows)

        logger.info(f"Moonshot: scraped {len(models)} models")
        return models

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_table_rows(html: str) -> List[List[str]]:
        """Extract text cells from table rows."""
        from html.parser import HTMLParser

        class _Collector(HTMLParser):
            def __init__(self):
                super().__init__()
                self.rows: List[List[str]] = []
                self._row: Optional[List[str]] = None
                self._cell: Optional[List[str]] = None

            def handle_starttag(self, tag, attrs):
                if tag == "tr":
                    self._row = []
                elif tag in ("td", "th") and self._row is not None:
                    self._cell = []

            def handle_endtag(self, tag):
                if tag in ("td", "th") and self._cell is not None:
                    text = " ".join("".join(self._cell).split()).strip()
                    if self._row is not None:
                        self._row.append(text)
                    self._cell = None
                elif tag == "tr" and self._row is not None:
                    if any(c.strip() for c in self._row):
                        self.rows.append(self._row)
                    self._row = None

            def handle_data(self, data):
                if self._cell is not None:
                    self._cell.append(data)

        collector = _Collector()
        collector.feed(html)
        return collector.rows

    def _extract_from_rows(self, rows: List[List[str]]) -> Dict[str, Any]:
        """Parse model pricing from table rows."""
        models: Dict[str, Any] = {}

        for row in rows:
            if len(row) < 3:
                continue
            model_m = _MODEL_RE.search(row[0])
            if not model_m:
                continue
            model_id = model_m.group(1).lower().strip()
            if model_id in models:
                continue

            prices = []
            for cell in row[1:]:
                val = _parse_cny_price(cell)
                if val is not None:
                    prices.append(val)

            if len(prices) < 2:
                continue

            input_price, output_price = prices[0], prices[1]
            entry = self._make_model_entry(model_id, input_price, output_price)
            models[model_id] = entry
            logger.debug(
                f"Moonshot: parsed {model_id} CNY {input_price}/{output_price}"
            )

        return models

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Fallback: extract models from plain text when no tables found."""
        models: Dict[str, Any] = {}
        for model_m in _MODEL_RE.finditer(text):
            model_id = model_m.group(1).lower().strip()
            if model_id in models:
                continue
            # Look for prices in the next 200 characters
            window = text[model_m.start(): model_m.start() + 200]
            prices = []
            for price_m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)", window):
                try:
                    val = float(price_m.group(1))
                    if 0 < val < 1000:  # sanity check: CNY/MTok range
                        prices.append(val)
                except ValueError:
                    pass
            if len(prices) < 2:
                continue
            input_price, output_price = prices[0], prices[1]
            models[model_id] = self._make_model_entry(model_id, input_price, output_price)
        return models

    def _make_model_entry(
        self, model_id: str, input_price: float, output_price: float
    ) -> Dict[str, Any]:
        metadata = {"provider": "moonshot", "family": self._extract_family(model_id)}
        endpoint_entry = self._build_endpoint_entry(
            {"in": input_price, "out": output_price},
        )
        return self._build_model_entry(endpoint_entry, metadata)

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """'kimi-k2-thinking-turbo' → 'kimi-k2', 'moonshot-v1' → 'moonshot-v1'"""
        base = re.sub(r"-(thinking|turbo|preview|fast|lite|pro).*$", "", model_id)
        return base
