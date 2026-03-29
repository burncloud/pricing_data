"""
Centralized configuration for LLM pricing data platform.
"""
import os
from dataclasses import dataclass, field
from datetime import timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# Ordered list of (model_id_prefix, provider_name) for provider inference.
# Used by infer_provider() — first match wins.
PROVIDER_PREFIXES: List[Tuple[str, str]] = [
    ("gpt-", "openai"),
    ("o1-", "openai"),
    ("o3-", "openai"),
    ("o4-", "openai"),
    ("text-embedding-", "openai"),
    ("dall-e-", "openai"),
    ("claude-", "anthropic"),
    ("gemini-", "google"),
    ("imagen-", "google"),
    ("deepseek-", "deepseek"),
    ("glm-", "zhipu"),
    ("chatglm-", "zhipu"),
    ("qwen-", "aliyun"),
    ("ernie-", "baidu"),
    ("spark-", "xunfei"),
    ("abab-", "minimax"),
    ("moonshot-", "moonshot"),
]


def infer_provider(model_id: str) -> str:
    """Infer provider name from model_id prefix.

    Falls back to the first path segment for slash-separated IDs
    (e.g. "openai/gpt-4o" -> "openai", "accounts/fireworks/models/llama" -> "fireworks").
    Returns "unknown" if no match.
    """
    if not model_id:
        return "unknown"
    lower = model_id.lower()
    for prefix, provider in PROVIDER_PREFIXES:
        if lower.startswith(prefix):
            return provider
    if "/" in model_id:
        parts = model_id.split("/")
        if parts[0] == "accounts" and len(parts) >= 2:
            return parts[1]
        return parts[0]
    return "unknown"


# Sources authorised to write modality-specific pricing (audio.*, image.*).
# LiteLLM and OpenRouter routinely omit or misattribute these fields, so they
# are blocked from writing them.  Only direct-provider fetchers and human-
# verified manual_overrides are trusted for modality pricing.
MODALITY_AUTHORITATIVE_SOURCES: frozenset = frozenset({
    "openai", "anthropic", "google", "deepseek",
    "zhipu", "aliyun", "baidu", "xunfei", "moonshot", "minimax",
    "manual_overrides",
})

# Anomaly detection thresholds ($/MTok). Prices strictly above these are rejected.
# Most expensive legitimate model today: claude-opus-4 at $75/MTok output.
# $200 gives ~2.7x safety margin for text. Image output can be higher.
PRICE_ANOMALY_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "text":  {"in": 200.0, "out": 200.0},
    "audio": {"in": 200.0, "out": 200.0},
    "image": {"in": 200.0, "out": 500.0},
    "video": {"in": 200.0, "out": 200.0},
}

# Minimum source priority for a model to be included in pricing.json.
# Sources at or above this threshold are considered "first-party verified".
FIRST_PARTY_PRIORITY_THRESHOLD: int = 100


@dataclass
class ProviderPricingRules:
    """
    Ratio-based derived pricing rules for a provider.

    Used when a provider's cache/batch prices are a fixed ratio of base prices,
    as documented in their official pricing docs (e.g. Zhipu's 50% cache discount).

    Source: https://docs.bigmodel.cn/cn/guide/capabilities/cache.md
            https://docs.bigmodel.cn/cn/guide/tools/batch.md
    """
    # cache_read_input_price = input_price * cache_read_ratio
    cache_read_ratio: Optional[float] = None
    # batch prices = base prices * batch_discount
    batch_discount: Optional[float] = None
    # Models that support batch API (None = all models)
    batch_supported_models: Optional[FrozenSet[str]] = None
    # Models that support cache (None = all models)
    cache_supported_models: Optional[FrozenSet[str]] = None


@dataclass
class FetcherConfig:
    """Configuration for a single data source fetcher."""
    name: str
    url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delays: List[float] = field(default_factory=lambda: [1.0, 2.0, 4.0])
    requires_auth: bool = False
    auth_env_var: Optional[str] = None
    # Endpoint-keyed pricing fields
    endpoint_key: str = ""    # domain key used in the "endpoints" dict (e.g. "api.openai.com")
    base_url: str = ""        # canonical API base URL for that endpoint
    currency: str = "USD"     # currency for prices from this endpoint

    @property
    def api_key(self) -> Optional[str]:
        """Get API key from environment if required."""
        if self.requires_auth and self.auth_env_var:
            return os.environ.get(self.auth_env_var)
        return None


