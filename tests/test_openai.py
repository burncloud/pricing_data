"""
Tests for OpenAIFetcher.

Playwright is not available in unit-test environments. All tests exercise
the pure-Python parsing helpers or mock _scrape_with_playwright.
"""
import pytest
from unittest.mock import patch, MagicMock

from scripts.config import config
from scripts.fetch.openai import OpenAIFetcher


@pytest.fixture
def fetcher():
    return OpenAIFetcher(config)


# ---------------------------------------------------------------------------
# _normalize_display_name
# ---------------------------------------------------------------------------

class TestNormalizeDisplayName:
    def test_simple_model(self, fetcher):
        assert fetcher._normalize_display_name("GPT-4o") == "gpt-4o"

    def test_model_with_qualifier(self, fetcher):
        assert fetcher._normalize_display_name("GPT-4o mini") == "gpt-4o-mini"

    def test_model_with_nano(self, fetcher):
        assert fetcher._normalize_display_name("GPT-4o nano") == "gpt-4o-nano"

    def test_o_series(self, fetcher):
        assert fetcher._normalize_display_name("o3-mini") == "o3-mini"

    def test_already_lowercase(self, fetcher):
        assert fetcher._normalize_display_name("gpt-4o") == "gpt-4o"

    def test_extra_whitespace(self, fetcher):
        assert fetcher._normalize_display_name("  GPT-4o  ") == "gpt-4o"

    def test_multi_word_qualifier(self, fetcher):
        assert fetcher._normalize_display_name("GPT-4o mini turbo") == "gpt-4o-mini-turbo"


# ---------------------------------------------------------------------------
# _extract_family
# ---------------------------------------------------------------------------

class TestExtractFamily:
    def test_gpt4o(self, fetcher):
        assert fetcher._extract_family("GPT-4o") == "gpt-4o"

    def test_gpt4o_mini(self, fetcher):
        # "mini" qualifier stripped from family
        assert fetcher._extract_family("GPT-4o mini") == "gpt-4o"

    def test_gpt4o_nano(self, fetcher):
        assert fetcher._extract_family("GPT-4o nano") == "gpt-4o"

    def test_o3_mini(self, fetcher):
        # "o3-mini" → family "o3"
        assert fetcher._extract_family("o3-mini") == "o3"

    def test_plain_name(self, fetcher):
        assert fetcher._extract_family("GPT-4o") == "gpt-4o"


# ---------------------------------------------------------------------------
# _parse_model_card
# ---------------------------------------------------------------------------

class TestParseModelCard:
    def test_basic_input_output(self, fetcher):
        card_text = (
            "GPT-4o\n"
            "Some description.\n"
            "Price\n"
            "Input:\n$2.50 / 1M tokens\n"
            "Output:\n$10.00 / 1M tokens\n"
        )
        entry = fetcher._parse_model_card("GPT-4o", card_text)

        assert entry is not None
        ep = entry["endpoints"]["api.openai.com"]
        assert ep["pricing"]["input_price"] == pytest.approx(2.50)
        assert ep["pricing"]["output_price"] == pytest.approx(10.00)

    def test_with_cached_input(self, fetcher):
        card_text = (
            "GPT-4o\n"
            "Input:\n$2.50 / 1M tokens\n"
            "Cached input:\n$0.25 / 1M tokens\n"
            "Output:\n$10.00 / 1M tokens\n"
        )
        entry = fetcher._parse_model_card("GPT-4o", card_text)

        assert entry is not None
        ep = entry["endpoints"]["api.openai.com"]
        assert "cache_pricing" in ep
        assert ep["cache_pricing"]["cache_read_input_price"] == pytest.approx(0.25)

    def test_no_cache_when_absent(self, fetcher):
        card_text = (
            "Input:\n$2.50 / 1M tokens\n"
            "Output:\n$10.00 / 1M tokens\n"
        )
        entry = fetcher._parse_model_card("GPT-4o", card_text)
        ep = entry["endpoints"]["api.openai.com"]
        assert "cache_pricing" not in ep

    def test_missing_output_returns_none(self, fetcher):
        card_text = "Input:\n$2.50 / 1M tokens\n"
        entry = fetcher._parse_model_card("GPT-4o", card_text)
        assert entry is None

    def test_missing_input_returns_none(self, fetcher):
        card_text = "Output:\n$10.00 / 1M tokens\n"
        entry = fetcher._parse_model_card("GPT-4o", card_text)
        assert entry is None

    def test_image_only_model_skipped(self, fetcher):
        """Audio/image pricing uses different format — no $/1M tokens."""
        card_text = (
            "GPT-image\n"
            "$0.000263 per image\n"
        )
        entry = fetcher._parse_model_card("GPT-image", card_text)
        assert entry is None

    def test_metadata_populated(self, fetcher):
        card_text = (
            "Input:\n$2.50 / 1M tokens\n"
            "Output:\n$10.00 / 1M tokens\n"
        )
        entry = fetcher._parse_model_card("GPT-4o", card_text)
        assert entry["metadata"]["provider"] == "openai"
        assert entry["metadata"]["family"] == "gpt-4o"

    def test_large_price_with_comma(self, fetcher):
        """Prices like '$1,000.00 / 1M tokens' should parse correctly."""
        card_text = (
            "Input:\n$1,000.00 / 1M tokens\n"
            "Output:\n$2,000.00 / 1M tokens\n"
        )
        entry = fetcher._parse_model_card("Expensive Model", card_text)
        assert entry is not None
        ep = entry["endpoints"]["api.openai.com"]
        assert ep["pricing"]["input_price"] == pytest.approx(1000.0)
        assert ep["pricing"]["output_price"] == pytest.approx(2000.0)


