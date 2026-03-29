"""
History management for pricing data snapshots.

Creates daily snapshots and manages retention (365 days).
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.config import config

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Manages pricing data history snapshots.

    Features:
    - Daily snapshots of pricing.json
    - 365-day retention with automatic cleanup
    - Gap detection for missing days
    """

    def __init__(self):
        self.history_dir = config.history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, date_str: Optional[str] = None) -> Path:
        """
        Create a snapshot of current pricing.json.

        Args:
            date_str: Date for snapshot (defaults to today)

        Returns:
            Path to created snapshot
        """
        if date_str is None:
            date_str = date.today().isoformat()

        source_file = config.pricing_file
        if not source_file.exists():
            raise FileNotFoundError(f"Pricing file not found: {source_file}")

        snapshot_path = self.history_dir / f"{date_str}.json"

        # Copy with metadata
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Add snapshot metadata
        data["_snapshot"] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_file": str(source_file),
        }

        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created snapshot: {snapshot_path}")
        return snapshot_path

    def load_snapshot(self, date_str: str) -> Optional[Dict]:
        """Load a specific day's snapshot."""
        snapshot_path = self.history_dir / f"{date_str}.json"

        if not snapshot_path.exists():
            return None

        with open(snapshot_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_snapshots(self) -> List[Tuple[str, date]]:
        """
        List all available snapshots.

        Returns:
            List of (filename, date) tuples sorted by date descending
        """
        snapshots = []

        for snapshot_file in self.history_dir.glob("*.json"):
            try:
                # Extract date from filename (YYYY-MM-DD.json)
                date_str = snapshot_file.stem
                snapshot_date = date.fromisoformat(date_str)
                snapshots.append((snapshot_file.name, snapshot_date))
            except ValueError:
                logger.warning(f"Invalid snapshot filename: {snapshot_file.name}")
                continue

        # Sort by date descending
        snapshots.sort(key=lambda x: x[1], reverse=True)
        return snapshots

    def get_latest_snapshot(self) -> Optional[Tuple[str, Dict]]:
        """
        Get the most recent snapshot.

        Returns:
            Tuple of (date_str, data) or None if no snapshots exist
        """
        snapshots = self.list_snapshots()
        if not snapshots:
            return None

        latest_file, _ = snapshots[0]
        date_str = latest_file.replace(".json", "")
        data = self.load_snapshot(date_str)

        if data:
            return (date_str, data)
        return None

    def get_previous_snapshot(self, days_back: int = 1) -> Optional[Tuple[str, Dict]]:
        """
        Get a snapshot from N days ago.

        Args:
            days_back: Number of days to look back

        Returns:
            Tuple of (date_str, data) or None
        """
        target_date = date.today() - timedelta(days=days_back)
        date_str = target_date.isoformat()
        data = self.load_snapshot(date_str)

        if data:
            return (date_str, data)
        return None

    def detect_gaps(self, days: int = 30) -> List[str]:
        """
        Detect missing snapshots in the last N days.

        Args:
            days: Number of days to check

        Returns:
            List of missing date strings
        """
        existing = {snap[1] for snap in self.list_snapshots()}
        gaps = []

        for i in range(days):
            check_date = date.today() - timedelta(days=i)
            if check_date not in existing:
                gaps.append(check_date.isoformat())

        return gaps

    def cleanup_old_snapshots(self) -> int:
        """
        Remove snapshots older than retention period.

        Returns:
            Number of snapshots removed
        """
        retention_days = config.history_retention_days
        cutoff_date = date.today() - timedelta(days=retention_days)

        removed = 0
        for snapshot_file in self.history_dir.glob("*.json"):
            try:
                date_str = snapshot_file.stem
                snapshot_date = date.fromisoformat(date_str)

                if snapshot_date < cutoff_date:
                    snapshot_file.unlink()
                    logger.info(f"Removed old snapshot: {snapshot_file.name}")
                    removed += 1

            except ValueError:
                # Invalid filename, skip
                continue

        return removed

    def get_price_history(
        self,
        model_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get price history for a specific model.

        Args:
            model_id: Model ID to track
            days: Number of days of history

        Returns:
            List of {date, input_price, output_price} dicts
        """
        history = []

        for i in range(days):
            check_date = date.today() - timedelta(days=i)
            date_str = check_date.isoformat()
            snapshot = self.load_snapshot(date_str)

            if snapshot and "models" in snapshot:
                model_data = snapshot["models"].get(model_id)
                if model_data:
                    # v7.0: model_data IS the currency map
                    usd_pricing = model_data.get("USD", {})
                    if usd_pricing:
                        usd_text = usd_pricing.get("text", {})
                        history.append({
                            "date": date_str,
                            "in": usd_text.get("in"),
                            "out": usd_text.get("out"),
                        })

        return history

    def write_gaps_file(self) -> Optional[Path]:
        """
        Write gaps.json with missing snapshot dates.

        Returns:
            Path to gaps file or None if no gaps
        """
        gaps = self.detect_gaps(30)

        if not gaps:
            return None

        gaps_file = self.history_dir / "gaps.json"
        gaps_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "missing_dates": gaps,
            "total_gaps": len(gaps),
        }

        with open(gaps_file, "w", encoding="utf-8") as f:
            json.dump(gaps_data, f, indent=2)

        return gaps_file


def main() -> int:
    """
    Main entry point for history management.

    Returns:
        0 on success
    """
    manager = HistoryManager()

    # Create today's snapshot
    try:
        snapshot_path = manager.create_snapshot()
        print(f"✅ Created snapshot: {snapshot_path}")
    except FileNotFoundError:
        print("❌ No pricing.json to snapshot")
        return 1

    # Clean up old snapshots
    removed = manager.cleanup_old_snapshots()
    if removed:
        print(f"🧹 Removed {removed} old snapshots")

    # Check for gaps
    gaps = manager.detect_gaps(30)
    if gaps:
        print(f"⚠️  {len(gaps)} missing snapshots in last 30 days")
        for gap in gaps[:5]:
            print(f"   - {gap}")

    # Stats
    snapshots = manager.list_snapshots()
    print(f"\n📊 Total snapshots: {len(snapshots)}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
