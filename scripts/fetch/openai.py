"""
OpenAI official pricing page fetcher.

Uses curl_cffi with firefox133 TLS fingerprint spoofing to bypass Cloudflare.
Standard requests and headless Playwright both get 403 in CI.

The pricing page (https://openai.com/api/pricing) renders server-side HTML —
no JS execution needed once Cloudflare is bypassed. Prices are embedded in
<span class="whitespace-nowrap"> elements inside <h2 class="text-h4"> model cards.
"""
import logging
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, Optional, Tuple

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

# Matches "Input:\n$2.50 / 1M tokens" within a whitespace-nowrap span
_PRICE_RE = re.compile(
    r"^([^:\n]+):\s*\n\s*\$([0-9,]+(?:\.[0-9]+)?)\s*/\s*1M\s+tokens",
    re.MULTILINE | re.IGNORECASE,
)

# CSS selectors expressed as regex patterns
_H2_RE = re.compile(r'<h2 class="text-h4">(.*?)</h2>')
_SPAN_RE = re.compile(r'<span class="whitespace-nowrap">(.*?)</span>', re.DOTALL)


class OpenAIFetcher(BaseFetcher):
    """
    Fetches pricing from https://openai.com/api/pricing.

    OpenAI's pricing page is behind Cloudflare. Standard HTTP requests and
    headless Playwright both receive 403. curl_cffi with firefox133
    impersonation successfully bypasses the Cloudflare bot check.

    Priority 100 — direct provider tier, same as other first-party fetchers.
    Only the text-completion models shown on the page are captured (typically
    3-5 flagship models). The full OpenAI catalog is covered by LiteLLM (p70).
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["openai"]
        super().__init__(config, fetcher_config)

    # ------------------------------------------------------------------
    # Override fetch() — curl_cffi doesn't fit the requests.Response interface
    # ------------------------------------------------------------------

    def fetch(self) -> FetchResult:
        try:
            import curl_cffi.requests as cffi_req  # noqa: F401
        except ImportError:
            logger.warning("curl_cffi not installed — skipping OpenAI fetcher")
            return FetchResult.error_result(
                self.fetcher_config.name,
                "curl_cffi not installed. Run: pip install curl_cffi",
            )

        try:
            html = self._fetch_html()
            models = self._parse_html(html)
        except Exception as e:
            logger.exception("OpenAI fetch failed")
            return FetchResult.error_result(self.fetcher_config.name, str(e))

        if not models:
            return FetchResult.error_result(
                self.fetcher_config.name,
                "No models parsed from OpenAI pricing page",
            )

        return FetchResult(
            source=self.fetcher_config.name,
            success=True,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            models=models,
            models_count=len(models),
            fetched_url=self.fetcher_config.url,
        )

    def _fetch_html(self) -> str:
        """Fetch OpenAI pricing page HTML using firefox133 TLS impersonation."""
        import curl_cffi.requests as cffi_req

        resp = cffi_req.get(
            self.fetcher_config.url,
            impersonate="firefox133",
            timeout=int(self.fetcher_config.timeout),
            headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        resp.raise_for_status()
        logger.debug(f"OpenAI: fetched {len(resp.text)} bytes (HTTP {resp.status_code})")
        return resp.text

    def _parse_html(self, html: str) -> Dict[str, Any]:
        """
        Parse model names and prices from the pricing page HTML.

        Structure:
          <h2 class="text-h4">GPT-5.4</h2>
          ...
          <span class="whitespace-nowrap">Input:<br/>$2.50 / 1M tokens</span>
          <span class="whitespace-nowrap">Cached input:<br/>$0.25 / 1M tokens</span>
          <span class="whitespace-nowrap">Output:<br/>$15.00 / 1M tokens</span>
        """
        # Collect (position, model_name) pairs
        h2_positions = [
            (m.start(), unescape(m.group(1)).strip())
            for m in _H2_RE.finditer(html)
        ]

        # Collect (position, span_text) for price spans
        span_positions: list[Tuple[int, str]] = []
        for m in _SPAN_RE.finditer(html):
            raw = m.group(1)
            # Convert <br/> to newline BEFORE stripping remaining tags
            text = re.sub(r"<br\s*/?>", "\n", raw)
            text = re.sub(r"<[^>]+>", "", text)
            text = unescape(text).strip()
            span_positions.append((m.start(), text))

        # Assign each span to the nearest preceding h2
        card_prices: Dict[str, Dict[str, float]] = {}
        for span_pos, span_text in span_positions:
            preceding = [(pos, name) for pos, name in h2_positions if pos < span_pos]
            if not preceding:
                continue
            _, model_name = max(preceding, key=lambda x: x[0])

            pm = _PRICE_RE.match(span_text)
            if pm:
                label = pm.group(1).strip().lower()
                value = float(pm.group(2).replace(",", ""))
                card_prices.setdefault(model_name, {})[label] = value

        # Build FetchResult model entries
        models: Dict[str, Any] = {}
        for display_name, prices in card_prices.items():
            entry = self._build_model_entry_from_prices(display_name, prices)
            if entry is not None:
                model_id = self._normalize_display_name(display_name)
                models[model_id] = entry
                logger.debug(f"OpenAI: parsed {display_name!r} → {model_id!r} {prices}")

        logger.info(f"OpenAI: scraped {len(models)} models")
        return models

    def _build_model_entry_from_prices(
        self, display_name: str, prices: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        input_price = prices.get("input")
        output_price = prices.get("output")

        if input_price is None or output_price is None:
            logger.debug(
                f"OpenAI: no input+output for {display_name!r} — skipping "
                f"(found labels: {list(prices)})"
            )
            return None

        metadata = {
            "provider": "openai",
            "family": self._extract_family(display_name),
        }

        cached_price = prices.get("cached input")
        cache_pricing = (
            {"read": cached_price} if cached_price is not None else None
        )

        endpoint_entry = self._build_endpoint_entry(
            {"in": input_price, "out": output_price},
            cache_pricing=cache_pricing,
        )
        return self._build_model_entry(endpoint_entry, metadata)

    @staticmethod
    def _normalize_display_name(display_name: str) -> str:
        """
        'GPT-5.4' → 'gpt-5.4'
        'GPT-5.4 mini' → 'gpt-5.4-mini'
        'o3-mini' → 'o3-mini'
        """
        name = display_name.lower().strip()
        name = re.sub(r"\s+", "-", name)
        name = name.strip("-")
        return name

    @staticmethod
    def _extract_family(display_name: str) -> str:
        name = display_name.lower().strip()
        parts = name.split()
        if not parts:
            return "openai"
        first = parts[0]
        family = re.sub(r"-(mini|nano|micro|small|large|pro|plus)$", "", first)
        return family

    # ------------------------------------------------------------------
    # BaseFetcher abstract stubs (not used — fetch() is overridden above)
    # ------------------------------------------------------------------

    def _make_request(self):  # type: ignore[override]
        raise NotImplementedError("OpenAIFetcher overrides fetch() directly")

    def _validate_response(self, response) -> bool:  # type: ignore[override]
        raise NotImplementedError("OpenAIFetcher overrides fetch() directly")

    def _parse_models(self, response) -> Dict[str, Any]:  # type: ignore[override]
        raise NotImplementedError("OpenAIFetcher overrides fetch() directly")
