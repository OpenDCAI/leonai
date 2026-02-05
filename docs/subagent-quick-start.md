# SubAgent 快速实现清单

基于 `subagent-design.md` 的快速实施指南。

---

## 阶段 1：核心实现（1-2 天）

### 1.1 创建文件结构

```bash
mkdir -p leon/middleware/subagent
touch leon/middleware/subagent/__init__.py
touch leon/middleware/subagent/middleware.py
touch leon/middleware/subagent/types.py
touch leon/middleware/subagent/context.py
touch leon/middleware/subagent/pool.py
```

### 1.2 实现子 Agent 类型定义

```python
# leon/middleware/subagent/types.py

from dataclasses import dataclass
from typing import List, Literal

@dataclass
class SubAgentType:
    """子 Agent 类型定义"""
    name: str
    system_prompt: str
    tools: List[str]
    readonly: bool
    max_tokens: int


# 三种预定义类型
GENERAL_PURPOSE = SubAgentType(
    name="generalPurpose",
    system_prompt="""
    你是一个通用任务处理 Agent，拥有完整的工具集。
    
    工作原则：
    1. 专注于给定的任务
    2. 不依赖对话历史（你看不到）
    3. 如果需要上下文，任务描述中会提供
    4. 完成任务后返回清晰的结果
    """,
    tools=[
        "read_file", "write_file", "edit_file", "multi_edit", "list_dir",
        "grep_search", "find_by_name",
        "run_command", "command_status",
        "web_search", "read_url_content",
        "load_skill",
    ],
    readonly=False,
    max_tokens=100000
)

EXPLORE = SubAgentType(
    name="explore",
    system_prompt="""
    你是一个代码探索专家 Agent，专注于快速搜索和分析代码。
    
    能力：文件读取、代码搜索、目录浏览
    限制：只读模式，不能修改文件
    
    工作原则：
    1. 快速定位相关代码
    2. 提供清晰的搜索结果
    3. 总结代码结构和功能
    """,
    tools=[
        "read_file", "list_dir",
        "grep_search", "find_by_name",
        "web_search", "read_url_content",
    ],
    readonly=True,
    max_tokens=50000
)

SHELL = SubAgentType(
    name="shell",
    system_prompt="""
    你是一个 Shell 命令执行专家 Agent，专注于运行和管理命令。
    
    能力：执行 Shell 命令、多步骤工作流、错误处理
    
    工作原则：
    1. 按顺序执行命令
    2. 检查每步的执行结果
    3. 如果失败，报告错误并停止
    4. 返回完整的执行日志
    """,
    tools=[
        "run_command", "command_status",
        "read_file", "list_dir",  # 用于查看结果
    ],
    readonly=False,
    max_tokens=30000
)


SUBAGENT_TYPES = {
    "generalPurpose": GENERAL_PURPOSE,
    "explore": EXPLORE,
    "shell": SHELL,
}
```

### 1.3 实现上下文构建器

```python
# leon/middleware/subagent/context.py

import os
import subprocess
from datetime import datetime
from typing import Dict, Optional

class SubAgentContextBuilder:
    """构建子 Agent 上下文"""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
    
    def build(self, subagent_type: str) -> Dict:
        """
        构建子 Agent 上下文
        
        继承：
        - 系统信息 ✅
        - CLAUDE.md ✅
        - 项目快照 ✅
        
        不继承：
        - 对话历史 ❌
        """
        
        return {
            "system_info": self._get_system_info(),
            "project_snapshot": self._get_project_snapshot(),
            "workspace_rules": self._load_claude_md(),
            "conversation_history": None,  # ❌ 显式不包含
        }
    
    def _get_system_info(self) -> Dict:
        """获取系统信息"""
        return {
            "os_version": os.uname().sysname + " " + os.uname().release,
            "shell": os.environ.get("SHELL", "unknown"),
            "workspace_root": self.workspace_root,
            "current_date": datetime.now().strftime("%A %b %d, %Y"),
            "username": os.environ.get("USER", "unknown"),
        }
    
    def _get_project_snapshot(self) -> Dict:
        """获取项目快照（文件树 + Git 状态）"""
        return {
            "git_status": self._get_git_status(),
            "git_branch": self._get_git_branch(),
        }
    
    def _get_git_status(self) -> str:
        """获取 Git 状态"""
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except:
            return ""
    
    def _get_git_branch(self) -> str:
        """获取当前分支"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except:
            return ""
    
    def _load_claude_md(self) -> str:
        """加载 CLAUDE.md"""
        claude_md_path = os.path.join(self.workspace_root, "CLAUDE.md")
        if os.path.exists(claude_md_path):
            with open(claude_md_path, "r") as f:
                return f.read()
        return ""
```

