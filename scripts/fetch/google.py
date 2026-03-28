"""
Google Gemini API pricing fetcher.

Scrapes https://ai.google.dev/pricing which lists per-million-token prices
for all Gemini models in a structured HTML table per model.

Models with tiered pricing (e.g. ≤200k / >200k token context breakpoints)
are represented as tiered_pricing. Context caching prices are captured as
cache_pricing.

Only text/image/video token pricing is extracted. Audio, per-image, and
per-second (video generation) pricing is skipped.
"""
import logging
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Matches dollar amounts in price cells: "$1.25" or "$0.05"
_DOLLAR_RE = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)")

# Tier boundary tokens from "prompts <= 200k tokens" / "prompts > 128k tokens"
_TIER_BOUNDARY_RE = re.compile(r"(?:<=|<)\s*([0-9]+)k\s*tokens", re.IGNORECASE)

# Models to skip — image/video/audio/embedding generation, not LLMs
_SKIP_MODEL_PREFIXES = (
    "imagen",
    "veo",
    "lyria",
    "gemini embedding",
    "gemini robotics",
)


class _TableExtractor(HTMLParser):
    """Collect <tr> rows from a single <table> block as lists of cell text."""

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


def _parse_table(table_html: str) -> List[List[str]]:
    ext = _TableExtractor()
    ext.feed(table_html)
    return ext.rows


def _first_dollar(text: str) -> Optional[float]:
    """Extract the first dollar amount from text, or None."""
    m = _DOLLAR_RE.search(text)
    return float(m.group(1)) if m else None


