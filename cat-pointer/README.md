# 小猫指物 🐱

复刻"小猫指物"蠢萌场景：用户语音说出物品名称 → Agent 调用 MCP 工具 → 动画小猫指向对应物体。

## 架构

```
用户语音 → Whisper API 转写 → Leon Agent → MCP Server → Next.js 动画
```

## 快速开始

### 1. 安装依赖

```bash
# 安装语音依赖（可选）
uv pip install sounddevice scipy

# 安装 MCP 服务器依赖
cd cat-pointer/mcp-server
uv pip install -e .

# 安装 Next.js 依赖
cd ../next-app
npm install
```

### 2. 启动服务

**终端 1 - 启动 Next.js 动画应用：**

```bash
cd cat-pointer/next-app
npm run dev
```

**终端 2 - 启动 Leon Agent：**

```bash
uv run leonai --profile profiles/cat-pointer.yaml
```

### 3. 使用

1. 打开浏览器访问 http://localhost:3000
2. 在 Leon TUI 中输入物品名称（如"萝卜"、"纸巾"、"米奇"）
3. 观察小猫动画指向对应物体

## 组件说明

### MCP Server (`mcp-server/`)

提供 3 个工具：
- `point_carrot` - 指向萝卜 🥕
- `point_tissue` - 指向纸巾 🧻
- `point_mickey` - 指向米奇 🐭

### Next.js App (`next-app/`)

- `/api/point` - POST 接收指令，GET 返回当前状态
- 前端轮询状态，触发小猫动画

### 语音输入 (`tui/widgets/voice_input.py`)

- 录音按钮，使用 `sounddevice` 录制
- 调用 OpenAI Whisper API 转写
- 需要安装可选依赖：`uv pip install sounddevice scipy`

## 环境变量

```bash
OPENAI_API_KEY=xxx      # 必需（用于 Agent 和 Whisper）
OPENAI_BASE_URL=xxx     # 可选（代理地址）
```

## 测试

### 手动测试 API

```bash
# 测试指向萝卜
curl -X POST http://localhost:3000/api/point \
  -H "Content-Type: application/json" \
  -d '{"target": "萝卜"}'

# 查看当前状态
curl http://localhost:3000/api/point
```

### 测试 MCP Server

```bash
cd cat-pointer/mcp-server
uv run python server.py
```

## 文件结构

```
cat-pointer/
├── mcp-server/
│   ├── __init__.py
│   ├── server.py           # MCP 服务器，定义 3 个工具
│   └── pyproject.toml
│
├── next-app/
│   ├── app/
│   │   ├── page.tsx        # 主页面
│   │   └── api/
│   │       └── point/route.ts  # API 端点
│   ├── components/
│   │   ├── Cat.tsx         # 小猫组件
│   │   └── Object.tsx      # 物体组件
│   └── package.json
│
└── README.md
```