### 1.4 实现 SubAgent 中间件

```python
# leon/middleware/subagent/middleware.py

import uuid
import asyncio
from typing import Optional, Literal, Dict
from dataclasses import dataclass

from .types import SUBAGENT_TYPES
from .context import SubAgentContextBuilder

@dataclass
class SubAgentResult:
    """子 Agent 执行结果"""
    output: str
    agent_id: str
    success: bool
    error: Optional[str]
    token_usage: Dict[str, int]


class SubAgentMiddleware:
    """SubAgent 中间件"""
    
    def __init__(self, profile):
        self.profile = profile
        self.workspace_root = profile.workspace_root
        self.context_builder = SubAgentContextBuilder(self.workspace_root)
        
        # 并发控制
        self.max_concurrent = 4
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Resume 支持
        self.active_sessions: Dict[str, 'LeonAgent'] = {}
    
    def get_tools(self):
        """返回 task 工具定义"""
        return [{
            "name": "task",
            "description": "启动子 Agent 执行独立任务",
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "任务描述"
                    },
                    "subagent_type": {
                        "type": "string",
                        "enum": ["generalPurpose", "explore", "shell"],
                        "description": "子 Agent 类型"
                    },
                    "description": {
                        "type": "string",
                        "description": "简短描述（3-5 词）"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["default", "fast"],
                        "description": "模型选择（可选）"
                    },
                    "readonly": {
                        "type": "boolean",
                        "description": "是否只读模式（可选）"
                    },
                    "resume": {
                        "type": "string",
                        "description": "恢复之前的 Agent ID（可选）"
                    }
                },
                "required": ["prompt", "subagent_type", "description"]
            }
        }]
    
    async def execute(
        self,
        prompt: str,
        subagent_type: Literal["generalPurpose", "explore", "shell"],
        description: str,
        model: Optional[str] = None,
        readonly: bool = False,
        resume: Optional[str] = None,
    ) -> SubAgentResult:
        """执行子 Agent 任务"""
        
        # Resume 现有 Agent
        if resume and resume in self.active_sessions:
            agent = self.active_sessions[resume]
            try:
                result = await agent.run(prompt)
                return SubAgentResult(
                    output=result,
                    agent_id=resume,
                    success=True,
                    error=None,
                    token_usage=agent.get_token_usage()
                )
            except Exception as e:
                return SubAgentResult(
                    output="",
                    agent_id=resume,
                    success=False,
                    error=str(e),
                    token_usage={}
                )
        
        # 创建新 Agent
        async with self.semaphore:
            try:
                # 1. 创建子 Agent
                agent = self._create_subagent(
                    subagent_type=subagent_type,
                    model=model,
                    readonly=readonly
                )
                
                # 2. 执行任务
                result = await agent.run(prompt)
                
                # 3. 保存会话
                agent_id = str(uuid.uuid4())
                self.active_sessions[agent_id] = agent
                
                return SubAgentResult(
                    output=result,
                    agent_id=agent_id,
                    success=True,
                    error=None,
                    token_usage=agent.get_token_usage()
                )
            
            except Exception as e:
                return SubAgentResult(
                    output="",
                    agent_id="",
                    success=False,
                    error=str(e),
                    token_usage={}
                )
    
    def _create_subagent(
        self,
        subagent_type: str,
        model: Optional[str],
        readonly: bool
    ):
        """创建子 Agent 实例"""
        
        # 获取类型配置
        type_config = SUBAGENT_TYPES[subagent_type]
        
        # 构建上下文
        context = self.context_builder.build(subagent_type)
        
        # 创建子 Agent Profile
        from leon.agent_profile import AgentProfile
        
        subagent_profile = AgentProfile(
            model=model or self.profile.model,
            workspace_root=self.workspace_root,
            system_prompt=type_config.system_prompt,
            
            # 继承配置
            skills=self.profile.skills,
            mcp_servers=self.profile.mcp_servers,
            
            # 子 Agent 配置
            tools=type_config.tools,
            readonly=readonly or type_config.readonly,
            max_tokens=type_config.max_tokens,
        )
        
        # 创建 LeonAgent
        from leon.agent import LeonAgent
        
        subagent = LeonAgent(
            profile=subagent_profile,
            context=context,  # 传入构建好的上下文
        )
        
        return subagent
```

