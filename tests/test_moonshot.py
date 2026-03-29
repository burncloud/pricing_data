"""
Tests for MoonshotFetcher.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.moonshot import MoonshotFetcher


@pytest.fixture
def fetcher():
    return MoonshotFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


_PRICING_TABLE = """
<html><body>
<table>
  <thead>
    <tr><th>模型</th><th>输入（元/百万Tokens）</th><th>输出（元/百万Tokens）</th></tr>
  </thead>
  <tbody>
    <tr><td>kimi-k2.5</td><td>2</td><td>10</td></tr>
    <tr><td>kimi-k2-thinking</td><td>4</td><td>16</td></tr>
    <tr><td>moonshot-v1-8k</td><td>12</td><td>12</td></tr>
  </tbody>
</table>
</body></html>
"""


class TestParseModels:
    def test_parses_kimi_model(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        assert "kimi-k2.5" in models

    def test_parses_moonshot_model(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        assert "moonshot-v1-8k" in models

    def test_input_price_cny(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["kimi-k2.5"]["endpoints"]["api.moonshot.cn"]
        assert ep["pricing"]["in"] == pytest.approx(2.0)

    def test_output_price_cny(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["kimi-k2.5"]["endpoints"]["api.moonshot.cn"]
        assert ep["pricing"]["out"] == pytest.approx(10.0)

    def test_currency_is_cny(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["kimi-k2.5"]["endpoints"]["api.moonshot.cn"]
        assert ep["currency"] == "CNY"

    def test_metadata_provider(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        assert models["kimi-k2.5"]["metadata"]["provider"] == "moonshot"

    def test_empty_on_no_models(self, fetcher):
        resp = _make_response("<html>kimi is great but no table</html>")
        models = fetcher._parse_models(resp)
        assert isinstance(models, dict)


class TestValidateResponse:
    def test_valid(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        assert fetcher._validate_response(resp) is True

    def test_missing_kimi_and_moonshot(self, fetcher):
        resp = _make_response("<html>some other page</html>")
        assert fetcher._validate_response(resp) is False


class TestExtractFamily:
    def test_thinking_suffix_removed(self, fetcher):
        assert fetcher._extract_family("kimi-k2-thinking-turbo") == "kimi-k2"

    def test_plain_model(self, fetcher):
        assert fetcher._extract_family("moonshot-v1") == "moonshot-v1"


class TestFetchIntegration:
    def test_fetch_success(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is True
        assert result.source == "moonshot"

    def test_fetch_exception(self, fetcher):
        with patch.object(fetcher, "_make_request", side_effect=Exception("timeout")):
            result = fetcher.fetch()
        assert result.success is False
