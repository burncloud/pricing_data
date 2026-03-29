"""
Mistral AI official pricing fetcher.

Mistral's pricing page (https://mistral.ai/pricing) is rendered by Next.js.
Pricing data is embedded as double-escaped JSON within the page source:

  \\"api_endpoint\\":\\"mistral-large-latest\\",\\"price\\":[
    {\\"value\\":\\"Input (/M tokens)\\",\\"price_dollar\\":\\"\\u003cp\\u003e$0.5\\u003c/p\\u003e\\"},
    {\\"value\\":\\"Output (/M tokens)\\",\\"price_dollar\\":\\"\\u003cp\\u003e$1.5\\u003c/p\\u003e\\"}
  ]

Uses curl_cffi with firefox133 TLS impersonation to bypass bot protection.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

# Patterns for the escaped JSON embedded in the page source
_API_ENDPOINT_RE = re.compile(r'\\"api_endpoint\\":\\"([^\\"]+)\\"')
_PRICE_BLOCK_RE = re.compile(r'\\"price\\":\[(.+?)\]')
_PRICE_PAIR_RE = re.compile(
    r'\\"value\\":\\"(.*?)\\",\\"price_dollar\\":\\"(.*?)\\"'
)
# Matches \\uXXXX unicode escapes embedded in the string
_UNICODE_ESC_RE = re.compile(r'\\u([0-9a-fA-F]{4})')


def _decode_price_value(raw: str) -> float | None:
    """
    Decode a raw price_dollar field value to a float USD/MTok price.

    Handles two formats:
    - '$$0.5' (doubled dollar sign) → 0.5
    - '\\u003cp\\u003e$0.15\\u003c/p\\u003e' (unicode-escaped HTML) → 0.15
    """
    # Decode \\uXXXX sequences (literals in the Python string, not real escapes)
    decoded = _UNICODE_ESC_RE.sub(lambda m: chr(int(m.group(1), 16)), raw)
    # Strip HTML tags
    decoded = re.sub(r"<[^>]+>", "", decoded).strip()
    # Strip leading dollar signs (including doubled $$)
    decoded = decoded.lstrip("$").strip()
    try:
        return float(decoded)
    except ValueError:
        return None


class MistralFetcher(BaseFetcher):
    """
    Fetches Mistral AI model pricing from https://mistral.ai/pricing.

    Uses curl_cffi firefox133 TLS impersonation to bypass Cloudflare.
    Priority 100 — direct provider tier.
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["mistral"]
        super().__init__(config, fetcher_config)

    # ------------------------------------------------------------------
    # Override fetch() — curl_cffi doesn't fit requests.Response interface
    # ------------------------------------------------------------------

    def fetch(self) -> FetchResult:
        try:
            import curl_cffi.requests as cffi_req  # noqa: F401
        except ImportError:
            logger.warning("curl_cffi not installed — skipping Mistral fetcher")
            return FetchResult.error_result(
                self.fetcher_config.name,
                "curl_cffi not installed. Run: pip install curl_cffi",
            )

        try:
            html = self._fetch_html()
            models = self._parse_html(html)
        except Exception as e:
            logger.exception("Mistral fetch failed")
            return FetchResult.error_result(self.fetcher_config.name, str(e))

        if not models:
            return FetchResult.error_result(
                self.fetcher_config.name,
                "No models parsed from Mistral pricing page",
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
        """Fetch Mistral pricing page using firefox133 TLS impersonation."""
        import curl_cffi.requests as cffi_req

        resp = cffi_req.get(
            self.fetcher_config.url,
            impersonate="firefox133",
            timeout=int(self.fetcher_config.timeout),
            headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        resp.raise_for_status()
        logger.debug(
            f"Mistral: fetched {len(resp.text)} bytes (HTTP {resp.status_code})"
        )
        return resp.text

    def _parse_html(self, html: str) -> Dict[str, Any]:
        """
        Parse model API names and prices from the Mistral page's embedded JSON.

        The Next.js page embeds pricing as double-escaped JSON. Each model block
        contains an api_endpoint name and a price array with Input/Output entries.
        """
        models: Dict[str, Any] = {}

        for ep_match in _API_ENDPOINT_RE.finditer(html):
            api_name = ep_match.group(1)
            if api_name in models:
                continue

            # Look for price array within 900 chars of the api_endpoint field
            block = html[ep_match.start(): ep_match.start() + 900]
            price_block_m = _PRICE_BLOCK_RE.search(block)
            if not price_block_m:
                continue

            price_arr = price_block_m.group(1)
            inp_price = out_price = None

            for pair_m in _PRICE_PAIR_RE.finditer(price_arr):
                label = pair_m.group(1)
                raw_price = pair_m.group(2)
                price_val = _decode_price_value(raw_price)
                if price_val is None:
                    continue
                if "Input" in label and inp_price is None:
                    inp_price = price_val
                elif "Output" in label and out_price is None:
                    out_price = price_val

            if inp_price is None or out_price is None:
                logger.debug(f"Mistral: skipping {api_name!r} — incomplete pricing")
                continue

            metadata = {
                "provider": "mistral",
                "family": self._extract_family(api_name),
            }
            endpoint_entry = self._build_endpoint_entry(
                {"in": inp_price, "out": out_price},
            )
            models[api_name] = self._build_model_entry(endpoint_entry, metadata)
            logger.debug(
                f"Mistral: parsed {api_name!r} in=${inp_price} out=${out_price}"
            )

        logger.info(f"Mistral: scraped {len(models)} models")
        return models

    @staticmethod
    def _extract_family(model_id: str) -> str:
        """'mistral-large-2' → 'mistral-large', 'codestral-latest' → 'codestral'"""
        # Remove numeric version suffix
        base = re.sub(r"-\d+$", "", model_id)
        # Remove qualifiers
        base = re.sub(r"-(latest|preview|exp|rc\d+)$", "", base)
        return base

    # ------------------------------------------------------------------
    # BaseFetcher abstract stubs (not used — fetch() is overridden)
    # ------------------------------------------------------------------

    def _make_request(self):  # type: ignore[override]
        raise NotImplementedError("MistralFetcher overrides fetch() directly")

    def _validate_response(self, response) -> bool:  # type: ignore[override]
        raise NotImplementedError("MistralFetcher overrides fetch() directly")

    def _parse_models(self, response) -> Dict[str, Any]:  # type: ignore[override]
        raise NotImplementedError("MistralFetcher overrides fetch() directly")
