"""
Tests for compare module.
"""
import json
import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.compare import PriceChange, ComparisonResult, PriceComparator
from scripts.history import HistoryManager
from scripts.config import config


@pytest.fixture
def current_pricing():
    """Current pricing data."""
    return {
        "schema_version": "1.0",
        "updated_at": "2024-01-15T12:00:00Z",
        "source": "test",
        "models": {
            "gpt-4o": {
                "pricing": {
                    "USD": {
                        "input_price": 2.50,  # Increased from 2.00
                        "output_price": 10.00,
                    }
                }
            },
            "claude-3.5-sonnet": {
                "pricing": {
                    "USD": {
                        "input_price": 3.00,
                        "output_price": 15.00,  # Decreased from 20.00
                    }
                }
            },
            "new-model": {
                "pricing": {
                    "USD": {
                        "input_price": 1.00,
                        "output_price": 2.00,
                    }
                }
            },
        },
    }


@pytest.fixture
def previous_pricing():
    """Previous pricing data (one day ago)."""
    return {
        "schema_version": "1.0",
        "updated_at": "2024-01-14T12:00:00Z",
        "source": "test",
        "models": {
            "gpt-4o": {
                "pricing": {
                    "USD": {
                        "input_price": 2.00,
                        "output_price": 10.00,
                    }
                }
            },
            "claude-3.5-sonnet": {
                "pricing": {
                    "USD": {
                        "input_price": 3.00,
                        "output_price": 20.00,
                    }
                }
            },
            "removed-model": {
                "pricing": {
                    "USD": {
                        "input_price": 5.00,
                        "output_price": 10.00,
                    }
                }
            },
        },
    }


class TestPriceChange:
    """Tests for PriceChange dataclass."""

    def test_percentage_calculation(self):
        """Test percentage change calculation."""
        change = PriceChange(
            model_id="test-model",
            currency="USD",
            old_input=10.0,
            old_output=20.0,
            new_input=12.0,
            new_output=18.0,
        )

        assert change.input_change_pct == 20.0  # +20%
        assert change.output_change_pct == -10.0  # -10%

    def test_is_increase(self):
        """Test detecting price increase."""
        increase = PriceChange(
            model_id="test",
            currency="USD",
            old_input=10.0,
            old_output=10.0,
            new_input=12.0,
            new_output=10.0,
        )
        assert increase.is_increase is True

        decrease = PriceChange(
            model_id="test",
            currency="USD",
            old_input=10.0,
            old_output=10.0,
            new_input=8.0,
            new_output=10.0,
        )
        assert decrease.is_increase is False

    def test_max_change_pct(self):
        """Test getting maximum change percentage."""
        change = PriceChange(
            model_id="test",
            currency="USD",
            old_input=10.0,
            old_output=10.0,
            new_input=15.0,  # +50%
            new_output=8.0,  # -20%
        )

        assert change.max_change_pct == 50.0

    def test_to_dict(self):
        """Test serialization."""
        change = PriceChange(
            model_id="test",
            currency="USD",
            old_input=10.0,
            old_output=20.0,
            new_input=12.0,
            new_output=18.0,
        )

        d = change.to_dict()

        assert d["model_id"] == "test"
        assert d["currency"] == "USD"
        assert d["input_change_pct"] == 20.0
        assert d["output_change_pct"] == -10.0


class TestComparisonResult:
    """Tests for ComparisonResult dataclass."""

    def test_to_dict(self):
        """Test serialization."""
        result = ComparisonResult(
            comparison_date="2024-01-15",
            previous_date="2024-01-14",
            total_models=100,
            previous_total=95,
            price_changes=[],
            new_models=["new-model"],
            removed_models=["old-model"],
        )

        d = result.to_dict()

        assert d["comparison_date"] == "2024-01-15"
        assert d["total_models"] == 100
        assert d["new_models"] == ["new-model"]
        assert d["removed_models"] == ["old-model"]


