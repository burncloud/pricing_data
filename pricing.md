# AI Model Pricing

*Updated: 2026-03-29 &nbsp;·&nbsp; 1359 models &nbsp;·&nbsp; [Raw JSON](pricing.json)*

> Prices are **per million tokens (MTok)** unless noted.  
> USD prices in **$**, CNY prices in **¥**.  
> Jump to: [Quick Reference](#quick-reference) · [All Providers](#providers)

## Quick Reference

Most-used models across major providers. Cache Read and Batch In are per MTok.

| Model | Provider | Input | Output | Cache Read | Batch In | Currency |
|-------|----------|------:|-------:|-----------:|---------:|---------|
| `claude-opus-4-6` | Anthropic | $5.00 | $25.00 | — | — | USD |
| `claude-sonnet-4-6` | Anthropic | $3.00 | $15.00 | — | — | USD |
| `gpt-4o` | OpenAI | $2.50 | $10.00 | — | $1.25 | USD |
| `gpt-4o-mini` | OpenAI | $0.15 | $0.60 | — | $0.075 | USD |
| `o3` | Unknown | $2.00 | $8.00 | — | — | USD |
| `o3-mini` | OpenAI | $1.10 | $4.40 | — | — | USD |
| `gemini-2.5-pro` | Google | $1.25 | $10.00 | $0.12 | — | USD |
| `gemini-2.0-flash` | Google | $0.10 | $0.40 | $0.025 | — | USD |
| `gemini-2.0-flash-lite` | Google | $0.075 | $0.30 | — | — | USD |
| `deepseek-chat` | DeepSeek | $0.28 | $0.42 | $0.028 | — | USD |
| `deepseek-reasoner` | DeepSeek | $0.28 | $0.42 | $0.028 | — | USD |
| `grok-3` | Unknown | $3.00 | $15.00 | — | — | USD |
| `grok-3-mini` | Unknown | $0.30 | $0.50 | — | — | USD |
| `mistral-large-latest` | Unknown | $0.50 | $1.50 | — | — | USD |
| `mistral-small-latest` | Unknown | $0.060 | $0.18 | — | — | USD |
| `glm-4-plus` | Zhipu AI (智谱) | ¥5.00 | ¥5.00 | ¥2.50 | ¥2.50 | CNY |
| `glm-4.7-flash` | Zhipu AI (智谱) | $0.070 | $0.40 | $0.035 | — | USD |
| `llama-3.3-70b-instruct` | Unknown | $0.14 | $0.40 | — | — | USD |

> Cache / Batch columns appear only when at least one model in the section offers them.

## Providers

| Provider | Models |
|----------|-------:|
| [Anthropic](#anthropic) | 40 |
| [OpenAI](#openai) | 140 |
| [Google](#google) | 45 |
| [DeepSeek](#deepseek) | 54 |
| [Zhipu AI (智谱)](#zhipu-ai--智谱) | 38 |
| [Mistral](#mistral) | 1 |
| [Moonshot AI (月之暗面)](#moonshot-ai--月之暗面) | 10 |
| [Aliyun](#aliyun) | 23 |
| [Baidu](#baidu) | 9 |
| [Fireworks](#fireworks) | 260 |
| [Meta](#meta) | 2 |
| [NVIDIA](#nvidia) | 1 |
| [Thebloke](#thebloke) | 1 |
| [Unknown](#unknown) | 735 |

## Anthropic

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `claude-opus-4.1` | $15.00 | $75.00 | USD |
| `claude-opus-4` | $15.00 | $75.00 | USD |
| `claude-3-opus-20240229` | $15.00 | $75.00 | USD |
| `claude-4-opus-20250514` | $15.00 | $75.00 | USD |
| `claude-opus-4-1` | $15.00 | $75.00 | USD |
| `claude-opus-4-1-20250805` | $15.00 | $75.00 | USD |
| `claude-opus-4-20250514` | $15.00 | $75.00 | USD |
| `claude-4-opus` | $15.00 | $75.00 | USD |
| `claude-3-opus` | $15.00 | $75.00 | USD |
| `claude-opus-4.6` | $5.00 | $25.00 | USD |
| `claude-opus-4.5` | $5.00 | $25.00 | USD |
| `claude-opus-4-6` | $5.00 | $25.00 | USD |
| `claude-opus-4-5-20251101` | $5.00 | $25.00 | USD |
| `claude-opus-4-5` | $5.00 | $25.00 | USD |
| `claude-opus-4-6-20260205` | $5.00 | $25.00 | USD |
| `claude-3-7-sonnet-latest` | $3.30 | $16.50 | USD |
| `claude-sonnet-4.6` | $3.00 | $15.00 | USD |
| `claude-sonnet-4.5` | $3.00 | $15.00 | USD |
| `claude-sonnet-4` | $3.00 | $15.00 | USD |
| `claude-3.7-sonnet` | $3.00 | $15.00 | USD |
| `claude-3.7-sonnet:thinking` | $3.00 | $15.00 | USD |
| `claude-3.5-sonnet` | $3.00 | $15.00 | USD |
| `claude-sonnet-4-6` | $3.00 | $15.00 | USD |
| `claude-3-7-sonnet-20250219` | $3.00 | $15.00 | USD |
| `claude-4-sonnet-20250514` | $3.00 | $15.00 | USD |
| `claude-sonnet-4-5` | $3.00 | $15.00 | USD |
| `claude-sonnet-4-5-20250929` | $3.00 | $15.00 | USD |
| `claude-sonnet-4-20250514` | $3.00 | $15.00 | USD |
| `claude-4-sonnet` | $3.00 | $15.00 | USD |
| `claude-4.5-sonnet` | $3.00 | $15.00 | USD |
| `claude-3-5-sonnet` | $3.00 | $15.00 | USD |
| `claude-3-5-sonnet-20241022` | $3.00 | $15.00 | USD |
| `claude-3-7-sonnet` | $3.00 | $15.00 | USD |
| `claude-haiku-4.5` | $1.00 | $5.00 | USD |
| `claude-haiku-4-5-20251001` | $1.00 | $5.00 | USD |
| `claude-haiku-4-5` | $1.00 | $5.00 | USD |
| `claude-4.5-haiku` | $1.00 | $5.00 | USD |
| `claude-3.5-haiku` | $0.80 | $4.00 | USD |
| `claude-3-haiku` | $0.25 | $1.25 | USD |
| `claude-3-haiku-20240307` | $0.25 | $1.25 | USD |

## OpenAI

| Model | Input | Output | Cache Read | Batch In | Batch Out | Currency |
|-------|------:|-------:|----------:|---------:|----------:|---------|
| `o1-pro` | $150.00 | $600.00 | — | $75.00 | $300.00 | USD |
| `o1-pro-2025-03-19` | $150.00 | $600.00 | — | $75.00 | $300.00 | USD |
| `gpt-5.4-pro` | $30.00 | $180.00 | — | $15.00 | $90.00 | USD |
| `gpt-4` | $30.00 | $60.00 | — | — | — | USD |
| `gpt-4-0314` | $30.00 | $60.00 | — | — | — | USD |
| `gpt-4-0613` | $30.00 | $60.00 | — | — | — | USD |
| `gpt-5.4-pro-2026-03-05` | $30.00 | $180.00 | — | $15.00 | $90.00 | USD |
| `gpt-5.2-pro` | $21.00 | $168.00 | — | — | — | USD |
| `gpt-5.2-pro-2025-12-11` | $21.00 | $168.00 | — | — | — | USD |
| `o3-pro` | $20.00 | $80.00 | — | $10.00 | $40.00 | USD |
| `o3-pro-2025-06-10` | $20.00 | $80.00 | — | $10.00 | $40.00 | USD |
| `gpt-5-pro` | $15.00 | $120.00 | — | $7.50 | $60.00 | USD |
| `gpt-5-pro-2025-10-06` | $15.00 | $120.00 | — | $7.50 | $60.00 | USD |
| `o1-2024-12-17` | $15.00 | $60.00 | — | — | — | USD |
| `gpt-5-image` | $10.00 | $10.00 | — | — | — | USD |
| `o3-deep-research` | $10.00 | $40.00 | — | $5.00 | $20.00 | USD |
| `gpt-4-turbo` | $10.00 | $30.00 | — | — | — | USD |
| `gpt-4-turbo-preview` | $10.00 | $30.00 | — | — | — | USD |
| `gpt-4-1106-preview` | $10.00 | $30.00 | — | — | — | USD |
| `gpt-4-0125-preview` | $10.00 | $30.00 | — | — | — | USD |
| `gpt-4-turbo-2024-04-09` | $10.00 | $30.00 | — | — | — | USD |
| `o3-deep-research-2025-06-26` | $10.00 | $40.00 | — | $5.00 | $20.00 | USD |
| `gpt-4o:extended` | $6.00 | $18.00 | — | — | — | USD |
| `gpt-4o-2024-05-13` | $5.00 | $15.00 | — | $2.50 | $7.50 | USD |
| `gpt-4o-realtime-preview` | $5.00 | $20.00 | — | — | — | USD |
| `gpt-4o-realtime-preview-2024-12-17` | $5.00 | $20.00 | — | — | — | USD |
| `gpt-4o-realtime-preview-2025-06-03` | $5.00 | $20.00 | — | — | — | USD |
| `gpt-image-1.5` | $5.00 | $10.00 | — | — | — | USD |
| `gpt-image-1.5-2025-12-16` | $5.00 | $10.00 | — | — | — | USD |
| `gpt-realtime` | $4.00 | $16.00 | — | — | — | USD |
| `gpt-realtime-1.5` | $4.00 | $16.00 | — | — | — | USD |
| `gpt-realtime-2025-08-28` | $4.00 | $16.00 | — | — | — | USD |
| `gpt-oss-120b` | $3.00 | $4.50 | — | — | — | USD |
| `gpt-3.5-turbo-16k` | $3.00 | $4.00 | — | — | — | USD |
| `gpt-5.4` | $2.50 | $15.00 | $0.25 | $1.25 | $7.50 | USD |
| `gpt-audio` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-5-image-mini` | $2.50 | $2.00 | — | — | — | USD |
| `gpt-4o-audio-preview` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-4o-search-preview` | $2.50 | $10.00 | — | $1.25 | $5.00 | USD |
| `gpt-4o-2024-11-20` | $2.50 | $10.00 | — | $1.25 | $5.00 | USD |
| `gpt-4o-2024-08-06` | $2.50 | $10.00 | — | $1.25 | $5.00 | USD |
| `gpt-4o` | $2.50 | $10.00 | — | $1.25 | $5.00 | USD |
| `gpt-4o-transcribe-diarize` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-4o-audio-preview-2024-12-17` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-4o-audio-preview-2025-06-03` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-audio-1.5` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-audio-2025-08-28` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-4o-mini-tts` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-4o-search-preview-2025-03-11` | $2.50 | $10.00 | — | $1.25 | $5.00 | USD |
| `gpt-4o-transcribe` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-5.4-2026-03-05` | $2.50 | $15.00 | — | $1.25 | $7.50 | USD |
| `gpt-4o-mini-tts-2025-03-20` | $2.50 | $10.00 | — | — | — | USD |
| `gpt-4o-mini-tts-2025-12-15` | $2.50 | $10.00 | — | — | — | USD |
| `o4-mini-deep-research` | $2.00 | $8.00 | — | $1.00 | $4.00 | USD |
| `gpt-4.1` | $2.00 | $8.00 | — | $1.00 | $4.00 | USD |
| `gpt-4.1-2025-04-14` | $2.00 | $8.00 | — | $1.00 | $4.00 | USD |
| `o3-2025-04-16` | $2.00 | $8.00 | — | — | — | USD |
| `o4-mini-deep-research-2025-06-26` | $2.00 | $8.00 | — | $1.00 | $4.00 | USD |
| `gpt-5.3-chat` | $1.75 | $14.00 | — | — | — | USD |
| `gpt-5.3-codex` | $1.75 | $14.00 | — | — | — | USD |
| `gpt-5.2-codex` | $1.75 | $14.00 | — | — | — | USD |
| `gpt-5.2-chat` | $1.75 | $14.00 | — | — | — | USD |
| `gpt-5.2` | $1.75 | $14.00 | — | — | — | USD |
| `gpt-5.2-2025-12-11` | $1.75 | $14.00 | — | — | — | USD |
| `gpt-5.2-chat-latest` | $1.75 | $14.00 | — | — | — | USD |
| `gpt-5.3-chat-latest` | $1.75 | $14.00 | — | — | — | USD |
| `gpt-3.5-turbo-instruct` | $1.50 | $2.00 | — | — | — | USD |
| `gpt-3.5-turbo-instruct-0914` | $1.50 | $2.00 | — | — | — | USD |
| `gpt-35-turbo-instruct` | $1.50 | $2.00 | — | — | — | USD |
| `gpt-35-turbo-instruct-0914` | $1.50 | $2.00 | — | — | — | USD |
| `gpt-5.1-codex-max` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5.1` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5.1-chat` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5.1-codex` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5-codex` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5-chat` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-4o-mini-transcribe` | $1.25 | $5.00 | — | — | — | USD |
| `gpt-5.1-2025-11-13` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5.1-chat-latest` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5-2025-08-07` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5-chat-latest` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-4o-mini-transcribe-2025-03-20` | $1.25 | $5.00 | — | — | — | USD |
| `gpt-4o-mini-transcribe-2025-12-15` | $1.25 | $5.00 | — | — | — | USD |
| `gpt-5-search-api` | $1.25 | $10.00 | — | — | — | USD |
| `gpt-5-search-api-2025-10-14` | $1.25 | $10.00 | — | — | — | USD |
| `o4-mini-high` | $1.10 | $4.40 | — | — | — | USD |
| `o4-mini` | $1.10 | $4.40 | — | — | — | USD |
| `o3-mini-high` | $1.10 | $4.40 | — | — | — | USD |
| `o3-mini` | $1.10 | $4.40 | — | — | — | USD |
| `o3-mini-2025-01-31` | $1.10 | $4.40 | — | — | — | USD |
| `o4-mini-2025-04-16` | $1.10 | $4.40 | — | — | — | USD |
| `o1-mini` | $1.10 | $4.40 | — | — | — | USD |
| `gpt-3.5-turbo-0613` | $1.00 | $2.00 | — | — | — | USD |
| `gpt-3.5-turbo-1106` | $1.00 | $2.00 | — | — | — | USD |
| `gpt-5.4-mini` | $0.75 | $4.50 | $0.075 | $0.38 | $2.25 | USD |
| `gpt-audio-mini` | $0.60 | $2.40 | — | — | — | USD |
| `gpt-audio-mini-2025-10-06` | $0.60 | $2.40 | — | — | — | USD |
| `gpt-audio-mini-2025-12-15` | $0.60 | $2.40 | — | — | — | USD |
| `gpt-4o-mini-realtime-preview` | $0.60 | $2.40 | — | — | — | USD |
| `gpt-4o-mini-realtime-preview-2024-12-17` | $0.60 | $2.40 | — | — | — | USD |
| `gpt-realtime-mini` | $0.60 | $2.40 | — | — | — | USD |
| `gpt-realtime-mini-2025-10-06` | $0.60 | $2.40 | — | — | — | USD |
| `gpt-realtime-mini-2025-12-15` | $0.60 | $2.40 | — | — | — | USD |
| `gpt-3.5-turbo` | $0.50 | $1.50 | — | — | — | USD |
| `gpt-3.5-turbo-0125` | $0.50 | $1.50 | — | — | — | USD |
| `gpt-4.1-mini` | $0.40 | $1.60 | — | $0.20 | $0.80 | USD |
| `gpt-4.1-mini-2025-04-14` | $0.40 | $1.60 | — | $0.20 | $0.80 | USD |
| `gpt-5.1-codex-mini` | $0.25 | $2.00 | — | — | — | USD |
| `gpt-5-mini` | $0.25 | $2.00 | — | — | — | USD |
| `gpt-5-mini-2025-08-07` | $0.25 | $2.00 | — | — | — | USD |
| `gpt-5.4-nano` | $0.20 | $1.25 | $0.020 | $0.10 | $0.62 | USD |
| `gpt-4o-mini-search-preview` | $0.15 | $0.60 | — | $0.075 | $0.30 | USD |
| `gpt-4o-mini` | $0.15 | $0.60 | — | $0.075 | $0.30 | USD |
| `gpt-4o-mini-2024-07-18` | $0.15 | $0.60 | — | $0.075 | $0.30 | USD |
| `gpt-4o-mini-audio-preview` | $0.15 | $0.60 | — | — | — | USD |
| `gpt-4o-mini-audio-preview-2024-12-17` | $0.15 | $0.60 | — | — | — | USD |
| `gpt-4o-mini-search-preview-2025-03-11` | $0.15 | $0.60 | — | $0.075 | $0.30 | USD |
| `gpt-oss-120b-maas` | $0.15 | $0.60 | — | — | — | USD |
| `text-embedding-3-large` | $0.13 | free | — | $0.065 | free | USD |
| `gpt-4.1-nano` | $0.10 | $0.40 | — | $0.050 | $0.20 | USD |
| `gpt-4.1-nano-2025-04-14` | $0.10 | $0.40 | — | $0.050 | $0.20 | USD |
| `text-embedding-004` | $0.10 | free | — | — | — | USD |
| `text-embedding-005` | $0.10 | free | — | — | — | USD |
| `text-embedding-ada-002` | $0.10 | free | — | — | — | USD |
| `text-embedding-ada-002-v2` | $0.10 | free | — | $0.050 | free | USD |
| `text-embedding-large-exp-03-07` | $0.10 | free | — | — | — | USD |
| `gpt-oss-safeguard-20b` | $0.075 | $0.30 | — | — | — | USD |
| `gpt-oss-20b-maas` | $0.075 | $0.30 | — | — | — | USD |
| `gpt-5-nano` | $0.050 | $0.40 | — | — | — | USD |
| `gpt-5-nano-2025-08-07` | $0.050 | $0.40 | — | — | — | USD |
| `gpt-oss-20b` | $0.040 | $0.15 | — | — | — | USD |
| `text-embedding-3-small` | $0.020 | free | — | $0.010 | free | USD |
| `text-embedding-preview-0409` | $0.0063 | free | — | — | — | USD |
| `gpt-oss-120b:free` | free | free | — | — | — | USD |
| `gpt-oss-20b:free` | free | free | — | — | — | USD |
| `gpt-oss-20b-mxfp4-GGUF` | free | free | — | — | — | USD |
| `gpt-oss-120b-mxfp-GGUF` | free | free | — | — | — | USD |
| `gpt-oss:120b-cloud` | free | free | — | — | — | USD |
| `gpt-oss:20b-cloud` | free | free | — | — | — | USD |

## Google

| Model | Input | Output | Cache Read | Batch In | Batch Out | Currency |
|-------|------:|-------:|----------:|---------:|----------:|---------|
| `gemini-3-pro-image-preview` | $2.00 | $12.00 | — | $1.00 | $6.00 | USD |
| `gemini-3.1-pro-preview-customtools` | $2.00 | $12.00 | — | $1.00 | $6.00 | USD |
| `gemini-3.1-pro-preview` | $2.00 | $12.00 | $0.20 | $1.00 | $6.00 | USD |
| `gemini-3-pro-preview` | $2.00 | $12.00 | — | $1.00 | $6.00 | USD |
| `gemini-3-pro` | $2.00 | $12.00 | — | — | — | USD |
| `gemini-2.5-pro` | $1.25 | $10.00 | $0.12 | — | — | USD |
| `gemini-2.5-pro-preview` | $1.25 | $10.00 | — | — | — | USD |
| `gemini-2.5-pro-preview-05-06` | $1.25 | $10.00 | — | — | — | USD |
| `gemini-2.5-computer-use-preview` | $1.25 | $10.00 | — | — | — | USD |
| `gemini-2.5-computer-use-preview-10-2025` | $1.25 | $10.00 | — | — | — | USD |
| `gemini-pro-latest` | $1.25 | $10.00 | — | — | — | USD |
| `gemini-2.5-pro-preview-tts` | $1.00 | — | — | — | — | USD |
| `gemini-3.1-flash-live-preview` | $0.75 | $4.50 | — | — | — | USD |
| `gemini-3.1-flash-image-preview` | $0.50 | $3.00 | — | $0.25 | $1.50 | USD |
| `gemini-2.5-flash-preview-tts` | $0.50 | — | — | — | — | USD |
| `gemini-3-flash-preview` | $0.50 | $3.00 | $0.050 | — | — | USD |
| `gemini-2.5-flash-native-audio` | $0.50 | $2.00 | — | — | — | USD |
| `gemini-gemma-2-27b-it` | $0.35 | $1.05 | — | — | — | USD |
| `gemini-gemma-2-9b-it` | $0.35 | $1.05 | — | — | — | USD |
| `gemini-2.5-flash-image` | $0.30 | $2.50 | — | $0.15 | $1.25 | USD |
| `gemini-2.5-flash` | $0.30 | $2.50 | $0.030 | — | — | USD |
| `gemini-2.5-flash-preview-09-2025` | $0.30 | $2.50 | — | — | — | USD |
| `gemini-live-2.5-flash-preview-native-audio-09-2025` | $0.30 | $2.00 | — | — | — | USD |
| `gemini-robotics-er-1.5-preview` | $0.30 | $2.50 | — | — | — | USD |
| `gemini-flash-latest` | $0.30 | $2.50 | — | — | — | USD |
| `gemini-exp-1206` | $0.30 | $2.50 | — | — | — | USD |
| `gemini-2.5-flash-native-audio-latest` | $0.30 | $2.50 | — | — | — | USD |
| `gemini-2.5-flash-native-audio-preview-09-2025` | $0.30 | $2.50 | — | — | — | USD |
| `gemini-2.5-flash-native-audio-preview-12-2025` | $0.30 | $2.50 | — | — | — | USD |
| `gemini-3.1-flash-lite-preview` | $0.25 | $1.50 | $0.025 | — | — | USD |
| `gemini-embedding-2-preview` | $0.20 | free | — | — | — | USD |
| `gemini-embedding-001` | $0.15 | free | — | — | — | USD |
| `gemini-2.5-flash-lite-preview-09-2025` | $0.10 | $0.40 | — | — | — | USD |
| `gemini-2.5-flash-lite` | $0.10 | $0.40 | $0.010 | — | — | USD |
| `gemini-2.0-flash-001` | $0.10 | $0.40 | — | — | — | USD |
| `gemini-2.5-flash-lite-preview` | $0.10 | $0.40 | $0.010 | — | — | USD |
| `gemini-2.0-flash` | $0.10 | $0.40 | $0.025 | — | — | USD |
| `gemini-2.5-flash-lite-preview-06-17` | $0.10 | $0.40 | — | — | — | USD |
| `gemini-flash-lite-latest` | $0.10 | $0.40 | — | — | — | USD |
| `gemini-2.0-flash-lite-001` | $0.075 | $0.30 | — | — | — | USD |
| `gemini-2.0-flash-lite` | $0.075 | $0.30 | — | — | — | USD |
| `gemini-1.5-flash` | $0.075 | free | — | — | — | USD |
| `gemini-flash-experimental` | free | free | — | — | — | USD |
| `gemini-exp-1114` | free | free | — | — | — | USD |
| `gemini-2.0-flash-exp-image-generation` | free | free | — | — | — | USD |

## DeepSeek

| Model | Input | Output | Cache Read | Batch In | Batch Out | Currency |
|-------|------:|-------:|----------:|---------:|----------:|---------|
| `DeepSeek-R1-0528` | $135000.00 | $540000.00 | — | — | — | USD |
| `DeepSeek-V3-0324` | $114000.00 | $275000.00 | — | — | — | USD |
| `DeepSeek-V3.1` | $55000.00 | $165000.00 | — | — | — | USD |
| `DeepSeek-R1` | $3.00 | $7.00 | — | — | — | USD |
| `deepseek-v3.1-maas` | $1.35 | $5.40 | — | — | — | USD |
| `deepseek-r1-0528-maas` | $1.35 | $5.40 | — | — | — | USD |
| `DeepSeek-V3` | $1.25 | $1.25 | — | — | — | USD |
| `DeepSeek-R1-0528-Turbo` | $1.00 | $3.00 | — | — | — | USD |
| `DeepSeek-R1-Turbo` | $1.00 | $3.00 | — | — | — | USD |
| `deepseek-r1-distill-llama-70b` | $0.99 | $0.99 | — | — | — | USD |
| `deepseek-r1-671b` | $0.80 | $0.80 | — | — | — | USD |
| `deepseek-prover-v2-671b` | $0.70 | $2.50 | — | — | — | USD |
| `deepseek-r1-turbo` | $0.70 | $2.50 | — | — | — | USD |
| `deepseek-v3.1` | $0.67 | $2.02 | — | — | — | USD |
| `deepseek-v3.2-maas` | $0.56 | $1.68 | — | $0.28 | $0.84 | USD |
| `deepseek-r1` | $0.55 | $2.19 | — | — | — | USD |
| `DeepSeek-R1-0528-tput` | $0.55 | $2.19 | — | — | — | USD |
| `deepseek-v3.2-speciale` | $0.40 | $1.20 | — | — | — | USD |
| `deepseek-v3-turbo` | $0.40 | $1.30 | — | — | — | USD |
| `deepseek-r1t2-chimera` | $0.30 | $1.10 | — | — | — | USD |
| `deepseek-r1-distill-qwen-32b` | $0.30 | $0.30 | — | — | — | USD |
| `deepseek-chat` | $0.28 | $0.42 | $0.028 | — | — | USD |
| `deepseek-reasoner` | $0.28 | $0.42 | $0.028 | — | — | USD |
| `deepseek-v3.2` | $0.28 | $0.40 | — | — | — | USD |
| `DeepSeek-V3.2` | $0.28 | $0.40 | — | — | — | USD |
| `deepseek-v3.2-exp` | $0.27 | $0.41 | — | — | — | USD |
| `deepseek-v3.1-terminus` | $0.27 | $1.00 | — | — | — | USD |
| `DeepSeek-V3.1-Terminus` | $0.27 | $1.00 | — | — | — | USD |
| `deepseek-v3` | $0.27 | $1.10 | — | — | — | USD |
| `DeepSeek-R1-Distill-Llama-70B` | $0.25 | $0.75 | — | — | — | USD |
| `deepseek-chat-v3.1` | $0.20 | $0.80 | — | — | — | USD |
| `deepseek-r1-0528` | $0.20 | $0.60 | — | — | — | USD |
| `deepseek-llama3.3-70b` | $0.20 | $0.60 | — | — | — | USD |
| `deepseek-v3-0324` | $0.20 | $0.60 | — | — | — | USD |
| `DeepSeek-R1-Distill-Qwen-7B` | $0.20 | $0.20 | — | — | — | USD |
| `DeepSeek-R1-Distill-Qwen-32B` | $0.15 | $0.15 | — | — | — | USD |
| `deepseek-r1-distill-qwen-14b` | $0.15 | $0.15 | — | — | — | USD |
| `deepseek-chat-v3-0324` | $0.14 | $0.28 | — | — | — | USD |
| `deepseek-coder` | $0.14 | $0.28 | — | — | — | USD |
| `deepseek-v3.1-nex-n1` | $0.14 | $0.50 | — | — | — | USD |
| `deepseek-r1-8b` | $0.10 | $0.20 | — | — | — | USD |
| `DeepSeek-R1-Distill-Qwen-1.5B` | $0.090 | $0.090 | — | — | — | USD |
| `deepseek-r1-7b-qwen` | $0.080 | $0.15 | — | — | — | USD |
| `DeepSeek-R1-Distill-Qwen-14B` | $0.070 | $0.070 | — | — | — | USD |
| `deepseek-r1-0528-qwen3-8b` | $0.060 | $0.090 | — | — | — | USD |
| `deepseek-coder-6.7b` | $0.060 | $0.12 | — | — | — | USD |
| `deepseek-ocr` | $0.030 | $0.030 | — | — | — | USD |
| `DeepSeek-R1-Distill-Llama-8B` | $0.025 | $0.025 | — | — | — | USD |
| `deepseek-v3-2-251201` | free | free | — | — | — | USD |
| `deepseek-coder-v2-base` | free | free | — | — | — | USD |
| `deepseek-coder-v2-instruct` | free | free | — | — | — | USD |
| `deepseek-coder-v2-lite-base` | free | free | — | — | — | USD |
| `deepseek-coder-v2-lite-instruct` | free | free | — | — | — | USD |
| `deepseek-v3.1:671b-cloud` | free | free | — | — | — | USD |

## Zhipu AI (智谱)

| Model | Input | Output | Cache Read | Batch In | Batch Out | Currency |
|-------|------:|-------:|----------:|---------:|----------:|---------|
| `GLM-4.5` | $55000.00 | $200000.00 | $27500.00 | — | — | USD |
| `glm-4-airx` | ¥10.00 | ¥10.00 | ¥5.00 | — | — | CNY |
| `glm-4-plus` | ¥5.00 | ¥5.00 | ¥2.50 | ¥2.50 | ¥2.50 | CNY |
| `glm-4-assistant` | ¥5.00 | ¥5.00 | ¥2.50 | — | — | CNY |
| `glm-z1-airx` | ¥5.00 | ¥5.00 | ¥2.50 | — | — | CNY |
| `glm-4.5-x` | $2.20 | $8.90 | $1.10 | — | — | USD |
| `glm-5-turbo` | $1.20 | $4.00 | $0.60 | — | — | USD |
| `glm-5-code` | $1.20 | $5.00 | $0.60 | — | — | USD |
| `glm-4.5-airx` | $1.10 | $4.50 | $0.55 | — | — | USD |
| `glm-4-long` | ¥1.00 | ¥1.00 | ¥0.50 | ¥0.50 | ¥0.50 | CNY |
| `glm-5-maas` | $1.00 | $3.20 | $0.50 | — | — | USD |
| `glm-5` | $0.80 | $2.56 | $0.40 | — | — | USD |
| `glm-4.5v` | $0.60 | $1.80 | $0.30 | — | — | USD |
| `glm-4.5` | $0.60 | $2.20 | $0.30 | — | — | USD |
| `glm-4p7` | $0.60 | $2.20 | $0.30 | — | — | USD |
| `GLM-4.6` | $0.60 | $2.20 | $0.30 | — | — | USD |
| `glm-4.7-maas` | $0.60 | $2.20 | $0.30 | — | — | USD |
| `glm-4.7-flashx` | ¥0.50 | ¥3.00 | ¥0.25 | — | — | CNY |
| `glm-4-air-250414` | ¥0.50 | ¥0.50 | ¥0.25 | ¥0.25 | ¥0.25 | CNY |
| `glm-z1-air` | ¥0.50 | ¥0.50 | ¥0.25 | — | — | CNY |
| `glm-4.6:exacto` | $0.45 | $1.90 | $0.23 | — | — | USD |
| `GLM-4.7` | $0.45 | $2.00 | $0.23 | — | — | USD |
| `glm-4.7` | $0.40 | $1.50 | $0.20 | — | — | USD |
| `glm-4.6` | $0.40 | $1.75 | $0.20 | — | — | USD |
| `GLM-4.7-FP8` | $0.40 | $2.00 | $0.20 | — | — | USD |
| `glm-4.6v` | $0.30 | $0.90 | $0.15 | — | — | USD |
| `glm-4.5-air` | $0.20 | $1.10 | $0.10 | — | — | USD |
| `GLM-4.5-Air-FP8` | $0.20 | $1.10 | $0.10 | — | — | USD |
| `glm-z1-flashx` | ¥0.10 | ¥0.10 | ¥0.050 | — | — | CNY |
| `glm-4-flashx-250414` | ¥0.10 | ¥0.10 | ¥0.050 | ¥0.050 | ¥0.050 | CNY |
| `glm-4-32b` | $0.10 | $0.10 | $0.050 | — | — | USD |
| `glm-4-32b-0414-128k` | $0.10 | $0.10 | $0.050 | — | — | USD |
| `glm-4.7-flash` | $0.070 | $0.40 | $0.035 | — | — | USD |
| `glm-4-flash-250414` | free | free | — | — | — | CNY |
| `glm-z1-flash` | free | free | — | — | — | CNY |
| `glm-4.5-air:free` | free | free | — | — | — | USD |
| `glm-4-7-251222` | free | free | — | — | — | USD |
| `glm-4.5-flash` | free | free | — | — | — | USD |

## Mistral

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `mistral/mistral-7b-instruct-v0.1` | $1.92 | $1.92 | USD |

## Moonshot AI (月之暗面)

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `moonshot-v1-128k` | $2.00 | $5.00 | USD |
| `moonshot-v1-128k-0430` | $2.00 | $5.00 | USD |
| `moonshot-v1-128k-vision-preview` | $2.00 | $5.00 | USD |
| `moonshot-v1-auto` | $2.00 | $5.00 | USD |
| `moonshot-v1-32k` | $1.00 | $3.00 | USD |
| `moonshot-v1-32k-0430` | $1.00 | $3.00 | USD |
| `moonshot-v1-32k-vision-preview` | $1.00 | $3.00 | USD |
| `moonshot-v1-8k` | $0.20 | $2.00 | USD |
| `moonshot-v1-8k-0430` | $0.20 | $2.00 | USD |
| `moonshot-v1-8k-vision-preview` | $0.20 | $2.00 | USD |

## Aliyun

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `qwen-max` | $1.60 | $6.40 | USD |
| `qwen-vl-max` | $0.52 | $2.08 | USD |
| `qwen-plus` | $0.40 | $1.20 | USD |
| `qwen-3-32b` | $0.40 | $0.80 | USD |
| `qwen-plus-2025-01-25` | $0.40 | $1.20 | USD |
| `qwen-plus-2025-04-28` | $0.40 | $1.20 | USD |
| `qwen-plus-2025-07-14` | $0.40 | $1.20 | USD |
| `qwen-2.5-72b-instruct` | $0.38 | $0.40 | USD |
| `qwen-coder` | $0.30 | $1.50 | USD |
| `qwen-plus-2025-07-28:thinking` | $0.26 | $0.78 | USD |
| `qwen-plus-2025-07-28` | $0.26 | $0.78 | USD |
| `qwen-mt-plus` | $0.25 | $0.75 | USD |
| `qwen-vl-plus` | $0.21 | $0.63 | USD |
| `qwen-3-235b` | $0.20 | $0.60 | USD |
| `qwen-2.5-coder-32b-instruct` | $0.18 | $0.18 | USD |
| `qwen-3-30b` | $0.10 | $0.30 | USD |
| `qwen-3-14b` | $0.080 | $0.24 | USD |
| `qwen-turbo` | $0.050 | $0.20 | USD |
| `qwen-turbo-2024-11-01` | $0.050 | $0.20 | USD |
| `qwen-turbo-2025-04-28` | $0.050 | $0.20 | USD |
| `qwen-turbo-latest` | $0.050 | $0.20 | USD |
| `qwen-2.5-7b-instruct` | $0.040 | $0.10 | USD |
| `Qwen-SEA-LION-v4-32B-IT` | free | free | USD |

## Baidu

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `ernie-4.5-vl-424b-a47b` | $0.42 | $1.25 | USD |
| `ernie-4.5-vl-28b-a3b-thinking` | $0.39 | $0.39 | USD |
| `ernie-4.5-300b-a47b` | $0.28 | $1.10 | USD |
| `ernie-4.5-300b-a47b-paddle` | $0.28 | $1.10 | USD |
| `ernie-4.5-vl-28b-a3b` | $0.14 | $0.56 | USD |
| `ernie-4.5-21b-a3b-thinking` | $0.070 | $0.28 | USD |
| `ernie-4.5-21b-a3b` | $0.070 | $0.28 | USD |
| `ernie-4.5-21B-a3b-thinking` | $0.070 | $0.28 | USD |
| `ernie-4.5-21B-a3b` | $0.070 | $0.28 | USD |

## Fireworks

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `fireworks/models/deepseek-r1` | $3.00 | $8.00 | USD |
| `fireworks/models/deepseek-r1-0528` | $3.00 | $8.00 | USD |
| `fireworks/models/llama-v3p1-405b-instruct` | $3.00 | $3.00 | USD |
| `fireworks/models/yi-large` | $3.00 | $3.00 | USD |
| `fireworks/models/deepseek-coder-v2-instruct` | $1.20 | $1.20 | USD |
| `fireworks/models/mixtral-8x22b-instruct-hf` | $1.20 | $1.20 | USD |
| `fireworks/models/cogito-671b-v2-p1` | $1.20 | $1.20 | USD |
| `fireworks/models/dbrx-instruct` | $1.20 | $1.20 | USD |
| `fireworks/models/deepseek-prover-v2` | $1.20 | $1.20 | USD |
| `fireworks/models/deepseek-v2p5` | $1.20 | $1.20 | USD |
| `fireworks/models/glm-4p5v` | $1.20 | $1.20 | USD |
| `fireworks/models/gpt-oss-safeguard-120b` | $1.20 | $1.20 | USD |
| `fireworks/models/mistral-large-3-fp8` | $1.20 | $1.20 | USD |
| `fireworks/models/mixtral-8x22b` | $1.20 | $1.20 | USD |
| `fireworks/models/mixtral-8x22b-instruct` | $1.20 | $1.20 | USD |
| `fireworks/models/deepseek-v3` | $0.90 | $0.90 | USD |
| `fireworks/models/deepseek-v3-0324` | $0.90 | $0.90 | USD |
| `fireworks/models/firefunction-v2` | $0.90 | $0.90 | USD |
| `fireworks/models/llama-v3p2-90b-vision-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2-72b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-coder-32b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/code-llama-34b` | $0.90 | $0.90 | USD |
| `fireworks/models/code-llama-34b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/code-llama-34b-python` | $0.90 | $0.90 | USD |
| `fireworks/models/code-llama-70b` | $0.90 | $0.90 | USD |
| `fireworks/models/code-llama-70b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/code-llama-70b-python` | $0.90 | $0.90 | USD |
| `fireworks/models/cogito-v1-preview-llama-70b` | $0.90 | $0.90 | USD |
| `fireworks/models/cogito-v1-preview-qwen-32b` | $0.90 | $0.90 | USD |
| `fireworks/models/deepseek-coder-33b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/deepseek-r1-distill-llama-70b` | $0.90 | $0.90 | USD |
| `fireworks/models/deepseek-r1-distill-qwen-32b` | $0.90 | $0.90 | USD |
| `fireworks/models/devstral-small-2505` | $0.90 | $0.90 | USD |
| `fireworks/models/dobby-unhinged-llama-3-3-70b-new` | $0.90 | $0.90 | USD |
| `fireworks/models/dolphin-2-9-2-qwen2-72b` | $0.90 | $0.90 | USD |
| `fireworks/models/fare-20b` | $0.90 | $0.90 | USD |
| `fireworks/models/gemma-3-27b-it` | $0.90 | $0.90 | USD |
| `fireworks/models/internvl3-38b` | $0.90 | $0.90 | USD |
| `fireworks/models/internvl3-78b` | $0.90 | $0.90 | USD |
| `fireworks/models/kat-coder` | $0.90 | $0.90 | USD |
| `fireworks/models/kat-dev-32b` | $0.90 | $0.90 | USD |
| `fireworks/models/kat-dev-72b-exp` | $0.90 | $0.90 | USD |
| `fireworks/models/llama-v2-70b-chat` | $0.90 | $0.90 | USD |
| `fireworks/models/llama-v3-70b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/llama-v3-70b-instruct-hf` | $0.90 | $0.90 | USD |
| `fireworks/models/llama-v3p1-70b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/llama-v3p1-nemotron-70b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/llama-v3p3-70b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/llava-yi-34b` | $0.90 | $0.90 | USD |
| `fireworks/models/mistral-small-24b-instruct-2501` | $0.90 | $0.90 | USD |
| `fireworks/models/nous-hermes-2-yi-34b` | $0.90 | $0.90 | USD |
| `fireworks/models/nous-hermes-llama2-70b` | $0.90 | $0.90 | USD |
| `fireworks/models/phind-code-llama-34b-python-v1` | $0.90 | $0.90 | USD |
| `fireworks/models/phind-code-llama-34b-v1` | $0.90 | $0.90 | USD |
| `fireworks/models/phind-code-llama-34b-v2` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen-qwq-32b-preview` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen1p5-72b-chat` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2-vl-72b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-32b` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-32b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-72b` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-72b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-coder-32b` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-coder-32b-instruct-128k` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-coder-32b-instruct-32k-rope` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-coder-32b-instruct-64k` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-math-72b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-vl-32b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen2p5-vl-72b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen3-30b-a3b-thinking-2507` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen3-32b` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen3-coder-480b-instruct-bf16` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen3-next-80b-a3b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen3-next-80b-a3b-thinking` | $0.90 | $0.90 | USD |
| `fireworks/models/qwen3-vl-32b-instruct` | $0.90 | $0.90 | USD |
| `fireworks/models/qwq-32b` | $0.90 | $0.90 | USD |
| `fireworks/models/yi-34b` | $0.90 | $0.90 | USD |
| `fireworks/models/yi-34b-200k-capybara` | $0.90 | $0.90 | USD |
| `fireworks/models/yi-34b-chat` | $0.90 | $0.90 | USD |
| `fireworks/models/glm-4p7` | $0.60 | $2.20 | USD |
| `fireworks/models/kimi-k2-instruct` | $0.60 | $2.50 | USD |
| `fireworks/models/kimi-k2-instruct-0905` | $0.60 | $2.50 | USD |
| `fireworks/models/kimi-k2-thinking` | $0.60 | $2.50 | USD |
| `fireworks/models/kimi-k2p5` | $0.60 | $3.00 | USD |
| `fireworks/models/deepseek-v3p1` | $0.56 | $1.68 | USD |
| `fireworks/models/deepseek-v3p1-terminus` | $0.56 | $1.68 | USD |
| `fireworks/models/deepseek-v3p2` | $0.56 | $1.68 | USD |
| `fireworks/models/deepseek-r1-basic` | $0.55 | $2.19 | USD |
| `fireworks/models/glm-4p5` | $0.55 | $2.19 | USD |
| `fireworks/models/glm-4p6` | $0.55 | $2.19 | USD |
| `fireworks/models/deepseek-coder-v2-lite-base` | $0.50 | $0.50 | USD |
| `fireworks/models/deepseek-coder-v2-lite-instruct` | $0.50 | $0.50 | USD |
| `fireworks/models/deepseek-v2-lite-chat` | $0.50 | $0.50 | USD |
| `fireworks/models/dolphin-2p6-mixtral-8x7b` | $0.50 | $0.50 | USD |
| `fireworks/models/firefunction-v1` | $0.50 | $0.50 | USD |
| `fireworks/models/gpt-oss-safeguard-20b` | $0.50 | $0.50 | USD |
| `fireworks/models/mixtral-8x7b` | $0.50 | $0.50 | USD |
| `fireworks/models/mixtral-8x7b-instruct` | $0.50 | $0.50 | USD |
| `fireworks/models/mixtral-8x7b-instruct-hf` | $0.50 | $0.50 | USD |
| `fireworks/models/nous-hermes-2-mixtral-8x7b-dpo` | $0.50 | $0.50 | USD |
| `fireworks/models/qwen3-30b-a3b-instruct-2507` | $0.50 | $0.50 | USD |
| `fireworks/models/qwen3-coder-480b-a35b-instruct` | $0.45 | $1.80 | USD |
| `fireworks/models/minimax-m2p1` | $0.30 | $1.20 | USD |
| `fireworks/models/minimax-m2` | $0.30 | $1.20 | USD |
| `fireworks/models/glm-4p5-air` | $0.22 | $0.88 | USD |
| `fireworks/models/llama4-maverick-instruct-basic` | $0.22 | $0.88 | USD |
| `fireworks/models/qwen3-235b-a22b` | $0.22 | $0.88 | USD |
| `fireworks/models/qwen3-235b-a22b-instruct-2507` | $0.22 | $0.88 | USD |
| `fireworks/models/qwen3-235b-a22b-thinking-2507` | $0.22 | $0.88 | USD |
| `fireworks/models/qwen3-vl-235b-a22b-instruct` | $0.22 | $0.88 | USD |
| `fireworks/models/qwen3-vl-235b-a22b-thinking` | $0.22 | $0.88 | USD |
| `fireworks/models/llama-v3p2-11b-vision-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/chronos-hermes-13b-v2` | $0.20 | $0.20 | USD |
| `fireworks/models/code-llama-13b` | $0.20 | $0.20 | USD |
| `fireworks/models/code-llama-13b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/code-llama-13b-python` | $0.20 | $0.20 | USD |
| `fireworks/models/code-llama-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/code-llama-7b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/code-llama-7b-python` | $0.20 | $0.20 | USD |
| `fireworks/models/code-qwen-1p5-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/codegemma-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/cogito-v1-preview-llama-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/cogito-v1-preview-qwen-14b` | $0.20 | $0.20 | USD |
| `fireworks/models/deepseek-coder-7b-base` | $0.20 | $0.20 | USD |
| `fireworks/models/deepseek-coder-7b-base-v1p5` | $0.20 | $0.20 | USD |
| `fireworks/models/deepseek-coder-7b-instruct-v1p5` | $0.20 | $0.20 | USD |
| `fireworks/models/deepseek-r1-0528-distill-qwen3-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/deepseek-r1-distill-llama-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/deepseek-r1-distill-qwen-14b` | $0.20 | $0.20 | USD |
| `fireworks/models/deepseek-r1-distill-qwen-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/dobby-mini-unhinged-plus-llama-3-1-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/firellava-13b` | $0.20 | $0.20 | USD |
| `fireworks/models/firesearch-ocr-v6` | $0.20 | $0.20 | USD |
| `fireworks/models/gemma-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/gemma-7b-it` | $0.20 | $0.20 | USD |
| `fireworks/models/gemma2-9b-it` | $0.20 | $0.20 | USD |
| `fireworks/models/hermes-2-pro-mistral-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/internvl3-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/llama-guard-2-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/llama-guard-3-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/llama-v2-13b` | $0.20 | $0.20 | USD |
| `fireworks/models/llama-v2-13b-chat` | $0.20 | $0.20 | USD |
| `fireworks/models/llama-v2-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/llama-v2-7b-chat` | $0.20 | $0.20 | USD |
| `fireworks/models/llama-v3-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/llama-v3-8b-instruct-hf` | $0.20 | $0.20 | USD |
| `fireworks/models/llamaguard-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/ministral-3-14b-instruct-2512` | $0.20 | $0.20 | USD |
| `fireworks/models/ministral-3-8b-instruct-2512` | $0.20 | $0.20 | USD |
| `fireworks/models/mistral-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/mistral-7b-instruct-4k` | $0.20 | $0.20 | USD |
| `fireworks/models/mistral-7b-instruct-v0p2` | $0.20 | $0.20 | USD |
| `fireworks/models/mistral-7b-instruct-v3` | $0.20 | $0.20 | USD |
| `fireworks/models/mistral-7b-v0p2` | $0.20 | $0.20 | USD |
| `fireworks/models/mistral-nemo-base-2407` | $0.20 | $0.20 | USD |
| `fireworks/models/mistral-nemo-instruct-2407` | $0.20 | $0.20 | USD |
| `fireworks/models/mythomax-l2-13b` | $0.20 | $0.20 | USD |
| `fireworks/models/nous-capybara-7b-v1p9` | $0.20 | $0.20 | USD |
| `fireworks/models/nous-hermes-llama2-13b` | $0.20 | $0.20 | USD |
| `fireworks/models/nous-hermes-llama2-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/nvidia-nemotron-nano-12b-v2` | $0.20 | $0.20 | USD |
| `fireworks/models/nvidia-nemotron-nano-9b-v2` | $0.20 | $0.20 | USD |
| `fireworks/models/openchat-3p5-0106-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/openhermes-2-mistral-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/openhermes-2p5-mistral-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/openorca-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/phi-3-vision-128k-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/pythia-12b` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen-v2p5-14b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen-v2p5-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2-7b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2-vl-7b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2p5-14b` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2p5-7b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2p5-coder-14b` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2p5-coder-14b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2p5-coder-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2p5-coder-7b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2p5-vl-3b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen2p5-vl-7b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen3-14b` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen3-4b` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen3-4b-instruct-2507` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen3-8b` | $0.20 | $0.20 | USD |
| `fireworks/models/qwen3-vl-8b-instruct` | $0.20 | $0.20 | USD |
| `fireworks/models/rolm-ocr` | $0.20 | $0.20 | USD |
| `fireworks/models/snorkel-mistral-7b-pairrm-dpo` | $0.20 | $0.20 | USD |
| `fireworks/models/starcoder-16b` | $0.20 | $0.20 | USD |
| `fireworks/models/starcoder-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/starcoder2-15b` | $0.20 | $0.20 | USD |
| `fireworks/models/starcoder2-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/toppy-m-7b` | $0.20 | $0.20 | USD |
| `fireworks/models/yi-6b` | $0.20 | $0.20 | USD |
| `fireworks/models/zephyr-7b-beta` | $0.20 | $0.20 | USD |
| `fireworks/models/gpt-oss-120b` | $0.15 | $0.60 | USD |
| `fireworks/models/llama4-scout-instruct-basic` | $0.15 | $0.60 | USD |
| `fireworks/models/qwen3-30b-a3b` | $0.15 | $0.60 | USD |
| `fireworks/models/qwen3-coder-30b-a3b-instruct` | $0.15 | $0.60 | USD |
| `fireworks/models/qwen3-vl-30b-a3b-instruct` | $0.15 | $0.60 | USD |
| `fireworks/models/qwen3-vl-30b-a3b-thinking` | $0.15 | $0.60 | USD |
| `fireworks/models/llama-v3p1-8b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/llama-v3p2-1b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/llama-v3p2-3b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/codegemma-2b` | $0.10 | $0.10 | USD |
| `fireworks/models/cogito-v1-preview-llama-3b` | $0.10 | $0.10 | USD |
| `fireworks/models/deepseek-coder-1b-base` | $0.10 | $0.10 | USD |
| `fireworks/models/deepseek-r1-distill-qwen-1p5b` | $0.10 | $0.10 | USD |
| `fireworks/models/ernie-4p5-21b-a3b-pt` | $0.10 | $0.10 | USD |
| `fireworks/models/ernie-4p5-300b-a47b-pt` | $0.10 | $0.10 | USD |
| `fireworks/models/flux-1-dev` | $0.10 | $0.10 | USD |
| `fireworks/models/flux-1-schnell` | $0.10 | $0.10 | USD |
| `fireworks/models/gemma-2b-it` | $0.10 | $0.10 | USD |
| `fireworks/models/llama-guard-3-1b` | $0.10 | $0.10 | USD |
| `fireworks/models/llama-v2-70b` | $0.10 | $0.10 | USD |
| `fireworks/models/llama-v3p1-405b-instruct-long` | $0.10 | $0.10 | USD |
| `fireworks/models/llama-v3p1-70b-instruct-1b` | $0.10 | $0.10 | USD |
| `fireworks/models/llama-v3p2-1b` | $0.10 | $0.10 | USD |
| `fireworks/models/llama-v3p2-3b` | $0.10 | $0.10 | USD |
| `fireworks/models/minimax-m1-80k` | $0.10 | $0.10 | USD |
| `fireworks/models/ministral-3-3b-instruct-2512` | $0.10 | $0.10 | USD |
| `fireworks/models/nemotron-nano-v2-12b-vl` | $0.10 | $0.10 | USD |
| `fireworks/models/phi-2-3b` | $0.10 | $0.10 | USD |
| `fireworks/models/phi-3-mini-128k-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2-vl-2b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2p5-0p5b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2p5-1p5b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2p5-coder-0p5b` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2p5-coder-0p5b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2p5-coder-1p5b` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2p5-coder-1p5b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2p5-coder-3b` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen2p5-coder-3b-instruct` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen3-0p6b` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen3-1p7b` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen3-1p7b-fp8-draft` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen3-1p7b-fp8-draft-131072` | $0.10 | $0.10 | USD |
| `fireworks/models/qwen3-1p7b-fp8-draft-40960` | $0.10 | $0.10 | USD |
| `fireworks/models/` | $0.10 | free | USD |
| `fireworks/models/stablecode-3b` | $0.10 | $0.10 | USD |
| `fireworks/models/starcoder2-3b` | $0.10 | $0.10 | USD |
| `fireworks/models/flux-kontext-max` | $0.080 | $0.080 | USD |
| `fireworks/models/gpt-oss-20b` | $0.050 | $0.20 | USD |
| `fireworks/models/flux-kontext-pro` | $0.040 | $0.040 | USD |
| `fireworks/models/flux-1-dev-controlnet-union` | $0.0010 | $0.0010 | USD |
| `fireworks/models/flux-1-dev-fp8` | $0.000500 | $0.000500 | USD |
| `fireworks/models/flux-1-schnell-fp8` | $0.000350 | $0.000350 | USD |
| `fireworks/models/SSD-1B` | $0.000130 | $0.000130 | USD |
| `fireworks/models/japanese-stable-diffusion-xl` | $0.000130 | $0.000130 | USD |
| `fireworks/models/playground-v2-1024px-aesthetic` | $0.000130 | $0.000130 | USD |
| `fireworks/models/playground-v2-5-1024px-aesthetic` | $0.000130 | $0.000130 | USD |
| `fireworks/models/stable-diffusion-xl-1024-v1-0` | $0.000130 | $0.000130 | USD |
| `fireworks/models/fireworks-asr-large` | free | free | USD |
| `fireworks/models/fireworks-asr-v2` | free | free | USD |
| `fireworks/models/qwen3-embedding-0p6b` | free | free | USD |
| `fireworks/models/qwen3-embedding-4b` | free | free | USD |
| `fireworks/models/qwen3-reranker-0p6b` | free | free | USD |
| `fireworks/models/qwen3-reranker-4b` | free | free | USD |
| `fireworks/models/qwen3-reranker-8b` | free | free | USD |
| `fireworks/models/whisper-v3` | free | free | USD |
| `fireworks/models/whisper-v3-turbo` | free | free | USD |

## Meta

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `meta/llama-2-7b-chat-fp16` | $1.92 | $1.92 | USD |
| `meta/llama-2-7b-chat-int8` | $1.92 | $1.92 | USD |

## NVIDIA

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `nvidia/llama-3.2-nv-rerankqa-1b-v2` | free | free | USD |

## Thebloke

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `thebloke/codellama-7b-instruct-awq` | $1.92 | $1.92 | USD |

## Unknown

| Model | Input | Output | Batch In | Batch Out | Currency |
|-------|------:|-------:|---------:|----------:|---------|
| `Qwen3-Coder-480B-A35B-Instruct` | $100000.00 | $150000.00 | — | — | USD |
| `Llama-3.3-70B-Instruct` | $71000.00 | $71000.00 | — | — | USD |
| `Llama-3.1-8B-Instruct` | $22000.00 | $22000.00 | — | — | USD |
| `Llama-4-Scout-17B-16E-Instruct` | $17000.00 | $66000.00 | — | — | USD |
| `Qwen3-235B-A22B-Instruct-2507` | $10000.00 | $10000.00 | — | — | USD |
| `Qwen3-235B-A22B-Thinking-2507` | $10000.00 | $10000.00 | — | — | USD |
| `Phi-4-mini-instruct` | $8000.00 | $35000.00 | — | — | USD |
| `luminous-supreme-control` | $218.75 | $240.62 | — | — | USD |
| `luminous-supreme` | $175.00 | $192.50 | — | — | USD |
| `embed-multilingual-light-v3.0` | $100.00 | free | — | — | USD |
| `luminous-extended-control` | $56.25 | $61.88 | — | — | USD |
| `luminous-extended` | $45.00 | $49.50 | — | — | USD |
| `luminous-base-control` | $37.50 | $41.25 | — | — | USD |
| `ft:gpt-4-0613` | $30.00 | $60.00 | — | — | USD |
| `luminous-base` | $30.00 | $33.00 | — | — | USD |
| `databricks-claude-opus-4` | $15.00 | $75.00 | — | — | USD |
| `databricks-claude-opus-4-1` | $15.00 | $75.00 | — | — | USD |
| `o1` | $15.00 | $60.00 | — | — | USD |
| `anthropic-claude-3-opus` | $15.00 | $75.00 | — | — | USD |
| `j2-ultra` | $15.00 | $15.00 | — | — | USD |
| `v0-1.5-lg` | $15.00 | $75.00 | — | — | USD |
| `ft:davinci-002` | $12.00 | $12.00 | $1.00 | $1.00 | USD |
| `meta.llama-3.1-405b-instruct` | $10.68 | $10.68 | — | — | USD |
| `j2-mid` | $10.00 | $10.00 | — | — | USD |
| `text-unicorn` | $10.00 | $28.00 | — | — | USD |
| `text-unicorn@001` | $10.00 | $28.00 | — | — | USD |
| `mistral-large` | $8.00 | $24.00 | — | — | USD |
| `weaver` | $5.62 | $5.62 | — | — | USD |
| `databricks-claude-opus-4-5` | $5.00 | $25.00 | — | — | USD |
| `databricks-meta-llama-3-1-405b-instruct` | $5.00 | $15.00 | — | — | USD |
| `chatgpt-4o-latest` | $5.00 | $15.00 | — | — | USD |
| `xai.grok-3-fast` | $5.00 | $25.00 | — | — | USD |
| `grok-3-fast` | $5.00 | $25.00 | — | — | USD |
| `grok-3-fast-beta` | $5.00 | $25.00 | — | — | USD |
| `grok-3-fast-latest` | $5.00 | $25.00 | — | — | USD |
| `grok-beta` | $5.00 | $15.00 | — | — | USD |
| `grok-vision-beta` | $5.00 | $15.00 | — | — | USD |
| `aion-1.0` | $4.00 | $8.00 | — | — | USD |
| `ft:o4-mini-2025-04-16` | $4.00 | $16.00 | $2.00 | $8.00 | USD |
| `mistral-large-2402` | $4.00 | $12.00 | — | — | USD |
| `goliath-120b` | $3.75 | $7.50 | — | — | USD |
| `ft:gpt-4o-2024-08-06` | $3.75 | $15.00 | $1.88 | $7.50 | USD |
| `ft:gpt-4o-2024-11-20` | $3.75 | $15.00 | — | — | USD |
| `Meta-Llama-3.1-405B-Instruct-Turbo` | $3.50 | $3.50 | — | — | USD |
| `sonar-pro-search` | $3.00 | $15.00 | — | — | USD |
| `grok-4` | $3.00 | $15.00 | — | — | USD |
| `grok-3` | $3.00 | $15.00 | — | — | USD |
| `grok-3-beta` | $3.00 | $15.00 | — | — | USD |
| `sonar-pro` | $3.00 | $15.00 | — | — | USD |
| `l3.1-70b-hanami-x1` | $3.00 | $3.00 | — | — | USD |
| `mistral-large-2407` | $3.00 | $9.00 | — | — | USD |
| `magnum-v4-72b` | $3.00 | $5.00 | — | — | USD |
| `ft:gpt-3.5-turbo` | $3.00 | $6.00 | $1.50 | $3.00 | USD |
| `ft:gpt-3.5-turbo-0125` | $3.00 | $6.00 | — | — | USD |
| `ft:gpt-3.5-turbo-0613` | $3.00 | $6.00 | — | — | USD |
| `ft:gpt-3.5-turbo-1106` | $3.00 | $6.00 | — | — | USD |
| `ft:gpt-4.1-2025-04-14` | $3.00 | $12.00 | $1.50 | $6.00 | USD |
| `anthropic-claude-3.5-sonnet` | $3.00 | $15.00 | — | — | USD |
| `anthropic-claude-3.7-sonnet` | $3.00 | $15.00 | — | — | USD |
| `j2-light` | $3.00 | $3.00 | — | — | USD |
| `xai.grok-3` | $3.00 | $15.00 | — | — | USD |
| `xai.grok-4` | $3.00 | $15.00 | — | — | USD |
| `v0-1.0-md` | $3.00 | $15.00 | — | — | USD |
| `v0-1.5-md` | $3.00 | $15.00 | — | — | USD |
| `grok-3-latest` | $3.00 | $15.00 | — | — | USD |
| `grok-4-0709` | $3.00 | $15.00 | — | — | USD |
| `grok-4-latest` | $3.00 | $15.00 | — | — | USD |
| `databricks-claude-3-7-sonnet` | $3.00 | $15.00 | — | — | USD |
| `databricks-claude-sonnet-4` | $3.00 | $15.00 | — | — | USD |
| `databricks-claude-sonnet-4-1` | $3.00 | $15.00 | — | — | USD |
| `databricks-claude-sonnet-4-5` | $3.00 | $15.00 | — | — | USD |
| `mistral-medium` | $2.70 | $8.10 | — | — | USD |
| `mistral-medium-2312` | $2.70 | $8.10 | — | — | USD |
| `nova-premier-v1` | $2.50 | $12.50 | — | — | USD |
| `command-a` | $2.50 | $10.00 | — | — | USD |
| `inflection-3-productivity` | $2.50 | $10.00 | — | — | USD |
| `inflection-3-pi` | $2.50 | $10.00 | — | — | USD |
| `command-r-plus-08-2024` | $2.50 | $10.00 | — | — | USD |
| `command-a-03-2025` | $2.50 | $10.00 | — | — | USD |
| `command-r-plus` | $2.50 | $10.00 | — | — | USD |
| `zai-glm-4.6` | $2.25 | $2.75 | — | — | USD |
| `zai-glm-4.7` | $2.25 | $2.75 | — | — | USD |
| `qwen3-max` | $2.11 | $8.45 | — | — | USD |
| `grok-4.20-multi-agent-beta` | $2.00 | $6.00 | — | — | USD |
| `grok-4.20-beta` | $2.00 | $6.00 | — | — | USD |
| `jamba-large-1.7` | $2.00 | $8.00 | — | — | USD |
| `o3` | $2.00 | $8.00 | — | — | USD |
| `sonar-reasoning-pro` | $2.00 | $8.00 | — | — | USD |
| `sonar-deep-research` | $2.00 | $8.00 | — | — | USD |
| `mistral-large-2411` | $2.00 | $6.00 | — | — | USD |
| `pixtral-large-2411` | $2.00 | $6.00 | — | — | USD |
| `davinci-002` | $2.00 | $2.00 | — | — | USD |
| `deep-research-pro-preview-12-2025` | $2.00 | $12.00 | $1.00 | $6.00 | USD |
| `openai-o3` | $2.00 | $8.00 | — | — | USD |
| `jamba-1.5-large` | $2.00 | $8.00 | — | — | USD |
| `jamba-1.5-large@001` | $2.00 | $8.00 | — | — | USD |
| `jamba-large-1.6` | $2.00 | $8.00 | — | — | USD |
| `magistral-medium-2506` | $2.00 | $5.00 | — | — | USD |
| `magistral-medium-2509` | $2.00 | $5.00 | — | — | USD |
| `magistral-medium-1-2-2509` | $2.00 | $5.00 | — | — | USD |
| `magistral-medium-latest` | $2.00 | $5.00 | — | — | USD |
| `open-mixtral-8x22b` | $2.00 | $6.00 | — | — | USD |
| `pixtral-large-latest` | $2.00 | $6.00 | — | — | USD |
| `kimi-latest` | $2.00 | $5.00 | — | — | USD |
| `kimi-latest-128k` | $2.00 | $5.00 | — | — | USD |
| `meta.llama-3.2-90b-vision-instruct` | $2.00 | $2.00 | — | — | USD |
| `Qwen3-Coder-480B-A35B-Instruct-FP8` | $2.00 | $2.00 | — | — | USD |
| `magistral-medium` | $2.00 | $5.00 | — | — | USD |
| `pixtral-large` | $2.00 | $6.00 | — | — | USD |
| `grok-2` | $2.00 | $10.00 | — | — | USD |
| `grok-2-vision` | $2.00 | $10.00 | — | — | USD |
| `grok-2-1212` | $2.00 | $10.00 | — | — | USD |
| `grok-2-latest` | $2.00 | $10.00 | — | — | USD |
| `grok-2-vision-1212` | $2.00 | $10.00 | — | — | USD |
| `grok-2-vision-latest` | $2.00 | $10.00 | — | — | USD |
| `grok-4.20-multi-agent-beta-0309` | $2.00 | $6.00 | — | — | USD |
| `grok-4.20-beta-0309-reasoning` | $2.00 | $6.00 | — | — | USD |
| `grok-4.20-beta-0309-non-reasoning` | $2.00 | $6.00 | — | — | USD |
| `remm-slerp-l2-13b` | $1.88 | $1.88 | — | — | USD |
| `together-ai-81.1b-110b` | $1.80 | $1.80 | — | — | USD |
| `ft:babbage-002` | $1.60 | $1.60 | $0.20 | $0.20 | USD |
| `cohere.command-latest` | $1.56 | $1.56 | — | — | USD |
| `cohere.command-a-03-2025` | $1.56 | $1.56 | — | — | USD |
| `cohere.command-plus-latest` | $1.56 | $1.56 | — | — | USD |
| `codex-mini-latest` | $1.50 | $6.00 | — | — | USD |
| `l3-euryale-70b` | $1.48 | $1.48 | — | — | USD |
| `l3-70b-euryale-v2.1` | $1.48 | $1.48 | — | — | USD |
| `l31-70b-euryale-v2.2` | $1.48 | $1.48 | — | — | USD |
| `cogito-v2.1-671b` | $1.25 | $1.25 | — | — | USD |
| `databricks-gemini-2-5-pro` | $1.25 | $10.00 | — | — | USD |
| `databricks-gpt-5` | $1.25 | $10.00 | — | — | USD |
| `databricks-gpt-5-1` | $1.25 | $10.00 | — | — | USD |
| `llama-3.1-nemotron-70b-instruct` | $1.20 | $1.20 | — | — | USD |
| `fireworks-ai-56b-to-176b` | $1.20 | $1.20 | — | — | USD |
| `kimi-k2-turbo-preview` | $1.15 | $8.00 | — | — | USD |
| `kimi-k2-thinking-turbo` | $1.15 | $8.00 | — | — | USD |
| `openai-o3-mini` | $1.10 | $4.40 | — | — | USD |
| `databricks-claude-haiku-4-5` | $1.00 | $5.00 | — | — | USD |
| `databricks-meta-llama-3-70b-instruct` | $1.00 | $3.00 | — | — | USD |
| `databricks-mpt-30b-instruct` | $1.00 | $1.00 | — | — | USD |
| `mimo-v2-pro` | $1.00 | $3.00 | — | — | USD |
| `relace-search` | $1.00 | $3.00 | — | — | USD |
| `qwen3-coder-plus` | $1.00 | $5.00 | — | — | USD |
| `hermes-4-405b` | $1.00 | $3.00 | — | — | USD |
| `sonar` | $1.00 | $1.00 | — | — | USD |
| `hermes-3-llama-3.1-405b` | $1.00 | $1.00 | — | — | USD |
| `llama-3.1-70b-instruct` | $1.00 | $1.00 | — | — | USD |
| `CodeLlama-34b-Instruct-hf` | $1.00 | $1.00 | — | — | USD |
| `CodeLlama-70b-Instruct-hf` | $1.00 | $1.00 | — | — | USD |
| `Llama-2-70b-chat-hf` | $1.00 | $1.00 | — | — | USD |
| `command` | $1.00 | $2.00 | — | — | USD |
| `command-nightly` | $1.00 | $2.00 | — | — | USD |
| `Hermes-3-Llama-3.1-405B` | $1.00 | $3.00 | — | — | USD |
| `Kimi-K2-Instruct-0905` | $1.00 | $3.00 | — | — | USD |
| `kimi-k2-instruct-0905` | $1.00 | $3.00 | — | — | USD |
| `Meta-Llama-3.1-405B-Instruct` | $1.00 | $3.00 | — | — | USD |
| `kimi-latest-32k` | $1.00 | $3.00 | — | — | USD |
| `sonar-reasoning` | $1.00 | $5.00 | — | — | USD |
| `qwen3-coder-480b-a35b-instruct-maas` | $1.00 | $4.00 | — | — | USD |
| `morph-v3-large` | $0.90 | $1.90 | — | — | USD |
| `maestro-reasoning` | $0.90 | $3.30 | — | — | USD |
| `Mixtral-8x22B-Instruct-v0.1` | $0.90 | $0.90 | — | — | USD |
| `fireworks-ai-above-16b` | $0.90 | $0.90 | — | — | USD |
| `together-ai-41.1b-80b` | $0.90 | $0.90 | — | — | USD |
| `Llama-3.3-70B-Instruct-Turbo` | $0.88 | $0.88 | — | — | USD |
| `Meta-Llama-3.1-70B-Instruct-Turbo` | $0.88 | $0.88 | — | — | USD |
| `relace-apply-3` | $0.85 | $1.25 | — | — | USD |
| `router` | $0.85 | $3.40 | — | — | USD |
| `l3.1-euryale-70b` | $0.85 | $0.85 | — | — | USD |
| `llama-3.3-70b` | $0.85 | $1.20 | — | — | USD |
| `aion-2.0` | $0.80 | $1.60 | — | — | USD |
| `morph-v3-fast` | $0.80 | $1.20 | — | — | USD |
| `llemma_7b` | $0.80 | $1.20 | — | — | USD |
| `codellama-7b-instruct-solidity` | $0.80 | $1.20 | — | — | USD |
| `aion-rp-llama-3.1-8b` | $0.80 | $1.60 | — | — | USD |
| `qwen2.5-vl-72b-instruct` | $0.80 | $0.80 | — | — | USD |
| `nova-pro-v1` | $0.80 | $3.20 | — | — | USD |
| `qwq-plus` | $0.80 | $2.40 | — | — | USD |
| `ft:gpt-4.1-mini-2025-04-14` | $0.80 | $3.20 | $0.40 | $1.60 | USD |
| `Kimi-K2-Thinking` | $0.80 | $1.20 | — | — | USD |
| `anthropic-claude-3.5-haiku` | $0.80 | $4.00 | — | — | USD |
| `hermes3-405b` | $0.80 | $0.80 | — | — | USD |
| `llama3.1-405b-instruct-fp8` | $0.80 | $0.80 | — | — | USD |
| `multimodalembedding` | $0.80 | free | — | — | USD |
| `multimodalembedding@001` | $0.80 | free | — | — | USD |
| `together-ai-21.1b-41b` | $0.80 | $0.80 | — | — | USD |
| `nova-pro` | $0.80 | $3.20 | — | — | USD |
| `mistral-saba-24b` | $0.79 | $0.79 | — | — | USD |
| `qwen3-max-thinking` | $0.78 | $3.90 | — | — | USD |
| `virtuoso-large` | $0.75 | $1.20 | — | — | USD |
| `meta.llama-3.3-70b-instruct` | $0.72 | $0.72 | — | — | USD |
| `meta.llama-4-maverick-17b-128e-instruct-fp8` | $0.72 | $0.72 | — | — | USD |
| `meta.llama-4-scout-17b-16e-instruct` | $0.72 | $0.72 | — | — | USD |
| `llama-3.1-70b` | $0.72 | $0.72 | — | — | USD |
| `llama-3.2-90b` | $0.72 | $0.72 | — | — | USD |
| `aion-1.0-mini` | $0.70 | $1.40 | — | — | USD |
| `open-mixtral-8x7b` | $0.70 | $0.70 | — | — | USD |
| `codellama-70b-instruct` | $0.70 | $2.80 | — | — | USD |
| `llama-2-70b-chat` | $0.70 | $2.80 | — | — | USD |
| `pplx-70b-chat` | $0.70 | $2.80 | — | — | USD |
| `Meta-Llama-3_1-70B-Instruct` | $0.67 | $0.67 | — | — | USD |
| `Meta-Llama-3_3-70B-Instruct` | $0.67 | $0.67 | — | — | USD |
| `l3.3-euryale-70b` | $0.65 | $0.75 | — | — | USD |
| `gemma-2-27b-it` | $0.65 | $0.65 | — | — | USD |
| `mixtral-8x22b-instruct` | $0.65 | $0.65 | — | — | USD |
| `L3.1-70B-Euryale-v2.2` | $0.65 | $0.75 | — | — | USD |
| `L3.3-70B-Euryale-v2.3` | $0.65 | $0.75 | — | — | USD |
| `llama3.3-70b-instruct` | $0.65 | $0.65 | — | — | USD |
| `llama-2-70b` | $0.65 | $2.75 | — | — | USD |
| `Llama-4-Maverick-17B-128E-Instruct` | $0.63 | $1.80 | — | — | USD |
| `wizardlm-2-8x22b` | $0.62 | $0.62 | — | — | USD |
| `qwen3.5-397b-a17b` | $0.60 | $3.60 | — | — | USD |
| `kimi-k2.5` | $0.60 | $3.00 | — | — | USD |
| `palmyra-x5` | $0.60 | $6.00 | — | — | USD |
| `kimi-k2-thinking` | $0.60 | $2.50 | — | — | USD |
| `kimi-k2-0905` | $0.60 | $2.50 | — | — | USD |
| `llama-3.1-nemotron-ultra-253b-v1` | $0.60 | $1.80 | — | — | USD |
| `Mixtral-8x7B-Instruct-v0.1` | $0.60 | $0.60 | — | — | USD |
| `llama3.1-70b` | $0.60 | $0.60 | — | — | USD |
| `Kimi-K2-Instruct` | $0.60 | $2.50 | — | — | USD |
| `Llama-3.1-Nemotron-70B-Instruct` | $0.60 | $0.60 | — | — | USD |
| `kimi-k2p5` | $0.60 | $3.00 | — | — | USD |
| `meta-llama-3.1-70b-instruct` | $0.60 | $0.60 | — | — | USD |
| `kimi-k2-0711-preview` | $0.60 | $2.50 | — | — | USD |
| `kimi-k2-0905-preview` | $0.60 | $2.50 | — | — | USD |
| `kimi-thinking-preview` | $0.60 | $2.50 | — | — | USD |
| `mixtral-8x22b-instruct-v0.1` | $0.60 | $0.60 | — | — | USD |
| `Llama-3.1-Nemotron-Ultra-253B-v1` | $0.60 | $1.80 | — | — | USD |
| `xai.grok-3-mini-fast` | $0.60 | $4.00 | — | — | USD |
| `sonar-medium-chat` | $0.60 | $1.80 | — | — | USD |
| `Meta-Llama-3.3-70B-Instruct` | $0.60 | $1.20 | — | — | USD |
| `Qwen3.5-397B-A17B` | $0.60 | $3.60 | — | — | USD |
| `grok-3-mini-fast` | $0.60 | $4.00 | — | — | USD |
| `kimi-k2-thinking-maas` | $0.60 | $2.50 | — | — | USD |
| `grok-3-mini-fast-beta` | $0.60 | $4.00 | — | — | USD |
| `grok-3-mini-fast-latest` | $0.60 | $4.00 | — | — | USD |
| `llama-3.3-70b-versatile` | $0.59 | $0.79 | — | — | USD |
| `llama-3-70b` | $0.59 | $0.79 | — | — | USD |
| `kimi-k2-instruct` | $0.57 | $2.30 | — | — | USD |
| `kimi-k2` | $0.55 | $2.20 | — | — | USD |
| `skyfall-36b-v2` | $0.55 | $0.80 | — | — | USD |
| `minimax-m1-80k` | $0.55 | $2.20 | — | — | USD |
| `llama-3-70b-instruct` | $0.51 | $0.74 | — | — | USD |
| `databricks-llama-2-70b-chat` | $0.50 | $1.50 | — | — | USD |
| `databricks-llama-4-maverick` | $0.50 | $1.50 | — | — | USD |
| `databricks-meta-llama-3-3-70b-instruct` | $0.50 | $1.50 | — | — | USD |
| `databricks-mixtral-8x7b-instruct` | $0.50 | $1.00 | — | — | USD |
| `databricks-mpt-7b-instruct` | $0.50 | free | — | — | USD |
| `mistral-large-2512` | $0.50 | $1.50 | — | — | USD |
| `coder-large` | $0.50 | $0.80 | — | — | USD |
| `chatdolphin` | $0.50 | $0.50 | — | — | USD |
| `dolphin` | $0.50 | $0.50 | — | — | USD |
| `fireworks-ai-moe-up-to-56b` | $0.50 | $0.50 | — | — | USD |
| `magistral-small-2506` | $0.50 | $1.50 | — | — | USD |
| `magistral-small-latest` | $0.50 | $1.50 | — | — | USD |
| `magistral-small-1-2-2509` | $0.50 | $1.50 | — | — | USD |
| `mistral-large-latest` | $0.50 | $1.50 | — | — | USD |
| `mistral-large-3` | $0.50 | $1.50 | — | — | USD |
| `Qwen2-Audio-7B-Instruct` | $0.50 | $100.00 | — | — | USD |
| `Kimi-K2.5` | $0.50 | $2.80 | — | — | USD |
| `magistral-small` | $0.50 | $1.50 | — | — | USD |
| `WizardLM-2-8x22B` | $0.48 | $0.48 | — | — | USD |
| `qwen3-235b-a22b` | $0.46 | $1.82 | — | — | USD |
| `mimo-v2-omni` | $0.40 | $2.00 | — | — | USD |
| `qwen3.5-122b-a10b` | $0.40 | $2.00 | — | — | USD |
| `qwen3.5-plus-02-15` | $0.40 | $2.40 | — | — | USD |
| `devstral-2512` | $0.40 | $2.00 | — | — | USD |
| `qwen3-vl-235b-a22b-thinking` | $0.40 | $4.00 | — | — | USD |
| `qwen3-vl-235b-a22b-instruct` | $0.40 | $1.60 | — | — | USD |
| `mistral-medium-3.1` | $0.40 | $2.00 | — | — | USD |
| `devstral-medium` | $0.40 | $2.00 | — | — | USD |
| `minimax-m1` | $0.40 | $2.20 | — | — | USD |
| `mistral-medium-3` | $0.40 | $2.00 | — | — | USD |
| `unslopnemo-12b` | $0.40 | $0.40 | — | — | USD |
| `babbage-002` | $0.40 | $0.40 | — | — | USD |
| `devstral-medium-2507` | $0.40 | $2.00 | — | — | USD |
| `devstral-latest` | $0.40 | $2.00 | — | — | USD |
| `devstral-medium-latest` | $0.40 | $2.00 | — | — | USD |
| `mistral-medium-2505` | $0.40 | $2.00 | — | — | USD |
| `mistral-medium-latest` | $0.40 | $2.00 | — | — | USD |
| `mistral-medium-3-1-2508` | $0.40 | $2.00 | — | — | USD |
| `codellama-34b-instruct` | $0.35 | $1.40 | — | — | USD |
| `databricks-gemini-2-5-flash` | $0.30 | $2.50 | — | — | USD |
| `kat-coder-pro-v2` | $0.30 | $1.20 | — | — | USD |
| `minimax-m2.7` | $0.30 | $1.20 | — | — | USD |
| `qwen3.5-27b` | $0.30 | $2.40 | — | — | USD |
| `minimax-m2.5` | $0.30 | $1.10 | — | — | USD |
| `minimax-m2-her` | $0.30 | $1.20 | — | — | USD |
| `minimax-m2.1` | $0.30 | $1.20 | — | — | USD |
| `nova-2-lite-v1` | $0.30 | $2.50 | — | — | USD |
| `kat-coder-pro` | $0.30 | $1.20 | — | — | USD |
| `minimax-m2` | $0.30 | $1.20 | — | — | USD |
| `cydonia-24b-v4.1` | $0.30 | $0.50 | — | — | USD |
| `codestral-2508` | $0.30 | $0.90 | — | — | USD |
| `qwen3-235b-a22b-thinking-2507` | $0.30 | $3.00 | — | — | USD |
| `grok-3-mini` | $0.30 | $0.50 | — | — | USD |
| `grok-3-mini-beta` | $0.30 | $0.50 | — | — | USD |
| `hermes-3-llama-3.1-70b` | $0.30 | $0.30 | — | — | USD |
| `command-light` | $0.30 | $0.60 | — | — | USD |
| `minimax-m2p1` | $0.30 | $1.20 | — | — | USD |
| `ft:gpt-4o-mini-2024-07-18` | $0.30 | $1.20 | $0.15 | $0.60 | USD |
| `MiniMax-M2.1` | $0.30 | $1.20 | — | — | USD |
| `Qwen3-VL-235B-A22B-Instruct-FP8` | $0.30 | $1.40 | — | — | USD |
| `mistral-nemo-instruct-2407` | $0.30 | $0.30 | — | — | USD |
| `MiniMax-M2.1-lightning` | $0.30 | $2.40 | — | — | USD |
| `MiniMax-M2.5` | $0.30 | $1.20 | — | — | USD |
| `MiniMax-M2.5-lightning` | $0.30 | $2.40 | — | — | USD |
| `MiniMax-M2` | $0.30 | $1.20 | — | — | USD |
| `open-mistral-nemo` | $0.30 | $0.30 | — | — | USD |
| `open-mistral-nemo-2407` | $0.30 | $0.30 | — | — | USD |
| `xai.grok-3-mini` | $0.30 | $0.50 | — | — | USD |
| `mixtral-8x7b-instruct-v0.1` | $0.30 | $1.00 | — | — | USD |
| `Meta-Llama-Guard-3-8B` | $0.30 | $0.30 | — | — | USD |
| `together-ai-8.1b-21b` | $0.30 | $0.30 | — | — | USD |
| `codestral` | $0.30 | $0.90 | — | — | USD |
| `minimax-m2-maas` | $0.30 | $1.20 | — | — | USD |
| `grok-3-mini-latest` | $0.30 | $0.50 | — | — | USD |
| `qwen3-coder-480b-a35b-instruct` | $0.30 | $1.30 | — | — | USD |
| `qwen3-32b` | $0.29 | $0.59 | — | — | USD |
| `Qwen3-Coder-480B-A35B-Instruct-Turbo` | $0.29 | $1.20 | — | — | USD |
| `llava-v1.6-mistral-7b-hf` | $0.29 | $0.29 | — | — | USD |
| `olmOCR-7B-0725-FP8` | $0.27 | $1.50 | — | — | USD |
| `Llama-4-Maverick-17B-128E-Instruct-FP8` | $0.27 | $0.85 | — | — | USD |
| `seed-2.0-lite` | $0.25 | $2.00 | — | — | USD |
| `mercury-2` | $0.25 | $0.75 | — | — | USD |
| `qwen3.5-35b-a3b` | $0.25 | $2.00 | — | — | USD |
| `seed-1.6` | $0.25 | $2.00 | — | — | USD |
| `mercury` | $0.25 | $0.75 | — | — | USD |
| `mercury-coder` | $0.25 | $0.75 | — | — | USD |
| `Llama-2-13b-chat-hf` | $0.25 | $0.25 | — | — | USD |
| `codestral-mamba-latest` | $0.25 | $0.25 | — | — | USD |
| `mistral-tiny` | $0.25 | $0.25 | — | — | USD |
| `open-codestral-mamba` | $0.25 | $0.25 | — | — | USD |
| `open-mistral-7b` | $0.25 | $0.25 | — | — | USD |
| `mercury-coder-small` | $0.25 | $1.00 | — | — | USD |
| `qwen3-235b-a22b-instruct-2507-maas` | $0.25 | $1.00 | — | — | USD |
| `qwen3-omni-30b-a3b-thinking` | $0.25 | $0.97 | — | — | USD |
| `qwen3-omni-30b-a3b-instruct` | $0.25 | $0.97 | — | — | USD |
| `databricks-gpt-5-mini` | $0.25 | $2.00 | — | — | USD |
| `qwen3-coder` | $0.22 | $0.95 | — | — | USD |
| `olmo-3.1-32b-instruct` | $0.20 | $0.60 | — | — | USD |
| `ministral-14b-2512` | $0.20 | $0.20 | — | — | USD |
| `intellect-3` | $0.20 | $1.10 | — | — | USD |
| `grok-4.1-fast` | $0.20 | $0.50 | — | — | USD |
| `nemotron-nano-12b-v2-vl` | $0.20 | $0.60 | — | — | USD |
| `qwen3-vl-30b-a3b-thinking` | $0.20 | $1.00 | — | — | USD |
| `qwen3-vl-30b-a3b-instruct` | $0.20 | $0.70 | — | — | USD |
| `grok-4-fast` | $0.20 | $0.50 | — | — | USD |
| `longcat-flash-chat` | $0.20 | $0.80 | — | — | USD |
| `grok-code-fast-1` | $0.20 | $1.50 | — | — | USD |
| `llama-guard-4-12b` | $0.20 | $0.20 | — | — | USD |
| `llama-4-maverick` | $0.20 | $0.60 | — | — | USD |
| `qwen2.5-vl-32b-instruct` | $0.20 | $0.60 | — | — | USD |
| `mistral-saba` | $0.20 | $0.60 | — | — | USD |
| `minimax-01` | $0.20 | $1.10 | — | — | USD |
| `llama-3.1-8b-instruct` | $0.20 | $0.20 | — | — | USD |
| `Qwen2.5-VL-32B-Instruct` | $0.20 | $0.60 | — | — | USD |
| `Qwen3-235B-A22B` | $0.20 | $0.60 | — | — | USD |
| `fireworks-ai-4.1b-to-16b` | $0.20 | $0.20 | — | — | USD |
| `fireworks-ai-up-to-4b` | $0.20 | $0.20 | — | — | USD |
| `ft:gpt-4.1-nano-2025-04-14` | $0.20 | $0.80 | $0.10 | $0.40 | USD |
| `llama3-8b-instruct` | $0.20 | $0.20 | — | — | USD |
| `llama-4-maverick-17b-128e-instruct` | $0.20 | $0.60 | — | — | USD |
| `jamba-1.5` | $0.20 | $0.40 | — | — | USD |
| `jamba-1.5-mini` | $0.20 | $0.40 | — | — | USD |
| `jamba-1.5-mini@001` | $0.20 | $0.40 | — | — | USD |
| `jamba-mini-1.6` | $0.20 | $0.40 | — | — | USD |
| `jamba-mini-1.7` | $0.20 | $0.40 | — | — | USD |
| `ministral-3-14b-2512` | $0.20 | $0.20 | — | — | USD |
| `kimi-latest-8k` | $0.20 | $2.00 | — | — | USD |
| `together-ai-4.1b-8b` | $0.20 | $0.20 | — | — | USD |
| `Qwen3-235B-A22B-Instruct-2507-tput` | $0.20 | $6.00 | — | — | USD |
| `Qwen3-235B-A22B-fp8-tput` | $0.20 | $0.60 | — | — | USD |
| `gemma-2-9b` | $0.20 | $0.20 | — | — | USD |
| `grok-4-fast-reasoning` | $0.20 | $0.50 | — | — | USD |
| `grok-4-fast-non-reasoning` | $0.20 | $0.50 | — | — | USD |
| `grok-4-1-fast` | $0.20 | $0.50 | — | — | USD |
| `grok-4-1-fast-reasoning` | $0.20 | $0.50 | — | — | USD |
| `grok-4-1-fast-reasoning-latest` | $0.20 | $0.50 | — | — | USD |
| `grok-4-1-fast-non-reasoning` | $0.20 | $0.50 | — | — | USD |
| `grok-4-1-fast-non-reasoning-latest` | $0.20 | $0.50 | — | — | USD |
| `grok-code-fast` | $0.20 | $1.50 | — | — | USD |
| `grok-code-fast-1-0825` | $0.20 | $1.50 | — | — | USD |
| `r1v4-lite` | $0.20 | $0.60 | — | — | USD |
| `qwen3-235b-a22b-fp8` | $0.20 | $0.80 | — | — | USD |
| `qwen3-coder-flash` | $0.20 | $0.97 | — | — | USD |
| `mamba-codestral-7B-v0.1` | $0.19 | $0.19 | — | — | USD |
| `spotlight` | $0.18 | $0.18 | — | — | USD |
| `Llama-Guard-4-12B` | $0.18 | $0.18 | — | — | USD |
| `Meta-Llama-3.1-8B-Instruct-Turbo` | $0.18 | $0.18 | — | — | USD |
| `llama-4-scout-17b-16e-instruct` | $0.18 | $0.59 | — | — | USD |
| `voyage-3-large` | $0.18 | free | — | — | USD |
| `voyage-code-3` | $0.18 | free | — | — | USD |
| `voyage-context-3` | $0.18 | free | — | — | USD |
| `rocinante-12b` | $0.17 | $0.43 | — | — | USD |
| `qwen3-vl-32b-instruct` | $0.16 | $0.64 | — | — | USD |
| `qwen3-vl-32b-thinking` | $0.16 | $2.87 | — | — | USD |
| `llama-3.2-11b` | $0.16 | $0.16 | — | — | USD |
| `databricks-gemma-3-12b` | $0.15 | $0.50 | — | — | USD |
| `databricks-gpt-oss-120b` | $0.15 | $0.60 | — | — | USD |
| `databricks-meta-llama-3-1-8b-instruct` | $0.15 | $0.45 | — | — | USD |
| `mistral-small-2603` | $0.15 | $0.60 | — | — | USD |
| `solar-pro-3` | $0.15 | $0.60 | — | — | USD |
| `olmo-3.1-32b-think` | $0.15 | $0.50 | — | — | USD |
| `rnj-1-instruct` | $0.15 | $0.15 | — | — | USD |
| `ministral-8b-2512` | $0.15 | $0.15 | — | — | USD |
| `olmo-3-32b-think` | $0.15 | $0.50 | — | — | USD |
| `qwen3-next-80b-a3b-thinking` | $0.15 | $1.20 | — | — | USD |
| `qwen3-next-80b-a3b-instruct` | $0.15 | $1.20 | — | — | USD |
| `qwq-32b` | $0.15 | $0.58 | — | — | USD |
| `command-r7b-12-2024` | $0.15 | $0.037 | — | — | USD |
| `command-r-08-2024` | $0.15 | $0.60 | — | — | USD |
| `zephyr-7b-beta` | $0.15 | $0.15 | — | — | USD |
| `gemma-7b-it` | $0.15 | $0.15 | — | — | USD |
| `Llama-2-7b-chat-hf` | $0.15 | $0.15 | — | — | USD |
| `Mistral-7B-Instruct-v0.1` | $0.15 | $0.15 | — | — | USD |
| `command-r` | $0.15 | $0.60 | — | — | USD |
| `QwQ-32B` | $0.15 | $0.45 | — | — | USD |
| `Qwen3-Next-80B-A3B-Instruct` | $0.15 | $1.50 | — | — | USD |
| `Qwen3-Next-80B-A3B-Thinking` | $0.15 | $1.50 | — | — | USD |
| `ministral-3-8b-2512` | $0.15 | $0.15 | — | — | USD |
| `pixtral-12b-2409` | $0.15 | $0.15 | — | — | USD |
| `llama-3.2-3b` | $0.15 | $0.15 | — | — | USD |
| `codestral-embed` | $0.15 | free | — | — | USD |
| `pixtral-12b` | $0.15 | $0.15 | — | — | USD |
| `qwen3-next-80b-a3b-instruct-maas` | $0.15 | $1.20 | — | — | USD |
| `qwen3-next-80b-a3b-thinking-maas` | $0.15 | $1.20 | — | — | USD |
| `qwen3-vl-8b` | $0.15 | $0.55 | — | — | USD |
| `openai.gpt-oss-120b` | $0.15 | $0.60 | — | — | USD |
| `openai.gpt-oss-safeguard-120b` | $0.15 | $0.60 | — | — | USD |
| `hunyuan-a13b-instruct` | $0.14 | $0.57 | — | — | USD |
| `hermes-2-pro-llama-3-8b` | $0.14 | $0.14 | — | — | USD |
| `llama-3.3-70b-instruct` | $0.14 | $0.40 | — | — | USD |
| `hermes-4-70b` | $0.13 | $0.40 | — | — | USD |
| `Qwen2.5-72B-Instruct` | $0.13 | $0.40 | — | — | USD |
| `Meta-Llama-3.1-70B-Instruct` | $0.13 | $0.40 | — | — | USD |
| `Qwen2.5-VL-72B-Instruct` | $0.13 | $0.40 | — | — | USD |
| `Qwen2-VL-72B-Instruct` | $0.13 | $0.40 | — | — | USD |
| `mistral-7b-instruct` | $0.13 | $0.13 | — | — | USD |
| `databricks-gte-large-en` | $0.13 | free | — | — | USD |
| `chat-bison` | $0.12 | $0.12 | — | — | USD |
| `chat-bison-001` | $0.12 | $0.12 | — | — | USD |
| `text-bison` | $0.12 | $0.12 | — | — | USD |
| `text-bison-001` | $0.12 | $0.12 | — | — | USD |
| `text-bison-safety-off` | $0.12 | $0.12 | — | — | USD |
| `text-bison-safety-recitation-off` | $0.12 | $0.12 | — | — | USD |
| `qwen3-coder-next` | $0.12 | $0.75 | — | — | USD |
| `Meta-Llama-3-70B-Instruct` | $0.12 | $0.30 | — | — | USD |
| `embed-v4.0` | $0.12 | free | — | — | USD |
| `Hermes-3-Llama-3.1-70B` | $0.12 | $0.30 | — | — | USD |
| `Llama-3.2-3B-Instruct` | $0.12 | $0.30 | — | — | USD |
| `hermes3-70b` | $0.12 | $0.30 | — | — | USD |
| `llama3.1-70b-instruct-fp8` | $0.12 | $0.30 | — | — | USD |
| `llama3.1-nemotron-70b-instruct-fp8` | $0.12 | $0.30 | — | — | USD |
| `llama3.3-70b-instruct-fp8` | $0.12 | $0.30 | — | — | USD |
| `voyage-code-2` | $0.12 | free | — | — | USD |
| `voyage-finance-2` | $0.12 | free | — | — | USD |
| `voyage-large-2` | $0.12 | free | — | — | USD |
| `voyage-law-2` | $0.12 | free | — | — | USD |
| `voyage-multimodal-3` | $0.12 | free | — | — | USD |
| `gemma-3-27b-it` | $0.12 | $0.20 | — | — | USD |
| `qwen3-vl-8b-thinking` | $0.12 | $1.36 | — | — | USD |
| `mistral-7b-instruct-v0.1` | $0.11 | $0.19 | — | — | USD |
| `databricks-bge-large-en` | $0.10 | free | — | — | USD |
| `reka-edge` | $0.10 | $0.10 | — | — | USD |
| `nemotron-3-super-120b-a12b` | $0.10 | $0.50 | — | — | USD |
| `seed-2.0-mini` | $0.10 | $0.40 | — | — | USD |
| `qwen3.5-flash-02-23` | $0.10 | $0.40 | — | — | USD |
| `step-3.5-flash` | $0.10 | $0.30 | — | — | USD |
| `mistral-small-creative` | $0.10 | $0.30 | — | — | USD |
| `ministral-3b-2512` | $0.10 | $0.10 | — | — | USD |
| `voxtral-small-24b-2507` | $0.10 | $0.30 | — | — | USD |
| `llama-3.3-nemotron-super-49b-v1.5` | $0.10 | $0.40 | — | — | USD |
| `ui-tars-1.5-7b` | $0.10 | $0.20 | — | — | USD |
| `mistral-small-3.2-24b-instruct` | $0.10 | $0.30 | — | — | USD |
| `llama-4-scout` | $0.10 | $0.30 | — | — | USD |
| `mistral-small-3.1-24b-instruct` | $0.10 | $0.30 | — | — | USD |
| `llama3.1-8b` | $0.10 | $0.10 | — | — | USD |
| `Qwen3-30B-A3B` | $0.10 | $0.30 | — | — | USD |
| `Qwen3-32B` | $0.10 | $0.30 | — | — | USD |
| `Llama-3.3-Nemotron-Super-49B-v1.5` | $0.10 | $0.40 | — | — | USD |
| `embed-english-light-v2.0` | $0.10 | free | — | — | USD |
| `embed-english-light-v3.0` | $0.10 | free | — | — | USD |
| `embed-english-v2.0` | $0.10 | free | — | — | USD |
| `embed-english-v3.0` | $0.10 | free | — | — | USD |
| `embed-multilingual-v2.0` | $0.10 | free | — | — | USD |
| `embed-multilingual-v3.0` | $0.10 | free | — | — | USD |
| `meta-llama-3.1-8b-instruct` | $0.10 | $0.10 | — | — | USD |
| `lfm-40b` | $0.10 | $0.20 | — | — | USD |
| `devstral-small-2505` | $0.10 | $0.30 | — | — | USD |
| `devstral-small-2507` | $0.10 | $0.30 | — | — | USD |
| `devstral-small-latest` | $0.10 | $0.30 | — | — | USD |
| `labs-devstral-small-2512` | $0.10 | $0.30 | — | — | USD |
| `mistral-small` | $0.10 | $0.30 | — | — | USD |
| `ministral-3-3b-2512` | $0.10 | $0.10 | — | — | USD |
| `Llama-3.3-Nemotron-Super-49B-v1` | $0.10 | $0.40 | — | — | USD |
| `Mistral-7B-Instruct-v0.3` | $0.10 | $0.10 | — | — | USD |
| `llama-2-13b` | $0.10 | $0.50 | — | — | USD |
| `llama-2-13b-chat` | $0.10 | $0.50 | — | — | USD |
| `text-multilingual-embedding-002` | $0.10 | free | — | — | USD |
| `together-ai-up-to-4b` | $0.10 | $0.10 | — | — | USD |
| `llama-3.2-1b` | $0.10 | $0.10 | — | — | USD |
| `ministral-8b` | $0.10 | $0.10 | — | — | USD |
| `mistral-embed` | $0.10 | free | — | — | USD |
| `voyage-2` | $0.10 | free | — | — | USD |
| `voyage-lite-01` | $0.10 | free | — | — | USD |
| `voyage-lite-02-instruct` | $0.10 | free | — | — | USD |
| `mistral-7b-v0.3` | $0.10 | $0.15 | — | — | USD |
| `llava-7b` | $0.10 | $0.20 | — | — | USD |
| `mimo-v2-flash` | $0.090 | $0.29 | — | — | USD |
| `tongyi-deepresearch-30b-a3b` | $0.090 | $0.45 | — | — | USD |
| `qwen3-30b-a3b-instruct-2507` | $0.090 | $0.30 | — | — | USD |
| `mythomax-l2-13b` | $0.090 | $0.090 | — | — | USD |
| `qwen3-235b-a22b-instruct-2507` | $0.090 | $0.58 | — | — | USD |
| `qwen3-30b-a3b-fp8` | $0.090 | $0.45 | — | — | USD |
| `qwen3-vl-8b-instruct` | $0.080 | $0.50 | — | — | USD |
| `qwen3-30b-a3b-thinking-2507` | $0.080 | $0.40 | — | — | USD |
| `qwen3-30b-a3b` | $0.080 | $0.28 | — | — | USD |
| `MythoMax-L2-13b` | $0.080 | $0.090 | — | — | USD |
| `Qwen3-14B` | $0.080 | $0.24 | — | — | USD |
| `Qwen3-4B` | $0.080 | $0.24 | — | — | USD |
| `Meta-Llama-3.2-3B-Instruct` | $0.080 | $0.16 | — | — | USD |
| `dolphin3-8b` | $0.080 | $0.15 | — | — | USD |
| `openthinker-7b` | $0.080 | $0.15 | — | — | USD |
| `seed-1.6-flash` | $0.075 | $0.30 | — | — | USD |
| `Mistral-Small-3.2-24B-Instruct-2506` | $0.075 | $0.20 | — | — | USD |
| `openai.gpt-oss-20b` | $0.075 | $0.30 | — | — | USD |
| `openai.gpt-oss-safeguard-20b` | $0.075 | $0.30 | — | — | USD |
| `qwen3-235b-a22b-2507` | $0.071 | $0.10 | — | — | USD |
| `qwen3-coder-30b-a3b-instruct` | $0.070 | $0.27 | — | — | USD |
| `devstral-small` | $0.070 | $0.28 | — | — | USD |
| `phi-4` | $0.070 | $0.14 | — | — | USD |
| `mixtral-8x7b-instruct` | $0.070 | $0.28 | — | — | USD |
| `databricks-gpt-oss-20b` | $0.070 | $0.30 | — | — | USD |
| `pplx-7b-chat` | $0.070 | $0.28 | — | — | USD |
| `sonar-small-chat` | $0.070 | $0.28 | — | — | USD |
| `baichuan-m2-32b` | $0.070 | $0.070 | — | — | USD |
| `qwen2.5-7b-instruct` | $0.070 | $0.070 | — | — | USD |
| `qwen3-embedding-0.6b` | $0.070 | free | — | — | USD |
| `qwen3-embedding-8b` | $0.070 | free | — | — | USD |
| `qwen3-14b` | $0.060 | $0.24 | — | — | USD |
| `nova-lite-v1` | $0.060 | $0.24 | — | — | USD |
| `Qwen2.5-Coder-32B-Instruct` | $0.060 | $0.20 | — | — | USD |
| `mistral-small-latest` | $0.060 | $0.18 | — | — | USD |
| `mistral-small-3-2-2506` | $0.060 | $0.18 | — | — | USD |
| `Qwen2.5-32B-Instruct` | $0.060 | $0.20 | — | — | USD |
| `nova-lite` | $0.060 | $0.24 | — | — | USD |
| `voyage-3` | $0.060 | free | — | — | USD |
| `voyage-3.5` | $0.060 | free | — | — | USD |
| `qwen2.5-coder-7b` | $0.060 | $0.12 | — | — | USD |
| `codellama-7b` | $0.060 | $0.12 | — | — | USD |
| `qwen3.5-9b` | $0.050 | $0.15 | — | — | USD |
| `nemotron-3-nano-30b-a3b` | $0.050 | $0.20 | — | — | USD |
| `olmo-2-0325-32b-instruct` | $0.050 | $0.20 | — | — | USD |
| `gemma-3-12b-it` | $0.050 | $0.10 | — | — | USD |
| `mistral-small-24b-instruct-2501` | $0.050 | $0.080 | — | — | USD |
| `llama-3-8b-instruct` | $0.050 | $0.25 | — | — | USD |
| `Mistral-Small-24B-Instruct-2501` | $0.050 | $0.080 | — | — | USD |
| `llama-3.1-8b-instant` | $0.050 | $0.080 | — | — | USD |
| `llama-4-maverick-17b-128e-instruct-fp8` | $0.050 | $0.10 | — | — | USD |
| `qwen25-coder-32b-instruct` | $0.050 | $0.10 | — | — | USD |
| `qwen3-32b-fp8` | $0.050 | $0.10 | — | — | USD |
| `llama-2-7b` | $0.050 | $0.25 | — | — | USD |
| `llama-2-7b-chat` | $0.050 | $0.25 | — | — | USD |
| `llama-3-8b` | $0.050 | $0.080 | — | — | USD |
| `mistral-7b-instruct-v0.2` | $0.050 | $0.25 | — | — | USD |
| `mistral-7b-v0.1` | $0.050 | $0.25 | — | — | USD |
| `llama-3.1-8b` | $0.050 | $0.080 | — | — | USD |
| `rerank-2` | $0.050 | free | — | — | USD |
| `rerank-2.5` | $0.050 | free | — | — | USD |
| `l3-8b-lunaris` | $0.050 | $0.050 | — | — | USD |
| `L3-8B-Stheno-v3.2` | $0.050 | $0.050 | — | — | USD |
| `qwen3-reranker-8b` | $0.050 | $0.050 | — | — | USD |
| `databricks-gpt-5-nano` | $0.050 | $0.40 | — | — | USD |
| `llama-3.2-11b-vision-instruct` | $0.049 | $0.049 | — | — | USD |
| `Llama-3.2-11B-Vision-Instruct` | $0.049 | $0.049 | — | — | USD |
| `trinity-mini` | $0.045 | $0.15 | — | — | USD |
| `nemotron-nano-9b-v2` | $0.040 | $0.16 | — | — | USD |
| `qwen3-8b` | $0.040 | $0.14 | — | — | USD |
| `gemma-3-4b-it` | $0.040 | $0.080 | — | — | USD |
| `l3-lunaris-8b` | $0.040 | $0.050 | — | — | USD |
| `mistral-nemo` | $0.040 | $0.17 | — | — | USD |
| `Qwen2.5-7B-Instruct` | $0.040 | $0.10 | — | — | USD |
| `L3-8B-Lunaris-v1-Turbo` | $0.040 | $0.050 | — | — | USD |
| `Mistral-Nemo-Instruct-2407` | $0.040 | $0.12 | — | — | USD |
| `NVIDIA-Nemotron-Nano-9B-v2` | $0.040 | $0.16 | — | — | USD |
| `Meta-Llama-3.2-1B-Instruct` | $0.040 | $0.080 | — | — | USD |
| `ministral-3b` | $0.040 | $0.040 | — | — | USD |
| `nova-micro-v1` | $0.035 | $0.14 | — | — | USD |
| `nova-micro` | $0.035 | $0.14 | — | — | USD |
| `autoglm-phone-9b-multilingual` | $0.035 | $0.14 | — | — | USD |
| `qwen3-8b-fp8` | $0.035 | $0.14 | — | — | USD |
| `lfm-2-24b-a2b` | $0.030 | $0.12 | — | — | USD |
| `qwen2.5-coder-7b-instruct` | $0.030 | $0.090 | — | — | USD |
| `llama-3.2-3b-instruct` | $0.030 | $0.050 | — | — | USD |
| `gemma-2-9b-it` | $0.030 | $0.090 | — | — | USD |
| `Meta-Llama-3-8B-Instruct` | $0.030 | $0.060 | — | — | USD |
| `pplx-embed-v1-4b` | $0.030 | free | — | — | USD |
| `granite-3.3-8b-instruct` | $0.030 | $0.25 | — | — | USD |
| `qwen3-4b-fp8` | $0.030 | $0.030 | — | — | USD |
| `gemma3-4b` | $0.030 | $0.080 | — | — | USD |
| `llama-3.2-1b-instruct` | $0.027 | $0.20 | — | — | USD |
| `hermes3-8b` | $0.025 | $0.040 | — | — | USD |
| `lfm-7b` | $0.025 | $0.040 | — | — | USD |
| `llama3.1-8b-instruct` | $0.025 | $0.040 | — | — | USD |
| `gemma-3n-e4b-it` | $0.020 | $0.040 | — | — | USD |
| `llama-guard-3-8b` | $0.020 | $0.060 | — | — | USD |
| `Llama-Guard-3-8B` | $0.020 | $0.060 | — | — | USD |
| `Meta-Llama-3.1-8B-Instruct` | $0.020 | $0.060 | — | — | USD |
| `Qwen2-VL-7B-Instruct` | $0.020 | $0.060 | — | — | USD |
| `titan-embed-text-v2` | $0.020 | free | — | — | USD |
| `rerank-2-lite` | $0.020 | free | — | — | USD |
| `rerank-2.5-lite` | $0.020 | free | — | — | USD |
| `voyage-3-lite` | $0.020 | free | — | — | USD |
| `voyage-3.5-lite` | $0.020 | free | — | — | USD |
| `paddleocr-vl` | $0.020 | $0.020 | — | — | USD |
| `nomic-embed-text` | $0.020 | free | — | — | USD |
| `jina-reranker-v2-base-multilingual` | $0.018 | $0.018 | — | — | USD |
| `granite-4.0-h-micro` | $0.017 | $0.11 | — | — | USD |
| `fireworks-ai-embedding-150m-to-350m` | $0.016 | free | — | — | USD |
| `UAE-Large-V1` | $0.016 | free | — | — | USD |
| `gte-large` | $0.016 | free | — | — | USD |
| `together-ai-embedding-151m-to-350m` | $0.016 | free | — | — | USD |
| `llama3.2-11b-vision-instruct` | $0.015 | $0.025 | — | — | USD |
| `llama3.2-3b-instruct` | $0.015 | $0.025 | — | — | USD |
| `lfm2-8b-a1b` | $0.010 | $0.020 | — | — | USD |
| `lfm-2.2-6b` | $0.010 | $0.020 | — | — | USD |
| `Qwen2.5-Coder-3B-Instruct` | $0.010 | $0.030 | — | — | USD |
| `Qwen2.5-Coder-7B-Instruct` | $0.010 | $0.030 | — | — | USD |
| `Qwen2.5-Coder-7B` | $0.010 | $0.030 | — | — | USD |
| `bge-en-icl` | $0.010 | free | — | — | USD |
| `bge-multilingual-gemma2` | $0.010 | free | — | — | USD |
| `e5-mistral-7b-instruct` | $0.010 | free | — | — | USD |
| `bge-m3` | $0.010 | $0.010 | — | — | USD |
| `bge-reranker-v2-m3` | $0.010 | $0.010 | — | — | USD |
| `fireworks-ai-embedding-up-to-150m` | $0.0080 | free | — | — | USD |
| `nomic-embed-text-v1` | $0.0080 | free | — | — | USD |
| `nomic-embed-text-v1.5` | $0.0080 | free | — | — | USD |
| `gte-base` | $0.0080 | free | — | — | USD |
| `together-ai-embedding-up-to-150m` | $0.0080 | free | — | — | USD |
| `bge-base-en-v1.5` | $0.0080 | free | — | — | USD |
| `pplx-embed-v1-0.6b` | $0.0040 | free | — | — | USD |
| `nemotron-3-super-120b-a12b:free` | free | free | — | — | USD |
| `minimax-m2.5:free` | free | free | — | — | USD |
| `free` | free | free | — | — | USD |
| `step-3.5-flash:free` | free | free | — | — | USD |
| `trinity-large-preview:free` | free | free | — | — | USD |
| `lfm-2.5-1.2b-thinking:free` | free | free | — | — | USD |
| `lfm-2.5-1.2b-instruct:free` | free | free | — | — | USD |
| `nemotron-3-nano-30b-a3b:free` | free | free | — | — | USD |
| `trinity-mini:free` | free | free | — | — | USD |
| `nemotron-nano-12b-v2-vl:free` | free | free | — | — | USD |
| `qwen3-next-80b-a3b-instruct:free` | free | free | — | — | USD |
| `nemotron-nano-9b-v2:free` | free | free | — | — | USD |
| `qwen3-coder:free` | free | free | — | — | USD |
| `dolphin-mistral-24b-venice-edition:free` | free | free | — | — | USD |
| `gemma-3n-e2b-it:free` | free | free | — | — | USD |
| `gemma-3n-e4b-it:free` | free | free | — | — | USD |
| `gemma-3-4b-it:free` | free | free | — | — | USD |
| `gemma-3-12b-it:free` | free | free | — | — | USD |
| `gemma-3-27b-it:free` | free | free | — | — | USD |
| `llama-3.3-70b-instruct:free` | free | free | — | — | USD |
| `llama-3.2-3b-instruct:free` | free | free | — | — | USD |
| `hermes-3-llama-3.1-405b:free` | free | free | — | — | USD |
| `codestral-2405` | free | free | — | — | USD |
| `codestral-latest` | free | free | — | — | USD |
| `kimi-k2-thinking-251104` | free | free | — | — | USD |
| `doubao-embedding` | free | free | — | — | USD |
| `doubao-embedding-large` | free | free | — | — | USD |
| `doubao-embedding-large-text-240915` | free | free | — | — | USD |
| `doubao-embedding-large-text-250515` | free | free | — | — | USD |
| `doubao-embedding-text-240715` | free | free | — | — | USD |
| `fireworks-ai-default` | free | free | — | — | USD |
| `learnlm-1.5-pro-experimental` | free | free | — | — | USD |
| `lyria-3-clip-preview` | free | free | — | — | USD |
| `lyria-3-pro-preview` | free | free | — | — | USD |
| `GigaChat-2-Lite` | free | free | — | — | USD |
| `GigaChat-2-Max` | free | free | — | — | USD |
| `GigaChat-2-Pro` | free | free | — | — | USD |
| `Embeddings` | free | free | — | — | USD |
| `Embeddings-2` | free | free | — | — | USD |
| `EmbeddingsGigaR` | free | free | — | — | USD |
| `Qwen3-Coder-30B-A3B-Instruct-GGUF` | free | free | — | — | USD |
| `Gemma-3-4b-it-GGUF` | free | free | — | — | USD |
| `Qwen3-4B-Instruct-2507-GGUF` | free | free | — | — | USD |
| `codegeex4` | free | free | — | — | USD |
| `codegemma` | free | free | — | — | USD |
| `codellama` | free | free | — | — | USD |
| `internlm2_5-20b-chat` | free | free | — | — | USD |
| `llama2` | free | free | — | — | USD |
| `llama2-uncensored` | free | free | — | — | USD |
| `llama2:13b` | free | free | — | — | USD |
| `llama2:70b` | free | free | — | — | USD |
| `llama2:7b` | free | free | — | — | USD |
| `llama3` | free | free | — | — | USD |
| `llama3.1` | free | free | — | — | USD |
| `llama3:70b` | free | free | — | — | USD |
| `llama3:8b` | free | free | — | — | USD |
| `mistral` | free | free | — | — | USD |
| `mistral-7B-Instruct-v0.1` | free | free | — | — | USD |
| `mistral-7B-Instruct-v0.2` | free | free | — | — | USD |
| `mistral-large-instruct-2407` | free | free | — | — | USD |
| `mixtral-8x22B-Instruct-v0.1` | free | free | — | — | USD |
| `mixtral-8x7B-Instruct-v0.1` | free | free | — | — | USD |
| `orca-mini` | free | free | — | — | USD |
| `qwen3-coder:480b-cloud` | free | free | — | — | USD |
| `vicuna` | free | free | — | — | USD |
| `omni-moderation-2024-09-26` | free | free | — | — | USD |
| `omni-moderation-latest` | free | free | — | — | USD |
| `auto` | free | free | — | — | USD |
| `bodybuilder` | free | free | — | — | USD |
| `pplx-70b-online` | free | $2.80 | — | — | USD |
| `pplx-7b-online` | free | $0.28 | — | — | USD |
| `sonar-medium-online` | free | $1.80 | — | — | USD |
| `sonar-small-online` | free | $0.28 | — | — | USD |
| `apertus-8b-instruct` | free | free | — | — | USD |
| `apertus-70b-instruct` | free | free | — | — | USD |
| `Gemma-SEA-LION-v4-27B-IT` | free | free | — | — | USD |
| `salamandra-7b-instruct-tools-16k` | free | free | — | — | USD |
| `ALIA-40b-instruct_Q8_0` | free | free | — | — | USD |
| `Olmo-3-7B-Instruct` | free | free | — | — | USD |
| `Olmo-3-7B-Think` | free | free | — | — | USD |
| `Olmo-3-32B-Think` | free | free | — | — | USD |
| `rerank-english-v2.0` | free | free | — | — | USD |
| `rerank-english-v3.0` | free | free | — | — | USD |
| `rerank-multilingual-v2.0` | free | free | — | — | USD |
| `rerank-multilingual-v3.0` | free | free | — | — | USD |
| `rerank-v3.5` | free | free | — | — | USD |
| `nv-rerankqa-mistral-4b-v3` | free | free | — | — | USD |
| `llama-3_2-nv-rerankqa-1b-v2` | free | free | — | — | USD |
| `text-moderation-007` | free | free | — | — | USD |
| `text-moderation-latest` | free | free | — | — | USD |
| `text-moderation-stable` | free | free | — | — | USD |
| `Llama-3.3-70B-Instruct-Turbo-Free` | free | free | — | — | USD |
| `sarvam-m` | free | free | — | — | USD |
