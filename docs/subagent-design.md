# Leon SubAgent 设计方案

基于 Claude (Cursor) 的 SubAgent 系统设计，为 Leon 实现完全一致的 `Task` 工具。

---

## 一、核心设计哲学

### 1.1 设计原则

| 原则 | 说明 | 生物学类比 |
|------|------|-----------|
| **上下文隔离** | 子 Agent 不继承对话历史 | 子细胞不继承母细胞的记忆 |
| **配置继承** | 子 Agent 继承系统信息、Skills、MCP | 子细胞继承 DNA 和细胞器 |
| **显式传递** | 必要上下文通过 prompt 传递 | 通过信号分子传递信息 |
| **任务完成即销毁** | 子 Agent 执行完任务后凋亡 | 细胞完成任务后程序性凋亡 |

### 1.2 继承矩阵

| 内容 | 主 Agent | 子 Agent | 传递方式 |
|------|---------|---------|---------|
| 系统信息 | ✅ | ✅ | 自动继承 |
| 工作目录 | ✅ | ✅ | 自动继承 |
| 项目文件树 | ✅ | ✅ | 自动继承（快照） |
| Git 状态 | ✅ | ✅ | 自动继承（快照） |
| CLAUDE.md | ✅ | ✅ | 自动继承 |
| Skills 列表 | ✅ | ✅ | 自动继承 |
| MCP 服务器 | ✅ | ✅ | 自动继承 |
| 工具集 | ✅ | ✅/部分 | 根据子 Agent 类型 |
| 对话历史 | ✅ | ❌ | 不继承 |
| 用户打开的文件 | ✅ | ❌ | 不继承 |
| 主 Agent 读取的内容 | ✅ | ❌ | 不继承 |
| 编辑历史 | ✅ | ❌ | 不继承 |

---

## 二、Task 工具接口设计

### 2.1 工具定义

```python
class TaskTool:
    """
    启动子 Agent 执行独立任务
    
    类比：主 Agent 分化出特化的 Worker Agent
    """
    
    name: str = "Task"
    description: str = """
    启动一个独立的子 Agent 来执行特定任务。
    
    用途：
    1. 复杂的多步骤任务（>3 步）
    2. 需要专注执行的任务（Shell 工作流、代码探索）
    3. 可并行的独立任务（最多 4 个并行）
    4. 需要错误处理和回滚的流程
    
    不适用：
    1. 单个简单命令
    2. 需要立即反馈的操作
    3. 与其他工具紧密交织的任务
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": """
                给子 Agent 的任务描述（必需）
                
                最佳实践：
                1. 明确任务目标
                2. 提供必要的背景上下文
                3. 说明期望的输出格式
                4. 如果有多步骤，明确列出步骤
                
                示例：
                "探索 middleware/ 目录，找出所有中间件的功能。
                 对每个中间件：
                 1. 读取主要文件
                 2. 识别提供的工具
                 3. 总结职责
                 返回：表格形式（中间件名称 | 工具列表 | 职责描述）"
                """
            },
            "subagent_type": {
                "type": "string",
                "enum": ["generalPurpose", "explore", "shell"],
                "description": """
                子 Agent 类型（必需）
                
                - generalPurpose: 通用任务，全工具集
                - explore: 代码探索，只读工具集
                - shell: 命令执行，专注 Shell 操作
                
                选择指南：
                - 需要修改文件 → generalPurpose
                - 只读搜索/分析 → explore
                - 多步骤命令流程 → shell
                """
            },
            "description": {
                "type": "string",
                "description": """
                任务简短描述（必需，3-5 词）
                
                用途：
                1. 日志记录
                2. 并行任务管理
                3. 用户界面显示
                
                示例：
                - "探索中间件目录"
                - "执行 Git 工作流"
                - "分析核心 Agent"
                """
            },
            "model": {
                "type": "string",
                "enum": ["default", "fast"],
                "description": """
                使用的模型（可选）
                
                - default: 默认模型（继承主 Agent）
                - fast: 快速模型（低成本、低智能，适合简单任务）
                
                选择指南：
                - 简单、明确定义的任务 → fast
                - 需要推理、复杂决策 → default
                """
            },
            "readonly": {
                "type": "boolean",
                "default": False,
                "description": """
                是否为只读模式（可选）
                
                - True: 禁止文件修改操作
                - False: 允许所有操作
                
                注意：explore 类型默认只读
                """
            },
            "resume": {
                "type": "string",
                "description": """
                恢复之前的子 Agent（可选）
                
                用法：
                1. 第一次调用返回 agent_id
                2. 后续调用传入 agent_id
                3. 子 Agent 保留之前的上下文
                
                示例：
                # 第一次
                result = Task(prompt="探索代码库", ...)
                agent_id = result.agent_id
                
                # 继续对话
                Task(prompt="刚才找到的文件，详细分析", resume=agent_id)
                """
            }
        },
        "required": ["prompt", "subagent_type", "description"]
    }
```

