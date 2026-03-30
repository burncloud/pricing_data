"""
Merge pricing data from multiple sources into pricing.json.

Output format: v8.0 — pricing-only, no metadata, supports token/per-second/per-item pricing.
  pricing.json → model → {
    "USD": {
      "text":  { "in": ..., "out": ... },
      "audio": { "in": ..., "out": ... },   # optional
      "image": { "in": ..., "out": ..., "per": ... },  # optional
      "video": { "in": ..., "sec": ... },   # optional, may have tiered
      "music": { "per": ... },              # optional
      "cache": { ... },   # optional, at currency level
      "batch":  { ... },  # optional, at currency level
      "tiered": [ ... ],  # optional, at currency level
    },
    "CNY": { ... }
  }

Provider is inferred from model_id prefix by consumers (see infer_provider() in config.py).

Modality field rules:
- text.*        : any source may contribute
- audio.*       : MODALITY_AUTHORITATIVE_SOURCES only (blocks litellm, openrouter)
- image.*       : MODALITY_AUTHORITATIVE_SOURCES only (blocks litellm, openrouter)
- cache/batch/tiered : first-party sources only (priority >= 100, blocks litellm, openrouter)

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

from scripts.config import (
    config, infer_provider, MODALITY_AUTHORITATIVE_SOURCES,
    PRICE_ANOMALY_THRESHOLDS, FIRST_PARTY_PRIORITY_THRESHOLD,
)

logger = logging.getLogger(__name__)


def _is_nested_pricing(pricing: Dict[str, Any]) -> bool:
    """Return True if pricing already uses v5.0 nested modality format."""
    return any(k in pricing for k in ("text", "audio", "image", "video", "music"))


def _flat_to_nested(pricing: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """
    Convert flat pricing dict (from fetchers) to v5.0 nested modality.

    Flat: { "in": x, "out": y, "image_out": z? }
    Nested: { "text": {"in": x, "out": y}, "image": {"out": z} }

    image.* and audio.* fields are only populated when source is authoritative.
    """
    result: Dict[str, Any] = {}

    # Accept new ("in"/"out"), transitional ("input"/"output") and legacy ("input_price"/"output_price") keys
    input_price = pricing.get("in") if pricing.get("in") is not None else (
        pricing.get("input") if pricing.get("input") is not None else pricing.get("input_price")
    )
    # Treat null output as 0.0 (matches old merge.py behaviour: `or 0.0`)
    raw_output = pricing.get("out") if pricing.get("out") is not None else (
        pricing.get("output") if pricing.get("output") is not None else pricing.get("output_price")
    )
    output_price = raw_output or 0.0

    text: Dict[str, Any] = {}
    if input_price is not None:
        text["in"] = input_price
    text["out"] = output_price
    if text:
        result["text"] = text

    # image_out is per-image fee (e.g. Google image gen models)
    image_output_price = (
        pricing.get("image_out") if pricing.get("image_out") is not None else (
            pricing.get("image_output") if pricing.get("image_output") is not None else pricing.get("image_output_price")
        )
    )
    if image_output_price is not None and source_name in MODALITY_AUTHORITATIVE_SOURCES:
        result["image"] = {"out": image_output_price}

    return result


def _normalize_modality_fields(modality_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Rename legacy input_price/output_price/input/output/read_input keys to in/out."""
    result = {}
    for k, v in modality_dict.items():
        if k in ("input_price", "input"):
            result["in"] = v
        elif k in ("output_price", "output"):
            result["out"] = v
        elif k == "read_input":
            result["in"] = v
        elif k == "image_output":
            result["image_out"] = v
        else:
            result[k] = v
    return result


def _normalize_tiered(tiered: list) -> list:
    """Normalize legacy input/output keys in tier objects to in/out."""
    return [_normalize_modality_fields(tier) for tier in tiered]


