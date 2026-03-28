"""
Generate pricing.md — a human-readable Markdown pricing table from pricing.json.

Usage:
    python -m scripts.render
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from scripts.config import config

# Endpoints that are aggregators, not direct provider APIs
AGGREGATORS = {"litellm", "openrouter.ai"}

# Display names for known providers
PROVIDER_DISPLAY: Dict[str, str] = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "google": "Google",
    "gemini": "Google (Gemini)",
    "deepseek": "DeepSeek",
    "zhipu": "Zhipu AI (智谱)",
    "mistral": "Mistral",
    "mistralai": "Mistral AI",
    "xai": "xAI (Grok)",
    "qwen": "Qwen (通义千问)",
    "dashscope": "DashScope (阿里云)",
    "perplexity": "Perplexity",
    "cohere": "Cohere",
    "together_ai": "Together AI",
    "fireworks_ai": "Fireworks AI",
    "deepinfra": "DeepInfra",
    "novita": "Novita AI",
    "nebius": "Nebius AI",
    "sambanova": "SambaNova",
    "moonshot": "Moonshot AI (月之暗面)",
    "minimax": "MiniMax",
    "meta-llama": "Meta (Llama)",
    "ollama": "Ollama (local)",
    "bedrock_converse": "AWS Bedrock",
    "vertex_ai-anthropic_models": "Google Vertex (Anthropic)",
    "vertex_ai-mistral_models": "Google Vertex (Mistral)",
    "vertex_ai-llama_models": "Google Vertex (Llama)",
    "vercel_ai_gateway": "Vercel AI Gateway",
    "databricks": "Databricks",
    "replicate": "Replicate",
    "lambda_ai": "Lambda AI",
    "anyscale": "Anyscale",
    "nvidia": "NVIDIA",
    "voyage": "Voyage AI",
    "wandb": "Weights & Biases",
    "ovhcloud": "OVHcloud",
    "oci": "Oracle Cloud",
    "openrouter": "OpenRouter",
    "llamagate": "LlamaGate",
    "gradient_ai": "Gradient AI",
    "unknown": "Unknown",
}

# Providers shown expanded (important / official APIs first)
FEATURED_PROVIDERS = [
    "anthropic", "openai", "google", "gemini", "deepseek", "zhipu",
    "mistral", "mistralai", "xai", "qwen", "dashscope",
    "perplexity", "cohere", "moonshot", "minimax",
]

CURRENCY_SYMBOL = {"USD": "$", "CNY": "¥"}


def pick_canonical_endpoint(model: Dict) -> Tuple[str, Dict]:
    """
    Return (endpoint_key, endpoint_data) for the best endpoint to display.

    Priority:
    1. The endpoint the model was merged from (if it's not an aggregator)
    2. Any non-aggregator endpoint (official direct API)
    3. litellm (has pricing for almost everything)
    4. First available endpoint
    """
    endpoints = model.get("endpoints", {})
    if not endpoints:
        return "", {}

    merged_from = model.get("metadata", {}).get("_merged_from", "")
    if merged_from and merged_from not in AGGREGATORS and merged_from in endpoints:
        return merged_from, endpoints[merged_from]

    for key, ep in endpoints.items():
        if key not in AGGREGATORS:
            return key, ep

    if "litellm" in endpoints:
        return "litellm", endpoints["litellm"]

    key = next(iter(endpoints))
    return key, endpoints[key]


def fmt_price(price: Optional[float], symbol: str = "$") -> str:
    if price is None:
        return "—"
    if price == 0.0:
        return "free"
    if price < 0.001:
        return f"{symbol}{price:.6f}"
    if price < 0.01:
        return f"{symbol}{price:.4f}"
    if price < 0.1:
        return f"{symbol}{price:.3f}"
    return f"{symbol}{price:.2f}"


def fmt_context(tokens: Optional[int]) -> str:
    if not tokens:
        return "—"
    if tokens >= 1_000_000:
        return f"{tokens // 1_000_000}M"
    if tokens >= 1_000:
        return f"{tokens // 1_000}K"
    return str(tokens)


def _provider_sort_key(prov: str) -> tuple:
    try:
        return (0, FEATURED_PROVIDERS.index(prov))
    except ValueError:
        return (1, prov)


def _model_sort_key(item: Tuple[str, Dict]) -> float:
    _, m = item
    _, ep = pick_canonical_endpoint(m)
    p = ep.get("pricing", {})
    return -(p.get("input_price") or 0.0)


def render(data: Dict) -> str:
    models = data["models"]
    updated_at = (data.get("updated_at") or "")[:10]
    total_models = len(models)

    # Group by provider
    by_provider: Dict[str, list] = {}
    for mid, model in models.items():
        provider = model.get("metadata", {}).get("provider", "unknown")
        by_provider.setdefault(provider, []).append((mid, model))

    sorted_providers = sorted(by_provider.keys(), key=_provider_sort_key)

    lines: list[str] = []

    # ------------------------------------------------------------------ header
    lines += [
        "# AI Model Pricing",
        "",
        f"*Updated: {updated_at} &nbsp;·&nbsp; "
        f"{total_models} models &nbsp;·&nbsp; "
        f"[Raw JSON](pricing.json)*",
        "",
        "> Prices are **per million tokens (MTok)** unless noted.  ",
        "> USD prices in **$**, CNY prices in **¥**.  ",
        "> Cache / Batch columns appear only when at least one model in the section offers them.",
        "",
    ]

    # --------------------------------------------------------------- TOC table
    lines += [
        "## Providers",
        "",
        "| Provider | Models |",
        "|----------|-------:|",
    ]
    for prov in sorted_providers:
        count = len(by_provider[prov])
        display = PROVIDER_DISPLAY.get(prov, prov.replace("_", " ").title())
        anchor = display.lower()
        for ch in " /()（）,、":
            anchor = anchor.replace(ch, "-")
        anchor = anchor.strip("-")
        lines.append(f"| [{display}](#{anchor}) | {count} |")
    lines.append("")

    # ------------------------------------------------ per-provider sections
    for prov in sorted_providers:
        display = PROVIDER_DISPLAY.get(prov, prov.replace("_", " ").title())
        models_list = sorted(by_provider[prov], key=_model_sort_key)

        lines += [f"## {display}", ""]

        # Detect which optional columns exist in this provider's models
        has_cache = any(
            pick_canonical_endpoint(m)[1].get("cache_pricing")
            for _, m in models_list
        )
        has_batch = any(
            pick_canonical_endpoint(m)[1].get("batch_pricing")
            for _, m in models_list
        )
        has_context = any(
            m.get("metadata", {}).get("context_window")
            for _, m in models_list
        )

        # Table header
        header_cols = ["| Model", "Input", "Output"]
        sep_cols = ["|-------", "------:", "-------:"]
        if has_cache:
            header_cols.append("Cache Read")
            sep_cols.append("----------:")
        if has_batch:
            header_cols.append("Batch In")
            header_cols.append("Batch Out")
            sep_cols.append("---------:")
            sep_cols.append("----------:")
        if has_context:
            header_cols.append("Context")
            sep_cols.append("--------:")
        header_cols.append("Currency |")
        sep_cols.append("---------|")

        lines.append(" | ".join(header_cols))
        lines.append("|".join(sep_cols))

        for mid, model in models_list:
            ep_key, ep = pick_canonical_endpoint(model)
            p = ep.get("pricing", {})
            currency = ep.get("currency", "USD")
            sym = CURRENCY_SYMBOL.get(currency, currency)
            meta = model.get("metadata", {})

            inp = fmt_price(p.get("input_price"), sym)
            out = fmt_price(p.get("output_price"), sym)

            row_cols = [f"| `{mid}`", inp, out]

            if has_cache:
                cp = ep.get("cache_pricing", {})
                row_cols.append(fmt_price(cp.get("cache_read_input_price"), sym))

            if has_batch:
                bp = ep.get("batch_pricing", {})
                row_cols.append(fmt_price(bp.get("input_price"), sym))
                row_cols.append(fmt_price(bp.get("output_price"), sym))

            if has_context:
                row_cols.append(fmt_context(meta.get("context_window")))

            row_cols.append(f"{currency} |")
            lines.append(" | ".join(row_cols))

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    pricing_path = config.pricing_file
    output_path = config.repo_root / "pricing.md"

    with open(pricing_path, encoding="utf-8") as f:
        data = json.load(f)

    md = render(data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"✅ Generated {output_path} ({len(data['models'])} models)")


if __name__ == "__main__":
    main()