---

## 三、子 Agent 类型设计

### 3.1 generalPurpose Agent

```python
class GeneralPurposeAgent:
    """通用任务处理 Agent"""
    
    type: str = "generalPurpose"
    
    system_prompt: str = """
    你是一个通用任务处理 Agent，拥有完整的工具集。
    
    能力：
    - 文件读写和编辑
    - 代码搜索和语义分析
    - Shell 命令执行
    - Web 搜索和内容获取
    - MCP 工具调用
    - 任务管理和用户交互
    
    工作原则：
    1. 专注于给定的任务
    2. 不依赖对话历史（你看不到）
    3. 如果需要上下文，在任务描述中会提供
    4. 完成任务后返回清晰的结果
    """
    
    tools: List[str] = [
        # 文件系统
        "read_file",
        "write_file", 
        "edit_file",
        "multi_edit",
        "list_dir",
        
        # 搜索
        "grep_search",
        "find_by_name",
        "codebase_search",  # 语义搜索
        
        # 命令执行
        "run_command",
        "command_status",
        
        # Web
        "web_search",
        "read_url_content",
        "view_web_content",
        
        # Skills
        "load_skill",
        
        # MCP
        "mcp__<server>__<tool>",  # 动态生成
        
        # 其他
        "generate_image",
        "ask_question",
        "todo_write",
    ]
    
    readonly: bool = False
    
    # Token 预算（参考）
    max_tokens: int = 100000
```

### 3.2 explore Agent

```python
class ExploreAgent:
    """代码探索专家 Agent（只读）"""
    
    type: str = "explore"
    
    system_prompt: str = """
    你是一个代码探索专家 Agent，专注于快速搜索和分析代码。
    
    能力：
    - 文件读取（只读）
    - 代码搜索（grep、语义搜索）
    - 文件名查找
    - 目录浏览
    
    限制：
    - 不能修改文件
    - 不能执行可能有副作用的命令
    - 不能写入文件
    
    工作原则：
    1. 快速定位相关代码
    2. 提供清晰的搜索结果
    3. 总结代码结构和功能
    4. 返回精炼的分析报告
    """
    
    tools: List[str] = [
        # 只读文件操作
        "read_file",
        "list_dir",
        
        # 搜索
        "grep_search",
        "find_by_name", 
        "codebase_search",
        
        # Web（只读）
        "web_search",
        "read_url_content",
        
        # 其他
        "generate_image",  # 用于生成架构图等
    ]
    
    readonly: bool = True  # 强制只读
    
    # Token 预算（更低）
    max_tokens: int = 50000
```

### 3.3 shell Agent

```python
class ShellAgent:
    """命令执行专家 Agent"""
    
    type: str = "shell"
    
    system_prompt: str = """
    你是一个 Shell 命令执行专家 Agent，专注于运行和管理命令。
    
    能力：
    - 执行 Shell 命令（同步/异步）
    - 多步骤命令工作流
    - 错误处理和回滚
    - 命令状态查询
    
    工作原则：
    1. 按顺序执行命令
    2. 检查每步的执行结果
    3. 如果失败，报告错误并停止（或回滚）
    4. 返回完整的执行日志
    """
    
    tools: List[str] = [
        # 命令执行
        "run_command",
        "command_status",
        
        # 基础文件操作（用于查看命令结果）
        "read_file",
        "list_dir",
    ]
    
    readonly: bool = False
    
    # Token 预算（更低，专注执行）
    max_tokens: int = 30000
```

---

## 四、实现架构