def _to_v5_pricing(pricing: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """Return v7.0 pricing dict regardless of input format."""
    if _is_nested_pricing(pricing):
        # Already nested — enforce source blocking for audio/image, normalize field names
        if source_name not in MODALITY_AUTHORITATIVE_SOURCES:
            filtered = {k: v for k, v in pricing.items() if k not in ("audio", "image", "video", "music")}
        else:
            filtered = dict(pricing)
        # Normalize legacy field names inside each modality dict
        return {
            modality: _normalize_modality_fields(v) if isinstance(v, dict) else v
            for modality, v in filtered.items()
        }
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

    @staticmethod
    def _convert_manual_overrides(raw_models: Dict[str, Any]) -> Dict[str, Any]:
        """Convert manual_overrides v5.0 format to endpoints format for merge."""
        _optional = ("cache", "batch", "tiered")
        result: Dict[str, Any] = {}
        for model_id, entry in raw_models.items():
            if not isinstance(entry, dict):
                continue
            endpoints: Dict[str, Any] = {}
            for key, val in entry.items():
                if key.startswith("_") or not isinstance(val, dict):
                    continue
                currency = key
                pricing = {k: v for k, v in val.items() if k not in _optional}
                ep: Dict[str, Any] = {"currency": currency, "pricing": pricing}
                for f in _optional:
                    if f in val:
                        ep[f] = val[f]
                endpoints[f"manual_{currency}"] = ep
            if endpoints:
                result[model_id] = {"endpoints": endpoints}
        return result

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
        raw_merged, source_map = self._merge_with_priority(all_sources, warnings)

        # Filter anomalous prices
        filtered, anomalous = self._filter_anomalous_prices(raw_merged)

        # Admission gate: only models with first-party verified sources
        admitted, unverified = self._apply_admission_gate(filtered, source_map)

        merged_models = admitted

        output = {
            "version": "8.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "burncloud-official",
            "models": merged_models,
        }

        # Validate against schema
        self._validate(output)

        # Generate validation report
        from scripts.validate import generate_validation_report
        generate_validation_report(
            included=admitted,
            anomalous=anomalous,
            unverified=unverified,
            source_map=source_map,
            output_dir=config.repo_root,
        )

        return output, warnings

    def _collect_sources(self, sources_dir: Path) -> List[Dict[str, Any]]:
        """Collect all source JSON files, including manual overrides.

        Each source entry includes:
        - name: source identifier
        - data: the full JSON data (models, status, etc.)
        - fetched_url: the URL the crawler actually fetched (None for non-crawler sources)
        """
        sources = []

        # Load manual overrides first (highest priority, priority=200)
        # Note: manual_overrides have NO fetched_url — they are human-verified, not crawled.
        # The admission gate will only admit them if they also appear in a crawler source,
        # OR if they are explicitly allowed via _verified_source metadata.
        manual_override_path = config.data_dir / "manual_overrides.json"
        if manual_override_path.exists():
            try:
                with open(manual_override_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("models"):
                    converted = self._convert_manual_overrides(data["models"])
                    sources.append({
                        "name": "manual_overrides",
                        "data": {"models": converted, "status": "success"},
                        "fetched_url": None,
                    })
                    logger.info(f"Loaded manual overrides: {len(converted)} models")
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
                        "fetched_url": data.get("fetched_url"),
                    })
                    logger.info(f"Loaded source: {source_file.name} ({model_count} models)")

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load {source_file}: {e}")

        return sources

    def _merge_with_priority(
        self,
        sources: List[Dict[str, Any]],
        warnings: List[str]
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, list]]]:
        """
        Merge models from all sources into v5.0 nested modality pricing.

        Returns:
            Tuple of (merged_models, source_map) where source_map is
            model_id → currency → [(source_name, ep_data, priority, fetched_url), ...]

        For each model:
        - Group all endpoint entries by currency
        - Highest-priority source wins base pricing per currency
        - Lower-priority FIRST-PARTY sources (priority >= 100) may fill missing cache/batch/tiered
        - Aggregators (litellm p70, openrouter p50) cannot contribute any pricing fields
        - audio.* and image.* only from MODALITY_AUTHORITATIVE_SOURCES
        - Warn on price drift within the same currency
        - Warn on completeness gaps across currencies
        """
        merged = {}

        # model_id → { currency → [(source_name, ep_data, priority, fetched_url), ...] }
        model_currency_sources: Dict[str, Dict[str, List[Tuple[str, Dict, int, Optional[str]]]]] = {}

        for source in sources:
            source_name = source["name"]
            priority = config.get_source_priority(source_name)
            fetched_url = source.get("fetched_url")

            for model_id, model_data in source["data"]["models"].items():
                normalized_id = self._normalize_model_id(model_id, source_name)

                if normalized_id not in model_currency_sources:
                    model_currency_sources[normalized_id] = {}

                for ep_key, ep_data in model_data.get("endpoints", {}).items():
                    currency = ep_data.get("currency", "USD")
                    if currency not in model_currency_sources[normalized_id]:
                        model_currency_sources[normalized_id][currency] = []
                    model_currency_sources[normalized_id][currency].append(
                        (source_name, ep_data, priority, fetched_url)
                    )

        for model_id, currency_map in model_currency_sources.items():
            pricing: Dict[str, Any] = {}

            # Infer provider from model_id for derived pricing.
            _provider = infer_provider(model_id)

            for currency, source_list in currency_map.items():
                source_list.sort(key=lambda x: x[2], reverse=True)

                winner_name, winner_ep, _, _ = source_list[0]

                # Build v5.0 modality entry from winner's pricing
                entry = _to_v5_pricing(winner_ep.get("pricing", {}), winner_name)

                # Pass through cache/batch/tiered from winner.
                # Safe: the winner is always the highest-priority source. A model is
                # only admitted if it has a first-party source (priority >= 100,
                # fetched_url set), so the winner's optional fields are first-party origin.
                for field in ("cache", "batch", "tiered"):
                    if field in winner_ep:
                        val = copy.deepcopy(winner_ep[field])
                        if field == "tiered" and isinstance(val, list):
                            val = _normalize_tiered(val)
                        entry[field] = val

                # Iterate over lower-priority sources for enrichment and drift checks.
                for src_name, ep_data, src_priority, _ in source_list[1:]:
                    # cache/batch/tiered: first-party sources only (priority >= 100).
                    # FIRST_PARTY_PRIORITY_THRESHOLD is reused intentionally — the same
                    # policy as the admission gate: only crawler-verified first-party
                    # sources are trusted for pricing. Aggregators (litellm p70,
                    # openrouter p50) cannot contribute any pricing fields.
                    if src_priority >= FIRST_PARTY_PRIORITY_THRESHOLD:
                        for field in ("cache", "batch", "tiered"):
                            if field not in entry and field in ep_data:
                                val = copy.deepcopy(ep_data[field])
                                if field == "tiered" and isinstance(val, list):
                                    val = _normalize_tiered(val)
                                entry[field] = val
                                logger.debug(
                                    f"Field-merged {model_id}[{currency}].{field} from {src_name}"
                                )
                    else:
                        logger.debug(
                            f"Skipping {src_name} (p{src_priority}) "
                            f"field enrichment for {model_id}"
                        )

                    # Modality fields from lower-priority AUTHORITATIVE sources only
                    if src_name in MODALITY_AUTHORITATIVE_SOURCES:
                        src_v5 = _to_v5_pricing(ep_data.get("pricing", {}), src_name)
                        for modality in ("audio", "image", "video", "music"):
                            if modality not in entry and modality in src_v5:
                                entry[modality] = src_v5[modality]
                                logger.debug(
                                    f"Field-merged {model_id}[{currency}].{modality} from {src_name}"
                                )

                    # Price drift check within same currency (text.in)
                    base_input = entry.get("text", {}).get("in")
                    other_p = ep_data.get("pricing", {})
                    if _is_nested_pricing(other_p):
                        other_input = other_p.get("text", {}).get("in") or other_p.get("text", {}).get("input")
                    else:
                        other_input = other_p.get("in") or other_p.get("input")
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

                # Normalize cache field names (unit field cleanup)
                if "cache" in entry:
                    entry["cache"].pop("unit", None)

                # Apply provider-level derived pricing for missing optional fields.
                if _provider and _provider != "unknown":
                    text_p = entry.get("text", {})
                    text_input = text_p.get("in", 0) or 0
                    text_output = text_p.get("out", 0) or 0
                    cache_d, batch_d = config.get_derived_pricing(
                        _provider, model_id, text_input, text_output
                    )
                    if "cache" not in entry and cache_d:
                        entry["cache"] = cache_d
                        logger.debug(
                            f"Derived cache_pricing for {model_id}[{currency}] "
                            f"from {_provider} rules"
                        )
                    if "batch" not in entry and batch_d:
                        entry["batch"] = batch_d
                        logger.debug(
                            f"Derived batch_pricing for {model_id}[{currency}] "
                            f"from {_provider} rules"
                        )

                pricing[currency] = entry

            # Quality check: completeness across currencies
            self._check_pricing_completeness(model_id, pricing, warnings)

            merged[model_id] = pricing

        return merged, model_currency_sources

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

        for field in ("batch", "cache"):
            currencies_with = [c for c in currencies if field in pricing[c]]
            currencies_without = [c for c in currencies if field not in pricing[c]]

            if currencies_with and currencies_without:
                warning = (
                    f"Incomplete pricing for {model_id}: "
                    f"{field} present in {currencies_with} but missing in {currencies_without}"
                )
                warnings.append(warning)
                logger.warning(warning)

    @staticmethod
    def _filter_anomalous_prices(
        merged: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Remove models with prices above anomaly thresholds or negative prices.

        Uses strict > comparison: price exactly at threshold passes.
        If ANY modality in a model is anomalous, the whole model is rejected.
        Zero prices ($0/$0) are treated as free tier and pass through.

        Returns:
            (filtered_models, anomalous_list)
        """
        filtered = {}
        anomalous: List[Dict[str, Any]] = []
        modalities = ("text", "audio", "image", "video", "music")

        for model_id, currency_map in merged.items():
            is_anomalous = False
            for currency, entry in currency_map.items():
                for modality in modalities:
                    mod_data = entry.get(modality)
                    if not isinstance(mod_data, dict):
                        continue
                    thresholds = PRICE_ANOMALY_THRESHOLDS.get(modality, {})
                    for direction in ("in", "out", "sec", "per"):
                        price = mod_data.get(direction)
                        if price is None:
                            continue
                        if price < 0:
                            anomalous.append({
                                "model": model_id,
                                "reason": f"negative {modality}.{direction}: {price}",
                                "value": price,
                            })
                            is_anomalous = True
                        elif direction in thresholds and price > thresholds[direction]:
                            unit = {"in": "/MTok", "out": "/MTok", "sec": "/sec", "per": "/item"}.get(direction, "")
                            anomalous.append({
                                "model": model_id,
                                "reason": (
                                    f"{modality}.{direction} ${price}{unit} "
                                    f"> ${thresholds[direction]} threshold"
                                ),
                                "value": price,
                            })
                            is_anomalous = True

            if not is_anomalous:
                filtered[model_id] = currency_map
            else:
                logger.warning(f"Anomalous price: excluding {model_id}")

        if anomalous:
            logger.info(
                f"Anomaly filter: excluded {len(merged) - len(filtered)} models "
                f"({len(anomalous)} anomalous prices found)"
            )

        return filtered, anomalous

    @staticmethod
    def _apply_admission_gate(
        models: Dict[str, Any],
        source_map: Dict[str, Dict[str, list]],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Only admit models that have at least one crawler-verified source.

        A source is crawler-verified if:
        1. It has a fetched_url (proves a crawler actually fetched from an official page), OR
        2. It is manual_overrides with priority >= 200 (human-verified with _verified_source)

        Aggregator sources (litellm, openrouter) have fetched_url pointing to their
        API, but their priority < FIRST_PARTY_PRIORITY_THRESHOLD so they don't count.

        Returns:
            (admitted_models, unverified_list)
        """
        admitted = {}
        unverified: List[Dict[str, Any]] = []

        for model_id, pricing in models.items():
            sources_for_model = source_map.get(model_id, {})
            has_verified_source = False
            max_priority = 0
            all_sources = set()
            for currency_sources in sources_for_model.values():
                for src_name, _, priority, fetched_url in currency_sources:
                    all_sources.add(src_name)
                    if priority > max_priority:
                        max_priority = priority
                    # Crawler-verified: has URL AND is a first-party source (not aggregator)
                    if fetched_url and priority >= FIRST_PARTY_PRIORITY_THRESHOLD:
                        has_verified_source = True
                    # Manual overrides: human-verified, allowed at priority 200
                    if src_name == "manual_overrides" and priority >= 200:
                        has_verified_source = True

            if has_verified_source:
                admitted[model_id] = pricing
            else:
                unverified.append({
                    "model": model_id,
                    "sources": sorted(all_sources),
                    "max_priority": max_priority,
                })
                logger.debug(f"Admission gate: excluding {model_id} (no verified source)")

        if unverified:
            logger.info(
                f"Admission gate: excluded {len(unverified)} unverified models, "
                f"admitted {len(admitted)}"
            )

        return admitted, unverified

    def _normalize_model_id(self, model_id: str, source: str) -> str:
        """
        Normalize model ID for merging.

        - OpenRouter: remove provider prefix (openai/gpt-4o -> gpt-4o)
        - All others: keep as-is
        """
        if source in ("openrouter", "litellm") and "/" in model_id:
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

        unknown_providers = [m for m in data["models"] if infer_provider(m) == "unknown"]
        if unknown_providers:
            print(f"\n⚠️  {len(unknown_providers)} models with unknown provider (no prefix match):")
            for m in unknown_providers[:5]:
                print(f"   - {m}")
            if len(unknown_providers) > 5:
                print(f"   ... and {len(unknown_providers) - 5} more")

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
