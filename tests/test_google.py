"""
Tests for GoogleFetcher.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.google import GoogleFetcher, _parse_paid_price, _first_dollar, _parse_per_image_price


@pytest.fixture
def fetcher():
    return GoogleFetcher(config)


def _make_response(text: str) -> Mock:
    resp = Mock()
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestParsePaidPrice:
    def test_flat_price(self):
        price, boundary = _parse_paid_price("$0.25 (text / image / video)")
        assert price == pytest.approx(0.25)
        assert boundary is None

    def test_tiered_price_200k(self):
        price, boundary = _parse_paid_price(
            "$1.25, prompts <= 200k tokens\n$2.50, prompts > 200k tokens"
        )
        assert price == pytest.approx(1.25)
        assert boundary == 200_000

    def test_tiered_price_128k(self):
        price, boundary = _parse_paid_price(
            "$1.00, prompts <= 128k tokens\n$2.00, prompts > 128k tokens"
        )
        assert price == pytest.approx(1.00)
        assert boundary == 128_000

    def test_not_available(self):
        price, boundary = _parse_paid_price("Not available")
        assert price is None
        assert boundary is None

    def test_flat_with_qualifier(self):
        price, boundary = _parse_paid_price("$0.50 (text) | $3.00 (audio)")
        assert price == pytest.approx(0.50)
        assert boundary is None


class TestParsePerImagePrice:
    def test_simple_per_image(self):
        assert _parse_per_image_price("$0.039 per image") == pytest.approx(0.039)

    def test_per_1k2k_image(self):
        assert _parse_per_image_price("$0.134 per 1K/2K image") == pytest.approx(0.134)

    def test_per_4k_image(self):
        assert _parse_per_image_price("$0.24 per 4K image") == pytest.approx(0.24)

    def test_returns_first_price_in_multiline(self):
        cell = "$0.134 per 1K/2K image\n$0.24 per 4K image"
        assert _parse_per_image_price(cell) == pytest.approx(0.134)

    def test_per_token_cell_returns_none(self):
        assert _parse_per_image_price("$120.00 (text and thinking)") is None

    def test_no_price_returns_none(self):
        assert _parse_per_image_price("Not available") is None


class TestFirstDollar:
    def test_finds_dollar(self):
        assert _first_dollar("$0.125 something") == pytest.approx(0.125)

    def test_returns_none_when_absent(self):
        assert _first_dollar("No price here") is None


# ---------------------------------------------------------------------------
# _normalize_display_name
# ---------------------------------------------------------------------------

class TestNormalizeDisplayName:
    def test_gemini_pro(self, fetcher):
        assert fetcher._normalize_display_name("Gemini 2.5 Pro") == "gemini-2.5-pro"

    def test_gemini_flash(self, fetcher):
        assert fetcher._normalize_display_name("Gemini 2.5 Flash") == "gemini-2.5-flash"

    def test_flash_lite(self, fetcher):
        assert fetcher._normalize_display_name("Gemini 2.5 Flash-Lite") == "gemini-2.5-flash-lite"

    def test_strips_parenthetical(self, fetcher):
        assert fetcher._normalize_display_name("Gemini 2.5 Flash (Preview)") == "gemini-2.5-flash"

    def test_strips_emoji(self, fetcher):
        result = fetcher._normalize_display_name("Gemini 3 Flash Preview 🍌")
        assert "🍌" not in result
        assert result.startswith("gemini-3")


# ---------------------------------------------------------------------------
# _should_skip
# ---------------------------------------------------------------------------

class TestShouldSkip:
    def test_skip_imagen(self, fetcher):
        assert fetcher._should_skip("Imagen 4") is True

    def test_skip_veo(self, fetcher):
        assert fetcher._should_skip("Veo 3") is True

    def test_skip_lyria(self, fetcher):
        assert fetcher._should_skip("Lyria 3") is True

    def test_skip_gemini_embedding(self, fetcher):
        assert fetcher._should_skip("Gemini Embedding") is True

    def test_skip_pricing_for(self, fetcher):
        assert fetcher._should_skip("Pricing for tools") is True

    def test_keep_gemini_pro(self, fetcher):
        assert fetcher._should_skip("Gemini 2.5 Pro") is False

    def test_keep_gemini_flash(self, fetcher):
        assert fetcher._should_skip("Gemini 2.5 Flash") is False


# ---------------------------------------------------------------------------
# _parse_model_section
# ---------------------------------------------------------------------------

_FLAT_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier, per 1M tokens in USD</th></tr>
  </thead>
  <tbody>
    <tr><td>Input price</td><td>Free of charge</td><td>$0.25 (text / image / video)</td></tr>
    <tr><td>Output price (including thinking tokens)</td><td>Free of charge</td><td>$1.50</td></tr>
    <tr><td>Context caching price</td><td>Not available</td><td>$0.025 (text)</td></tr>
  </tbody>
</table>
"""

