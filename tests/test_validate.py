"""
Tests for validation report generation.
"""
import json
import pytest
from pathlib import Path

from scripts.validate import generate_validation_report


@pytest.fixture
def sample_data():
    """Sample data for report generation."""
    included = {
        "gemini-2.5-pro": {"USD": {"text": {"input": 1.25, "output": 10.0}}},
        "deepseek-chat": {"USD": {"text": {"input": 0.28, "output": 0.42}}},
    }
    anomalous = [
        {"model": "bad-model", "reason": "text.output $540000/MTok > $200 threshold", "value": 540000.0},
    ]
    unverified = [
        {"model": "obscure-model", "sources": ["litellm"], "max_priority": 70},
    ]
    source_map = {
        "gemini-2.5-pro": {
            "USD": [("google", {}, 100)],
        },
        "deepseek-chat": {
            "USD": [("manual_overrides", {}, 200)],
        },
    }
    return included, anomalous, unverified, source_map


class TestValidationReport:

    def test_report_structure(self, sample_data, tmp_path):
        """Report has correct top-level structure."""
        included, anomalous, unverified, source_map = sample_data

        path = generate_validation_report(
            included=included,
            anomalous=anomalous,
            unverified=unverified,
            source_map=source_map,
            output_dir=tmp_path,
        )

        assert path.exists()
        with open(path) as f:
            report = json.load(f)

        assert "generated_at" in report
        assert "summary" in report
        assert "included_models" in report
        assert "excluded_models" in report
        assert "anomalous" in report["excluded_models"]
        assert "unverified" in report["excluded_models"]

    def test_report_counts_match(self, sample_data, tmp_path):
        """Summary counts match detail lists."""
        included, anomalous, unverified, source_map = sample_data

        generate_validation_report(
            included=included,
            anomalous=anomalous,
            unverified=unverified,
            source_map=source_map,
            output_dir=tmp_path,
        )

        with open(tmp_path / "validation_report.json") as f:
            report = json.load(f)

        assert report["summary"]["total_included"] == len(included)
        assert report["summary"]["total_included"] == len(report["included_models"])
        assert report["summary"]["excluded_anomalous"] == 1
        assert report["summary"]["excluded_unverified"] == len(unverified)
        assert len(report["excluded_models"]["anomalous"]) == len(anomalous)
        assert len(report["excluded_models"]["unverified"]) == len(unverified)

    def test_included_models_have_source_info(self, sample_data, tmp_path):
        """Included models have sources and top_priority fields."""
        included, anomalous, unverified, source_map = sample_data

        generate_validation_report(
            included=included,
            anomalous=anomalous,
            unverified=unverified,
            source_map=source_map,
            output_dir=tmp_path,
        )

        with open(tmp_path / "validation_report.json") as f:
            report = json.load(f)

        gemini = report["included_models"]["gemini-2.5-pro"]
        assert gemini["sources"] == ["google"]
        assert gemini["top_priority"] == 100

        deepseek = report["included_models"]["deepseek-chat"]
        assert deepseek["sources"] == ["manual_overrides"]
        assert deepseek["top_priority"] == 200

    def test_empty_report(self, tmp_path):
        """All models pass: 0 anomalous, 0 unverified → valid report."""
        included = {"gpt-4o": {"USD": {"text": {"input": 2.5, "output": 10.0}}}}
        source_map = {"gpt-4o": {"USD": [("openai", {}, 100)]}}

        generate_validation_report(
            included=included,
            anomalous=[],
            unverified=[],
            source_map=source_map,
            output_dir=tmp_path,
        )

        with open(tmp_path / "validation_report.json") as f:
            report = json.load(f)

        assert report["summary"]["total_included"] == 1
        assert report["summary"]["excluded_anomalous"] == 0
        assert report["summary"]["excluded_unverified"] == 0
        assert report["excluded_models"]["anomalous"] == []
        assert report["excluded_models"]["unverified"] == []