@dataclass
class Config:
    """Global configuration for the pricing data platform."""

    # Paths
    repo_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    pricing_file: Path = field(init=False)
    schema_file: Path = field(init=False)
    sources_dir: Path = field(init=False)
    history_dir: Path = field(init=False)
    feed_file: Path = field(init=False)

    # History settings
    history_retention_days: int = 365

    # Price comparison thresholds
    price_drift_warning_threshold: float = 0.01  # 1%
    price_drift_critical_threshold: float = 0.50  # 50% (suspicious)

    # Timezone for timestamps
    timezone: timezone = field(default=timezone.utc)

    # Minimum model count guard — skip source if it returns fewer than this
    # (protects against broken fetches returning near-empty responses)
    # Set to 0 to disable for a source
    min_models_guard: Dict[str, int] = field(default_factory=lambda: {
        "openrouter": 50,   # OpenRouter normally has 300+ models
        "litellm": 500,     # LiteLLM normally has 2500+ models
    })

    # Source priority (higher = more authoritative)
    source_priority: Dict[str, int] = field(default_factory=lambda: {
        # Original providers (highest priority)
        "openai": 100,
        "anthropic": 100,
        "google": 100,
        "meta": 100,
        "mistral": 100,
        "deepseek": 100,
        # Chinese providers
        "zhipu": 100,
        "aliyun": 100,
        "baidu": 100,
        "xunfei": 100,
        "moonshot": 100,
        "minimax": 100,
        # Aggregators (lower priority)
        "openrouter": 50,
        # LiteLLM community aggregator (beats OpenRouter, below direct providers)
        "litellm": 70,
        # Manual overrides (highest priority — human-verified data)
        "manual_overrides": 200,
        "manual": 10,
    })

    # Fetchers configuration
    fetchers: Dict[str, FetcherConfig] = field(init=False)

    def __post_init__(self):
        # Ratio-based derived pricing rules per provider.
        # Populated from official provider docs — update when docs change.
        self.provider_pricing_rules: Dict[str, ProviderPricingRules] = {
            # Zhipu (智谱): cache read = 50%, batch = 50% of base prices.
            # Source: docs.bigmodel.cn/cn/guide/capabilities/cache.md
            #         docs.bigmodel.cn/cn/guide/tools/batch.md
            "zhipu": ProviderPricingRules(
                cache_read_ratio=0.5,
                batch_discount=0.5,
                batch_supported_models=frozenset({
                    "glm-4-plus", "glm-4-air-250414", "glm-4-flashx-250414",
                    "glm-4-long", "glm-4v-plus-0111", "glm-4v-plus",
                    "glm-4-0520", "glm-4", "glm-4v",
                }),
                # Cache: "支持所有主流模型" (all mainstream models)
                cache_supported_models=None,
            ),
        }

        self.data_dir = self.repo_root
        self.pricing_file = self.repo_root / "pricing.json"
        self.schema_file = self.repo_root / "schema.json"
        self.sources_dir = self.repo_root / "sources"
        self.history_dir = self.repo_root / "history"
        self.feed_file = self.repo_root / "feed.xml"

        self.fetchers = {
            "openai": FetcherConfig(
                name="openai",
                url="https://openai.com/api/pricing",
                timeout=60.0,   # Playwright needs more time than plain HTTP
                max_retries=1,  # No retry for browser automation
                requires_auth=False,
                endpoint_key="api.openai.com",
                base_url="https://api.openai.com/v1",
                currency="USD",
            ),
            "anthropic": FetcherConfig(
                name="anthropic",
                url="https://docs.anthropic.com/en/docs/about-claude/models/overview",
                timeout=30.0,
                max_retries=3,
                requires_auth=False,
                endpoint_key="api.anthropic.com",
                base_url="https://api.anthropic.com",
                currency="USD",
            ),
            "google": FetcherConfig(
                name="google",
                url="https://ai.google.dev/pricing",
                timeout=30.0,
                max_retries=3,
                requires_auth=False,
                endpoint_key="generativelanguage.googleapis.com",
                base_url="https://generativelanguage.googleapis.com",
                currency="USD",
            ),
            "deepseek": FetcherConfig(
                name="deepseek",
                url="https://api-docs.deepseek.com/quick_start/pricing",
                timeout=30.0,
                max_retries=3,
                requires_auth=False,
                endpoint_key="api.deepseek.com",
                base_url="https://api.deepseek.com/v1",
                currency="USD",
            ),
            "openrouter": FetcherConfig(
                name="openrouter",
                url="https://openrouter.ai/api/v1/models",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="OPENROUTER_API_KEY",
                endpoint_key="openrouter.ai",
                base_url="https://openrouter.ai/api/v1",
                currency="USD",
            ),
            "litellm": FetcherConfig(
                name="litellm",
                url="https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
                timeout=30.0,
                max_retries=3,
                requires_auth=False,
                endpoint_key="litellm",
                base_url="",
                currency="USD",
            ),
            "zhipu": FetcherConfig(
                name="zhipu",
                url="https://open.bigmodel.cn/pricing",
                timeout=45.0,
                max_retries=2,
                requires_auth=False,
                endpoint_key="open.bigmodel.cn",
                base_url="https://open.bigmodel.cn/api/paas/v4",
                currency="CNY",
            ),
            "aliyun": FetcherConfig(
                name="aliyun",
                url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="ALIYUN_API_KEY",
                endpoint_key="dashscope.aliyuncs.com",
                base_url="https://dashscope.aliyuncs.com/api/v1",
                currency="CNY",
            ),
            "baidu": FetcherConfig(
                name="baidu",
                url="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="BAIDU_API_KEY",
                endpoint_key="aip.baidubce.com",
                base_url="https://aip.baidubce.com",
                currency="CNY",
            ),
            "xunfei": FetcherConfig(
                name="xunfei",
                url="https://spark-api-open.xf-yun.com/v1/chat/completions",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="XUNFEI_API_KEY",
                endpoint_key="spark-api-open.xf-yun.com",
                base_url="https://spark-api-open.xf-yun.com/v1",
                currency="CNY",
            ),
            "moonshot": FetcherConfig(
                name="moonshot",
                url="https://api.moonshot.cn/v1/models",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="MOONSHOT_API_KEY",
                endpoint_key="api.moonshot.cn",
                base_url="https://api.moonshot.cn/v1",
                currency="CNY",
            ),
            "minimax": FetcherConfig(
                name="minimax",
                url="https://api.minimax.chat/v1/models",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="MINIMAX_API_KEY",
                endpoint_key="api.minimax.chat",
                base_url="https://api.minimax.chat/v1",
                currency="CNY",
            ),
        }

    def get_fetcher(self, name: str) -> Optional[FetcherConfig]:
        """Get fetcher configuration by name."""
        return self.fetchers.get(name)

    def get_source_priority(self, source: str) -> int:
        """Get priority for a source. Higher = more authoritative."""
        return self.source_priority.get(source, 0)

    def get_derived_pricing(
        self,
        provider: str,
        model_id: str,
        input_price: float,
        output_price: float,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Derive cache_pricing and batch_pricing from base prices using provider rules.

        Free models (input_price == 0 and output_price == 0) receive no derived pricing.
        Returns (cache_pricing, batch_pricing) — either may be None.
        """
        rules = self.provider_pricing_rules.get(provider)
        if not rules:
            return None, None

        cache_pricing = None
        if rules.cache_read_ratio is not None and input_price > 0:
            supported = rules.cache_supported_models
            if supported is None or model_id in supported:
                cache_pricing = {
                    "in": round(input_price * rules.cache_read_ratio, 6)
                }

        batch_pricing = None
        if rules.batch_discount is not None and (input_price > 0 or output_price > 0):
            supported = rules.batch_supported_models
            if supported is None or model_id in supported:
                batch_pricing = {
                    "in": round(input_price * rules.batch_discount, 6),
                    "out": round(output_price * rules.batch_discount, 6),
                }

        return cache_pricing, batch_pricing

    def get_today_sources_dir(self, date_str: str) -> Path:
        """Get sources directory for a specific date."""
        return self.sources_dir / date_str

    def get_history_file(self, date_str: str) -> Path:
        """Get history snapshot file for a specific date."""
        return self.history_dir / f"{date_str}.json"


# Global config instance
config = Config()
