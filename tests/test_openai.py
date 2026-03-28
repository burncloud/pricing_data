"""
Tests for OpenAIFetcher.

curl_cffi is available in the test environment but all network calls are mocked.
Tests exercise pure-Python parsing helpers or mock _fetch_html / _parse_html.
"""
import pytest
from unittest.mock import patch, MagicMock

from scripts.config import config
from scripts.fetch.openai import OpenAIFetcher


@pytest.fixture
def fetcher():
    return OpenAIFetcher(config)


# ---------------------------------------------------------------------------
# _normalize_display_name
# ---------------------------------------------------------------------------

class TestNormalizeDisplayName:
    def test_simple_model(self, fetcher):
        assert fetcher._normalize_display_name("GPT-4o") == "gpt-4o"

    def test_model_with_qualifier(self, fetcher):
        assert fetcher._normalize_display_name("GPT-4o mini") == "gpt-4o-mini"

    def test_model_with_nano(self, fetcher):
        assert fetcher._normalize_display_name("GPT-4o nano") == "gpt-4o-nano"

    def test_o_series(self, fetcher):
        assert fetcher._normalize_display_name("o3-mini") == "o3-mini"

    def test_already_lowercase(self, fetcher):
        assert fetcher._normalize_display_name("gpt-4o") == "gpt-4o"

    def test_extra_whitespace(self, fetcher):
        assert fetcher._normalize_display_name("  GPT-4o  ") == "gpt-4o"

    def test_multi_word_qualifier(self, fetcher):
        assert fetcher._normalize_display_name("GPT-4o mini turbo") == "gpt-4o-mini-turbo"

    def test_new_model_naming(self, fetcher):
        assert fetcher._normalize_display_name("GPT-5.4") == "gpt-5.4"
        assert fetcher._normalize_display_name("GPT-5.4 mini") == "gpt-5.4-mini"


# ---------------------------------------------------------------------------
# _extract_family
# ---------------------------------------------------------------------------

class TestExtractFamily:
    def test_gpt4o(self, fetcher):
        assert fetcher._extract_family("GPT-4o") == "gpt-4o"

    def test_gpt4o_mini(self, fetcher):
        assert fetcher._extract_family("GPT-4o mini") == "gpt-4o"

    def test_gpt4o_nano(self, fetcher):
        assert fetcher._extract_family("GPT-4o nano") == "gpt-4o"

    def test_o3_mini(self, fetcher):
        assert fetcher._extract_family("o3-mini") == "o3"

    def test_plain_name(self, fetcher):
        assert fetcher._extract_family("GPT-4o") == "gpt-4o"


# ---------------------------------------------------------------------------
# _build_model_entry_from_prices
# ---------------------------------------------------------------------------

class TestBuildModelEntryFromPrices:
    def test_basic_input_output(self, fetcher):
        entry = fetcher._build_model_entry_from_prices(
            "GPT-4o", {"input": 2.50, "output": 10.00}
        )
        assert entry is not None
        ep = entry["endpoints"]["api.openai.com"]
        assert ep["pricing"]["input_price"] == pytest.approx(2.50)
        assert ep["pricing"]["output_price"] == pytest.approx(10.00)

    def test_with_cached_input(self, fetcher):
        entry = fetcher._build_model_entry_from_prices(
            "GPT-4o", {"input": 2.50, "cached input": 0.25, "output": 10.00}
        )
        assert entry is not None
        ep = entry["endpoints"]["api.openai.com"]
        assert "cache_pricing" in ep
        assert ep["cache_pricing"]["cache_read_input_price"] == pytest.approx(0.25)

    def test_no_cache_when_absent(self, fetcher):
        entry = fetcher._build_model_entry_from_prices(
            "GPT-4o", {"input": 2.50, "output": 10.00}
        )
        ep = entry["endpoints"]["api.openai.com"]
        assert "cache_pricing" not in ep

    def test_missing_output_returns_none(self, fetcher):
        entry = fetcher._build_model_entry_from_prices("GPT-4o", {"input": 2.50})
        assert entry is None

    def test_missing_input_returns_none(self, fetcher):
        entry = fetcher._build_model_entry_from_prices("GPT-4o", {"output": 10.00})
        assert entry is None

    def test_image_only_model_skipped(self, fetcher):
        """Non-token pricing has no 'input' or 'output' keys."""
        entry = fetcher._build_model_entry_from_prices("GPT-image", {})
        assert entry is None

    def test_metadata_populated(self, fetcher):
        entry = fetcher._build_model_entry_from_prices(
            "GPT-4o", {"input": 2.50, "output": 10.00}
        )
        assert entry["metadata"]["provider"] == "openai"
        assert entry["metadata"]["family"] == "gpt-4o"

    def test_large_price(self, fetcher):
        entry = fetcher._build_model_entry_from_prices(
            "Expensive Model", {"input": 1000.0, "output": 2000.0}
        )
        assert entry is not None
        ep = entry["endpoints"]["api.openai.com"]
        assert ep["pricing"]["input_price"] == pytest.approx(1000.0)
        assert ep["pricing"]["output_price"] == pytest.approx(2000.0)


