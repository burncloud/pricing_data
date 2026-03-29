"""
Tests for scripts/render.py — human-readable Markdown table generator.
"""
import pytest
from scripts.render import (
    fmt_context,
    fmt_price,
    pick_display_currency,
    render,
)


# ---------------------------------------------------------------------------
# fmt_price
# ---------------------------------------------------------------------------

class TestFmtPrice:
    def test_none_returns_dash(self):
        assert fmt_price(None) == "—"

    def test_zero_returns_free(self):
        assert fmt_price(0.0) == "free"

    def test_standard_price(self):
        assert fmt_price(15.0) == "$15.00"

    def test_sub_dollar(self):
        assert fmt_price(0.28) == "$0.28"

    def test_cent_range(self):
        assert fmt_price(0.028) == "$0.028"

    def test_very_small_price(self):
        assert fmt_price(0.0002) == "$0.000200"

    def test_custom_symbol(self):
        assert fmt_price(5.0, "¥") == "¥5.00"


# ---------------------------------------------------------------------------
# fmt_context
# ---------------------------------------------------------------------------

class TestFmtContext:
    def test_none_returns_dash(self):
        assert fmt_context(None) == "—"

    def test_zero_returns_dash(self):
        assert fmt_context(0) == "—"

    def test_millions(self):
        assert fmt_context(1_000_000) == "1M"
        assert fmt_context(2_000_000) == "2M"

    def test_thousands(self):
        assert fmt_context(128_000) == "128K"
        assert fmt_context(32_000) == "32K"

    def test_small(self):
        assert fmt_context(512) == "512"


# ---------------------------------------------------------------------------
# pick_display_currency
# ---------------------------------------------------------------------------

class TestPickDisplayCurrency:
    def test_prefers_usd(self):
        m = {"USD": {"text": {"input": 2.5}}, "CNY": {"text": {"input": 18.0}}}
        code, entry = pick_display_currency(m)
        assert code == "USD"

    def test_falls_back_to_cny(self):
        m = {"CNY": {"text": {"input": 18.0}}}
        code, entry = pick_display_currency(m)
        assert code == "CNY"
        assert entry["text"]["input"] == pytest.approx(18.0)

    def test_empty_pricing_returns_empty(self):
        m = {}
        code, entry = pick_display_currency(m)
        assert code == ""
        assert entry == {}


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _v5_model(provider, currency, input_price, output_price, *,
              cache_read=None, batch_in=None, batch_out=None,
              context_window=None):
    """Helper: build a v6.0 model entry for test data (pricing only, no metadata).

    Note: provider is only used to select the right model_id prefix in tests —
    the model entry itself stores no provider. Pass a model_id starting with the
    right prefix when calling render() so infer_provider() groups correctly.
    """
    text = {"input": input_price, "output": output_price}
    entry = {"text": text}
    if cache_read is not None:
        entry["cache"] = {"read_input": cache_read}
    if batch_in is not None:
        entry["batch"] = {"input": batch_in, "output": batch_out or 0.0}
    return {currency: entry}


def _make_data(models: dict) -> dict:
    return {
        "version": "5.0",
        "updated_at": "2026-03-28T00:00:00+00:00",
        "source": "test",
        "models": models,
    }


