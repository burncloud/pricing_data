"""
Tests for merge module.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.merge import PricingMerger
from scripts.config import config


@pytest.fixture
def sample_openai_data():
    """Sample OpenAI pricing data."""
    return {
        "status": "success",
        "models": {
            "gpt-4o": {
                "pricing": {
                    "USD": {
                        "input_price": 2.50,
                        "output_price": 10.00,
                        "unit": "per_million_tokens",
                    }
                },
                "metadata": {"provider": "openai"},
            },
            "gpt-4o-mini": {
                "pricing": {
                    "USD": {
                        "input_price": 0.15,
                        "output_price": 0.60,
                        "unit": "per_million_tokens",
                    }
                },
                "metadata": {"provider": "openai"},
            },
        },
    }


@pytest.fixture
def sample_openrouter_data():
    """Sample OpenRouter pricing data."""
    return {
        "status": "success",
        "models": {
            "openai/gpt-4o": {
                "pricing": {
                    "USD": {
                        "input_price": 2.50,
                        "output_price": 10.00,
                        "unit": "per_million_tokens",
                    }
                },
                "metadata": {"provider": "openai"},
            },
            "openai/gpt-4o-mini": {
                "pricing": {
                    "USD": {
                        "input_price": 0.15,
                        "output_price": 0.60,
                        "unit": "per_million_tokens",
                    }
                },
                "metadata": {"provider": "openai"},
            },
            "anthropic/claude-3.5-sonnet": {
                "pricing": {
                    "USD": {
                        "input_price": 3.00,
                        "output_price": 15.00,
                        "unit": "per_million_tokens",
                    }
                },
                "metadata": {"provider": "anthropic"},
            },
        },
    }


@pytest.fixture
def sample_chinese_data():
    """Sample Chinese provider data."""
    return {
        "status": "success",
        "models": {
            "qwen-max": {
                "pricing": {
                    "CNY": {
                        "input_price": 0.04,
                        "output_price": 0.12,
                        "unit": "per_thousand_tokens",
                    }
                },
                "metadata": {"provider": "aliyun"},
            },
            "glm-4": {
                "pricing": {
                    "CNY": {
                        "input_price": 0.1,
                        "output_price": 0.1,
                        "unit": "per_thousand_tokens",
                    }
                },
                "metadata": {"provider": "zhipu"},
            },
        },
    }


class TestPricingMerger:
    """Tests for PricingMerger class."""

    def test_merge_single_source(self, sample_openai_data, tmp_path):
        """Test merging from a single source."""
        # Setup sources directory
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        merger = PricingMerger()

        # data_dir points to tmp_path so manual_overrides.json is not loaded
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        assert result["version"] == "1.0"
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
        # Modify OpenRouter to have different price
        sample_openrouter_data["models"]["openai/gpt-4o"]["pricing"]["USD"]["input_price"] = 3.00

        # Setup sources directory
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(sample_openrouter_data, f)

        merger = PricingMerger()

        # Disable min_models guard so test data (3 models) passes
        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "min_models_guard", {}), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        # OpenAI (priority 100) should override OpenRouter (priority 50)
        assert result["models"]["gpt-4o"]["pricing"]["USD"]["input_price"] == 2.50

        # Should have warning about price drift
        assert len(warnings) > 0
        assert "gpt-4o" in warnings[0] or "drift" in warnings[0].lower()

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

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir):
            result, warnings = merger.merge_all("2024-01-01")

        # Should have both Western and Chinese models
        assert "gpt-4o" in result["models"]
        assert "qwen-max" in result["models"]
        assert "glm-4" in result["models"]

        # Chinese models should have CNY pricing
        assert "CNY" in result["models"]["qwen-max"]["pricing"]

    def test_merge_no_sources_raises(self, tmp_path):
        """Test that merge raises when no sources exist (including no manual_overrides)."""
        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        merger = PricingMerger()

        # data_dir must point to tmp_path so manual_overrides.json is not found
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

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir):
            with patch.object(config, "pricing_file", output_dir / "pricing.json"):
                result, _ = merger.merge_all("2024-01-01")
                output_path = merger.save(result)

        assert output_path.exists()

        with open(output_path) as f:
            saved_data = json.load(f)

        assert saved_data["version"] == "1.0"
        assert "updated_at" in saved_data
        assert "models" in saved_data


class TestPriceConflictDetection:
    """Tests for price conflict detection."""

    def test_large_drift_warning(self, sample_openai_data, tmp_path):
        """Test warning for significant price drift."""
        # Create source with significantly different price
        openrouter_data = {
            "status": "success",
            "models": {
                "openai/gpt-4o": {
                    "pricing": {
                        "USD": {
                            "input_price": 5.00,  # 100% higher
                            "output_price": 10.00,
                            "unit": "per_million_tokens",
                        }
                    },
                    "metadata": {"provider": "openai"},
                },
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir), \
             patch.object(config, "min_models_guard", {}), \
             patch.object(config, "data_dir", tmp_path):
            result, warnings = merger.merge_all("2024-01-01")

        # Should have drift warning
        assert len(warnings) > 0
        assert any("gpt-4o" in w for w in warnings)

    def test_small_drift_no_warning(self, sample_openai_data, tmp_path):
        """Test no warning for small price differences."""
        openrouter_data = {
            "status": "success",
            "models": {
                "openai/gpt-4o": {
                    "pricing": {
                        "USD": {
                            "input_price": 2.51,  # 0.4% difference
                            "output_price": 10.00,
                            "unit": "per_million_tokens",
                        }
                    },
                    "metadata": {"provider": "openai"},
                },
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        with open(sources_dir / "openai.json", "w") as f:
            json.dump(sample_openai_data, f)

        with open(sources_dir / "openrouter.json", "w") as f:
            json.dump(openrouter_data, f)

        merger = PricingMerger()

        with patch.object(config, "get_today_sources_dir", return_value=sources_dir):
            result, warnings = merger.merge_all("2024-01-01")

        # Should NOT have drift warning (< 1% threshold)
        assert len(warnings) == 0


class TestNormalizeModelFormat:
    """Tests for _normalize_model_format post-processing."""

    def test_unit_field_removed(self):
        """unit field must not appear in output (not in burncloud CurrencyPricing)."""
        merger = PricingMerger()
        model = {
            "pricing": {
                "USD": {
                    "input_price": 2.50,
                    "output_price": 10.00,
                    "unit": "per_million_tokens",
                }
            },
            "metadata": {"provider": "openai"},
        }
        result = merger._normalize_model_format(model)
        assert "unit" not in result["pricing"]["USD"]

    def test_null_output_price_set_to_zero(self):
        """output_price: null → 0.0 (CurrencyPricing.output_price is i64, not Option)."""
        merger = PricingMerger()
        model = {
            "pricing": {
                "USD": {"input_price": 2.0, "output_price": None}
            }
        }
        result = merger._normalize_model_format(model)
        assert result["pricing"]["USD"]["output_price"] == 0.0

    def test_cache_pricing_moved_to_top_level(self):
        """cache_pricing nested inside pricing dict must be promoted to top-level."""
        merger = PricingMerger()
        model = {
            "pricing": {
                "USD": {
                    "input_price": 3.0,
                    "output_price": 15.0,
                    "cache_pricing": {
                        "USD": {"cache_read_input_price": 0.30, "cache_write_input_price": 3.75}
                    },
                }
            }
        }
        result = merger._normalize_model_format(model)
        # cache_pricing should be promoted to top-level
        assert "cache_pricing" in result
        assert "cache_pricing" not in result["pricing"]["USD"]

    def test_cache_write_input_price_renamed(self):
        """cache_write_input_price → cache_creation_input_price (burncloud field name)."""
        merger = PricingMerger()
        model = {
            "pricing": {"USD": {"input_price": 3.0, "output_price": 15.0}},
            "cache_pricing": {
                "USD": {
                    "cache_write_input_price": 3.75,
                    "cache_read_input_price": 0.30,
                }
            },
        }
        result = merger._normalize_model_format(model)
        cp = result["cache_pricing"]["USD"]
        assert "cache_creation_input_price" in cp
        assert "cache_write_input_price" not in cp
        assert cp["cache_creation_input_price"] == 3.75

    def test_cache_unit_field_removed(self):
        """unit field inside cache_pricing must be removed."""
        merger = PricingMerger()
        model = {
            "pricing": {"USD": {"input_price": 3.0, "output_price": 15.0}},
            "cache_pricing": {
                "USD": {
                    "cache_read_input_price": 0.30,
                    "unit": "per_million_tokens",
                }
            },
        }
        result = merger._normalize_model_format(model)
        assert "unit" not in result["cache_pricing"]["USD"]

    def test_original_model_not_mutated(self):
        """_normalize_model_format must not mutate its input."""
        merger = PricingMerger()
        model = {
            "pricing": {
                "USD": {"input_price": 2.0, "output_price": 10.0, "unit": "per_million_tokens"}
            }
        }
        original_has_unit = "unit" in model["pricing"]["USD"]
        merger._normalize_model_format(model)
        assert "unit" in model["pricing"]["USD"], "original dict should not be mutated"


class TestManualOverrides:
    """Tests for manual_overrides.json loading."""

    def test_manual_overrides_loaded_with_highest_priority(self, tmp_path):
        """manual_overrides source gets priority 200 — highest of all sources."""
        overrides = {
            "models": {
                "gemini-3-pro": {
                    "pricing": {"USD": {"input_price": 2.0, "output_price": 0.0}},
                    "metadata": {"provider": "google"},
                }
            }
        }
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": {
                    "pricing": {"USD": {"input_price": 2.50, "output_price": 10.0}},
                    "metadata": {"provider": "openai"},
                }
            },
        }

        sources_dir = tmp_path / "sources" / "2024-01-01"
        sources_dir.mkdir(parents=True)

        # manual_overrides goes in sources/ (not the date-scoped dir)
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
                "gpt-4o": {
                    "pricing": {"USD": {"input_price": 9.99, "output_price": 0.0}},
                    "metadata": {"provider": "openai"},
                }
            }
        }
        openrouter_data = {
            "status": "success",
            "models": {
                "openai/gpt-4o": {
                    "pricing": {"USD": {"input_price": 2.50, "output_price": 10.0}},
                    "metadata": {"provider": "openai"},
                }
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

        assert result["models"]["gpt-4o"]["pricing"]["USD"]["input_price"] == 9.99


class TestMinModelsGuard:
    """Tests for min_models guard protecting against broken fetches."""

    def test_source_skipped_below_min_models(self, tmp_path):
        """Source with fewer models than min_models_guard threshold is skipped."""
        # openrouter returns only 1 model but min is 50
        sparse_openrouter = {
            "status": "success",
            "models": {
                "openai/gpt-4o": {
                    "pricing": {"USD": {"input_price": 2.50, "output_price": 10.0}},
                    "metadata": {"provider": "openai"},
                }
            },
        }
        openai_data = {
            "status": "success",
            "models": {
                "gpt-4o": {
                    "pricing": {"USD": {"input_price": 2.50, "output_price": 10.0}},
                    "metadata": {"provider": "openai"},
                }
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
            models[f"provider/model-{i}"] = {
                "pricing": {"USD": {"input_price": 1.0, "output_price": 2.0}},
                "metadata": {"provider": "provider"},
            }
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
