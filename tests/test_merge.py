"""
Tests for merge module.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.merge import PricingMerger
from scripts.config import config


# ---------------------------------------------------------------------------
# Helper: build an endpoint entry in the v2.0 format
# ---------------------------------------------------------------------------

def _ep(ep_key, pricing, *, currency="USD", base_url="", cache_pricing=None,
        batch_pricing=None, tiered_pricing=None):
    """Build a model entry with a single endpoint."""
    ep_data = {
        "base_url": base_url,
        "currency": currency,
        "pricing": pricing,
    }
    if cache_pricing is not None:
        ep_data["cache_pricing"] = cache_pricing
    if batch_pricing is not None:
        ep_data["batch_pricing"] = batch_pricing
    if tiered_pricing is not None:
        ep_data["tiered_pricing"] = tiered_pricing
    return {"endpoints": {ep_key: ep_data}}


def _model(ep_key, pricing, *, currency="USD", base_url="", metadata=None,
           cache_pricing=None, batch_pricing=None, tiered_pricing=None):
    """Build a full model entry (endpoints + metadata)."""
    entry = _ep(ep_key, pricing, currency=currency, base_url=base_url,
                cache_pricing=cache_pricing, batch_pricing=batch_pricing,
                tiered_pricing=tiered_pricing)
    entry["metadata"] = metadata or {}
    return entry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_openai_data():
    """Sample OpenAI pricing data (v2.0 endpoint-keyed)."""
    return {
        "status": "success",
        "models": {
            "gpt-4o": _model(
                "api.openai.com",
                {"input_price": 2.50, "output_price": 10.00},
                base_url="https://api.openai.com/v1",
                metadata={"provider": "openai"},
            ),
            "gpt-4o-mini": _model(
                "api.openai.com",
                {"input_price": 0.15, "output_price": 0.60},
                base_url="https://api.openai.com/v1",
                metadata={"provider": "openai"},
            ),
        },
    }


@pytest.fixture
def sample_openrouter_data():
    """Sample OpenRouter pricing data (v2.0 endpoint-keyed)."""
    return {
        "status": "success",
        "models": {
            "openai/gpt-4o": _model(
                "openrouter.ai",
                {"input_price": 2.50, "output_price": 10.00},
                base_url="https://openrouter.ai/api/v1",
                metadata={"provider": "openai"},
            ),
            "openai/gpt-4o-mini": _model(
                "openrouter.ai",
                {"input_price": 0.15, "output_price": 0.60},
                base_url="https://openrouter.ai/api/v1",
                metadata={"provider": "openai"},
            ),
            "anthropic/claude-3.5-sonnet": _model(
                "openrouter.ai",
                {"input_price": 3.00, "output_price": 15.00},
                base_url="https://openrouter.ai/api/v1",
                metadata={"provider": "anthropic"},
            ),
        },
    }


@pytest.fixture
def sample_chinese_data():
    """Sample Chinese provider data (v2.0 endpoint-keyed, CNY)."""
    return {
        "status": "success",
        "models": {
            "qwen-max": _model(
                "dashscope.aliyuncs.com",
                {"input_price": 40.0, "output_price": 120.0},
                currency="CNY",
                base_url="https://dashscope.aliyuncs.com/api/v1",
                metadata={"provider": "aliyun"},
            ),
            "glm-4": _model(
                "open.bigmodel.cn",
                {"input_price": 100.0, "output_price": 100.0},
                currency="CNY",
                base_url="https://open.bigmodel.cn/api/paas/v4",
                metadata={"provider": "zhipu"},
            ),
        },
    }


class TestPricingMerger:
    """Tests for PricingMerger class."""

    def test_merge_single_source(self, sample_openai_data, tmp_path):
        """Test merging from a single source."""
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        assert result["version"] == "2.0"
        assert "models" in result
        assert len(result["models"]) == 2
        assert "gpt-4o" in result["models"]
        assert len(warnings) == 0

    def test_merge_multiple_sources_priority(
        self,
        sample_openai_data,
        sample_openrouter_data,
        tmp_path
    ):
        """Test that original provider takes priority over aggregator."""
        # Both sources claim the same endpoint key for drift detection
        # openrouter/gpt-4o claims api.openai.com with a different price
        sample_openrouter_data["models"]["openai/gpt-4o"]["endpoints"]["openrouter.ai"]["pricing"]["input_price"] = 3.00

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(sample_openrouter_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "min_models_guard", {}), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        # OpenAI (priority 100) wins — its api.openai.com endpoint present
        assert result["models"]["gpt-4o"]["endpoints"]["api.openai.com"]["pricing"]["input_price"] == 2.50

    def test_normalize_model_id(self):
        """Test model ID normalization."""
        merger = PricingMerger()

        # OpenRouter prefix removal
        assert merger._normalize_model_id("openai/gpt-4o", "openrouter") == "gpt-4o"
        assert merger._normalize_model_id("anthropic/claude-3.5-sonnet", "openrouter") == "claude-3.5-sonnet"

        # Non-OpenRouter keeps as-is
        assert merger._normalize_model_id("gpt-4o", "openai") == "gpt-4o"
        assert merger._normalize_model_id("qwen-max", "aliyun") == "qwen-max"

    def test_merge_chinese_providers(
        self,
        sample_openai_data,
        sample_chinese_data,
        tmp_path
    ):
        """Test merging Chinese provider data."""
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        with open(sources_dir / "chinese-all.json", "w") as f:
            json.dump(sample_chinese_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        # Should have both Western and Chinese models
        assert "gpt-4o" in result["models"]
        assert "qwen-max" in result["models"]
        assert "glm-4" in result["models"]

        # Chinese models have CNY endpoint
        assert "dashscope.aliyuncs.com" in result["models"]["qwen-max"]["endpoints"]
        assert result["models"]["qwen-max"]["endpoints"]["dashscope.aliyuncs.com"]["currency"] == "CNY"

    def test_merge_no_sources_raises(self, tmp_path):
        """Test that merge raises when no sources exist (including no manual_overrides)."""
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            with pytest.raises(ValueError, match="No source data found"):
                merger.merge_all("2024-01-01")

    def test_save_merged_data(self, sample_openai_data, tmp_path):
        """Test saving merged output."""
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            with patch.object(config, "pricing_file", output_dir / "pricing.json"):
                result, _ = merger.merge_all("2024-01-01")
                output_path = merger.save(result)

        assert output_path.exists()

        with open(output_path) as f:
            saved_data = json.load(f)

        assert saved_data["version"] == "2.0"
        assert "updated_at" in saved_data
        assert "models" in saved_data


class TestPriceConflictDetection:
    """Tests for price conflict detection."""

    def test_large_drift_warning(self, sample_openai_data, tmp_path):
        """Warning for significant price drift on the same endpoint key."""
        # Two sources both claim api.openai.com for gpt-4o with different prices
        conflicting_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 5.00, "output_price": 10.00},  # 100% higher
                    base_url="https://api.openai.com/v1",
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        with open(sources_dir / "openai2.json", "w") as f:
            json.dump(conflicting_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "min_models_guard", {}), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        assert len(warnings) > 0
        assert any("gpt-4o" in w for w in warnings)

    def test_small_drift_no_warning(self, sample_openai_data, tmp_path):
        """No warning for small price differences."""
        close_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.51, "output_price": 10.00},  # 0.4% difference
                    base_url="https://api.openai.com/v1",
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        with open(sources_dir / "openai2.json", "w") as f:
            json.dump(close_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "min_models_guard", {}), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        assert len(warnings) == 0


class TestNormalizeModelFormat:
    """Tests for _normalize_model_format post-processing."""

    def test_unit_field_removed(self):
        """unit field in endpoint pricing must not appear in output."""
        merger = PricingMerger()
        model = _model(
            "api.openai.com",
            {"input_price": 2.50, "output_price": 10.00, "unit": "per_million_tokens"},
            metadata={"provider": "openai"},
        )
        result = merger._normalize_model_format(model)
        assert "unit" not in result["endpoints"]["api.openai.com"]["pricing"]

    def test_null_output_price_set_to_zero(self):
        """output_price: null → 0.0 in endpoint pricing."""
        merger = PricingMerger()
        model = _model(
            "api.openai.com",
            {"input_price": 2.0, "output_price": None},
            metadata={"provider": "openai"},
        )
        result = merger._normalize_model_format(model)
        assert result["endpoints"]["api.openai.com"]["pricing"]["output_price"] == 0.0

    def test_cache_write_input_price_renamed(self):
        """cache_write_input_price → cache_creation_input_price."""
        merger = PricingMerger()
        model = _model(
            "api.anthropic.com",
            {"input_price": 3.0, "output_price": 15.0},
            cache_pricing={
                "cache_write_input_price": 3.75,
                "cache_read_input_price": 0.30,
            },
            metadata={"provider": "anthropic"},
        )
        result = merger._normalize_model_format(model)
        cp = result["endpoints"]["api.anthropic.com"]["cache_pricing"]
        assert "cache_creation_input_price" in cp
        assert "cache_write_input_price" not in cp
        assert cp["cache_creation_input_price"] == 3.75

    def test_cache_unit_field_removed(self):
        """unit field inside cache_pricing must be removed."""
        merger = PricingMerger()
        model = _model(
            "api.anthropic.com",
            {"input_price": 3.0, "output_price": 15.0},
            cache_pricing={
                "cache_read_input_price": 0.30,
                "unit": "per_million_tokens",
            },
            metadata={"provider": "anthropic"},
        )
        result = merger._normalize_model_format(model)
        assert "unit" not in result["endpoints"]["api.anthropic.com"]["cache_pricing"]

    def test_original_model_not_mutated(self):
        """_normalize_model_format must not mutate its input."""
        merger = PricingMerger()
        model = _model(
            "api.openai.com",
            {"input_price": 2.0, "output_price": 10.0, "unit": "per_million_tokens"},
            metadata={"provider": "openai"},
        )
        merger._normalize_model_format(model)
        assert "unit" in model["endpoints"]["api.openai.com"]["pricing"], \
            "original dict should not be mutated"


class TestManualOverrides:
    """Tests for manual_overrides.json loading."""

    def test_manual_overrides_loaded_with_highest_priority(self, tmp_path):
        """manual_overrides source gets priority 200 — highest of all sources."""
        overrides = {
            "models": {
                "gemini-3-pro": _model(
                    "generativelanguage.googleapis.com",
                    {"input_price": 2.0, "output_price": 0.0},
                    base_url="https://generativelanguage.googleapis.com",
                    metadata={"provider": "google"},
                ),
            }
        }
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        overrides_dir = tmp_path / "sources"
        with open(overrides_dir / "manual_overrides.json", "w") as f:
            json.dump(overrides, f)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert "gemini-3-pro" in result["models"]
        assert result["models"]["gemini-3-pro"]["metadata"]["_merged_from"] == "manual_overrides"

    def test_manual_overrides_override_openrouter(self, tmp_path):
        """manual_overrides (priority 200) beats openrouter (priority 50) for same model."""
        overrides = {
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 9.99, "output_price": 0.0},
                    metadata={"provider": "openai"},
                ),
            }
        }
        openrouter_data = {
            "status": "success",
            "models": {
                "openai/gpt-4o": _model(
                    "openrouter.ai",
                    {"input_price": 2.50, "output_price": 10.0},
                    base_url="https://openrouter.ai/api/v1",
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        overrides_dir = tmp_path / "sources"
        with open(overrides_dir / "manual_overrides.json", "w") as f:
            json.dump(overrides, f)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "min_models_guard", {}), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert result["models"]["gpt-4o"]["endpoints"]["api.openai.com"]["pricing"]["input_price"] == 9.99


class TestMinModelsGuard:
    """Tests for min_models guard protecting against broken fetches."""

    def test_source_skipped_below_min_models(self, tmp_path):
        """Source with fewer models than min_models_guard threshold is skipped."""
        sparse_openrouter = {
            "status": "success",
            "models": {
                "openai/gpt-4o": _model(
                    "openrouter.ai",
                    {"input_price": 2.50, "output_price": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(sparse_openrouter, f)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)

        merger = PricingMerger()

        # Default guard: openrouter requires 50 models
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        # openrouter was skipped so only 1 model (from openai, not openrouter)
        assert len(result["models"]) == 1
        # The model came from openai, not openrouter
        assert result["models"]["gpt-4o"]["metadata"]["_merged_from"] == "openai"

    def test_source_accepted_at_min_models(self, tmp_path):
        """Source with exactly min_models models is accepted."""
        # Build an openrouter payload with exactly 50 models
        models = {}
        for i in range(50):
            models[f"provider/model-{i}"] = _model(
                "openrouter.ai",
                {"input_price": 1.0, "output_price": 2.0},
                metadata={"provider": "provider"},
            )
        openrouter_data = {"status": "success", "models": models}

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert len(result["models"]) == 50


class TestFieldLevelEnrichment:
    """Endpoint-level enrichment: different endpoint keys from different sources coexist."""

    def test_batch_pricing_from_litellm_endpoint(self, tmp_path):
        """openai (priority 100) provides api.openai.com; litellm (70) provides litellm
        endpoint with batch_pricing — both endpoints appear in merged result."""
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        litellm_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "litellm",
                    {"input_price": 2.50, "output_price": 10.0},
                    batch_pricing={"input_price": 1.25, "output_price": 5.0},
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)
        with open(sources_dir / "litellm.json", "w") as f:
            json.dump(litellm_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        model = result["models"]["gpt-4o"]
        # openai wins primary
        assert model["metadata"]["_merged_from"] == "openai"
        # litellm endpoint present with batch_pricing
        assert "litellm" in model["endpoints"]
        assert "batch_pricing" in model["endpoints"]["litellm"]
        assert model["endpoints"]["litellm"]["batch_pricing"]["input_price"] == pytest.approx(1.25)

    def test_tiered_pricing_from_litellm_endpoint(self, tmp_path):
        """litellm endpoint with tiered_pricing coexists alongside openai endpoint."""
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        litellm_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "litellm",
                    {"input_price": 2.50, "output_price": 10.0},
                    tiered_pricing=[
                        {"tier_start": 0, "tier_end": 128000, "input_price": 2.5, "output_price": 10.0},
                        {"tier_start": 128000, "input_price": 5.0, "output_price": 10.0},
                    ],
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)
        with open(sources_dir / "litellm.json", "w") as f:
            json.dump(litellm_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        model = result["models"]["gpt-4o"]
        assert "litellm" in model["endpoints"]
        assert "tiered_pricing" in model["endpoints"]["litellm"]
        assert len(model["endpoints"]["litellm"]["tiered_pricing"]) == 2

    def test_winner_endpoint_not_overwritten(self, tmp_path):
        """If winner already has an endpoint key, lower source doesn't overwrite it."""
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    batch_pricing={"input_price": 1.25, "output_price": 5.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        # litellm also claims api.openai.com — should NOT overwrite winner
        litellm_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    batch_pricing={"input_price": 0.99, "output_price": 3.0},  # different
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)
        with open(sources_dir / "litellm.json", "w") as f:
            json.dump(litellm_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        # openai's api.openai.com endpoint wins (batch input 1.25), not litellm's (0.99)
        ep = result["models"]["gpt-4o"]["endpoints"]["api.openai.com"]
        assert ep["batch_pricing"]["input_price"] == pytest.approx(1.25)


class TestBatchDriftDetection:
    """Batch pricing drift detection extension to _check_price_conflicts."""

    def test_batch_price_drift_warning(self, tmp_path):
        """When two sources claim same endpoint with conflicting batch_pricing, a warning is emitted."""
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    batch_pricing={"input_price": 1.25, "output_price": 5.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        # Second source claims same endpoint with different batch price (60% drift)
        openai2_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    batch_pricing={"input_price": 0.50, "output_price": 5.0},
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)
        with open(sources_dir / "openai2.json", "w") as f:
            json.dump(openai2_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, warnings = merger.merge_all("2024-01-01")

        batch_warnings = [w for w in warnings if "Batch price" in w and "gpt-4o" in w]
        assert len(batch_warnings) == 1
        assert "60" in batch_warnings[0] or "0.5" in batch_warnings[0]

    def test_no_batch_drift_warning_below_threshold(self, tmp_path):
        """Batch price drift under 1% does not emit a warning."""
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    batch_pricing={"input_price": 1.25, "output_price": 5.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        openai2_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.50, "output_price": 10.0},
                    batch_pricing={"input_price": 1.255, "output_price": 5.0},  # 0.4%
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)
        with open(sources_dir / "openai2.json", "w") as f:
            json.dump(openai2_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, warnings = merger.merge_all("2024-01-01")

        batch_warnings = [w for w in warnings if "Batch price" in w and "gpt-4o" in w]
        assert len(batch_warnings) == 0


class TestMergeEndpoints:
    """Tests for _merge_endpoints: different endpoint keys coexist per the multi-endpoint design."""

    def test_two_endpoints_coexist(self, tmp_path):
        """
        Model with USD from one source (api.openai.com) and CNY from another
        (open.bigmodel.cn) should have both endpoint entries.
        This is the GLM-5 use case: z.ai provides USD, bigmodel.cn provides CNY.
        """
        international_data = {
            "status": "success",
            "models": {
                "glm-5": _model(
                    "api.z.ai",
                    {"input_price": 2.0, "output_price": 8.0},
                    currency="USD",
                    metadata={"provider": "zhipu"},
                ),
            },
        }
        chinese_data = {
            "status": "success",
            "models": {
                "glm-5": _model(
                    "open.bigmodel.cn",
                    {"input_price": 14.0, "output_price": 56.0},
                    currency="CNY",
                    metadata={"provider": "zhipu"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "zhipu.json", "w") as f:
            json.dump(international_data, f)
        with open(sources_dir / "chinese.json", "w") as f:
            json.dump(chinese_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        model = result["models"]["glm-5"]
        # Both endpoints present
        assert "api.z.ai" in model["endpoints"]
        assert "open.bigmodel.cn" in model["endpoints"]
        assert model["endpoints"]["api.z.ai"]["pricing"]["input_price"] == pytest.approx(2.0)
        assert model["endpoints"]["open.bigmodel.cn"]["pricing"]["input_price"] == pytest.approx(14.0)

    def test_higher_priority_endpoint_not_overwritten(self, tmp_path):
        """If winner has an endpoint key and lower source has same key, winner's data wins."""
        high_prio = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 2.5, "output_price": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        # openrouter also claims api.openai.com with wrong price
        low_prio = {
            "status": "success",
            "models": {
                "openai/gpt-4o": _model(
                    "api.openai.com",
                    {"input_price": 99.0, "output_price": 99.0},  # wrong, should be ignored
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(high_prio, f)
        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(low_prio, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        model = result["models"]["gpt-4o"]
        # Winner's api.openai.com untouched
        assert model["endpoints"]["api.openai.com"]["pricing"]["input_price"] == pytest.approx(2.5)

    def test_cny_only_model_preserved(self, tmp_path):
        """Model with only CNY endpoint (Chinese-only model) passes through intact."""
        chinese_data = {
            "status": "success",
            "models": {
                "ernie-4.0": _model(
                    "aip.baidubce.com",
                    {"input_price": 0.12, "output_price": 0.12},
                    currency="CNY",
                    metadata={"provider": "baidu"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "baidu.json", "w") as f:
            json.dump(chinese_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        model = result["models"]["ernie-4.0"]
        ep = model["endpoints"]["aip.baidubce.com"]
        assert ep["currency"] == "CNY"
        assert ep["pricing"]["input_price"] == pytest.approx(0.12)


class TestLiteLLMMergeIntegration:
    """LiteLLM (priority 70) wins over OpenRouter (50) for overlapping models."""

    def test_litellm_wins_over_openrouter(self, tmp_path):
        openrouter_data = {
            "status": "success",
            "models": {
                "openai/gpt-4o": _model(
                    "openrouter.ai",
                    {"input_price": 2.50, "output_price": 10.0},
                    base_url="https://openrouter.ai/api/v1",
                    metadata={"provider": "openai"},
                ),
            },
        }
        litellm_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "litellm",
                    {"input_price": 2.50, "output_price": 10.0},
                    batch_pricing={"input_price": 1.25, "output_price": 5.0},
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)
        with open(sources_dir / "litellm.json", "w") as f:
            json.dump(litellm_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        model = result["models"]["gpt-4o"]
        assert model["metadata"]["_merged_from"] == "litellm"
        # litellm endpoint has batch_pricing
        assert "batch_pricing" in model["endpoints"]["litellm"]
        assert model["endpoints"]["litellm"]["batch_pricing"]["input_price"] == pytest.approx(1.25)

    def test_litellm_only_model_included(self, tmp_path):
        """Model only in LiteLLM (not OpenRouter) still appears in output."""
        litellm_data = {
            "status": "success",
            "models": {
                "doubao-pro-32k-240828": _model(
                    "litellm",
                    {"input_price": 0.8, "output_price": 1.0},
                    metadata={"provider": "volcengine"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "litellm.json", "w") as f:
            json.dump(litellm_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        assert "doubao-pro-32k-240828" in result["models"]
