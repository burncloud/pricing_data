"""
Tests for DeepSeekFetcher.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.deepseek import DeepSeekFetcher


@pytest.fixture
def fetcher():
    return DeepSeekFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


# Minimal HTML matching the real DeepSeek pricing page structure
_PRICING_TABLE = """
<table style="text-align:center">
  <tr><td colspan="2">MODEL</td><td>deepseek-chat</td><td>deepseek-reasoner</td></tr>
  <tr><td colspan="2">BASE URL</td><td colspan="2">https://api.deepseek.com</td></tr>
  <tr><td colspan="2">CONTEXT LENGTH</td><td colspan="2">128K</td></tr>
  <tr>
    <td rowspan="3">PRICING</td>
    <td>1M INPUT TOKENS (CACHE HIT)</td>
    <td colspan="2">$0.028</td>
  </tr>
  <tr>
    <td>1M INPUT TOKENS (CACHE MISS)</td>
    <td colspan="2">$0.28</td>
  </tr>
  <tr>
    <td>1M OUTPUT TOKENS</td>
    <td colspan="2">$0.42</td>
  </tr>
</table>
"""


class TestParseModels:
    def test_both_models_present(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        assert "deepseek-chat" in models
        assert "deepseek-reasoner" in models

    def test_input_price_is_cache_miss(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["deepseek-chat"]["endpoints"]["api.deepseek.com"]
        assert ep["pricing"]["input_price"] == pytest.approx(0.28)

    def test_output_price(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["deepseek-chat"]["endpoints"]["api.deepseek.com"]
        assert ep["pricing"]["output_price"] == pytest.approx(0.42)

    def test_cache_read_price(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        ep = models["deepseek-chat"]["endpoints"]["api.deepseek.com"]
        assert "cache_pricing" in ep
        assert ep["cache_pricing"]["cache_read_input_price"] == pytest.approx(0.028)

    def test_reasoner_same_pricing(self, fetcher):
        """Both models share the same pricing (colspan=2 in source table)."""
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        chat_ep = models["deepseek-chat"]["endpoints"]["api.deepseek.com"]
        reasoner_ep = models["deepseek-reasoner"]["endpoints"]["api.deepseek.com"]
        assert chat_ep["pricing"] == reasoner_ep["pricing"]

    def test_metadata_provider(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        models = fetcher._parse_models(resp)
        assert models["deepseek-chat"]["metadata"]["provider"] == "deepseek"

    def test_no_cache_hit_row(self, fetcher):
        """When CACHE HIT row is absent, cache_pricing is not added."""
        html = """
        <table>
          <tr><td>MODEL</td><td>deepseek-chat</td></tr>
          <tr><td>PRICING</td><td>1M INPUT TOKENS (CACHE MISS)</td><td>$0.28</td></tr>
          <tr><td></td><td>1M OUTPUT TOKENS</td><td>$0.42</td></tr>
        </table>
        """
        resp = _make_response(html)
        models = fetcher._parse_models(resp)
        chat = models.get("deepseek-chat", {})
        if "endpoints" in chat:
            assert "cache_pricing" not in chat["endpoints"].get("api.deepseek.com", {})

    def test_empty_on_no_table(self, fetcher):
        resp = _make_response("<html>No table here</html>")
        models = fetcher._parse_models(resp)
        assert models == {}


class TestValidateResponse:
    def test_valid_response(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        assert fetcher._validate_response(resp) is True

    def test_missing_model(self, fetcher):
        resp = _make_response("<html>PRICING found but no deepseek- model</html>")
        assert fetcher._validate_response(resp) is False

    def test_missing_pricing(self, fetcher):
        resp = _make_response("<html>deepseek-chat model info</html>")
        assert fetcher._validate_response(resp) is False


class TestExtractModelIds:
    def test_extracts_from_model_row(self, fetcher):
        rows = [
            ["MODEL", "deepseek-chat", "deepseek-reasoner"],
            ["BASE URL", "https://api.deepseek.com", ""],
        ]
        ids = fetcher._extract_model_ids(rows)
        assert "deepseek-chat" in ids
        assert "deepseek-reasoner" in ids

    def test_single_model(self, fetcher):
        rows = [["MODEL", "deepseek-chat"]]
        ids = fetcher._extract_model_ids(rows)
        assert ids == ["deepseek-chat"]


class TestFindPrice:
    def test_finds_cache_hit(self, fetcher):
        rows = [
            ["PRICING", "1M INPUT TOKENS (CACHE HIT)", "$0.028"],
        ]
        assert fetcher._find_price(rows, "CACHE HIT") == pytest.approx(0.028)

    def test_finds_output(self, fetcher):
        rows = [
            ["", "1M OUTPUT TOKENS", "$0.42"],
        ]
        assert fetcher._find_price(rows, "OUTPUT TOKENS") == pytest.approx(0.42)

    def test_returns_none_when_absent(self, fetcher):
        rows = [["some", "data"]]
        assert fetcher._find_price(rows, "CACHE HIT") is None


class TestFetchIntegration:
    def test_fetch_success(self, fetcher):
        resp = _make_response(_PRICING_TABLE)
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is True
        assert result.models_count == 2
        assert result.source == "deepseek"
