"""
Tests for MistralFetcher.

curl_cffi is available in test env but all network calls are mocked.
The real Mistral page embeds pricing as double-escaped JSON (Next.js SSR).
Mock HTML mirrors that format.
"""
import pytest
from unittest.mock import patch, MagicMock

from scripts.config import config
from scripts.fetch.mistral import MistralFetcher, _decode_price_value


@pytest.fixture
def fetcher():
    return MistralFetcher(config)


def _make_block(api_name: str, inp: float, out: float) -> str:
    """
    Build a fake api_endpoint+price block matching the real Mistral page format.

    Prices use the unicode-escaped HTML format: \\u003cp\\u003e$X\\u003c/p\\u003e
    """
    return (
        f'\\"api_endpoint\\":\\"{api_name}\\",'
        f'\\"price\\":[{{'
        f'\\"value\\":\\"Input (/M tokens)\\",'
        f'\\"price_dollar\\":\\"\\u003cp\\u003e${inp}\\u003c/p\\u003e\\"}},'
        f'{{\\"value\\":\\"Output (/M tokens)\\",'
        f'\\"price_dollar\\":\\"\\u003cp\\u003e${out}\\u003c/p\\u003e\\"}}]'
    )


def _make_block_double_dollar(api_name: str, inp: float, out: float) -> str:
    """Price block using the '$$X.XX' format (alternate encoding on the page)."""
    return (
        f'\\"api_endpoint\\":\\"{api_name}\\",'
        f'\\"price\\":[{{'
        f'\\"value\\":\\"Input (/M tokens)\\",'
        f'\\"price_dollar\\":\\"$${inp}\\"}},'
        f'{{\\"value\\":\\"Output (/M tokens)\\",'
        f'\\"price_dollar\\":\\"$${out}\\"}}]'
    )


_PAGE_SINGLE = f"<html><body>{_make_block('mistral-large-latest', 2.0, 6.0)}</body></html>"
_PAGE_DOUBLE_DOLLAR = f"<html><body>{_make_block_double_dollar('mistral-small-latest', 0.2, 0.6)}</body></html>"
_PAGE_TWO_MODELS = (
    "<html><body>"
    + _make_block("mistral-large-latest", 2.0, 6.0)
    + _make_block("codestral-latest", 0.3, 0.9)
    + "</body></html>"
)


class TestDecodePriceValue:
    def test_unicode_escaped_html(self):
        # \\u003cp\\u003e$0.15\\u003c/p\\u003e → 0.15
        raw = "\\u003cp\\u003e$0.15\\u003c/p\\u003e"
        assert _decode_price_value(raw) == pytest.approx(0.15)

    def test_double_dollar(self):
        assert _decode_price_value("$$0.5") == pytest.approx(0.5)

    def test_plain_dollar(self):
        assert _decode_price_value("$2.0") == pytest.approx(2.0)

    def test_non_numeric_returns_none(self):
        assert _decode_price_value("Custom") is None

    def test_per_page_billing_returns_none(self):
        assert _decode_price_value("$2 / 1,000 pages") is None


class TestParseHtml:
    def test_parses_single_model(self, fetcher):
        models = fetcher._parse_html(_PAGE_SINGLE)
        assert "mistral-large-latest" in models

    def test_input_output_prices(self, fetcher):
        models = fetcher._parse_html(_PAGE_SINGLE)
        ep = models["mistral-large-latest"]["endpoints"]["api.mistral.ai"]
        assert ep["pricing"]["in"] == pytest.approx(2.0)
        assert ep["pricing"]["out"] == pytest.approx(6.0)

    def test_parses_double_dollar_format(self, fetcher):
        models = fetcher._parse_html(_PAGE_DOUBLE_DOLLAR)
        assert "mistral-small-latest" in models
        ep = models["mistral-small-latest"]["endpoints"]["api.mistral.ai"]
        assert ep["pricing"]["in"] == pytest.approx(0.2)

    def test_parses_multiple_models(self, fetcher):
        models = fetcher._parse_html(_PAGE_TWO_MODELS)
        assert len(models) == 2
        assert "mistral-large-latest" in models
        assert "codestral-latest" in models

    def test_empty_html(self, fetcher):
        models = fetcher._parse_html("<html></html>")
        assert models == {}

    def test_metadata_provider(self, fetcher):
        models = fetcher._parse_html(_PAGE_SINGLE)
        assert models["mistral-large-latest"]["metadata"]["provider"] == "mistral"

    def test_currency_usd(self, fetcher):
        models = fetcher._parse_html(_PAGE_SINGLE)
        ep = models["mistral-large-latest"]["endpoints"]["api.mistral.ai"]
        assert ep["currency"] == "USD"

    def test_skips_models_without_both_prices(self, fetcher):
        """OCR / voice models with non-token pricing should be skipped."""
        no_in_out = (
            '\\"api_endpoint\\":\\"mistral-ocr-latest\\",'
            '\\"price\\":[{\\"value\\":\\"Per page\\",\\"price_dollar\\":\\"$$3 / 1,000 pages\\"}]'
        )
        models = fetcher._parse_html(f"<html>{no_in_out}</html>")
        assert "mistral-ocr-latest" not in models


class TestFetchCurlCffiMissing:
    def test_returns_error_when_curl_cffi_missing(self, fetcher):
        with patch.dict("sys.modules", {"curl_cffi": None, "curl_cffi.requests": None}):
            result = fetcher.fetch()
        assert result.success is False
        assert "curl_cffi" in result.error


class TestFetchWithMockedHtml:
    def test_successful_fetch(self, fetcher):
        mock_models = {
            "mistral-large-latest": {
                "endpoints": {"api.mistral.ai": {
                    "base_url": "https://api.mistral.ai/v1",
                    "currency": "USD",
                    "pricing": {"in": 2.0, "out": 6.0},
                }},
                "metadata": {"provider": "mistral", "family": "mistral-large"},
            }
        }
        with patch.object(fetcher, "_fetch_html", return_value="<html></html>"), \
             patch.object(fetcher, "_parse_html", return_value=mock_models):
            result = fetcher.fetch()
        assert result.success is True
        assert result.models_count == 1
        assert result.source == "mistral"
        assert "mistral-large-latest" in result.models

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


class TestExtractFamily:
    def test_latest_suffix_removed(self, fetcher):
        assert fetcher._extract_family("codestral-latest") == "codestral"

    def test_plain_model(self, fetcher):
        assert fetcher._extract_family("mistral-small") == "mistral-small"

    def test_numeric_suffix_removed(self, fetcher):
        assert fetcher._extract_family("mistral-large-2") == "mistral-large"
