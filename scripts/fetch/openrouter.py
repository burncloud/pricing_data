"""
OpenRouter API fetcher.

OpenRouter provides pricing data for 100+ models via their /api/v1/models endpoint.
Prices are returned per-token and need to be converted to per-million.
"""
import logging
from typing import Any, Dict, Optional, Tuple

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

# Map OpenRouter provider prefix (from model_id like "openai/gpt-4o") → (endpoint_key, base_url).
# OpenRouter is a data source / routing layer, not a provider endpoint.
# Models for known providers are filed under the real API so prices merge correctly.
# Unknown providers fall back to endpoint_key="openrouter.ai".
_OR_PROVIDER_ENDPOINT: Dict[str, Tuple[str, str]] = {
    "openai":       ("api.openai.com",                   "https://api.openai.com/v1"),
    "anthropic":    ("api.anthropic.com",                "https://api.anthropic.com"),
    "google":       ("generativelanguage.googleapis.com", "https://generativelanguage.googleapis.com"),
    "deepseek":     ("api.deepseek.com",                 "https://api.deepseek.com/v1"),
    "mistralai":    ("api.mistral.ai",                   "https://api.mistral.ai/v1"),
    "x-ai":         ("api.x.ai",                         "https://api.x.ai/v1"),
    "meta-llama":   ("api.llama-api.com",                "https://api.llama-api.com"),
    "cohere":       ("api.cohere.ai",                    "https://api.cohere.ai/v2"),
    "perplexity":   ("api.perplexity.ai",                "https://api.perplexity.ai"),
    "together":     ("api.together.xyz",                 "https://api.together.xyz/v1"),
    "fireworks":    ("api.fireworks.ai",                 "https://api.fireworks.ai/inference/v1"),
    "deepinfra":    ("api.deepinfra.com",                "https://api.deepinfra.com/v1/openai"),
    "groq":         ("api.groq.com",                     "https://api.groq.com/openai/v1"),
    "cerebras":     ("api.cerebras.ai",                  "https://api.cerebras.ai/v1"),
    "qwen":         ("dashscope.aliyuncs.com",           "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "zhipuai":      ("open.bigmodel.cn",                 "https://open.bigmodel.cn/api/paas/v4"),
    "moonshot":     ("api.moonshot.cn",                  "https://api.moonshot.cn/v1"),
    "minimax":      ("api.minimax.chat",                 "https://api.minimax.chat/v1"),
    "sambanova":    ("api.sambanova.ai",                 "https://api.sambanova.ai/v1"),
    "nebius":       ("api.studio.nebius.ai",             "https://api.studio.nebius.ai/v1"),
    "novita":       ("api.novita.ai",                    "https://api.novita.ai/v3/openai"),
}


class OpenRouterFetcher(BaseFetcher):
    """
    Fetches pricing data from OpenRouter API.

    Note: OpenRouter returns prices per-token, not per-million tokens.
    We multiply by 1,000,000 to standardize.
    """

    # Multiplier to convert per-token to per-million tokens
    PRICE_MULTIPLIER = 1_000_000

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["openrouter"]
        super().__init__(config, fetcher_config)

    def _make_request(self) -> Optional[requests.Response]:
        """Make request to OpenRouter API."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "burncloud-pricing-data/1.0",
        }

        # Add API key if available (optional for public endpoint)
        if self.fetcher_config.api_key:
            headers["Authorization"] = f"Bearer {self.fetcher_config.api_key}"

        response = self.session.get(
            self.fetcher_config.url,
            headers=headers,
            timeout=self.fetcher_config.timeout,
        )
        response.raise_for_status()

        # Validate content type
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise ValueError(f"Unexpected content type: {content_type}")

        return response

    def _validate_response(self, response: requests.Response) -> bool:
        """Validate OpenRouter response structure."""
        try:
            data = response.json()

            # Check for expected structure
            if "data" not in data:
                logger.error("OpenRouter response missing 'data' field")
                return False

            if not isinstance(data["data"], list):
                logger.error("OpenRouter 'data' field is not a list")
                return False

            return True

        except Exception as e:
            logger.error(f"OpenRouter response validation failed: {e}")
            return False

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        """Parse models from OpenRouter response."""
        data = response.json()
        models = {}

        for model_data in data.get("data", []):
            model_id = model_data.get("id", "")
            if not model_id:
                continue

            # Normalize model ID (remove provider prefix for pricing.json)
            normalized_id = self._normalize_model_id(model_id)

            # Extract pricing (convert from per-token to per-million)
            pricing_data = model_data.get("pricing", {})
            pricing = self._extract_pricing(pricing_data, model_id)

            if not pricing:
                continue

            # Extract metadata
            metadata = self._extract_metadata(model_data)
            metadata["source_id"] = model_id  # Keep original ID for reference

            # Extract cache pricing
            cache_pricing = self._extract_cache_pricing(pricing_data) or None

            # Use real provider endpoint key instead of "openrouter.ai"
            or_provider = model_id.split("/", 1)[0] if "/" in model_id else ""
            ep_key, ep_base_url = _OR_PROVIDER_ENDPOINT.get(
                or_provider, ("openrouter.ai", "https://openrouter.ai/api/v1")
            )

            endpoint_entry = self._build_endpoint_entry(
                pricing, cache_pricing=cache_pricing,
                base_url=ep_base_url,
            )
            models[normalized_id] = self._build_model_entry(endpoint_entry, metadata, endpoint_key=ep_key)

        return models

    def _normalize_model_id(self, model_id: str) -> str:
        """
        Normalize model ID by removing provider prefix.

        Examples:
            "openai/gpt-4o" -> "gpt-4o"
            "anthropic/claude-3.5-sonnet" -> "claude-3.5-sonnet"
            "google/gemini-1.5-pro" -> "gemini-1.5-pro"
        """
        if "/" in model_id:
            return model_id.split("/", 1)[1]
        return model_id

    def _extract_pricing(self, pricing_data: Dict[str, Any], model_id: str) -> Dict[str, Any]:
        """Extract and convert pricing from OpenRouter format. Returns flat dict (no currency key)."""
        prompt_price = pricing_data.get("prompt")
        completion_price = pricing_data.get("completion")

        if prompt_price is None or completion_price is None:
            logger.debug(f"Skipping {model_id}: missing pricing data")
            return {}

        try:
            # Convert string prices to float and scale to per-million
            input_price = float(prompt_price) * self.PRICE_MULTIPLIER
            output_price = float(completion_price) * self.PRICE_MULTIPLIER

            # OpenRouter uses -1 per-token as a sentinel for "no fixed price"
            # (e.g., openrouter/auto, bodybuilder). Skip these.
            if input_price < 0 or output_price < 0:
                logger.debug(f"Skipping {model_id}: negative price (OpenRouter sentinel value)")
                return {}

            return {
                "in": round(input_price, 6),
                "out": round(output_price, 6),
            }
        except (ValueError, TypeError) as e:
            logger.debug(f"Skipping {model_id}: invalid price value — {e}")
            return {}

    def _extract_cache_pricing(self, pricing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract cache pricing. Returns flat dict (no currency key)."""
        cache_read = pricing_data.get("cache_read")
        cache_write = pricing_data.get("cache_write")

        if cache_read is None and cache_write is None:
            return {}

        try:
            return {
                "in": round(float(cache_read or 0) * self.PRICE_MULTIPLIER, 6),
                "creation_input": round(float(cache_write or 0) * self.PRICE_MULTIPLIER, 6),
            }
        except (ValueError, TypeError):
            return {}

    def _extract_metadata(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from model data."""
        metadata = {
            "provider": self._extract_provider(model_data.get("id", "")),
            "family": self._extract_family(model_data.get("id", "")),
            "context_window": model_data.get("context_length"),
        }

        # Extract capabilities
        architecture = model_data.get("architecture", {})
        metadata["supports_vision"] = "vision" in str(architecture.get("modality", "")).lower()
        metadata["supports_function_calling"] = architecture.get("function_calling", False)

        # Top providers info
        top_provider = model_data.get("top_provider", {})
        if top_provider.get("max_completion_tokens"):
            metadata["max_output_tokens"] = top_provider["max_completion_tokens"]

        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}

    def _extract_provider(self, model_id: str) -> str:
        """Extract provider from model ID."""
        if "/" in model_id:
            return model_id.split("/", 1)[0]
        return "unknown"

    def _extract_family(self, model_id: str) -> str:
        """Extract model family from ID."""
        # Remove provider prefix
        name = self._normalize_model_id(model_id)

        # Extract family (first part before version numbers or modifiers)
        parts = name.split("-")
        if len(parts) >= 2:
            # Handle common patterns: "gpt-4o", "claude-3.5", "gemini-1.5"
            family = "-".join(parts[:2])
            # Normalize version-like second parts
            if parts[1].replace(".", "").isdigit():
                family = parts[0]
            return family
        return parts[0] if parts else name