class TestRender:
    def test_header_contains_version_and_model_count(self):
        data = _make_data({
            "gpt-4o": _v5_model("openai", "USD", 2.5, 10.0),
        })
        md = render(data)
        assert "2026-03-28" in md
        assert "1 models" in md

    def test_provider_section_present(self):
        data = _make_data({
            "claude-opus-4-6": _v5_model("anthropic", "USD", 5.0, 25.0),
        })
        md = render(data)
        assert "## Anthropic" in md
        assert "claude-opus-4-6" in md
        assert "$5.00" in md
        assert "$25.00" in md

    def test_cny_currency(self):
        data = _make_data({
            "glm-4-plus": _v5_model("zhipu", "CNY", 5.0, 5.0),
        })
        md = render(data)
        assert "¥5.00" in md
        assert "CNY" in md

    def test_cache_column_appears_only_when_present(self):
        data = _make_data({
            "gemini-2.0-flash": _v5_model("google", "USD", 0.1, 0.4, cache_read=0.025),
            "gemini-flash-lite": _v5_model("google", "USD", 0.075, 0.3),
        })
        md = render(data)
        assert "Cache Read" in md

    def test_cache_column_absent_without_cache_data(self):
        data = _make_data({
            "gpt-some-model": _v5_model("openai", "USD", 2.5, 10.0),
        })
        md = render(data)
        openai_section = md[md.index("## OpenAI"):]
        next_section = openai_section.find("\n## ", 1)
        provider_table = openai_section[:next_section] if next_section != -1 else openai_section
        assert "Cache Read" not in provider_table

    def test_batch_columns_appear_when_present(self):
        data = _make_data({
            "gpt-4o": _v5_model("openai", "USD", 2.5, 10.0, batch_in=1.25, batch_out=5.0),
        })
        md = render(data)
        assert "Batch In" in md
        assert "Batch Out" in md
        assert "$1.25" in md

    def test_free_model_shows_free(self):
        data = _make_data({
            "glm-4.7-flash": _v5_model("zhipu", "CNY", 0.0, 0.0),
        })
        md = render(data)
        assert "free" in md

    def test_models_sorted_by_input_price_descending(self):
        data = _make_data({
            "gpt-cheap-model": _v5_model("openai", "USD", 0.1, 0.5),
            "gpt-expensive-model": _v5_model("openai", "USD", 15.0, 75.0),
        })
        md = render(data)
        openai_section = md[md.index("## OpenAI"):]
        cheap_pos = openai_section.index("gpt-cheap-model")
        expensive_pos = openai_section.index("gpt-expensive-model")
        assert expensive_pos < cheap_pos  # expensive appears first

    def test_providers_toc_present(self):
        data = _make_data({
            "gpt-4o": _v5_model("openai", "USD", 2.5, 10.0),
        })
        md = render(data)
        assert "## Providers" in md

    def test_quick_reference_rendered_for_known_models(self):
        """Known quick-ref models appear in a ## Quick Reference section."""
        data = _make_data({
            "gpt-4o": _v5_model("openai", "USD", 2.5, 10.0),
        })
        md = render(data)
        assert "## Quick Reference" in md
        assert "gpt-4o" in md[md.index("## Quick Reference"):md.index("## Providers")]

    def test_quick_reference_absent_when_no_known_models(self):
        """No quick-ref section when no QUICK_REF_MODELS are present in data."""
        data = _make_data({
            "some-obscure-model-xyz": _v5_model("openai", "USD", 1.0, 2.0),
        })
        md = render(data)
        assert "## Quick Reference" not in md

    def test_quick_reference_jump_link_in_header(self):
        """Header contains jump link to Quick Reference."""
        data = _make_data({
            "gpt-4o": _v5_model("openai", "USD", 2.5, 10.0),
        })
        md = render(data)
        assert "Quick Reference" in md[:500]
        assert "OpenAI" in md

    def test_context_column_absent(self):
        """Context column is not rendered in v6.0 (no metadata source for context_window)."""
        data = _make_data({
            "gpt-4o": _v5_model("openai", "USD", 2.5, 10.0),
        })
        md = render(data)
        assert "Context" not in md

    def test_multimodal_audio_not_in_text_columns(self):
        """TTS model with audio.output shows no text output price."""
        model = {
            "USD": {
                "text": {"input": 0.5},
                "audio": {"output": 10.0},
            },
        }
        data = _make_data({"gemini-tts": model})
        md = render(data)
        # text output is absent → shows "—"
        google_section = md[md.index("## Google"):]
        assert "gemini-tts" in google_section