_TIERED_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier, per 1M tokens in USD</th></tr>
  </thead>
  <tbody>
    <tr><td>Input price</td><td>Not available</td>
        <td>$1.25, prompts &lt;= 200k tokens
$2.50, prompts &gt; 200k tokens</td></tr>
    <tr><td>Output price (including thinking tokens)</td><td>Not available</td>
        <td>$10.00, prompts &lt;= 200k tokens
$15.00, prompts &gt; 200k</td></tr>
    <tr><td>Context caching price</td><td>Not available</td><td>$0.125, prompts &lt;= 200k tokens</td></tr>
  </tbody>
</table>
"""

_NO_OUTPUT_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier, per 1M tokens in USD</th></tr>
  </thead>
  <tbody>
    <tr><td>Input price</td><td>Not available</td><td>Not available</td></tr>
    <tr><td>Output price</td><td>Not available</td><td>Not available</td></tr>
  </tbody>
</table>
"""

# Image-only output model (e.g. Gemini 2.5 Flash Image): output is per-image fee
_IMAGE_GEN_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier, per 1M tokens in USD</th></tr>
  </thead>
  <tbody>
    <tr><td>Input price</td><td>Free of charge</td><td>$0.30 (text / image)</td></tr>
    <tr><td>Output price</td><td>Free of charge</td><td>$0.039 per image</td></tr>
  </tbody>
</table>
"""

# Mixed text+image output model (e.g. Gemini 3 Pro Image Preview):
# separate rows for text output and image output
_PRO_IMAGE_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier, per 1M tokens in USD</th></tr>
  </thead>
  <tbody>
    <tr><td>Input price</td><td>Free</td><td>$2.00 (text/image)</td></tr>
    <tr><td>Output price (text and thinking)</td><td>Free</td><td>$12.00</td></tr>
    <tr><td>Output price (images)</td><td>Free</td>
        <td>$0.134 per 1K/2K image
$0.24 per 4K image</td></tr>
  </tbody>
</table>
"""


_GGL_EP = "generativelanguage.googleapis.com"


