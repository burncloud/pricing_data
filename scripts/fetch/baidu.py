"""
Baidu ERNIE / Qianfan official pricing fetcher.

Scrapes https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Fm2vrveyu
which lists ERNIE model pricing in CNY per thousand tokens (or per million tokens).

Note: Baidu pricing page is in Chinese (中文). Prices may be in 元/千tokens
and are converted to CNY/MTok (multiply by 1000).
"""
import logging
import re
from typing import Any, Dict, List, Optional

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Matches ERNIE model names like "ERNIE-4.0-8K", "ERNIE-Speed-8K"
_ERNIE_MODEL_RE = re.compile(r"(ERNIE[\w./-]+\d+(?:[KMB])?[\w.-]*)", re.IGNORECASE)

# Matches CNY prices in various formats
_PRICE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(?:元|CNY)?")

# Per-thousand-token to per-million-token multiplier
_THOUSAND_TO_MILLION = 1000


class BaiduFetcher(BaseFetcher):
    """
    Fetches Baidu ERNIE model pricing from Baidu Cloud documentation.

    Uses plain HTTP GET. Priority 100. Currency: CNY.
    Prices on page may be in 元/千tokens — converted to CNY/MTok.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["baidu"]
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
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
            timeout=self.fetcher_config.timeout,
        )
        resp.raise_for_status()
        return resp

    def _validate_response(self, response: requests.Response) -> bool:
        text = response.text
        if "ERNIE" not in text and "文心" not in text and "ernie" not in text.lower():
            logger.error("Baidu: no ERNIE model names found on pricing page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text
        rows = self._extract_table_rows(html)

        models: Dict[str, Any] = {}
        if rows:
            models = self._extract_from_rows(rows)

        if not models:
            # Fallback: regex on plain text
            plain = re.sub(r"<[^>]+>", " ", html)
            plain = re.sub(r"\s+", " ", plain)
            models = self._extract_from_text(plain)

        logger.info(f"Baidu: scraped {len(models)} models")
        return models

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_table_rows(html: str) -> List[List[str]]:
        """Extract text cells from HTML table rows."""
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
        """Parse ERNIE model pricing from table rows."""
        models: Dict[str, Any] = {}

        for row in rows:
            if len(row) < 3:
                continue

            model_m = _ERNIE_MODEL_RE.search(row[0])
            if not model_m:
                continue
            model_id = model_m.group(1).lower().strip()
            if model_id in models:
                continue

            prices: List[float] = []
            for cell in row[1:]:
                m = _PRICE_RE.search(cell)
                if m:
                    try:
                        prices.append(float(m.group(1)))
                    except ValueError:
                        pass

            if len(prices) < 2:
                continue

            # Detect if prices are per-thousand (typical Baidu format: small values like 0.004)
            # CNY/MTok prices are typically > 0.1; CNY/Ktok prices are 0.001-0.05
            input_price, output_price = prices[0], prices[1]
            if input_price < 0.1 and output_price < 0.1:
                # Likely per-thousand-token — convert to per-million
                input_price *= _THOUSAND_TO_MILLION
                output_price *= _THOUSAND_TO_MILLION

            models[model_id] = self._make_model_entry(model_id, input_price, output_price)
            logger.debug(
                f"Baidu: parsed {model_id} CNY {input_price}/{output_price}"
            )

        return models

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Fallback: extract from plain text when tables not found."""
        models: Dict[str, Any] = {}
        for model_m in _ERNIE_MODEL_RE.finditer(text):
            model_id = model_m.group(1).lower().strip()
            if model_id in models:
                continue
            window = text[model_m.start(): model_m.start() + 200]
            prices = []
            for pm in _PRICE_RE.finditer(window):
                try:
                    val = float(pm.group(1))
                    if 0 < val:
                        prices.append(val)
                except ValueError:
                    pass
            if len(prices) < 2:
                continue
            input_price, output_price = prices[0], prices[1]
            if input_price < 0.1:
                input_price *= _THOUSAND_TO_MILLION
                output_price *= _THOUSAND_TO_MILLION
            models[model_id] = self._make_model_entry(model_id, input_price, output_price)
        return models

    def _make_model_entry(
        self, model_id: str, input_price: float, output_price: float
    ) -> Dict[str, Any]:
        metadata = {"provider": "baidu", "family": self._extract_family(model_id)}
        endpoint_entry = self._build_endpoint_entry(
            {"in": input_price, "out": output_price},
        )
        return self._build_model_entry(endpoint_entry, metadata)

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """'ernie-4.0-8k' → 'ernie-4.0', 'ernie-speed-8k' → 'ernie-speed'"""
        base = re.sub(r"-\d+[kmb]$", "", model_id, flags=re.IGNORECASE)
        base = re.sub(r"-(latest|preview|turbo)$", "", base)
        return base
