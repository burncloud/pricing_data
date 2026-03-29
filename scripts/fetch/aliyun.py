"""
Alibaba Cloud / Qwen official pricing fetcher (international).

Scrapes https://www.alibabacloud.com/help/en/model-studio/model-pricing
which has USD-priced HTML tables for Qwen models.

Tiered pricing (e.g. "$1.2-$3 / MTok"): use the first (lowest) tier price.
Only text models with explicit input+output token pricing are captured.
"""
import logging
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Matches "$1.2" or "$0.072" — dollar amounts
_DOLLAR_RE = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)")

# Matches qwen model IDs: qwen-max, qwen3-max, qwen-plus, qwq-plus, etc.
_QWEN_MODEL_RE = re.compile(r"((?:qwen[\w.-]+|qwq[\w.-]+))", re.IGNORECASE)


class _TableCollector(HTMLParser):
    """Collect text cells from all <td>/<th> rows in HTML."""

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


def _first_dollar(text: str) -> Optional[float]:
    """Extract the first dollar amount from a cell (handles '1.2-3' ranges → first value)."""
    m = _DOLLAR_RE.search(text)
    return float(m.group(1)) if m else None


class AliyunFetcher(BaseFetcher):
    """
    Fetches Qwen model pricing from Alibaba Cloud international pricing page.

    Uses plain HTTP GET — no Playwright required. Priority 100. Currency: USD.
    Tiered pricing → takes first (entry-level) price tier.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["aliyun"]
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
        if "qwen" not in text:
            logger.error("Aliyun: 'qwen' not found on pricing page")
            return False
        if not _DOLLAR_RE.search(response.text):
            logger.error("Aliyun: no dollar prices found on page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text
        collector = _TableCollector()
        collector.feed(html)
        rows = collector.rows

        models = self._extract_from_rows(rows)
        logger.info(f"Aliyun: scraped {len(models)} models")
        return models

    def _extract_from_rows(self, rows: List[List[str]]) -> Dict[str, Any]:
        """
        Scan table rows for Qwen model pricing.

        Strategy: any row whose first cell contains a qwen/qwq model name
        AND has at least 2 dollar values elsewhere → input=first, output=second.
        """
        models: Dict[str, Any] = {}

        for row in rows:
            if not row:
                continue

            # Check if first cell (or any cell) has a Qwen model ID
            model_id = self._extract_model_id(row[0])
            if model_id is None:
                continue
            if model_id in models:
                continue

            # Collect dollar amounts from all remaining cells
            prices: List[float] = []
            for cell in row[1:]:
                val = _first_dollar(cell)
                if val is not None:
                    prices.append(val)

            if len(prices) < 2:
                logger.debug(f"Aliyun: skipping {model_id!r} — fewer than 2 prices")
                continue

            input_price = prices[0]
            output_price = prices[1]

            metadata = {
                "provider": "aliyun",
                "family": self._extract_family(model_id),
            }
            endpoint_entry = self._build_endpoint_entry(
                {"in": input_price, "out": output_price},
            )
            models[model_id] = self._build_model_entry(endpoint_entry, metadata)
            logger.debug(
                f"Aliyun: parsed {model_id} in=${input_price} out=${output_price}"
            )

        return models

    @staticmethod
    def _extract_model_id(cell: str) -> Optional[str]:
        """Extract normalized qwen model ID from a table cell."""
        m = _QWEN_MODEL_RE.search(cell)
        if not m:
            return None
        return m.group(1).lower().strip()

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """'qwen3-max' → 'qwen3-max', 'qwen-plus' → 'qwen-plus'"""
        # Remove version suffixes like '-turbo-latest' or '-2024-09-19'
        base = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model_id)
        base = re.sub(r"-(latest|preview|exp)$", "", base)
        return base