class TestImageGenerationPricing:
    """Image generation models have per-image output fees, not per-token output."""

    def test_image_only_output_extracted(self, fetcher):
        """Flash Image: $0.039 per image → image_output_price=0.039."""
        entry = fetcher._parse_model_section("Gemini 2.5 Flash Image", _IMAGE_GEN_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["image_output_price"] == pytest.approx(0.039)

    def test_image_only_output_price_is_zero(self, fetcher):
        """Flash Image: no text output → output_price=0.0."""
        entry = fetcher._parse_model_section("Gemini 2.5 Flash Image", _IMAGE_GEN_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["output_price"] == 0.0

    def test_image_only_input_price_preserved(self, fetcher):
        """Flash Image: input_price=$0.30 still captured."""
        entry = fetcher._parse_model_section("Gemini 2.5 Flash Image", _IMAGE_GEN_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["input_price"] == pytest.approx(0.30)

    def test_pro_image_text_output_preserved(self, fetcher):
        """Pro Image Preview: text output_price=$12.00 still captured."""
        entry = fetcher._parse_model_section("Gemini 3 Pro Image Preview", _PRO_IMAGE_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["output_price"] == pytest.approx(12.0)

    def test_pro_image_image_output_price(self, fetcher):
        """Pro Image Preview: image_output_price=$0.134 (1K/2K base price)."""
        entry = fetcher._parse_model_section("Gemini 3 Pro Image Preview", _PRO_IMAGE_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["image_output_price"] == pytest.approx(0.134)

    def test_pro_image_input_price(self, fetcher):
        """Pro Image Preview: input_price=$2.00."""
        entry = fetcher._parse_model_section("Gemini 3 Pro Image Preview", _PRO_IMAGE_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["input_price"] == pytest.approx(2.0)

    def test_regular_model_no_image_output_price(self, fetcher):
        """Regular text model has no image_output_price."""
        entry = fetcher._parse_model_section("Gemini 2.5 Flash", _FLAT_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert "image_output_price" not in ep["pricing"]


class TestParseModelSection:
    def test_flat_pricing(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Flash", _FLAT_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["input_price"] == pytest.approx(0.25)
        assert ep["pricing"]["output_price"] == pytest.approx(1.50)

    def test_flat_with_cache(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Flash", _FLAT_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert "cache_pricing" in ep
        assert ep["cache_pricing"]["cache_read_input_price"] == pytest.approx(0.025)

    def test_tiered_pricing_two_tiers(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Pro", _TIERED_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert "tiered_pricing" in ep
        tiers = ep["tiered_pricing"]
        assert len(tiers) == 2
        assert tiers[0]["tier_start"] == 0
        assert tiers[0]["tier_end"] == 200_000
        assert tiers[0]["input_price"] == pytest.approx(1.25)
        assert tiers[0]["output_price"] == pytest.approx(10.00)
        assert tiers[1]["tier_start"] == 200_000
        assert "tier_end" not in tiers[1]
        assert tiers[1]["input_price"] == pytest.approx(2.50)
        assert tiers[1]["output_price"] == pytest.approx(15.00)

    def test_tiered_also_has_top_level_pricing(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Pro", _TIERED_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        # Top-level pricing uses tier-1 (cheapest) price
        assert ep["pricing"]["input_price"] == pytest.approx(1.25)

    def test_not_available_returns_none(self, fetcher):
        entry = fetcher._parse_model_section("Gemini X", _NO_OUTPUT_TABLE)
        assert entry is None

    def test_metadata_provider(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Flash", _FLAT_TABLE)
        assert entry["metadata"]["provider"] == "google"


# ---------------------------------------------------------------------------
# _parse_models (full page)
# ---------------------------------------------------------------------------

_FULL_PAGE = """
<html><body>
<h1>Gemini Developer API pricing</h1>
<h2>Gemini 2.5 Pro</h2>
<p>Some text</p>
{tiered}
<h2>Gemini 2.5 Flash</h2>
{flat}
<h2>Imagen 4</h2>
<table><tr><td>Input price</td><td>Not available</td><td>$2.00</td></tr></table>
<h2>Pricing for tools</h2>
<table><tr><td>Google Search</td><td>free</td><td>$14/1000</td></tr></table>
</body></html>
""".format(tiered=_TIERED_TABLE, flat=_FLAT_TABLE)


class TestParseModels:
    def test_models_count(self, fetcher):
        resp = _make_response(_FULL_PAGE)
        models = fetcher._parse_models(resp)
        # Should have gemini-2.5-pro and gemini-2.5-flash, not imagen or pricing-for-tools
        assert "gemini-2.5-pro" in models
        assert "gemini-2.5-flash" in models
        assert "imagen-4" not in models

    def test_tiered_model(self, fetcher):
        resp = _make_response(_FULL_PAGE)
        models = fetcher._parse_models(resp)
        ep = models["gemini-2.5-pro"]["endpoints"][_GGL_EP]
        assert "tiered_pricing" in ep

    def test_flat_model(self, fetcher):
        resp = _make_response(_FULL_PAGE)
        models = fetcher._parse_models(resp)
        ep = models["gemini-2.5-flash"]["endpoints"][_GGL_EP]
        assert "tiered_pricing" not in ep
        assert ep["pricing"]["input_price"] == pytest.approx(0.25)


class TestValidateResponse:
    def test_valid(self, fetcher):
        resp = _make_response("<html>Input price ... Gemini</html>")
        assert fetcher._validate_response(resp) is True

    def test_no_input_price(self, fetcher):
        resp = _make_response("<html>Gemini models</html>")
        assert fetcher._validate_response(resp) is False

    def test_no_gemini(self, fetcher):
        resp = _make_response("<html>Input price data</html>")
        assert fetcher._validate_response(resp) is False
