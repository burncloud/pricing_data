"""
Anthropic official model pricing fetcher.

Scrapes the model overview table from Anthropic's public docs page which lists
current Claude API model IDs alongside their per-million-token prices.

Source: https://docs.anthropic.com/en/docs/about-claude/models/overview

NOTE: Only models listed in the "current models" table are captured.
Deprecated models are not shown on this page.
"""
import logging
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Price cell format: "$5 / input MTok<br/>$25 / output MTok"
_PRICE_CELL_RE = re.compile(
    r"\$([0-9]+(?:\.[0-9]+)?)\s*/\s*input MTok.*?\$([0-9]+(?:\.[0-9]+)?)\s*/\s*output MTok",
    re.DOTALL | re.IGNORECASE,
)

# Model ID: looks like claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5-20251001
_MODEL_ID_RE = re.compile(r"(claude-[a-z0-9]+(?:-[a-z0-9]+)+)")


class _TableExtractor(HTMLParser):
    """
    Minimal HTMLParser that captures all <tr> rows as lists of cell text.

    Strips nested tags inside cells — only the visible text is kept.
    """

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
        elif tag == "br" and self._in_cell:
            # Convert <br> to newline so multiline cells stay structured
            if self._cell_parts is not None:
                self._cell_parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            cell = "".join(self._cell_parts or []).strip()
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


def _extract_table_containing(html: str, marker: str) -> Optional[List[List[str]]]:
    """
    Find the first <table>…</table> block whose text contains `marker`
    and return its rows as a list of cell-text lists.
    """
    # Find all <table> blocks
    for m in re.finditer(r"<table[\s\S]*?</table>", html, re.IGNORECASE):
        block = m.group(0)
        if marker in block:
            extractor = _TableExtractor()
            extractor.feed(block)
            return extractor.rows
    return None


class AnthropicFetcher(BaseFetcher):
    """
    Fetches current Claude model pricing from Anthropic's public docs.

    Parses the model overview table which maps API model IDs to their
    input/output prices (in $/MTok = $/million tokens).

    Priority 100 — direct provider tier.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["anthropic"]
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
        text = response.text
        if "Claude API ID" not in text:
            logger.error("Anthropic: 'Claude API ID' row not found on page")
            return False
        if "input MTok" not in text:
            logger.error("Anthropic: pricing data not found on page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text

        rows = _extract_table_containing(html, "Claude API ID")
        if not rows:
            logger.warning("Anthropic: could not extract model table")
            return {}

        # Find column positions: row with "Claude API ID" defines model IDs
        model_ids: List[str] = []
        price_cells: List[str] = []

        for row in rows:
            if not row:
                continue
            label = row[0].strip()

            if "Claude API ID" in label:
                # Each subsequent cell has one model ID (may be wrapped in code spans)
                for cell in row[1:]:
                    ids = _MODEL_ID_RE.findall(cell)
                    model_ids.append(ids[0] if ids else "")

            elif label.startswith("Pricing") and model_ids:
                # Cells: "$5 / input MTok\n$25 / output MTok"
                price_cells = row[1:]
                break

        if not model_ids or not price_cells:
            logger.warning("Anthropic: model IDs or prices not found in table")
            return {}

        models: Dict[str, Any] = {}
        for model_id, cell in zip(model_ids, price_cells):
            if not model_id:
                continue
            m = _PRICE_CELL_RE.search(cell)
            if not m:
                logger.debug(f"Anthropic: no price found in cell {cell!r}")
                continue

            input_price = float(m.group(1))
            output_price = float(m.group(2))

            models[model_id] = {
                "pricing": {
                    "USD": {
                        "input_price": input_price,
                        "output_price": output_price,
                    }
                },
                "metadata": {
                    "provider": "anthropic",
                    "family": self._extract_family(model_id),
                },
            }

        logger.info(f"Anthropic: parsed {len(models)} models")
        return models

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """
        'claude-opus-4-6' → 'claude-opus'
        'claude-haiku-4-5-20251001' → 'claude-haiku'
        """
        parts = model_id.split("-")
        # Take first two meaningful parts (claude + model-type)
        return "-".join(parts[:2]) if len(parts) >= 2 else parts[0]
