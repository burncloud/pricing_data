"""
Tests for scripts/render.py — human-readable Markdown table generator.
"""
import pytest
from scripts.render import (
    AGGREGATORS,
    fmt_context,
    fmt_price,
    pick_canonical_endpoint,
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

    def test_large_price(self):
        assert fmt_price(15.0) == "$15.00"

    def test_small_price(self):
        assert fmt_price(0.28) == "$0.28"

    def test_tiny_price(self):
        assert fmt_price(0.028) == "$0.028"

    def test_very_tiny_price(self):
        assert fmt_price(0.0002) == "$0.000200"

    def test_cny_symbol(self):
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
# pick_canonical_endpoint
# ---------------------------------------------------------------------------

class TestPickCanonicalEndpoint:
    def _model(self, endpoints, merged_from="source_a"):
        return {
            "endpoints": endpoints,
            "metadata": {"_merged_from": merged_from},
        }

    def test_prefers_merged_from_if_official(self):
        m = self._model({
            "api.anthropic.com": {"pricing": {"input_price": 5.0}},
            "litellm": {"pricing": {"input_price": 5.0}},
        }, merged_from="anthropic")
        # anthropic → endpoint key "api.anthropic.com" won't be found directly,
        # but "api.anthropic.com" is not an aggregator, so it's picked first
        key, ep = pick_canonical_endpoint(m)
        assert key not in AGGREGATORS

    def test_skips_aggregators_for_official(self):
        m = self._model({
            "litellm": {"pricing": {"input_price": 5.0}},
            "api.anthropic.com": {"pricing": {"input_price": 5.0}},
        }, merged_from="litellm")  # merged_from is aggregator → should skip
        key, ep = pick_canonical_endpoint(m)
        assert key == "api.anthropic.com"

    def test_falls_back_to_litellm_when_no_official(self):
        m = self._model({
            "litellm": {"pricing": {"input_price": 2.5}},
            "openrouter.ai": {"pricing": {"input_price": 2.5}},
        }, merged_from="litellm")
        key, _ = pick_canonical_endpoint(m)
        assert key == "litellm"

    def test_empty_endpoints_returns_empty(self):
        m = {"endpoints": {}, "metadata": {}}
        key, ep = pick_canonical_endpoint(m)
        assert key == ""
        assert ep == {}

    def test_merged_from_official_ep_key_wins(self):
        """When merged_from matches an endpoint key directly, use it."""
        m = self._model({
            "api.deepseek.com": {"currency": "USD", "pricing": {"input_price": 0.28}},
            "litellm": {"currency": "USD", "pricing": {"input_price": 0.28}},
        }, merged_from="api.deepseek.com")
        key, ep = pick_canonical_endpoint(m)
        assert key == "api.deepseek.com"
        assert ep["pricing"]["input_price"] == pytest.approx(0.28)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _make_data(models: dict) -> dict:
    return {
        "version": "2.0",
        "updated_at": "2026-03-28T00:00:00+00:00",
        "source": "test",
        "models": models,
    }


class TestRender:
    def test_header_contains_version_and_model_count(self):
        data = _make_data({
            "gpt-4o": {
                "endpoints": {"litellm": {"currency": "USD", "pricing": {"input_price": 2.5, "output_price": 10.0}}},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            }
        })
        md = render(data)
        assert "2026-03-28" in md
        assert "1 models" in md

    def test_provider_section_present(self):
        data = _make_data({
            "claude-opus-4-6": {
                "endpoints": {"api.anthropic.com": {"currency": "USD", "pricing": {"input_price": 5.0, "output_price": 25.0}}},
                "metadata": {"provider": "anthropic", "_merged_from": "anthropic"},
            }
        })
        md = render(data)
        assert "## Anthropic" in md
        assert "claude-opus-4-6" in md
        assert "$5.00" in md
        assert "$25.00" in md

    def test_cny_currency(self):
        data = _make_data({
            "glm-4-plus": {
                "endpoints": {"open.bigmodel.cn": {"currency": "CNY", "pricing": {"input_price": 5.0, "output_price": 5.0}}},
                "metadata": {"provider": "zhipu", "_merged_from": "zhipu"},
            }
        })
        md = render(data)
        assert "¥5.00" in md
        assert "CNY" in md

    def test_cache_column_appears_only_when_present(self):
        data = _make_data({
            "gemini-2.0-flash": {
                "endpoints": {"generativelanguage.googleapis.com": {
                    "currency": "USD",
                    "pricing": {"input_price": 0.1, "output_price": 0.4},
                    "cache_pricing": {"cache_read_input_price": 0.025},
                }},
                "metadata": {"provider": "google", "_merged_from": "google"},
            },
            "gemini-flash-lite": {
                "endpoints": {"generativelanguage.googleapis.com": {
                    "currency": "USD",
                    "pricing": {"input_price": 0.075, "output_price": 0.3},
                }},
                "metadata": {"provider": "google", "_merged_from": "google"},
            },
        })
        md = render(data)
        assert "Cache Read" in md

    def test_cache_column_absent_without_cache_data(self):
        # Use a model NOT in QUICK_REF_MODELS so the Quick Reference table isn't rendered
        data = _make_data({
            "some-obscure-model": {
                "endpoints": {"litellm": {"currency": "USD", "pricing": {"input_price": 2.5, "output_price": 10.0}}},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            }
        })
        md = render(data)
        # The provider section (## OpenAI) should not have a Cache Read column
        openai_section = md[md.index("## OpenAI"):]
        next_section = openai_section.find("\n## ", 1)
        provider_table = openai_section[:next_section] if next_section != -1 else openai_section
        assert "Cache Read" not in provider_table

    def test_batch_columns_appear_when_present(self):
        data = _make_data({
            "gpt-4o": {
                "endpoints": {"litellm": {
                    "currency": "USD",
                    "pricing": {"input_price": 2.5, "output_price": 10.0},
                    "batch_pricing": {"input_price": 1.25, "output_price": 5.0},
                }},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            }
        })
        md = render(data)
        assert "Batch In" in md
        assert "Batch Out" in md
        assert "$1.25" in md

    def test_free_model_shows_free(self):
        data = _make_data({
            "glm-4.7-flash": {
                "endpoints": {"open.bigmodel.cn": {"currency": "CNY", "pricing": {"input_price": 0.0, "output_price": 0.0}}},
                "metadata": {"provider": "zhipu", "_merged_from": "zhipu"},
            }
        })
        md = render(data)
        assert "free" in md

    def test_models_sorted_by_input_price_descending(self):
        data = _make_data({
            "cheap-model": {
                "endpoints": {"litellm": {"currency": "USD", "pricing": {"input_price": 0.1, "output_price": 0.5}}},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            },
            "expensive-model": {
                "endpoints": {"litellm": {"currency": "USD", "pricing": {"input_price": 15.0, "output_price": 75.0}}},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            },
        })
        md = render(data)
        openai_section = md[md.index("## OpenAI"):]
        cheap_pos = openai_section.index("cheap-model")
        expensive_pos = openai_section.index("expensive-model")
        assert expensive_pos < cheap_pos  # expensive appears first

    def test_providers_toc_present(self):
        data = _make_data({
            "gpt-4o": {
                "endpoints": {"litellm": {"currency": "USD", "pricing": {"input_price": 2.5, "output_price": 10.0}}},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            }
        })
        md = render(data)
        assert "## Providers" in md

    def test_quick_reference_rendered_for_known_models(self):
        """Known quick-ref models appear in a ## Quick Reference section."""
        data = _make_data({
            "gpt-4o": {
                "endpoints": {"litellm": {"currency": "USD", "pricing": {"input_price": 2.5, "output_price": 10.0}}},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            }
        })
        md = render(data)
        assert "## Quick Reference" in md
        assert "gpt-4o" in md[md.index("## Quick Reference"):md.index("## Providers")]

    def test_quick_reference_absent_when_no_known_models(self):
        """No quick-ref section when no QUICK_REF_MODELS are present in data."""
        data = _make_data({
            "some-obscure-model-xyz": {
                "endpoints": {"litellm": {"currency": "USD", "pricing": {"input_price": 1.0, "output_price": 2.0}}},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            }
        })
        md = render(data)
        assert "## Quick Reference" not in md

    def test_quick_reference_jump_link_in_header(self):
        """Header contains jump link to Quick Reference."""
        data = _make_data({
            "gpt-4o": {
                "endpoints": {"litellm": {"currency": "USD", "pricing": {"input_price": 2.5, "output_price": 10.0}}},
                "metadata": {"provider": "openai", "_merged_from": "litellm"},
            }
        })
        md = render(data)
        assert "Quick Reference" in md[:500]
        assert "OpenAI" in md
