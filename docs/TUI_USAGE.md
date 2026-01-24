# Leon CLI - TUI 使用指南

## 概述

Leon CLI 提供了基于 Textual 框架的现代化终端用户界面（TUI），相比传统的命令行交互，提供了更好的视觉体验和交互方式。

## 启动方式

```bash
# 方式 1: 直接运行
python leon_cli.py

# 方式 2: 使用 uv
uv run leon_cli.py
```

## 功能特性

### 1. 流式输出
- AI 响应实时流式显示
- Markdown 格式自动渲染
- 代码块语法高亮

### 2. 工具调用可视化
- 工具调用实时展示（黄色边框）
- 参数详情自动格式化
- 工具返回结果展示（绿色边框）

### 3. 多行输入
- **Enter**: 发送消息
- **Shift+Enter**: 插入换行
- 支持 Markdown 格式输入

### 4. 对话管理
- `/clear`: 清空对话历史（生成新 thread）
- `/exit` 或 `/quit`: 退出程序
- **Ctrl+C**: 快速退出
- **Ctrl+L**: 清空历史（快捷键）

### 5. 状态栏
- 显示当前 Thread ID
- 显示快捷键提示

## 界面布局

```
╔══════════════════════════════════════════════════════════════════╗
║                      Leon Agent - TUI 模式                        ║
║                   流式输出 + 工具调用可视化                        ║
╚══════════════════════════════════════════════════════════════════╝

👤 你: 帮我创建一个 hello.py 文件

🤖 Leon: 我来帮你创建...

🔧 调用工具: write_file
   参数:
     file_path: /path/to/hello.py
     content: print("Hello, World!")

📤 工具返回:
   文件已创建: hello.py

🤖 Leon: 已成功创建 hello.py 文件...

[输入框]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Leon Agent | Thread: tui-abc123 | Ctrl+C: 退出
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Enter | 发送消息 |
| Shift+Enter | 换行 |
| Ctrl+C | 退出程序 |
| Ctrl+L | 清空历史 |

## 与传统 chat.py 的对比

| 特性 | chat.py | leon_cli.py (TUI) |
|------|---------|-------------------|
| 界面 | 简单文本 | 全屏 TUI |
| 消息格式 | 纯文本 | Markdown 渲染 |
| 工具调用 | 文本输出 | 可视化卡片 |
| 多行输入 | 不支持 | 支持 |
| 滚动 | 终端滚动 | 应用内滚动 |
| 颜色 | ANSI 颜色 | Rich 样式 |

## 技术架构

### 组件结构

```
ui/
├── __init__.py
├── app.py                    # 主应用
└── widgets/
    ├── __init__.py
    ├── messages.py           # 消息组件
    ├── chat_input.py         # 输入组件
    └── status.py             # 状态栏组件
```

### 核心组件

1. **LeonApp**: 主应用类
   - 管理整体布局
   - 处理消息流
   - 协调各个组件

2. **UserMessage**: 用户消息组件
   - 蓝色左边框
   - 显示用户输入

3. **AssistantMessage**: AI 消息组件
   - Markdown 渲染
   - 支持流式更新

4. **ToolCallMessage**: 工具调用组件
   - 黄色左边框
   - 显示工具名称和参数

5. **ToolResultMessage**: 工具结果组件
   - 绿色左边框
   - 显示返回值

6. **ChatInput**: 输入组件
   - 多行编辑
   - 智能 Enter 处理

7. **StatusBar**: 状态栏
   - Thread ID 显示
   - 快捷键提示

## 自定义样式

TUI 使用 Textual CSS 进行样式定制，主要样式定义在 `ui/app.py` 的 `CSS` 字符串中。

### 修改颜色主题

可以通过修改各组件的 `DEFAULT_CSS` 来自定义颜色：

```python
# 例如修改用户消息边框颜色
UserMessage {
    border-left: thick $success;  # 改为绿色
}
```

### 可用颜色变量

- `$primary`: 主色调
- `$success`: 成功色（绿色）
- `$warning`: 警告色（黄色）
- `$error`: 错误色（红色）
- `$surface`: 表面色
- `$background`: 背景色

## 故障排除

### 1. 依赖缺失

```bash
# 确保安装了所需依赖
uv sync
```

### 2. 终端不支持

某些老旧终端可能不支持 Textual，建议使用：
- macOS: iTerm2 或 Terminal.app
- Linux: GNOME Terminal, Konsole
- Windows: Windows Terminal

### 3. 显示异常

如果显示异常，尝试：
```bash
# 清除终端
clear

# 重新运行
python leon_cli.py
```

## 未来改进

- [ ] 添加历史记录浏览
- [ ] 支持文件预览
- [ ] 添加主题切换
- [ ] 支持命令自动补全
- [ ] 添加工具调用审批界面
