# AI Model Pricing

*Updated: 2026-03-29 &nbsp;·&nbsp; 42 models &nbsp;·&nbsp; [Raw JSON](pricing.json)*

> Prices are **per million tokens (MTok)** unless noted.  
> USD prices in **$**, CNY prices in **¥**.  
> Jump to: [Quick Reference](#quick-reference) · [All Providers](#providers)

## Quick Reference

Most-used models across major providers. Cache Read and Batch In are per MTok.

| Model | Provider | Input | Output | Cache Read | Batch In | Currency |
|-------|----------|------:|-------:|-----------:|---------:|---------|
| `claude-opus-4-6` | Anthropic | $5.00 | $25.00 | — | — | USD |
| `claude-sonnet-4-6` | Anthropic | $3.00 | $15.00 | — | — | USD |
| `gemini-2.5-pro` | Google | $1.25 | $10.00 | $0.12 | — | USD |
| `gemini-2.0-flash` | Google | $0.10 | $0.40 | $0.025 | — | USD |
| `gemini-2.0-flash-lite` | Google | $0.075 | $0.30 | — | — | USD |
| `deepseek-chat` | DeepSeek | $0.28 | $0.42 | $0.028 | — | USD |
| `deepseek-reasoner` | DeepSeek | $0.28 | $0.42 | $0.028 | — | USD |
| `glm-4-plus` | Zhipu AI (智谱) | ¥5.00 | ¥5.00 | ¥2.50 | ¥2.50 | CNY |
| `glm-4.7-flash` | Zhipu AI (智谱) | $0.070 | $0.40 | $0.035 | — | USD |

> Cache / Batch columns appear only when at least one model in the section offers them.

## Providers

| Provider | Models |
|----------|-------:|
| [Anthropic](#anthropic) | 3 |
| [OpenAI](#openai) | 3 |
| [Google](#google) | 17 |
| [DeepSeek](#deepseek) | 2 |
| [Zhipu AI (智谱)](#zhipu-ai--智谱) | 17 |

## Anthropic

| Model | Input | Output | Currency |
|-------|------:|-------:|---------|
| `claude-opus-4-6` | $5.00 | $25.00 | USD |
| `claude-sonnet-4-6` | $3.00 | $15.00 | USD |
| `claude-haiku-4-5-20251001` | $1.00 | $5.00 | USD |

## OpenAI

| Model | Input | Output | Cache Read | Currency |
|-------|------:|-------:|----------:|---------|
| `gpt-5.4` | $2.50 | $15.00 | $0.25 | USD |
| `gpt-5.4-mini` | $0.75 | $4.50 | $0.075 | USD |
| `gpt-5.4-nano` | $0.20 | $1.25 | $0.020 | USD |

## Google

| Model | Input | Output | Cache Read | Batch In | Batch Out | Currency |
|-------|------:|-------:|----------:|---------:|----------:|---------|
| `gemini-3-pro-image-preview` | $2.00 | $12.00 | — | $1.00 | $6.00 | USD |
| `gemini-3.1-pro-preview` | $2.00 | $12.00 | $0.20 | — | — | USD |
| `gemini-2.5-pro` | $1.25 | $10.00 | $0.12 | — | — | USD |
| `gemini-2.5-computer-use-preview` | $1.25 | $10.00 | — | — | — | USD |
| `gemini-2.5-pro-preview-tts` | $1.00 | — | — | — | — | USD |
| `gemini-3.1-flash-live-preview` | $0.75 | $4.50 | — | — | — | USD |
| `gemini-3.1-flash-image-preview` | $0.50 | $3.00 | — | $0.25 | $1.50 | USD |
| `gemini-2.5-flash-preview-tts` | $0.50 | — | — | — | — | USD |
| `gemini-3-flash-preview` | $0.50 | $3.00 | $0.050 | — | — | USD |
| `gemini-2.5-flash-native-audio` | $0.50 | $2.00 | — | — | — | USD |
| `gemini-2.5-flash-image` | $0.30 | $2.50 | — | $0.15 | $1.25 | USD |
| `gemini-2.5-flash` | $0.30 | $2.50 | $0.030 | — | — | USD |
| `gemini-3.1-flash-lite-preview` | $0.25 | $1.50 | $0.025 | — | — | USD |
| `gemini-2.5-flash-lite` | $0.10 | $0.40 | $0.010 | — | — | USD |
| `gemini-2.5-flash-lite-preview` | $0.10 | $0.40 | $0.010 | — | — | USD |
| `gemini-2.0-flash` | $0.10 | $0.40 | $0.025 | — | — | USD |
| `gemini-2.0-flash-lite` | $0.075 | $0.30 | — | — | — | USD |

## DeepSeek

| Model | Input | Output | Cache Read | Currency |
|-------|------:|-------:|----------:|---------|
| `deepseek-chat` | $0.28 | $0.42 | $0.028 | USD |
| `deepseek-reasoner` | $0.28 | $0.42 | $0.028 | USD |

## Zhipu AI (智谱)

| Model | Input | Output | Cache Read | Batch In | Batch Out | Currency |
|-------|------:|-------:|----------:|---------:|----------:|---------|
| `glm-4-airx` | ¥10.00 | ¥10.00 | ¥5.00 | — | — | CNY |
| `glm-4-plus` | ¥5.00 | ¥5.00 | ¥2.50 | ¥2.50 | ¥2.50 | CNY |
| `glm-4-assistant` | ¥5.00 | ¥5.00 | ¥2.50 | — | — | CNY |
| `glm-z1-airx` | ¥5.00 | ¥5.00 | ¥2.50 | — | — | CNY |
| `glm-5-turbo` | $1.20 | $4.00 | $0.60 | — | — | USD |
| `glm-4-long` | ¥1.00 | ¥1.00 | ¥0.50 | ¥0.50 | ¥0.50 | CNY |
| `glm-5` | $0.80 | $2.56 | $0.40 | — | — | USD |
| `glm-4.7-flashx` | ¥0.50 | ¥3.00 | ¥0.25 | — | — | CNY |
| `glm-4-air-250414` | ¥0.50 | ¥0.50 | ¥0.25 | ¥0.25 | ¥0.25 | CNY |
| `glm-z1-air` | ¥0.50 | ¥0.50 | ¥0.25 | — | — | CNY |
| `glm-4.7` | $0.40 | $1.50 | $0.20 | — | — | USD |
| `glm-4.5-air` | $0.20 | $1.10 | $0.10 | — | — | USD |
| `glm-z1-flashx` | ¥0.10 | ¥0.10 | ¥0.050 | — | — | CNY |
| `glm-4-flashx-250414` | ¥0.10 | ¥0.10 | ¥0.050 | ¥0.050 | ¥0.050 | CNY |
| `glm-4.7-flash` | $0.070 | $0.40 | $0.035 | — | — | USD |
| `glm-4-flash-250414` | free | free | — | — | — | CNY |
| `glm-z1-flash` | free | free | — | — | — | CNY |