### 4.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      LeonAgent (主 Agent)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Middleware Stack                                     │   │
│  │  - PromptCaching                                      │   │
│  │  - Filesystem                                         │   │
│  │  - Search                                             │   │
│  │  - Web                                                │   │
│  │  - Command                                            │   │
│  │  - Skills                                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tools (主 Agent)                                     │   │
│  │  - Task ⭐ (新增：启动子 Agent)                        │   │
│  │  - read_file, write_file, edit_file                  │   │
│  │  - grep_search, codebase_search                      │   │
│  │  - run_command, web_search                           │   │
│  │  - ...                                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Task(prompt, subagent_type, ...)
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 SubAgent Spawner                             │
│                                                              │
│  1. 选择子 Agent 类型（generalPurpose/explore/shell）        │
│  2. 构建子 Agent 上下文：                                    │
│     - 系统信息 ✅                                            │
│     - CLAUDE.md ✅                                           │
│     - Skills 列表 ✅                                         │
│     - MCP 服务器 ✅                                          │
│     - 对话历史 ❌                                            │
│  3. 注入工具集（根据类型）                                   │
│  4. 启动子 Agent                                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌───────────────┬───────────────┬───────────────┬─────────────┐
│ SubAgent 1    │ SubAgent 2    │ SubAgent 3    │ SubAgent 4  │
│ (explore)     │ (shell)       │ (generalPurpose)│ (explore) │
│               │               │               │             │
│ 独立上下文     │ 独立上下文     │ 独立上下文     │ 独立上下文  │
│ 独立工具集     │ 独立工具集     │ 独立工具集     │ 独立工具集  │
└───────────────┴───────────────┴───────────────┴─────────────┘
                           │
                           │ 返回结果
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 主 Agent 汇总结果                            │
│  - 收集所有子 Agent 的输出                                   │
│  - 合成最终答案                                              │
│  - 返回给用户                                                │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 核心实现

```python
# leon/middleware/subagent.py

from typing import Optional, Literal, List
from dataclasses import dataclass
import asyncio

@dataclass
class SubAgentResult:
    """子 Agent 执行结果"""
    output: str           # 子 Agent 的最终输出
    agent_id: str        # 子 Agent ID（用于 resume）
    success: bool        # 是否成功
    error: Optional[str] # 错误信息（如果有）
    token_usage: dict    # Token 使用统计


class SubAgentMiddleware:
    """子 Agent 中间件"""
    
    def __init__(self, agent_profile: AgentProfile):
        self.profile = agent_profile
        self.workspace_root = agent_profile.workspace_root
        
        # 子 Agent 类型定义
        self.subagent_types = {
            "generalPurpose": GeneralPurposeAgent,
            "explore": ExploreAgent,
            "shell": ShellAgent,
        }
        
        # 并发控制
        self.max_concurrent = 4
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Resume 支持
        self.active_agents: dict[str, 'LeonAgent'] = {}
    
    def get_tools(self) -> List[dict]:
        """返回 Task 工具定义"""
        return [{
            "name": "task",
            "description": TaskTool.description,
            "input_schema": TaskTool.parameters
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
        """
        启动子 Agent 执行任务
        
        Args:
            prompt: 任务描述
            subagent_type: 子 Agent 类型
            description: 简短描述（3-5 词）
            model: 模型选择（default/fast）
            readonly: 是否只读
            resume: 恢复之前的 Agent ID
        
        Returns:
            SubAgentResult: 执行结果
        """
        
        # 1. Resume 现有 Agent
        if resume and resume in self.active_agents:
            agent = self.active_agents[resume]
            result = await self._run_agent(agent, prompt)
            return SubAgentResult(
                output=result,
                agent_id=resume,
                success=True,
                error=None,
                token_usage=agent.get_token_usage()
            )
        
        # 2. 创建新的子 Agent
        async with self.semaphore:  # 并发控制
            agent = await self._create_subagent(
                subagent_type=subagent_type,
                model=model,
                readonly=readonly
            )
            
            # 3. 执行任务
            try:
                result = await self._run_agent(agent, prompt)
                
                # 4. 保存 Agent（支持 resume）
                agent_id = agent.session_id
                self.active_agents[agent_id] = agent
                
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
    
    async def _create_subagent(
        self,
        subagent_type: str,
        model: Optional[str],
        readonly: bool
    ) -> 'LeonAgent':
        """创建子 Agent 实例"""
        
        # 1. 获取子 Agent 配置
        agent_class = self.subagent_types[subagent_type]
        agent_config = agent_class()
        
        # 2. 构建子 Agent 的 Profile
        subagent_profile = AgentProfile(
            model=model or self.profile.model,
            workspace_root=self.profile.workspace_root,
            system_prompt=agent_config.system_prompt,
            
            # 继承的配置
            skills=self.profile.skills,        # ✅ 继承 Skills
            mcp_servers=self.profile.mcp_servers,  # ✅ 继承 MCP
            
            # 子 Agent 特定配置
            tools=agent_config.tools,
            readonly=readonly or agent_config.readonly,
            max_tokens=agent_config.max_tokens,
        )
        
        # 3. 创建子 Agent（不继承对话历史！）
        subagent = LeonAgent(
            profile=subagent_profile,
            session_id=self._generate_agent_id(),
            parent_agent=None,  # 不建立父子关系（避免循环引用）
        )
        
        # 4. 注入系统信息（自动继承）
        subagent.inject_system_info({
            "os_version": os.uname(),
            "shell": os.environ.get("SHELL"),
            "workspace_root": self.workspace_root,
            "git_status": self._get_git_status(),
            "project_structure": self._get_project_structure(),
            "current_date": datetime.now().strftime("%A %b %d, %Y"),
        })
        
        return subagent
    
    async def _run_agent(self, agent: 'LeonAgent', prompt: str) -> str:
        """运行子 Agent"""
        
        # 执行任务
        response = await agent.run(prompt)
        
        # 提取最终输出
        return response.get("output", "")
    
    def _generate_agent_id(self) -> str:
        """生成唯一的 Agent ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _get_git_status(self) -> dict:
        """获取 Git 状态快照"""
        # 实现 git status 快照
        pass
    
    def _get_project_structure(self) -> dict:
        """获取项目文件结构快照"""
        # 实现文件树快照
        pass
```

