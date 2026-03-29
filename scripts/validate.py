"""
Generate validation_report.json alongside pricing.json.

Documents all inclusion/exclusion decisions made during the merge pipeline.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def generate_validation_report(
    *,
    included: Dict[str, Any],
    anomalous: List[Dict[str, Any]],
    unverified: List[Dict[str, Any]],
    source_map: Dict[str, Dict[str, list]],
    output_dir: Path,
) -> Path:
    """
    Write validation_report.json with inclusion/exclusion details.

    Args:
        included: models that made it into pricing.json
        anomalous: models rejected by anomaly filter
        unverified: models rejected by admission gate
        source_map: model_id → currency → [(source_name, ep_data, priority), ...]
        output_dir: directory to write the report to

    Returns:
        Path to written report file
    """
    # Build included_models with source info and verification evidence
    included_models = {}
    for model_id in included:
        sources_for_model = source_map.get(model_id, {})
        all_sources = set()
        top_priority = 0
        verified_urls = set()
        for currency_sources in sources_for_model.values():
            for entry in currency_sources:
                src_name = entry[0]
                priority = entry[2]
                fetched_url = entry[3] if len(entry) > 3 else None
                all_sources.add(src_name)
                if priority > top_priority:
                    top_priority = priority
                if fetched_url:
                    verified_urls.add(fetched_url)
        included_models[model_id] = {
            "sources": sorted(all_sources),
            "top_priority": top_priority,
            "verified_urls": sorted(verified_urls),
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_included": len(included),
            "excluded_anomalous": len(set(a["model"] for a in anomalous)),
            "excluded_unverified": len(unverified),
        },
        "included_models": included_models,
        "excluded_models": {
            "anomalous": anomalous,
            "unverified": unverified,
        },
    }

    output_path = output_dir / "validation_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Validation report: {len(included)} included, "
        f"{report['summary']['excluded_anomalous']} anomalous, "
        f"{len(unverified)} unverified → {output_path}"
    )

    return output_path
