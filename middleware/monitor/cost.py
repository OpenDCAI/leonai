"""模型成本计算

定价来源优先级：
1. OpenRouter API（启动时拉取，缓存到 ~/.leon/pricing_cache.json，24h TTL）
2. 本地 bundled 文件（pricing_bundled.json，随代码发布，离线兜底）
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

# 定价数据（运行时填充）
_pricing_data: dict[str, dict[str, Decimal]] = {}
_initialized = False

# 路径
_BUNDLED_PATH = Path(__file__).parent / "pricing_bundled.json"
_CACHE_PATH = Path.home() / ".leon" / "pricing_cache.json"
_CACHE_TTL = 86400  # 24 小时

M = Decimal("1000000")
_PER_TOKEN_TO_PER_M = Decimal("1000000")


def _parse_openrouter_model(model: dict[str, Any]) -> tuple[str, dict[str, Decimal]] | None:
    """从 OpenRouter 模型数据中提取定价

    OpenRouter pricing 字段是 per-token（字符串），转换为 per-1M-tokens（Decimal）。
    模型 ID 格式为 "provider/model-name"，提取 model-name 部分。
    """
    model_id = model.get("id", "")
    pricing = model.get("pricing")
    if not pricing or not model_id:
        return None

    prompt_price = pricing.get("prompt", "0")
    completion_price = pricing.get("completion", "0")

    # 跳过免费模型（无意义的定价数据）
    if prompt_price == "0" and completion_price == "0":
        return None

    try:
        input_per_m = Decimal(prompt_price) * _PER_TOKEN_TO_PER_M
        output_per_m = Decimal(completion_price) * _PER_TOKEN_TO_PER_M
    except Exception:
        return None

    cache_read_per_m = Decimal("0")
    cache_write_per_m = Decimal("0")
    if pricing.get("input_cache_read"):
        try:
            cache_read_per_m = Decimal(pricing["input_cache_read"]) * _PER_TOKEN_TO_PER_M
        except Exception:
            pass
    if pricing.get("input_cache_write"):
        try:
            cache_write_per_m = Decimal(pricing["input_cache_write"]) * _PER_TOKEN_TO_PER_M
        except Exception:
            pass

    # 兜底：OpenRouter 可能不返回缓存字段，但直连 API 时缓存有价格
    # 根据 provider 推断默认缓存价格
    if not cache_read_per_m or not cache_write_per_m:
        provider = model_id.split("/", 1)[0] if "/" in model_id else ""
        if provider == "anthropic":
            # Anthropic: cache_read = 0.1x input, cache_write = 1.25x input
            if not cache_read_per_m:
                cache_read_per_m = input_per_m * Decimal("0.1")
            if not cache_write_per_m:
                cache_write_per_m = input_per_m * Decimal("1.25")
        elif provider in ("openai", ""):
            # OpenAI: cache_read = 0.5x input (50% discount), cache_write = input (same price)
            if not cache_read_per_m:
                cache_read_per_m = input_per_m * Decimal("0.5")
            if not cache_write_per_m:
                cache_write_per_m = input_per_m
        elif provider == "deepseek":
            # DeepSeek: cache_read = 0.1x input, cache_write = input
            if not cache_read_per_m:
                cache_read_per_m = input_per_m * Decimal("0.1")
            if not cache_write_per_m:
                cache_write_per_m = input_per_m
        else:
            # 通用兜底：cache_read = 0.5x input, cache_write = input
            if not cache_read_per_m:
                cache_read_per_m = input_per_m * Decimal("0.5")
            if not cache_write_per_m:
                cache_write_per_m = input_per_m

    costs = {
        "input": input_per_m,
        "output": output_per_m,
        "cache_read": cache_read_per_m,
        "cache_write": cache_write_per_m,
    }

    # 提取 model-name（去掉 provider/ 前缀）
    short_name = model_id.split("/", 1)[-1] if "/" in model_id else model_id
    return short_name, costs


def _load_cache() -> dict[str, dict[str, str]] | None:
    """从磁盘缓存加载定价数据"""
    if not _CACHE_PATH.exists():
        return None
    try:
        data = json.loads(_CACHE_PATH.read_text())
        if time.time() - data.get("timestamp", 0) > _CACHE_TTL:
            return None
        return data.get("models", {})
    except Exception:
        return None


def _save_cache(models: dict[str, dict[str, str]]) -> None:
    """保存定价数据到磁盘缓存"""
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"timestamp": time.time(), "models": models}
        _CACHE_PATH.write_text(json.dumps(data))
    except Exception:
        pass


def _deserialize_costs(raw: dict[str, dict[str, str]]) -> dict[str, dict[str, Decimal]]:
    """将缓存中的字符串值转为 Decimal"""
    result = {}
    for model_name, costs in raw.items():
        try:
            result[model_name] = {k: Decimal(v) for k, v in costs.items()}
        except Exception:
            continue
    return result


def _serialize_costs(costs: dict[str, dict[str, Decimal]]) -> dict[str, dict[str, str]]:
    """将 Decimal 值转为字符串用于缓存"""
    return {model: {k: str(v) for k, v in c.items()} for model, c in costs.items()}


def fetch_openrouter_pricing() -> dict[str, dict[str, Decimal]]:
    """加载定价数据：API 缓存 → OpenRouter API → bundled 文件

    同步调用（启动时一次性），超时 5 秒。
    """
    global _pricing_data, _initialized

    if _initialized:
        return _pricing_data

    # 1. 尝试磁盘缓存（24h TTL）
    cached = _load_cache()
    if cached:
        _pricing_data = _deserialize_costs(cached)
        _initialized = True
        return _pricing_data

    # 2. 拉取 OpenRouter API
    try:
        import urllib.request

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "leon-agent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        models = data.get("data", [])
        result: dict[str, dict[str, Decimal]] = {}
        for model in models:
            parsed = _parse_openrouter_model(model)
            if parsed:
                name, costs = parsed
                if name not in result:
                    result[name] = costs

        if result:
            _pricing_data = result
            _save_cache(_serialize_costs(result))
            _initialized = True
            return _pricing_data
    except Exception:
        pass

    # 3. 加载 bundled 文件（最终兜底）
    _pricing_data = _load_bundled()
    _initialized = True
    return _pricing_data


def _load_bundled() -> dict[str, dict[str, Decimal]]:
    """从随代码发布的 pricing_bundled.json 加载"""
    if not _BUNDLED_PATH.exists():
        return {}
    try:
        data = json.loads(_BUNDLED_PATH.read_text())
        return _deserialize_costs(data.get("models", data))
    except Exception:
        return {}


class CostCalculator:
    """基于模型单价表计算 token 成本

    查找优先级：精确匹配 → 前缀匹配 → 空（不计费）
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.costs = self._resolve_costs(model_name)

    def _resolve_costs(self, model_name: str) -> dict[str, Decimal]:
        """解析模型单价"""
        # 1. 精确匹配
        if model_name in _pricing_data:
            return _pricing_data[model_name]

        # 2. 规范化匹配：Anthropic API 用 claude-sonnet-4-5-20250929，
        # OpenRouter 用 claude-sonnet-4.5，尝试去掉日期后缀 + 横杠转点号
        normalized = self._normalize_model_name(model_name)
        if normalized != model_name and normalized in _pricing_data:
            return _pricing_data[normalized]

        # 3. 前缀匹配（如 gpt-4o-2024-08-06 → gpt-4o）
        for key in sorted(_pricing_data.keys(), key=len, reverse=True):
            if model_name.startswith(key):
                return _pricing_data[key]

        return {}

    @staticmethod
    def _normalize_model_name(name: str) -> str:
        """规范化模型名：去日期后缀，版本号横杠转点号

        claude-sonnet-4-5-20250929 → claude-sonnet-4.5
        claude-haiku-4-5-20251001 → claude-haiku-4.5
        claude-opus-4-1-20250805 → claude-opus-4.1
        """
        import re

        # 去掉末尾的日期后缀 -YYYYMMDD
        name = re.sub(r"-\d{8}$", "", name)
        # 版本号横杠转点号：claude-sonnet-4-5 → claude-sonnet-4.5
        # 匹配 -数字-数字 结尾（版本号模式）
        name = re.sub(r"-(\d+)-(\d+)$", r"-\1.\2", name)
        return name

    def calculate(self, tokens: dict) -> dict:
        """返回各项成本（USD）

        Args:
            tokens: dict with keys input_tokens, output_tokens,
                    cache_read_tokens, cache_write_tokens
        Returns:
            {"total": Decimal, "breakdown": {...}}
        """
        if not self.costs:
            return {"total": Decimal("0"), "breakdown": {}}

        breakdown = {
            "input": self.costs.get("input", Decimal("0")) * Decimal(str(tokens.get("input_tokens", 0))) / M,
            "output": self.costs.get("output", Decimal("0")) * Decimal(str(tokens.get("output_tokens", 0))) / M,
            "cache_read": self.costs.get("cache_read", Decimal("0"))
            * Decimal(str(tokens.get("cache_read_tokens", 0)))
            / M,
            "cache_write": self.costs.get("cache_write", Decimal("0"))
            * Decimal(str(tokens.get("cache_write_tokens", 0)))
            / M,
        }
        return {"total": sum(breakdown.values()), "breakdown": breakdown}
