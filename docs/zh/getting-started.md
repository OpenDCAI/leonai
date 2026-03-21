[English](../en/getting-started.md) | 中文

# Mycel 快速上手

Mycel 是一个具备持久记忆、终端界面（TUI）和 Web 界面的主动式 AI 编程助手。它支持多种 LLM 提供商，并具备沙箱代码执行、时间旅行调试和多智能体通信等功能。

## 安装

需要 Python 3.12 或更高版本。

### 从 PyPI 安装

```bash
pip install leonai
```

或使用 [uv](https://docs.astral.sh/uv/)（推荐）：

```bash
uv tool install leonai
```

### 从源码安装

```bash
git clone https://github.com/Ju-Yi-AI-Lab/leonai.git
cd leonai
uv tool install .
```

### 可选扩展

安装额外功能的扩展包：

```bash
# PDF 和 PowerPoint 文件读取
pip install "leonai[docs]"

# 沙箱提供商
pip install "leonai[sandbox]"     # AgentBay
pip install "leonai[e2b]"         # E2B
pip install "leonai[daytona]"     # Daytona

# 可观测性
pip install "leonai[langfuse]"
pip install "leonai[langsmith]"

# 全部安装
pip install "leonai[all]"
```

## 首次运行与配置

首次启动 Mycel：

```bash
leonai
```

如果未检测到 API 密钥，交互式配置向导会自动启动。它会询问三项内容：

1. **API_KEY**（必填）—— 你的 OpenAI 兼容 API 密钥。会存储为 `OPENAI_API_KEY`。
2. **BASE_URL**（可选）—— API 端点。默认为 `https://api.openai.com/v1`。向导会自动补齐 `/v1` 后缀。
3. **MODEL_NAME**（可选）—— 使用的模型。默认为 `claude-sonnet-4-5-20250929`。

你可以随时重新运行配置向导：

```bash
leonai config
```

查看当前配置：

```bash
leonai config show
```

配置存储在 `~/.leon/config.env` 中，采用简单的 `KEY=VALUE` 格式。

## LLM 提供商设置

Mycel 使用 OpenAI 兼容的 API 格式。任何支持该协议的提供商都可以直接使用。

### 配置方式

**方式一：配置文件**（推荐用于持久化设置）

运行 `leonai config`，输入你的提供商 API 密钥和 Base URL。

**方式二：环境变量**（优先级高于配置文件）

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
```

环境变量优先于 `~/.leon/config.env` 中的配置。

### 提供商示例

#### OpenAI

```
API_KEY:    sk-...
BASE_URL:   https://api.openai.com/v1
MODEL_NAME: gpt-4o
```

#### Anthropic Claude（通过 OpenAI 兼容代理）

Claude 模型通过 OpenAI 兼容代理使用（例如 OpenRouter）：

```
API_KEY:    sk-or-...
BASE_URL:   https://openrouter.ai/api/v1
MODEL_NAME: claude-sonnet-4-5-20250929
```

#### DeepSeek

```
API_KEY:    sk-...
BASE_URL:   https://api.deepseek.com/v1
MODEL_NAME: deepseek-chat
```

#### OpenRouter

OpenRouter 通过单一 API 提供多种模型的访问：

```
API_KEY:    sk-or-...
BASE_URL:   https://openrouter.ai/api/v1
MODEL_NAME: anthropic/claude-sonnet-4-5-20250929
```

### Web UI 提供商配置

Web UI 的设置页面支持图形化配置提供商。提供商凭据存储在 `~/.leon/models.json` 中，与 TUI 的 `config.env` 分开。Web UI 支持：

- 同时配置多个提供商（OpenAI、Anthropic、OpenRouter 等）
- 虚拟模型映射（例如 `leon:large` 映射到具体模型）
- 按模型路由到不同提供商
- 自定义模型注册和测试

## 第一次对话（TUI）

开始新对话：

```bash
leonai
```

继续上次的对话：

```bash
leonai -c
```

恢复特定线程：

```bash
leonai --thread <thread-id>
```

使用特定模型：

```bash
leonai --model gpt-4o
```

设置工作目录：

```bash
leonai --workspace /path/to/project
```

### 线程管理

列出所有对话：

```bash
leonai thread ls
```

查看对话历史：

```bash
leonai thread history <thread-id>
```

回退到检查点（时间旅行）：

```bash
leonai thread rewind <thread-id> <checkpoint-id>
```

删除线程：

```bash
leonai thread rm <thread-id>
```

### 非交互模式

无需 TUI 发送单条消息：

```bash
leonai run "Explain this codebase"
```

从标准输入读取：

```bash
echo "Summarize this file" | leonai run --stdin
```

无 TUI 交互模式：

```bash
leonai run -i
```

## 启动 Web UI

Web UI 是一个 FastAPI 后端，提供基于浏览器的界面，支持实时流式输出、智能体管理和多智能体聊天。

启动后端服务器：

```bash
python -m backend.web.main
```

这会在端口 8001（默认）上启动 uvicorn 服务器，并启用自动重载。端口可通过以下方式配置：

- `LEON_BACKEND_PORT` 或 `PORT` 环境变量
- Git worktree 配置：`git config --worktree worktree.ports.backend 8002`

Web UI 提供了 TUI 之外的更多功能：

- 可视化智能体配置（系统提示词、工具、规则、MCP 服务器）
- 人类与 AI 智能体之间的多智能体聊天
- 沙箱会话管理与资源监控
- 模型和提供商设置，支持实时测试
- 通过 SSE 实时推送智能体响应

## 沙箱管理

Mycel 支持多种沙箱提供商，用于隔离的代码执行。通过在 `~/.leon/sandboxes/` 中放置 JSON 文件进行配置：

```bash
leonai sandbox            # 打开沙箱管理器 TUI
leonai sandbox ls         # 列出活动会话
leonai sandbox new docker # 创建新的 Docker 会话
leonai sandbox metrics <id>  # 查看资源使用情况
```

支持的提供商：Docker、AgentBay、E2B、Daytona。

## 下一步

- [多智能体聊天](multi-agent-chat.md) —— 了解用于人机和智能体间通信的 Entity-Chat 系统
- [沙箱配置](SANDBOX.md) —— 配置沙箱执行环境
- [故障排除](TROUBLESHOOTING.md) —— 常见问题与解决方案