---

## 五、使用模式和最佳实践

### 5.1 模式 1：单个子 Agent

```python
# 场景：执行复杂的 Shell 工作流
async def handle_user_request(user_input: str):
    if "创建新功能分支" in user_input:
        result = await agent.task(
            prompt="""
            执行以下 Git 工作流：
            1. 切换到 master: git checkout master
            2. 拉取最新代码: git pull origin master
            3. 创建新分支: git checkout -b feature/new-auth
            4. 创建目录: mkdir -p src/auth
            5. 创建初始文件: touch src/auth/__init__.py src/auth/handler.py
            6. 初始提交: git add . && git commit -m "feat: init auth module"
            
            如果任何步骤失败，停止并报告错误。
            """,
            subagent_type="shell",
            description="创建新功能分支"
        )
        
        return result.output
```

### 5.2 模式 2：并行子 Agent

```python
# 场景：并行探索多个目录
async def analyze_codebase():
    tasks = [
        agent.task(
            prompt="探索 middleware/ 目录，列出所有中间件及其功能",
            subagent_type="explore",
            description="探索 middleware"
        ),
        agent.task(
            prompt="探索 tui/ 目录，分析 UI 组件结构",
            subagent_type="explore",
            description="探索 TUI"
        ),
        agent.task(
            prompt="读取 agent.py，分析核心 Agent 逻辑",
            subagent_type="explore",
            description="分析核心 Agent"
        ),
        agent.task(
            prompt="运行 git log --oneline -20，查看最近提交",
            subagent_type="shell",
            description="查看 Git 历史"
        ),
    ]
    
    # 并行执行（最多 4 个）
    results = await asyncio.gather(*tasks)
    
    # 汇总结果
    summary = synthesize_results(results)
    return summary
```

### 5.3 模式 3：Resume 继续对话

```python
# 场景：多轮交互式探索
async def interactive_exploration():
    # 第一次：探索代码库
    result1 = await agent.task(
        prompt="探索整个项目，找出所有 Python 模块",
        subagent_type="explore",
        description="探索项目模块"
    )
    agent_id = result1.agent_id
    
    # 第二次：基于第一次的结果，深入分析
    result2 = await agent.task(
        prompt="刚才你找到的中间件模块中，哪个负责文件操作？详细分析它的功能。",
        subagent_type="explore",
        description="分析文件中间件",
        resume=agent_id  # 🔑 保留之前的上下文
    )
    
    # 第三次：继续深入
    result3 = await agent.task(
        prompt="这个文件中间件支持哪些文件格式？",
        subagent_type="explore",
        description="查询支持格式",
        resume=agent_id  # 🔑 继续保留上下文
    )
    
    return [result1.output, result2.output, result3.output]
```

### 5.4 模式 4：显式上下文传递

```python
# 场景：主 Agent 需要传递上下文给子 Agent
async def context_passing_example():
    # 主 Agent 读取文件
    file_content = await agent.read_file("docs/agent-biology-model.md")
    
    # 提取关键信息
    key_concepts = extract_key_concepts(file_content)
    
    # 传递给子 Agent
    result = await agent.task(
        prompt=f"""
        背景上下文：
        用户正在设计一个基于生物学模型的 Agent 系统。
        
        关键概念：
        {key_concepts}
        
        你的任务：
        基于这些概念，设计一个 Agent 分化机制的实现方案。
        包括：
        1. 分化触发条件
        2. 分化类型选择
        3. 可逆性设计
        4. 凋亡机制
        """,
        subagent_type="generalPurpose",
        description="设计分化机制"
    )
    
    return result.output
```

---

## 六、关键实现细节

### 6.1 上下文构建

