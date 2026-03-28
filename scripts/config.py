"""
Centralized configuration for LLM pricing data platform.
"""
import os
from dataclasses import dataclass, field
from datetime import timezone
from pathlib import Path
from typing import Dict, List, Optional


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
    equivalence_file: Path = field(init=False)
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
        self.data_dir = self.repo_root
        self.pricing_file = self.repo_root / "pricing.json"
        self.schema_file = self.repo_root / "schema.json"
        self.equivalence_file = self.repo_root / "equivalence.json"
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
            ),
            "anthropic": FetcherConfig(
                name="anthropic",
                url="https://docs.anthropic.com/en/docs/about-claude/models/overview",
                timeout=30.0,
                max_retries=3,
                requires_auth=False,
            ),
            "google": FetcherConfig(
                name="google",
                url="https://ai.google.dev/pricing",
                timeout=30.0,
                max_retries=3,
                requires_auth=False,
            ),
            "deepseek": FetcherConfig(
                name="deepseek",
                url="https://api-docs.deepseek.com/quick_start/pricing",
                timeout=30.0,
                max_retries=3,
                requires_auth=False,
            ),
            "openrouter": FetcherConfig(
                name="openrouter",
                url="https://openrouter.ai/api/v1/models",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="OPENROUTER_API_KEY",
            ),
            "litellm": FetcherConfig(
                name="litellm",
                url="https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
                timeout=30.0,
                max_retries=3,
                requires_auth=False,
            ),
            "zhipu": FetcherConfig(
                name="zhipu",
                url="https://open.bigmodel.cn/api/paas/v4/models",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="ZHIPU_API_KEY",
            ),
            "aliyun": FetcherConfig(
                name="aliyun",
                url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="ALIYUN_API_KEY",
            ),
            "baidu": FetcherConfig(
                name="baidu",
                url="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="BAIDU_API_KEY",
            ),
            "xunfei": FetcherConfig(
                name="xunfei",
                url="https://spark-api-open.xf-yun.com/v1/chat/completions",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="XUNFEI_API_KEY",
            ),
            "moonshot": FetcherConfig(
                name="moonshot",
                url="https://api.moonshot.cn/v1/models",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="MOONSHOT_API_KEY",
            ),
            "minimax": FetcherConfig(
                name="minimax",
                url="https://api.minimax.chat/v1/models",
                timeout=30.0,
                max_retries=3,
                requires_auth=True,
                auth_env_var="MINIMAX_API_KEY",
            ),
        }

    def get_fetcher(self, name: str) -> Optional[FetcherConfig]:
        """Get fetcher configuration by name."""
        return self.fetchers.get(name)

    def get_source_priority(self, source: str) -> int:
        """Get priority for a source. Higher = more authoritative."""
        return self.source_priority.get(source, 0)

    def get_today_sources_dir(self, date_str: str) -> Path:
        """Get sources directory for a specific date."""
        return self.sources_dir / date_str

    def get_history_file(self, date_str: str) -> Path:
        """Get history snapshot file for a specific date."""
        return self.history_dir / f"{date_str}.json"


# Global config instance
config = Config()
