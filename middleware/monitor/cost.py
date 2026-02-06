"""模型成本计算

定价来源优先级：
1. OpenRouter API（启动时异步拉取，缓存到 ~/.leon/pricing_cache.json）
2. 本地 fallback 表（离线可用）
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

# ===== 本地 fallback 表（离线 / API 不可用时使用）=====
# 单价：USD per 1M tokens
_FALLBACK_COSTS: dict[str, dict[str, Decimal]] = {
    # Anthropic
    "claude-opus-4-6": {
        "input": Decimal("5.00"),
        "output": Decimal("25.00"),
        "cache_read": Decimal("0.50"),
        "cache_write": Decimal("6.25"),
    },
    "claude-sonnet-4-5-20250929": {
        "input": Decimal("3.00"),
        "output": Decimal("15.00"),
        "cache_read": Decimal("0.30"),
        "cache_write": Decimal("3.75"),
    },
    "claude-haiku-4-5-20251001": {
        "input": Decimal("1.00"),
        "output": Decimal("5.00"),
        "cache_read": Decimal("0.10"),
        "cache_write": Decimal("1.25"),
    },
    # OpenAI
    "gpt-4o": {
        "input": Decimal("2.50"),
        "output": Decimal("10.00"),
        "cache_read": Decimal("1.25"),
        "cache_write": Decimal("2.50"),
    },
    "gpt-4o-mini": {
        "input": Decimal("0.15"),
        "output": Decimal("0.60"),
        "cache_read": Decimal("0.075"),
        "cache_write": Decimal("0.15"),
    },
    "gpt-4.1": {
        "input": Decimal("2.00"),
        "output": Decimal("8.00"),
        "cache_read": Decimal("0.50"),
        "cache_write": Decimal("2.00"),
    },
    "gpt-4.1-mini": {
        "input": Decimal("0.40"),
        "output": Decimal("1.60"),
        "cache_read": Decimal("0.10"),
        "cache_write": Decimal("0.40"),
    },
    # DeepSeek
    "deepseek-chat": {
        "input": Decimal("0.28"),
        "output": Decimal("0.42"),
        "cache_read": Decimal("0.028"),
        "cache_write": Decimal("0.28"),
    },
}

# OpenRouter API 拉取的定价（运行时填充）
_openrouter_costs: dict[str, dict[str, Decimal]] = {}

# 缓存配置
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
    """从 OpenRouter API 拉取定价，带磁盘缓存

    同步调用（启动时一次性），超时 5 秒。
    返回 {model_name: {input, output, cache_read, cache_write}} per 1M tokens。
    """
    global _openrouter_costs

    # 1. 尝试磁盘缓存
    cached = _load_cache()
    if cached:
        _openrouter_costs = _deserialize_costs(cached)
        return _openrouter_costs

    # 2. 拉取 API
    try:
        import urllib.request

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "leon-agent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
    except Exception:
        return {}

    models = data.get("data", [])
    result: dict[str, dict[str, Decimal]] = {}
    for model in models:
        parsed = _parse_openrouter_model(model)
        if parsed:
            name, costs = parsed
            # 同名模型保留第一个（OpenRouter 按热度排序）
            if name not in result:
                result[name] = costs

    _openrouter_costs = result

    # 3. 写入缓存
    _save_cache(_serialize_costs(result))

    return result


class CostCalculator:
    """基于模型单价表计算 token 成本

    查找优先级：OpenRouter 缓存 → 本地 fallback → 前缀匹配 → 空（不计费）
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.costs = self._resolve_costs(model_name)

    def _resolve_costs(self, model_name: str) -> dict[str, Decimal]:
        """解析模型单价"""
        # 1. OpenRouter 精确匹配
        if model_name in _openrouter_costs:
            return _openrouter_costs[model_name]

        # 2. 本地 fallback 精确匹配
        if model_name in _FALLBACK_COSTS:
            return _FALLBACK_COSTS[model_name]

        # 3. OpenRouter 前缀匹配
        for key in sorted(_openrouter_costs.keys(), key=len, reverse=True):
            if model_name.startswith(key):
                return _openrouter_costs[key]

        # 4. 本地 fallback 前缀匹配
        for key in sorted(_FALLBACK_COSTS.keys(), key=len, reverse=True):
            if model_name.startswith(key):
                return _FALLBACK_COSTS[key]

        return {}

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
