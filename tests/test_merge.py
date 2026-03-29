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
        ep_data["cache"] = cache_pricing
    if batch_pricing is not None:
        ep_data["batch"] = batch_pricing
    if tiered_pricing is not None:
        ep_data["tiered"] = tiered_pricing
    return {"endpoints": {ep_key: ep_data}}


def _model(ep_key, pricing, *, currency="USD", base_url="", metadata=None,
           cache_pricing=None, batch_pricing=None, tiered_pricing=None):
    """Build a full model entry (endpoints + metadata) in source format."""
    entry = _ep(ep_key, pricing, currency=currency, base_url=base_url,
                cache_pricing=cache_pricing, batch_pricing=batch_pricing,
                tiered_pricing=tiered_pricing)
    entry["metadata"] = metadata or {}
    return entry


# URLs for first-party fetchers — source files must include fetched_url
# to pass the admission gate (proves data came from a real crawler).
_SOURCE_URLS = {
    "openai": "https://openai.com/api/pricing",
    "anthropic": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
    "google": "https://ai.google.dev/pricing",
    "deepseek": "https://api-docs.deepseek.com/quick_start/pricing",
    "zhipu": "https://open.bigmodel.cn/pricing",
    "aliyun": "https://dashscope.console.aliyun.com",
    "litellm": "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
    "openrouter": "https://openrouter.ai/api/v1/models",
}


def _source(models, *, source_name=None, fetched_url=None):
    """Wrap models dict into a source file format with fetched_url."""
    data = {"status": "success", "models": models}
    url = fetched_url or (source_name and _SOURCE_URLS.get(source_name))
    if url:
        data["fetched_url"] = url
    return data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_openai_data():
    """Sample OpenAI pricing data (source endpoint-keyed format)."""
    return _source({
        "gpt-4o": _model(
            "api.openai.com",
            {"input": 2.50, "output": 10.00},
            base_url="https://api.openai.com/v1",
            metadata={"provider": "openai"},
        ),
        "gpt-4o-mini": _model(
            "api.openai.com",
            {"input": 0.15, "output": 0.60},
            base_url="https://api.openai.com/v1",
            metadata={"provider": "openai"},
        ),
    }, source_name="openai")


@pytest.fixture
def sample_openrouter_data():
    """Sample OpenRouter pricing data (source endpoint-keyed format)."""
    return _source({
        "openai/gpt-4o": _model(
            "openrouter.ai",
            {"input": 2.50, "output": 10.00},
            base_url="https://openrouter.ai/api/v1",
            metadata={"provider": "openai"},
        ),
        "openai/gpt-4o-mini": _model(
            "openrouter.ai",
            {"input": 0.15, "output": 0.60},
            base_url="https://openrouter.ai/api/v1",
            metadata={"provider": "openai"},
        ),
        "anthropic/claude-3.5-sonnet": _model(
            "openrouter.ai",
            {"input": 3.00, "output": 15.00},
            base_url="https://openrouter.ai/api/v1",
            metadata={"provider": "anthropic"},
        ),
    }, source_name="openrouter")


