# TODOS

## P1 — Fix OpenAI Playwright Fetcher

**What:** `scripts/fetch/openai.py` fails in CI with Playwright timeout (`waiting for locator("text=/1M tokens/") to be visible`). OpenAI pricing page structure changed. 144 OpenAI models are currently aggregator-only.

**Why:** OpenAI is the most-referenced provider. Accurate first-party prices matter. Currently relying solely on LiteLLM/OpenRouter for OpenAI pricing.

**Context:** Anthropic, Google, DeepSeek fetchers are working. OpenAI alone is broken. Options: (a) fix the Playwright selector to match current page structure, (b) switch to scraping the OpenAI pricing API endpoint if one exists, (c) expand manual_overrides.json to cover key OpenAI models with verified prices.

**Effort:** M (human ~2h / CC ~20 min)
**Priority:** P1
**Depends on:** Nothing.

---

## P2 — Chinese Providers Beyond Zhipu

**What:** Add fetchers for Baidu (文心), Moonshot (Kimi), MiniMax, Qwen/DashScope with direct CNY pricing.

**Why:** These are listed in the design doc as targets. Currently only Zhipu (bigmodel.cn) has a direct fetcher. Other Chinese providers are aggregator-only.

**Context:** Zhipu required Playwright + custom parser. Other providers likely need similar approaches. DashScope has an API. Moonshot has a pricing page.

**Effort:** XL (human ~1 week / CC ~60 min per provider)
**Priority:** P2
**Depends on:** Nothing blocking.