# ---------------------------------------------------------------------------
# _parse_html
# ---------------------------------------------------------------------------

class TestParseHtml:
    def _make_html(self, cards: list) -> str:
        """Build minimal HTML with model cards."""
        spans = ""
        for name, prices in cards:
            price_spans = "".join(
                f'<span class="whitespace-nowrap">{label}:<br/>${value} / 1M tokens</span>'
                for label, value in prices.items()
            )
            spans += f'<h2 class="text-h4">{name}</h2>{price_spans}'
        return f"<html><body>{spans}</body></html>"

    def test_parses_single_model(self, fetcher):
        html = self._make_html([
            ("GPT-5.4", {"Input": "2.50", "Cached input": "0.25", "Output": "15.00"}),
        ])
        models = fetcher._parse_html(html)
        assert "gpt-5.4" in models
        ep = models["gpt-5.4"]["endpoints"]["api.openai.com"]
        assert ep["pricing"]["input_price"] == pytest.approx(2.50)
        assert ep["pricing"]["output_price"] == pytest.approx(15.00)
        assert ep["cache_pricing"]["cache_read_input_price"] == pytest.approx(0.25)

    def test_parses_multiple_models(self, fetcher):
        html = self._make_html([
            ("GPT-5.4", {"Input": "2.50", "Output": "15.00"}),
            ("GPT-5.4 mini", {"Input": "0.750", "Output": "4.500"}),
        ])
        models = fetcher._parse_html(html)
        assert len(models) == 2
        assert "gpt-5.4" in models
        assert "gpt-5.4-mini" in models

    def test_skips_non_token_models(self, fetcher):
        """Model with no $/1M token spans produces no entry."""
        html = '<h2 class="text-h4">GPT-image-1.5</h2><p>$0.000263 per image</p>'
        models = fetcher._parse_html(html)
        assert len(models) == 0

    def test_empty_html(self, fetcher):
        models = fetcher._parse_html("<html></html>")
        assert models == {}


# ---------------------------------------------------------------------------
# fetch() — curl_cffi not installed
# ---------------------------------------------------------------------------

class TestFetchCurlCffiMissing:
    def test_returns_error_when_curl_cffi_missing(self, fetcher):
        with patch.dict("sys.modules", {"curl_cffi": None, "curl_cffi.requests": None}):
            result = fetcher.fetch()

        assert result.success is False
        assert "curl_cffi" in result.error


# ---------------------------------------------------------------------------
# fetch() — mocked _fetch_html / _parse_html
# ---------------------------------------------------------------------------

class TestFetchWithMockedHtml:
    def test_successful_fetch(self, fetcher):
        mock_models = {
            "gpt-5.4": {
                "endpoints": {"api.openai.com": {
                    "base_url": "https://api.openai.com/v1",
                    "currency": "USD",
                    "pricing": {"input_price": 2.5, "output_price": 15.0},
                }},
                "metadata": {"provider": "openai", "family": "gpt-5.4"},
            },
        }

        with patch.object(fetcher, "_fetch_html", return_value="<html></html>"), \
             patch.object(fetcher, "_parse_html", return_value=mock_models):
            result = fetcher.fetch()

        assert result.success is True
        assert result.models_count == 1
        assert result.source == "openai"
        assert "gpt-5.4" in result.models

    def test_empty_parse_returns_error(self, fetcher):
        with patch.object(fetcher, "_fetch_html", return_value="<html></html>"), \
             patch.object(fetcher, "_parse_html", return_value={}):
            result = fetcher.fetch()

        assert result.success is False
        assert "No models" in result.error

    def test_fetch_exception_returns_error(self, fetcher):
        with patch.object(fetcher, "_fetch_html", side_effect=Exception("connection refused")):
            result = fetcher.fetch()

        assert result.success is False
        assert "connection refused" in result.error
