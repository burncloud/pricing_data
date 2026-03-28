"""
Tests for ZhipuFetcher (bigmodel.cn CNY pricing scraper).
"""
import pytest
from unittest.mock import patch

from scripts.config import config
from scripts.fetch.chinese import ZhipuFetcher


@pytest.fixture
def fetcher():
    return ZhipuFetcher(config)


# ---------------------------------------------------------------------------
# Realistic page snippets matching actual bigmodel.cn structure
# ---------------------------------------------------------------------------

# Flagship section snippet (旗舰模型) — "4元" / "18元" format, per MTok
FLAGSHIP_SNIPPET = """\
旗舰模型

GLM-5-Turbo

新品
\t
输入长度 [0, 32)
\t
5元
\t
22元
\t
限时免费
\t
1.2元


输入长度 [32+)
\t
7元
\t
26元
\t
限时免费
\t
1.8元


GLM-5
\t
输入长度 [0, 32)
\t
4元
\t
18元
\t
限时免费
\t
1元


GLM-4.7-FlashX
\t
200K
\t
0.5元
\t
3元
\t
限时免费
\t
0.1元


GLM-4.7-Flash
\t
200K
\t
免费
\t
免费
\t
免费
\t
免费
"""

# Standard section snippet (模型推理) — "X 元 / 百万Tokens" format
STANDARD_SNIPPET = """\
模型推理

GLM-4-Plus
\t
高智能旗舰
\t
128K
\t
5 元 / 百万Tokens
\t
2.5 元 / 百万Tokens


GLM-4-Air-250414
\t
高性价比
\t
128K
\t
0.5 元 / 百万Tokens
\t
0.25 元 / 百万Tokens


GLM-4-Flash-250414
\t
语言模型
\t
128K
\t
免费
\t
不支持
"""

# Combined snippet with both sections (for full _parse_page_text path)
FULL_SNIPPET = FLAGSHIP_SNIPPET + "\n" + STANDARD_SNIPPET + "\n模型微调\n"


# ---------------------------------------------------------------------------
# TestParsePageText
# ---------------------------------------------------------------------------

class TestParsePageText:

    def test_flagship_section_extracts_models(self, fetcher):
        """旗舰模型 section: GLM-5, GLM-5-Turbo, GLM-4.7-Flash extracted."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        assert "glm-5" in models
        assert "glm-5-turbo" in models
        assert "glm-4.7-flashx" in models
        assert "glm-4.7-flash" in models

    def test_standard_section_extracts_models(self, fetcher):
        """模型推理 section: GLM-4-Plus, GLM-4-Air-250414 extracted."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        assert "glm-4-plus" in models
        assert "glm-4-air-250414" in models
        assert "glm-4-flash-250414" in models

    _EP = "open.bigmodel.cn"

    def test_flagship_asymmetric_prices(self, fetcher):
        """GLM-5: input=4 CNY/MTok, output=18 CNY/MTok (already per-million on page)."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        pricing = models["glm-5"]["endpoints"][self._EP]["pricing"]
        assert pricing["input_price"] == pytest.approx(4.0)
        assert pricing["output_price"] == pytest.approx(18.0)

    def test_flagship_tiered_uses_first_tier(self, fetcher):
        """GLM-5-Turbo has tiered pricing — first tier [0,32) is used."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        pricing = models["glm-5-turbo"]["endpoints"][self._EP]["pricing"]
        assert pricing["input_price"] == pytest.approx(5.0)
        assert pricing["output_price"] == pytest.approx(22.0)

    def test_flagship_free_model(self, fetcher):
        """GLM-4.7-Flash is free — both prices are 0.0."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        pricing = models["glm-4.7-flash"]["endpoints"][self._EP]["pricing"]
        assert pricing["input_price"] == 0.0
        assert pricing["output_price"] == 0.0

    def test_standard_price_per_million(self, fetcher):
        """GLM-4-Plus: 5 元 / 百万Tokens stored as 5.0 (already per-million)."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        pricing = models["glm-4-plus"]["endpoints"][self._EP]["pricing"]
        assert pricing["input_price"] == pytest.approx(5.0)
        assert pricing["output_price"] == pytest.approx(5.0)

    def test_standard_free_model(self, fetcher):
        """GLM-4-Flash-250414 is free in standard section."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        pricing = models["glm-4-flash-250414"]["endpoints"][self._EP]["pricing"]
        assert pricing["input_price"] == 0.0
        assert pricing["output_price"] == 0.0

    def test_model_ids_lowercased(self, fetcher):
        """All model IDs must be lowercase."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        for model_id in models:
            assert model_id == model_id.lower()

    def test_currency_is_cny(self, fetcher):
        """All extracted pricing must use CNY, not USD."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        for m, d in models.items():
            ep = d["endpoints"].get("open.bigmodel.cn", {})
            assert ep.get("currency") == "CNY", f"{m} missing CNY currency"

    def test_metadata_provider_is_zhipu(self, fetcher):
        """Metadata provider must be 'zhipu' for all models."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        for m, d in models.items():
            assert d["metadata"]["provider"] == "zhipu", f"{m}: wrong provider"

    def test_duplicate_models_deduped(self, fetcher):
        """Same model appearing in both sections: first (flagship) wins."""
        # Put GLM-5 in both sections
        text = (
            "旗舰模型\nGLM-5\n输入长度 [0, 32)\n4元\n18元\n"
            "模型推理\nGLM-5\n\t\n128K\n5 元 / 百万Tokens\n"
            "模型微调\n"
        )
        models = fetcher._parse_page_text(text)
        assert len([k for k in models if "glm-5" in k]) >= 1
        # Flagship section prices win (4 not 5)
        assert models["glm-5"]["endpoints"]["open.bigmodel.cn"]["pricing"]["input_price"] == pytest.approx(4.0)

    def test_non_glm_lines_ignored(self, fetcher):
        """Non-GLM model names (qwen-max etc.) are not extracted."""
        text = STANDARD_SNIPPET.replace("模型推理", "模型推理\nqwen-max\n\t\n128K\n5 元 / 百万Tokens\n")
        models = fetcher._parse_page_text(text + "\n模型微调\n")
        assert "qwen-max" not in models

    def test_empty_page_returns_empty_dict(self, fetcher):
        """Page with no recognizable content returns empty dict."""
        models = fetcher._parse_page_text("Loading... 请稍候")
        assert models == {}


