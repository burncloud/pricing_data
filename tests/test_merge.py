"""
Tests for merge module (v3.0 currency-keyed output).
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.merge import PricingMerger
from scripts.config import config


# ---------------------------------------------------------------------------
# Helper: build an endpoint entry in the source format (endpoint-keyed)
# Fetchers still output endpoint-keyed; only the merged output is currency-keyed.
# ---------------------------------------------------------------------------

def _ep(ep_key, pricing, *, currency="USD", base_url="", cache_pricing=None,
        batch_pricing=None, tiered_pricing=None):
    """Build a model entry with a single endpoint (source format)."""
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
    """Build a full model entry (endpoints + metadata) in source format."""
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
    """Sample OpenAI pricing data (source endpoint-keyed format)."""
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
    """Sample OpenRouter pricing data (source endpoint-keyed format)."""
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
    """Sample Chinese provider data (source endpoint-keyed, CNY)."""
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

        assert result["version"] == "3.0"
        assert "models" in result
        assert len(result["models"]) == 2
        assert "gpt-4o" in result["models"]
        assert len(warnings) == 0

    def test_merge_output_is_currency_keyed(self, sample_openai_data, tmp_path):
        """Merged output uses currency-keyed pricing (v3.0 format)."""
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        model = result["models"]["gpt-4o"]
        assert "pricing" in model
        assert "USD" in model["pricing"]
        assert model["pricing"]["USD"]["input_price"] == pytest.approx(2.50)
        assert model["pricing"]["USD"]["output_price"] == pytest.approx(10.00)
        # No endpoints key in output
        assert "endpoints" not in model

    def test_merge_multiple_sources_priority(
        self,
        sample_openai_data,
        sample_openrouter_data,
        tmp_path
    ):
        """Original provider (priority 100) beats aggregator (priority 50)."""
        # openrouter claims a higher price for gpt-4o
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

        # OpenAI (priority 100) wins — openrouter's 3.00 is ignored
        assert result["models"]["gpt-4o"]["pricing"]["USD"]["input_price"] == pytest.approx(2.50)
        # Drift warning fired since openrouter claimed a different USD price
        assert any("gpt-4o" in w for w in warnings)

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
        """Chinese provider data produces CNY pricing entries."""
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        with open(sources_dir / "chinese-all.json", "w") as f:
            json.dump(sample_chinese_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert "gpt-4o" in result["models"]
        assert "qwen-max" in result["models"]
        assert "glm-4" in result["models"]

        # Chinese models have CNY pricing
        assert "CNY" in result["models"]["qwen-max"]["pricing"]
        assert result["models"]["qwen-max"]["pricing"]["CNY"]["input_price"] == pytest.approx(40.0)
        # USD-only models have no CNY entry
        assert "CNY" not in result["models"]["gpt-4o"]["pricing"]

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

        assert saved_data["version"] == "3.0"
        assert "updated_at" in saved_data
        assert "models" in saved_data


class TestPriceConflictDetection:
    """Tests for price drift detection within the same currency."""

    def test_large_drift_warning(self, sample_openai_data, tmp_path):
        """Warning for significant price drift when two sources claim same currency."""
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


class TestNormalization:
    """Normalization applied during merge: null prices, field renames, stray fields."""

    def _merge_single(self, model_data, tmp_path):
        """Helper: merge a single model and return its currency pricing entry."""
        source = {"status": "success", "models": {"test-model": model_data}}
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True, exist_ok=True)
        with open(sources_dir / "test.json", "w") as f:
            json.dump(source, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")
        return result["models"]["test-model"]["pricing"]

    def test_unit_field_removed(self, tmp_path):
        """unit field in source pricing does not appear in merged output."""
        model = _model(
            "api.openai.com",
            {"input_price": 2.50, "output_price": 10.00, "unit": "per_million_tokens"},
            metadata={"provider": "openai"},
        )
        pricing = self._merge_single(model, tmp_path)
        assert "unit" not in pricing["USD"]

    def test_null_output_price_set_to_zero(self, tmp_path):
        """output_price: null in source → 0.0 in merged output."""
        model = _model(
            "api.openai.com",
            {"input_price": 2.0, "output_price": None},
            metadata={"provider": "openai"},
        )
        pricing = self._merge_single(model, tmp_path)
        assert pricing["USD"]["output_price"] == 0.0

    def test_cache_write_input_price_renamed(self, tmp_path):
        """cache_write_input_price → cache_creation_input_price in merged output."""
        model = _model(
            "api.anthropic.com",
            {"input_price": 3.0, "output_price": 15.0},
            cache_pricing={
                "cache_write_input_price": 3.75,
                "cache_read_input_price": 0.30,
            },
            metadata={"provider": "anthropic"},
        )
        pricing = self._merge_single(model, tmp_path)
        cp = pricing["USD"]["cache_pricing"]
        assert "cache_creation_input_price" in cp
        assert "cache_write_input_price" not in cp
        assert cp["cache_creation_input_price"] == pytest.approx(3.75)

    def test_cache_unit_field_removed(self, tmp_path):
        """unit field inside cache_pricing is removed from merged output."""
        model = _model(
            "api.anthropic.com",
            {"input_price": 3.0, "output_price": 15.0},
            cache_pricing={
                "cache_read_input_price": 0.30,
                "unit": "per_million_tokens",
            },
            metadata={"provider": "anthropic"},
        )
        pricing = self._merge_single(model, tmp_path)
        assert "unit" not in pricing["USD"]["cache_pricing"]


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

        assert result["models"]["gpt-4o"]["pricing"]["USD"]["input_price"] == pytest.approx(9.99)


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
        assert result["models"]["gpt-4o"]["metadata"]["_merged_from"] == "openai"

    def test_source_accepted_at_min_models(self, tmp_path):
        """Source with exactly min_models models is accepted."""
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
    """Lower-priority sources contribute missing batch/cache/tiered pricing."""

    def test_batch_pricing_merged_from_litellm(self, tmp_path):
        """openai (priority 100) has no batch_pricing; litellm (70) contributes it."""
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
        assert model["metadata"]["_merged_from"] == "openai"
        usd = model["pricing"]["USD"]
        assert usd["input_price"] == pytest.approx(2.50)
        assert "batch_pricing" in usd
        assert usd["batch_pricing"]["input_price"] == pytest.approx(1.25)

    def test_tiered_pricing_merged_from_litellm(self, tmp_path):
        """litellm tiered_pricing is merged into the winner's USD entry."""
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

        usd = result["models"]["gpt-4o"]["pricing"]["USD"]
        assert "tiered_pricing" in usd
        assert len(usd["tiered_pricing"]) == 2

    def test_winner_batch_pricing_not_overwritten(self, tmp_path):
        """When winner already has batch_pricing, lower source cannot overwrite it."""
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
        litellm_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "litellm",
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

        # openai's batch_pricing wins (1.25), litellm's (0.99) is ignored
        usd = result["models"]["gpt-4o"]["pricing"]["USD"]
        assert usd["batch_pricing"]["input_price"] == pytest.approx(1.25)


