"""
Shared pytest fixtures for pricing_data tests.
"""
import json
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory structure."""
    project_dir = tmp_path / "pricing_data"
    project_dir.mkdir()

    # Create directories
    (project_dir / "sources").mkdir()
    (project_dir / "output").mkdir()
    (project_dir / "history").mkdir()

    return project_dir


@pytest.fixture
def mock_config(tmp_project):
    """Mock config with temp directories."""
    from scripts.config import Config

    with patch.object(Config, "__init__", lambda self: None):
        config = Config()
        config.project_root = tmp_project
        config.sources_dir = tmp_project / "sources"
        config.output_dir = tmp_project / "output"
        config.history_dir = tmp_project / "history"
        config.pricing_file = tmp_project / "output" / "pricing.json"
        config.schema_file = tmp_project / "schema.json"
        config.history_retention_days = 365
        config.price_drift_warning_threshold = 0.01

        yield config


@pytest.fixture
def sample_openai_response():
    """Sample OpenAI API response."""
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-4o",
                "object": "model",
                "created": 1700000000,
                "owned_by": "openai",
            },
            {
                "id": "gpt-4o-mini",
                "object": "model",
                "created": 1700000000,
                "owned_by": "openai",
            },
        ],
    }


@pytest.fixture
def sample_openrouter_response():
    """Sample OpenRouter API response."""
    return {
        "data": [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "context_length": 128000,
                "pricing": {
                    "prompt": "0.0000025",
                    "completion": "0.00001",
                },
                "architecture": {
                    "modality": "text+image",
                    "function_calling": True,
                },
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "context_length": 200000,
                "pricing": {
                    "prompt": "0.000003",
                    "completion": "0.000015",
                },
                "architecture": {
                    "modality": "text+image",
                    "function_calling": True,
                },
            },
        ],
    }


@pytest.fixture
def sample_pricing_json():
    """Sample merged pricing.json content."""
    return {
        "schema_version": "1.0",
        "updated_at": "2024-01-15T12:00:00Z",
        "source": "burncloud-official",
        "models": {
            "gpt-4o": {
                "pricing": {
                    "USD": {
                        "in": 2.50,
                        "out": 10.00,
                        "unit": "per_million_tokens",
                        "source": "openai",
                    }
                },
                "metadata": {
                    "provider": "openai",
                    "family": "gpt-4",
                    "context_window": 128000,
                    "supports_vision": True,
                    "supports_function_calling": True,
                },
            },
            "claude-3.5-sonnet": {
                "pricing": {
                    "USD": {
                        "in": 3.00,
                        "out": 15.00,
                        "unit": "per_million_tokens",
                        "source": "anthropic",
                    }
                },
                "metadata": {
                    "provider": "anthropic",
                    "family": "claude-3.5",
                    "context_window": 200000,
                    "supports_vision": True,
                    "supports_function_calling": True,
                },
            },
            "qwen-max": {
                "pricing": {
                    "CNY": {
                        "in": 0.04,
                        "out": 0.12,
                        "unit": "per_thousand_tokens",
                        "source": "aliyun",
                    }
                },
                "metadata": {
                    "provider": "aliyun",
                    "family": "qwen",
                },
            },
        },
    }


@pytest.fixture
def sample_sources():
    """Sample source files for testing merge."""
    return {
        "openai.json": {
            "status": "success",
            "fetched_at": "2024-01-15T10:00:00Z",
            "models_count": 2,
            "models": {
                "gpt-4o": {
                    "pricing": {
                        "USD": {
                            "in": 2.50,
                            "out": 10.00,
                            "unit": "per_million_tokens",
                        }
                    },
                    "metadata": {"provider": "openai"},
                },
                "gpt-4o-mini": {
                    "pricing": {
                        "USD": {
                            "in": 0.15,
                            "out": 0.60,
                            "unit": "per_million_tokens",
                        }
                    },
                    "metadata": {"provider": "openai"},
                },
            },
        },
        "openrouter.json": {
            "status": "success",
            "fetched_at": "2024-01-15T10:05:00Z",
            "models_count": 2,
            "models": {
                "openai/gpt-4o": {
                    "pricing": {
                        "USD": {
                            "in": 2.50,
                            "out": 10.00,
                            "unit": "per_million_tokens",
                        }
                    },
                    "metadata": {"provider": "openai"},
                },
                "anthropic/claude-3.5-sonnet": {
                    "pricing": {
                        "USD": {
                            "in": 3.00,
                            "out": 15.00,
                            "unit": "per_million_tokens",
                        }
                    },
                    "metadata": {"provider": "anthropic"},
                },
            },
        },
    }