---

## 阶段 2：集成到 LeonAgent（半天）

### 2.1 修改 agent.py

```python
# leon/agent.py

from leon.middleware.subagent import SubAgentMiddleware

class LeonAgent:
    def __init__(self, profile: AgentProfile, context: Optional[Dict] = None):
        self.profile = profile
        self.context = context  # 新增：支持传入上下文
        
        # 注册中间件
        self.middleware = [
            PromptCachingMiddleware(profile),
            SubAgentMiddleware(profile),  # ⭐ 新增
            FileSystemMiddleware(profile),
            SearchMiddleware(profile),
            WebMiddleware(profile),
            CommandMiddleware(profile),
            SkillsMiddleware(profile),
        ]
    
    async def run(self, user_input: str) -> str:
        """运行 Agent"""
        
        # 构建工具集
        tools = []
        for mw in self.middleware:
            tools.extend(mw.get_tools())
        
        # 构建系统提示（包含上下文）
        system_prompt = self._build_system_prompt()
        
        # 调用 LLM
        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            tools=tools
        )
        
        # 处理工具调用
        if response.tool_calls:
            for tool_call in response.tool_calls:
                # 找到对应的中间件
                for mw in self.middleware:
                    if tool_call.name in [t["name"] for t in mw.get_tools()]:
                        result = await mw.execute(**tool_call.arguments)
                        return result
        
        return response.content
    
    def _build_system_prompt(self) -> str:
        """构建系统提示（包含上下文信息）"""
        
        base_prompt = self.profile.system_prompt
        
        # 如果有上下文，添加系统信息
        if self.context:
            system_info = self.context.get("system_info", {})
            project_snapshot = self.context.get("project_snapshot", {})
            
            context_section = f"""
## 系统信息

- OS: {system_info.get('os_version')}
- Shell: {system_info.get('shell')}
- 工作目录: {system_info.get('workspace_root')}
- 当前日期: {system_info.get('current_date')}
- Git 分支: {project_snapshot.get('git_branch')}

## Git 状态

```
{project_snapshot.get('git_status')}
```
"""
            
            base_prompt += "\n\n" + context_section
        
        return base_prompt
```

---

## 阶段 3：测试（半天）

### 3.1 单元测试

```python
# tests/test_subagent.py

import pytest
from leon.middleware.subagent import SubAgentMiddleware
from leon.agent_profile import AgentProfile

@pytest.fixture
def profile():
    return AgentProfile(
        model="gpt-4",
        workspace_root="/Users/apple/Desktop/project/v1/文稿/project/leon"
    )

@pytest.fixture
def middleware(profile):
    return SubAgentMiddleware(profile)

@pytest.mark.asyncio
async def test_spawn_explore_agent(middleware):
    """测试生成 explore 子 Agent"""
    
    result = await middleware.execute(
        prompt="列出根目录的文件",
        subagent_type="explore",
        description="列出文件"
    )
    
    assert result.success
    assert result.agent_id
    print(f"Output: {result.output}")

@pytest.mark.asyncio
async def test_spawn_shell_agent(middleware):
    """测试生成 shell 子 Agent"""
    
    result = await middleware.execute(
        prompt="运行 ls -la",
        subagent_type="shell",
        description="列出文件"
    )
    
    assert result.success
    print(f"Output: {result.output}")

@pytest.mark.asyncio
async def test_parallel_agents(middleware):
    """测试并行执行"""
    
    import asyncio
    
    tasks = [
        middleware.execute(
            prompt="列出根目录",
            subagent_type="explore",
            description="列出根目录"
        ),
        middleware.execute(
            prompt="查看 Git 状态",
            subagent_type="shell",
            description="Git 状态"
        ),
        middleware.execute(
            prompt="搜索 'Agent' 关键词",
            subagent_type="explore",
            description="搜索 Agent"
        ),
    ]
    
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 3
    assert all(r.success for r in results)
```

### 3.2 手动测试

