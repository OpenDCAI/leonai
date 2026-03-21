[English](../en/getting-started.md) | 中文

# Mycel 快速上手

Mycel 是一个具备持久记忆、沙箱代码执行和多智能体通信的主动式 AI 编程助手。它提供两种界面：**Web UI**（可视化交互）和 **CLI/TUI**（终端工作流）。选择适合你的方式即可。

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

---

## 方式 A：Web UI（推荐大多数用户使用）

Web UI 提供基于浏览器的界面，支持实时流式输出、可视化智能体配置和多智能体聊天。

### 1. 启动后端

```bash
python -m backend.web.main
```

在 `http://localhost:8001` 启动 uvicorn 服务器，默认开启自动重载。

使用其他端口：

```bash
LEON_BACKEND_PORT=8002 python -m backend.web.main
```

### 2. 启动前端

```bash
cd frontend/app
npm install
npm run dev
```

前端在 `http://localhost:5173` 打开。

### 3. 注册与配置

1. 打开浏览器，访问 `http://localhost:5173`
2. 通过注册表单创建账户
3. 进入 **设置** 页面配置 LLM 提供商：
   - 添加 API 密钥
   - 设置提供商的 Base URL
   - 选择或注册模型

Web UI 的提供商凭据存储在 `~/.leon/models.json` 中。Web UI 支持：

- 同时配置多个提供商（OpenAI、Anthropic、OpenRouter 等）
- 虚拟模型映射（例如 `leon:large` 映射到具体模型）
- 按模型路由到不同提供商
- 自定义模型注册与实时测试

### Web UI 功能

- 可视化智能体配置（系统提示词、工具、规则、MCP 服务器）
- 人类与 AI 智能体之间的多智能体聊天
- 沙箱会话管理与资源监控
- 通过 SSE 实时推送智能体响应

---

## 方式 B：CLI / TUI

CLI 提供基于终端的界面，适合快速交互和脚本集成。

### 首次运行

```bash
leonai
```

如果未检测到 API 密钥，交互式配置向导（`leonai config`）会自动启动，询问以下内容：

1. **API_KEY**（必填）—— OpenAI 兼容的 API 密钥，存储为 `OPENAI_API_KEY`。
2. **BASE_URL**（可选）—— API 端点，默认 `https://api.openai.com/v1`，自动补齐 `/v1`。
3. **MODEL_NAME**（可选）—— 使用的模型，默认 `claude-sonnet-4-5-20250929`。

配置保存在 `~/.leon/config.env` 中，采用 `KEY=VALUE` 格式。

随时重新运行或查看配置：

```bash
leonai config          # 重新运行向导
leonai config show     # 查看当前设置
```

### 使用方法

```bash
leonai                          # 开始新对话
leonai -c                       # 继续上次对话
leonai --thread <thread-id>     # 恢复特定线程
leonai --model gpt-4o           # 使用特定模型
leonai --workspace /path/to/dir # 设置工作目录
```

### 线程管理

```bash
leonai thread ls                          # 列出所有对话
leonai thread history <thread-id>         # 查看对话历史
leonai thread rewind <thread-id> <cp-id>  # 回退到检查点
leonai thread rm <thread-id>              # 删除线程
```

### 非交互模式

```bash
leonai run "Explain this codebase"            # 发送单条消息
echo "Summarize this" | leonai run --stdin    # 从标准输入读取
leonai run -i                                  # 无 TUI 交互模式
```

---

## LLM 提供商设置

Mycel 使用 OpenAI 兼容的 API 格式。任何支持该协议的提供商都可以直接使用。以下示例适用于 CLI（`~/.leon/config.env`）和 Web UI（设置页面）。

### 提供商示例

#### OpenAI

```
API_KEY:    sk-...
BASE_URL:   https://api.openai.com/v1
MODEL_NAME: gpt-4o
```

#### Anthropic Claude（通过 OpenAI 兼容代理）

Claude 模型通过 OpenAI 兼容代理访问，例如 OpenRouter：

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

### 配置优先级

环境变量优先于 `~/.leon/config.env`：

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
```

---

## 沙箱管理

Mycel 支持多种沙箱提供商，用于隔离的代码执行。通过在 `~/.leon/sandboxes/` 中放置 JSON 文件进行配置。

```bash
leonai sandbox              # 打开沙箱管理器 TUI
leonai sandbox ls           # 列出活动会话
leonai sandbox new docker   # 创建新的 Docker 会话
leonai sandbox metrics <id> # 查看资源使用情况
```

支持的提供商：Docker、AgentBay、E2B、Daytona。

## 下一步

- [多智能体聊天](multi-agent-chat.md) —— 用于人机和智能体间通信的 Entity-Chat 系统
- [沙箱配置](SANDBOX.md) —— 配置沙箱执行环境
- [故障排除](TROUBLESHOOTING.md) —— 常见问题与解决方案
