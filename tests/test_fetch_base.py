"""
Tests for fetch base module.
"""
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from scripts.fetch.base import BaseFetcher, FetchResult
from scripts.config import Config, FetcherConfig


class TestFetchResult:
    """Tests for FetchResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = FetchResult(
            source="test",
            success=True,
            fetched_at="2024-01-01T00:00:00Z",
            models={"gpt-4": {}},
            models_count=1,
        )

        assert result.success is True
        assert result.error is None
        assert result.models_count == 1

    def test_error_result(self):
        """Test error result factory method."""
        result = FetchResult.error_result("test", "Something went wrong")

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.source == "test"
        assert result.models == {}
        assert result.models_count == 0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = FetchResult(
            source="test",
            success=True,
            fetched_at="2024-01-01T00:00:00Z",
            models={"gpt-4": {}},
            models_count=1,
        )

        d = result.to_dict()

        assert d["source"] == "test"
        assert d["status"] == "success"
        assert d["models_count"] == 1
        assert "fetched_at" in d


class TestBaseFetcher:
    """Tests for BaseFetcher abstract class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        return Mock(spec=Config)

    @pytest.fixture
    def fetcher_config(self):
        """Create test fetcher config."""
        return FetcherConfig(
            name="test-fetcher",
            url="https://api.example.com/v1/models",
            timeout=10.0,
            max_retries=2,
        )

    @pytest.fixture
    def concrete_fetcher(self, mock_config, fetcher_config):
        """Create concrete fetcher implementation for testing."""
        class ConcreteFetcher(BaseFetcher):
            def _make_request(self):
                return None

            def _validate_response(self, response):
                return True

            def _parse_models(self, response):
                return {}

        return ConcreteFetcher(mock_config, fetcher_config)

    def test_session_creation(self, concrete_fetcher):
        """Test HTTP session is created with retry logic."""
        session = concrete_fetcher.session

        assert session is not None
        assert session.verify is True

    def test_save_result(self, concrete_fetcher, tmp_path, mock_config):
        """Test saving fetch result to file."""
        # Mock config to use temp directory
        mock_config.get_today_sources_dir.return_value = tmp_path

        result = FetchResult(
            source="test",
            success=True,
            fetched_at="2024-01-01T00:00:00Z",
            models={"gpt-4": {}},
            models_count=1,
        )

        output_path = concrete_fetcher.save_result(result, "2024-01-01")

        assert output_path.exists()
        assert output_path.name == "test-fetcher.json"

        # Verify content
        with open(output_path) as f:
            data = json.load(f)

        assert data["source"] == "test"
        assert data["status"] == "success"

    def test_load_cached_result(self, concrete_fetcher, tmp_path, mock_config):
        """Test loading cached result."""
        mock_config.get_today_sources_dir.return_value = tmp_path

        # Create a cached file
        cached_data = {
            "source": "test",
            "status": "success",
            "fetched_at": "2024-01-01T00:00:00Z",
            "models": {"gpt-4": {}},
            "models_count": 1,
        }

        cache_file = tmp_path / "test-fetcher.json"
        with open(cache_file, "w") as f:
            json.dump(cached_data, f)

        # Load cached result
        result = concrete_fetcher.load_cached_result("2024-01-01")

        assert result is not None
        assert result.success is True
        assert result.source == "test"
        assert "gpt-4" in result.models

    def test_load_cached_result_not_found(self, concrete_fetcher, tmp_path, mock_config):
        """Test loading cached result when file doesn't exist."""
        mock_config.get_today_sources_dir.return_value = tmp_path

        result = concrete_fetcher.load_cached_result("2024-01-01")

        assert result is None


class TestFetcherErrorHandling:
    """Tests for error handling in fetchers."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = Mock(spec=Config)
        config.get_today_sources_dir = Mock(return_value=Path("/tmp"))
        return config

    def test_timeout_error(self, mock_config):
        """Test timeout handling."""
        import requests

        class TimeoutFetcher(BaseFetcher):
            def _make_request(self):
                raise requests.Timeout("Request timed out")

            def _validate_response(self, response):
                return True

            def _parse_models(self, response):
                return {}

        fetcher_config = FetcherConfig(name="test", url="https://example.com", timeout=1.0)
        fetcher = TimeoutFetcher(mock_config, fetcher_config)

        result = fetcher.fetch()

        assert result.success is False
        assert "timeout" in result.error.lower()

    def test_http_error(self, mock_config):
        """Test HTTP error handling."""
        import requests

        class HTTPErrorFetcher(BaseFetcher):
            def _make_request(self):
                response = Mock()
                response.status_code = 500
                raise requests.HTTPError(response=response)

            def _validate_response(self, response):
                return True

            def _parse_models(self, response):
                return {}

        fetcher_config = FetcherConfig(name="test", url="https://example.com")
        fetcher = HTTPErrorFetcher(mock_config, fetcher_config)

        result = fetcher.fetch()

        assert result.success is False
        assert "500" in result.error

    def test_json_decode_error(self, mock_config):
        """Test JSON decode error handling."""
        class JSONErrorFetcher(BaseFetcher):
            def _make_request(self):
                response = Mock()
                response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
                return response

            def _validate_response(self, response):
                return True

            def _parse_models(self, response):
                return {}

        fetcher_config = FetcherConfig(name="test", url="https://example.com")
        fetcher = JSONErrorFetcher(mock_config, fetcher_config)

        result = fetcher.fetch()

        # raw_response is best-effort: a JSONDecodeError there should NOT fail the
        # fetch (HTML-based fetchers have responses that are not JSON). The fetch
        # succeeds and raw_response is silently set to None.
        assert result.success is True
        assert result.raw_response is None
