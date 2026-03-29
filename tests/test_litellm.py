"""
Tests for LiteLLMFetcher.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from scripts.config import config
from scripts.fetch.litellm import LiteLLMFetcher


@pytest.fixture
def fetcher():
    return LiteLLMFetcher(config)


def _make_response(data: dict) -> Mock:
    """Build a mock requests.Response with .json() returning data."""
    resp = Mock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    resp.headers = {"Content-Type": "application/json"}
    return resp


# ---------------------------------------------------------------------------
# Basic pricing
# ---------------------------------------------------------------------------

class TestBasicPricing:
    def test_standard_model_pricing(self, fetcher):
        """input/output prices converted correctly from per-token to per-million."""
        data = {
            "openai/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "output_cost_per_token": 10e-6,
                "litellm_provider": "openai",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)

        ep = models["gpt-4o"]["endpoints"]["api.openai.com"]
        assert "gpt-4o" in models
        assert ep["pricing"]["in"] == pytest.approx(2.5)
        assert ep["pricing"]["out"] == pytest.approx(10.0)

    def test_model_missing_input_cost_skipped(self, fetcher):
        data = {
            "openai/gpt-4o": {
                "output_cost_per_token": 10e-6,
                "litellm_provider": "openai",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert "gpt-4o" not in models

    def test_model_missing_output_cost_skipped(self, fetcher):
        data = {
            "openai/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "litellm_provider": "openai",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert "gpt-4o" not in models


# ---------------------------------------------------------------------------
# Batch pricing
# ---------------------------------------------------------------------------

class TestBatchPricing:
    def test_batch_pricing_populated(self, fetcher):
        data = {
            "openai/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "output_cost_per_token": 10e-6,
                "input_cost_per_token_batches": 1.25e-6,
                "output_cost_per_token_batches": 5e-6,
                "litellm_provider": "openai",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)

        ep = models["gpt-4o"]["endpoints"]["api.openai.com"]
        assert "batch" in ep
        bp = ep["batch"]
        assert bp["in"] == pytest.approx(1.25)
        assert bp["out"] == pytest.approx(5.0)

    def test_no_batch_pricing_when_fields_absent(self, fetcher):
        data = {
            "openai/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "output_cost_per_token": 10e-6,
                "litellm_provider": "openai",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert "batch" not in models["gpt-4o"]["endpoints"]["api.openai.com"]

    def test_batch_pricing_partial_fields_skipped(self, fetcher):
        """Only one of the two batch fields present — no batch_pricing."""
        data = {
            "openai/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "output_cost_per_token": 10e-6,
                "input_cost_per_token_batches": 1.25e-6,
                # missing output_cost_per_token_batches
                "litellm_provider": "openai",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert "batch" not in models["gpt-4o"]["endpoints"]["api.openai.com"]


# ---------------------------------------------------------------------------
# Explicit tiered_pricing
# ---------------------------------------------------------------------------

class TestExplicitTieredPricing:
    def test_two_tier_explicit(self, fetcher):
        data = {
            "qwen/qwen-max": {
                "input_cost_per_token": 2e-6,
                "output_cost_per_token": 6e-6,
                "tiered": [
                    {"range": [0, 128000], "input_cost_per_token": 2e-6, "output_cost_per_token": 6e-6},
                    {"range": [128000, None], "input_cost_per_token": 4e-6, "output_cost_per_token": 6e-6},
                ],
                "litellm_provider": "qwen",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)

        tiers = models["qwen-max"]["endpoints"]["litellm"]["tiered"]
        assert len(tiers) == 2
        assert tiers[0]["tier_start"] == 0
        assert tiers[0]["tier_end"] == 128000
        assert tiers[0]["in"] == pytest.approx(2.0)
        assert tiers[1]["tier_start"] == 128000
        assert "tier_end" not in tiers[1]  # last tier: open-ended
        assert tiers[1]["in"] == pytest.approx(4.0)

    def test_explicit_tiered_output_price_preserved(self, fetcher):
        """output_cost_per_token in tier entry is used when present."""
        data = {
            "qwen/qwen-max": {
                "input_cost_per_token": 2e-6,
                "output_cost_per_token": 6e-6,
                "tiered": [
                    {"range": [0, 128000], "input_cost_per_token": 2e-6, "output_cost_per_token": 6e-6},
                    {"range": [128000, None], "input_cost_per_token": 4e-6, "output_cost_per_token": 12e-6},
                ],
                "litellm_provider": "qwen",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)

        tiers = models["qwen-max"]["endpoints"]["litellm"]["tiered"]
        assert tiers[0]["out"] == pytest.approx(6.0)
        assert tiers[1]["out"] == pytest.approx(12.0)

    def test_explicit_tiered_missing_output_uses_base(self, fetcher):
        """When tier has no output_cost_per_token, use base output price."""
        data = {
            "qwen/qwen-max": {
                "input_cost_per_token": 2e-6,
                "output_cost_per_token": 6e-6,
                "tiered": [
                    {"range": [0, 128000], "input_cost_per_token": 2e-6},
                    {"range": [128000, None], "input_cost_per_token": 4e-6},
                ],
                "litellm_provider": "qwen",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)

        tiers = models["qwen-max"]["endpoints"]["litellm"]["tiered"]
        # Both tiers get base output_cost_per_token (6e-6 * 1M = 6.0)
        assert tiers[0]["out"] == pytest.approx(6.0)
        assert tiers[1]["out"] == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# Inline tiered pricing (above_128k / above_200k)
# ---------------------------------------------------------------------------

class TestInlineTieredPricing:
    def test_two_tier_inline(self, fetcher):
        """above_128k only → two tiers."""
        data = {
            "anthropic/claude-3-5-sonnet": {
                "input_cost_per_token": 3e-6,
                "output_cost_per_token": 15e-6,
                "input_cost_per_token_above_128k_tokens": 6e-6,
                "litellm_provider": "anthropic",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)

        tiers = models["claude-3-5-sonnet"]["endpoints"]["api.anthropic.com"]["tiered"]
        assert len(tiers) == 2
        assert tiers[0] == {"tier_start": 0, "tier_end": 128000, "in": pytest.approx(3.0), "out": pytest.approx(15.0)}
        assert tiers[1] == {"tier_start": 128000, "in": pytest.approx(6.0), "out": pytest.approx(15.0)}

    def test_three_tier_inline(self, fetcher):
        """above_128k + above_200k → three tiers."""
        data = {
            "google/gemini-1.5-pro": {
                "input_cost_per_token": 1.25e-6,
                "output_cost_per_token": 5e-6,
                "input_cost_per_token_above_128k_tokens": 2.5e-6,
                "input_cost_per_token_above_200k_tokens": 3.5e-6,
                "litellm_provider": "google",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)

        tiers = models["gemini-1.5-pro"]["endpoints"]["generativelanguage.googleapis.com"]["tiered"]
        assert len(tiers) == 3
        assert tiers[0]["tier_start"] == 0
        assert tiers[0]["tier_end"] == 128000
        assert tiers[1]["tier_start"] == 128000
        assert tiers[1]["tier_end"] == 200000
        assert tiers[2]["tier_start"] == 200000
        assert "tier_end" not in tiers[2]

    def test_inline_tiered_output_flat(self, fetcher):
        """All tiers share the base output price."""
        data = {
            "google/gemini-1.5-pro": {
                "input_cost_per_token": 1.25e-6,
                "output_cost_per_token": 5e-6,
                "input_cost_per_token_above_128k_tokens": 2.5e-6,
                "litellm_provider": "google",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)

        tiers = models["gemini-1.5-pro"]["endpoints"]["generativelanguage.googleapis.com"]["tiered"]
        for tier in tiers:
            assert tier["out"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Provider filtering
# ---------------------------------------------------------------------------

class TestProviderFiltering:
    def test_bedrock_models_skipped(self, fetcher):
        data = {
            "bedrock/anthropic.claude-3-sonnet": {
                "input_cost_per_token": 3e-6,
                "output_cost_per_token": 15e-6,
                "litellm_provider": "bedrock",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert len(models) == 0

    def test_vertex_ai_models_skipped(self, fetcher):
        data = {
            "vertex_ai/gemini-1.5-pro": {
                "input_cost_per_token": 1.25e-6,
                "output_cost_per_token": 5e-6,
                "litellm_provider": "vertex_ai",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert len(models) == 0

    def test_azure_models_skipped(self, fetcher):
        data = {
            "azure/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "output_cost_per_token": 10e-6,
                "litellm_provider": "azure",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert len(models) == 0

    def test_vertex_ai_anthropic_models_skipped(self, fetcher):
        """Bare Claude model IDs with vertex_ai-anthropic_models provider are skipped."""
        data = {
            "claude-opus-4-6": {
                "input_cost_per_token": 15e-6,
                "output_cost_per_token": 75e-6,
                "litellm_provider": "vertex_ai-anthropic_models",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert len(models) == 0

    def test_bedrock_converse_skipped(self, fetcher):
        """bedrock_converse proxy route is skipped."""
        data = {
            "bedrock_converse/anthropic.claude-3-sonnet": {
                "input_cost_per_token": 3e-6,
                "output_cost_per_token": 15e-6,
                "litellm_provider": "bedrock_converse",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert len(models) == 0

    def test_direct_provider_included(self, fetcher):
        """Models with direct provider (anthropic, openai) are included."""
        data = {
            "anthropic/claude-3-5-sonnet-20240620": {
                "input_cost_per_token": 3e-6,
                "output_cost_per_token": 15e-6,
                "litellm_provider": "anthropic",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert "claude-3-5-sonnet-20240620" in models


# ---------------------------------------------------------------------------
# Model ID normalization
# ---------------------------------------------------------------------------

class TestModelIdNormalization:
    def test_strip_openai_prefix(self, fetcher):
        assert fetcher._normalize_id("openai/gpt-4o") == "gpt-4o"

    def test_strip_anthropic_prefix(self, fetcher):
        assert fetcher._normalize_id("anthropic/claude-3-5-sonnet-20240620") == "claude-3-5-sonnet-20240620"

    def test_strip_dashscope_prefix(self, fetcher):
        assert fetcher._normalize_id("dashscope/qwen-max") == "qwen-max"

    def test_strip_volcengine_prefix(self, fetcher):
        assert fetcher._normalize_id("volcengine/doubao-pro-32k-240828") == "doubao-pro-32k-240828"

    def test_no_prefix_unchanged(self, fetcher):
        assert fetcher._normalize_id("gpt-4o") == "gpt-4o"


# ---------------------------------------------------------------------------
# Min models guard
# ---------------------------------------------------------------------------

class TestMinModelsGuard:
    def test_response_below_min_models_rejected(self, fetcher):
        """validate_response returns False when model count < 500."""
        # Build a dict with fewer than 500 entries
        data = {f"openai/model-{i}": {} for i in range(10)}
        resp = _make_response(data)
        assert fetcher._validate_response(resp) is False

    def test_response_above_min_models_accepted(self, fetcher):
        data = {f"openai/model-{i}": {} for i in range(600)}
        resp = _make_response(data)
        assert fetcher._validate_response(resp) is True

    def test_non_dict_response_rejected(self, fetcher):
        resp = Mock()
        resp.json.return_value = [{"id": "model-1"}]  # list, not dict
        assert fetcher._validate_response(resp) is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_malformed_entry_skipped(self, fetcher):
        """Entry with invalid types is skipped, others still processed."""
        data = {
            "bad/model": "not-a-dict",
            "openai/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "output_cost_per_token": 10e-6,
                "litellm_provider": "openai",
            },
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert "gpt-4o" in models
        assert "model" not in models  # bad entry silently skipped

    def test_malformed_tiered_pricing_skipped(self, fetcher):
        """Model with invalid tiered_pricing is skipped; no exception raised."""
        data = {
            "openai/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "output_cost_per_token": 10e-6,
                "tiered": "not-a-list",  # invalid
                "litellm_provider": "openai",
            }
        }
        resp = _make_response(data)
        # Should not raise; model is skipped due to parse error
        models = fetcher._parse_models(resp)
        assert "gpt-4o" not in models

    def test_tiered_missing_range_skipped(self, fetcher):
        data = {
            "openai/gpt-4o": {
                "input_cost_per_token": 2.5e-6,
                "output_cost_per_token": 10e-6,
                "tiered": [
                    {"input_cost_per_token": 2e-6},  # missing 'range'
                ],
                "litellm_provider": "openai",
            }
        }
        resp = _make_response(data)
        models = fetcher._parse_models(resp)
        assert "gpt-4o" not in models


# ---------------------------------------------------------------------------
# Full fetch integration (mocked HTTP)
# ---------------------------------------------------------------------------

class TestFetchIntegration:
    def test_fetch_returns_success_result(self, fetcher):
        """Full fetch() call with mocked HTTP returns successful FetchResult."""
        litellm_data = {f"openai/model-{i}": {
            "input_cost_per_token": 1e-6,
            "output_cost_per_token": 2e-6,
            "litellm_provider": "openai",
        } for i in range(600)}

        mock_resp = _make_response(litellm_data)

        with patch.object(fetcher, "_make_request", return_value=mock_resp):
            result = fetcher.fetch()

        assert result.success is True
        assert result.models_count == 600
        assert result.source == "litellm"
