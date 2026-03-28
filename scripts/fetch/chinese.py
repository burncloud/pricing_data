"""
Chinese LLM providers fetcher.

Most Chinese LLM APIs do not expose pricing via REST endpoints.
This module uses Playwright to scrape provider pricing pages.

Priority: each fetcher saves with its provider name so config.source_priority applies:
    zhipu=100, aliyun=100, baidu=100, moonshot=100
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from scripts.config import Config
from scripts.fetch.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

# Per-million-token multiplier for prices given per thousand tokens
_PER_THOUSAND_TO_PER_MILLION = 1000

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available — Chinese provider fetchers will fail.")


def _run_playwright(url: str, timeout_ms: int = 45_000) -> Optional[str]:
    """
    Load a page with Playwright and return the rendered page text.
    Returns None if Playwright is unavailable or loading fails.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                locale="zh-CN",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            # Extra wait for React renders that happen after networkidle
            page.wait_for_timeout(2000)
            return page.inner_text("body")
        except Exception as e:
            logger.error(f"Playwright failed to load {url}: {e}")
            return None
        finally:
            browser.close()


class ZhipuFetcher(BaseFetcher):
    """
    Fetches Zhipu GLM pricing from https://open.bigmodel.cn/pricing.

    The page is a React SPA. We use Playwright to render it, then extract
    CNY prices from the visible text.

    Prices on the page are typically in CNY per thousand tokens — we convert
    to CNY per million tokens to match our standard format.
    """

    def __init__(self, config: Config):
        super().__init__(config, config.fetchers["zhipu"])

    # ------------------------------------------------------------------
    # BaseFetcher interface (not used — we override fetch() entirely)
    # ------------------------------------------------------------------

    def _make_request(self):
        return None

    def _validate_response(self, response) -> bool:
        return True

    def _parse_models(self, response) -> Dict[str, Any]:
        return {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def fetch(self) -> FetchResult:
        if not PLAYWRIGHT_AVAILABLE:
            return FetchResult.error_result("zhipu", "Playwright not available")

        logger.info(f"Scraping Zhipu pricing from {self.fetcher_config.url}")
        page_text = _run_playwright(self.fetcher_config.url)

        if page_text is None:
            return FetchResult.error_result("zhipu", "Playwright failed to load page")

        try:
            models = self._parse_page_text(page_text)
        except Exception as e:
            logger.exception("Zhipu pricing parse failed")
            return FetchResult.error_result("zhipu", f"Parse error: {e}")

        if not models:
            logger.warning("Zhipu: no models extracted from page")
            return FetchResult.error_result("zhipu", "No models found in page")

        logger.info(f"Zhipu: extracted {len(models)} models")
        return FetchResult(
            source="zhipu",
            success=True,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            models=models,
            models_count=len(models),
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Parsing (two section formats on bigmodel.cn)
    # ------------------------------------------------------------------

    # Section B — 模型推理 (standard models):
    #   Columns: model | desc | context | 单价 | Batch API
    #   Price format: "5 元 / 百万Tokens"
    #   Free model format: "免费" (no "元 / 百万Tokens" suffix)
    _STANDARD_PRICE_PAT = re.compile(
        r"(\d+(?:\.\d+)?)\s*元\s*/\s*百万Tokens"
    )

    def _parse_page_text(self, text: str) -> Dict[str, Any]:
        """
        Extract GLM model pricing from bigmodel.cn page text (rendered by Playwright).

        bigmodel.cn has two sections:

        A) 旗舰模型 (pos ~91 to ~1087):
           Separate input/output price columns. Prices: "4元", "0.5元", "免费".
           Tiered models: take first tier.  Unit: CNY / million tokens.

        B) 模型推理 (pos ~1087 to ~2166):
           Single 单价 column: "5 元 / 百万Tokens".
           input = output = 单价.  Free models: "免费".
        """
        models: Dict[str, Any] = {}

        # Locate section boundaries (positions are approximate — tolerate ±500 chars).
        flagship_start = text.find("旗舰模型")
        standard_start = text.find("模型推理")
        search_end = text.find("模型微调")

        if flagship_start != -1 and standard_start != -1:
            flagship_text = text[flagship_start:standard_start]
            standard_text = text[standard_start:search_end if search_end != -1 else len(text)]
        else:
            # Fallback: treat entire page as standard section
            flagship_text = ""
            standard_text = text

        # --- Section A: flagship models ---
        models.update(self._parse_flagship_section(flagship_text))

        # --- Section B: standard models ---
        for model_id, entry in self._parse_standard_section(standard_text).items():
            if model_id not in models:
                models[model_id] = entry

        return models

    # ---- Section A parser ----

    def _parse_flagship_section(self, text: str) -> Dict[str, Any]:
        """
        Parse 旗舰模型 section line by line.

        Strategy:
        - Find model name lines (match ^GLM-…)
        - For each model, collect lines until next model
        - Extract first two price tokens: "Nelem" or "免费" (not "限时免费")
        - First price = input, second = output
        """
        models: Dict[str, Any] = {}

        # Normalised (non-empty, non-tab) lines
        lines = [l.strip() for l in text.split("\n")]
        lines = [l for l in lines if l and l != "\t"]

        model_name_pat = re.compile(r"^(GLM-[\w.-]+)")
        price_pat = re.compile(r"^(\d+(?:\.\d+)?)元$")

        current_model: Optional[str] = None
        prices: list = []

        def _flush(name: str, prices: list) -> None:
            if len(prices) >= 2:
                model_id = name.lower()
                models[model_id] = self._make_entry(prices[0], prices[1])
                logger.debug(
                    f"Zhipu flagship: {model_id} CNY {prices[0]}/{prices[1]}"
                )

        for line in lines:
            name_m = model_name_pat.match(line)
            if name_m:
                # New model — flush the previous one
                if current_model:
                    _flush(current_model, prices)
                current_model = name_m.group(1)
                prices = []
                continue

            if current_model is None:
                continue

            # Skip tier descriptions and cache labels
            if "输入长度" in line or "输出长度" in line:
                continue
            if "限时免费" in line:
                continue
            # Free price
            if line == "免费":
                prices.append(0.0)
                continue
            # Numeric price like "4元" or "0.5元"
            p_m = price_pat.match(line)
            if p_m:
                prices.append(float(p_m.group(1)))

        # Flush last model
        if current_model:
            _flush(current_model, prices)

        return models

    # ---- Section B parser ----

    def _parse_standard_section(self, text: str) -> Dict[str, Any]:
        """
        Parse 模型推理 section.

        For each GLM model, find the first price in "N 元 / 百万Tokens" format
        (or "免费" on its own line) and use it as input = output price.
        """
        models: Dict[str, Any] = {}
        lines = [l.strip() for l in text.split("\n")]
        lines = [l for l in lines if l and l != "\t"]

        model_name_pat = re.compile(r"^(GLM-[\w.-]+)$")
        price_pat = self._STANDARD_PRICE_PAT

        current_model: Optional[str] = None
        found_price: Optional[float] = None

        for line in lines:
            name_m = model_name_pat.match(line)
            if name_m:
                # Flush previous if we had a price
                if current_model and found_price is not None:
                    model_id = current_model.lower()
                    if model_id not in models:
                        models[model_id] = self._make_entry(found_price, found_price)
                        logger.debug(
                            f"Zhipu standard: {model_id} CNY {found_price}/{found_price}"
                        )
                current_model = name_m.group(1)
                found_price = None
                continue

            if current_model is None or found_price is not None:
                continue

            # Match "N 元 / 百万Tokens"
            pm = price_pat.search(line)
            if pm:
                found_price = float(pm.group(1))
                continue

            # Match bare "免费"
            if line == "免费":
                found_price = 0.0

        # Flush last
        if current_model and found_price is not None:
            model_id = current_model.lower()
            if model_id not in models:
                models[model_id] = self._make_entry(found_price, found_price)

        return models

    def _parse_yuan(self, raw: Optional[str]) -> Optional[float]:
        """Convert price string to float. '免费' → 0.0."""
        if raw is None:
            return None
        raw = raw.strip()
        if raw == "免费":
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return None

    def _make_entry(self, input_price: float, output_price: float) -> Dict[str, Any]:
        metadata = {"provider": "zhipu", "family": "glm"}
        endpoint_entry = self._build_endpoint_entry(
            {
                "input_price": round(input_price, 6),
                "output_price": round(output_price, 6),
            },
        )
        return self._build_model_entry(endpoint_entry, metadata)
