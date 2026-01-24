# Leon 主动智能设计文档

## 核心理念：人机协同 · 主动智能

Leon 不是被动响应的工具，而是主动思考的协作伙伴。

---

## 🧠 主动智能的三个层次

### Level 1: 模式识别（Pattern Recognition）

**观察用户行为，识别重复模式**

```python
# 示例：检测到重复操作
用户连续 3 次执行:
1. docker-compose up -d
2. pytest tests/
3. docker-compose down

Leon 主动建议:
"我注意到你每次测试都要启动/关闭 Docker，
要不要创建一个快捷命令？

建议: /test -> 自动执行完整流程"
```

**实现要点**：
- 记录用户命令序列
- 识别时间窗口内的重复模式（5分钟内）
- 阈值：3次以上重复触发建议

---

### Level 2: 上下文推理（Context Inference）

**理解项目结构，推断用户意图**

```python
# 示例：智能补全
用户: "创建一个用户接口"

Leon 分析项目:
- 检测到 FastAPI + SQLAlchemy
- 已有 models/user.py
- 已有 schemas/user.py
- 缺少 routers/user.py

Leon 主动问:
"我看到你已经有了 User model 和 schema，
是要创建 CRUD 接口吗？我可以：

1. 创建 routers/user.py（包含 GET/POST/PUT/DELETE）
2. 添加到 main.py 的路由注册
3. 生成对应的 pytest 测试
4. 更新 API 文档

需要我全部做吗？"
```

**实现要点**：
- 项目结构分析（AST + 文件树）
- 技术栈识别（pyproject.toml, package.json）
- 缺失组件推断

---

### Level 3: 主动优化（Proactive Optimization）

**发现潜在问题，主动提出改进**

```python
# 示例：性能优化建议
Leon 后台分析:
- 检测到 requirements.txt 有 50+ 依赖
- 但 pyproject.toml 只声明了 10 个
- 可能存在冗余依赖

Leon 主动提醒:
"⚠️  发现潜在问题：

你的 requirements.txt 有 52 个包，
但 pyproject.toml 只声明了 12 个直接依赖。

可能有 40 个是传递依赖，建议：
1. 运行 pip-audit 检查安全漏洞
2. 使用 pipdeptree 清理冗余依赖
3. 迁移到 uv 加速安装

需要我帮你做吗？"
```

**实现要点**：
- 后台静默分析（不阻塞用户）
- 问题优先级排序
- 非侵入式提醒

---

## 🚀 第一阶段实现：模式识别

### 功能：重复命令检测

**技术方案**：

```python
# middleware/proactive.py

class ProactiveMiddleware(AgentMiddleware):
    """主动智能中间件"""
    
    def __init__(self):
        self.command_history = []  # [(timestamp, command), ...]
        self.patterns = {}  # {pattern_hash: count}
        self.suggestions_given = set()  # 避免重复建议
    
    def after_tool_call(self, tool_name, args, result):
        """工具调用后的钩子"""
        if tool_name == "bash":
            self._track_command(args["command"])
            self._detect_patterns()
    
    def _track_command(self, command):
        """记录命令"""
        self.command_history.append({
            "timestamp": time.time(),
            "command": command
        })
        
        # 只保留最近 10 分钟的历史
        cutoff = time.time() - 600
        self.command_history = [
            h for h in self.command_history 
            if h["timestamp"] > cutoff
        ]
    
    def _detect_patterns(self):
        """检测重复模式"""
        # 检测最近 5 分钟内的命令序列
        recent = self._get_recent_commands(300)
        
        # 滑动窗口检测 2-5 个命令的序列
        for window_size in range(2, 6):
            pattern = self._find_repeated_sequence(recent, window_size)
            if pattern and len(pattern["occurrences"]) >= 3:
                self._suggest_workflow(pattern)
    
    def _suggest_workflow(self, pattern):
        """建议创建工作流"""
        pattern_hash = hash(tuple(pattern["commands"]))
        
        if pattern_hash in self.suggestions_given:
            return
        
        self.suggestions_given.add(pattern_hash)
        
        suggestion = f"""
💡 主动建议：

我注意到你重复执行了这个命令序列 {len(pattern["occurrences"])} 次：

{self._format_commands(pattern["commands"])}

要不要创建一个快捷命令？例如：
  /deploy -> 自动执行上述流程

回复 'yes' 或 '是' 来创建
"""
        return suggestion
```

---

## 📊 效果预期

### 用户体验提升

**传统 Agent**：
```
用户: pytest
用户: docker-compose up
用户: pytest
用户: docker-compose down
用户: pytest
用户: docker-compose up
...（重复 10 次）
```

**Leon（主动智能）**：
```
用户: pytest
用户: docker-compose up
用户: pytest

Leon: 💡 我注意到你在重复这个流程，要创建快捷命令吗？

用户: 好的

Leon: ✅ 已创建 /test 命令，下次直接输入 /test 即可
```

---

## 🎯 后续规划

### Phase 1（当前）
- ✅ 重复命令检测
- ✅ 工作流建议

### Phase 2（下一步）
- 项目结构分析
- 技术栈识别
- 智能补全建议

### Phase 3（未来）
- 代码质量分析
- 性能优化建议
- 安全漏洞检测

---

## 💡 设计原则

1. **非侵入性**：建议不应打断用户工作流
2. **可关闭**：用户可以关闭主动建议
3. **学习能力**：记住用户的偏好（接受/拒绝建议）
4. **透明性**：清楚说明为什么提出建议
5. **可撤销**：所有自动化操作都可以撤销

---

## 🔧 配置选项

```toml
# .leon/config.toml

[proactive]
enabled = true
detection_window = 300  # 5分钟
min_repetitions = 3     # 至少重复3次
suggestion_cooldown = 3600  # 同一建议1小时内不重复

[proactive.features]
pattern_detection = true
context_inference = false  # Phase 2
optimization_suggestions = false  # Phase 3
```
