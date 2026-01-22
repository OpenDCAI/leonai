# 项目结构整理方案

## 📊 当前状态分析

### 根目录的 Python 文件（混乱）

1. **`agent.py`** (289 行)
   - **用途**: 使用 State-based middleware（StateClaudeTextEditorMiddleware, StateClaudeMemoryMiddleware）
   - **状态**: ⚠️ 这是旧的实现，使用虚拟文件系统
   - **应该**: 移到 `examples/state_based_agent.py`

2. **`cascade_agent.py`** (348 行)
   - **用途**: 完整的 Cascade-Like Agent，使用 FileSystemMiddleware + SearchMiddleware
   - **状态**: ✅ 这是最新的、完整的实现
   - **应该**: **保留在根目录**（这是主入口）

3. **`main.py`** (7 行)
   - **用途**: 空壳，只有 "Hello from leon!"
   - **状态**: ❌ 完全没用
   - **应该**: 删除

### examples/ 目录

1. **`cascade_demo.py`** (261 行)
   - **用途**: 演示 cascade_agent.py 的所有功能
   - **状态**: ✅ 正确位置
   - **应该**: 保留

2. **`chat.py`** (5051 bytes)
   - **用途**: 未知（需要查看）
   - **状态**: ⚠️ 需要检查
   - **应该**: 检查后决定

3. **`examples.py`** (10337 bytes)
   - **用途**: 未知（需要查看）
   - **状态**: ⚠️ 需要检查
   - **应该**: 检查后决定

4. **`quick_start.py`** (2656 bytes)
   - **用途**: 快速开始示例
   - **状态**: ✅ 正确位置
   - **应该**: 保留

---

## 🎯 推荐的项目结构

```
leon/
├── cascade_agent.py          # ✅ 主入口（唯一的根目录 Python 文件）
├── middleware/               # ✅ 所有 middleware 实现
│   ├── __init__.py
│   ├── filesystem.py         # ✅ 已修复格式
│   ├── search.py             # ✅ 已修复格式
│   ├── extensible_bash.py
│   ├── anthropic_tools.py
│   ├── prompt_caching.py
│   └── bash_hooks/
├── examples/                 # ✅ 所有示例代码
│   ├── cascade_demo.py       # 完整功能演示
│   ├── quick_start.py        # 快速开始
│   ├── state_based_agent.py  # 从 agent.py 移过来
│   ├── chat.py               # 交互式聊天示例
│   └── examples.py           # 其他示例
├── tests/                    # ✅ 测试文件
├── docs/                     # ✅ 文档
│   └── CHANGELOG_FORMAT_FIXES.md
├── pyproject.toml            # ✅ 项目配置
├── README.md                 # ✅ 项目说明
└── .env.example              # ✅ 环境变量模板
```

---

## 🔧 需要执行的操作

### 1. 移动文件
```bash
# 将 agent.py 移到 examples/
mv agent.py examples/state_based_agent.py

# 删除无用的 main.py
rm main.py
```

### 2. 更新 cascade_agent.py
- 保持在根目录
- 这是唯一的主入口文件
- 提供 `create_cascade_agent()` 工厂函数

### 3. 更新 examples/cascade_demo.py
- 确保 import 路径正确：`from cascade_agent import create_cascade_agent`

### 4. 更新 README.md
- 明确说明 `cascade_agent.py` 是主入口
- 提供使用示例
- 说明 examples/ 目录的作用

---

## 📝 使用方式

### 作为库使用
```python
from cascade_agent import create_cascade_agent

# 创建 agent
agent = create_cascade_agent(
    workspace_root="/path/to/workspace",
    read_only=False
)

# 使用
response = agent.get_response("Create a Python file...")
```

### 运行示例
```bash
# 完整功能演示
python examples/cascade_demo.py

# 快速开始
python examples/quick_start.py

# State-based agent（旧实现）
python examples/state_based_agent.py
```

---

## 🎯 核心原则

1. **根目录只有一个入口**: `cascade_agent.py`
2. **所有示例放在 examples/**
3. **所有 middleware 放在 middleware/**
4. **所有测试放在 tests/**
5. **所有文档放在 docs/**

这样结构清晰，职责明确，不会混乱。
