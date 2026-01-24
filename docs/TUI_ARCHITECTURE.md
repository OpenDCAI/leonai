# Leon TUI 架构文档

## 概述

Leon TUI 是基于 Textual 框架构建的现代化终端用户界面，为 Leon Agent 提供了更好的交互体验。

## 设计原则

1. **保持 Agent 独立性**：UI 层完全独立，不修改 agent.py 核心逻辑
2. **流式优先**：所有输出都支持流式显示
3. **可视化工具调用**：工具调用和返回值以卡片形式展示
4. **响应式布局**：自适应终端大小

## 技术栈

- **Textual 7.3.0**: TUI 框架
- **Rich 14.2.0**: 终端美化和文本渲染
- **LangChain**: Agent 核心（保持不变）

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        leon_cli.py                          │
│                      (Entry Point)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      ui/app.py                              │
│                     (LeonApp)                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Header                                              │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  VerticalScroll (chat-container)                     │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  WelcomeBanner                                 │  │  │
│  │  ├────────────────────────────────────────────────┤  │  │
│  │  │  Messages Container                            │  │  │
│  │  │  - UserMessage                                 │  │  │
│  │  │  - AssistantMessage                            │  │  │
│  │  │  - ToolCallMessage                             │  │  │
│  │  │  - ToolResultMessage                           │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ChatInput (input-container)                         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  StatusBar                                           │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Footer                                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    agent.py                                 │
│                  (LeonAgent)                                │
│  - FileSystemMiddleware                                     │
│  - SearchMiddleware                                         │
│  - ShellMiddleware                                          │
│  - PromptCachingMiddleware                                  │
└─────────────────────────────────────────────────────────────┘
```

## 组件详解

### 1. LeonApp (ui/app.py)

主应用类，继承自 `textual.app.App`。

**职责**：
- 管理整体布局
- 处理用户输入
- 协调消息流
- 管理 agent 交互

**关键方法**：
- `compose()`: 构建 UI 布局
- `on_chat_input_submitted()`: 处理消息提交
- `_process_message()`: 异步处理 agent 响应
- `action_clear_history()`: 清空对话历史

### 2. Widgets (ui/widgets/)

#### UserMessage
- 显示用户输入
- 蓝色左边框
- 简单文本格式

#### AssistantMessage
- 显示 AI 响应
- Markdown 渲染
- 支持流式更新（`update_content()`, `append_content()`）

#### ToolCallMessage
- 显示工具调用
- 黄色左边框
- 格式化显示工具名称和参数

#### ToolResultMessage
- 显示工具返回值
- 绿色左边框
- 自动截断长输出

#### ChatInput
- 多行文本输入
- Enter 发送，Shift+Enter 换行
- Markdown 语法高亮

#### StatusBar
- 显示 Thread ID
- 显示快捷键提示
- 固定在底部

## 消息流

```
用户输入
   │
   ▼
ChatInput.Submitted 事件
   │
   ▼
LeonApp.on_chat_input_submitted()
   │
   ├─> 添加 UserMessage
   │
   └─> 启动 Worker: _process_message()
          │
          ▼
       agent.stream()
          │
          ├─> AIMessage → AssistantMessage
          │
          ├─> ToolCall → ToolCallMessage
          │
          └─> ToolMessage → ToolResultMessage
```

## 状态管理

### Thread 管理
- 每个会话有唯一的 `thread_id`
- `/clear` 命令生成新 thread
- Thread ID 显示在状态栏

### 工具调用追踪
```python
self._shown_tool_calls = set()      # 已显示的工具调用
self._shown_tool_results = set()    # 已显示的工具结果
```

防止重复显示同一工具调用。

### 流式更新
```python
self._current_assistant_msg = None  # 当前 AI 消息组件
```

复用同一组件进行流式更新。

## 样式系统

使用 Textual CSS 进行样式定制：

```css
/* 主容器 */
#chat-container {
    height: 1fr;
    padding: 1 2;
    background: $background;
}

/* 输入框 */
ChatInput {
    border: solid $primary;
}
```

### 颜色变量
- `$primary`: 主色（蓝色）
- `$success`: 成功色（绿色）
- `$warning`: 警告色（黄色）
- `$error`: 错误色（红色）
- `$surface`: 表面色
- `$background`: 背景色

## 与 Agent 的集成

### 保持独立性
```python
# leon_cli.py
agent = create_leon_agent()  # 使用现有 agent
run_tui(agent, ...)          # 传递给 TUI
```

TUI 不修改 agent 内部逻辑，只负责：
1. 接收用户输入
2. 调用 `agent.stream()`
3. 展示响应

### 流式处理
```python
for chunk in agent.agent.stream(...):
    # 解析 chunk
    # 更新 UI 组件
```

使用 LangChain 的 `stream_mode="values"` 获取完整状态。

## 性能优化

1. **异步处理**：使用 `run_worker()` 避免阻塞 UI
2. **增量更新**：只更新变化的消息
3. **去重机制**：防止重复显示工具调用
4. **自动滚动**：`scroll_end(animate=False)` 快速滚动

## 扩展点

### 添加新组件
1. 在 `ui/widgets/` 创建新组件
2. 继承 `Static` 或 `Vertical`
3. 定义 `DEFAULT_CSS`
4. 在 `__init__.py` 导出

### 自定义样式
修改组件的 `DEFAULT_CSS` 或 `LeonApp.CSS`。

### 添加新命令
在 `on_chat_input_submitted()` 中处理：
```python
if content.lower() == "/your_command":
    # 处理命令
    return
```

## 对比传统 CLI

| 特性 | chat.py | leon_cli.py |
|------|---------|-------------|
| 框架 | 无 | Textual |
| 布局 | 线性输出 | 全屏 TUI |
| 消息格式 | ANSI 颜色 | Rich 样式 |
| Markdown | 不支持 | 实时渲染 |
| 多行输入 | 不支持 | 支持 |
| 工具可视化 | 文本 | 卡片 |
| 滚动 | 终端 | 应用内 |
| 代码量 | 203 行 | ~500 行 |

## 依赖关系

```
leon_cli.py
  └─> ui/app.py
       ├─> ui/widgets/messages.py
       ├─> ui/widgets/chat_input.py
       └─> ui/widgets/status.py
  └─> agent.py (不变)
       ├─> middleware/filesystem.py
       ├─> middleware/search.py
       ├─> middleware/shell/
       └─> middleware/prompt_caching.py
```

## 未来改进方向

1. **历史浏览**：上下键浏览历史消息
2. **文件预览**：内联显示文件内容
3. **主题切换**：支持多种颜色主题
4. **命令补全**：自动补全文件路径和命令
5. **工具审批**：交互式审批工具调用
6. **分屏模式**：同时显示多个视图
7. **导出功能**：导出对话历史为 Markdown

## 故障排除

### 显示异常
- 检查终端是否支持 Textual
- 尝试 `clear` 清除终端
- 使用现代终端（iTerm2, GNOME Terminal）

### 导入错误
```bash
uv sync  # 重新同步依赖
```

### 性能问题
- 减少消息历史（使用 `/clear`）
- 关闭不必要的终端美化
- 使用更快的终端模拟器