class TestPricingCompletenessCheck:
    """Quality check: completeness of batch/cache pricing across currencies."""

    def _merge_two_sources(self, model_usd, model_cny, tmp_path):
        """Helper: merge a model with two currency sources."""
        usd_source = {"status": "success", "models": {"test-model": model_usd}}
        cny_source = {"status": "success", "models": {"test-model": model_cny}}
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "usd_provider.json", "w") as f:
            json.dump(usd_source, f)
        with open(sources_dir / "cny_provider.json", "w") as f:
            json.dump(cny_source, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            return merger.merge_all("2024-01-01")

    def test_completeness_warning_when_usd_has_batch_cny_does_not(self, tmp_path):
        """Warn when USD has batch_pricing but CNY entry lacks it."""
        model_usd = _model(
            "api.deepseek.com",
            {"input_price": 0.27, "output_price": 1.10},
            currency="USD",
            batch_pricing={"input_price": 0.135, "output_price": 0.55},
            metadata={"provider": "deepseek"},
        )
        model_cny = _model(
            "api.deepseek.com",
            {"input_price": 2.0, "output_price": 8.0},
            currency="CNY",
            metadata={"provider": "deepseek"},
        )
        result, warnings = self._merge_two_sources(model_usd, model_cny, tmp_path)

        completeness_warnings = [w for w in warnings if "batch_pricing" in w and "test-model" in w]
        assert len(completeness_warnings) == 1
        assert "CNY" in completeness_warnings[0]
        assert "USD" in completeness_warnings[0]

    def test_completeness_warning_when_usd_has_cache_cny_does_not(self, tmp_path):
        """Warn when USD has cache_pricing but CNY entry lacks it."""
        model_usd = _model(
            "api.anthropic.com",
            {"input_price": 3.0, "output_price": 15.0},
            currency="USD",
            cache_pricing={"cache_read_input_price": 0.30, "cache_creation_input_price": 3.75},
            metadata={"provider": "anthropic"},
        )
        model_cny = _model(
            "api.anthropic.com",
            {"input_price": 21.0, "output_price": 105.0},
            currency="CNY",
            metadata={"provider": "anthropic"},
        )
        result, warnings = self._merge_two_sources(model_usd, model_cny, tmp_path)

        completeness_warnings = [w for w in warnings if "cache_pricing" in w and "test-model" in w]
        assert len(completeness_warnings) == 1

    def test_no_completeness_warning_single_currency(self, tmp_path):
        """No completeness warning when model has only one currency."""
        source = {
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
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(source, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            _, warnings = merger.merge_all("2024-01-01")

        assert not any("batch_pricing" in w for w in warnings)
        assert not any("cache_pricing" in w for w in warnings)

    def test_no_completeness_warning_when_both_currencies_have_batch(self, tmp_path):
        """No completeness warning when both currencies have batch_pricing."""
        model_usd = _model(
            "api.deepseek.com",
            {"input_price": 0.27, "output_price": 1.10},
            currency="USD",
            batch_pricing={"input_price": 0.135, "output_price": 0.55},
            metadata={"provider": "deepseek"},
        )
        model_cny = _model(
            "api.deepseek.com",
            {"input_price": 2.0, "output_price": 8.0},
            currency="CNY",
            batch_pricing={"input_price": 1.0, "output_price": 4.0},
            metadata={"provider": "deepseek"},
        )
        _, warnings = self._merge_two_sources(model_usd, model_cny, tmp_path)

        assert not any("batch_pricing" in w for w in warnings)
