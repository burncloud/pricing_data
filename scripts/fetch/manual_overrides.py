"""
Manual overrides fetcher.

Loads human-verified prices from manual_overrides.json at the repo root.
Priority 200 — beats all automated sources.

Never generate entries in this file programmatically. Each entry must be
manually verified by a human against the official provider pricing URL.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

_OVERRIDES_FILENAME = "manual_overrides.json"

# Fields prefixed with "_" are metadata/annotations, not model data
_META_FIELDS = {"_verified_at", "_verified_source", "_notes"}


class ManualOverridesFetcher(BaseFetcher):
    """
    Loads manual_overrides.json and exposes it as a FetchResult.

    This fetcher does NOT make HTTP requests. It reads a local JSON file
    that contains human-verified pricing data. Because it overrides the
    entire fetch() method, _make_request / _validate_response / _parse_models
    are not used.

    Priority 200 — highest of all sources.
    """

    def __init__(self, config: Config):
        from scripts.config import FetcherConfig
        fetcher_config = FetcherConfig(
            name="manual_overrides",
            url="",  # no URL — local file only
            timeout=0.0,
            max_retries=0,
            requires_auth=False,
        )
        super().__init__(config, fetcher_config)
        self._overrides_path = config.repo_root / _OVERRIDES_FILENAME

    # ------------------------------------------------------------------
    # Override fetch() entirely — no HTTP needed
    # ------------------------------------------------------------------

    def fetch(self) -> FetchResult:
        """Load manual_overrides.json and return as a FetchResult."""
        try:
            if not self._overrides_path.exists():
                logger.warning(
                    f"manual_overrides.json not found at {self._overrides_path}; skipping"
                )
                return FetchResult(
                    source="manual_overrides",
                    success=True,  # not an error — file is optional
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    models={},
                    models_count=0,
                )

            with open(self._overrides_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            models = self._parse_overrides(data)

            logger.info(f"manual_overrides: loaded {len(models)} model(s)")
            return FetchResult(
                source="manual_overrides",
                success=True,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                models=models,
                raw_response=data,
                models_count=len(models),
            )

        except json.JSONDecodeError as e:
            logger.error(f"manual_overrides.json is not valid JSON: {e}")
            return FetchResult.error_result(
                "manual_overrides",
                f"Invalid JSON in manual_overrides.json: {e}",
            )
        except Exception as e:
            logger.exception("Unexpected error loading manual_overrides.json")
            return FetchResult.error_result(
                "manual_overrides",
                f"Unexpected error: {e}",
            )

    def _parse_overrides(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert manual_overrides.json (v5.0 pricing.json format) into the
        endpoints-based format expected by the merge pipeline.

        v5.0 input:  model → { "USD": { "text": {...}, "cache": {...} } }
        pipeline output: model → { "endpoints": { "manual": { "currency": "USD", "pricing": {...}, "cache": {...} } } }
        """
        raw_models = data.get("models", {})
        models: Dict[str, Any] = {}

        for model_id, entry in raw_models.items():
            if not isinstance(entry, dict):
                logger.warning(f"manual_overrides: skipping {model_id!r} — not a dict")
                continue

            # Collect currency keys (anything not starting with "_")
            currencies = {k: v for k, v in entry.items() if not k.startswith("_") and isinstance(v, dict)}

            if not currencies:
                logger.warning(
                    f"manual_overrides: skipping {model_id!r} — no currency pricing found"
                )
                continue

            endpoints: Dict[str, Any] = {}
            for currency, pricing_data in currencies.items():
                # Separate modality pricing from optional fields (cache, batch, tiered)
                optional_fields = ("cache", "batch", "tiered")
                pricing = {k: v for k, v in pricing_data.items() if k not in optional_fields}
                ep: Dict[str, Any] = {
                    "currency": currency,
                    "pricing": pricing,
                }
                for field in optional_fields:
                    if field in pricing_data:
                        ep[field] = pricing_data[field]

                ep_key = f"manual_{currency}"
                endpoints[ep_key] = ep

            models[model_id] = {"endpoints": endpoints}

        return models

    # ------------------------------------------------------------------
    # BaseFetcher abstract methods — not used (fetch() is overridden)
    # ------------------------------------------------------------------

    def _make_request(self) -> Optional[requests.Response]:
        raise NotImplementedError("ManualOverridesFetcher does not make HTTP requests")

    def _validate_response(self, response: requests.Response) -> bool:
        raise NotImplementedError("ManualOverridesFetcher does not make HTTP requests")

    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        raise NotImplementedError("ManualOverridesFetcher does not make HTTP requests")