```python
class SubAgentContextBuilder:
    """子 Agent 上下文构建器"""
    
    def build_context(
        self,
        parent_profile: AgentProfile,
        subagent_type: str
    ) -> dict:
        """
        构建子 Agent 上下文
        
        继承的内容：
        - 系统信息 ✅
        - CLAUDE.md ✅
        - Skills ✅
        - MCP ✅
        - 项目快照 ✅
        
        不继承的内容：
        - 对话历史 ❌
        - 主 Agent 状态 ❌
        """
        
        context = {
            # 1. 系统信息（自动继承）
            "system_info": {
                "os_version": self._get_os_version(),
                "shell": self._get_shell(),
                "workspace_root": parent_profile.workspace_root,
                "current_date": self._get_current_date(),
            },
            
            # 2. 项目快照（启动时生成）
            "project_snapshot": {
                "file_structure": self._get_file_tree(),
                "git_status": self._get_git_status(),
            },
            
            # 3. 配置继承
            "workspace_rules": self._load_claude_md(),  # CLAUDE.md
            "skills": parent_profile.skills,            # Skills 列表
            "mcp_servers": parent_profile.mcp_servers,  # MCP 服务器
            
            # 4. 工具集（根据类型）
            "tools": self._get_tools_for_type(subagent_type),
            
            # 5. 明确不包含对话历史
            "conversation_history": None,  # ❌ 显式设为 None
        }
        
        return context
```

### 6.2 并发控制

```python
class SubAgentPool:
    """子 Agent 池（控制并发）"""
    
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_agents: dict[str, LeonAgent] = {}
    
    async def spawn(
        self,
        prompt: str,
        subagent_type: str,
        **kwargs
    ) -> SubAgentResult:
        """生成子 Agent（带并发控制）"""
        
        async with self.semaphore:
            # 检查当前活跃数
            if len(self.active_agents) >= self.max_concurrent:
                raise Exception(
                    f"已达到最大并发数 {self.max_concurrent}，"
                    "请等待其他子 Agent 完成"
                )
            
            # 创建并执行
            agent = await self._create_agent(subagent_type, **kwargs)
            agent_id = agent.session_id
            self.active_agents[agent_id] = agent
            
            try:
                result = await agent.run(prompt)
                return SubAgentResult(
                    output=result,
                    agent_id=agent_id,
                    success=True,
                    error=None,
                    token_usage=agent.get_token_usage()
                )
            finally:
                # 清理（凋亡）
                del self.active_agents[agent_id]
```

### 6.3 Resume 机制

```python
class SubAgentSession:
    """子 Agent 会话管理"""
    
    def __init__(self):
        self.sessions: dict[str, dict] = {}
    
    def save_session(self, agent_id: str, agent: LeonAgent):
        """保存会话（支持 resume）"""
        self.sessions[agent_id] = {
            "agent": agent,
            "history": agent.get_conversation_history(),
            "created_at": datetime.now(),
        }
    
    def resume_session(self, agent_id: str) -> Optional[LeonAgent]:
        """恢复会话"""
        if agent_id not in self.sessions:
            return None
        
        session = self.sessions[agent_id]
        agent = session["agent"]
        
        # 恢复对话历史（只在 resume 时恢复！）
        agent.restore_history(session["history"])
        
        return agent
    
    def cleanup_old_sessions(self, max_age_minutes: int = 30):
        """清理旧会话（防止内存泄漏）"""
        now = datetime.now()
        to_remove = []
        
        for agent_id, session in self.sessions.items():
            age = (now - session["created_at"]).total_seconds() / 60
            if age > max_age_minutes:
                to_remove.append(agent_id)
        
        for agent_id in to_remove:
            del self.sessions[agent_id]
```

---

## 七、测试用例

### 7.1 单元测试

