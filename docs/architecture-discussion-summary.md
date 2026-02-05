# Leon 架构讨论总结

> 日期：2026-02-05
> 状态：初步讨论，待进一步设计

## 一、战略背景（来自 Jack）

### 1.1 项目定位

人机协同平台要解决的核心问题：**Agent 能力在指数级增长，但管理和协作基础设施还停留在初级阶段**。

四大核心痛点：
- 人机协作效率瓶颈：用户同时管理多个 Agent 时，缺乏统一的监控与调度机制
- Agent 间协同机制缺失：现有框架中 Agent 在任务结束后即失去身份，无法建立持久化的协作关系
- 人际协作同步依赖：传统协作高度依赖成员的实时在场
- Agent 能力流通受阻：开发者生态缺乏经济激励机制

### 1.2 最新战略调整

**能力市场已被淡化**，不是当前重点。

当前核心聚焦：
- **数字分身** + **多 Agent 协同** + **人机协作效率**
- 商业模式：**按人头计费**（20-30 元/月/员工）
- 6 个月目标：中关村学院试点 + 企业级功能

### 1.3 Leon 的定位

Leon 是平台的**基础设施层**，负责：
- 持久化通信协议（WebSocket 长连接、会话恢复）
- Agent 生命周期管理（持久身份、状态保留）
- 多 Agent 协同的技术基础（消息路由、上下文压缩）

关键技术指标：
- 通信延迟 ≤500ms
- 支持 ≥10 个 Agent 协同管理
- 新 Agent 接入 <5 分钟

---

## 二、上云架构讨论

### 2.1 用户的核心困惑

当前 Leon 使用 YAML/JSON 本地配置，未来要上云做多用户 SaaS。困惑点：
- 配置文件上云后怎么办？
- 全存数据库？还是混合存储？
- 如何设计才能让迁移成本最小？

### 2.2 数据分类

| 类型 | 说明 | 存储策略 |
|------|------|----------|
| **定义**（Agent 是什么） | AgentProfile、MCP、Skill 配置 | 可以是文件或数据库 |
| **状态**（Agent 在做什么） | 会话历史、消息、上下文 | 必须数据库持久化 |

### 2.3 最小迁移成本方案

**配置数据 → 直接存数据库（Supabase）**
- AgentProfile → Supabase 表
- Skill → Supabase 表
- MCP 配置 → Supabase 表

**会话/消息 → LangChain 持久化**（用户已有方案）

**用户工作区 → 交给 AgentBay**，不自己实现文件同步或挂载

---

## 三、Sandbox 方案

### 3.1 Manus Sandbox 分析

用户爬取了 Manus 的沙盒文件结构，关键发现：

**目录结构**：
```
/home/ubuntu/
├── .browser_data_dir/    # 完整的 Chromium 浏览器环境
├── .config/              # 应用配置
│   ├── code-server/      # VS Code Server
│   └── state-sync/       # 状态同步服务
├── .env                  # 环境变量
├── .secrets/             # 敏感信息
├── .logs/                # 日志
├── Downloads/            # 下载目录
└── skills/               # Skill 目录
    ├── .skill_versions.json
    └── <skill-name>/SKILL.md
```

**持久化方案验证**：
- 执行 `lsblk`、`mount`、`df -h` 等命令
- 结果：只有一个 vda 磁盘（42G），挂载在根目录 /
- 没有额外的块设备挂载
- 发现 `state-sync` 服务，配置为 `pull: true, push: true`

**结论**：Manus 使用 **state-sync 同步方案**，不是挂载方案。启动时拉取，运行时/关闭前推送。

### 3.2 用户的偏好

用户更偏好**持久化挂载方案**，而不是同步方案。理由：
- 数据量大时拉取慢
- 同步可能有延迟和一致性问题
- 挂载更可靠

### 3.3 Sandbox 是基础设施

用户明确：**Sandbox 是必须的基础设施**，不应该因为复杂度而回避。

