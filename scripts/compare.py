"""
Price comparison and drift detection.

Compares pricing across sources and time to detect:
- Price inconsistencies between sources
- Significant price changes over time
- New or removed models
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.config import config
from scripts.history import HistoryManager

logger = logging.getLogger(__name__)


@dataclass
class PriceChange:
    """Represents a price change for a model."""
    model_id: str
    currency: str
    old_input: Optional[float]
    old_output: Optional[float]
    new_input: Optional[float]
    new_output: Optional[float]
    input_change_pct: Optional[float] = None
    output_change_pct: Optional[float] = None

    def __post_init__(self):
        # Calculate percentage changes
        if self.old_input and self.new_input:
            self.input_change_pct = (
                (self.new_input - self.old_input) / self.old_input
            ) * 100

        if self.old_output and self.new_output:
            self.output_change_pct = (
                (self.new_output - self.old_output) / self.old_output
            ) * 100

    @property
    def is_increase(self) -> bool:
        """Check if price increased."""
        return (self.input_change_pct or 0) > 0 or (self.output_change_pct or 0) > 0

    @property
    def max_change_pct(self) -> float:
        """Get maximum absolute change percentage."""
        return max(
            abs(self.input_change_pct or 0),
            abs(self.output_change_pct or 0)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "currency": self.currency,
            "old_input": self.old_input,
            "old_output": self.old_output,
            "new_input": self.new_input,
            "new_output": self.new_output,
            "input_change_pct": round(self.input_change_pct, 2) if self.input_change_pct else None,
            "output_change_pct": round(self.output_change_pct, 2) if self.output_change_pct else None,
        }


@dataclass
class ComparisonResult:
    """Result of price comparison."""
    comparison_date: str
    previous_date: Optional[str]
    price_changes: List[PriceChange] = field(default_factory=list)
    new_models: List[str] = field(default_factory=list)
    removed_models: List[str] = field(default_factory=list)
    total_models: int = 0
    previous_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "comparison_date": self.comparison_date,
            "previous_date": self.previous_date,
            "total_models": self.total_models,
            "previous_total": self.previous_total,
            "price_changes_count": len(self.price_changes),
            "price_changes": [c.to_dict() for c in self.price_changes],
            "new_models_count": len(self.new_models),
            "new_models": self.new_models,
            "removed_models_count": len(self.removed_models),
            "removed_models": self.removed_models,
        }


class PriceComparator:
    """
    Compares pricing data across time and sources.

    Features:
    - Day-over-day price comparison
    - Significant drift detection
    - New/removed model tracking
    - Source consistency checks
    """

    def __init__(self):
        self.history = HistoryManager()
        self.drift_threshold = config.price_drift_warning_threshold * 100  # Convert to %

    def compare_with_previous(
        self,
        current_data: Optional[Dict] = None,
        days_back: int = 1
    ) -> ComparisonResult:
        """
        Compare current pricing with a previous snapshot.

        Args:
            current_data: Current pricing data (loads from file if None)
            days_back: Number of days to look back for comparison

        Returns:
            ComparisonResult with changes
        """
        # Load current data
        if current_data is None:
            if not config.pricing_file.exists():
                raise FileNotFoundError("No pricing.json found")

            with open(config.pricing_file, "r", encoding="utf-8") as f:
                current_data = json.load(f)

        current_date = current_data.get("updated_at", date.today().isoformat())
        current_models = current_data.get("models", {})

        # Get previous snapshot
        previous = self.history.get_previous_snapshot(days_back)

        result = ComparisonResult(
            comparison_date=current_date,
            previous_date=previous[0] if previous else None,
            total_models=len(current_models),
            previous_total=0,
        )

        if not previous:
            logger.warning("No previous snapshot found for comparison")
            return result

        prev_date_str, prev_data = previous
        prev_models = prev_data.get("models", {})
        result.previous_total = len(prev_models)

        # Find new and removed models
        current_ids = set(current_models.keys())
        previous_ids = set(prev_models.keys())

        result.new_models = sorted(current_ids - previous_ids)
        result.removed_models = sorted(previous_ids - current_ids)

        # Compare prices for common models
        for model_id in current_ids & previous_ids:
            changes = self._compare_model_prices(
                model_id,
                current_models[model_id],
                prev_models[model_id]
            )
            result.price_changes.extend(changes)

        # Sort by significance
        result.price_changes.sort(
            key=lambda c: abs(c.max_change_pct),
            reverse=True
        )

        return result

    def _compare_model_prices(
        self,
        model_id: str,
        current: Dict,
        previous: Dict
    ) -> List[PriceChange]:
        """Compare prices for a single model across currencies."""
        changes = []

        curr_pricing = current.get("pricing", {})
        prev_pricing = previous.get("pricing", {})

        # Check each currency
        all_currencies = set(curr_pricing.keys()) | set(prev_pricing.keys())

        for currency in all_currencies:
            curr = curr_pricing.get(currency, {})
            prev = prev_pricing.get(currency, {})

            curr_input = curr.get("input_price")
            curr_output = curr.get("output_price")
            prev_input = prev.get("input_price")
            prev_output = prev.get("output_price")

            # Check if anything changed
            if curr_input != prev_input or curr_output != prev_output:
                change = PriceChange(
                    model_id=model_id,
                    currency=currency,
                    old_input=prev_input,
                    old_output=prev_output,
                    new_input=curr_input,
                    new_output=curr_output,
                )

                # Only include if change is significant
                if change.max_change_pct >= self.drift_threshold:
                    changes.append(change)

        return changes

    def detect_source_drift(
        self,
        sources_data: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Detect price drift between sources.

        Args:
            sources_data: Dict mapping source name to pricing data

        Returns:
            List of drift warnings
        """
        warnings = []

        # Collect all model prices by source
        model_prices: Dict[str, Dict[str, Tuple[str, float, float]]] = {}

        for source_name, data in sources_data.items():
            for model_id, model_data in data.get("models", {}).items():
                pricing = model_data.get("pricing", {}).get("USD", {})

                input_price = pricing.get("input_price")
                output_price = pricing.get("output_price")

                if input_price is not None:
                    if model_id not in model_prices:
                        model_prices[model_id] = {}

                    model_prices[model_id][source_name] = (
                        source_name,
                        input_price,
                        output_price or input_price
                    )

        # Compare sources for each model
        for model_id, sources in model_prices.items():
            if len(sources) < 2:
                continue

            # Find max drift
            source_names = list(sources.keys())
            for i, s1 in enumerate(source_names):
                for s2 in source_names[i+1:]:
                    _, inp1, out1 = sources[s1]
                    _, inp2, out2 = sources[s2]

                    inp_drift = abs(inp1 - inp2) / min(inp1, inp2) * 100
                    out_drift = abs(out1 - out2) / min(out1, out2) * 100

                    max_drift = max(inp_drift, out_drift)

                    if max_drift >= self.drift_threshold:
                        warnings.append({
                            "model_id": model_id,
                            "source_1": s1,
                            "source_2": s2,
                            "source_1_input": inp1,
                            "source_2_input": inp2,
                            "drift_pct": round(max_drift, 2),
                        })

        return warnings

    def get_trending_models(
        self,
        days: int = 7,
        min_change: float = 10.0
    ) -> Dict[str, List[PriceChange]]:
        """
        Get models with significant price trends.

        Args:
            days: Number of days to analyze
            min_change: Minimum percentage change to include

        Returns:
            Dict with 'increases' and 'decreases' lists
        """
        increases = []
        decreases = []

        # Compare today with N days ago
        result = self.compare_with_previous(days_back=days)

        for change in result.price_changes:
            if change.max_change_pct >= min_change:
                if change.is_increase:
                    increases.append(change)
                else:
                    decreases.append(change)

        return {
            "increases": sorted(increases, key=lambda c: c.max_change_pct, reverse=True),
            "decreases": sorted(decreases, key=lambda c: c.max_change_pct, reverse=True),
        }

    def save_comparison(self, result: ComparisonResult) -> Path:
        """Save comparison result to file."""
        output_path = config.repo_root / "comparison.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved comparison to {output_path}")
        return output_path


