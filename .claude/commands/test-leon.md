# 测试 Leon 新功能

在开发 Leon 时，用此命令验证新功能是否正常工作。

**重要**：Middleware 级别的更新必须通过此测试才能交付。

## 使用方法

```bash
/test-leon                    # Middleware 级别更新，执行完整测试
/test-leon <测试场景描述>      # 指定测试场景
```

## 何时必须执行

以下情况**必须**执行完整测试后才能交付：

- 新增或修改 `middleware/` 下的模块
- 修改 `agent.py` 核心逻辑
- 修改 `tui/app.py` 或 `tui/runner.py`
- 新增工具或修改工具行为
- 修改 checkpointer / session 相关逻辑

## 执行流程

### 1. 清理环境

测试前先清理可能卡住的进程：

```bash
# 杀掉所有 leonai 相关进程
pkill -9 -f "leonai" 2>/dev/null || true
pkill -9 -f "context7\|upstash" 2>/dev/null || true
sleep 1
```

### 2. 重新安装

每次测试前**必须**按以下顺序执行，确保测试的是最新代码：

```bash
# 1. 清除缓存（必须！否则可能安装旧版本）
# 如果提示 "Cache is currently in-use"，加 --force
uv cache clean leonai --force

# 2. 强制重新安装（必须用 --force）
uv tool install . --force
```

⚠️ 注意：
- `uv cache clean` 必须加 `--force`，否则可能因为有进程占用而卡住
- `uv tool install` 必须加 `--force`，否则不会覆盖已安装版本

### 3. 完整测试（Middleware 级别更新）

无参数调用时，执行以下全部测试：

#### 2.1 基础响应测试

```bash
leonai run -d "你好，用一句话介绍你自己"
```

验证：Agent 能正常响应，无报错。

#### 2.2 工具调用测试

```bash
leonai run -d "列出当前目录的文件"
```

验证：`[TOOL_CALL] list_dir` 出现，`[TOOL_RESULT]` 返回文件列表。

#### 2.3 多轮对话测试

```bash
cat << 'EOF' | leonai run --stdin -d
你好

列出当前目录的 Python 文件

读取 agent.py 的前 5 行
EOF
```

验证：3 轮对话都正常完成，工具调用正确。

#### 2.4 Thread 持久化测试

```bash
leonai run --thread test-mem-$(date +%s) "记住数字 42"
# 记录上面的 thread id，然后：
leonai run --thread <同一个thread-id> "我让你记住的数字是多少？"
```

验证：第二轮能正确回忆出 42。

### 4. 指定场景测试

用户指定测试场景时，构造对应的测试命令。

**单轮快速验证**：

```bash
leonai run -d "<测试消息>"
```

**多轮验证**（stdin）：

```bash
cat << 'EOF' | leonai run --stdin -d --thread test-$(date +%s)
<第一轮消息>

<第二轮消息>
EOF
```

**持久化验证**（跨命令）：

```bash
leonai run --thread <thread-id> "<第一轮>"
leonai run --thread <thread-id> "<第二轮验证>"
```

**交互模式**（需要手动输入，如测试 Queue Mode）：

```bash
leonai run -i -d
```

### 5. 结果分析

检查 debug 输出：
- `[TOOL_CALL]` - 工具是否被正确调用
- `[TOOL_RESULT]` - 工具返回是否正确
- `[QUEUE]` - 队列状态是否符合预期
- `[ASSISTANT]` - AI 响应是否合理
- `[SUMMARY]` - 总轮次和工具调用数

## 测试通过标准

- 所有测试无报错
- 工具调用符合预期
- 多轮对话上下文正确
- Thread 持久化正常工作