# ---------------------------------------------------------------------------
# TestDerivedPricing — cache_pricing and batch_pricing from documented ratios
# ---------------------------------------------------------------------------

class TestDerivedPricing:
    """
    Zhipu docs: cache read = 50% of input, batch = 50% of all prices.
    Sources: docs.bigmodel.cn/cn/guide/capabilities/cache.md
             docs.bigmodel.cn/cn/guide/tools/batch.md
    """

    _EP = "open.bigmodel.cn"

    def test_paid_model_gets_cache_pricing(self, fetcher):
        """Paid models get cache_read_input_price = input_price * 0.5."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        ep = models["glm-4-plus"]["endpoints"][self._EP]
        assert "cache_pricing" in ep
        assert ep["cache_pricing"]["cache_read_input_price"] == pytest.approx(2.5)  # 5.0 * 0.5

    def test_free_model_no_cache_pricing(self, fetcher):
        """Free models (input_price=0) do not get cache_pricing."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        ep = models["glm-4.7-flash"]["endpoints"][self._EP]
        assert "cache_pricing" not in ep

    def test_batch_supported_model_gets_batch_pricing(self, fetcher):
        """GLM-4-Plus is in the batch supported list — gets batch_pricing at 50%."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        ep = models["glm-4-plus"]["endpoints"][self._EP]
        assert "batch_pricing" in ep
        assert ep["batch_pricing"]["input_price"] == pytest.approx(2.5)   # 5.0 * 0.5
        assert ep["batch_pricing"]["output_price"] == pytest.approx(2.5)  # 5.0 * 0.5

    def test_batch_unsupported_model_no_batch_pricing(self, fetcher):
        """GLM-5-Turbo is not in the batch supported list — no batch_pricing."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        ep = models["glm-5-turbo"]["endpoints"][self._EP]
        assert "batch_pricing" not in ep

    def test_batch_supported_from_standard_section(self, fetcher):
        """GLM-4-Air-250414 (standard section) is in batch list — gets batch_pricing."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        ep = models["glm-4-air-250414"]["endpoints"][self._EP]
        assert "batch_pricing" in ep
        assert ep["batch_pricing"]["input_price"] == pytest.approx(0.25)  # 0.5 * 0.5

    def test_free_model_no_batch_pricing(self, fetcher):
        """Free models (both prices = 0) get no batch_pricing even if in supported list."""
        models = fetcher._parse_page_text(FULL_SNIPPET)
        # glm-4-flash-250414 is free
        ep = models["glm-4-flash-250414"]["endpoints"][self._EP]
        assert "batch_pricing" not in ep


# ---------------------------------------------------------------------------
# TestFetch
# ---------------------------------------------------------------------------

class TestFetch:

    def test_playwright_unavailable_returns_error(self, fetcher):
        """Returns error result when Playwright is not installed."""
        with patch("scripts.fetch.chinese.PLAYWRIGHT_AVAILABLE", False):
            result = fetcher.fetch()
        assert result.success is False
        assert "Playwright" in result.error

    def test_playwright_load_failure_returns_error(self, fetcher):
        """Returns error result when page load fails."""
        with patch("scripts.fetch.chinese.PLAYWRIGHT_AVAILABLE", True), \
             patch("scripts.fetch.chinese._run_playwright", return_value=None):
            result = fetcher.fetch()
        assert result.success is False

    def test_successful_scrape(self, fetcher):
        """Successful Playwright scrape returns success result with CNY pricing."""
        with patch("scripts.fetch.chinese.PLAYWRIGHT_AVAILABLE", True), \
             patch("scripts.fetch.chinese._run_playwright", return_value=FULL_SNIPPET):
            result = fetcher.fetch()
        assert result.success is True
        assert result.source == "zhipu"
        assert result.models_count > 0
        assert "glm-5" in result.models

    def test_no_models_found_returns_error(self, fetcher):
        """Empty parse result (no GLM models found) returns error."""
        with patch("scripts.fetch.chinese.PLAYWRIGHT_AVAILABLE", True), \
             patch("scripts.fetch.chinese._run_playwright", return_value="No pricing here"):
            result = fetcher.fetch()
        assert result.success is False