```python
# tests/test_subagent.py

import pytest
from leon.middleware.subagent import SubAgentMiddleware

@pytest.mark.asyncio
async def test_spawn_explore_agent():
    """测试生成 explore 子 Agent"""
    
    middleware = SubAgentMiddleware(profile)
    
    result = await middleware.execute(
        prompt="列出 middleware/ 目录下的所有文件",
        subagent_type="explore",
        description="列出中间件文件"
    )
    
    assert result.success
    assert "middleware" in result.output.lower()
    assert result.agent_id  # 应该返回 agent_id

@pytest.mark.asyncio
async def test_spawn_shell_agent():
    """测试生成 shell 子 Agent"""
    
    middleware = SubAgentMiddleware(profile)
    
    result = await middleware.execute(
        prompt="运行 git status",
        subagent_type="shell",
        description="查看 Git 状态"
    )
    
    assert result.success
    assert "branch" in result.output.lower() or "working tree" in result.output.lower()

@pytest.mark.asyncio
async def test_parallel_agents():
    """测试并行执行多个子 Agent"""
    
    middleware = SubAgentMiddleware(profile)
    
    tasks = [
        middleware.execute(
            prompt="列出根目录文件",
            subagent_type="explore",
            description="列出根文件"
        ),
        middleware.execute(
            prompt="查看 Git 分支",
            subagent_type="shell",
            description="查看分支"
        ),
        middleware.execute(
            prompt="搜索 'Agent' 关键词",
            subagent_type="explore",
            description="搜索关键词"
        ),
    ]
    
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 3
    assert all(r.success for r in results)

@pytest.mark.asyncio
async def test_resume_agent():
    """测试 resume 机制"""
    
    middleware = SubAgentMiddleware(profile)
    
    # 第一次调用
    result1 = await middleware.execute(
        prompt="探索 middleware/ 目录",
        subagent_type="explore",
        description="探索中间件"
    )
    agent_id = result1.agent_id
    
    # 第二次调用（resume）
    result2 = await middleware.execute(
        prompt="刚才找到了哪些文件？",
        subagent_type="explore",
        description="查询结果",
        resume=agent_id
    )
    
    assert result2.success
    assert result2.agent_id == agent_id  # 应该是同一个 agent_id

@pytest.mark.asyncio
async def test_context_isolation():
    """测试上下文隔离（不继承对话历史）"""
    
    # 主 Agent 有一段对话历史
    main_agent = LeonAgent(profile)
    await main_agent.run("用户问题 1")
    await main_agent.run("用户问题 2")
    await main_agent.run("用户问题 3")
    
    # 生成子 Agent
    middleware = SubAgentMiddleware(profile)
    result = await middleware.execute(
        prompt="我们刚才讨论了什么？",
        subagent_type="generalPurpose",
        description="查询历史"
    )
    
    # 子 Agent 应该看不到历史
    assert "看不到" in result.output.lower() or "没有" in result.output.lower()
```

### 7.2 集成测试

```python
# tests/test_subagent_integration.py

@pytest.mark.asyncio
async def test_full_workflow():
    """测试完整工作流：主 Agent → 子 Agent → 结果汇总"""
    
    # 1. 主 Agent 收到用户请求
    main_agent = LeonAgent(profile)
    user_input = "分析整个项目的架构"
    
    # 2. 主 Agent 决策：需要并行探索
    tasks = [
        main_agent.task(
            prompt="探索 middleware/ 目录",
            subagent_type="explore",
            description="探索 middleware"
        ),
        main_agent.task(
            prompt="探索 tui/ 目录",
            subagent_type="explore",
            description="探索 TUI"
        ),
        main_agent.task(
            prompt="读取 agent.py",
            subagent_type="explore",
            description="读取核心文件"
        ),
    ]
    
    # 3. 并行执行
    results = await asyncio.gather(*tasks)
    
    # 4. 主 Agent 汇总
    summary = main_agent.synthesize_results(results)
    
    # 5. 验证
    assert "middleware" in summary.lower()
    assert "tui" in summary.lower()
    assert "agent" in summary.lower()
```

---

## 八、配置和部署

### 8.1 配置文件

```yaml
# profiles/default.yaml

agent:
  model: "gpt-4"
  workspace_root: "/path/to/project"

subagent:
  enabled: true
  max_concurrent: 4        # 最大并行数
  session_timeout: 30      # 会话超时（分钟）
  
  types:
    generalPurpose:
      enabled: true
      max_tokens: 100000
      
    explore:
      enabled: true
      max_tokens: 50000
      readonly: true         # 强制只读
      
    shell:
      enabled: true
      max_tokens: 30000

middleware:
  subagent:
    priority: 10             # 高优先级（在其他中间件之前）
```

### 8.2 注册中间件

```python
# leon/agent.py

class LeonAgent:
    def __init__(self, profile: AgentProfile):
        self.profile = profile
        
        # 注册中间件栈
        self.middleware = [
            PromptCachingMiddleware(profile),
            
            # ⭐ 新增：SubAgent 中间件
            SubAgentMiddleware(profile),  # 高优先级
            
            FileSystemMiddleware(profile),
            SearchMiddleware(profile),
            WebMiddleware(profile),
            CommandMiddleware(profile),
            SkillsMiddleware(profile),
        ]
    
    async def run(self, user_input: str) -> str:
        """运行 Agent"""
        
        # 构建工具集（包含 task 工具）
        tools = []
        for mw in self.middleware:
            tools.extend(mw.get_tools())
        
        # 调用 LLM
        response = await self.llm.chat(
            messages=[{"role": "user", "content": user_input}],
            tools=tools
        )
        
        # 处理工具调用
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.name == "task":
                    # 调用 SubAgent 中间件
                    result = await self.middleware.subagent.execute(**tool_call.arguments)
                    return result.output
        
        return response.content
```

