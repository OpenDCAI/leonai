# Leon 快速开始

## 📁 项目结构（已整理）

```
leon/
├── cascade_agent.py          # ✅ 唯一的主入口文件
├── middleware/               # 所有 middleware 实现
│   ├── filesystem.py         # 文件操作（已修复格式）
│   ├── search.py             # 搜索功能（已修复格式）
│   ├── extensible_bash.py    # Bash 执行 + hooks
│   └── ...
├── examples/                 # 所有示例代码
│   ├── cascade_demo.py       # 完整功能演示
│   ├── quick_start.py        # 快速开始
│   ├── state_based_agent.py  # State-based 实现（旧）
│   └── ...
├── tests/                    # 测试文件
└── docs/                     # 文档
```

## 🚀 使用方式

### 1. 作为库使用

```python
from cascade_agent import create_cascade_agent

# 创建 agent
agent = create_cascade_agent(
    workspace_root="/path/to/workspace",
    read_only=False
)

# 使用
response = agent.get_response("Create a Python file that prints Hello World")
print(response)
```

### 2. 运行示例

```bash
# 完整功能演示
python examples/cascade_demo.py

# 快速开始
python examples/quick_start.py
```

## ✅ 已完成的格式修复

所有工具输出格式已与 Cascade 100% 一致：

1. **read_file**: 使用 `→` 分隔符，无 header
2. **list_dir**: Tab 缩进，空目录格式正确
3. **find_by_name**: 结果计数 + 绝对路径
4. **grep_search**: 上下文显示（前后 2 行）
5. **所有 emoji 已移除**

详见：`docs/CHANGELOG_FORMAT_FIXES.md`

## 🎯 核心原则

1. **根目录只有一个入口**: `cascade_agent.py`
2. **所有示例放在 examples/**
3. **所有 middleware 放在 middleware/**
4. **所有测试放在 tests/**
5. **所有文档放在 docs/**

## 📝 可用工具

- **文件操作**: `read_file`, `write_file`, `edit_file`, `multi_edit`, `list_dir`
- **搜索**: `grep_search`, `find_by_name`
- **命令执行**: `bash`（带安全 hooks）

所有工具都通过 middleware 自动注入，无需手动配置。