既然 Sandbox 必须做：
- Skill 可以是代码（Python/JS），在 Sandbox 里执行
- MCP 服务器也可以平台托管，跑在 Sandbox 里
- 用户的自定义逻辑都可以在 Sandbox 里安全执行

### 3.4 Sandbox 集成方案

用户的方案：
1. 首先集成 **AgentBay**
2. 后续接一些本地的 Sandbox 方案
3. 用户文件系统会挂载在 Sandbox

架构：
```
用户的 Sandbox VM ──挂载──► 用户的持久存储（云盘）
```

### 3.5 Sandbox 抽象层设计

用户需求：支持多种 Sandbox 后端的水平扩展
1. AgentBay（云端 Sandbox）
2. Docker（本地容器）
3. Local（本地非隔离模式）

Sandbox 提供两个核心能力：**终端** + **文件系统**

**接口设计**：

```python
class Terminal(Protocol):
    """终端能力"""
    def execute(self, command: str, timeout: int = 120) -> ExecuteResult: ...
    def execute_async(self, command: str) -> str: ...
    def get_status(self, task_id: str) -> TaskStatus: ...


class FileSystem(Protocol):
    """文件系统能力"""
    def read(self, path: str) -> bytes: ...
    def write(self, path: str, content: bytes) -> None: ...
    def list_dir(self, path: str) -> list[FileInfo]: ...
    def exists(self, path: str) -> bool: ...
    def delete(self, path: str) -> None: ...


class Sandbox(ABC):
    """Sandbox 统一接口"""
    @property
    def terminal(self) -> Terminal: ...
    @property
    def filesystem(self) -> FileSystem: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

**配置模型（Discriminated Union）**：

```python
class AgentBaySandboxConfig(BaseModel):
    type: Literal["agentbay"] = "agentbay"
    api_key: str | None = None
    region: str | None = None
    mounts: list[MountConfig] = Field(default_factory=list)
    limits: ResourceLimits = Field(default_factory=ResourceLimits)


class DockerSandboxConfig(BaseModel):
    type: Literal["docker"] = "docker"
    image: str = "leon-sandbox:latest"
    network: str = "none"
    mounts: list[MountConfig] = Field(default_factory=list)


class LocalSandboxConfig(BaseModel):
    type: Literal["local"] = "local"
    workspace_root: str
    allowed_paths: list[str] = Field(default_factory=list)


SandboxConfig = AgentBaySandboxConfig | DockerSandboxConfig | LocalSandboxConfig
```

**工厂函数**：

```python
def create_sandbox(config: SandboxConfig) -> Sandbox:
    match config.type:
        case "agentbay": return AgentBaySandbox(config)
        case "docker": return DockerSandbox(config)
        case "local": return LocalSandbox(config)
```

---

## 四、AgentProfile 配置设计

### 4.1 格式选择

用户决定：**从 YAML 改为 JSON**，以便兼容 Claude Code 的 MCP 配置格式。

### 4.2 Claude Code 的 MCP 配置格式

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "disabled": false,
      "env": {
        "KEY": "value"
      }
    }
  }
}
```

### 4.3 System Prompt 的问题

System Prompt 是富文本，直接写在 JSON 里很痛苦（转义地狱）。

### 4.4 Claude Code 的分层设计

Claude Code 的配置是分层的：

```
┌─────────────────────────────────────┐
│ 1. 内置 System Prompt（不可见）      │  ← Anthropic 写的，固定
├─────────────────────────────────────┤
│ 2. ~/.claude/CLAUDE.md              │  ← 用户全局 Prompt
├─────────────────────────────────────┤
│ 3. 项目/CLAUDE.md                   │  ← 项目级 Prompt
├─────────────────────────────────────┤
│ 4. .claude/settings.json            │  ← MCP、权限等配置
├─────────────────────────────────────┤
│ 5. ~/.mcp.json                      │  ← MCP 服务器
└─────────────────────────────────────┘
```