@pytest.fixture
def sample_chinese_data():
    """Sample Chinese provider data (source endpoint-keyed, CNY)."""
    return _source({
            "qwen-max": _model(
                "dashscope.aliyuncs.com",
                {"input": 40.0, "output": 120.0},
                currency="CNY",
                base_url="https://dashscope.aliyuncs.com/api/v1",
                metadata={"provider": "aliyun"},
            ),
            "glm-4": _model(
                "open.bigmodel.cn",
                {"input": 100.0, "output": 100.0},
                currency="CNY",
                base_url="https://open.bigmodel.cn/api/paas/v4",
                metadata={"provider": "zhipu"},
            ),
        }, source_name="aliyun")


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

        assert result["version"] == "7.0"
        assert "models" in result
        assert len(result["models"]) == 2
        assert "gpt-4o" in result["models"]
        assert len(warnings) == 0

    def test_merge_output_is_v7_format(self, sample_openai_data, tmp_path):
        """Merged output uses v7.0 format: model IS the currency map, no pricing wrapper, no metadata."""
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        model = result["models"]["gpt-4o"]
        # v7.0: model IS the currency map — no pricing wrapper, no metadata
        assert "USD" in model
        assert "metadata" not in model
        assert "pricing" not in model
        usd = model["USD"]
        assert "text" in usd
        assert usd["text"]["input"] == pytest.approx(2.50)
        assert usd["text"]["output"] == pytest.approx(10.00)

    def test_merge_multiple_sources_priority(
        self,
        sample_openai_data,
        sample_openrouter_data,
        tmp_path
    ):
        """Original provider (priority 100) beats aggregator (priority 50)."""
        # openrouter claims a higher price for gpt-4o
        sample_openrouter_data["models"]["openai/gpt-4o"]["endpoints"]["openrouter.ai"]["pricing"]["input"] = 3.00

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
        assert result["models"]["gpt-4o"]["USD"]["text"]["input"] == pytest.approx(2.50)
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

        # Split into per-provider files so each gets correct priority (100)
        aliyun_data = {"status": "success", "fetched_url": "https://dashscope.console.aliyun.com", "models": {
            k: v for k, v in sample_chinese_data["models"].items()
            if k.startswith("qwen")
        }}
        zhipu_data = {"status": "success", "fetched_url": "https://open.bigmodel.cn/pricing", "models": {
            k: v for k, v in sample_chinese_data["models"].items()
            if k.startswith("glm")
        }}
        with open(sources_dir / "aliyun.json", "w") as f:
            json.dump(aliyun_data, f)
        with open(sources_dir / "zhipu.json", "w") as f:
            json.dump(zhipu_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert "gpt-4o" in result["models"]
        assert "qwen-max" in result["models"]
        assert "glm-4" in result["models"]

        # Chinese models have CNY pricing
        assert "CNY" in result["models"]["qwen-max"]
        assert result["models"]["qwen-max"]["CNY"]["text"]["input"] == pytest.approx(40.0)
        # USD-only models have no CNY entry
        assert "CNY" not in result["models"]["gpt-4o"]

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

        assert saved_data["version"] == "7.0"
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
                    {"input": 5.00, "output": 10.00},  # 100% higher
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
                    {"input": 2.51, "output": 10.00},  # 0.4% difference
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
        source = {"status": "success", "fetched_url": "https://openai.com/api/pricing", "models": {"gpt-test": model_data}}
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True, exist_ok=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(source, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")
        # Return the model dict (v7.0: model IS the currency map)
        return result["models"]["gpt-test"]

    def test_unit_field_removed(self, tmp_path):
        """unit field in source pricing does not appear in merged output."""
        model = _model(
            "api.openai.com",
            {"input": 2.50, "output": 10.00, "unit": "per_million_tokens"},
            metadata={"provider": "openai"},
        )
        pricing = self._merge_single(model, tmp_path)
        assert "unit" not in pricing["USD"]
        assert "unit" not in pricing["USD"].get("text", {})

    def test_null_output_price_set_to_zero(self, tmp_path):
        """output_price: null in source → 0.0 in merged output."""
        model = _model(
            "api.openai.com",
            {"input": 2.0, "output": None},
            metadata={"provider": "openai"},
        )
        pricing = self._merge_single(model, tmp_path)
        assert pricing["USD"]["text"]["output"] == 0.0

    def test_cache_creation_input_present(self, tmp_path):
        """creation_input cache pricing is preserved in merged output."""
        model = _model(
            "api.anthropic.com",
            {"input": 3.0, "output": 15.0},
            cache_pricing={
                "creation_input": 3.75,
                "read_input": 0.30,
            },
            metadata={"provider": "anthropic"},
        )
        pricing = self._merge_single(model, tmp_path)
        cp = pricing["USD"]["cache"]
        assert "creation_input" in cp
        assert cp["creation_input"] == pytest.approx(3.75)

    def test_cache_unit_field_removed(self, tmp_path):
        """unit field inside cache_pricing is removed from merged output."""
        model = _model(
            "api.anthropic.com",
            {"input": 3.0, "output": 15.0},
            cache_pricing={
                "read_input": 0.30,
                "unit": "per_million_tokens",
            },
            metadata={"provider": "anthropic"},
        )
        pricing = self._merge_single(model, tmp_path)
        assert "unit" not in pricing["USD"]["cache"]


class TestManualOverrides:
    """Tests for manual_overrides.json loading."""

    def test_manual_overrides_loaded_with_highest_priority(self, tmp_path):
        """manual_overrides source gets priority 200 — highest of all sources."""
        overrides = {
            "models": {
                "gemini-3-pro": {
                    "USD": {
                        "text": {"input": 2.0, "output": 0.0},
                    },
                },
            }
        }
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input": 2.50, "output": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(tmp_path / "manual_overrides.json", "w") as f:
            json.dump(overrides, f)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert "gemini-3-pro" in result["models"]
        assert "USD" in result["models"]["gemini-3-pro"]

    def test_manual_overrides_override_openrouter(self, tmp_path):
        """manual_overrides (priority 200) beats openrouter (priority 50) for same model."""
        overrides = {
            "models": {
                "gpt-4o": {
                    "USD": {
                        "text": {"input": 9.99, "output": 0.0},
                    },
                },
            }
        }
        openrouter_data = {
            "status": "success",
            "models": {
                "openai/gpt-4o": _model(
                    "openrouter.ai",
                    {"input": 2.50, "output": 10.0},
                    base_url="https://openrouter.ai/api/v1",
                    metadata={"provider": "openai"},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(tmp_path / "manual_overrides.json", "w") as f:
            json.dump(overrides, f)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "min_models_guard", {}), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert result["models"]["gpt-4o"]["USD"]["text"]["input"] == pytest.approx(9.99)


class TestMinModelsGuard:
    """Tests for min_models guard protecting against broken fetches."""

    def test_source_skipped_below_min_models(self, tmp_path):
        """Source with fewer models than min_models_guard threshold is skipped."""
        sparse_openrouter = {
            "status": "success",
            "models": {
                "openai/gpt-4o": _model(
                    "openrouter.ai",
                    {"input": 2.50, "output": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        openai_data = {
            "status": "success",
            "fetched_url": _SOURCE_URLS["openai"],
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input": 2.50, "output": 10.0},
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
        assert "USD" in result["models"]["gpt-4o"]

    def test_source_accepted_at_min_models(self, tmp_path):
        """Source with exactly min_models models is accepted."""
        or_models = {}
        google_models = {}
        for i in range(50):
            model_id = f"gemini-model-{i}"
            or_models[f"google/{model_id}"] = _model(
                "openrouter.ai",
                {"input": 1.0, "output": 2.0},
                metadata={"provider": "google"},
            )
            # First-party source so models pass admission gate
            google_models[model_id] = _model(
                "generativelanguage.googleapis.com",
                {"input": 1.0, "output": 2.0},
                metadata={"provider": "google"},
            )
        openrouter_data = {"status": "success", "models": or_models}
        google_data = {"status": "success", "fetched_url": _SOURCE_URLS["google"], "models": google_models}

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)
        with open(sources_dir / "google.json", "w") as f:
            json.dump(google_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert len(result["models"]) == 50


class TestFieldLevelEnrichment:
    """Only first-party sources (priority >= 100) may contribute cache/batch/tiered fields."""

    def test_batch_pricing_not_merged_from_litellm(self, tmp_path):
        """openai (priority 100) has no batch_pricing; litellm (70) cannot contribute it."""
        openai_data = {
            "status": "success",
            "fetched_url": "https://openai.com/api/pricing",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input": 2.50, "output": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        litellm_data = {
            "status": "success",
            "fetched_url": "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
            "models": {
                "gpt-4o": _model(
                    "litellm",
                    {"input": 2.50, "output": 10.0},
                    batch_pricing={"input": 1.25, "output": 5.0},
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

        usd = result["models"]["gpt-4o"]["USD"]
        assert usd["text"]["input"] == pytest.approx(2.50)
        # litellm's batch pricing must NOT appear — unverified source
        assert "batch" not in usd

    def test_tiered_pricing_not_merged_from_litellm(self, tmp_path):
        """litellm tiered_pricing must NOT be merged — unverified source."""
        openai_data = {
            "status": "success",
            "fetched_url": "https://openai.com/api/pricing",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input": 2.50, "output": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        litellm_data = {
            "status": "success",
            "fetched_url": "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
            "models": {
                "gpt-4o": _model(
                    "litellm",
                    {"input": 2.50, "output": 10.0},
                    tiered_pricing=[
                        {"tier_start": 0, "tier_end": 128000, "input": 2.5, "output": 10.0},
                        {"tier_start": 128000, "input": 5.0, "output": 10.0},
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

        usd = result["models"]["gpt-4o"]["USD"]
        # litellm's tiered pricing must NOT appear — unverified source
        assert "tiered" not in usd

    def test_winner_batch_pricing_not_overwritten(self, tmp_path):
        """When winner already has batch_pricing, lower source cannot overwrite it."""
        openai_data = {
            "status": "success",
            "fetched_url": "https://openai.com/api/pricing",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input": 2.50, "output": 10.0},
                    batch_pricing={"input": 1.25, "output": 5.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        litellm_data = {
            "status": "success",
            "fetched_url": "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
            "models": {
                "gpt-4o": _model(
                    "litellm",
                    {"input": 2.50, "output": 10.0},
                    batch_pricing={"input": 0.99, "output": 3.0},  # different
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

        # openai's batch wins (1.25), litellm's (0.99) is ignored
        usd = result["models"]["gpt-4o"]["USD"]
        assert usd["batch"]["input"] == pytest.approx(1.25)

    def test_batch_pricing_merged_from_second_first_party(self, tmp_path):
        """A second first-party source (priority 100) CAN fill missing batch pricing."""
        openai_data = {
            "status": "success",
            "fetched_url": "https://openai.com/api/pricing",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input": 2.50, "output": 10.0},
                    metadata={"provider": "openai"},
                ),
            },
        }
        # anthropic source has priority 100 and a fetched_url — first-party
        second_first_party_data = {
            "status": "success",
            "fetched_url": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
            "models": {
                "gpt-4o": _model(
                    "api.anthropic.com",
                    {"input": 2.50, "output": 10.0},
                    batch_pricing={"input": 1.25, "output": 5.0},
                ),
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "openai.json", "w") as f:
            json.dump(openai_data, f)
        with open(sources_dir / "anthropic.json", "w") as f:
            json.dump(second_first_party_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        usd = result["models"]["gpt-4o"]["USD"]
        # second first-party source (anthropic p100) CAN contribute missing batch
        assert "batch" in usd
        assert usd["batch"]["input"] == pytest.approx(1.25)


class TestDerivedPricing:
    """
    Merge-stage derived pricing for providers with documented ratio rules.
    Zhipu: cache read = 50% of input, batch = 50% (batch_supported_models whitelist).
    Sources: docs.bigmodel.cn/cn/guide/capabilities/cache.md
             docs.bigmodel.cn/cn/guide/tools/batch.md
    """

    def _merge_zhipu(self, model_id: str, input_price: float, output_price: float,
                     tmp_path, *, existing_cache=None, existing_batch=None):
        """Helper: merge a single Zhipu CNY model and return its CNY pricing entry."""
        model = _model(
            "open.bigmodel.cn",
            {"input": input_price, "output": output_price},
            currency="CNY",
            metadata={"provider": "zhipu", "family": "glm"},
            cache_pricing=existing_cache,
            batch_pricing=existing_batch,
        )
        source = {"status": "success", "fetched_url": _SOURCE_URLS["zhipu"], "models": {model_id: model}}
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True, exist_ok=True)
        with open(sources_dir / "zhipu.json", "w") as f:
            json.dump(source, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")
        return result["models"][model_id]["CNY"], warnings

    def test_paid_model_gets_cache_pricing(self, tmp_path):
        """Paid Zhipu model: cache_read_input_price = input * 0.5."""
        cny, _ = self._merge_zhipu("glm-4-plus", 5.0, 5.0, tmp_path)
        assert "cache" in cny
        assert cny["cache"]["read_input"] == pytest.approx(2.5)

    def test_free_model_no_cache_pricing(self, tmp_path):
        """Free model (input=0): no cache_pricing derived."""
        cny, _ = self._merge_zhipu("glm-4.7-flash", 0.0, 0.0, tmp_path)
        assert "cache" not in cny

    def test_batch_supported_model_gets_batch_pricing(self, tmp_path):
        """GLM-4-Plus is in batch whitelist — gets batch_pricing at 50%."""
        cny, _ = self._merge_zhipu("glm-4-plus", 5.0, 5.0, tmp_path)
        assert "batch" in cny
        assert cny["batch"]["input"] == pytest.approx(2.5)
        assert cny["batch"]["output"] == pytest.approx(2.5)

    def test_batch_unsupported_model_no_batch_pricing(self, tmp_path):
        """GLM-5-Turbo is not in batch whitelist — no batch_pricing."""
        cny, _ = self._merge_zhipu("glm-5-turbo", 5.0, 22.0, tmp_path)
        assert "batch" not in cny

    def test_existing_cache_not_overwritten(self, tmp_path):
        """Source-provided cache_pricing is not overwritten by derived value."""
        explicit = {"read_input": 1.0}
        cny, _ = self._merge_zhipu("glm-4-plus", 5.0, 5.0, tmp_path, existing_cache=explicit)
        assert cny["cache"]["read_input"] == pytest.approx(1.0)

    def test_existing_batch_not_overwritten(self, tmp_path):
        """Source-provided batch_pricing is not overwritten by derived value."""
        explicit = {"input": 1.0, "output": 1.0}
        cny, _ = self._merge_zhipu("glm-4-plus", 5.0, 5.0, tmp_path, existing_batch=explicit)
        assert cny["batch"]["input"] == pytest.approx(1.0)

    def test_non_zhipu_model_no_derived(self, tmp_path):
        """Provider with no rules (deepseek) gets no derived cache/batch."""
        model = _model(
            "api.deepseek.com",
            {"input": 0.27, "output": 1.10},
            currency="USD",
            metadata={"provider": "deepseek"},
        )
        source = {"status": "success", "fetched_url": _SOURCE_URLS["deepseek"], "models": {"deepseek-chat": model}}
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True, exist_ok=True)
        with open(sources_dir / "deepseek.json", "w") as f:
            json.dump(source, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")
        usd = result["models"]["deepseek-chat"]["USD"]
        assert "cache" not in usd
        assert "batch" not in usd

    def test_zhipu_usd_gets_derived_same_as_cny(self, tmp_path):
        """
        GLM model with both USD (openrouter) and CNY (zhipu) sources:
        derived pricing is applied to both currencies — no completeness warning.
        """
        zhipu_data = {
            "status": "success",
            "fetched_url": _SOURCE_URLS["zhipu"],
            "models": {
                "glm-4-plus": _model(
                    "open.bigmodel.cn",
                    {"input": 5.0, "output": 5.0},
                    currency="CNY",
                    metadata={"provider": "zhipu", "family": "glm"},
                ),
            },
        }
        openrouter_data = {
            "status": "success",
            "models": {
                "zhipu/glm-4-plus": _model(
                    "openrouter.ai",
                    {"input": 0.70, "output": 0.70},
                    currency="USD",
                    metadata={"provider": "zhipu"},
                ),
            },
        }
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True, exist_ok=True)
        with open(sources_dir / "zhipu.json", "w") as f:
            json.dump(zhipu_data, f)
        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "min_models_guard", {}), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        model = result["models"]["glm-4-plus"]
        # Both currencies get cache and batch derived
        assert "cache" in model["CNY"]
        assert "cache" in model["USD"]
        assert "batch" in model["CNY"]
        assert "batch" in model["USD"]
        # No completeness warnings
        completeness = [w for w in warnings if "cache" in w or "batch" in w]
        assert completeness == [], f"Unexpected completeness warnings: {completeness}"

    def test_zhipu_derived_pricing_inferred_from_model_id(self, tmp_path):
        """
        Regression: Zhipu derived pricing still applies after metadata removal (v6.0).
        Provider is now inferred from glm- prefix, not from metadata.provider.
        """
        model = _ep(
            "open.bigmodel.cn",
            {"input": 5.0, "output": 5.0},
            currency="CNY",
        )
        source = {"status": "success", "fetched_url": _SOURCE_URLS["zhipu"], "models": {"glm-4-plus": model}}
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True, exist_ok=True)
        with open(sources_dir / "zhipu.json", "w") as f:
            json.dump(source, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        cny = result["models"]["glm-4-plus"]["CNY"]
        # cache derived from infer_provider("glm-4-plus") == "zhipu"
        assert "cache" in cny
        assert cny["cache"]["read_input"] == pytest.approx(2.5)
        assert "batch" in cny
        assert cny["batch"]["input"] == pytest.approx(2.5)
        # v6.0: no metadata key in output
        assert "metadata" not in result["models"]["glm-4-plus"]


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
            {"input": 0.27, "output": 1.10},
            currency="USD",
            batch_pricing={"input": 0.135, "output": 0.55},
            metadata={"provider": "deepseek"},
        )
        model_cny = _model(
            "api.deepseek.com",
            {"input": 2.0, "output": 8.0},
            currency="CNY",
            metadata={"provider": "deepseek"},
        )
        result, warnings = self._merge_two_sources(model_usd, model_cny, tmp_path)

        completeness_warnings = [w for w in warnings if "batch" in w and "test-model" in w]
        assert len(completeness_warnings) == 1
        assert "CNY" in completeness_warnings[0]
        assert "USD" in completeness_warnings[0]

    def test_completeness_warning_when_usd_has_cache_cny_does_not(self, tmp_path):
        """Warn when USD has cache_pricing but CNY entry lacks it."""
        model_usd = _model(
            "api.anthropic.com",
            {"input": 3.0, "output": 15.0},
            currency="USD",
            cache_pricing={"read_input": 0.30, "creation_input": 3.75},
            metadata={"provider": "anthropic"},
        )
        model_cny = _model(
            "api.anthropic.com",
            {"input": 21.0, "output": 105.0},
            currency="CNY",
            metadata={"provider": "anthropic"},
        )
        result, warnings = self._merge_two_sources(model_usd, model_cny, tmp_path)

        completeness_warnings = [w for w in warnings if "cache" in w and "test-model" in w]
        assert len(completeness_warnings) == 1

    def test_no_completeness_warning_single_currency(self, tmp_path):
        """No completeness warning when model has only one currency."""
        source = {
            "status": "success",
            "models": {
                "gpt-4o": _model(
                    "api.openai.com",
                    {"input": 2.50, "output": 10.0},
                    batch_pricing={"input": 1.25, "output": 5.0},
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

        assert not any("batch" in w for w in warnings)
        assert not any("cache" in w for w in warnings)

    def test_no_completeness_warning_when_both_currencies_have_batch(self, tmp_path):
        """No completeness warning when both currencies have batch_pricing."""
        model_usd = _model(
            "api.deepseek.com",
            {"input": 0.27, "output": 1.10},
            currency="USD",
            batch_pricing={"input": 0.135, "output": 0.55},
            metadata={"provider": "deepseek"},
        )
        model_cny = _model(
            "api.deepseek.com",
            {"input": 2.0, "output": 8.0},
            currency="CNY",
            batch_pricing={"input": 1.0, "output": 4.0},
            metadata={"provider": "deepseek"},
        )
        _, warnings = self._merge_two_sources(model_usd, model_cny, tmp_path)

        assert not any("batch" in w for w in warnings)


class TestAnomalyFilter:
    """Tests for _filter_anomalous_prices() in merge pipeline."""

    def _merge_with_source(self, model_id, model_data, source_name, tmp_path):
        """Helper: merge a single model from a named source."""
        source = {"status": "success", "fetched_url": _SOURCE_URLS.get(source_name, ""), "models": {model_id: model_data}}
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True, exist_ok=True)
        with open(sources_dir / f"{source_name}.json", "w") as f:
            json.dump(source, f)
        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            return merger.merge_all("2024-01-01")

    def test_anomalous_price_rejected(self, tmp_path):
        """Model with $540K/MTok output is filtered out."""
        model = _model(
            "api.deepseek.com",
            {"input": 0.28, "output": 540000.0},
            metadata={"provider": "deepseek"},
        )
        result, _ = self._merge_with_source("deepseek-bad", model, "deepseek", tmp_path)
        assert "deepseek-bad" not in result["models"]

    def test_negative_price_rejected(self, tmp_path):
        """Model with negative price (OpenRouter sentinel) is filtered out."""
        model = _model(
            "api.deepseek.com",
            {"input": -1.0, "output": 2.0},
            metadata={"provider": "deepseek"},
        )
        result, _ = self._merge_with_source("deepseek-neg", model, "deepseek", tmp_path)
        assert "deepseek-neg" not in result["models"]

    def test_zero_price_passes_filter(self, tmp_path):
        """Free tier model ($0/$0) is not anomalous."""
        model = _model(
            "generativelanguage.googleapis.com",
            {"input": 0.0, "output": 0.0},
            metadata={"provider": "google"},
        )
        result, _ = self._merge_with_source("gemini-free", model, "google", tmp_path)
        assert "gemini-free" in result["models"]

    def test_threshold_boundary_passes(self, tmp_path):
        """Price exactly at threshold ($200.00) passes (strict >)."""
        model = _model(
            "api.openai.com",
            {"input": 200.0, "output": 200.0},
            metadata={"provider": "openai"},
        )
        result, _ = self._merge_with_source("gpt-expensive", model, "openai", tmp_path)
        assert "gpt-expensive" in result["models"]

    def test_image_uses_500_threshold(self, tmp_path):
        """Image output uses $500 threshold, not $200."""
        # $400 image output — below $500 threshold, should pass
        model_ok = _ep(
            "generativelanguage.googleapis.com",
            {"text": {"input": 1.0, "output": 2.0}, "image": {"output": 400.0}},
            currency="USD",
        )
        result, _ = self._merge_with_source("gemini-img-ok", model_ok, "google", tmp_path)
        assert "gemini-img-ok" in result["models"]

    def test_image_above_threshold_rejected(self, tmp_path):
        """Image output above $500 threshold is rejected."""
        model_bad = _ep(
            "generativelanguage.googleapis.com",
            {"text": {"input": 1.0, "output": 2.0}, "image": {"output": 600.0}},
            currency="USD",
        )
        result, _ = self._merge_with_source("gemini-img-bad", model_bad, "google", tmp_path)
        assert "gemini-img-bad" not in result["models"]

    def test_mixed_modality_anomaly_rejects_whole_model(self, tmp_path):
        """Normal text + anomalous image → whole model rejected."""
        model = _ep(
            "generativelanguage.googleapis.com",
            {"text": {"input": 1.0, "output": 2.0}, "image": {"output": 999.0}},
            currency="USD",
        )
        result, _ = self._merge_with_source("gemini-mixed", model, "google", tmp_path)
        assert "gemini-mixed" not in result["models"]


class TestAdmissionGate:
    """Tests for _apply_admission_gate() in merge pipeline."""

    def test_aggregator_only_rejected(self, tmp_path):
        """Model with only litellm source (priority 70) is excluded."""
        litellm_data = {
            "status": "success",
            "models": {
                "some-obscure-model": _model(
                    "litellm",
                    {"input": 1.0, "output": 2.0},
                    metadata={"provider": "unknown"},
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

        assert "some-obscure-model" not in result["models"]

    def test_first_party_passes(self, tmp_path):
        """Model with google source (priority 100) is included."""
        google_data = {
            "status": "success",
            "fetched_url": _SOURCE_URLS["google"],
            "models": {
                "gemini-2.5-pro": _model(
                    "generativelanguage.googleapis.com",
                    {"input": 1.25, "output": 10.0},
                    metadata={"provider": "google"},
                ),
            },
        }
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "google.json", "w") as f:
            json.dump(google_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert "gemini-2.5-pro" in result["models"]

    def test_manual_overrides_passes(self, tmp_path):
        """Model from manual_overrides (priority 200) is included."""
        overrides = {
            "models": {
                "deepseek-chat": {
                    "USD": {
                        "text": {"input": 0.28, "output": 0.42},
                    },
                },
            }
        }
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(tmp_path / "manual_overrides.json", "w") as f:
            json.dump(overrides, f)
        # Need at least one source file for sources_dir to exist
        with open(sources_dir / "dummy.json", "w") as f:
            json.dump({"status": "error"}, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, _ = merger.merge_all("2024-01-01")

        assert "deepseek-chat" in result["models"]

    def test_multi_aggregator_below_threshold_rejected(self, tmp_path):
        """litellm + openrouter both present but no first-party → rejected."""
        litellm_data = {
            "status": "success",
            "models": {
                "some-model": _model(
                    "litellm",
                    {"input": 1.0, "output": 2.0},
                ),
            },
        }
        openrouter_data = {
            "status": "success",
            "models": {
                "unknown/some-model": _model(
                    "openrouter.ai",
                    {"input": 1.0, "output": 2.0},
                ),
            },
        }
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "litellm.json", "w") as f:
            json.dump(litellm_data, f)
        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        assert "some-model" not in result["models"]

    def test_full_pipeline_integration(self, tmp_path):
        """End-to-end: anomalous model filtered, aggregator-only excluded, first-party kept."""
        # First-party model — should survive
        google_data = {
            "status": "success",
            "fetched_url": _SOURCE_URLS["google"],
            "models": {
                "gemini-2.5-flash": _model(
                    "generativelanguage.googleapis.com",
                    {"input": 0.15, "output": 0.60},
                ),
            },
        }
        # Aggregator-only model — should be excluded by gate
        litellm_data = {
            "status": "success",
            "models": {
                "random-model": _model(
                    "litellm",
                    {"input": 1.0, "output": 2.0},
                ),
            },
        }
        # Manual override with anomalous price — should be excluded by anomaly filter
        overrides = {
            "models": {
                "deepseek-bad": {
                    "USD": {
                        "text": {"input": 999999.0, "output": 0.0},
                    },
                },
            }
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)
        with open(sources_dir / "google.json", "w") as f:
            json.dump(google_data, f)
        with open(sources_dir / "litellm.json", "w") as f:
            json.dump(litellm_data, f)
        with open(tmp_path / "manual_overrides.json", "w") as f:
            json.dump(overrides, f)

        merger = PricingMerger()
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path), \
             patch.object(config, "repo_root", tmp_path), \
             patch.object(config, "min_models_guard", {}):
            result, _ = merger.merge_all("2024-01-01")

        # Only gemini-2.5-flash survives
        assert "gemini-2.5-flash" in result["models"]
        assert "random-model" not in result["models"]
        assert "deepseek-bad" not in result["models"]

        # Validation report was generated
        report_path = tmp_path / "validation_report.json"
        assert report_path.exists()
        with open(report_path) as f:
            report = json.load(f)
        assert report["summary"]["total_included"] == 1
        assert report["summary"]["excluded_anomalous"] >= 1
        assert report["summary"]["excluded_unverified"] >= 1
