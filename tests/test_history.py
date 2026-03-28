"""
Tests for history module.
"""
import json
import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.history import HistoryManager
from scripts.config import config


@pytest.fixture
def sample_pricing_data():
    """Sample pricing data for testing."""
    return {
        "schema_version": "1.0",
        "updated_at": "2024-01-15T00:00:00Z",
        "source": "test",
        "models": {
            "gpt-4o": {
                "pricing": {
                    "USD": {
                        "input_price": 2.50,
                        "output_price": 10.00,
                    }
                }
            },
            "claude-3.5-sonnet": {
                "pricing": {
                    "USD": {
                        "input_price": 3.00,
                        "output_price": 15.00,
                    }
                }
            },
        },
    }


@pytest.fixture
def history_manager(tmp_path):
    """Create history manager with temp directory."""
    manager = HistoryManager.__new__(HistoryManager)
    manager.history_dir = tmp_path / "history"
    manager.history_dir.mkdir(parents=True, exist_ok=True)
    return manager


class TestHistoryManager:
    """Tests for HistoryManager class."""

    def test_create_snapshot(self, history_manager, sample_pricing_data, tmp_path):
        """Test creating a snapshot."""
        # Create pricing file
        pricing_file = tmp_path / "pricing.json"
        with open(pricing_file, "w") as f:
            json.dump(sample_pricing_data, f)

        with patch.object(config, "pricing_file", pricing_file):
            snapshot_path = history_manager.create_snapshot("2024-01-15")

        assert snapshot_path.exists()
        assert snapshot_path.name == "2024-01-15.json"

        with open(snapshot_path) as f:
            data = json.load(f)

        assert "_snapshot" in data
        assert data["_snapshot"]["created_at"] is not None

    def test_create_snapshot_today(self, history_manager, sample_pricing_data, tmp_path):
        """Test creating snapshot with default date."""
        pricing_file = tmp_path / "pricing.json"
        with open(pricing_file, "w") as f:
            json.dump(sample_pricing_data, f)

        with patch.object(config, "pricing_file", pricing_file):
            snapshot_path = history_manager.create_snapshot()

        today_str = date.today().isoformat()
        assert snapshot_path.name == f"{today_str}.json"

    def test_load_snapshot(self, history_manager, sample_pricing_data):
        """Test loading a snapshot."""
        # Create snapshot file
        snapshot_path = history_manager.history_dir / "2024-01-15.json"
        with open(snapshot_path, "w") as f:
            json.dump(sample_pricing_data, f)

        data = history_manager.load_snapshot("2024-01-15")

        assert data is not None
        assert "models" in data
        assert "gpt-4o" in data["models"]

    def test_load_snapshot_not_found(self, history_manager):
        """Test loading non-existent snapshot."""
        data = history_manager.load_snapshot("2024-01-01")

        assert data is None

    def test_list_snapshots(self, history_manager, sample_pricing_data):
        """Test listing snapshots."""
        # Create multiple snapshots
        for i in range(3):
            snapshot_date = f"2024-01-{10+i:02d}"
            snapshot_path = history_manager.history_dir / f"{snapshot_date}.json"
            with open(snapshot_path, "w") as f:
                json.dump(sample_pricing_data, f)

        snapshots = history_manager.list_snapshots()

        assert len(snapshots) == 3
        # Should be sorted descending by date
        assert snapshots[0][0] == "2024-01-12.json"
        assert snapshots[2][0] == "2024-01-10.json"

    def test_list_snapshots_ignores_invalid(self, history_manager, sample_pricing_data):
        """Test that invalid filenames are ignored."""
        # Valid snapshot
        valid_path = history_manager.history_dir / "2024-01-15.json"
        with open(valid_path, "w") as f:
            json.dump(sample_pricing_data, f)

        # Invalid filenames
        invalid_path = history_manager.history_dir / "not-a-date.json"
        with open(invalid_path, "w") as f:
            json.dump(sample_pricing_data, f)

        snapshots = history_manager.list_snapshots()

        assert len(snapshots) == 1
        assert snapshots[0][0] == "2024-01-15.json"

    def test_get_latest_snapshot(self, history_manager, sample_pricing_data):
        """Test getting latest snapshot."""
        # Create snapshots
        for day in [10, 15, 20]:
            snapshot_path = history_manager.history_dir / f"2024-01-{day:02d}.json"
            with open(snapshot_path, "w") as f:
                json.dump(sample_pricing_data, f)

        result = history_manager.get_latest_snapshot()

        assert result is not None
        date_str, data = result
        assert date_str == "2024-01-20"

    def test_get_latest_snapshot_empty(self, history_manager):
        """Test getting latest snapshot when none exist."""
        result = history_manager.get_latest_snapshot()

        assert result is None

    def test_detect_gaps(self, history_manager, sample_pricing_data):
        """Test detecting missing snapshots."""
        # Create snapshot for today
        today = date.today()
        today_path = history_manager.history_dir / f"{today.isoformat()}.json"
        with open(today_path, "w") as f:
            json.dump(sample_pricing_data, f)

        # Create snapshot for 3 days ago
        three_days = today - timedelta(days=3)
        old_path = history_manager.history_dir / f"{three_days.isoformat()}.json"
        with open(old_path, "w") as f:
            json.dump(sample_pricing_data, f)

        gaps = history_manager.detect_gaps(days=7)

        # Should have gaps for yesterday, 2 days ago
        assert len(gaps) >= 1
        assert len(gaps) <= 5

    def test_detect_gaps_complete(self, history_manager, sample_pricing_data):
        """Test no gaps when all snapshots exist."""
        # Create snapshots for last 7 days
        today = date.today()
        for i in range(7):
            day = today - timedelta(days=i)
            snapshot_path = history_manager.history_dir / f"{day.isoformat()}.json"
            with open(snapshot_path, "w") as f:
                json.dump(sample_pricing_data, f)

        gaps = history_manager.detect_gaps(days=7)

        assert len(gaps) == 0

    def test_cleanup_old_snapshots(self, history_manager, sample_pricing_data):
        """Test removing old snapshots."""
        # Create old snapshot
        old_date = date.today() - timedelta(days=400)
        old_path = history_manager.history_dir / f"{old_date.isoformat()}.json"
        with open(old_path, "w") as f:
            json.dump(sample_pricing_data, f)

        # Create recent snapshot
        recent_path = history_manager.history_dir / f"{date.today().isoformat()}.json"
        with open(recent_path, "w") as f:
            json.dump(sample_pricing_data, f)

        removed = history_manager.cleanup_old_snapshots()

        assert removed == 1
        assert not old_path.exists()
        assert recent_path.exists()

    def test_get_price_history(self, history_manager, sample_pricing_data):
        """Test getting price history for a model."""
        # Create snapshots with varying prices
        for i in range(5):
            day = date.today() - timedelta(days=i)
            data = sample_pricing_data.copy()
            data["models"]["gpt-4o"]["pricing"]["USD"]["input_price"] = 2.50 + (i * 0.1)

            snapshot_path = history_manager.history_dir / f"{day.isoformat()}.json"
            with open(snapshot_path, "w") as f:
                json.dump(data, f)

        history = history_manager.get_price_history("gpt-4o", days=5)

        assert len(history) == 5
        # Check prices are present
        for entry in history:
            assert "date" in entry
            assert "input_price" in entry

    def test_write_gaps_file(self, history_manager, sample_pricing_data):
        """Test writing gaps file."""
        # Don't create all snapshots to create gaps
        today_path = history_manager.history_dir / f"{date.today().isoformat()}.json"
        with open(today_path, "w") as f:
            json.dump(sample_pricing_data, f)

        gaps_path = history_manager.write_gaps_file()

        if gaps_path:  # Only if there are gaps
            assert gaps_path.exists()
            assert gaps_path.name == "gaps.json"

            with open(gaps_path) as f:
                gaps_data = json.load(f)

            assert "missing_dates" in gaps_data
            assert "total_gaps" in gaps_data
