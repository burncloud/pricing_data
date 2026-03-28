# TODOS

## P2 — Field-Level Enrichment in merge.py

**What:** After priority-based source selection, enrich winning model entry with `batch_pricing`/`tiered_pricing` from any lower-priority source that has them.

**Why:** Anthropic (priority 100), Google (priority 100), DeepSeek (priority 100) are now live. They win over LiteLLM (priority 70), so LiteLLM's `batch_pricing`/`tiered_pricing` gets silently dropped for any model those fetchers cover.

**Context:** `scripts/merge.py` `_merge_with_priority()` selects the highest-priority source for the full model entry. A field-enrichment pass after `_merge_endpoints` would copy missing pricing fields from lower-priority sources. New codepath, new tests needed. The `_merge_endpoints` mechanism (already in place) handles endpoint-level merging — this is the pricing-field-level complement.

**Effort:** M (human ~1 day / CC ~15 min)
**Priority:** P2 — NOW URGENT (Anthropic/Google/DeepSeek at priority 100 are live)
**Depends on:** Nothing blocking. Anthropic, Google, DeepSeek fetchers are already shipping.

---

## P3 — Fix OpenAI Playwright Fetcher

**What:** `scripts/fetch/openai.py` fails in CI with Playwright timeout (`waiting for locator("text=/1M tokens/") to be visible`). OpenAI pricing page structure changed. 144 OpenAI models are currently aggregator-only.

**Why:** OpenAI is the most-referenced provider. Accurate first-party prices matter. Currently relying solely on LiteLLM/OpenRouter for OpenAI pricing.

**Context:** Anthropic, Google, DeepSeek fetchers are working. OpenAI alone is broken. Options: (a) fix the Playwright selector to match current page structure, (b) switch to scraping the OpenAI pricing API endpoint if one exists, (c) expand manual_overrides.json to cover key OpenAI models with verified prices.

**Effort:** M (human ~2h / CC ~20 min)
**Priority:** P3
**Depends on:** Nothing.

---

## P4 — Chinese Providers Beyond Zhipu

**What:** Add fetchers for Baidu (文心), Moonshot (Kimi), MiniMax, Qwen/DashScope with direct CNY pricing.

**Why:** These are listed in the design doc as targets. Currently only Zhipu (bigmodel.cn) has a direct fetcher. Other Chinese providers are aggregator-only.

**Context:** Zhipu required Playwright + custom parser. Other providers likely need similar approaches. DashScope has an API. Moonshot has a pricing page.

**Effort:** XL (human ~1 week / CC ~60 min per provider)
**Priority:** P4
**Depends on:** Nothing blocking.
