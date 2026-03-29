"""
Merge pricing data from multiple sources into pricing.json.

Output format: v5.0 — nested modality pricing per model.
  pricing.json → model → {
    "pricing": {
      "USD": {
        "text": { "input_price": ..., "output_price": ... },
        "audio": { "input_price": ..., "output_price": ... },   # optional
        "image": { "input_price": ..., "output_price": ... },   # optional
        "cache_pricing": { ... },   # optional, at currency level
        "batch_pricing":  { ... },  # optional, at currency level
        "tiered_pricing": [ ... ],  # optional, at currency level
      },
      "CNY": { ... }
    },
    "metadata": { "provider": ..., "family": ..., ... }
  }

Modality field rules:
- text.*  : any source may contribute
- audio.* : MODALITY_AUTHORITATIVE_SOURCES only (blocks litellm, openrouter)
- image.* : MODALITY_AUTHORITATIVE_SOURCES only (blocks litellm, openrouter)

Priority order (higher = more authoritative):
1. manual_overrides (priority 200)
2. Original providers (OpenAI, Anthropic, etc.) - priority 100
3. Chinese providers (Zhipu, Aliyun, etc.) - priority 100
4. LiteLLM community aggregator - priority 70
5. OpenRouter aggregator - priority 50

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

from scripts.config import config, MODALITY_AUTHORITATIVE_SOURCES

logger = logging.getLogger(__name__)


def _is_nested_pricing(pricing: Dict[str, Any]) -> bool:
    """Return True if pricing already uses v5.0 nested modality format."""
    return any(k in pricing for k in ("text", "audio", "image"))


def _flat_to_nested(pricing: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """
    Convert flat pricing dict (from fetchers) to v5.0 nested modality.

    Flat: { "input_price": x, "output_price": y, "image_output_price": z? }
    Nested: { "text": {"input_price": x, "output_price": y}, "image": {"output_price": z} }

    image.* and audio.* fields are only populated when source is authoritative.
    """
    result: Dict[str, Any] = {}

    input_price = pricing.get("input_price")
    # Treat null output_price as 0.0 (matches old merge.py behaviour: `or 0.0`)
    output_price = pricing.get("output_price") or 0.0

    text: Dict[str, Any] = {}
    if input_price is not None:
        text["input_price"] = input_price
    text["output_price"] = output_price
    if text:
        result["text"] = text

    # image_output_price is per-image fee (e.g. Google image gen models)
    image_output_price = pricing.get("image_output_price")
    if image_output_price is not None and source_name in MODALITY_AUTHORITATIVE_SOURCES:
        result["image"] = {"output_price": image_output_price}

    return result


def _to_v5_pricing(pricing: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """Return v5.0 pricing dict regardless of input format."""
    if _is_nested_pricing(pricing):
        # Already nested — enforce source blocking for audio/image
        if source_name not in MODALITY_AUTHORITATIVE_SOURCES:
            result = {k: v for k, v in pricing.items() if k not in ("audio", "image")}
            return result
        return dict(pricing)
    return _flat_to_nested(pricing, source_name)


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

        # Merge with priority resolution → v5.0 output
        merged_models = self._merge_with_priority(all_sources, warnings)

        output = {
            "version": "5.0",
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
        Merge models from all sources into v5.0 nested modality pricing.

        For each model:
        - Group all endpoint entries by currency
        - Highest-priority source wins base pricing per currency
        - Lower-priority sources contribute missing batch_pricing / cache_pricing
        - audio.* and image.* only from MODALITY_AUTHORITATIVE_SOURCES
        - Warn on price drift within the same currency
        - Warn on completeness gaps across currencies
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

            # Resolve provider early for derived pricing.
            _meta_list = model_metadata.get(model_id, [])
            _provider: Optional[str] = None
            _winner_source: Optional[str] = None
            if _meta_list:
                _meta_list.sort(key=lambda x: x[2], reverse=True)
                _provider = _meta_list[0][1].get("provider")

            for currency, source_list in currency_map.items():
                source_list.sort(key=lambda x: x[2], reverse=True)

                winner_name, winner_ep, _ = source_list[0]
                if _winner_source is None:
                    _winner_source = winner_name

                # Build v5.0 modality entry from winner's pricing
                entry = _to_v5_pricing(winner_ep.get("pricing", {}), winner_name)

                # Pass through cache/batch/tiered from winner
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

                    # Modality fields from lower-priority AUTHORITATIVE sources only
                    if src_name in MODALITY_AUTHORITATIVE_SOURCES:
                        src_v5 = _to_v5_pricing(ep_data.get("pricing", {}), src_name)
                        for modality in ("audio", "image"):
                            if modality not in entry and modality in src_v5:
                                entry[modality] = src_v5[modality]
                                logger.debug(
                                    f"Field-merged {model_id}[{currency}].{modality} from {src_name}"
                                )

                    # Price drift check within same currency (text.input_price)
                    base_input = entry.get("text", {}).get("input_price")
                    other_p = ep_data.get("pricing", {})
                    if _is_nested_pricing(other_p):
                        other_input = other_p.get("text", {}).get("input_price")
                    else:
                        other_input = other_p.get("input_price")
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

                # Apply provider-level derived pricing for missing optional fields.
                if _provider:
                    text_p = entry.get("text", {})
                    text_input = text_p.get("input_price", 0) or 0
                    text_output = text_p.get("output_price", 0) or 0
                    cache_d, batch_d = config.get_derived_pricing(
                        _provider, model_id, text_input, text_output
                    )
                    if "cache_pricing" not in entry and cache_d:
                        entry["cache_pricing"] = cache_d
                        logger.debug(
                            f"Derived cache_pricing for {model_id}[{currency}] "
                            f"from {_provider} rules"
                        )
                    if "batch_pricing" not in entry and batch_d:
                        entry["batch_pricing"] = batch_d
                        logger.debug(
                            f"Derived batch_pricing for {model_id}[{currency}] "
                            f"from {_provider} rules"
                        )

                pricing[currency] = entry

            # Quality check: completeness across currencies
            self._check_pricing_completeness(model_id, pricing, warnings)

            # Build best metadata from highest-priority sources
            best_metadata = self._build_metadata(_meta_list, _winner_source)

            merged[model_id] = {
                "pricing": pricing,
                "metadata": best_metadata,
            }

        return merged

    def _build_metadata(
        self,
        meta_list: List[Tuple[str, Dict, int]],
        winner_source: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build best metadata from all sources.

        Highest-priority source wins base fields (provider, family).
        Lower-priority sources fill in supplemental fields (context_window, etc.).
        """
        if not meta_list:
            return {}

        # meta_list is already sorted descending by priority
        best: Dict[str, Any] = {}
        for _, meta, _ in meta_list:
            for key, value in meta.items():
                if key not in best and value is not None:
                    best[key] = value

        if winner_source:
            best["_merged_from"] = winner_source

        return best

    def _check_pricing_completeness(
        self,
        model_id: str,
        pricing: Dict[str, Any],
        warnings: List[str],
    ) -> None:
        """
        Quality check: if one currency has batch_pricing or cache_pricing but
        another currency for the same model doesn't, emit a warning.
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
