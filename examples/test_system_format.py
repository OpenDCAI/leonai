#!/usr/bin/env python3
"""
最小示例：验证 yunyi 代理对 system 字段格式的要求。

问题：ChatAnthropic 发送 system 为字符串，yunyi 代理只接受数组格式。
测试：分别用 string 和 array 格式发送，确认哪个能通。
"""

import asyncio
import json
import os
from pathlib import Path

# 加载 .env
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

# 从 models.json 读取配置
models_json = Path.home() / ".leon" / "models.json"
config = json.loads(models_json.read_text())
anthropic_cfg = config["providers"]["anthropic"]
API_KEY = anthropic_cfg["api_key"]
BASE_URL = anthropic_cfg["base_url"]  # https://yunyi.rdzhvip.com/claude
MODEL = "claude-sonnet-4-5-20250929"

print(f"Base URL: {BASE_URL}")
print(f"Model:    {MODEL}")
print(f"API Key:  {API_KEY[:8]}...{API_KEY[-4:]}")
print()


# ── Test 1: 原生 anthropic SDK，string 格式（预期失败）──────────
async def test_string_system():
    """用 string 格式的 system，预期 400 错误。"""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=API_KEY, base_url=BASE_URL)
    print("=" * 60)
    print("Test 1: system = string（当前 ChatAnthropic 的默认行为）")
    print("=" * 60)
    try:
        resp = await client.messages.create(
            model=MODEL,
            max_tokens=50,
            system="You are a helpful assistant.",  # string 格式
            messages=[{"role": "user", "content": "Say hi in 5 words."}],
        )
        print(f"✅ 成功: {resp.content[0].text}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()


# ── Test 2: 原生 anthropic SDK，array 格式（预期成功）──────────
async def test_array_system():
    """用 array 格式的 system，预期成功。"""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=API_KEY, base_url=BASE_URL)
    print("=" * 60)
    print("Test 2: system = array（修复方案）")
    print("=" * 60)
    try:
        resp = await client.messages.create(
            model=MODEL,
            max_tokens=50,
            system=[{"type": "text", "text": "You are a helpful assistant."}],  # array 格式
            messages=[{"role": "user", "content": "Say hi in 5 words."}],
        )
        print(f"✅ 成功: {resp.content[0].text}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()


# ── Test 3: LangChain ChatAnthropic，默认行为（预期失败）──────
async def test_langchain_default():
    """LangChain ChatAnthropic 默认发送 string system。"""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    print("=" * 60)
    print("Test 3: LangChain ChatAnthropic 默认行为")
    print("=" * 60)
    try:
        llm = ChatAnthropic(
            model=MODEL,
            api_key=API_KEY,
            base_url=BASE_URL,
            max_tokens=50,
        )
        resp = await llm.ainvoke(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="Say hi in 5 words."),
            ]
        )
        print(f"✅ 成功: {resp.content}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()


# ── Test 4: LangChain + cache_control（强制 array 格式）──────
async def test_langchain_with_cache():
    """开启 cache_control 后，system 会变成 array 格式。"""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    print("=" * 60)
    print("Test 4: LangChain ChatAnthropic + cache_control")
    print("=" * 60)
    try:
        llm = ChatAnthropic(
            model=MODEL,
            api_key=API_KEY,
            base_url=BASE_URL,
            max_tokens=50,
            cache_control={"type": "ephemeral", "ttl": "5m"},
        )
        resp = await llm.ainvoke(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="Say hi in 5 words."),
            ]
        )
        print(f"✅ 成功: {resp.content}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()


# ── Test 5: LangChain + SystemMessage content 用 list 格式 ──────
async def test_langchain_content_blocks():
    """SystemMessage.content 传 list of content blocks，强制 array 格式。"""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    print("=" * 60)
    print("Test 5: LangChain SystemMessage content = list of blocks")
    print("=" * 60)
    try:
        llm = ChatAnthropic(
            model=MODEL,
            api_key=API_KEY,
            base_url=BASE_URL,
            max_tokens=50,
        )
        # content 传 list 而非 string → ChatAnthropic 会用 array 格式发送 system
        resp = await llm.ainvoke(
            [
                SystemMessage(content=[{"type": "text", "text": "You are a helpful assistant."}]),
                HumanMessage(content="Say hi in 5 words."),
            ]
        )
        print(f"✅ 成功: {resp.content}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()


# ── Test 6: LangChain init_chat_model（模拟 Leon 实际用法）──────
async def test_langchain_init_chat_model():
    """用 init_chat_model 创建模型（Leon 的实际方式），content blocks 格式。"""
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage

    print("=" * 60)
    print("Test 6: init_chat_model + content blocks（模拟 Leon）")
    print("=" * 60)
    try:
        llm = init_chat_model(
            MODEL,
            model_provider="anthropic",
            api_key=API_KEY,
            base_url=BASE_URL,
            max_tokens=50,
        )
        resp = await llm.ainvoke(
            [
                SystemMessage(content=[{"type": "text", "text": "You are a helpful assistant."}]),
                HumanMessage(content="Say hi in 5 words."),
            ]
        )
        print(f"✅ 成功: {resp.content}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    print()


async def main():
    await test_string_system()
    await test_array_system()
    await test_langchain_default()
    await test_langchain_with_cache()
    await test_langchain_content_blocks()
    await test_langchain_init_chat_model()

    print("=" * 60)
    print("结论")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
