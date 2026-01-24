# Leon CLI 使用指南

## 快速启动

Leon 已配置为类似 `deepagents-cli` 的命令行工具。

### 方式 1: 使用 uv run（推荐）

```bash
uv run leon
```

### 方式 2: 激活虚拟环境后直接使用

```bash
source .venv/bin/activate
leon
```

### 方式 3: 使用完整路径

```bash
.venv/bin/leon
```

### 方式 4: 全局安装（可选）

```bash
uv tool install .
leon
```

## 配置

### 设置 API Key

创建 `.env` 文件或设置环境变量：

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

或者在项目根目录创建 `.env` 文件：

```
ANTHROPIC_API_KEY=your-api-key
```

## TUI 功能

启动后，你将看到 Textual TUI 界面，支持：

### 快捷键

- **Enter**: 发送消息
- **Shift+Enter**: 换行
- **Ctrl+↑/↓**: 浏览历史输入
- **Ctrl+Y**: 复制最后一条消息
- **Ctrl+E**: 导出对话为 Markdown
- **Ctrl+L**: 清空对话历史
- **Ctrl+C**: 退出

### 功能特性

- ✅ 流式输出显示
- ✅ 工具调用可视化
- ✅ 对话历史导航
- ✅ 增强思考状态（显示工具执行）
- ✅ 消息计数统计
- ✅ 复制和导出功能
- ✅ Bash Session 持久化

## 开发模式

如果你正在开发 Leon，使用 editable 安装：

```bash
uv pip install -e .
```

这样修改代码后无需重新安装即可生效。

## 与 deepagents-cli 的对比

| 功能 | deepagents-cli | leon |
|------|----------------|------|
| 命令启动 | `deepagents` | `uv run leon` 或 `leon` |
| TUI 界面 | ❌ | ✅ |
| Bash 持久化 | ✅ | ✅ |
| 文件操作 | ✅ | ✅ |
| 搜索功能 | ✅ | ✅ |
| 安全沙箱 | ✅ | ✅（workspace 隔离）|
| 历史导航 | ❌ | ✅ |
| 工具可视化 | ❌ | ✅ |
