# TODOS

## P2 — Field-Level Enrichment in merge.py

**What:** After priority-based source selection, enrich winning model entry with `batch_pricing`/`tiered_pricing` from any lower-priority source that has them.

**Why:** Currently LiteLLM (priority 70) wins over OpenRouter (50) for all overlapping models, so batch_pricing is included correctly. But when direct provider fetchers at priority 100 (Anthropic, OpenAI) are added, they'll overwrite LiteLLM's entry entirely — and `batch_pricing`/`tiered_pricing` will disappear.

**Context:** `scripts/merge.py` `_merge_with_priority()` selects the highest-priority source for the full model entry. Adding a field-enrichment pass after selection would copy missing `batch_pricing`/`tiered_pricing` from any source. This is a new codepath with new tests needed.

**Effort:** M (human ~1 day / CC ~15 min)
**Priority:** P2
**Depends on:** Direct provider fetchers being added (priority 100)

---

## P3 — Direct Provider Fetchers (Anthropic, OpenAI, Google)

**What:** Write `scripts/fetch/anthropic.py`, `scripts/fetch/openai.py`, `scripts/fetch/google.py` that fetch pricing from official provider documentation/APIs.

**Why:** LiteLLM batch/tiered data can be 3-5 days stale. Direct fetchers would give same-day accuracy. Also enables the field-level enrichment pattern (P2 above).

**Context:** Provider pricing APIs don't exist — this requires HTML scraping of pricing pages OR accepting LiteLLM latency. LiteLLM is community-maintained and has historically been accurate. Direct fetchers are fragile (break on page layout changes).

**Effort:** XL (human ~1 week / CC ~60 min, each provider has different page structure)
**Priority:** P3
**Depends on:** Nothing. But P2 (field enrichment) should be done first.
