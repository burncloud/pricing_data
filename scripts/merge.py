"""
Merge pricing data from multiple sources into pricing.json.

Priority order (higher = more authoritative):
1. Original providers (OpenAI, Anthropic, etc.) - priority 100
2. Chinese providers (Zhipu, Aliyun, etc.) - priority 100
3. Aggregators (OpenRouter) - priority 50
4. Manual entries - priority 10
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

        # Merge with priority resolution
        merged_models = self._merge_with_priority(all_sources, warnings)

        # Build output structure (field names must match burncloud PricingConfig)
        output = {
            "version": "1.0",
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
                    # Guard: skip source if it has suspiciously few models
                    # (protects against OpenRouter returning empty/broken response)
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
        Merge models from all sources using priority resolution.

        When the same model appears in multiple sources:
        1. Use pricing from highest priority source
        2. Merge metadata (prefer non-null values)
        3. Log warnings for price conflicts >1%
        """
        merged = {}
        model_sources: Dict[str, List[Tuple[str, Dict[str, Any], int]]] = {}

        # Group models by normalized ID
        for source in sources:
            source_name = source["name"]
            priority = config.get_source_priority(source_name)

            for model_id, model_data in source["data"]["models"].items():
                normalized_id = self._normalize_model_id(model_id, source_name)

                if normalized_id not in model_sources:
                    model_sources[normalized_id] = []

                model_sources[normalized_id].append((source_name, model_data, priority))

        # Resolve each model
        for normalized_id, source_list in model_sources.items():
            # Sort by priority (descending)
            source_list.sort(key=lambda x: x[2], reverse=True)

            # Use highest priority source as base structure
            primary_source, primary_data, _ = source_list[0]
            merged[normalized_id] = self._normalize_model_format(primary_data)

            if len(source_list) > 1:
                # Currency-level merge for pricing / cache_pricing / batch_pricing:
                # For each currency key, keep the highest-priority source that has it.
                # This lets USD (z.ai / international) and CNY (bigmodel.cn / China)
                # coexist in the same model entry — neither overwrites the other.
                for field in ("pricing", "cache_pricing", "batch_pricing"):
                    self._merge_currencies(normalized_id, merged, source_list, field)

                # Field-level enrichment: tiered_pricing from lower source if winner lacks it
                for _src_name, src_data, _src_priority in source_list[1:]:
                    if "tiered_pricing" not in merged[normalized_id] and "tiered_pricing" in src_data:
                        merged[normalized_id]["tiered_pricing"] = copy.deepcopy(src_data["tiered_pricing"])
                        logger.debug(f"Field-enriched {normalized_id}.tiered_pricing from {_src_name}")

            # Check for price conflicts
            if len(source_list) > 1:
                self._check_price_conflicts(normalized_id, source_list, warnings)

            # Track source
            if "metadata" not in merged[normalized_id]:
                merged[normalized_id]["metadata"] = {}
            merged[normalized_id]["metadata"]["_merged_from"] = primary_source

        return merged

    def _merge_currencies(
        self,
        model_id: str,
        merged: Dict[str, Any],
        source_list: List[Tuple[str, Dict[str, Any], int]],
        field: str,
    ) -> None:
        """
        Merge a pricing field (pricing / cache_pricing / batch_pricing) across
        sources at currency granularity.

        Rule: for each currency key (USD, CNY, …), keep whichever source has the
        highest priority.  A lower-priority source can contribute a currency that
        the winner does not have — it never overwrites an existing currency entry.

        Example:
            source A (priority 100, USD only):  {"USD": {input:2.5, output:10}}
            source B (priority 70,  CNY only):  {"CNY": {input:18,  output:72}}
            result: {"USD": {input:2.5, output:10}, "CNY": {input:18, output:72}}
        """
        # Build a priority-ordered map: currency → already-seen priority
        seen_currencies: Dict[str, int] = {}

        # Seed with what the winner already contributed (full priority)
        winner_priority = source_list[0][2]
        for currency in merged[model_id].get(field, {}):
            seen_currencies[currency] = winner_priority

        # Walk sources in priority order; add currencies the winner didn't have
        for src_name, src_data, src_priority in source_list[1:]:
            src_field = src_data.get(field, {})
            if not isinstance(src_field, dict):
                continue
            for currency, currency_data in src_field.items():
                if currency not in seen_currencies:
                    # Normalize and add
                    normalized_entry = self._normalize_model_format(
                        {field: {currency: currency_data}}
                    )
                    if field not in merged[model_id]:
                        merged[model_id][field] = {}
                    merged[model_id][field][currency] = normalized_entry.get(field, {}).get(currency, currency_data)
                    seen_currencies[currency] = src_priority
                    logger.debug(
                        f"Currency-merged {model_id}.{field}.{currency} from {src_name} "
                        f"(priority {src_priority})"
                    )

    def _normalize_model_id(self, model_id: str, source: str) -> str:
        """
        Normalize model ID for merging.

        - OpenRouter: remove provider prefix (openai/gpt-4o -> gpt-4o)
        - Chinese providers: keep as-is (qwen-max, glm-4)
        - Original providers: keep as-is
        """
        if source == "openrouter" and "/" in model_id:
            return model_id.split("/", 1)[1]
        return model_id

    def _check_price_conflicts(
        self,
        model_id: str,
        source_list: List[Tuple[str, Dict[str, Any], int]],
        warnings: List[str]
    ) -> None:
        """Check for price conflicts between sources (standard and batch pricing)."""
        self._check_pricing_field_conflicts(
            model_id, source_list, warnings, field="pricing"
        )
        self._check_pricing_field_conflicts(
            model_id, source_list, warnings, field="batch_pricing"
        )

    def _check_pricing_field_conflicts(
        self,
        model_id: str,
        source_list: List[Tuple[str, Dict[str, Any], int]],
        warnings: List[str],
        field: str,
    ) -> None:
        """Check for input_price drift in a given pricing field across sources."""
        prices = []

        for source_name, model_data, _ in source_list:
            pricing = model_data.get(field, {})
            for currency, price_info in pricing.items():
                if not isinstance(price_info, dict):
                    continue
                input_price = price_info.get("input_price")
                output_price = price_info.get("output_price")
                if input_price is not None:
                    prices.append((source_name, currency, input_price, output_price))

        if len(prices) < 2:
            return

        # Compare first two sources
        base_source, base_currency, base_input, base_output = prices[0]
        other_source, other_currency, other_input, other_output = prices[1]

        # Only compare same currency
        if base_currency != other_currency:
            return

        # Check for >1% drift
        if base_input and other_input:
            drift = abs(base_input - other_input) / base_input
            if drift > config.price_drift_warning_threshold:
                label = "Batch price" if field == "batch_pricing" else "Price"
                warning = (
                    f"{label} drift detected for {model_id}: "
                    f"{base_source}={base_input} vs {other_source}={other_input} "
                    f"({drift*100:.1f}% difference)"
                )
                warnings.append(warning)
                logger.warning(warning)

    def _normalize_model_format(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a model entry to burncloud PricingConfig format.

        Fixes:
        - Remove 'unit' field from pricing (not in CurrencyPricing struct)
        - Move cache_pricing out of pricing dict to top-level if misplaced
        - cache_write_input_price → cache_creation_input_price
        - null output_price → 0.0 (CurrencyPricing.output_price is i64, not Option)
        - Warn on output_price == 0
        """
        model = copy.deepcopy(model)

        # Fix pricing entries
        pricing = model.get("pricing", {})
        cache_pricing_from_nested = None
        for currency, pp in list(pricing.items()):
            if not isinstance(pp, dict):
                continue
            pp.pop("unit", None)
            if pp.get("output_price") is None:
                logger.warning(f"output_price is null, setting to 0.0")
                pp["output_price"] = 0.0
            elif pp.get("output_price") == 0.0:
                logger.debug(f"output_price is 0.0 — may be incomplete data")
            # Move misplaced cache_pricing out of pricing dict
            if "cache_pricing" in pp:
                cache_pricing_from_nested = pp.pop("cache_pricing")

        if cache_pricing_from_nested and "cache_pricing" not in model:
            model["cache_pricing"] = cache_pricing_from_nested

        # Fix cache_pricing field names
        for currency, cp in model.get("cache_pricing", {}).items():
            if not isinstance(cp, dict):
                continue
            cp.pop("unit", None)
            if "cache_write_input_price" in cp:
                cp["cache_creation_input_price"] = cp.pop("cache_write_input_price")

        return model

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
        0 on success, 1 on error, 2 on warnings
    """
    import sys

    if date_str is None:
        from datetime import date
        date_str = date.today().isoformat()

    try:
        merger = PricingMerger()
        data, warnings = merger.merge_all(date_str)

        # Save
        output_path = merger.save(data)

        print(f"✅ Merged {len(data['models'])} models to {output_path}")

        if warnings:
            print(f"\n⚠️  {len(warnings)} warnings:")
            for warning in warnings:
                print(f"   - {warning}")
            return 2

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
