"""
RSS feed generator for pricing updates.

Generates RSS 2.0 feeds for:
- All pricing updates
- Model-specific price changes
- Daily summaries
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from scripts.config import config, infer_provider

logger = logging.getLogger(__name__)


class RSSGenerator:
    """
    Generates RSS feeds for pricing data updates.

    Feeds:
    - pricing-updates.xml - All price changes
    - daily-summary.xml - Daily update summaries
    """

    def __init__(self):
        self.output_dir = config.repo_root
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://pricing.burncloud.com"

    def generate_price_change_feed(
        self,
        changes: List[Dict],
        output_file: str = "pricing-updates.xml"
    ) -> Path:
        """
        Generate RSS feed for price changes.

        Args:
            changes: List of price change dicts with keys:
                - model_id: Model identifier
                - old_price: Previous price dict
                - new_price: New price dict
                - change_percent: Percentage change
                - currency: Currency code
            output_file: Output filename

        Returns:
            Path to generated feed
        """
        rss = self._create_rss_root(
            title="BurnCloud LLM Pricing Updates",
            description="Latest pricing changes for LLM APIs",
            link=f"{self.base_url}/pricing-updates.xml",
        )

        channel = rss.find("channel")

        # Add items for each change
        for change in changes[:50]:  # Limit to 50 items
            item = self._create_change_item(change)
            channel.append(item)

        return self._save_feed(rss, output_file)

    def generate_daily_summary_feed(
        self,
        summary: Dict,
        output_file: str = "daily-summary.xml"
    ) -> Path:
        """
        Generate RSS feed for daily summaries.

        Args:
            summary: Daily summary dict with:
                - date: ISO date string
                - total_models: Total models tracked
                - models_updated: Number of models updated
                - new_models: List of new model IDs
                - price_changes: Number of price changes
            output_file: Output filename

        Returns:
            Path to generated feed
        """
        rss = self._create_rss_root(
            title="BurnCloud Daily Pricing Summary",
            description="Daily summary of LLM pricing data",
            link=f"{self.base_url}/daily-summary.xml",
        )

        channel = rss.find("channel")

        # Create summary item
        item = Element("item")
        date_str = summary.get("date", datetime.now(timezone.utc).date().isoformat())

        SubElement(item, "title").text = f"Pricing Update - {date_str}"
        SubElement(item, "link").text = f"{self.base_url}/pricing.json"
        SubElement(item, "pubDate").text = self._format_rfc822(date_str)

        # Build description
        desc_parts = [
            f"Total models: {summary.get('total_models', 0)}",
            f"Models updated: {summary.get('models_updated', 0)}",
            f"Price changes: {summary.get('price_changes', 0)}",
        ]

        if summary.get("new_models"):
            desc_parts.append(f"New models: {', '.join(summary['new_models'][:5])}")
            if len(summary['new_models']) > 5:
                desc_parts.append(f"... and {len(summary['new_models']) - 5} more")

        SubElement(item, "description").text = " | ".join(desc_parts)

        # Add JSON-LD for machine-readable data
        SubElement(item, "{http://search.yahoo.com/mrss/}content").attrib = {
            "url": f"{self.base_url}/pricing.json",
            "type": "application/json",
        }

        channel.append(item)

        return self._save_feed(rss, output_file)

    def generate_model_feed(
        self,
        model_id: str,
        history: List[Dict],
        output_file: Optional[str] = None
    ) -> Path:
        """
        Generate RSS feed for a specific model's price history.

        Args:
            model_id: Model identifier
            history: List of historical price points
            output_file: Output filename (defaults to models/{model_id}.xml)

        Returns:
            Path to generated feed
        """
        if output_file is None:
            safe_id = model_id.replace("/", "-").replace(".", "-")
            output_file = f"models/{safe_id}.xml"

        rss = self._create_rss_root(
            title=f"BurnCloud - {model_id} Pricing History",
            description=f"Price changes for {model_id}",
            link=f"{self.base_url}/{output_file}",
        )

        channel = rss.find("channel")

        for entry in history[:20]:  # Last 20 entries
            item = Element("item")

            date_str = entry.get("date", "")
            SubElement(item, "title").text = f"{model_id} - {date_str}"
            SubElement(item, "link").text = f"{self.base_url}/history/{date_str}.json"
            SubElement(item, "pubDate").text = self._format_rfc822(date_str)

            # Price info
            input_price = entry.get("input", "N/A")
            output_price = entry.get("output", "N/A")
            SubElement(item, "description").text = (
                f"Input: ${input_price}/M tokens, Output: ${output_price}/M tokens"
            )

            channel.append(item)

        return self._save_feed(rss, output_file)

    def _create_rss_root(
        self,
        title: str,
        description: str,
        link: str
    ) -> Element:
        """Create RSS 2.0 root element with channel."""
        rss = Element("rss")
        rss.attrib["version"] = "2.0"
        rss.attrib["xmlns:atom"] = "http://www.w3.org/2005/Atom"
        rss.attrib["xmlns:content"] = "http://purl.org/rss/1.0/modules/content/"

        channel = SubElement(rss, "channel")

        SubElement(channel, "title").text = title
        SubElement(channel, "description").text = description
        SubElement(channel, "link").text = link
        SubElement(channel, "language").text = "en-us"
        SubElement(channel, "lastBuildDate").text = datetime.now(
            timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Self-link
        atom_link = SubElement(channel, "atom:link")
        atom_link.attrib = {
            "href": link,
            "rel": "self",
            "type": "application/rss+xml",
        }

        return rss

    def _create_change_item(self, change: Dict) -> Element:
        """Create RSS item for a price change."""
        item = Element("item")

        model_id = change.get("model_id", "unknown")
        SubElement(item, "title").text = f"{model_id} Price Update"
        SubElement(item, "link").text = f"{self.base_url}/pricing.json"
        SubElement(item, "pubDate").text = datetime.now(
            timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Build description
        old = change.get("old_price", {})
        new = change.get("new_price", {})
        pct = change.get("change_percent", 0)
        currency = change.get("currency", "USD")

        direction = "increased" if pct > 0 else "decreased"
        abs_pct = abs(pct)

        # v5.0: prices live under "text"; fall back to flat for old data
        old_text = old.get("text", old)
        new_text = new.get("text", new)
        desc = (
            f"{model_id} pricing {direction} by {abs_pct:.1f}%. "
            f"Old: ${old_text.get('input_price', 'N/A')}/${old_text.get('output_price', 'N/A')} "
            f"New: ${new_text.get('input_price', 'N/A')}/${new_text.get('output_price', 'N/A')} "
            f"({currency}/M tokens)"
        )

        SubElement(item, "description").text = desc

        # Categories
        SubElement(item, "category").text = "pricing"
        SubElement(item, "category").text = infer_provider(model_id)

        return item

    def _format_rfc822(self, date_str: str) -> str:
        """Format ISO date string as RFC 822 for RSS."""
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
        except (ValueError, TypeError):
            return date_str

    def _save_feed(self, rss: Element, filename: str) -> Path:
        """Save RSS feed to file."""
        output_path = self.output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Pretty print
        xml_str = tostring(rss, encoding="unicode")
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

        # Remove extra blank lines
        lines = [line for line in pretty_xml.split("\n") if line.strip()]

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Generated RSS feed: {output_path}")
        return output_path


def main() -> int:
    """
    Main entry point for RSS generation.

    Returns:
        0 on success
    """
    generator = RSSGenerator()

    # Check for pricing file
    if not config.pricing_file.exists():
        print("❌ No pricing.json found. Run fetch and merge first.")
        return 1

    # Load current pricing
    with open(config.pricing_file, "r", encoding="utf-8") as f:
        current_data = json.load(f)

    # Load previous pricing for comparison
    from scripts.history import HistoryManager
    history = HistoryManager()

    latest_snapshot = history.get_latest_snapshot()

    changes = []
    if latest_snapshot:
        prev_data = latest_snapshot[1]

        for model_id, model_data in current_data.get("models", {}).items():
            prev_model = prev_data.get("models", {}).get(model_id)

            if prev_model:
                # Compare prices
                curr_pricing = model_data.get("USD", {})
                prev_pricing = prev_model.get("USD", {})

                curr_input = curr_pricing.get("text", {}).get("input")
                prev_input = prev_pricing.get("text", {}).get("input")

                if curr_input and prev_input and curr_input != prev_input:
                    pct = ((curr_input - prev_input) / prev_input) * 100
                    changes.append({
                        "model_id": model_id,
                        "old_price": prev_pricing,
                        "new_price": curr_pricing,
                        "change_percent": pct,
                        "currency": "USD",
                    })

    # Generate feeds
    if changes:
        generator.generate_price_change_feed(changes)
        print(f"✅ Generated pricing-updates.xml ({len(changes)} changes)")
    else:
        print("ℹ️  No price changes detected")

    # Generate daily summary
    summary = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "total_models": len(current_data.get("models", {})),
        "models_updated": len(current_data.get("models", {})),
        "price_changes": len(changes),
        "new_models": [],
    }

    # Detect new models
    if latest_snapshot:
        prev_models = set(latest_snapshot[1].get("models", {}).keys())
        curr_models = set(current_data.get("models", {}).keys())
        summary["new_models"] = list(curr_models - prev_models)

    generator.generate_daily_summary_feed(summary)
    print(f"✅ Generated daily-summary.xml")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