---

## 九、监控和调试

### 9.1 日志记录

```python
import logging

logger = logging.getLogger("leon.subagent")

class SubAgentMiddleware:
    async def execute(self, ...):
        logger.info(
            f"Spawning SubAgent: type={subagent_type}, "
            f"description={description}, "
            f"readonly={readonly}"
        )
        
        start_time = time.time()
        
        try:
            result = await self._run_agent(agent, prompt)
            
            elapsed = time.time() - start_time
            logger.info(
                f"SubAgent completed: agent_id={agent_id}, "
                f"elapsed={elapsed:.2f}s, "
                f"tokens={result.token_usage}"
            )
            
            return result
        
        except Exception as e:
            logger.error(
                f"SubAgent failed: agent_id={agent_id}, "
                f"error={str(e)}"
            )
            raise
```

### 9.2 性能监控

```python
class SubAgentMetrics:
    """子 Agent 性能指标"""
    
    def __init__(self):
        self.metrics = {
            "total_spawned": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_tokens": 0,
            "average_duration": 0,
            "by_type": {
                "generalPurpose": {"count": 0, "tokens": 0},
                "explore": {"count": 0, "tokens": 0},
                "shell": {"count": 0, "tokens": 0},
            }
        }
    
    def record_spawn(self, subagent_type: str):
        self.metrics["total_spawned"] += 1
        self.metrics["by_type"][subagent_type]["count"] += 1
    
    def record_completion(
        self,
        subagent_type: str,
        duration: float,
        tokens: int,
        success: bool
    ):
        if success:
            self.metrics["total_completed"] += 1
        else:
            self.metrics["total_failed"] += 1
        
        self.metrics["total_tokens"] += tokens
        self.metrics["by_type"][subagent_type]["tokens"] += tokens
        
        # 更新平均时长
        total = self.metrics["total_completed"] + self.metrics["total_failed"]
        current_avg = self.metrics["average_duration"]
        self.metrics["average_duration"] = (
            (current_avg * (total - 1) + duration) / total
        )
    
    def get_summary(self) -> dict:
        return self.metrics
```

---

## 十、最佳实践和常见陷阱

### 10.1 最佳实践

✅ **DO：明确任务目标**
```python
# Good
await agent.task(
    prompt="""
    探索 middleware/ 目录，找出所有中间件。
    对每个中间件：
    1. 读取主要文件
    2. 识别提供的工具
    3. 总结职责
    返回表格：中间件名 | 工具列表 | 职责
    """,
    ...
)
```

✅ **DO：选择合适的子 Agent 类型**
```python
# 只读搜索 → explore
await agent.task(..., subagent_type="explore")

# 多步骤命令 → shell
await agent.task(..., subagent_type="shell")

# 需要修改文件 → generalPurpose
await agent.task(..., subagent_type="generalPurpose")
```

✅ **DO：利用并行能力**
```python
# Good：并行执行独立任务
tasks = [
    agent.task(...),
    agent.task(...),
    agent.task(...),
]
results = await asyncio.gather(*tasks)
```

✅ **DO：使用 Resume 保持上下文**
```python
# Good：多轮交互
result1 = await agent.task(...)
agent_id = result1.agent_id

result2 = await agent.task(..., resume=agent_id)
```

### 10.2 常见陷阱

❌ **DON'T：假设子 Agent 能看到历史**
```python
# Bad：子 Agent 看不到之前的对话
await main_agent.run("我们讨论了生物学模型")
await agent.task(
    prompt="刚才讨论的模型是什么？",  # ❌ 子 Agent 不知道
    ...
)

# Good：显式传递上下文
await agent.task(
    prompt="""
    背景：我们讨论了基于细胞分化的 Agent 模型。
    问题：这个模型的核心概念是什么？
    """,
    ...
)
```

❌ **DON'T：过度使用子 Agent**
```python
# Bad：简单任务也用子 Agent（浪费）
await agent.task(
    prompt="列出当前目录",
    subagent_type="shell",
    description="ls"
)

# Good：主 Agent 直接执行
await agent.run_command("ls")
```

❌ **DON'T：超过并发限制**
```python
# Bad：启动太多子 Agent
tasks = [agent.task(...) for _ in range(10)]  # ❌ 超过限制 4
await asyncio.gather(*tasks)

# Good：批量处理
for batch in chunks(tasks, 4):
    await asyncio.gather(*batch)
```

