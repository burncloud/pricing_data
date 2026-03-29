"""
MiniMax official pricing fetcher (international).

Scrapes https://platform.minimax.io/docs/pricing/overview or
https://platform.minimax.io/docs/guides/pricing-token-plan
for MiniMax text model pricing.

Note: The international platform may use subscription bundles rather than
per-token pricing. If the page doesn't contain per-token prices, returns empty.
"""
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Matches MiniMax model IDs: MiniMax-Text-01, abab6.5-chat, M2.7, etc.
_MODEL_RE = re.compile(
    r"((?:MiniMax-[\w.-]+|abab[\w.-]+-(?:chat|pro)|M\d+(?:\.\d+)?(?:-highspeed)?))",
    re.IGNORECASE,
)

# Dollar or CNY price: "$0.20 / 1M tokens" or "¥0.8/MTok"
_DOLLAR_RE = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)")
_YUAN_RE = re.compile(r"[¥￥]([0-9]+(?:\.[0-9]+)?)")


class MiniMaxFetcher(BaseFetcher):
    """
    Fetches MiniMax model pricing from the international platform.

    Uses plain HTTP GET. Priority 100.
    Currency: USD (international platform) or CNY (Chinese platform).
    Returns empty gracefully if per-token pricing is not available.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["minimax"]
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
        if "minimax" not in text and "abab" not in text:
            logger.error("MiniMax: no model names found on pricing page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text
        rows = self._extract_table_rows(html)
        models = {}

        if rows:
            models = self._extract_from_rows(rows)

        if not models:
            plain = re.sub(r"<[^>]+>", " ", html)
            plain = re.sub(r"\s+", " ", plain)
            models = self._extract_from_text(plain)

        if not models:
            logger.info(
                "MiniMax: no per-token pricing found — "
                "page may use subscription pricing (acceptable)"
            )

        logger.info(f"MiniMax: scraped {len(models)} models")
        return models

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_table_rows(html: str) -> List[List[str]]:
        """Extract text from table rows."""
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
        """Parse pricing from table rows."""
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

            prices, use_cny = self._extract_prices(row[1:])
            if len(prices) < 2:
                continue

            currency = "CNY" if use_cny else "USD"
            models[model_id] = self._make_entry(
                model_id, prices[0], prices[1], currency
            )
        return models

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Fallback: extract from plain text."""
        models: Dict[str, Any] = {}
        for model_m in _MODEL_RE.finditer(text):
            model_id = model_m.group(1).lower().strip()
            if model_id in models:
                continue
            window = text[model_m.start(): model_m.start() + 300]
            prices, use_cny = self._extract_prices([window])
            if len(prices) < 2:
                continue
            currency = "CNY" if use_cny else "USD"
            models[model_id] = self._make_entry(
                model_id, prices[0], prices[1], currency
            )
        return models

    @staticmethod
    def _extract_prices(cells: List[str]) -> tuple:
        """Extract (prices_list, is_cny) from a list of cells."""
        text = " ".join(cells)
        dollar_prices = [float(m.group(1)) for m in _DOLLAR_RE.finditer(text)]
        if dollar_prices:
            return dollar_prices, False
        yuan_prices = [float(m.group(1)) for m in _YUAN_RE.finditer(text)]
        if yuan_prices:
            return yuan_prices, True
        # Fallback: bare numbers
        nums = [float(m.group(1)) for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)", text)]
        return nums, False

    def _make_entry(
        self,
        model_id: str,
        input_price: float,
        output_price: float,
        currency: str = "USD",
    ) -> Dict[str, Any]:
        metadata = {"provider": "minimax", "family": self._extract_family(model_id)}
        endpoint_entry = self._build_endpoint_entry(
            {"in": input_price, "out": output_price},
            currency=currency,
        )
        return self._build_model_entry(endpoint_entry, metadata)

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """'minimax-text-01' → 'minimax-text', 'abab6.5-chat' → 'abab6.5'"""
        base = re.sub(r"-(chat|pro|highspeed|01|02|latest)$", "", model_id)
        return base