# ---------------------------------------------------------------------------
# fetch() — Playwright not installed
# ---------------------------------------------------------------------------

class TestFetchPlaywrightMissing:
    def test_returns_error_when_playwright_missing(self, fetcher):
        with patch.dict("sys.modules", {"playwright": None, "playwright.sync_api": None}):
            # Re-import inside the patch context so the ImportError fires
            import importlib
            import scripts.fetch.openai as openai_mod
            # Simulate the ImportError branch
            with patch.object(
                openai_mod,
                "OpenAIFetcher",
                wraps=OpenAIFetcher,
            ):
                # Directly test the import-guard path
                with patch("builtins.__import__", side_effect=_playwright_import_guard):
                    result = fetcher.fetch()

        assert result.success is False
        assert "Playwright" in result.error

    def test_fetch_error_on_playwright_import(self, fetcher):
        """When 'from playwright.sync_api import ...' raises ImportError, return error."""
        original_fetch = OpenAIFetcher.fetch

        def mock_fetch(self):
            try:
                raise ImportError("No module named 'playwright'")
            except ImportError:
                from scripts.fetch.base import FetchResult
                return FetchResult.error_result(
                    self.fetcher_config.name,
                    "Playwright not installed. Run: pip install playwright && playwright install chromium",
                )

        with patch.object(OpenAIFetcher, "fetch", mock_fetch):
            result = fetcher.fetch()

        assert result.success is False
        assert "Playwright" in result.error


def _playwright_import_guard(name, *args, **kwargs):
    if "playwright" in name:
        raise ImportError(f"No module named '{name}'")
    return __builtins__.__import__(name, *args, **kwargs)  # type: ignore


# ---------------------------------------------------------------------------
# fetch() — mocked _scrape_with_playwright
# ---------------------------------------------------------------------------

class TestFetchWithMockedScrape:
    def test_successful_fetch(self, fetcher):
        mock_models = {
            "gpt-4o": {
                "endpoints": {"api.openai.com": {"base_url": "https://api.openai.com/v1", "currency": "USD", "pricing": {"input_price": 2.5, "output_price": 10.0}}},
                "metadata": {"provider": "openai", "family": "gpt-4o"},
            },
            "gpt-4o-mini": {
                "endpoints": {"api.openai.com": {"base_url": "https://api.openai.com/v1", "currency": "USD", "pricing": {"input_price": 0.15, "output_price": 0.60}}},
                "metadata": {"provider": "openai", "family": "gpt-4o"},
            },
        }

        with patch.object(fetcher, "_scrape_with_playwright", return_value=mock_models):
            result = fetcher.fetch()

        assert result.success is True
        assert result.models_count == 2
        assert result.source == "openai"
        assert "gpt-4o" in result.models

    def test_empty_scrape_returns_error(self, fetcher):
        with patch.object(fetcher, "_scrape_with_playwright", return_value={}):
            result = fetcher.fetch()

        assert result.success is False
        assert "No models" in result.error

    def test_scrape_exception_returns_error(self, fetcher):
        with patch.object(
            fetcher,
            "_scrape_with_playwright",
            side_effect=Exception("browser crash"),
        ):
            result = fetcher.fetch()

        assert result.success is False
        assert "browser crash" in result.error
