#!/usr/bin/env python3
"""
验证 Thinking/Reasoning 在不同 Provider 下的行为：
1. 输入侧：各 provider 开启 thinking 的参数差异
2. 输出侧：content_blocks 是否能统一解析 reasoning

结论模板：
- Anthropic: thinking={"type":"enabled"} → content 里 {"type":"thinking"} → content_blocks 转为 {"type":"reasoning"}
- OpenAI:    reasoning_effort="medium"   → additional_kwargs["reasoning"] → content_blocks 转为 {"type":"reasoning"}
- DeepSeek:  始终开启                     → additional_kwargs["reasoning_content"] → content_blocks 转为 {"type":"reasoning"}
"""

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
openai_cfg = config["providers"].get("openai", {})

ANTHROPIC_KEY = anthropic_cfg["api_key"]
ANTHROPIC_URL = anthropic_cfg["base_url"]
OPENAI_KEY = openai_cfg.get("api_key", "")
OPENAI_URL = openai_cfg.get("base_url", "")

QUESTION = "What is 17 * 19? Think step by step."


def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def inspect_response(resp):
    """统一检查 response 的各个字段，对比 raw content vs content_blocks。"""
    print(f"\n  [type] {type(resp).__name__}")

    # 1) raw content
    print(f"\n  --- raw content (type={type(resp.content).__name__}) ---")
    if isinstance(resp.content, list):
        for i, block in enumerate(resp.content):
            if isinstance(block, dict):
                btype = block.get("type", "?")
                preview = str(block.get("thinking") or block.get("text") or block.get("reasoning") or "")[:120]
                print(f"    [{i}] type={btype}  preview={preview!r}")
            else:
                print(f"    [{i}] {str(block)[:120]!r}")
    else:
        print(f"    {str(resp.content)[:200]!r}")

    # 2) additional_kwargs (DeepSeek/OpenAI reasoning 落在这里)
    ak = resp.additional_kwargs
    if ak:
        print(f"\n  --- additional_kwargs keys: {list(ak.keys())} ---")
        if "reasoning_content" in ak:
            print(f"    reasoning_content: {str(ak['reasoning_content'])[:200]!r}")
        if "reasoning" in ak:
            print(f"    reasoning: {str(ak['reasoning'])[:200]!r}")

    # 3) content_blocks — 统一抽象层
    print("\n  --- content_blocks (统一格式) ---")
    for i, block in enumerate(resp.content_blocks):
        btype = block.get("type", "?")
        if btype == "reasoning":
            preview = str(block.get("reasoning", ""))[:120]
            extras = block.get("extras", {})
            print(
                f"    [{i}] type=reasoning  preview={preview!r}  extras_keys={list(extras.keys()) if extras else '[]'}"
            )
        elif btype == "text":
            print(f"    [{i}] type=text  text={str(block.get('text', ''))[:120]!r}")
        else:
            print(f"    [{i}] type={btype}  {str(block)[:120]}")

    # 4) .text 属性 — 只取 text 块
    print("\n  --- .text (纯文本) ---")
    print(f"    {resp.text!r}")
    print()


# ── Test 1: Anthropic thinking=enabled ──────────────────────────────
async def test_anthropic_thinking_enabled():
    """Anthropic 开启 thinking，验证 content 里出现 thinking block。"""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    print_header("Test 1: Anthropic thinking=enabled (budget_tokens=5000)")
    try:
        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            api_key=ANTHROPIC_KEY,
            base_url=ANTHROPIC_URL,
            max_tokens=8000,
            thinking={"type": "enabled", "budget_tokens": 5000},
        )
        resp = await llm.ainvoke(
            [
                SystemMessage(content=[{"type": "text", "text": "You are a math tutor."}]),
                HumanMessage(content=QUESTION),
            ]
        )
        print("  ✅ 成功")
        inspect_response(resp)
    except Exception as e:
        print(f"  ❌ 失败: {e}")


# ── Test 2: Anthropic thinking=disabled ─────────────────────────────
async def test_anthropic_thinking_disabled():
    """Anthropic 关闭 thinking，验证 content 里没有 thinking block。"""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    print_header("Test 2: Anthropic thinking=disabled (对照组)")
    try:
        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            api_key=ANTHROPIC_KEY,
            base_url=ANTHROPIC_URL,
            max_tokens=200,
        )
        resp = await llm.ainvoke(
            [
                SystemMessage(content=[{"type": "text", "text": "You are a math tutor."}]),
                HumanMessage(content=QUESTION),
            ]
        )
        print("  ✅ 成功")
        inspect_response(resp)
    except Exception as e:
        print(f"  ❌ 失败: {e}")


