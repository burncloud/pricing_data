"""
Base class for all data fetchers with retry logic and error handling.
"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scripts.config import Config, FetcherConfig

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    source: str
    success: bool
    fetched_at: str
    models: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    models_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "fetched_at": self.fetched_at,
            "status": "success" if self.success else "error",
            "error": self.error,
            "models_count": self.models_count,
            "models": self.models,
            "raw_response": self.raw_response,
        }

    @classmethod
    def error_result(cls, source: str, error: str) -> "FetchResult":
        """Create an error result."""
        return cls(
            source=source,
            success=False,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            error=error,
        )


class BaseFetcher(ABC):
    """
    Abstract base class for data fetchers.

    Provides:
    - HTTP session with retry logic
    - Response validation
    - Error handling
    - File I/O for results
    """

    def __init__(self, config: Config, fetcher_config: FetcherConfig):
        self.config = config
        self.fetcher_config = fetcher_config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.fetcher_config.max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # SSL verification (security hardening)
        session.verify = True

        return session

    def fetch(self) -> FetchResult:
        """
        Fetch data from the source.

        Returns:
            FetchResult with models data or error
        """
        try:
            logger.info(f"Fetching from {self.fetcher_config.name}...")

            response = self._make_request()

            if response is None:
                return FetchResult.error_result(
                    self.fetcher_config.name,
                    "No response received"
                )

            # Validate response
            validated = self._validate_response(response)
            if not validated:
                return FetchResult.error_result(
                    self.fetcher_config.name,
                    "Response validation failed"
                )

            # Parse models
            models = self._parse_models(response)

            # raw_response is best-effort (HTML fetchers won't have JSON bodies)
            raw_response = None
            if hasattr(response, "json"):
                try:
                    raw_response = response.json()
                except Exception:
                    pass

            return FetchResult(
                source=self.fetcher_config.name,
                success=True,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                models=models,
                raw_response=raw_response,
                models_count=len(models),
            )

        except requests.Timeout:
            logger.error(f"Timeout fetching from {self.fetcher_config.name}")
            return FetchResult.error_result(
                self.fetcher_config.name,
                f"Request timeout after {self.fetcher_config.timeout}s"
            )
        except requests.HTTPError as e:
            logger.error(f"HTTP error from {self.fetcher_config.name}: {e}")
            return FetchResult.error_result(
                self.fetcher_config.name,
                f"HTTP error: {e.response.status_code}"
            )
        except requests.RequestException as e:
            logger.error(f"Request error from {self.fetcher_config.name}: {e}")
            return FetchResult.error_result(
                self.fetcher_config.name,
                f"Request error: {str(e)}"
            )
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from {self.fetcher_config.name}: {e}")
            return FetchResult.error_result(
                self.fetcher_config.name,
                f"Invalid JSON response: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error fetching from {self.fetcher_config.name}")
            return FetchResult.error_result(
                self.fetcher_config.name,
                f"Unexpected error: {str(e)}"
            )

    @abstractmethod
    def _make_request(self) -> Optional[requests.Response]:
        """Make the HTTP request to the data source."""
        pass

    @abstractmethod
    def _validate_response(self, response: requests.Response) -> bool:
        """Validate the response structure."""
        pass

    @abstractmethod
    def _parse_models(self, response: requests.Response) -> Dict[str, Any]:
        """Parse models from the response."""
        pass

    def _build_endpoint_entry(
        self,
        pricing: Dict[str, Any],
        *,
        cache_pricing: Optional[Dict[str, Any]] = None,
        batch_pricing: Optional[Dict[str, Any]] = None,
        tiered_pricing: Optional[Any] = None,
        base_url: Optional[str] = None,
        currency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a single endpoint entry for the endpoint-keyed model structure.

        Args:
            pricing: flat dict with input_price / output_price (no currency wrapper)
            cache_pricing: optional flat cache pricing dict
            batch_pricing: optional flat batch pricing dict
            tiered_pricing: optional tiered pricing structure
            base_url: override the fetcher config base_url (for dynamic endpoint keys)
            currency: override the fetcher config currency (for dynamic endpoint keys)

        Returns:
            {"base_url": ..., "currency": ..., "pricing": ..., ...}
        """
        entry: Dict[str, Any] = {
            "base_url": base_url if base_url is not None else self.fetcher_config.base_url,
            "currency": currency if currency is not None else self.fetcher_config.currency,
            "pricing": pricing,
        }
        if cache_pricing is not None:
            entry["cache"] = cache_pricing
        if batch_pricing is not None:
            entry["batch"] = batch_pricing
        if tiered_pricing is not None:
            entry["tiered"] = tiered_pricing
        return entry

    def _build_model_entry(
        self,
        endpoint_entry: Dict[str, Any],
        metadata: Dict[str, Any],
        endpoint_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a full model entry with endpoint-keyed pricing.

        Args:
            endpoint_entry: result of _build_endpoint_entry()
            metadata: provider metadata dict
            endpoint_key: override the fetcher config endpoint_key (for dynamic routing)

        Returns:
            {"endpoints": {endpoint_key: endpoint_entry}, "metadata": metadata}
        """
        key = endpoint_key if endpoint_key is not None else self.fetcher_config.endpoint_key
        return {
            "endpoints": {key: endpoint_entry},
            "metadata": metadata,
        }

    def save_result(self, result: FetchResult, date_str: str) -> Path:
        """
        Save fetch result to sources directory.

        Args:
            result: FetchResult to save
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Path to saved file
        """
        sources_dir = self.config.get_today_sources_dir(date_str)
        sources_dir.mkdir(parents=True, exist_ok=True)

        output_file = sources_dir / f"{self.fetcher_config.name}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {self.fetcher_config.name} data to {output_file}")
        return output_file

    def load_cached_result(self, date_str: str) -> Optional[FetchResult]:
        """
        Load cached result from previous successful fetch.

        Args:
            date_str: Date string to look for

        Returns:
            Cached FetchResult or None
        """
        cache_file = self.config.get_today_sources_dir(date_str) / f"{self.fetcher_config.name}.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return FetchResult(
                    source=data["source"],
                    success=data["status"] == "success",
                    fetched_at=data["fetched_at"],
                    models=data.get("models", {}),
                    raw_response=data.get("raw_response"),
                    error=data.get("error"),
                    models_count=data.get("models_count", 0),
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load cache: {e}")

        return None
