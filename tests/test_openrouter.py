"""
Tests for OpenRouterFetcher.
"""
import pytest
from unittest.mock import Mock

from scripts.config import config
from scripts.fetch.openrouter import OpenRouterFetcher


@pytest.fixture
def fetcher():
    return OpenRouterFetcher(config)


def _make_response(data: dict) -> Mock:
    resp = Mock()
    resp.json.return_value = data
    resp.headers = {"Content-Type": "application/json"}
    return resp


class TestExtractPricing:

    def test_normal_prices(self, fetcher):
        """Standard positive prices are converted from per-token to per-MTok."""
        pricing = fetcher._extract_pricing(
            {"prompt": "0.0000025", "completion": "0.00001"},
            "openai/gpt-4o",
        )
        assert pricing["USD"]["input_price"] == pytest.approx(2.5)
        assert pricing["USD"]["output_price"] == pytest.approx(10.0)

    def test_negative_price_skipped(self, fetcher):
        """OpenRouter sentinel value -1 per-token must be rejected (not -1M per MTok)."""
        pricing = fetcher._extract_pricing(
            {"prompt": "-0.000001", "completion": "-0.000001"},
            "openrouter/auto",
        )
        assert pricing == {}

    def test_negative_input_only_skipped(self, fetcher):
        """Negative input price alone is enough to skip the model."""
        pricing = fetcher._extract_pricing(
            {"prompt": "-0.000001", "completion": "0.00001"},
            "openrouter/auto",
        )
        assert pricing == {}

    def test_negative_output_only_skipped(self, fetcher):
        """Negative output price alone is enough to skip the model."""
        pricing = fetcher._extract_pricing(
            {"prompt": "0.000001", "completion": "-0.000001"},
            "openrouter/bodybuilder",
        )
        assert pricing == {}

    def test_zero_price_kept(self, fetcher):
        """Zero price is valid (free models) and must NOT be filtered."""
        pricing = fetcher._extract_pricing(
            {"prompt": "0", "completion": "0"},
            "some/free-model",
        )
        assert pricing != {}
        assert pricing["USD"]["input_price"] == 0.0

    def test_missing_prompt_skipped(self, fetcher):
        pricing = fetcher._extract_pricing({}, "some/model")
        assert pricing == {}


class TestValidateResponse:

    def test_valid_response(self, fetcher):
        resp = _make_response({"data": [{"id": "openai/gpt-4o", "pricing": {}}]})
        assert fetcher._validate_response(resp) is True

    def test_missing_data_field(self, fetcher):
        resp = _make_response({"models": []})
        assert fetcher._validate_response(resp) is False

    def test_data_not_list(self, fetcher):
        resp = _make_response({"data": {"id": "x"}})
        assert fetcher._validate_response(resp) is False


class TestNormalizeModelId:

    def test_strips_provider_prefix(self, fetcher):
        assert fetcher._normalize_model_id("openai/gpt-4o") == "gpt-4o"
        assert fetcher._normalize_model_id("anthropic/claude-3.5-sonnet") == "claude-3.5-sonnet"

    def test_no_prefix_unchanged(self, fetcher):
        assert fetcher._normalize_model_id("gpt-4o") == "gpt-4o"


class TestParseModels:

    def test_negative_price_models_excluded_from_output(self, fetcher):
        """Models with sentinel pricing must not appear in parsed output at all."""
        resp = _make_response({
            "data": [
                {
                    "id": "openrouter/auto",
                    "pricing": {"prompt": "-0.000001", "completion": "-0.000001"},
                    "context_length": 200000,
                    "architecture": {},
                    "top_provider": {},
                },
                {
                    "id": "openai/gpt-4o",
                    "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                    "context_length": 128000,
                    "architecture": {},
                    "top_provider": {},
                },
            ]
        })
        models = fetcher._parse_models(resp)
        assert "auto" not in models
        assert "gpt-4o" in models
