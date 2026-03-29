"""
Tests for AliyunFetcher.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.aliyun import AliyunFetcher


@pytest.fixture
def fetcher():
    return AliyunFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


_PRICING_TABLE = """
<html><body>
<table>
  <thead>
    <tr><th>Model</th><th>Input ($/MTok)</th><th>Output ($/MTok)</th></tr>
  </thead>
  <tbody>
    <tr><td>qwen-max</td><td>$1.6</td><td>$6.4</td></tr>
    <tr><td>qwen-plus</td><td>$0.4</td><td>$1.2</td></tr>
    <tr><td>qwen-turbo</td><td>$0.05</td><td>$0.20</td></tr>
  </tbody>
</table>
</body></html>
"""

_TIERED_TABLE = """
<table>
  <tr><th>Model</th><th>Input</th><th>Output</th></tr>
  <tr><td>qwen3-max</td><td>$1.2-$3.0</td><td>$6-$15</td></tr>
</table>
"""


class TestParseModels:
    def test_parses_qwen_max(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        assert "qwen-max" in models

    def test_parses_multiple_models(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        assert len(models) >= 2

    def test_input_price(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["qwen-max"]["endpoints"]["dashscope.aliyuncs.com"]
        assert ep["pricing"]["in"] == pytest.approx(1.6)

    def test_output_price(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["qwen-max"]["endpoints"]["dashscope.aliyuncs.com"]
        assert ep["pricing"]["out"] == pytest.approx(6.4)

    def test_tiered_takes_first_value(self, fetcher):
        """Tiered pricing 'X-Y' → take first (lower) value."""
        resp = _make_response(_TIERED_TABLE)
        models = fetcher._parse_models(resp)
        assert "qwen3-max" in models
        ep = models["qwen3-max"]["endpoints"]["dashscope.aliyuncs.com"]
        assert ep["pricing"]["in"] == pytest.approx(1.2)
        assert ep["pricing"]["out"] == pytest.approx(6.0)

    def test_metadata_provider(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        assert models["qwen-max"]["metadata"]["provider"] == "aliyun"

    def test_currency_usd(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["qwen-max"]["endpoints"]["dashscope.aliyuncs.com"]
        assert ep["currency"] == "USD"

    def test_empty_on_no_table(self, fetcher):
        resp = _make_response("<html><body>No models here.</body></html>")
        models = fetcher._parse_models(resp)
        assert models == {}


class TestValidateResponse:
    def test_valid_response(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        assert fetcher._validate_response(resp) is True

    def test_missing_qwen(self, fetcher):
        resp = _make_response("<html>Some page without any model names $1.00</html>")
        assert fetcher._validate_response(resp) is False

    def test_missing_dollar(self, fetcher):
        resp = _make_response("<html>qwen-max model info, no prices</html>")
        assert fetcher._validate_response(resp) is False


class TestExtractFamily:
    def test_qwen_max(self, fetcher):
        assert fetcher._extract_family("qwen-max") == "qwen-max"

    def test_version_suffix_removed(self, fetcher):
        assert fetcher._extract_family("qwen-plus-2024-09-19") == "qwen-plus"

    def test_preview_suffix_removed(self, fetcher):
        assert fetcher._extract_family("qwen3-max-preview") == "qwen3-max"


class TestFetchIntegration:
    def test_fetch_success(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is True
        assert result.models_count >= 2
        assert result.source == "aliyun"

    def test_fetch_exception_returns_error(self, fetcher):
        with patch.object(fetcher, "_make_request", side_effect=Exception("timeout")):
            result = fetcher.fetch()
        assert result.success is False
        assert "timeout" in result.error