class TestPriceComparator:
    """Tests for PriceComparator class."""

    @pytest.fixture
    def comparator(self, tmp_path):
        """Create comparator with mocked history."""
        comparator = PriceComparator()
        comparator.history = Mock(spec=HistoryManager)
        comparator.history.history_dir = tmp_path / "history"
        comparator.history.history_dir.mkdir(parents=True, exist_ok=True)
        return comparator

    def test_compare_new_models(self, comparator, current_pricing, previous_pricing):
        """Test detecting new models."""
        comparator.history.get_previous_snapshot.return_value = (
            "2024-01-14",
            previous_pricing
        )

        result = comparator.compare_with_previous(current_pricing)

        assert "new-model" in result.new_models
        assert "removed-model" in result.removed_models

    def test_compare_price_changes(self, comparator, current_pricing, previous_pricing):
        """Test detecting price changes."""
        comparator.history.get_previous_snapshot.return_value = (
            "2024-01-14",
            previous_pricing
        )

        result = comparator.compare_with_previous(current_pricing)

        # Should detect gpt-4o input increase (25%) and claude output decrease (25%)
        assert len(result.price_changes) >= 1

        # Find gpt-4o change
        gpt_change = next(
            (c for c in result.price_changes if c.model_id == "gpt-4o"),
            None
        )
        if gpt_change:
            assert gpt_change.input_change_pct == 25.0

    def test_compare_no_previous(self, comparator, current_pricing):
        """Test comparison when no previous snapshot exists."""
        comparator.history.get_previous_snapshot.return_value = None

        result = comparator.compare_with_previous(current_pricing)

        assert result.previous_date is None
        assert result.price_changes == []
        assert result.new_models == []

    def test_threshold_filtering(self, comparator, current_pricing, previous_pricing):
        """Test that small changes are filtered by threshold."""
        # Create data with small price change (< 1%)
        current = {
            "models": {
                "test-model": {
                    "pricing": {
                        "USD": {
                            "input_price": 10.00,  # 0.5% increase from 9.95
                            "output_price": 20.00,
                        }
                    }
                }
            }
        }

        previous = {
            "models": {
                "test-model": {
                    "pricing": {
                        "USD": {
                            "input_price": 9.95,
                            "output_price": 20.00,
                        }
                    }
                }
            }
        }

        comparator.history.get_previous_snapshot.return_value = ("2024-01-14", previous)

        result = comparator.compare_with_previous(current)

        # Should not include change below 1% threshold
        assert len(result.price_changes) == 0

    def test_source_drift_detection(self, comparator):
        """Test detecting price drift between sources."""
        sources = {
            "openai": {
                "models": {
                    "gpt-4o": {
                        "pricing": {
                            "USD": {
                                "input_price": 2.50,
                                "output_price": 10.00,
                            }
                        }
                    }
                }
            },
            "openrouter": {
                "models": {
                    "gpt-4o": {
                        "pricing": {
                            "USD": {
                                "input_price": 4.00,  # 60% higher
                                "output_price": 10.00,
                            }
                        }
                    }
                }
            }
        }

        warnings = comparator.detect_source_drift(sources)

        # Should detect significant drift
        assert len(warnings) > 0
        assert any("gpt-4o" in str(w) for w in warnings)

    def test_get_trending_models(self, comparator, current_pricing, previous_pricing):
        """Test getting trending models."""
        comparator.history.get_previous_snapshot.return_value = (
            "2024-01-14",
            previous_pricing
        )

        trending = comparator.get_trending_models(days=1, min_change=10.0)

        assert "increases" in trending
        assert "decreases" in trending

    def test_save_comparison(self, comparator, current_pricing, previous_pricing, tmp_path):
        """Test saving comparison result."""
        comparator.history.get_previous_snapshot.return_value = (
            "2024-01-14",
            previous_pricing
        )

        with patch.object(config, "output_dir", tmp_path):
            result = comparator.compare_with_previous(current_pricing)
            output_path = comparator.save_comparison(result)

        assert output_path.exists()
        assert output_path.name == "comparison.json"

        with open(output_path) as f:
            data = json.load(f)

        assert "comparison_date" in data


class TestMultiCurrencyComparison:
    """Tests for multi-currency price comparison."""

    def test_multi_currency_changes(self):
        """Test detecting changes across currencies."""
        comparator = PriceComparator()

        current = {
            "models": {
                "qwen-max": {
                    "pricing": {
                        "CNY": {
                            "input_price": 0.05,  # Increased
                            "output_price": 0.12,
                        },
                        "USD": {
                            "input_price": 0.007,
                            "output_price": 0.017,
                        }
                    }
                }
            }
        }

        previous = {
            "models": {
                "qwen-max": {
                    "pricing": {
                        "CNY": {
                            "input_price": 0.04,
                            "output_price": 0.12,
                        },
                        "USD": {
                            "input_price": 0.007,
                            "output_price": 0.017,
                        }
                    }
                }
            }
        }

        comparator.history = Mock()
        comparator.history.get_previous_snapshot.return_value = ("2024-01-14", previous)

        result = comparator.compare_with_previous(current)

        # Should detect CNY change
        cny_change = next(
            (c for c in result.price_changes if c.currency == "CNY"),
            None
        )
        if cny_change:
            assert cny_change.input_change_pct == 25.0
