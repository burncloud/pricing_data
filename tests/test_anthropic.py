"""
Tests for AnthropicFetcher.
"""
import pytest
from unittest.mock import Mock

from scripts.config import config
from scripts.fetch.anthropic import AnthropicFetcher


@pytest.fixture
def fetcher():
    return AnthropicFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Minimal test HTML that matches the real docs page structure
# ---------------------------------------------------------------------------

_FULL_TABLE_HTML = """
<table>
  <tr>
    <td><strong>Claude API ID</strong></td>
    <td><span data-state="closed">claude-opus-4-6</span></td>
    <td><span data-state="closed">claude-sonnet-4-6</span></td>
    <td><span data-state="closed">claude-haiku-4-5-20251001</span></td>
  </tr>
  <tr>
    <td><strong>Description</strong></td>
    <td>Most intelligent</td>
    <td>Balanced</td>
    <td>Fastest</td>
  </tr>
  <tr>
    <td><strong>Pricing</strong><sup>1</sup></td>
    <td>$5 / input MTok<br/>$25 / output MTok</td>
    <td>$3 / input MTok<br/>$15 / output MTok</td>
    <td>$1 / input MTok<br/>$5 / output MTok</td>
  </tr>
</table>
"""


class TestParseModels:
    def test_three_models_parsed(self, fetcher):
        resp = _make_response(_FULL_TABLE_HTML)
        models = fetcher._parse_models(resp)
        assert len(models) == 3

    def test_opus_pricing(self, fetcher):
        resp = _make_response(_FULL_TABLE_HTML)
        models = fetcher._parse_models(resp)
        assert "claude-opus-4-6" in models
        ep = models["claude-opus-4-6"]["endpoints"]["api.anthropic.com"]
        assert ep["pricing"]["in"] == pytest.approx(5.0)
        assert ep["pricing"]["out"] == pytest.approx(25.0)

    def test_sonnet_pricing(self, fetcher):
        resp = _make_response(_FULL_TABLE_HTML)
        models = fetcher._parse_models(resp)
        ep = models["claude-sonnet-4-6"]["endpoints"]["api.anthropic.com"]
        assert ep["pricing"]["in"] == pytest.approx(3.0)
        assert ep["pricing"]["out"] == pytest.approx(15.0)

    def test_haiku_pricing(self, fetcher):
        resp = _make_response(_FULL_TABLE_HTML)
        models = fetcher._parse_models(resp)
        ep = models["claude-haiku-4-5-20251001"]["endpoints"]["api.anthropic.com"]
        assert ep["pricing"]["in"] == pytest.approx(1.0)
        assert ep["pricing"]["out"] == pytest.approx(5.0)

    def test_metadata_provider(self, fetcher):
        resp = _make_response(_FULL_TABLE_HTML)
        models = fetcher._parse_models(resp)
        assert models["claude-opus-4-6"]["metadata"]["provider"] == "anthropic"

    def test_empty_on_no_table(self, fetcher):
        resp = _make_response("<html><body>No table here</body></html>")
        models = fetcher._parse_models(resp)
        assert models == {}


class TestValidateResponse:
    def test_valid_response(self, fetcher):
        resp = _make_response(_FULL_TABLE_HTML)
        assert fetcher._validate_response(resp) is True

    def test_missing_api_id_row(self, fetcher):
        resp = _make_response("<table><tr><td>Other row</td></tr></table>")
        assert fetcher._validate_response(resp) is False

    def test_missing_pricing_data(self, fetcher):
        resp = _make_response("<p>Claude API ID is mentioned but no MTok pricing</p>")
        assert fetcher._validate_response(resp) is False


class TestExtractFamily:
    def test_opus(self, fetcher):
        assert fetcher._extract_family("claude-opus-4-6") == "claude-opus"

    def test_sonnet(self, fetcher):
        assert fetcher._extract_family("claude-sonnet-4-6") == "claude-sonnet"

    def test_haiku_with_date(self, fetcher):
        assert fetcher._extract_family("claude-haiku-4-5-20251001") == "claude-haiku"


class TestFetchIntegration:
    def test_fetch_success(self, fetcher):
        from unittest.mock import patch
        resp = _make_response(_FULL_TABLE_HTML)
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is True
        assert result.models_count == 3
        assert result.source == "anthropic"