**关键洞察**：配置和 Prompt 是分开的
- **Prompt**：Markdown 文件，可以多层叠加
- **配置**：JSON 文件，结构化数据

### 4.5 Leon 的分层设计

**本地模式**：

```
┌─────────────────────────────────────┐
│ 1. 内置 System Prompt               │  ← Leon 默认的
├─────────────────────────────────────┤
│ 2. ~/.leon/LEON.md                  │  ← 用户全局 Prompt
├─────────────────────────────────────┤
│ 3. 项目/LEON.md                     │  ← 项目级 Prompt
├─────────────────────────────────────┤
│ 4. ~/.leon/config.json              │  ← 全局配置（MCP 等）
├─────────────────────────────────────┤
│ 5. 项目/.leon/config.json           │  ← 项目配置
└─────────────────────────────────────┘
```

**云端模式**（三层）：

```
┌─────────────────────────────────────┐
│ 1. 平台默认（内置）                  │
├─────────────────────────────────────┤
│ 2. 用户级配置                        │  ← user_configs 表
├─────────────────────────────────────┤
│ 3. 工作区/项目级配置                 │  ← workspace_configs 表
└─────────────────────────────────────┘
```

用户确认：**云端也保留工作区/项目的概念**。

### 4.6 数据库表设计

```sql
-- 用户级配置
CREATE TABLE user_configs (
    user_id UUID PRIMARY KEY,
    prompt TEXT,           -- 用户的全局 LEON.md
    config JSONB           -- MCP、Tools 等
);

-- 工作区级配置
CREATE TABLE workspace_configs (
    id UUID PRIMARY KEY,
    user_id UUID,
    name TEXT,
    prompt TEXT,           -- 工作区的 LEON.md
    config JSONB           -- 覆盖用户级的配置
);
```

### 4.7 合并逻辑

```python
def build_agent_profile(user_id: str, workspace_id: str | None) -> AgentProfile:
    # 1. 平台默认
    prompt = BUILTIN_PROMPT
    config = DEFAULT_CONFIG

    # 2. 用户级
    user_cfg = db.get_user_config(user_id)
    if user_cfg:
        prompt += "\n\n" + user_cfg.prompt
        config = merge_config(config, user_cfg.config)

    # 3. 工作区级
    if workspace_id:
        ws_cfg = db.get_workspace_config(workspace_id)
        if ws_cfg:
            prompt += "\n\n" + ws_cfg.prompt
            config = merge_config(config, ws_cfg.config)

    return AgentProfile(system_prompt=prompt, **config)
```

---

## 五、用户偏好总结

1. **持久化优于同步**：偏好挂载方案，而不是 state-sync 同步
2. **Sandbox 是基础设施**：不因复杂度而回避，Skill 可以是代码
3. **兼容 Claude Code**：MCP 配置格式兼容，降低迁移成本
4. **Prompt 和配置分离**：Prompt 用 Markdown，配置用 JSON
5. **分层配置**：本地和云端都支持多层配置叠加
6. **保留工作区概念**：云端也有用户级 + 工作区级的分层
7. **最小迁移成本**：设计抽象层，让本地到云端的迁移平滑

---

## 六、待解决问题

1. 用户提到有"更好的系统级设计"，待进一步讨论
2. 具体的数据模型和 Pydantic 定义需要细化
3. 本地和云端的配置合并逻辑需要统一
4. Sandbox 的具体集成方案（AgentBay API）

---

## 七、相关文件

- `/Users/apple/Desktop/project/v1/文稿/project/leon/agent_profile.py` - 当前的 AgentProfile 定义
- `/Users/apple/Desktop/project/v1/文稿/project/leon/profiles/default.yaml` - 当前的默认配置
- `/Users/apple/.mcp.json` - Claude Code 的 MCP 配置示例
- `/Users/apple/.claude/settings.json` - Claude Code 的设置示例
- `/Users/apple/Desktop/project/v1/文稿/project/leon/survey/filesystem_tree.txt` - Manus Sandbox 文件结构
