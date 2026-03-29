# TODOS

## P1 — Concurrent Fetcher Execution

**What:** `scripts/fetch_all.py` runs all 15 fetchers sequentially. Switch to `ThreadPoolExecutor` for parallel HTTP calls.

**Why:** With 15 fetchers, sequential execution takes ~15-30s on a fast connection but could degrade to 5-8 minutes if 3-4 Chinese sites time out. Parallelism would cap total time at `max(individual_fetcher_time)` instead of the sum.

**Context:** All fetchers already handle their own exceptions and return `FetchResult`. Thread safety is not a concern — each fetcher writes to its own file in `sources/{date}/`. The main risk is that Playwright fetchers (OpenAI, Zhipu) may not be thread-safe.

**Effort:** S (human ~2h / CC ~15 min)
**Priority:** P1
**Depends on:** Verify Playwright thread safety first (or keep Playwright fetchers sequential).

---

## P2 — Together AI / Fireworks AI Fetchers

**What:** Add first-party price fetchers for Together AI and Fireworks AI.

**Why:** Both are popular inference providers with many hosted models. Currently aggregator-only (LiteLLM/OpenRouter at p50/p70), so their models don't pass the admission gate.

**Context:** Together AI pricing page may require JS rendering. Fireworks AI has a pricing API endpoint. Deferred from v7.0 plan due to complexity.

**Effort:** L (human ~1 week / CC ~45 min per provider)
**Priority:** P2
**Depends on:** Nothing blocking.