❌ **DON'T：忘记处理错误**
```python
# Bad：不检查结果
result = await agent.task(...)
print(result.output)  # ❌ 可能失败了

# Good：检查成功状态
result = await agent.task(...)
if result.success:
    print(result.output)
else:
    print(f"Error: {result.error}")
```

---

## 十一、FAQ

### Q1: 子 Agent 和主 Agent 使用相同的模型吗？

A: 默认是，但可以通过 `model` 参数指定。

```python
# 使用快速模型（节省成本）
await agent.task(
    prompt="列出文件",
    subagent_type="explore",
    model="fast"  # ⚡ 快速但简单
)
```

### Q2: 子 Agent 会消耗多少 Token？

A: 取决于类型和任务复杂度：

| 类型 | 典型消耗 | 说明 |
|------|---------|------|
| explore | 5,000 - 20,000 | 只读搜索，系统提示较短 |
| shell | 3,000 - 15,000 | 专注命令执行 |
| generalPurpose | 10,000 - 50,000 | 全功能，系统提示最长 |

相比主 Agent 每次调用 5,000+ tokens，子 Agent 在多步骤任务中能节省 70%+ Token。

### Q3: Resume 机制会保留多久？

A: 默认 30 分钟，超时自动清理。

```python
# 配置文件中设置
subagent:
  session_timeout: 60  # 60 分钟
```

### Q4: 子 Agent 可以嵌套吗？（子 Agent 调用子 Agent）

A: 技术上可以，但**不推荐**。

```python
# ❌ 不推荐：嵌套子 Agent
await agent.task(
    prompt="启动另一个子 Agent 来...",  # ❌ 复杂度爆炸
    ...
)

# ✅ 推荐：主 Agent 协调多个子 Agent
results = await asyncio.gather(
    agent.task(...),
    agent.task(...),
)
```

### Q5: 如何调试子 Agent？

A: 启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("leon.subagent")
logger.setLevel(logging.DEBUG)
```

---

## 十二、迁移路径

### 12.1 从单 Agent 到多 Agent

```python
# 旧代码（单 Agent）
async def analyze_project():
    # 主 Agent 做所有事情
    files = await agent.list_dir("middleware/")
    for file in files:
        content = await agent.read_file(file)
        analysis = await agent.analyze(content)
    return analysis

# 新代码（多 Agent）
async def analyze_project():
    # 并行探索
    result = await agent.task(
        prompt="""
        探索 middleware/ 目录，分析所有中间件。
        对每个中间件文件：
        1. 读取内容
        2. 分析功能
        3. 总结职责
        返回完整报告
        """,
        subagent_type="explore",
        description="分析中间件"
    )
    return result.output
```

### 12.2 分阶段迁移

**阶段 1：实现基础框架**
- [ ] 实现 SubAgentMiddleware
- [ ] 实现三种子 Agent 类型
- [ ] 实现上下文构建器
- [ ] 单元测试

**阶段 2：并发控制**
- [ ] 实现 SubAgentPool
- [ ] 实现并发限制（4 个）
- [ ] 测试并行执行

**阶段 3：Resume 机制**
- [ ] 实现 SubAgentSession
- [ ] 实现会话保存/恢复
- [ ] 实现超时清理

**阶段 4：监控和优化**
- [ ] 添加日志记录
- [ ] 添加性能监控
- [ ] 优化 Token 使用

---

## 十三、总结

### 核心要点

1. **上下文隔离** - 子 Agent 不继承对话历史（节省 Token）
2. **配置继承** - 子 Agent 继承系统信息、Skills、MCP
3. **三种类型** - generalPurpose（全能）、explore（只读）、shell（命令）
4. **并行执行** - 最多 4 个子 Agent 并行
5. **Resume 机制** - 支持多轮交互保留上下文

### 生物学类比

```
主 Agent = 干细胞（多能，决策）
    ↓ 分化
子 Agent = 特化细胞（专一，高效）
    ├─ generalPurpose = 祖细胞（多能但受限）
    ├─ explore = 感觉神经元（只读感知）
    └─ shell = 运动神经元（执行命令）
```

### Token 效率

```
单 Agent（8 个命令）：
- 8 次调用 × 5,500 tokens = 44,000 tokens

多 Agent（shell 子 Agent）：
- 1 次调用 ≈ 10,500 tokens
- 节省：76%！
```

### 下一步

1. 阅读本文档
2. 实现 SubAgentMiddleware
3. 编写单元测试
4. 集成到 Leon Agent
5. 测试实际场景
6. 优化性能

---

**文档版本**: 1.0  
**创建日期**: 2026-02-03  
**作者**: Leon Team  
**状态**: Draft → Review → Implementation
