"""
Generate pricing.md — a human-readable Markdown pricing table from pricing.json.

Usage:
    python -m scripts.render
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from scripts.config import config, infer_provider

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


def pick_display_currency(model: Dict) -> Tuple[str, Dict]:
    """
    Return (currency_code, currency_entry) for the best currency to display.

    Priority: USD > CNY > first available. Model is the currency map directly.
    """
    if not model:
        return "", {}
    for code in ("USD", "CNY"):
        if code in model:
            return code, model[code]
    code = next(iter(model))
    return code, model[code]


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
    _, entry = pick_display_currency(m)
    return -(entry.get("text", {}).get("input") or 0.0)


def render(data: Dict) -> str:
    models = data["models"]
    updated_at = (data.get("updated_at") or "")[:10]
    total_models = len(models)

    # Group by provider (inferred from model_id prefix)
    by_provider: Dict[str, list] = {}
    for mid, model in models.items():
        provider = infer_provider(mid)
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
        "> Jump to: [Quick Reference](#quick-reference) · [All Providers](#providers)",
        "",
    ]

    # ---------------------------------------------------------- quick reference
    QUICK_REF_MODELS = [
        # Anthropic
        "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-3-5",
        # OpenAI
        "gpt-4o", "gpt-4o-mini", "o3", "o3-mini",
        # Google
        "gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite",
        # DeepSeek
        "deepseek-chat", "deepseek-reasoner",
        # xAI
        "grok-3", "grok-3-mini",
        # Mistral
        "mistral-large-latest", "mistral-small-latest",
        # Zhipu
        "glm-4-plus", "glm-4.7-flash",
        # Meta
        "llama-3.3-70b-instruct",
    ]
    qr_rows = []
    for mid in QUICK_REF_MODELS:
        m = models.get(mid)
        if not m:
            continue
        currency, entry = pick_display_currency(m)
        if not entry:
            continue
        text_p = entry.get("text", {})
        if not text_p.get("input"):
            continue
        sym = CURRENCY_SYMBOL.get(currency, currency)
        provider = infer_provider(mid)
        display_prov = PROVIDER_DISPLAY.get(provider, provider.replace("_", " ").title())
        inp = fmt_price(text_p.get("input"), sym)
        out = fmt_price(text_p.get("output"), sym)
        cp = entry.get("cache", {})
        bp = entry.get("batch", {})
        cache = fmt_price(cp.get("read_input"), sym) if cp else "—"
        batch = fmt_price(bp.get("input"), sym) if bp else "—"
        qr_rows.append(f"| `{mid}` | {display_prov} | {inp} | {out} | {cache} | {batch} | {currency} |")

    if qr_rows:
        lines += [
            "## Quick Reference",
            "",
            "Most-used models across major providers. Cache Read and Batch In are per MTok.",
            "",
            "| Model | Provider | Input | Output | Cache Read | Batch In | Currency |",
            "|-------|----------|------:|-------:|-----------:|---------:|---------|",
        ]
        lines += qr_rows
        lines.append("")

    lines += [
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
            pick_display_currency(m)[1].get("cache")
            for _, m in models_list
        )
        has_batch = any(
            pick_display_currency(m)[1].get("batch")
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
        header_cols.append("Currency |")
        sep_cols.append("---------|")

        lines.append(" | ".join(header_cols))
        lines.append("|".join(sep_cols))

        for mid, model in models_list:
            currency, entry = pick_display_currency(model)
            text_p = entry.get("text", {})
            sym = CURRENCY_SYMBOL.get(currency, currency)

            inp = fmt_price(text_p.get("input"), sym)
            out = fmt_price(text_p.get("output"), sym)

            row_cols = [f"| `{mid}`", inp, out]

            if has_cache:
                cp = entry.get("cache", {})
                row_cols.append(fmt_price(cp.get("read_input"), sym))

            if has_batch:
                bp = entry.get("batch", {})
                row_cols.append(fmt_price(bp.get("input"), sym))
                row_cols.append(fmt_price(bp.get("output"), sym))

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
