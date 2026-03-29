"""
Tests for CohereFetcher.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.cohere import CohereFetcher, _normalize_model_id


@pytest.fixture
def fetcher():
    return CohereFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


_PRICING_HTML = """
<html><body>
<div>
  <h3>Command R+ 08-2024</h3>
  <p>$2.50/1M input tokens, $10.00/1M output tokens</p>
</div>
<div>
  <h3>Command R 03-2024</h3>
  <p>$0.50/1M input tokens, $1.50/1M output tokens</p>
</div>
<div>
  <h3>Command</h3>
  <p>$1.00/1M input tokens, $2.00/1M output tokens</p>
</div>
</body></html>
"""


class TestParseModels:
    def test_parses_command_r_plus(self, fetcher):
        resp = _make_response(_PRICING_HTML)
        models = fetcher._parse_models(resp)
        assert "command-r-plus-08-2024" in models

    def test_parses_command_r(self, fetcher):
        resp = _make_response(_PRICING_HTML)
        models = fetcher._parse_models(resp)
        assert "command-r-03-2024" in models

    def test_input_price(self, fetcher):
        resp = _make_response(_PRICING_HTML)
        models = fetcher._parse_models(resp)
        ep = models["command-r-plus-08-2024"]["endpoints"]["api.cohere.com"]
        assert ep["pricing"]["in"] == pytest.approx(2.50)

    def test_output_price(self, fetcher):
        resp = _make_response(_PRICING_HTML)
        models = fetcher._parse_models(resp)
        ep = models["command-r-plus-08-2024"]["endpoints"]["api.cohere.com"]
        assert ep["pricing"]["out"] == pytest.approx(10.00)

    def test_metadata_provider(self, fetcher):
        resp = _make_response(_PRICING_HTML)
        models = fetcher._parse_models(resp)
        assert models["command-r-plus-08-2024"]["metadata"]["provider"] == "cohere"

    def test_empty_on_no_command(self, fetcher):
        resp = _make_response("<html>No models here.</html>")
        models = fetcher._parse_models(resp)
        assert models == {}


class TestValidateResponse:
    def test_valid(self, fetcher):
        resp = _make_response(_PRICING_HTML)
        assert fetcher._validate_response(resp) is True

    def test_missing_command(self, fetcher):
        resp = _make_response("<html>Some page $1.00</html>")
        assert fetcher._validate_response(resp) is False

    def test_missing_prices(self, fetcher):
        resp = _make_response("<html>Command model info</html>")
        assert fetcher._validate_response(resp) is False


class TestNormalizeModelId:
    def test_command_r_plus(self):
        assert _normalize_model_id("Command R+ 08-2024") == "command-r-plus-08-2024"

    def test_command_r(self):
        assert _normalize_model_id("Command R 03-2024") == "command-r-03-2024"

    def test_plain_command(self):
        assert _normalize_model_id("Command") == "command"

    def test_command_light(self):
        assert _normalize_model_id("Command-light") == "command-light"


class TestExtractFamily:
    def test_with_date(self, fetcher):
        assert fetcher._extract_family("command-r-plus-08-2024") == "command-r-plus"

    def test_without_date(self, fetcher):
        assert fetcher._extract_family("command-r-plus") == "command-r-plus"

    def test_plain(self, fetcher):
        assert fetcher._extract_family("command") == "command"


class TestFetchIntegration:
    def test_fetch_success(self, fetcher):
        resp = _make_response(_PRICING_HTML)
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is True
        assert result.source == "cohere"

    def test_fetch_exception(self, fetcher):
        with patch.object(fetcher, "_make_request", side_effect=Exception("timeout")):
            result = fetcher.fetch()
        assert result.success is False