def main() -> int:
    """
    Main entry point for comparison script.

    Returns:
        0 on success
    """
    comparator = PriceComparator()

    try:
        # Compare with yesterday
        result = comparator.compare_with_previous()

        print(f"📊 Price Comparison Report")
        print(f"   Date: {result.comparison_date}")
        print(f"   Previous: {result.previous_date or 'N/A'}")
        print(f"   Total models: {result.total_models}")
        print()

        if result.new_models:
            print(f"🆕 New models ({len(result.new_models)}):")
            for model_id in result.new_models[:10]:
                print(f"   + {model_id}")
            if len(result.new_models) > 10:
                print(f"   ... and {len(result.new_models) - 10} more")
            print()

        if result.removed_models:
            print(f"🗑️  Removed models ({len(result.removed_models)}):")
            for model_id in result.removed_models[:10]:
                print(f"   - {model_id}")
            if len(result.removed_models) > 10:
                print(f"   ... and {len(result.removed_models) - 10} more")
            print()

        if result.price_changes:
            print(f"💰 Price changes ({len(result.price_changes)}):")
            for change in result.price_changes[:10]:
                direction = "📈" if change.is_increase else "📉"
                print(
                    f"   {direction} {change.model_id}: "
                    f"{change.input_change_pct:+.1f}%/{change.output_change_pct:+.1f}% "
                    f"({change.currency})"
                )
            if len(result.price_changes) > 10:
                print(f"   ... and {len(result.price_changes) - 10} more")
        else:
            print("✅ No significant price changes detected")

        # Save comparison
        comparator.save_comparison(result)

        # Return exit code based on findings
        if result.price_changes:
            return 2  # Changes found
        return 0

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1
    except Exception as e:
        logger.exception("Comparison failed")
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
