"""
Tests for XAIFetcher.

All network calls are mocked — tests exercise pure-Python parsing helpers.
The real xAI docs page embeds pricing as escaped JSON (Next.js SSR), not
as a visible HTML table. Mock HTML mirrors that format.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.xai import XAIFetcher, _nanocents_to_mtok


@pytest.fixture
def fetcher():
    return XAIFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


def _make_lm_block(name: str, inp_n: int, out_n: int, cache_n: int = 0) -> str:
    """
    Build a fake LanguageModel JSON block matching the real xAI page format.

    inp_n / out_n / cache_n are nanocents/token values.
    E.g. inp_n=2000 → $2.00/MTok.
    """
    return (
        f'LanguageModel\\",'
        f'\\"name\\":\\"{name}\\",'
        f'\\"version\\":\\"1.0\\",'
        f'\\"inputModalities\\":[1],\\"outputModalities\\":[1],'
        f'\\"promptTextTokenPrice\\":\\"$n{inp_n}\\",'
        f'\\"promptImageTokenPrice\\":\\"$n0\\",'
        f'\\"cachedPromptTokenPrice\\":\\"$n{cache_n}\\",'
        f'\\"completionTextTokenPrice\\":\\"$n{out_n}\\",'
        f'\\"searchPrice\\":\\"$n0\\"'
    )


# Single model with cache
_PAGE_WITH_CACHE = f"<html><body>{_make_lm_block('grok-4.20-0309-reasoning', 2000, 6000, 200)}</body></html>"

# Two models
_PAGE_TWO_MODELS = (
    "<html><body>"
    + _make_lm_block("grok-4.20-0309-reasoning", 2000, 6000, 200)
    + _make_lm_block("grok-3-mini", 300, 500, 75)
    + "</body></html>"
)

# Model with zero cache (no effective cache price)
_PAGE_ZERO_CACHE = f"<html><body>{_make_lm_block('grok-3', 3000, 15000, 0)}</body></html>"


class TestNanocentsConversion:
    def test_basic(self):
        assert _nanocents_to_mtok("2000") == pytest.approx(2.00)

    def test_large(self):
        assert _nanocents_to_mtok("30000") == pytest.approx(30.00)

    def test_small(self):
        assert _nanocents_to_mtok("300") == pytest.approx(0.30)


class TestParseModels:
    def test_parses_reasoning_model(self, fetcher):
        resp = _make_response(_PAGE_WITH_CACHE)
        models = fetcher._parse_models(resp)
        assert "grok-4.20-0309-reasoning" in models

    def test_parses_multiple_models(self, fetcher):
        resp = _make_response(_PAGE_TWO_MODELS)
        models = fetcher._parse_models(resp)
        assert len(models) == 2

    def test_input_price(self, fetcher):
        resp = _make_response(_PAGE_WITH_CACHE)
        models = fetcher._parse_models(resp)
        ep = models["grok-4.20-0309-reasoning"]["endpoints"]["api.x.ai"]
        assert ep["pricing"]["in"] == pytest.approx(2.00)

    def test_output_price(self, fetcher):
        resp = _make_response(_PAGE_WITH_CACHE)
        models = fetcher._parse_models(resp)
        ep = models["grok-4.20-0309-reasoning"]["endpoints"]["api.x.ai"]
        assert ep["pricing"]["out"] == pytest.approx(6.00)

    def test_cache_price(self, fetcher):
        resp = _make_response(_PAGE_WITH_CACHE)
        models = fetcher._parse_models(resp)
        ep = models["grok-4.20-0309-reasoning"]["endpoints"]["api.x.ai"]
        assert "cache" in ep
        assert ep["cache"]["read"] == pytest.approx(0.20)

    def test_zero_cache_included(self, fetcher):
        """Cache price of 0 is still stored."""
        resp = _make_response(_PAGE_ZERO_CACHE)
        models = fetcher._parse_models(resp)
        ep = models["grok-3"]["endpoints"]["api.x.ai"]
        assert ep["cache"]["read"] == pytest.approx(0.0)

    def test_metadata_provider(self, fetcher):
        resp = _make_response(_PAGE_WITH_CACHE)
        models = fetcher._parse_models(resp)
        assert models["grok-4.20-0309-reasoning"]["metadata"]["provider"] == "xai"

    def test_currency_is_usd(self, fetcher):
        resp = _make_response(_PAGE_WITH_CACHE)
        models = fetcher._parse_models(resp)
        ep = models["grok-4.20-0309-reasoning"]["endpoints"]["api.x.ai"]
        assert ep["currency"] == "USD"

    def test_empty_on_no_blocks(self, fetcher):
        resp = _make_response("<html><body>No pricing here.</body></html>")
        models = fetcher._parse_models(resp)
        assert models == {}

    def test_skips_non_grok_blocks(self, fetcher):
        non_grok = (
            'LanguageModel\\",'
            '\\"name\\":\\"claude-3-5-sonnet\\",'
            '\\"promptTextTokenPrice\\":\\"$n3000\\",'
            '\\"cachedPromptTokenPrice\\":\\"$n750\\",'
            '\\"completionTextTokenPrice\\":\\"$n15000\\"'
        )
        resp = _make_response(f"<html><body>{non_grok}</body></html>")
        models = fetcher._parse_models(resp)
        assert "claude-3-5-sonnet" not in models
        assert models == {}


class TestValidateResponse:
    def test_valid_response(self, fetcher):
        resp = _make_response(_PAGE_WITH_CACHE)
        assert fetcher._validate_response(resp) is True

    def test_missing_grok(self, fetcher):
        resp = _make_response("<html>Some page without model names</html>")
        assert fetcher._validate_response(resp) is False

    def test_missing_prices(self, fetcher):
        resp = _make_response("<html>grok-4 model info, no prices</html>")
        assert fetcher._validate_response(resp) is False


class TestExtractFamily:
    def test_reasoning_suffix_removed(self, fetcher):
        assert fetcher._extract_family("grok-4.20-0309-reasoning") == "grok-4.20-0309"

    def test_fast_suffix_removed(self, fetcher):
        assert fetcher._extract_family("grok-4-1-fast-non-reasoning") == "grok-4-1"

    def test_plain_model(self, fetcher):
        assert fetcher._extract_family("grok-4") == "grok-4"


class TestFetchIntegration:
    def test_fetch_success(self, fetcher):
        resp = _make_response(_PAGE_TWO_MODELS)
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is True
        assert result.models_count == 2
        assert result.source == "xai"
        assert "grok-4.20-0309-reasoning" in result.models

    def test_fetch_empty_returns_error(self, fetcher):
        resp = _make_response("<html></html>")
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is False

    def test_fetch_exception_returns_error(self, fetcher):
        with patch.object(fetcher, "_make_request", side_effect=Exception("timeout")):
            result = fetcher.fetch()
        assert result.success is False
        assert "timeout" in result.error
