"""
LiteLLM community JSON fetcher.

Fetches pricing from LiteLLM's public GitHub raw JSON which includes
batch_pricing and tiered_pricing data not available from OpenRouter.

Source: https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json
"""
import logging
from typing import Any, Dict, List, Optional

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# Known non-model entries in the LiteLLM JSON (documentation templates, etc.)
_SKIP_MODEL_IDS = frozenset({"sample_spec"})

# litellm_provider values that are proxy routes — skip them.
# The same models appear directly as litellm_provider=anthropic/openai/etc.
_SKIP_PROVIDERS = frozenset({
    "bedrock",
    "vertex_ai",
    "vertex_ai_beta",
    "azure",
    "azure_ai",
    "sagemaker",
    "watson",
    "watsonx",
})

# Multiplier: LiteLLM stores cost per token, we want per million tokens
_PER_TOKEN_TO_PER_MILLION = 1_000_000


class LiteLLMFetcher(BaseFetcher):
    """
    Fetches pricing from LiteLLM's public GitHub raw JSON.

    Provides batch_pricing and tiered_pricing that OpenRouter doesn't expose.
    Priority 70 — beats OpenRouter (50), yields to direct providers (100).
    """

    def __init__(self, config: Config):
        fetcher_config = config.fetchers["litellm"]
        super().__init__(config, fetcher_config)

    # ------------------------------------------------------------------
    # BaseFetcher interface
    # ------------------------------------------------------------------

    def _make_request(self) -> Optional[requests.Response]:
        response = self.session.get(
            self.fetcher_config.url,
            headers={"Accept": "application/json", "User-Agent": "burncloud-pricing-data/1.0"},
            timeout=self.fetcher_config.timeout,
        )
        response.raise_for_status()
        return response

    def _validate_response(self, response: requests.Response) -> bool:
        try:
            data = response.json()
            if not isinstance(data, dict):
                logger.error("LiteLLM response is not a JSON object")
                return False
            model_count = len(data)
            min_expected = self.config.min_models_guard.get("litellm", 0)
            if min_expected > 0 and model_count < min_expected:
                logger.warning(
                    f"LiteLLM returned only {model_count} models "
                    f"(min expected: {min_expected}) — skipping source"
                )
                return False
            return True
        except Exception as e:
            logger.error(f"LiteLLM response validation error: {e}")
            return False

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        raw = response.json()
        models: Dict[str, Any] = {}

        for raw_id, entry in raw.items():
            if not isinstance(entry, dict):
                continue

            # Skip documentation templates
            if raw_id in _SKIP_MODEL_IDS:
                continue

            # Skip proxy routes — direct entries cover these models
            provider = entry.get("litellm_provider", "")
            if provider in _SKIP_PROVIDERS:
                continue

            # Normalize model ID: strip provider prefix (openai/gpt-4o → gpt-4o)
            model_id = self._normalize_id(raw_id)

            try:
                model_entry = self._build_litellm_entry(entry)
            except Exception as e:
                logger.warning(f"LiteLLM: skipping {raw_id} — {e}")
                continue

            if model_entry is None:
                continue

            models[model_id] = model_entry

        return models

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize_id(self, raw_id: str) -> str:
        """Strip provider prefix: 'openai/gpt-4o' → 'gpt-4o'."""
        if "/" in raw_id:
            return raw_id.split("/", 1)[1]
        return raw_id

    def _build_litellm_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build a normalized model entry from a LiteLLM JSON record."""
        input_per_token = entry.get("input_cost_per_token")
        output_per_token = entry.get("output_cost_per_token")

        if input_per_token is None or output_per_token is None:
            return None

        flat_pricing = {
            "input_price": round(float(input_per_token) * _PER_TOKEN_TO_PER_MILLION, 6),
            "output_price": round(float(output_per_token) * _PER_TOKEN_TO_PER_MILLION, 6),
        }

        # Batch pricing (flat — no currency wrapper)
        batch_pricing = None
        batch_in = entry.get("input_cost_per_token_batches")
        batch_out = entry.get("output_cost_per_token_batches")
        if batch_in is not None and batch_out is not None:
            batch_pricing = {
                "input_price": round(float(batch_in) * _PER_TOKEN_TO_PER_MILLION, 6),
                "output_price": round(float(batch_out) * _PER_TOKEN_TO_PER_MILLION, 6),
            }

        # Tiered pricing (flat list — no currency wrapper)
        tiered_pricing = None
        if "tiered_pricing" in entry:
            tiers = self._parse_explicit_tiered(
                entry["tiered_pricing"],
                base_output_per_token=float(output_per_token),
            )
            if tiers:
                tiered_pricing = tiers
        elif "input_cost_per_token_above_128k_tokens" in entry:
            tiers = self._parse_inline_tiered(entry, float(output_per_token))
            if tiers:
                tiered_pricing = tiers

        # Metadata (best-effort)
        metadata: Dict[str, Any] = {
            "provider": entry.get("litellm_provider", "unknown"),
            "family": self._extract_family(entry.get("litellm_provider", ""), entry),
        }
        if isinstance(entry.get("max_tokens"), int) and entry["max_tokens"] > 0:
            metadata["context_window"] = entry["max_tokens"]
        if isinstance(entry.get("max_output_tokens"), int) and entry["max_output_tokens"] > 0:
            metadata["max_output_tokens"] = entry["max_output_tokens"]

        endpoint_entry = self._build_endpoint_entry(
            flat_pricing,
            batch_pricing=batch_pricing,
            tiered_pricing=tiered_pricing,
        )
        return self._build_model_entry(endpoint_entry, metadata)

    def _parse_explicit_tiered(
        self,
        tiered_pricing: Any,
        base_output_per_token: float,
    ) -> List[Dict[str, Any]]:
        """
        Convert LiteLLM explicit tiered_pricing to burncloud format.

        LiteLLM format: [{"range": [start, end], "input_cost_per_token": X, ...}]
        burncloud format: [{"tier_start": S, "tier_end": E, "input_price": X*1M, "output_price": Y*1M}]
        Last tier has no tier_end (open-ended).
        """
        if not isinstance(tiered_pricing, list):
            raise ValueError(f"tiered_pricing is not a list: {type(tiered_pricing)}")

        tiers: List[Dict[str, Any]] = []
        for i, tier_entry in enumerate(tiered_pricing):
            if not isinstance(tier_entry, dict):
                raise ValueError(f"tier entry {i} is not a dict")

            tier_range = tier_entry.get("range")
            if not isinstance(tier_range, list) or len(tier_range) < 1:
                raise ValueError(f"tier entry {i} missing valid 'range'")

            inp = tier_entry.get("input_cost_per_token")
            out = tier_entry.get("output_cost_per_token")
            if inp is None:
                raise ValueError(f"tier entry {i} missing 'input_cost_per_token'")

            # Use base output if tier doesn't specify its own
            output_per_token = float(out) if out is not None else base_output_per_token

            tier: Dict[str, Any] = {
                "tier_start": int(tier_range[0]),
                "input_price": round(float(inp) * _PER_TOKEN_TO_PER_MILLION, 6),
                "output_price": round(output_per_token * _PER_TOKEN_TO_PER_MILLION, 6),
            }

            is_last = (i == len(tiered_pricing) - 1)
            if not is_last and len(tier_range) >= 2 and tier_range[1] is not None:
                tier["tier_end"] = int(tier_range[1])

            tiers.append(tier)

        return tiers

    def _parse_inline_tiered(
        self,
        entry: Dict[str, Any],
        base_output_per_token: float,
    ) -> List[Dict[str, Any]]:
        """
        Convert LiteLLM inline above_128k / above_200k fields to burncloud tiers.

        Two-tier (above_128k only):
          [{start:0, end:128000}, {start:128000}]
        Three-tier (above_128k + above_200k):
          [{start:0, end:128000}, {start:128000, end:200000}, {start:200000}]

        output_price is the same base value across all tiers (flat output pricing).
        """
        base_input = entry.get("input_cost_per_token")
        above_128k = entry.get("input_cost_per_token_above_128k_tokens")
        above_200k = entry.get("input_cost_per_token_above_200k_tokens")

        if base_input is None or above_128k is None:
            return []

        out_price = round(base_output_per_token * _PER_TOKEN_TO_PER_MILLION, 6)

        tiers: List[Dict[str, Any]] = [
            {
                "tier_start": 0,
                "tier_end": 128000,
                "input_price": round(float(base_input) * _PER_TOKEN_TO_PER_MILLION, 6),
                "output_price": out_price,
            }
        ]

        if above_200k is not None:
            tiers.append({
                "tier_start": 128000,
                "tier_end": 200000,
                "input_price": round(float(above_128k) * _PER_TOKEN_TO_PER_MILLION, 6),
                "output_price": out_price,
            })
            tiers.append({
                "tier_start": 200000,
                "input_price": round(float(above_200k) * _PER_TOKEN_TO_PER_MILLION, 6),
                "output_price": out_price,
            })
        else:
            tiers.append({
                "tier_start": 128000,
                "input_price": round(float(above_128k) * _PER_TOKEN_TO_PER_MILLION, 6),
                "output_price": out_price,
            })

        return tiers

    def _extract_family(self, provider: str, entry: Dict[str, Any]) -> str:
        """Best-effort model family extraction."""
        model_name = entry.get("model_name", "")
        if not model_name:
            return provider or "unknown"
        parts = model_name.split("-")
        return "-".join(parts[:2]) if len(parts) >= 2 else parts[0]
