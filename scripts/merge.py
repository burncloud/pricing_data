"""
Merge pricing data from multiple sources into pricing.json.

Output format: v3.0 — currency-keyed pricing per model.
  pricing.json → model → pricing → { "USD": {...}, "CNY": {...} }

Priority order (higher = more authoritative):
1. Original providers (OpenAI, Anthropic, etc.) - priority 100
2. Chinese providers (Zhipu, Aliyun, etc.) - priority 100
3. Aggregators (OpenRouter) - priority 50
4. Manual entries - priority 10

Quality checks:
- Price drift: warn when same currency has >1% price difference across sources
- Completeness: warn when one currency has batch/cache pricing but another doesn't
"""
import copy
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.config import config

logger = logging.getLogger(__name__)


class PricingMerger:
    """
    Merges pricing data from multiple sources with priority resolution.
    """

    def __init__(self):
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema for validation."""
        schema_path = config.schema_file
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def merge_all(self, date_str: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Merge all source files into pricing.json.

        Args:
            date_str: Date string (YYYY-MM-DD) for sources directory

        Returns:
            Tuple of (merged_data, list_of_warnings)
        """
        sources_dir = config.get_today_sources_dir(date_str)
        warnings = []

        if not sources_dir.exists():
            raise FileNotFoundError(f"Sources directory not found: {sources_dir}")

        # Collect all source data
        all_sources = self._collect_sources(sources_dir)

        if not all_sources:
            raise ValueError("No source data found")

        # Merge with priority resolution → currency-keyed output
        merged_models = self._merge_with_priority(all_sources, warnings)

        output = {
            "version": "3.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "burncloud-official",
            "models": merged_models,
        }

        # Validate against schema
        self._validate(output)

        return output, warnings

    def _collect_sources(self, sources_dir: Path) -> List[Dict[str, Any]]:
        """Collect all source JSON files, including manual overrides."""
        sources = []

        # Load manual overrides first (highest priority, priority=200)
        manual_override_path = config.data_dir / "sources" / "manual_overrides.json"
        if manual_override_path.exists():
            try:
                with open(manual_override_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("models"):
                    sources.append({
                        "name": "manual_overrides",
                        "data": {**data, "status": "success"},
                    })
                    logger.info(f"Loaded manual overrides: {len(data['models'])} models")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load manual overrides: {e}")

        for source_file in sources_dir.glob("*.json"):
            try:
                with open(source_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if data.get("status") == "success" and data.get("models"):
                    model_count = len(data["models"])
                    min_models = config.min_models_guard.get(source_file.stem, 0)
                    if min_models > 0 and model_count < min_models:
                        logger.warning(
                            f"Skipping {source_file.name}: only {model_count} models "
                            f"(min expected: {min_models}, likely broken fetch)"
                        )
                        continue

                    sources.append({
                        "name": source_file.stem,
                        "data": data,
                    })
                    logger.info(f"Loaded source: {source_file.name} ({model_count} models)")

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load {source_file}: {e}")

        return sources

    def _merge_with_priority(
        self,
        sources: List[Dict[str, Any]],
        warnings: List[str]
    ) -> Dict[str, Any]:
        """
        Merge models from all sources into currency-keyed pricing (v3.0).

        For each model:
        - Group all endpoint entries by currency
        - Highest-priority source wins base pricing per currency
        - Lower-priority sources contribute missing batch_pricing / cache_pricing
        - Warn on price drift within the same currency
        - Warn on completeness gaps across currencies (batch/cache present in one
          currency but absent in another)
        """
        merged = {}

        # model_id → { currency → [(source_name, ep_data, priority), ...] }
        model_currency_sources: Dict[str, Dict[str, List[Tuple[str, Dict, int]]]] = {}
        # model_id → [(source_name, metadata, priority), ...]
        model_metadata: Dict[str, List[Tuple[str, Dict, int]]] = {}

        for source in sources:
            source_name = source["name"]
            priority = config.get_source_priority(source_name)

            for model_id, model_data in source["data"]["models"].items():
                normalized_id = self._normalize_model_id(model_id, source_name)

                if normalized_id not in model_currency_sources:
                    model_currency_sources[normalized_id] = {}
                    model_metadata[normalized_id] = []

                if model_data.get("metadata"):
                    model_metadata[normalized_id].append(
                        (source_name, model_data["metadata"], priority)
                    )

                for ep_key, ep_data in model_data.get("endpoints", {}).items():
                    currency = ep_data.get("currency", "USD")
                    if currency not in model_currency_sources[normalized_id]:
                        model_currency_sources[normalized_id][currency] = []
                    model_currency_sources[normalized_id][currency].append(
                        (source_name, ep_data, priority)
                    )

        for model_id, currency_map in model_currency_sources.items():
            pricing: Dict[str, Any] = {}

            for currency, source_list in currency_map.items():
                source_list.sort(key=lambda x: x[2], reverse=True)

                winner_name, winner_ep, _ = source_list[0]
                entry: Dict[str, Any] = {
                    "input_price": winner_ep["pricing"]["input_price"],
                    "output_price": winner_ep["pricing"].get("output_price") or 0.0,
                }

                for field in ("cache_pricing", "batch_pricing", "tiered_pricing"):
                    if field in winner_ep:
                        entry[field] = copy.deepcopy(winner_ep[field])

                # Lower-priority sources contribute missing optional fields only
                for src_name, ep_data, _ in source_list[1:]:
                    for field in ("cache_pricing", "batch_pricing", "tiered_pricing"):
                        if field not in entry and field in ep_data:
                            entry[field] = copy.deepcopy(ep_data[field])
                            logger.debug(
                                f"Field-merged {model_id}[{currency}].{field} from {src_name}"
                            )

                    # Price drift check within same currency
                    base_input = entry["input_price"]
                    other_input = ep_data["pricing"].get("input_price")
                    if base_input and other_input:
                        drift = abs(base_input - other_input) / base_input
                        if drift > config.price_drift_warning_threshold:
                            warning = (
                                f"Price drift for {model_id} [{currency}]: "
                                f"{winner_name}={base_input} vs {src_name}={other_input} "
                                f"({drift * 100:.1f}%)"
                            )
                            warnings.append(warning)
                            logger.warning(warning)

                # Normalize cache_pricing field names
                if "cache_pricing" in entry:
                    cache = entry["cache_pricing"]
                    cache.pop("unit", None)
                    if "cache_write_input_price" in cache:
                        cache["cache_creation_input_price"] = cache.pop("cache_write_input_price")

                pricing[currency] = entry

            # Quality check: completeness across currencies
            self._check_pricing_completeness(model_id, pricing, warnings)

            # Metadata: highest priority source wins
            meta_list = model_metadata.get(model_id, [])
            if meta_list:
                meta_list.sort(key=lambda x: x[2], reverse=True)
                metadata = copy.deepcopy(meta_list[0][1])
                metadata["_merged_from"] = meta_list[0][0]
            else:
                metadata = {"_merged_from": "unknown"}

            merged[model_id] = {
                "pricing": pricing,
                "metadata": metadata,
            }

        return merged

    def _check_pricing_completeness(
        self,
        model_id: str,
        pricing: Dict[str, Any],
        warnings: List[str],
    ) -> None:
        """
        Quality check: if one currency has batch_pricing or cache_pricing but
        another currency for the same model doesn't, emit a warning.

        This flags gaps in data collection — e.g. USD has batch_pricing from
        LiteLLM but CNY batch pricing was never fetched.
        """
        currencies = list(pricing.keys())
        if len(currencies) < 2:
            return

        for field in ("batch_pricing", "cache_pricing"):
            currencies_with = [c for c in currencies if field in pricing[c]]
            currencies_without = [c for c in currencies if field not in pricing[c]]

            if currencies_with and currencies_without:
                warning = (
                    f"Incomplete pricing for {model_id}: "
                    f"{field} present in {currencies_with} but missing in {currencies_without}"
                )
                warnings.append(warning)
                logger.warning(warning)

    def _normalize_model_id(self, model_id: str, source: str) -> str:
        """
        Normalize model ID for merging.

        - OpenRouter: remove provider prefix (openai/gpt-4o -> gpt-4o)
        - All others: keep as-is
        """
        if source == "openrouter" and "/" in model_id:
            return model_id.split("/", 1)[1]
        return model_id

    def _validate(self, data: Dict[str, Any]) -> None:
        """Validate merged data against schema."""
        if not self.schema:
            logger.warning("No schema loaded, skipping validation")
            return

        try:
            import jsonschema
            jsonschema.validate(instance=data, schema=self.schema)
            logger.info("Schema validation passed")
        except ImportError:
            logger.warning("jsonschema not installed, skipping validation")
        except jsonschema.ValidationError as e:
            raise ValueError(f"Schema validation failed: {e.message}") from e

    def save(self, data: Dict[str, Any]) -> Path:
        """Save merged data to pricing.json."""
        output_path = config.pricing_file

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved merged pricing to {output_path}")
        return output_path


def main(date_str: Optional[str] = None) -> int:
    """
    Main entry point for merge script.

    Returns:
        0 on success (warnings are logged but non-blocking), 1 on error
    """
    if date_str is None:
        from datetime import date
        date_str = date.today().isoformat()

    try:
        merger = PricingMerger()
        data, warnings = merger.merge_all(date_str)

        output_path = merger.save(data)

        print(f"✅ Merged {len(data['models'])} models to {output_path}")

        if warnings:
            print(f"\n⚠️  {len(warnings)} warning(s):")
            for warning in warnings:
                print(f"   - {warning}")
            print("Continuing — warnings are informational, not blocking.")

        return 0

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1
    except ValueError as e:
        print(f"❌ Validation error: {e}")
        return 1
    except Exception as e:
        logger.exception("Unexpected error during merge")
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
