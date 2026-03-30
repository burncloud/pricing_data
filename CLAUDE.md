# pricing_data

LLM API pricing data platform. Fetches pricing from multiple providers, merges with priority resolution, outputs `pricing.json`.

## pricing.json Format (Schema v8.0)

```json
{
  "version": "8.0",
  "updated_at": "2026-03-29T00:00:00+00:00",
  "source": "burncloud-official",
  "models": {
    "<model-id>": {
      "<CURRENCY>": {
        "text":  { "in": <$/MTok>, "out": <$/MTok> },
        "audio": { "in": <$/MTok>, "out": <$/MTok> },
        "image": { "in": <$/MTok>, "out": <$/MTok>, "per": <$/image> },
        "video": { "in": <$/MTok>, "sec": <$/second> },
        "music": { "per": <$/request> },
        "cache": { "in": <$/MTok>, "creation_input": <$/MTok> },
        "batch": { "in": <$/MTok>, "out": <$/MTok> },
        "tiered": [
          { "tier_start": 0, "tier_end": 200000, "in": <$/MTok>, "out": <$/MTok> },
          { "tier_start": 200000, "in": <$/MTok>, "out": <$/MTok> }
        ]
      }
    }
  }
}
```

### Price Keys

| Key | Unit | Meaning |
|-----|------|---------|
| `in` | $/1M tokens | Input token price |
| `out` | $/1M tokens | Output token price |
| `sec` | $/second | Per-second price (video generation) |
| `per` | $/item | Per-item price (image generation, music generation, per-request) |

### Modalities

- `text` — Standard text token pricing. Present on all LLM models.
- `audio` — Audio token pricing. TTS and voice I/O models only.
- `image` — Image pricing. `in`/`out` for token-based, `per` for per-image generation.
- `video` — Video pricing. `in` for token understanding, `sec` for per-second generation. May contain `tiered` array with `resolution` field.
- `music` — Music generation pricing. Uses `per` key.
- `cache` — Context caching pricing ($/MTok).
- `batch` — Batch API pricing ($/MTok).
- `tiered` — Tiered pricing array. Token tiers use `tier_start`/`tier_end`/`in`/`out`. Resolution tiers use `resolution`/`sec`.

### Rules

- All prices are non-negative numbers.
- `tiered` array inside a modality (e.g., `video.tiered`) means resolution-based tiers. Top-level `tiered` means context-length tiers.
- When `tiered` exists inside a modality, no flat price keys at the same level (avoid redundancy).
- Currency codes follow ISO 4217 (USD, CNY, etc.).
- Model IDs are lowercase, hyphen-separated (e.g., `gemini-2.5-flash`, `imagen-4-standard`).
- Provider is inferred from model_id prefix by consumers, not stored in pricing.json.

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Fetch pricing data
python -m scripts.fetch_all "$(date +%Y-%m-%d)"

# Merge into pricing.json
python -m scripts.merge "$(date +%Y-%m-%d)"

# Validate schema
python3 -c "import json, jsonschema; jsonschema.validate(json.load(open('pricing.json')), json.load(open('schema.json'))); print('OK')"
```

## Architecture

- `scripts/fetch/*.py` — Per-provider fetchers (output to `sources/<date>/<provider>.json`)
- `scripts/merge.py` — Priority-based merge into `pricing.json`
- `scripts/config.py` — Centralized config, provider rules, anomaly thresholds
- `schema.json` — JSON Schema definition
- `manual_overrides.json` — Human-verified price overrides (priority 200)