```python
# manual_test.py

import asyncio
from leon.agent import LeonAgent
from leon.agent_profile import AgentProfile

async def main():
    # 1. 创建主 Agent
    profile = AgentProfile(
        model="gpt-4",
        workspace_root="/Users/apple/Desktop/project/v1/文稿/project/leon"
    )
    
    agent = LeonAgent(profile)
    
    # 2. 测试 Task 工具
    print("=== 测试 1: 探索代码库 ===")
    response = await agent.run("""
    使用 task 工具，探索 middleware/ 目录，找出所有中间件的功能。
    """)
    print(response)
    
    print("\n=== 测试 2: 执行 Git 命令 ===")
    response = await agent.run("""
    使用 task 工具，执行以下 Git 操作：
    1. git status
    2. git log --oneline -5
    """)
    print(response)
    
    print("\n=== 测试 3: 并行任务 ===")
    response = await agent.run("""
    启动 3 个子 Agent 并行执行：
    1. 探索 tui/ 目录
    2. 探索 middleware/ 目录
    3. 查看 Git 分支
    """)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 阶段 4：优化和监控（1 天）

### 4.1 添加日志

```python
# leon/middleware/subagent/middleware.py

import logging

logger = logging.getLogger("leon.subagent")

class SubAgentMiddleware:
    async def execute(self, ...):
        logger.info(
            f"[SubAgent] Spawning: type={subagent_type}, "
            f"description={description}"
        )
        
        start_time = time.time()
        
        # ... 执行 ...
        
        elapsed = time.time() - start_time
        logger.info(
            f"[SubAgent] Completed: agent_id={agent_id}, "
            f"elapsed={elapsed:.2f}s, "
            f"tokens={result.token_usage}"
        )
```

### 4.2 添加监控

```python
# leon/middleware/subagent/metrics.py

class SubAgentMetrics:
    def __init__(self):
        self.metrics = {
            "total_spawned": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_tokens": 0,
            "by_type": {
                "generalPurpose": {"count": 0, "tokens": 0},
                "explore": {"count": 0, "tokens": 0},
                "shell": {"count": 0, "tokens": 0},
            }
        }
    
    def record_spawn(self, subagent_type: str):
        self.metrics["total_spawned"] += 1
        self.metrics["by_type"][subagent_type]["count"] += 1
    
    def record_completion(self, subagent_type: str, tokens: int, success: bool):
        if success:
            self.metrics["total_completed"] += 1
        else:
            self.metrics["total_failed"] += 1
        
        self.metrics["total_tokens"] += tokens
        self.metrics["by_type"][subagent_type]["tokens"] += tokens
    
    def get_summary(self) -> dict:
        return self.metrics
```

---

## 完成检查清单

### ✅ 阶段 1: 核心实现
- [ ] 创建文件结构
- [ ] 实现 `types.py`（三种子 Agent 类型）
- [ ] 实现 `context.py`（上下文构建器）
- [ ] 实现 `middleware.py`（SubAgent 中间件）

### ✅ 阶段 2: 集成
- [ ] 修改 `agent.py`（注册中间件）
- [ ] 修改 `agent.py`（支持上下文传入）
- [ ] 修改 `agent_profile.py`（如果需要）

### ✅ 阶段 3: 测试
- [ ] 编写单元测试
- [ ] 运行单元测试（全部通过）
- [ ] 手动测试（explore、shell、generalPurpose）
- [ ] 测试并行执行
- [ ] 测试 Resume 机制

### ✅ 阶段 4: 优化
- [ ] 添加日志记录
- [ ] 添加性能监控
- [ ] 文档更新（README）

---

## 时间估算

| 阶段 | 时间 | 说明 |
|------|------|------|
| 阶段 1 | 1-2 天 | 核心实现 |
| 阶段 2 | 0.5 天 | 集成 |
| 阶段 3 | 0.5 天 | 测试 |
| 阶段 4 | 1 天 | 优化 |
| **总计** | **3-4 天** | 完整实现 |

---

## 快速命令

```bash
# 1. 创建目录
mkdir -p leon/middleware/subagent

# 2. 创建文件
touch leon/middleware/subagent/{__init__,types,context,middleware,pool,metrics}.py

# 3. 运行测试
pytest tests/test_subagent.py -v

# 4. 手动测试
python manual_test.py

# 5. 查看日志
tail -f logs/subagent.log
```

---

## 常见问题速查

### Q: 如何快速验证是否工作？

```python
# 最简单的测试
result = await agent.task(
    prompt="列出当前目录",
    subagent_type="shell",
    description="ls"
)
print(result.output)
```

### Q: 如何调试子 Agent？

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Q: 如何测试并行？

```python
# 并行执行 3 个任务
tasks = [agent.task(...) for _ in range(3)]
results = await asyncio.gather(*tasks)
```

---

**下一步**: 开始阶段 1 - 核心实现！
