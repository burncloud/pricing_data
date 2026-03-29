"""
Tests for BaiduFetcher.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.baidu import BaiduFetcher


@pytest.fixture
def fetcher():
    return BaiduFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


# Per-million-token pricing (元/MTok)
_PRICING_TABLE_PERMTOK = """
<html><body>
<table>
  <thead>
    <tr><th>模型</th><th>输入价格（元/千tokens）</th><th>输出价格（元/千tokens）</th></tr>
  </thead>
  <tbody>
    <tr><td>ERNIE-4.0-8K</td><td>0.12</td><td>0.12</td></tr>
    <tr><td>ERNIE-Speed-8K</td><td>0.004</td><td>0.008</td></tr>
  </tbody>
</table>
</body></html>
"""

# Per-thousand-token pricing (should be converted × 1000)
_PRICING_TABLE_PERKTOK = """
<table>
  <tr><th>Model</th><th>Input (CNY/Ktok)</th><th>Output (CNY/Ktok)</th></tr>
  <tr><td>ERNIE-4.0-8K</td><td>0.004</td><td>0.008</td></tr>
</table>
"""


class TestParseModels:
    def test_parses_ernie_model(self, fetcher):
        resp = _make_response(_PRICING_TABLE_PERMTOK)
        models = fetcher._parse_models(resp)
        assert len(models) > 0
        assert any("ernie" in m for m in models)

    def test_currency_cny(self, fetcher):
        resp = _make_response(_PRICING_TABLE_PERMTOK)
        models = fetcher._parse_models(resp)
        for model_id, model_data in models.items():
            ep_data = list(model_data["endpoints"].values())[0]
            assert ep_data["currency"] == "CNY"

    def test_metadata_provider(self, fetcher):
        resp = _make_response(_PRICING_TABLE_PERMTOK)
        models = fetcher._parse_models(resp)
        for model_id, model_data in models.items():
            assert model_data["metadata"]["provider"] == "baidu"

    def test_per_ktok_conversion(self, fetcher):
        """Prices < 0.1 (per-Ktok) should be multiplied by 1000."""
        resp = _make_response(_PRICING_TABLE_PERKTOK)
        models = fetcher._parse_models(resp)
        if models:
            model_id = list(models.keys())[0]
            ep = list(models[model_id]["endpoints"].values())[0]
            # 0.004 * 1000 = 4.0 CNY/MTok
            assert ep["pricing"]["in"] == pytest.approx(4.0)

    def test_empty_on_no_ernie(self, fetcher):
        resp = _make_response("<html>Some page without ERNIE models</html>")
        models = fetcher._parse_models(resp)
        assert models == {}


class TestValidateResponse:
    def test_valid(self, fetcher):
        resp = _make_response(_PRICING_TABLE_PERMTOK)
        assert fetcher._validate_response(resp) is True

    def test_missing_ernie(self, fetcher):
        resp = _make_response("<html>Some other page</html>")
        assert fetcher._validate_response(resp) is False


class TestExtractFamily:
    def test_context_size_suffix_removed(self, fetcher):
        assert fetcher._extract_family("ernie-4.0-8k") == "ernie-4.0"

    def test_plain_model(self, fetcher):
        assert fetcher._extract_family("ernie-speed") == "ernie-speed"


class TestFetchIntegration:
    def test_fetch_success(self, fetcher):
        resp = _make_response(_PRICING_TABLE_PERMTOK)
        with patch.object(fetcher, "_make_request", return_value=resp):
            result = fetcher.fetch()
        assert result.success is True
        assert result.source == "baidu"

    def test_fetch_exception(self, fetcher):
        with patch.object(fetcher, "_make_request", side_effect=Exception("timeout")):
            result = fetcher.fetch()
        assert result.success is False
