# Bash Middleware 使用指南

Leon Agent 提供了**两种 Bash Middleware**，适用于不同场景。

---

## 方案对比

| 特性 | LocalBashMiddleware | ClaudeBashToolMiddleware (Docker) | ClaudeBashToolMiddleware (无 Docker) |
|------|---------------------|-----------------------------------|-------------------------------------|
| **Python 环境** | ✅ 系统 Python 3.14 | ✅ 容器内 Python (可选版本) | ❌ 无 Python |
| **启动速度** | ⚡️ 极快 | 🐌 慢（需拉取镜像） | ⚡️ 快 |
| **文件访问** | ✅ workspace 内所有文件 | ✅ workspace 内所有文件（挂载） | ✅ workspace 内所有文件 |
| **安全性** | ⚠️ 低（直接系统访问） | ✅ 高（容器隔离） | ⚠️ 低（直接系统访问） |
| **pip 安装包** | ✅ 可以（系统级） | ✅ 可以（容器内） | ❌ 无 pip |
| **需要 Docker** | ❌ 不需要 | ✅ 需要 | ❌ 不需要 |
| **适用场景** | 开发环境 | 生产环境 | 简单脚本 |

---

## 方案 1: LocalBashMiddleware（推荐开发使用）

### 特点
- ✅ 直接使用你的系统 Python（3.14.2）
- ✅ 可以执行任何 Python 代码
- ✅ 启动快速，无需 Docker
- ✅ 可以访问 workspace 目录下的所有文件
- ⚠️ 安全性较低（agent 可以执行系统命令）

### 配置

```python
from agent import create_leon

leon = create_leon(
    workspace_root="/path/to/your/project",  # 你的项目目录
    use_local_bash=True,  # 使用本地 bash（默认）
)
```

### 使用示例

```python
# 执行 Python 代码
result = leon.invoke("用 Python 计算 100 的阶乘")

# 安装 Python 包（系统级）
result = leon.invoke("用 pip3 安装 pandas 包")

# 运行 Python 脚本
result = leon.invoke("运行 workspace 里的 script.py")
```

### 文件访问

```
你的项目: /Users/apple/my_project/
  ├── data.csv          ← Agent 可以访问
  ├── script.py         ← Agent 可以执行
  └── output/           ← Agent 可以写入
```

---

## 方案 2: ClaudeBashToolMiddleware + Docker

### 特点
- ✅ 完整的 Python 环境（可选任意版本）
- ✅ 容器隔离，安全性高
- ✅ 可以安装任何 pip 包（容器内）
- ✅ workspace 目录自动挂载到容器
- ❌ 需要安装 Docker Desktop
- ❌ 启动较慢

### 配置

```python
from agent import create_leon

leon = create_leon(
    workspace_root="/path/to/your/project",
    use_local_bash=False,      # 不使用本地 bash
    enable_docker=True,        # 启用 Docker
    docker_image="python:3.14" # Python 版本
)
```

### Docker 文件挂载机制

```
本地目录: /Users/apple/my_project/
    ↓ (自动挂载)
容器内部: /workspace/
    ├── data.csv          ← 同步
    ├── script.py         ← 同步
    └── output/           ← 同步
```

**关键点：**
- 容器内的 Python 可以读写 workspace 文件
- 你在本地创建的文件，容器能看到
- 容器创建的文件，你在本地也能看到
- Text Editor middleware 创建的文件也能被 bash 访问

### 使用示例

```python
# 在容器内安装包
result = leon.invoke("安装 numpy 和 pandas")

# 执行 Python 脚本（使用容器内的 Python）
result = leon.invoke("运行 /workspace/analysis.py")

# 数据处理
result = leon.invoke("用 pandas 读取 /workspace/data.csv 并统计")
```

---

## 方案 3: ClaudeBashToolMiddleware（无 Docker）

### 特点
- ✅ 不需要 Docker
- ✅ 启动快
- ✅ 可以执行基本 shell 命令
- ❌ 没有 Python
- ❌ 功能受限

### 配置

```python
leon = create_leon(
    use_local_bash=False,  # 不使用本地 bash
    enable_docker=False,   # 不启用 Docker
)
```

