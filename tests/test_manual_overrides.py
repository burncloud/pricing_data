"""
Tests for ManualOverridesFetcher.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.config import Config
from scripts.fetch.manual_overrides import ManualOverridesFetcher


@pytest.fixture
def mock_config(tmp_path):
    config = Mock(spec=Config)
    config.repo_root = tmp_path
    config.get_today_sources_dir = Mock(return_value=tmp_path)
    return config


@pytest.fixture
def valid_overrides():
    return {
        "_schema": "manual_overrides/5.0",
        "_note": "Human-verified prices.",
        "models": {
            "deepseek-chat": {
                "_verified_at": "2026-03-28",
                "_verified_source": "https://api-docs.deepseek.com/quick_start/pricing",
                "_notes": "Official pricing.",
                "USD": {
                    "text": {
                        "in": 0.28,
                        "out": 0.42,
                    },
                    "cache": {
                        "read": 0.028,
                    },
                },
            },
            "gemini-2.5-flash-preview-tts": {
                "_verified_at": "2026-03-28",
                "_verified_source": "https://ai.google.dev/pricing",
                "_notes": "TTS model.",
                "USD": {
                    "text": {
                        "in": 0.50,
                    },
                    "audio": {
                        "out": 10.00,
                    },
                },
            },
        },
    }


class TestManualOverridesFetcher:

    def test_fetch_success(self, mock_config, tmp_path, valid_overrides):
        """Loads models from a valid manual_overrides.json."""
        overrides_file = tmp_path / "manual_overrides.json"
        overrides_file.write_text(json.dumps(valid_overrides))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        assert result.success is True
        assert result.source == "manual_overrides"
        assert result.models_count == 2
        assert "deepseek-chat" in result.models
        assert "gemini-2.5-flash-preview-tts" in result.models

    def test_strips_annotation_fields(self, mock_config, tmp_path, valid_overrides):
        """_verified_at, _verified_source, _notes must not appear in output models."""
        overrides_file = tmp_path / "manual_overrides.json"
        overrides_file.write_text(json.dumps(valid_overrides))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        model = result.models["deepseek-chat"]
        assert "_verified_at" not in model
        assert "_verified_source" not in model
        assert "_notes" not in model

    def test_converts_to_endpoints_format(self, mock_config, tmp_path, valid_overrides):
        """v5.0 currency format is converted to endpoints format for merge pipeline."""
        overrides_file = tmp_path / "manual_overrides.json"
        overrides_file.write_text(json.dumps(valid_overrides))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        model = result.models["deepseek-chat"]
        ep = model["endpoints"]["manual_USD"]
        assert ep["currency"] == "USD"
        assert ep["pricing"]["text"]["in"] == 0.28
        assert ep["pricing"]["text"]["out"] == 0.42
        assert ep["cache"]["read"] == 0.028

    def test_tts_model_pricing(self, mock_config, tmp_path, valid_overrides):
        """TTS model with audio modality is correctly converted."""
        overrides_file = tmp_path / "manual_overrides.json"
        overrides_file.write_text(json.dumps(valid_overrides))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        model = result.models["gemini-2.5-flash-preview-tts"]
        ep = model["endpoints"]["manual_USD"]
        assert ep["pricing"]["text"]["in"] == 0.50
        assert ep["pricing"]["audio"]["out"] == 10.00

    def test_file_not_found_returns_empty_success(self, mock_config, tmp_path):
        """Missing file is not an error — returns success with 0 models."""
        # Don't create the file
        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        assert result.success is True
        assert result.models == {}
        assert result.models_count == 0
        assert result.error is None

    def test_invalid_json_returns_error(self, mock_config, tmp_path):
        """Malformed JSON file returns error result."""
        overrides_file = tmp_path / "manual_overrides.json"
        overrides_file.write_text("{not valid json}")

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        assert result.success is False
        assert result.error is not None
        assert "JSON" in result.error or "json" in result.error.lower()

    def test_skips_entry_without_currency(self, mock_config, tmp_path):
        """Model entry with no currency pricing dict is skipped."""
        data = {
            "models": {
                "some-model": {
                    "_verified_at": "2026-03-28",
                    "_notes": "no pricing here",
                }
            }
        }
        (tmp_path / "manual_overrides.json").write_text(json.dumps(data))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        assert result.success is True
        assert "some-model" not in result.models
        assert result.models_count == 0

    def test_skips_non_dict_entry(self, mock_config, tmp_path):
        """Non-dict model entry is skipped with a warning."""
        data = {
            "models": {
                "bad-model": "this should be a dict, not a string"
            }
        }
        (tmp_path / "manual_overrides.json").write_text(json.dumps(data))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        assert result.success is True
        assert "bad-model" not in result.models

    def test_empty_models_section(self, mock_config, tmp_path):
        """File with empty models dict returns success with 0 models."""
        data = {"_schema": "manual_overrides/5.0", "models": {}}
        (tmp_path / "manual_overrides.json").write_text(json.dumps(data))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        assert result.success is True
        assert result.models == {}

    def test_raw_response_is_full_file(self, mock_config, tmp_path, valid_overrides):
        """raw_response contains the full parsed JSON including metadata fields."""
        (tmp_path / "manual_overrides.json").write_text(json.dumps(valid_overrides))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        assert result.raw_response is not None
        assert "_schema" in result.raw_response
        assert "models" in result.raw_response

    def test_fetcher_name(self, mock_config):
        """Fetcher name is 'manual_overrides'."""
        fetcher = ManualOverridesFetcher(mock_config)
        assert fetcher.fetcher_config.name == "manual_overrides"

    def test_abstract_methods_raise(self, mock_config):
        """_make_request, _validate_response, _parse_models raise NotImplementedError."""
        fetcher = ManualOverridesFetcher(mock_config)
        with pytest.raises(NotImplementedError):
            fetcher._make_request()
        with pytest.raises(NotImplementedError):
            fetcher._validate_response(None)
        with pytest.raises(NotImplementedError):
            fetcher._parse_models(None)

    def test_save_and_reload(self, mock_config, tmp_path, valid_overrides):
        """Result can be saved and reloaded via BaseFetcher.save_result."""
        (tmp_path / "manual_overrides.json").write_text(json.dumps(valid_overrides))
        mock_config.get_today_sources_dir.return_value = tmp_path

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        saved_path = fetcher.save_result(result, "2026-03-28")
        assert saved_path.exists()
        assert saved_path.name == "manual_overrides.json"

        reloaded = fetcher.load_cached_result("2026-03-28")
        assert reloaded is not None
        assert reloaded.success is True
        assert "deepseek-chat" in reloaded.models

    def test_batch_pricing_preserved(self, mock_config, tmp_path):
        """batch pricing at currency level is converted to endpoint format."""
        data = {
            "models": {
                "test-model": {
                    "USD": {
                        "text": {"in": 1.0, "out": 2.0},
                        "batch": {"in": 0.5, "out": 1.0},
                    }
                }
            }
        }
        (tmp_path / "manual_overrides.json").write_text(json.dumps(data))

        fetcher = ManualOverridesFetcher(mock_config)
        result = fetcher.fetch()

        ep = result.models["test-model"]["endpoints"]["manual_USD"]
        assert ep["pricing"]["text"]["in"] == 1.0
        assert ep["batch"]["in"] == 0.5
