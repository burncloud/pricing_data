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
            "version": "2.0",
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
        1. Use the highest-priority source as the base structure
        2. Merge endpoints: lower-priority sources can contribute endpoint keys
           the winner doesn't have (e.g. CNY from bigmodel.cn + USD from z.ai)
        3. Log warnings for price conflicts on the same endpoint key
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
            merged[normalized_id] = copy.deepcopy(primary_data)

            if len(source_list) > 1:
                # Endpoint-level merge: lower-priority sources can contribute
                # endpoint keys the winner doesn't have (e.g. CNY bigmodel.cn
                # endpoint alongside USD api.openai.com endpoint).
                self._merge_endpoints(normalized_id, merged, source_list)

            # Normalize AFTER endpoint merging so all endpoints are cleaned
            # (stray 'unit'/'source' fields, null output_price, field renames)
            merged[normalized_id] = self._normalize_model_format(merged[normalized_id])

            # Check for price conflicts on shared endpoint keys
            if len(source_list) > 1:
                self._check_price_conflicts(normalized_id, source_list, warnings)

            # Track source
            if "metadata" not in merged[normalized_id]:
                merged[normalized_id]["metadata"] = {}
            merged[normalized_id]["metadata"]["_merged_from"] = primary_source

        return merged

    def _merge_endpoints(
        self,
        model_id: str,
        merged: Dict[str, Any],
        source_list: List[Tuple[str, Dict[str, Any], int]],
    ) -> None:
        """
        Merge endpoint entries across sources.

        Rule: for each endpoint key (api.openai.com, open.bigmodel.cn, …), keep
        whichever source has the highest priority.  A lower-priority source can
        contribute an endpoint the winner does not have — it never overwrites an
        existing endpoint entry.

        Example:
            source A (priority 100, api.openai.com/USD only)
            source B (priority 70,  openrouter.ai/USD)
            source C (priority 100, open.bigmodel.cn/CNY only)
            result: all three endpoint keys present
        """
        seen_endpoints: Dict[str, int] = {}

        # Seed with what the winner already contributed
        winner_priority = source_list[0][2]
        for ep_key in merged[model_id].get("endpoints", {}):
            seen_endpoints[ep_key] = winner_priority

        # Walk sources in priority order; add endpoints the winner didn't have
        for src_name, src_data, src_priority in source_list[1:]:
            for ep_key, ep_data in src_data.get("endpoints", {}).items():
                if ep_key not in seen_endpoints:
                    if "endpoints" not in merged[model_id]:
                        merged[model_id]["endpoints"] = {}
                    merged[model_id]["endpoints"][ep_key] = copy.deepcopy(ep_data)
                    seen_endpoints[ep_key] = src_priority
                    logger.debug(
                        f"Endpoint-merged {model_id}.endpoints.{ep_key} from {src_name} "
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
        """
        Check for price conflicts on shared endpoint keys across sources.

        For each endpoint key that appears in more than one source, compare
        the pricing.input_price and batch_pricing.input_price for drift.
        """
        # Collect endpoint-keyed prices: {ep_key: [(source_name, pricing, batch_pricing), ...]}
        ep_sources: Dict[str, List[Tuple[str, Dict, Dict]]] = {}
        for source_name, model_data, _ in source_list:
            for ep_key, ep_data in model_data.get("endpoints", {}).items():
                if ep_key not in ep_sources:
                    ep_sources[ep_key] = []
                ep_sources[ep_key].append((
                    source_name,
                    ep_data.get("pricing", {}),
                    ep_data.get("batch_pricing", {}),
                ))

        for ep_key, ep_list in ep_sources.items():
            if len(ep_list) < 2:
                continue

            base_source, base_pricing, base_batch = ep_list[0]
            other_source, other_pricing, other_batch = ep_list[1]

            for label, base_p, other_p in [
                ("Price", base_pricing, other_pricing),
                ("Batch price", base_batch, other_batch),
            ]:
                base_input = base_p.get("input_price")
                other_input = other_p.get("input_price")
                if base_input and other_input:
                    drift = abs(base_input - other_input) / base_input
                    if drift > config.price_drift_warning_threshold:
                        warning = (
                            f"{label} drift detected for {model_id} [{ep_key}]: "
                            f"{base_source}={base_input} vs {other_source}={other_input} "
                            f"({drift*100:.1f}% difference)"
                        )
                        warnings.append(warning)
                        logger.warning(warning)

    def _normalize_model_format(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a model entry to burncloud PricingConfig format (endpoint-keyed).

        Fixes per endpoint entry:
        - null output_price → 0.0
        - cache_write_input_price → cache_creation_input_price
        - Remove stray 'unit' or 'source' fields from pricing dicts
        """
        model = copy.deepcopy(model)

        for ep_key, ep_data in model.get("endpoints", {}).items():
            if not isinstance(ep_data, dict):
                continue

            # Normalize flat pricing
            pricing = ep_data.get("pricing", {})
            if isinstance(pricing, dict):
                pricing.pop("unit", None)
                pricing.pop("source", None)
                if pricing.get("output_price") is None:
                    logger.warning(f"output_price is null for {ep_key}, setting to 0.0")
                    pricing["output_price"] = 0.0
                elif pricing.get("output_price") == 0.0:
                    logger.debug(f"output_price is 0.0 for {ep_key} — may be incomplete data")

            # Fix cache_pricing field names
            cache_pricing = ep_data.get("cache_pricing", {})
            if isinstance(cache_pricing, dict):
                cache_pricing.pop("unit", None)
                if "cache_write_input_price" in cache_pricing:
                    cache_pricing["cache_creation_input_price"] = cache_pricing.pop("cache_write_input_price")

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