### 适用场景
- 只需要基本文件操作（ls, cat, grep）
- 不需要执行 Python 代码
- 配合 Text Editor middleware 使用

---

## 如何选择？

### 开发环境（推荐）
```python
leon = create_leon(
    workspace_root="/Users/apple/my_project",
    use_local_bash=True,  # 使用系统 Python
)
```

**优势：**
- 快速迭代
- 直接使用系统 Python
- 无需配置 Docker

---

### 生产环境
```python
leon = create_leon(
    workspace_root="/app/workspace",
    use_local_bash=False,
    enable_docker=True,
    docker_image="python:3.14-slim",
)
```

**优势：**
- 安全隔离
- 可控的 Python 环境
- 不会影响宿主系统

---

### 简单脚本（无 Python 需求）
```python
leon = create_leon(
    use_local_bash=False,
    enable_docker=False,
)
```

**优势：**
- 最轻量
- 启动最快
- 配合 Text Editor 足够

---

## 常见问题

### Q1: Docker 模式下，agent 能访问我的本地文件吗？

**A:** 只能访问 `workspace_root` 目录内的文件。

```python
leon = create_leon(
    workspace_root="/Users/apple/my_project",  # 只有这个目录被挂载
    enable_docker=True
)

# ✅ 可以访问: /Users/apple/my_project/data.csv
# ❌ 不能访问: /Users/apple/other_folder/file.txt
```

### Q2: LocalBashMiddleware 安全吗？

**A:** 不太安全。Agent 可以执行任意系统命令，包括：
- 删除文件
- 修改系统配置
- 访问网络

**建议：**
- 只在开发环境使用
- 不要用于不信任的 agent 代码
- 生产环境用 Docker 模式

### Q3: Text Editor 创建的文件，Bash 能访问吗？

**A:** 取决于配置：

**LocalBashMiddleware:**
- Text Editor 文件在 state 中，bash 看不到
- 需要先用 Text Editor 写入磁盘

**Docker 模式:**
- Text Editor 可以配置写入 workspace
- Bash 可以访问 workspace 文件

### Q4: 我想用 Docker 但不想每次都拉取镜像？

**A:** 提前拉取镜像：

```bash
docker pull python:3.14-slim
```

之后创建 agent 会直接使用本地镜像。

---

## 最佳实践

### 1. 开发时用 LocalBash
```python
# .env
USE_LOCAL_BASH=true
ENABLE_DOCKER=false
```

### 2. 部署时用 Docker
```python
# .env
USE_LOCAL_BASH=false
ENABLE_DOCKER=true
DOCKER_IMAGE=python:3.14-slim
```

### 3. 限制 workspace 范围
```python
# 不要用根目录
leon = create_leon(workspace_root="/")  # ❌ 危险

# 用专门的项目目录
leon = create_leon(workspace_root="/Users/apple/leon_workspace")  # ✅ 安全
```

### 4. 配合 Text Editor 使用
```python
# Text Editor 创建文件
leon.invoke("创建一个 Python 脚本 /project/analyze.py")

# LocalBash 执行文件（如果文件在 workspace）
leon.invoke("运行 analyze.py")
```

---

## 性能对比

| 操作 | LocalBash | Docker | 无 Docker |
|------|-----------|--------|-----------|
| 启动时间 | ~0.1s | ~3-5s | ~0.1s |
| Python 执行 | ✅ 快 | ✅ 快 | ❌ N/A |
| 文件读写 | ✅ 快 | ✅ 快 | ✅ 快 |
| pip 安装 | ✅ 可以 | ✅ 可以 | ❌ N/A |

---

## 总结

**推荐配置（开发环境）：**
```python
leon = create_leon(
    workspace_root="/Users/apple/my_project",
    use_local_bash=True,  # 使用系统 Python，快速方便
)
```

**推荐配置（生产环境）：**
```python
leon = create_leon(
    workspace_root="/app/workspace",
    use_local_bash=False,
    enable_docker=True,
    docker_image="python:3.14-slim",  # 安全隔离
)
```
