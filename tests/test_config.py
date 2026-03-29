"""
Tests for config module.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from scripts.config import Config, FetcherConfig, config, infer_provider


class TestFetcherConfig:
    """Tests for FetcherConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        fc = FetcherConfig(name="test", url="https://example.com")
        assert fc.name == "test"
        assert fc.url == "https://example.com"
        assert fc.timeout == 30.0
        assert fc.max_retries == 3
        assert fc.requires_auth is False
        assert fc.auth_env_var is None
        assert fc.api_key is None

    def test_api_key_from_env(self):
        """Test API key loading from environment."""
        with patch.dict(os.environ, {"TEST_API_KEY": "secret123"}):
            fc = FetcherConfig(
                name="test",
                url="https://example.com",
                requires_auth=True,
                auth_env_var="TEST_API_KEY"
            )
            assert fc.api_key == "secret123"

    def test_api_key_missing_env(self):
        """Test API key is None when env var not set."""
        fc = FetcherConfig(
            name="test",
            url="https://example.com",
            auth_env_var="NONEXISTENT_KEY"
        )
        assert fc.api_key is None


class TestConfig:
    """Tests for Config class."""

    def test_singleton(self):
        """Test that config module exports a single shared instance."""
        from scripts.config import config as config1
        from scripts.config import config as config2
        assert config1 is config2

    def test_project_root(self):
        """Test project root is set correctly."""
        assert config.repo_root.exists()
        assert config.repo_root.is_dir()

    def test_pricing_file_path(self):
        """Test pricing file path."""
        assert config.pricing_file.name == "pricing.json"
        assert config.pricing_file.parent.name == "pricing_data"

    def test_get_today_sources_dir(self):
        """Test sources directory for specific date."""
        from datetime import date

        today = date.today().isoformat()
        sources_dir = config.get_today_sources_dir(today)

        assert sources_dir.name == today
        assert sources_dir.parent.name == "sources"

    def test_get_source_priority(self):
        """Test source priority resolution."""
        # Original providers
        assert config.get_source_priority("openai") == 100
        assert config.get_source_priority("anthropic") == 100

        # Chinese providers
        assert config.get_source_priority("zhipu") == 100
        assert config.get_source_priority("aliyun") == 100

        # Aggregators
        assert config.get_source_priority("openrouter") == 50

        # Unknown sources default to 0
        assert config.get_source_priority("unknown") == 0

    def test_schema_file_path(self):
        """Test schema file path."""
        assert config.schema_file.name == "schema.json"
        assert config.schema_file.exists()

    def test_history_retention_days(self):
        """Test history retention setting."""
        assert config.history_retention_days == 365

    def test_price_drift_threshold(self):
        """Test price drift warning threshold."""
        assert 0 < config.price_drift_warning_threshold < 1


class TestInferProvider:
    """Tests for infer_provider() prefix-based inference."""

    def test_openai_gpt_prefix(self):
        assert infer_provider("gpt-4o") == "openai"

    def test_openai_o_series(self):
        assert infer_provider("o1-mini") == "openai"
        assert infer_provider("o3-mini") == "openai"
        assert infer_provider("o4-mini") == "openai"

    def test_anthropic_prefix(self):
        assert infer_provider("claude-opus-4-6") == "anthropic"
        assert infer_provider("claude-haiku-3-5") == "anthropic"

    def test_google_prefixes(self):
        assert infer_provider("gemini-2.0-flash") == "google"
        assert infer_provider("imagen-3") == "google"

    def test_zhipu_prefix(self):
        assert infer_provider("glm-4-plus") == "zhipu"
        assert infer_provider("glm-z1-flash") == "zhipu"

    def test_deepseek_prefix(self):
        assert infer_provider("deepseek-chat") == "deepseek"

    def test_slash_format(self):
        assert infer_provider("openai/gpt-4o") == "openai"

    def test_accounts_format(self):
        assert infer_provider("accounts/fireworks/models/llama") == "fireworks"

    def test_unknown_prefix(self):
        assert infer_provider("some-unknown-xyz-model") == "unknown"

    def test_empty_string(self):
        assert infer_provider("") == "unknown"


class TestSourcePriorities:
    """Tests for source priority configuration."""

    def test_original_providers_highest(self):
        """Original providers should have highest priority."""
        original_priority = config.get_source_priority("openai")
        aggregator_priority = config.get_source_priority("openrouter")

        assert original_priority > aggregator_priority

    def test_chinese_providers_high_priority(self):
        """Chinese providers should have same priority as original."""
        chinese_priority = config.get_source_priority("zhipu")
        original_priority = config.get_source_priority("openai")

        assert chinese_priority == original_priority