def _parse_paid_price(cell_text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse a "Paid Tier" price cell.

    Cases:
    - "$0.25 (text / image / video)" → (0.25, None)    flat, no tier end
    - "$1.25, prompts <= 200k tokens\n$2.50, prompts > 200k" → first tier, boundary 200k
      Returns (first_price, boundary_k * 1000) where boundary is tier_end of the first tier.
    - "Not available" → (None, None)
    - "$0.50 (text) | $3.00 or $0.005/min (audio)" → use text price only
    """
    text = cell_text.strip()
    if "Not available" in text or "not available" in text:
        return None, None

    prices = _DOLLAR_RE.findall(text)
    if not prices:
        return None, None

    # Detect tier boundary (e.g. "prompts <= 200k tokens")
    boundary_m = _TIER_BOUNDARY_RE.search(text)
    if boundary_m:
        boundary = int(boundary_m.group(1)) * 1000
        return float(prices[0]), boundary

    # Flat price (possibly with qualifiers like "(text / image / video)")
    return float(prices[0]), None


class GoogleFetcher(BaseFetcher):
    """
    Fetches Gemini model pricing from https://ai.google.dev/pricing.

    Each model is listed under an H2 heading with a pricing table below it.
    Tiered pricing (context-length dependent) is parsed into tiered_pricing.

    Priority 100 — direct provider tier.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["google"]
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
        if "Input price" not in response.text:
            logger.error("Google: 'Input price' not found on pricing page")
            return False
        if "Gemini" not in response.text:
            logger.error("Google: No Gemini models found on pricing page")
            return False
        return True

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        html = response.text
        models: Dict[str, Any] = {}

        # Match each H2 section: <h2>HEADING</h2> + content until next <h2 or end
        for heading_html, content in re.findall(
            r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|\Z)",
            html,
            re.DOTALL | re.IGNORECASE,
        ):
            display_name = re.sub(r"<[^>]+>", "", heading_html).strip()
            if not display_name or self._should_skip(display_name):
                continue

            table_m = re.search(r"<table[\s\S]*?</table>", content, re.IGNORECASE)
            if not table_m:
                continue

            entry = self._parse_model_section(display_name, table_m.group(0))
            if entry is not None:
                model_id = self._normalize_display_name(display_name)
                models[model_id] = entry

        logger.info(f"Google: parsed {len(models)} models")
        return models

    # ------------------------------------------------------------------
    # Per-model parsing
    # ------------------------------------------------------------------

    def _parse_model_section(
        self, display_name: str, table_html: str
    ) -> Optional[Dict[str, Any]]:
        """Parse a single model's pricing table into a model entry."""
        rows = _parse_table(table_html)

        # Find paid-tier column index (column header contains "Paid Tier")
        paid_col = self._find_paid_column(rows)
        if paid_col is None:
            logger.debug(f"Google: no Paid Tier column for {display_name!r}")
            return None

        input_cell: Optional[str] = None
        output_cell: Optional[str] = None
        cache_cell: Optional[str] = None

        for row in rows:
            if len(row) <= paid_col:
                continue
            label = row[0].lower()

            if "input price" in label and input_cell is None:
                input_cell = row[paid_col]
            elif "output price" in label and output_cell is None:
                output_cell = row[paid_col]
            elif "context caching price" in label and cache_cell is None:
                cache_cell = row[paid_col]

        if not input_cell or not output_cell:
            return None

        input_price, input_boundary = _parse_paid_price(input_cell)
        output_price, output_boundary = _parse_paid_price(output_cell)

        if input_price is None or output_price is None:
            return None

        metadata = {
            "provider": "google",
            "family": self._extract_family(display_name),
        }

        flat_pricing: Dict[str, Any]
        tiered_pricing = None

        if input_boundary is not None:
            all_input_prices = [float(p) for p in _DOLLAR_RE.findall(input_cell)]
            all_output_prices = [float(p) for p in _DOLLAR_RE.findall(output_cell)]

            if len(all_input_prices) >= 2:
                tier1_in = all_input_prices[0]
                tier2_in = all_input_prices[1]
                tier1_out = all_output_prices[0]
                tier2_out = all_output_prices[1] if len(all_output_prices) >= 2 else tier1_out

                tiered_pricing = [
                    {
                        "tier_start": 0,
                        "tier_end": input_boundary,
                        "input_price": tier1_in,
                        "output_price": tier1_out,
                    },
                    {
                        "tier_start": input_boundary,
                        "input_price": tier2_in,
                        "output_price": tier2_out,
                    },
                ]
                # Top-level pricing uses tier-1 prices (cheapest / most common)
                flat_pricing = {"input_price": tier1_in, "output_price": tier1_out}
            else:
                flat_pricing = {"input_price": input_price, "output_price": output_price}
        else:
            flat_pricing = {"input_price": input_price, "output_price": output_price}

        # Context caching
        cache_pricing = None
        if cache_cell:
            cache_price = _first_dollar(cache_cell)
            if cache_price is not None and "Not available" not in cache_cell:
                cache_pricing = {"cache_read_input_price": cache_price}

        endpoint_entry = self._build_endpoint_entry(
            flat_pricing,
            cache_pricing=cache_pricing,
            tiered_pricing=tiered_pricing,
        )
        return self._build_model_entry(endpoint_entry, metadata)

    @staticmethod
    def _find_paid_column(rows: List[List[str]]) -> Optional[int]:
        """Find the column index of the 'Paid Tier' column."""
        for row in rows[:3]:  # header is in first few rows
            for i, cell in enumerate(row):
                if "Paid Tier" in cell or "paid tier" in cell.lower():
                    return i
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _should_skip(display_name: str) -> bool:
        name_lower = display_name.lower()
        return any(name_lower.startswith(p) for p in _SKIP_MODEL_PREFIXES) or \
               "pricing for" in name_lower or \
               "notes" in name_lower

    @staticmethod
    def _normalize_display_name(display_name: str) -> str:
        """
        'Gemini 2.5 Pro' → 'gemini-2.5-pro'
        'Gemini 2.5 Flash-Lite' → 'gemini-2.5-flash-lite'
        'Gemini 2.5 Flash Native Audio (Live API)' → 'gemini-2.5-flash-native-audio'
        """
        # Strip parenthetical suffixes like "(Live API)", "(Preview)", "🍌"
        name = re.sub(r"\s*\(.*?\)", "", display_name)
        # Remove emoji and non-ASCII; keep letters, digits, spaces, dots, hyphens
        name = re.sub(r"[^\w\s.\-]", "", name)
        name = name.strip().lower()
        # Collapse spaces to hyphens
        name = re.sub(r"\s+", "-", name)
        name = name.strip("-")
        return name

    @staticmethod
    def _extract_family(display_name: str) -> str:
        """'Gemini 2.5 Flash-Lite Preview' → 'gemini-2.5'"""
        m = re.match(r"(gemini\s+[0-9]+(?:\.[0-9]+)?)", display_name, re.IGNORECASE)
        if m:
            return m.group(1).lower().replace(" ", "-")
        return display_name.split()[0].lower()
