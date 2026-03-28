"""
Tests for ZhipuFetcher (bigmodel.cn CNY pricing scraper).
"""
import pytest
from unittest.mock import patch, MagicMock

from scripts.config import config
from scripts.fetch.chinese import ZhipuFetcher, _PER_THOUSAND_TO_PER_MILLION


@pytest.fixture
def fetcher():
    return ZhipuFetcher(config)


class TestParsePageText:

    def test_standard_table_row(self, fetcher):
        """Standard page format: GLM model name followed by two decimal prices."""
        text = "GLM-4-Flash\t0.0001\t0.0001\nGLM-4\t0.1\t0.1"
        models = fetcher._parse_page_text(text)
        assert "glm-4-flash" in models
        assert "glm-4" in models

    def test_prices_converted_to_per_million(self, fetcher):
        """Prices on bigmodel.cn are per-thousand — must be multiplied by 1000."""
        text = "GLM-4-Flash  0.0001  0.0001"
        models = fetcher._parse_page_text(text)
        assert "glm-4-flash" in models
        cny = models["glm-4-flash"]["pricing"]["CNY"]
        assert cny["input_price"] == pytest.approx(0.0001 * 1000)
        assert cny["output_price"] == pytest.approx(0.0001 * 1000)

    def test_glm5_pricing(self, fetcher):
        """GLM-5 with asymmetric pricing."""
        text = "GLM-5\t0.014\t0.056"
        models = fetcher._parse_page_text(text)
        assert "glm-5" in models
        cny = models["glm-5"]["pricing"]["CNY"]
        assert cny["input_price"] == pytest.approx(14.0)
        assert cny["output_price"] == pytest.approx(56.0)

    def test_multiple_models_extracted(self, fetcher):
        """Multiple GLM models are all extracted from a realistic page snippet."""
        text = """
        GLM-4-Air\t0.001\t0.001
        GLM-4-Flash\t0.0001\t0.0001
        GLM-4V\t0.05\t0.05
        GLM-3-Turbo\t0.001\t0.001
        """
        models = fetcher._parse_page_text(text)
        assert len(models) == 4
        assert "glm-4-air" in models
        assert "glm-4-flash" in models
        assert "glm-4v" in models
        assert "glm-3-turbo" in models

    def test_model_ids_lowercased(self, fetcher):
        """Model IDs must be lowercase regardless of page casing."""
        text = "GLM-4-Flash  0.0001  0.0001"
        models = fetcher._parse_page_text(text)
        assert "glm-4-flash" in models
        assert "GLM-4-Flash" not in models

    def test_currency_is_cny(self, fetcher):
        """Extracted pricing currency must be CNY."""
        text = "GLM-4  0.1  0.1"
        models = fetcher._parse_page_text(text)
        assert "CNY" in models["glm-4"]["pricing"]
        assert "USD" not in models["glm-4"]["pricing"]

    def test_metadata_provider_is_zhipu(self, fetcher):
        """Metadata provider must be 'zhipu'."""
        text = "GLM-4  0.1  0.1"
        models = fetcher._parse_page_text(text)
        assert models["glm-4"]["metadata"]["provider"] == "zhipu"

    def test_duplicate_models_deduped(self, fetcher):
        """If the same model appears twice, only the first occurrence is kept."""
        text = "GLM-4  0.1  0.1\nGLM-4  0.2  0.2"
        models = fetcher._parse_page_text(text)
        assert len(models) == 1
        assert models["glm-4"]["pricing"]["CNY"]["input_price"] == pytest.approx(100.0)

    def test_empty_page_returns_empty_dict(self, fetcher):
        """Page with no GLM models returns empty dict (not an error)."""
        models = fetcher._parse_page_text("Loading... 请稍候")
        assert models == {}

    def test_non_glm_lines_ignored(self, fetcher):
        """Non-GLM model names are not included."""
        text = "qwen-max  0.04  0.12\nGLM-4  0.1  0.1"
        models = fetcher._parse_page_text(text)
        assert "qwen-max" not in models
        assert "glm-4" in models


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
        page_text = "GLM-4-Flash\t0.0001\t0.0001\nGLM-4\t0.1\t0.1"
        with patch("scripts.fetch.chinese.PLAYWRIGHT_AVAILABLE", True), \
             patch("scripts.fetch.chinese._run_playwright", return_value=page_text):
            result = fetcher.fetch()
        assert result.success is True
        assert result.source == "zhipu"
        assert result.models_count == 2
        assert "glm-4" in result.models

    def test_no_models_found_returns_error(self, fetcher):
        """Empty parse result (no GLM models found) returns error."""
        with patch("scripts.fetch.chinese.PLAYWRIGHT_AVAILABLE", True), \
             patch("scripts.fetch.chinese._run_playwright", return_value="No pricing here"):
            result = fetcher.fetch()
        assert result.success is False
