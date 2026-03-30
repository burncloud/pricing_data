"""
Google AI pricing fetcher.

Scrapes https://ai.google.dev/pricing which lists pricing for all Google AI
models: Gemini (token-based), Imagen (per-image), Veo (per-second video),
Lyria (per-request music), and embeddings.

LLM models use $/1M token pricing. Generation models use per-item or
per-second pricing with sec/per keys.
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

# Per-image fee: "$0.039 per image", "$0.134 per 1K/2K image", "$0.24 per 4K image"
_PER_IMAGE_RE = re.compile(
    r"\$([0-9]+(?:\.[0-9]+)?)\s+per\s+(?:[0-9]+[Kk](?:/[0-9]+[Kk])?\s+)?image",
    re.IGNORECASE,
)

# Per-second fee: "$0.40 per second", "$0.15/second"
_PER_SECOND_RE = re.compile(
    r"\$([0-9]+(?:\.[0-9]+)?)\s*(?:per\s+second|/\s*second|/\s*sec)",
    re.IGNORECASE,
)

# Per-request/song fee: "$0.08 per request", "$0.04 per song"
_PER_REQUEST_RE = re.compile(
    r"\$([0-9]+(?:\.[0-9]+)?)\s+per\s+(?:request|song)",
    re.IGNORECASE,
)

# Resolution label: "720p", "1080p", "4K", "4k"
_RESOLUTION_RE = re.compile(r"\b(720p|1080p|4[Kk])\b", re.IGNORECASE)

# Models to skip — free models with no paid pricing
_SKIP_MODEL_PREFIXES = (
    "gemma",
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


def _parse_per_image_price(cell_text: str) -> Optional[float]:
    """
    Extract the first per-image fee from an output price cell.

    Handles:
      "$0.039 per image"           → 0.039
      "$0.134 per 1K/2K image"     → 0.134  (base/smallest resolution)
      "$0.24 per 4K image"         → 0.24
      "$120.00 (text and thinking)" → None   (per-token, not per-image)
    """
    m = _PER_IMAGE_RE.search(cell_text)
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

            table_html = table_m.group(0)
            if self._is_generation_model(display_name):
                entry = self._parse_generation_section(display_name, table_html)
            else:
                entry = self._parse_model_section(display_name, table_html)
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
        output_cell: Optional[str] = None        # text / thinking output (per-token)
        image_output_cell: Optional[str] = None  # image output (per-image fee)
        cache_cell: Optional[str] = None

        for row in rows:
            if len(row) <= paid_col:
                continue
            label = row[0].lower()
            cell = row[paid_col]

            if "input price" in label and input_cell is None:
                input_cell = cell
            elif "output price" in label:
                if "image" in label and image_output_cell is None:
                    # Explicit "Output price (images)" row
                    image_output_cell = cell
                elif output_cell is None:
                    if _parse_per_image_price(cell) is not None:
                        # Cell value is "N per image" — image generation output
                        if image_output_cell is None:
                            image_output_cell = cell
                    else:
                        output_cell = cell
            elif "context caching price" in label and cache_cell is None:
                cache_cell = cell

        if not input_cell:
            return None

        # Parse image output price from whichever cell we found
        image_output_price: Optional[float] = None
        if image_output_cell:
            image_output_price = _parse_per_image_price(image_output_cell)

        # Need either text output or image output to build a useful entry
        if not output_cell and image_output_price is None:
            return None

        input_price, input_boundary = _parse_paid_price(input_cell)
        output_price: Optional[float] = None
        output_boundary: Optional[int] = None
        if output_cell:
            output_price, output_boundary = _parse_paid_price(output_cell)

        if input_price is None:
            return None
        # Text output is optional for image-generation models (no text output)
        if output_price is None and image_output_price is None:
            return None

        metadata = {
            "provider": "google",
            "family": self._extract_family(display_name),
        }

        # Image-only output models (e.g. Flash Image) have no text output_price
        effective_output_price = output_price if output_price is not None else 0.0

        flat_pricing: Dict[str, Any]
        tiered_pricing = None

        if input_boundary is not None and output_cell is not None:
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
                        "in": tier1_in,
                        "out": tier1_out,
                    },
                    {
                        "tier_start": input_boundary,
                        "in": tier2_in,
                        "out": tier2_out,
                    },
                ]
                # Top-level pricing uses tier-1 prices (cheapest / most common)
                flat_pricing = {"in": tier1_in, "out": tier1_out}
            else:
                flat_pricing = {"in": input_price, "out": effective_output_price}
        else:
            flat_pricing = {"in": input_price, "out": effective_output_price}

        if image_output_price is not None:
            flat_pricing["image_out"] = image_output_price
            logger.debug(
                f"Google image model: {display_name!r} "
                f"image_output_price={image_output_price}"
            )

        # Context caching
        cache_pricing = None
        if cache_cell:
            cache_price = _first_dollar(cache_cell)
            if cache_price is not None and "Not available" not in cache_cell:
                cache_pricing = {"read": cache_price}

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
    # Generation model parsing (Imagen, Veo, Lyria, Embeddings)
    # ------------------------------------------------------------------

    @staticmethod
    def _is_generation_model(display_name: str) -> bool:
        """Return True if this is a non-LLM generation/embedding model."""
        name_lower = display_name.lower()
        return any(name_lower.startswith(p) for p in (
            "imagen", "veo", "lyria", "gemini embedding", "gemini robotics",
        ))

    def _parse_generation_section(
        self, display_name: str, table_html: str
    ) -> Optional[Dict[str, Any]]:
        """Parse a generation model's pricing table into a model entry.

        Outputs already-nested pricing:
        - Imagen: {"image": {"per": X}}
        - Veo: {"video": {"sec": X}} or {"video": {"tiered": [...]}}
        - Lyria: {"music": {"per": X}}
        - Embedding: {"text": {"in": X}}
        - Robotics: {"text": {"in": X, "out": Y}}
        """
        rows = _parse_table(table_html)
        paid_col = self._find_paid_column(rows)
        if paid_col is None:
            logger.debug(f"Google: no Paid Tier column for generation model {display_name!r}")
            return None

        name_lower = display_name.lower()
        pricing: Dict[str, Any] = {}

        if name_lower.startswith("imagen"):
            pricing = self._parse_imagen(rows, paid_col)
        elif name_lower.startswith("veo"):
            pricing = self._parse_veo(rows, paid_col)
        elif name_lower.startswith("lyria"):
            pricing = self._parse_lyria(rows, paid_col)
        elif "embedding" in name_lower or "robotics" in name_lower:
            # Embedding and Robotics use standard token pricing
            return self._parse_model_section(display_name, table_html)

        if not pricing:
            logger.debug(f"Google: no pricing parsed for generation model {display_name!r}")
            return None

        metadata = {
            "provider": "google",
            "family": self._extract_family(display_name),
        }

        endpoint_entry = self._build_endpoint_entry(pricing)
        return self._build_model_entry(endpoint_entry, metadata)

    def _parse_imagen(self, rows: List[List[str]], paid_col: int) -> Dict[str, Any]:
        """Parse Imagen pricing table. Returns nested pricing dict."""
        for row in rows:
            if len(row) <= paid_col:
                continue
            cell = row[paid_col]
            m = _PER_IMAGE_RE.search(cell)
            if m:
                return {"image": {"per": float(m.group(1))}}
        return {}

    def _parse_veo(self, rows: List[List[str]], paid_col: int) -> Dict[str, Any]:
        """Parse Veo pricing table. Returns nested pricing dict.

        Veo tables may have resolution-based tiers or a single flat rate.
        """
        tiers: List[Dict[str, Any]] = []
        flat_sec: Optional[float] = None

        for row in rows:
            if len(row) <= paid_col:
                continue
            cell = row[paid_col]
            label = row[0] if row else ""
            full_text = label + " " + cell

            sec_m = _PER_SECOND_RE.search(cell)
            if not sec_m:
                # Try matching just dollar amount with "second" context
                sec_m = _PER_SECOND_RE.search(full_text)
            if sec_m:
                price = float(sec_m.group(1))
                res_m = _RESOLUTION_RE.search(full_text)
                if res_m:
                    resolution = res_m.group(1).lower()
                    tiers.append({"resolution": resolution, "sec": price})
                else:
                    flat_sec = price

        if tiers:
            return {"video": {"tiered": tiers}}
        elif flat_sec is not None:
            return {"video": {"sec": flat_sec}}
        return {}

    def _parse_lyria(self, rows: List[List[str]], paid_col: int) -> Dict[str, Any]:
        """Parse Lyria pricing table. Returns nested pricing dict."""
        for row in rows:
            if len(row) <= paid_col:
                continue
            cell = row[paid_col]
            m = _PER_REQUEST_RE.search(cell)
            if m:
                return {"music": {"per": float(m.group(1))}}
        return {}

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
        """'Gemini 2.5 Flash-Lite Preview' → 'gemini-2.5', 'Imagen 4 Fast' → 'imagen-4'"""
        # Match "Name Version" pattern for any model family
        m = re.match(r"(\w+\s+[0-9]+(?:\.[0-9]+)?)", display_name, re.IGNORECASE)
        if m:
            return m.group(1).lower().replace(" ", "-")
        return display_name.split()[0].lower()
