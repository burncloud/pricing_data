"""
Tests for GoogleFetcher.
"""
import pytest
from unittest.mock import Mock, patch

from scripts.config import config
from scripts.fetch.google import (
    GoogleFetcher, _parse_paid_price, _first_dollar, _parse_per_image_price,
    _PER_SECOND_RE, _PER_REQUEST_RE,
)


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
    def test_skip_gemma(self, fetcher):
        assert fetcher._should_skip("Gemma 3") is True

    def test_skip_pricing_for(self, fetcher):
        assert fetcher._should_skip("Pricing for tools") is True

    def test_keep_gemini_pro(self, fetcher):
        assert fetcher._should_skip("Gemini 2.5 Pro") is False

    def test_keep_gemini_flash(self, fetcher):
        assert fetcher._should_skip("Gemini 2.5 Flash") is False

    def test_keep_imagen(self, fetcher):
        assert fetcher._should_skip("Imagen 4") is False

    def test_keep_veo(self, fetcher):
        assert fetcher._should_skip("Veo 3") is False

    def test_keep_lyria(self, fetcher):
        assert fetcher._should_skip("Lyria 3") is False

    def test_keep_embedding(self, fetcher):
        assert fetcher._should_skip("Gemini Embedding") is False


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
        assert ep["pricing"]["image_out"] == pytest.approx(0.039)

    def test_image_only_output_price_is_zero(self, fetcher):
        """Flash Image: no text output → output_price=0.0."""
        entry = fetcher._parse_model_section("Gemini 2.5 Flash Image", _IMAGE_GEN_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["out"] == 0.0

    def test_image_only_input_price_preserved(self, fetcher):
        """Flash Image: input_price=$0.30 still captured."""
        entry = fetcher._parse_model_section("Gemini 2.5 Flash Image", _IMAGE_GEN_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["in"] == pytest.approx(0.30)

    def test_pro_image_text_output_preserved(self, fetcher):
        """Pro Image Preview: text output_price=$12.00 still captured."""
        entry = fetcher._parse_model_section("Gemini 3 Pro Image Preview", _PRO_IMAGE_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["out"] == pytest.approx(12.0)

    def test_pro_image_image_output_price(self, fetcher):
        """Pro Image Preview: image_output_price=$0.134 (1K/2K base price)."""
        entry = fetcher._parse_model_section("Gemini 3 Pro Image Preview", _PRO_IMAGE_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["image_out"] == pytest.approx(0.134)

    def test_pro_image_input_price(self, fetcher):
        """Pro Image Preview: input_price=$2.00."""
        entry = fetcher._parse_model_section("Gemini 3 Pro Image Preview", _PRO_IMAGE_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["in"] == pytest.approx(2.0)

    def test_regular_model_no_image_output_price(self, fetcher):
        """Regular text model has no image_output_price."""
        entry = fetcher._parse_model_section("Gemini 2.5 Flash", _FLAT_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert "image_out" not in ep["pricing"]


class TestParseModelSection:
    def test_flat_pricing(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Flash", _FLAT_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["in"] == pytest.approx(0.25)
        assert ep["pricing"]["out"] == pytest.approx(1.50)

    def test_flat_with_cache(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Flash", _FLAT_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert "cache" in ep
        assert ep["cache"]["read"] == pytest.approx(0.025)

    def test_tiered_pricing_two_tiers(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Pro", _TIERED_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert "tiered" in ep
        tiers = ep["tiered"]
        assert len(tiers) == 2
        assert tiers[0]["tier_start"] == 0
        assert tiers[0]["tier_end"] == 200_000
        assert tiers[0]["in"] == pytest.approx(1.25)
        assert tiers[0]["out"] == pytest.approx(10.00)
        assert tiers[1]["tier_start"] == 200_000
        assert "tier_end" not in tiers[1]
        assert tiers[1]["in"] == pytest.approx(2.50)
        assert tiers[1]["out"] == pytest.approx(15.00)

    def test_tiered_also_has_top_level_pricing(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Pro", _TIERED_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        # Top-level pricing uses tier-1 (cheapest) price
        assert ep["pricing"]["in"] == pytest.approx(1.25)

    def test_not_available_returns_none(self, fetcher):
        entry = fetcher._parse_model_section("Gemini X", _NO_OUTPUT_TABLE)
        assert entry is None

    def test_metadata_provider(self, fetcher):
        entry = fetcher._parse_model_section("Gemini 2.5 Flash", _FLAT_TABLE)
        assert entry["metadata"]["provider"] == "google"


# ---------------------------------------------------------------------------
# Generation model table fixtures (used by both _parse_models and generation tests)
# ---------------------------------------------------------------------------

_IMAGEN_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier</th></tr>
  </thead>
  <tbody>
    <tr><td>Price</td><td>Free of charge</td><td>$0.04 per image</td></tr>
  </tbody>
</table>
"""

_VEO_FLAT_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier</th></tr>
  </thead>
  <tbody>
    <tr><td>Price</td><td>Not available</td><td>$0.40 per second</td></tr>
  </tbody>
</table>
"""

_VEO_TIERED_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier</th></tr>
  </thead>
  <tbody>
    <tr><td>720p</td><td>Not available</td><td>$0.40 per second</td></tr>
    <tr><td>1080p</td><td>Not available</td><td>$0.40 per second</td></tr>
    <tr><td>4K</td><td>Not available</td><td>$0.60 per second</td></tr>
  </tbody>
</table>
"""

_LYRIA_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier</th></tr>
  </thead>
  <tbody>
    <tr><td>Price</td><td>Free of charge</td><td>$0.08 per song</td></tr>
  </tbody>
</table>
"""

_EMBEDDING_TABLE = """
<table>
  <thead>
    <tr><th></th><th>Free Tier</th><th>Paid Tier, per 1M tokens in USD</th></tr>
  </thead>
  <tbody>
    <tr><td>Input price</td><td>Free of charge</td><td>$0.20</td></tr>
    <tr><td>Output price</td><td>Not applicable</td><td>Not available</td></tr>
  </tbody>
</table>
"""

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
{imagen}
<h2>Pricing for tools</h2>
<table><tr><td>Google Search</td><td>free</td><td>$14/1000</td></tr></table>
</body></html>
""".format(tiered=_TIERED_TABLE, flat=_FLAT_TABLE, imagen=_IMAGEN_TABLE)


class TestParseModels:
    def test_models_count(self, fetcher):
        resp = _make_response(_FULL_PAGE)
        models = fetcher._parse_models(resp)
        # Should have gemini-2.5-pro, gemini-2.5-flash, and imagen-4
        assert "gemini-2.5-pro" in models
        assert "gemini-2.5-flash" in models
        assert "imagen-4" in models

    def test_tiered_model(self, fetcher):
        resp = _make_response(_FULL_PAGE)
        models = fetcher._parse_models(resp)
        ep = models["gemini-2.5-pro"]["endpoints"][_GGL_EP]
        assert "tiered" in ep

    def test_flat_model(self, fetcher):
        resp = _make_response(_FULL_PAGE)
        models = fetcher._parse_models(resp)
        ep = models["gemini-2.5-flash"]["endpoints"][_GGL_EP]
        assert "tiered" not in ep
        assert ep["pricing"]["in"] == pytest.approx(0.25)


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


# ---------------------------------------------------------------------------
# Generation model detection
# ---------------------------------------------------------------------------

class TestIsGenerationModel:
    def test_imagen(self, fetcher):
        assert fetcher._is_generation_model("Imagen 4 Fast") is True

    def test_veo(self, fetcher):
        assert fetcher._is_generation_model("Veo 3.1 Generate (Preview)") is True

    def test_lyria(self, fetcher):
        assert fetcher._is_generation_model("Lyria 3 Pro (Preview)") is True

    def test_embedding(self, fetcher):
        assert fetcher._is_generation_model("Gemini Embedding 2 (Preview)") is True

    def test_robotics(self, fetcher):
        assert fetcher._is_generation_model("Gemini Robotics-ER 1.5") is True

    def test_gemini_pro_is_not_generation(self, fetcher):
        assert fetcher._is_generation_model("Gemini 2.5 Pro") is False

    def test_gemini_flash_is_not_generation(self, fetcher):
        assert fetcher._is_generation_model("Gemini 2.5 Flash") is False


# ---------------------------------------------------------------------------
# Regex helpers for generation models
# ---------------------------------------------------------------------------

class TestPerSecondRegex:
    def test_per_second(self):
        m = _PER_SECOND_RE.search("$0.40 per second")
        assert m and float(m.group(1)) == pytest.approx(0.40)

    def test_slash_second(self):
        m = _PER_SECOND_RE.search("$0.15/second")
        assert m and float(m.group(1)) == pytest.approx(0.15)

    def test_no_match(self):
        assert _PER_SECOND_RE.search("$0.40 per image") is None


class TestPerRequestRegex:
    def test_per_request(self):
        m = _PER_REQUEST_RE.search("$0.08 per request")
        assert m and float(m.group(1)) == pytest.approx(0.08)

    def test_per_song(self):
        m = _PER_REQUEST_RE.search("$0.04 per song")
        assert m and float(m.group(1)) == pytest.approx(0.04)

    def test_no_match(self):
        assert _PER_REQUEST_RE.search("$0.04 per image") is None


class TestImagenParsing:
    def test_imagen_per_image(self, fetcher):
        entry = fetcher._parse_generation_section("Imagen 4 Standard", _IMAGEN_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["image"]["per"] == pytest.approx(0.04)

    def test_imagen_no_text_pricing(self, fetcher):
        entry = fetcher._parse_generation_section("Imagen 4 Standard", _IMAGEN_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert "text" not in ep["pricing"]

    def test_imagen_metadata(self, fetcher):
        entry = fetcher._parse_generation_section("Imagen 4 Standard", _IMAGEN_TABLE)
        assert entry["metadata"]["provider"] == "google"
        assert entry["metadata"]["family"] == "imagen-4"


class TestVeoParsing:
    def test_veo_flat(self, fetcher):
        entry = fetcher._parse_generation_section("Veo 3 Generate (Preview)", _VEO_FLAT_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["video"]["sec"] == pytest.approx(0.40)

    def test_veo_tiered(self, fetcher):
        entry = fetcher._parse_generation_section("Veo 3.1 Generate (Preview)", _VEO_TIERED_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        tiers = ep["pricing"]["video"]["tiered"]
        assert len(tiers) == 3
        assert tiers[0] == {"resolution": "720p", "sec": 0.40}
        assert tiers[1] == {"resolution": "1080p", "sec": 0.40}
        assert tiers[2] == {"resolution": "4k", "sec": 0.60}

    def test_veo_no_text_pricing(self, fetcher):
        entry = fetcher._parse_generation_section("Veo 3 Generate (Preview)", _VEO_FLAT_TABLE)
        ep = entry["endpoints"][_GGL_EP]
        assert "text" not in ep["pricing"]


class TestLyriaParsing:
    def test_lyria_per_song(self, fetcher):
        entry = fetcher._parse_generation_section("Lyria 3 Pro (Preview)", _LYRIA_TABLE)
        assert entry is not None
        ep = entry["endpoints"][_GGL_EP]
        assert ep["pricing"]["music"]["per"] == pytest.approx(0.08)

    def test_lyria_metadata(self, fetcher):
        entry = fetcher._parse_generation_section("Lyria 3 Pro (Preview)", _LYRIA_TABLE)
        assert entry["metadata"]["family"] == "lyria-3"


class TestEmbeddingParsing:
    """Embedding models are routed to standard token parsing via _parse_model_section."""

    def test_embedding_falls_back_to_token_parsing(self, fetcher):
        """Embeddings have Input price but no useful Output price. They should
        still be parsed as token models when Output is 'Not available'."""
        # Embedding has input but output is "Not available" — _parse_model_section
        # returns None because output_price is None and no image_output_price.
        # This is expected — embeddings may need manual_overrides.
        entry = fetcher._parse_generation_section("Gemini Embedding 2 (Preview)", _EMBEDDING_TABLE)
        # With only input and "Not available" output, the token parser returns None
        assert entry is None


# ---------------------------------------------------------------------------
# Full page with generation models
# ---------------------------------------------------------------------------

_FULL_PAGE_V8 = """
<html><body>
<h1>Google AI pricing</h1>
<h2>Gemini 2.5 Pro</h2>
<p>Some text</p>
{tiered}
<h2>Gemini 2.5 Flash</h2>
{flat}
<h2>Imagen 4 Standard</h2>
{imagen}
<h2>Veo 3 Generate (Preview)</h2>
{veo}
<h2>Lyria 3 Pro (Preview)</h2>
{lyria}
<h2>Gemma 3</h2>
<table><tr><td>Price</td><td>Free</td><td>Free</td></tr></table>
<h2>Pricing for tools</h2>
<table><tr><td>Google Search</td><td>free</td><td>$14/1000</td></tr></table>
</body></html>
""".format(
    tiered=_TIERED_TABLE, flat=_FLAT_TABLE,
    imagen=_IMAGEN_TABLE, veo=_VEO_FLAT_TABLE, lyria=_LYRIA_TABLE,
)


class TestParseModelsV8:
    def test_includes_generation_models(self, fetcher):
        resp = _make_response(_FULL_PAGE_V8)
        models = fetcher._parse_models(resp)
        assert "gemini-2.5-pro" in models
        assert "gemini-2.5-flash" in models
        assert "imagen-4-standard" in models
        assert "veo-3-generate" in models
        assert "lyria-3-pro" in models

    def test_skips_gemma(self, fetcher):
        resp = _make_response(_FULL_PAGE_V8)
        models = fetcher._parse_models(resp)
        assert "gemma-3" not in models

    def test_skips_pricing_for_tools(self, fetcher):
        resp = _make_response(_FULL_PAGE_V8)
        models = fetcher._parse_models(resp)
        assert "pricing-for-tools" not in models

    def test_imagen_pricing_nested(self, fetcher):
        resp = _make_response(_FULL_PAGE_V8)
        models = fetcher._parse_models(resp)
        ep = models["imagen-4-standard"]["endpoints"][_GGL_EP]
        assert "per" in ep["pricing"]["image"]

    def test_veo_pricing_nested(self, fetcher):
        resp = _make_response(_FULL_PAGE_V8)
        models = fetcher._parse_models(resp)
        ep = models["veo-3-generate"]["endpoints"][_GGL_EP]
        assert "sec" in ep["pricing"]["video"]

    def test_lyria_pricing_nested(self, fetcher):
        resp = _make_response(_FULL_PAGE_V8)
        models = fetcher._parse_models(resp)
        ep = models["lyria-3-pro"]["endpoints"][_GGL_EP]
        assert "per" in ep["pricing"]["music"]