# ── Test 3: init_chat_model + Anthropic thinking ────────────────────
async def test_init_chat_model_anthropic():
    """用 init_chat_model（Leon 实际方式）开启 thinking。"""
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage

    print_header("Test 3: init_chat_model + Anthropic thinking (模拟 Leon)")
    try:
        llm = init_chat_model(
            "claude-sonnet-4-5-20250929",
            model_provider="anthropic",
            api_key=ANTHROPIC_KEY,
            base_url=ANTHROPIC_URL,
            max_tokens=8000,
            thinking={"type": "enabled", "budget_tokens": 5000},
        )
        resp = await llm.ainvoke(
            [
                SystemMessage(content=[{"type": "text", "text": "You are a math tutor."}]),
                HumanMessage(content=QUESTION),
            ]
        )
        print("  ✅ 成功")
        inspect_response(resp)
    except Exception as e:
        print(f"  ❌ 失败: {e}")


# ── Test 4: Anthropic 运行时覆盖 thinking ───────────────────────────
async def test_anthropic_runtime_override():
    """创建时不开 thinking，invoke 时动态开启。"""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    print_header("Test 4: Anthropic 运行时覆盖 (invoke 时传 thinking)")
    try:
        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            api_key=ANTHROPIC_KEY,
            base_url=ANTHROPIC_URL,
            max_tokens=8000,
        )
        # invoke 时动态开启 thinking
        resp = await llm.ainvoke(
            [
                SystemMessage(content=[{"type": "text", "text": "You are a math tutor."}]),
                HumanMessage(content=QUESTION),
            ],
            thinking={"type": "enabled", "budget_tokens": 5000},
        )
        print("  ✅ 成功 — invoke 时动态开启 thinking 可行")
        inspect_response(resp)
    except Exception as e:
        print(f"  ❌ 失败: {e}")


# ── Test 5: Anthropic streaming + thinking ──────────────────────────
async def test_anthropic_streaming_thinking():
    """Streaming 模式下 thinking 的输出格式。"""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    print_header("Test 5: Anthropic streaming + thinking")
    try:
        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            api_key=ANTHROPIC_KEY,
            base_url=ANTHROPIC_URL,
            max_tokens=8000,
            thinking={"type": "enabled", "budget_tokens": 5000},
        )
        print("  Streaming chunks:")
        thinking_chunks = 0
        text_chunks = 0
        async for chunk in llm.astream(
            [
                SystemMessage(content=[{"type": "text", "text": "You are a math tutor."}]),
                HumanMessage(content=QUESTION),
            ]
        ):
            if isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, dict):
                        if block.get("type") == "thinking":
                            thinking_chunks += 1
                        elif block.get("type") == "text":
                            text_chunks += 1
            elif isinstance(chunk.content, str) and chunk.content:
                text_chunks += 1

        print(f"  ✅ 成功 — thinking chunks: {thinking_chunks}, text chunks: {text_chunks}")
        print("  最终 chunk content_blocks:")
        for i, block in enumerate(chunk.content_blocks):
            btype = block.get("type", "?")
            print(f"    [{i}] type={btype}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")


# ── Test 6: OpenAI 兼容 (DeepSeek R1 等) ───────────────────────────
async def test_openai_deepseek():
    """通过 OpenAI 兼容接口调 DeepSeek，验证 reasoning_content 解析。"""
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI

    if not OPENAI_KEY:
        print_header("Test 6: OpenAI/DeepSeek (跳过 — 无 OpenAI key)")
        return

    print_header("Test 6: OpenAI 兼容 — deepseek-chat (如果可用)")
    try:
        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=OPENAI_KEY,
            base_url=OPENAI_URL + "/v1" if not OPENAI_URL.endswith("/v1") else OPENAI_URL,
            max_tokens=500,
        )
        resp = await llm.ainvoke([HumanMessage(content=QUESTION)])
        print("  ✅ 成功")
        inspect_response(resp)
    except Exception as e:
        print(f"  ❌ 失败 (可能模型不可用): {e}")


# ── main ────────────────────────────────────────────────────────────
async def main():
    await test_anthropic_thinking_enabled()
    await test_anthropic_thinking_disabled()
    await test_init_chat_model_anthropic()
    await test_anthropic_runtime_override()
    await test_anthropic_streaming_thinking()
    await test_openai_deepseek()

    print_header("总结")
    print("""
  输入侧（开启 thinking 的参数）：
    Anthropic:  thinking={"type": "enabled", "budget_tokens": N}
    OpenAI:     reasoning_effort="medium" 或 reasoning={"effort": "medium"}
    DeepSeek:   无需配置（R1 始终开启）

  输出侧（统一读取）：
    所有 provider → response.content_blocks → [{"type": "reasoning", ...}, {"type": "text", ...}]
    纯文本 → response.text（自动过滤 reasoning）

  Leon 需要做的：
    1. 配置侧：全局 thinking: bool 开关 → 按 provider 映射参数
    2. 展示侧：遍历 content_blocks，type=reasoning 的展示为折叠思考过程
    """)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
