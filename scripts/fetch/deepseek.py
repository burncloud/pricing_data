"""
DeepSeek official API pricing fetcher.

Scrapes https://api-docs.deepseek.com/quick_start/pricing which has a
straightforward HTML table with model names and per-million-token prices.

The pricing table has a single PRICING section with three sub-rows:
  - 1M INPUT TOKENS (CACHE HIT) = cache_read_input_price
  - 1M INPUT TOKENS (CACHE MISS) = input_price (standard)
  - 1M OUTPUT TOKENS = output_price

Both deepseek-chat and deepseek-reasoner are captured from the same table.
"""
import logging
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Matches model IDs like "deepseek-chat", "deepseek-reasoner"
_DEEPSEEK_MODEL_RE = re.compile(r"(deepseek-[a-z]+)")

# Matches dollar amounts
_DOLLAR_RE = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)")


class _CellCollector(HTMLParser):
    """Collect visible text from all <td>/<th> cells in an HTML fragment."""

    def __init__(self):
        super().__init__()
        self.rows: List[List[str]] = []
        self._row: Optional[List[str]] = None
        self._cell_parts: Optional[List[str]] = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell_parts = []
            self._in_cell = True
        elif tag == "br" and self._in_cell and self._cell_parts is not None:
            self._cell_parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            cell = " ".join("".join(self._cell_parts or []).split()).strip()
            if self._row is not None:
                self._row.append(cell)
            self._cell_parts = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            if any(c.strip() for c in self._row):
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._in_cell and self._cell_parts is not None:
            self._cell_parts.append(data)


class DeepSeekFetcher(BaseFetcher):
    """
    Fetches deepseek-chat and deepseek-reasoner pricing from DeepSeek's API docs.

    Uses plain HTTP GET — no Playwright required. Priority 100.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["deepseek"]
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
        if "deepseek-chat" not in response.text:
            logger.error("DeepSeek: 'deepseek-chat' not found on pricing page")
            return False
        if "PRICING" not in response.text:
            logger.error("DeepSeek: PRICING section not found on page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text

        # Find the pricing table
        table_m = re.search(r"<table[\s\S]*?</table>", html, re.IGNORECASE)
        if not table_m:
            logger.warning("DeepSeek: no <table> found")
            return {}

        collector = _CellCollector()
        collector.feed(table_m.group(0))
        rows = collector.rows

        # Extract model IDs from the MODEL row
        model_ids = self._extract_model_ids(rows)
        if not model_ids:
            logger.warning("DeepSeek: no model IDs found in table")
            return {}

        # Extract per-million-token prices
        cache_hit = self._find_price(rows, "CACHE HIT")
        cache_miss = self._find_price(rows, "CACHE MISS")
        output = self._find_price(rows, "OUTPUT TOKENS")

        if cache_miss is None or output is None:
            logger.warning("DeepSeek: could not find input/output prices")
            return {}

        models: Dict[str, Any] = {}
        for model_id in model_ids:
            entry: Dict[str, Any] = {
                "pricing": {
                    "USD": {
                        "input_price": cache_miss,
                        "output_price": output,
                    }
                },
                "metadata": {
                    "provider": "deepseek",
                    "family": self._extract_family(model_id),
                },
            }
            if cache_hit is not None:
                entry["cache_pricing"] = {
                    "USD": {"cache_read_input_price": cache_hit}
                }
            models[model_id] = entry

        logger.info(f"DeepSeek: parsed {len(models)} models")
        return models

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_model_ids(rows: List[List[str]]) -> List[str]:
        """Find the row containing 'MODEL' and extract deepseek-* IDs."""
        for row in rows:
            for cell in row:
                if cell.upper() == "MODEL":
                    ids = []
                    for other in row:
                        found = _DEEPSEEK_MODEL_RE.findall(other)
                        ids.extend(found)
                    if ids:
                        return ids
        # Fallback: scan all cells
        ids = []
        for row in rows:
            for cell in row:
                ids.extend(_DEEPSEEK_MODEL_RE.findall(cell))
        return list(dict.fromkeys(ids))  # deduplicate, preserve order

    @staticmethod
    def _find_price(rows: List[List[str]], keyword: str) -> Optional[float]:
        """Find the first dollar amount in the row containing `keyword`."""
        for row in rows:
            row_text = " ".join(row).upper()
            if keyword.upper() in row_text:
                for cell in row:
                    m = _DOLLAR_RE.search(cell)
                    if m:
                        return float(m.group(1))
        return None

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """'deepseek-chat' → 'deepseek-chat', 'deepseek-reasoner' → 'deepseek-reasoner'"""
        return model_id
