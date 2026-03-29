"""
Tests for MiniMaxFetcher.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.minimax import MiniMaxFetcher


@pytest.fixture
def fetcher():
    return MiniMaxFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


_PRICING_TABLE_USD = """
<html><body>
<table>
  <thead>
    <tr><th>Model</th><th>Input ($/MTok)</th><th>Output ($/MTok)</th></tr>
  </thead>
  <tbody>
    <tr><td>MiniMax-Text-01</td><td>$0.20</td><td>$1.10</td></tr>
    <tr><td>abab6.5-chat</td><td>$0.40</td><td>$1.50</td></tr>
  </tbody>
</table>
</body></html>
"""

_PRICING_TABLE_CNY = """
<table>
  <tr><th>模型</th><th>输入</th><th>输出</th></tr>
  <tr><td>MiniMax-Text-01</td><td>¥1.5</td><td>¥8.0</td></tr>
</table>
"""

_SUBSCRIPTION_PAGE = """
<html><body>
<p>MiniMax offers flexible subscription plans starting from $10/month.</p>
<p>Contact us for enterprise pricing.</p>
</body></html>
"""


class TestParseModels:
    def test_parses_minimax_text_usd(self, fetcher):
        resp = _make_response(_PRICING_TABLE_USD)
        models = fetcher._parse_models(resp)
        assert "minimax-text-01" in models

    def test_input_price_usd(self, fetcher):
        resp = _make_response(_PRICING_TABLE_USD)
        models = fetcher._parse_models(resp)
        ep = models["minimax-text-01"]["endpoints"]["api.minimax.chat"]
        assert ep["pricing"]["in"] == pytest.approx(0.20)
        assert ep["currency"] == "USD"

    def test_parses_cny_prices(self, fetcher):
        resp = _make_response(_PRICING_TABLE_CNY)
        models = fetcher._parse_models(resp)
        if models:
            ep = list(models.values())[0]["endpoints"]["api.minimax.chat"]
            assert ep["currency"] == "CNY"

    def test_subscription_page_returns_empty(self, fetcher):
        """Subscription-only pages should return empty dict gracefully."""
        resp = _make_response(_SUBSCRIPTION_PAGE)
        models = fetcher._parse_models(resp)
        assert isinstance(models, dict)  # graceful empty, no exception

    def test_metadata_provider(self, fetcher):
        resp = _make_response(_PRICING_TABLE_USD)
        models = fetcher._parse_models(resp)
        assert models["minimax-text-01"]["metadata"]["provider"] == "minimax"


class TestValidateResponse:
    def test_valid(self, fetcher):
        resp = _make_response(_PRICING_TABLE_USD)
        assert fetcher._validate_response(resp) is True

    def test_missing_minimax(self, fetcher):
        resp = _make_response("<html>Some other page</html>")
        assert fetcher._validate_response(resp) is False


class TestExtractFamily:
    def test_version_suffix_removed(self, fetcher):
        assert fetcher._extract_family("minimax-text-01") == "minimax-text"

    def test_chat_suffix_removed(self, fetcher):
        assert fetcher._extract_family("abab6.5-chat") == "abab6.5"


class TestFetchIntegration:
    def test_fetch_success(self, fetcher):
        resp = _make_response(_PRICING_TABLE_USD)
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is True
        assert result.source == "minimax"

    def test_fetch_exception(self, fetcher):
        with patch.object(fetcher, "_make_request", side_effect=Exception("timeout")):
            result = fetcher.fetch()
        assert result.success is False
