# 当前敲定的方案（Summary）

## 1) 目标与约束
- **目标**：支持“多 Agent”——每个 Agent 能用不同的 `system_prompt`、启用/禁用不同 tools（file/search/web/shell/mcp/skill）、挂不同 MCP。
- **约束**：
  - 不搞多层抽象导致维护困难（避免“为了插件而插件”）。
  - **静态提示词**与**动态提示词**分工清晰：静态可配置/聚合，动态就地生成（middleware/validator）。

---

## 2) 架构核心：Agent Profile（配置档案）
- 每个 Agent 用一个 **Profile**（YAML/JSON）描述：
  - **`system_prompt`**（角色/规则/偏好）
  - **`tools`**（启用哪些 tools；只做开关，不做参数化）
  - **`mcp_servers`**（要连接哪些 MCP server）
  - **`skill`**（是否启用 skill 能力）
- LeonAgent 初始化时读取 profile，并据此构建 middleware 栈、合成最终 system prompt。

### Profile 的职责边界
- **Profile 管**：
  - 该 Agent “是谁”（system prompt）
  - 该 Agent “能用什么”（tools/mcp/skill）
- **middleware 管**：
  - 工具 schema 注入（wrap_model_call）
  - 工具执行与运行时校验（wrap_tool_call / _validate_path 等）

---

## 3) Core Tools
- `filesystem/search/web/shell/mcp/skill` 都被视为 **core tools**（不引入 capabilities 概念）。
- 是否启用，交给 profile 来决定（配置驱动）；只做开关，不做参数化。

---

## 4) Prompt 分层：静态 vs 动态
### 静态（可统筹、可配置、可聚合）
- 由 agent.py::_build_system_prompt() 生成：  
  - **Context 注入**（你推荐的做法）：`workspace_root` + OS + shell 
  - + Profile 的 `system_prompt`
  - + 少量通用规则（不要在这里塞每个工具的参数细节）

### 动态（运行时触达，难以/不应统筹）
- 由各 middleware 在运行时产生：  
  - 例如路径校验失败返回的纠错建议、命令被拦截的解释等
- 可选增强：只把“错误模板”抽成常量/模板，但生成仍在 middleware 内完成。

---

## 5) 这次已落地的最小修复（针对 `.` 相对路径）
- **工具参数描述**：在 middleware/filesystem/middleware.py 里把 `file_path/directory_path` 的 description 明确写了 **禁止 `.` / `..`**（同步/异步两份 schema 都改了）。
- **系统提示词 Context 注入**：在 agent.py 的 system prompt 开头注入了 workspace/os/shell。

---

## 6) 下一步落地方向（如果继续推进多 Agent）
- **新增 `AgentProfile` 结构**（`agent_profile.py`）+ `agents/*.yaml`：
  - `coder.yaml` / `reviewer.yaml` / `researcher.yaml` 等
- **在 LeonAgent 增加 `profile` 参数**：
  - 支持传路径或对象；不传则走默认 profile
- **方案已敲定**：用 **Agent Profile 配置驱动** 实现多 Agent；core tools 由配置启停；静态 prompt 聚合、动态 prompt 就地生成。

是的，刚才那版总结偏“架构决策”，确实漏了几条我们之前反复碰到、而且会影响后续工程化落地的**技术细节/坑位**。我把重要的补全在这里（按影响面排序）：

## 1) 同步/异步执行模型的约束（LangGraph / middleware）
- **现象**：`Synchronous implementation of wrap_tool_call is not available`
- **本质**：middleware 里只有 awrap_tool_call（或工具本身依赖 async）时，TUI/CLI 若走同步 `stream()` 就会踩雷；必须走 `astream()` 并且 UI 侧也要在 async 上下文里消费。
- **工程含义**：多 Agent / 多 Profile 时，要在配置层明确“运行模式”（sync/async）或在上层统一强制 async，避免某个 Agent 混用导致工具链断裂。

## 2) “相对路径 `.`”不是工具 bug，而是**模型-工具契约**的缺口
- 我们最终做的是：在工具参数描述里明确禁止 `.`/`..`，并在 system prompt 注入 workspace context。
- **更关键的工程结论**：  
  - **契约应以 Tool Schema 为准**（参数描述/JSON Schema），system prompt 只给原则，避免重复。
  - 运行时错误信息（dynamic prompt）要尽量“可恢复”（给 suggestion），否则模型会反复试错。

## 3) Tool schema 在 middleware 里有“双份”（sync/async 两套注入）
- FileSystemMiddleware 里存在 wrap_model_call 和 awrap_model_call 两套 tools 注入，因此我们当时 `edit` 会遇到“同一字符串出现 2 次”的问题。
- **工程含义**：未来做“配置化/多 Agent”时，需要一个明确策略：
  - 要么接受双份并确保两份一致（最好通过函数生成，避免复制粘贴）
  - 要么收敛成单份并让 sync 路径不可用/自动桥接
