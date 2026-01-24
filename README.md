# ⚡ Leon AI

> 你的 AI 伙伴 · 让代码开发更智能

Leon 是一个智能 AI 助手，帮你写代码、改 bug、管理项目。就像有个经验丰富的程序员坐在你旁边，随时准备帮忙。

## ✨ 选择 Leon

### 🧠 真正理解你的项目
- **记住上下文**：Leon 会记住你之前说过的话，不用每次都重复
- **理解项目结构**：自动分析你的代码组织方式
- **持续对话**：像和真人聊天一样，可以连续提问和讨论

### 🎨 现代化界面
- **全屏终端界面**：清爽美观的 TUI 界面
- **实时反馈**：看到 AI 的思考过程
- **Markdown 支持**：代码高亮、格式化显示

## 🚀 快速开始

### 安装

**推荐方式（全局安装）：**

```bash
# 使用 uv（推荐）
uv tool install leonai

# 或使用 pipx
pipx install leonai
```

**开发者方式：**

```bash
pip install leonai
```

### 配置

首次使用需要配置 API key：

```bash
leonai config
```

按提示输入：
- **OPENAI_API_KEY**: 你的 API key（必需）
- **OPENAI_BASE_URL**: 代理地址（可选）
- **MODEL_NAME**: 模型名称（可选，默认 claude-sonnet-4-5-20250929）

配置会保存到 `~/.config/leon/config.env`，之后无需重复配置。

### 启动

在任意项目目录下运行：

```bash
cd /path/to/your/project
leonai
```

Leon 会自动把当前目录作为工作目录，可以直接操作你的项目文件。

**注意**：如果使用 `pip install` 安装，需要先激活虚拟环境或使用 `python -m leonai`。

## 🎯 核心特性

- ✅ **文件操作**：读取、创建、编辑项目文件
- ✅ **代码搜索**：快速找到相关代码
- ✅ **命令执行**：运行测试、构建项目
- ✅ **持久记忆**：记住项目信息和你的偏好
- ✅ **安全隔离**：可选的 Docker 沙箱环境



## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**用 ❤️ 和 AI 打造** | [GitHub](https://github.com/Ju-Yi-AI-Lab/leonai)
