# LEON (Lane Runtime)

LEON 是一个面向企业级生产可用的 Agent Runtime：用于构建、运行与治理一组可长期运行的 Agent，并把它们当作可持续协作的 co-workers 来管理与调度。

LEON 以 LangChain Middleware 为核心架构：通过统一的 middleware 管线完成 tool 注入、运行时校验、安全拦截、上下文装载/卸载与可观测性。

[![](https://mermaid.ink/img/pako:eNqtWv9v00gW_1esICRWMm3zraXRHVJJW-jR0gqH7Wqvp8iJJ4lVx45spyUHSLBcoRRKy7FQWOAOWNjtrZYCq12-9Av8M3WS_hf3ZsYe24kd2rvkB5gv731m5s17b97HcCGS1yQUSUWKulgpcZkTMyoHv8OHuT-H_ZjEONJUbqiIVJMb0vMl2UR5s6oj7si5iiSaSPpqP1hUxqjm6AaGzqZP_XUmEgI9E_kblcc_Mg2yVCyt6ehPOb33OFYlQz7hKV0ryApyxO0uUZiqSaJqyvm9heXGzgbRcvXYxibGhkF5QpYkBc2LcMpxsYZ07ki_9fa7r3xL2cuVK2ZazJfwkm5PVosuBFl9SDVLulaR843tu9arB7vbD6xb99vwRmGzQs0wURng3E4LVv3-9d2td_W7y7s7j9sgBCSCJUGdNlpUd7d-bDy9Ul993Pj9eZvqNMqBHvzZogQjVGP3w23r2oK18bF5-7210r79tFYui6oEIHarBci6s7O79aJ-4-fms1vtG5-VFcXAGyeN1jMvXW5e3al_WG1-fmRtr1hLT5s7Oz4MpEqBNzoq-GzJZTRNMdpWP4tEaZR6jg7NLHMb68UP9afbsGTz9RacmbrS8Gjv1FTmm94zmolymjbbbkodfNnGm8dtD-DiI2trs37_Db3GNtURSTZtTQRNj-KrtcavP-1--K3-6HN9-Xlj-37z05029YmqYsoYA_TLuJ3FKNSGNz7uXV8J0RuXDXNY1kFLgVZWknV7t2vW9c3Gow1r596-zC1kmO-FmPqkjirMS4vQyRqkR9cj_kXdjQzocgXLcL3cVM0saWpAzKjSidoZsYwtVoBONlfLqtD1xIq1uuyBLEjBaGFHms7QsAg5D8yw48yjnO804DybqyHhhl3unK44HlfVlWxeU01IW0T33NnxjsH2tYzm01QeIOagl8WreyGsxWvWkzXbpP9-2Xh8syXt-Y45dXby67HhkbMCTWVzsgSJb1RUlJyYn-XSJVFuN77_6kdwWqcA9Mz1ldXdT4-alxcCFfEvI87JSg0UaIPmyjGaHkPsxgLlvAh68CdRar5-tfvxxhdURmUd5XVxXiEpwW4T9cbOnb1nf9SX7gaZmjlH6NFHRzLOyW1zf_Hkf5FVvH_8l3PfoBS2PAltUZ-VtHlVLmCDeXpE_1RmYry58ytkhv3t3zcQ5vrpjJvMwzJnVU2Xcc7Xqyp4HxElG9p7sGU9-1evtf1d_dXLkKQPmoIpmlWc923drEEGqAMT3cbSu_rlK-DAzdfPOznwyDcjacCZFMA1UL5qaroRaIpvjRIWAFG7hUXJemUxPykE6pwQmZLTZFrjslo9H6g1Jdg6U9o80oUSUhSf5jSkK22-fZf7uhvhNHssOfq2tSd1TZSIBE7r0M4auON5UAPeUfYWD6MCeY5Pj42P95TpnY7qkF7Komki3Vq4Wr_3pr68sa8cOpGewj6bnuLGID_BmCkH5HKYTysyzWjkIROQPod0NsyS6uNla-mZ9XC9sfGssXotCIc4K34D85UspGQMk82aMGhj3N-7um69f2ktvG--udr4fr0NAwPAOwwnxdkJOhztQW1HICAxwqVKBNNoPNyBN8Za3t8beWpy8jROFaegdAi9OzyJ74-sjzsc7dFsd_0Xa2md3l595Z9OHRESGAKJCwEcD0qRGkEOjoxhUS0iXasaNKLdLg1NA2tS-y2_3Xv4H7ueu_lTffEXMlzRZQ0vkeKSwfEgmiVnGzgqPF0G3Xz_2vr0D2vjhrWwXv_xMoR9IBQukaaQXpYNAzzJLvHcAQZnF8tPru49XA2Ba7kmn-nGJ09inqIVi3DvHSwHBsNC5LJsa9G-azJqrLWX1ue15sab1nrKey6GhDtD-TwyjBYweqrmxue9tQ0K-b_lkMy5Mezd2GyqqHDnxrgjGXTerIpKO9kB2aFKxWZt0KKE4sOWtfm9Ez8hRpweGz45ksEePy1LRWSGmLAkmmNqpYqDn7Xpad8t1q-8bn66ay0EO8OEUbSRceIAc4lFxNkjHgTr7b3Gi81AhFNQ9Gp67YQO6ZhGnG-A3uDta9bKb_U_Vpo_LwaCZEq4knMxfH1aZmx-bqzftBavBz3TnfxQGBGEsckzJIyJg0M1oMIpy60M2OWBRGyiqLs6VIXuZHf7h-brJ_VbV3Y_LgRRUcrn1IJcpBB224NAiXRIBu7kfYcPc0fhR7g8N6rgB9DP9mH6uEPlg6aApAfheVg7rVbVAJ5OAFw66Mp4KCIWoSW9O21TGjwFBb87jnkBHrSD3p1wqiYCRl7pL-zZ1OwKK2xLDkcNFWCsM1TCIZehAow-hkrYRNF7GI9tXHIXOO2SNa--Y0PGpNqnbLLUPuGhQb5Jz6KUWriztM8d7Tl6_GLB5jcXMZ1wRaDTOs_4gitlb4osgut4dwb3WgE8Bbv38F4_obV08BwrlT3rE3Eya1eygXNOwRo4SUtU323SkpLctVM_urNsyHVsXCgG-nZLtRcUyU5l506yIUegJSj8826VFrQD-l4HmtMtr9x5d4yIeKuhUCFvDRMq5K9NQsVYEdERyBFxhbwbpV43Jyoy_jh7sc2lvPv9kqx_263SQUmUnYAKi1XIJMG4AWJewPa7hPLDE8KkFiEmoR-Bg2ZYERE469YMgdP-9z9QxPe8B0q4j3DwBp33lc56nsl9fZgfhoQCm4AagBPMmgIF6v6_xINMWlTnRIPr5fAnI3gunTMYgIXIF3oOHmAldagvF43F-njD1LVZlDoUjyeiyaTdPTovS2YpFauc5_OaoumpQyiJBpwHkkLBc-0gFaIDMbEjUrQn2QlrVOgalJDpGtR096DS3YMSTncNCqfybmER9ts1NAinrmGxL6Cu48djCRcxlxD7E62IHV2ffRI9AGJH97e_M3YJDn8x6-JZu4cFtLtrWDb77OI5CRX7P_FYGj6NapyqSch-hvKKaBhQUUFWBk5A14hGo_l4nK3R3ycmC-K-EjBDq1A2FQwYi0lxhA4GWHaJi43ZFxVjiGGKA8dyB90k_pR2BkwR_O4MJsR47tg-A5phzqNcOGT8WE4qHBiyYv_jSDhuTJISucJBcUtQ64VjFnKDsXj-oJjlfKUDZGIglus_KKRZlcMhxTjqjycPConKlZJoyEbILSWk-ODgF13Jg2kzDBxC3lH7k4ITDC1TzhcC3q1DecoieeCTvE0eeJseuf7vhXEoOs-oOO9Qbp5Ra96m0LxLlnmXGPO0WuYZ3-MZ5eIZ3WKh4l2csV7eJqa8hxw7geBVoESYB7LLM3bLY-rKe7iqz9292jbl5B16yVMqGbg1L0PhvRSE93MMnhEI3kMSnMDwIjIayDsUkXe5oOP2vsOSuptnpIB3CQDvL_Z5X2HPu0U8zwp2Jwi8C3iomuPPjlNCbT4rkMdDQgUR_IDrnNTAuyN8pAxmEWUpkopcwDAzERPX-jORFDQluKCZyIx6CeTEqqkJNTUfSZl6FfGRKvl_OcOyCMS77AyC8Yslp1MR1W81jc0VdbyKLQcsBOlpraqakVS0L0mEI6kLkfORVH9soCeZgLoqMdiXiEcHo3ykhoUGegbjAwP9yb6-_sFjELqX-MjfCXxfz7HkQDIa7x-MDiaiff3J2KX_AlfSG4Y?type=png)](https://mermaid.live/edit#pako:eNqtWv9v00gW_1esICRWMm3zraXRHVJJW-jR0gqH7Wqvp8iJJ4lVx45spyUHSLBcoRRKy7FQWOAOWNjtrZYCq12-9Av8M3WS_hf3ZsYe24kd2rvkB5gv731m5s17b97HcCGS1yQUSUWKulgpcZkTMyoHv8OHuT-H_ZjEONJUbqiIVJMb0vMl2UR5s6oj7si5iiSaSPpqP1hUxqjm6AaGzqZP_XUmEgI9E_kblcc_Mg2yVCyt6ehPOb33OFYlQz7hKV0ryApyxO0uUZiqSaJqyvm9heXGzgbRcvXYxibGhkF5QpYkBc2LcMpxsYZ07ki_9fa7r3xL2cuVK2ZazJfwkm5PVosuBFl9SDVLulaR843tu9arB7vbD6xb99vwRmGzQs0wURng3E4LVv3-9d2td_W7y7s7j9sgBCSCJUGdNlpUd7d-bDy9Ul993Pj9eZvqNMqBHvzZogQjVGP3w23r2oK18bF5-7210r79tFYui6oEIHarBci6s7O79aJ-4-fms1vtG5-VFcXAGyeN1jMvXW5e3al_WG1-fmRtr1hLT5s7Oz4MpEqBNzoq-GzJZTRNMdpWP4tEaZR6jg7NLHMb68UP9afbsGTz9RacmbrS8Gjv1FTmm94zmolymjbbbkodfNnGm8dtD-DiI2trs37_Db3GNtURSTZtTQRNj-KrtcavP-1--K3-6HN9-Xlj-37z05029YmqYsoYA_TLuJ3FKNSGNz7uXV8J0RuXDXNY1kFLgVZWknV7t2vW9c3Gow1r596-zC1kmO-FmPqkjirMS4vQyRqkR9cj_kXdjQzocgXLcL3cVM0saWpAzKjSidoZsYwtVoBONlfLqtD1xIq1uuyBLEjBaGFHms7QsAg5D8yw48yjnO804DybqyHhhl3unK44HlfVlWxeU01IW0T33NnxjsH2tYzm01QeIOagl8WreyGsxWvWkzXbpP9-2Xh8syXt-Y45dXby67HhkbMCTWVzsgSJb1RUlJyYn-XSJVFuN77_6kdwWqcA9Mz1ldXdT4-alxcCFfEvI87JSg0UaIPmyjGaHkPsxgLlvAh68CdRar5-tfvxxhdURmUd5XVxXiEpwW4T9cbOnb1nf9SX7gaZmjlH6NFHRzLOyW1zf_Hkf5FVvH_8l3PfoBS2PAltUZ-VtHlVLmCDeXpE_1RmYry58ytkhv3t3zcQ5vrpjJvMwzJnVU2Xcc7Xqyp4HxElG9p7sGU9-1evtf1d_dXLkKQPmoIpmlWc923drEEGqAMT3cbSu_rlK-DAzdfPOznwyDcjacCZFMA1UL5qaroRaIpvjRIWAFG7hUXJemUxPykE6pwQmZLTZFrjslo9H6g1Jdg6U9o80oUSUhSf5jSkK22-fZf7uhvhNHssOfq2tSd1TZSIBE7r0M4auON5UAPeUfYWD6MCeY5Pj42P95TpnY7qkF7Komki3Vq4Wr_3pr68sa8cOpGewj6bnuLGID_BmCkH5HKYTysyzWjkIROQPod0NsyS6uNla-mZ9XC9sfGssXotCIc4K34D85UspGQMk82aMGhj3N-7um69f2ktvG--udr4fr0NAwPAOwwnxdkJOhztQW1HICAxwqVKBNNoPNyBN8Za3t8beWpy8jROFaegdAi9OzyJ74-sjzsc7dFsd_0Xa2md3l595Z9OHRESGAKJCwEcD0qRGkEOjoxhUS0iXasaNKLdLg1NA2tS-y2_3Xv4H7ueu_lTffEXMlzRZQ0vkeKSwfEgmiVnGzgqPF0G3Xz_2vr0D2vjhrWwXv_xMoR9IBQukaaQXpYNAzzJLvHcAQZnF8tPru49XA2Ba7kmn-nGJ09inqIVi3DvHSwHBsNC5LJsa9G-azJqrLWX1ue15sab1nrKey6GhDtD-TwyjBYweqrmxue9tQ0K-b_lkMy5Mezd2GyqqHDnxrgjGXTerIpKO9kB2aFKxWZt0KKE4sOWtfm9Ez8hRpweGz45ksEePy1LRWSGmLAkmmNqpYqDn7Xpad8t1q-8bn66ay0EO8OEUbSRceIAc4lFxNkjHgTr7b3Gi81AhFNQ9Gp67YQO6ZhGnG-A3uDta9bKb_U_Vpo_LwaCZEq4knMxfH1aZmx-bqzftBavBz3TnfxQGBGEsckzJIyJg0M1oMIpy60M2OWBRGyiqLs6VIXuZHf7h-brJ_VbV3Y_LgRRUcrn1IJcpBB224NAiXRIBu7kfYcPc0fhR7g8N6rgB9DP9mH6uEPlg6aApAfheVg7rVbVAJ5OAFw66Mp4KCIWoSW9O21TGjwFBb87jnkBHrSD3p1wqiYCRl7pL-zZ1OwKK2xLDkcNFWCsM1TCIZehAow-hkrYRNF7GI9tXHIXOO2SNa--Y0PGpNqnbLLUPuGhQb5Jz6KUWriztM8d7Tl6_GLB5jcXMZ1wRaDTOs_4gitlb4osgut4dwb3WgE8Bbv38F4_obV08BwrlT3rE3Eya1eygXNOwRo4SUtU323SkpLctVM_urNsyHVsXCgG-nZLtRcUyU5l506yIUegJSj8826VFrQD-l4HmtMtr9x5d4yIeKuhUCFvDRMq5K9NQsVYEdERyBFxhbwbpV43Jyoy_jh7sc2lvPv9kqx_263SQUmUnYAKi1XIJMG4AWJewPa7hPLDE8KkFiEmoR-Bg2ZYERE469YMgdP-9z9QxPe8B0q4j3DwBp33lc56nsl9fZgfhoQCm4AagBPMmgIF6v6_xINMWlTnRIPr5fAnI3gunTMYgIXIF3oOHmAldagvF43F-njD1LVZlDoUjyeiyaTdPTovS2YpFauc5_OaoumpQyiJBpwHkkLBc-0gFaIDMbEjUrQn2QlrVOgalJDpGtR096DS3YMSTncNCqfybmER9ts1NAinrmGxL6Cu48djCRcxlxD7E62IHV2ffRI9AGJH97e_M3YJDn8x6-JZu4cFtLtrWDb77OI5CRX7P_FYGj6NapyqSch-hvKKaBhQUUFWBk5A14hGo_l4nK3R3ycmC-K-EjBDq1A2FQwYi0lxhA4GWHaJi43ZFxVjiGGKA8dyB90k_pR2BkwR_O4MJsR47tg-A5phzqNcOGT8WE4qHBiyYv_jSDhuTJISucJBcUtQ64VjFnKDsXj-oJjlfKUDZGIglus_KKRZlcMhxTjqjycPConKlZJoyEbILSWk-ODgF13Jg2kzDBxC3lH7k4ITDC1TzhcC3q1DecoieeCTvE0eeJseuf7vhXEoOs-oOO9Qbp5Ra96m0LxLlnmXGPO0WuYZ3-MZ5eIZ3WKh4l2csV7eJqa8hxw7geBVoESYB7LLM3bLY-rKe7iqz9292jbl5B16yVMqGbg1L0PhvRSE93MMnhEI3kMSnMDwIjIayDsUkXe5oOP2vsOSuptnpIB3CQDvL_Z5X2HPu0U8zwp2Jwi8C3iomuPPjlNCbT4rkMdDQgUR_IDrnNTAuyN8pAxmEWUpkopcwDAzERPX-jORFDQluKCZyIx6CeTEqqkJNTUfSZl6FfGRKvl_OcOyCMS77AyC8Yslp1MR1W81jc0VdbyKLQcsBOlpraqakVS0L0mEI6kLkfORVH9soCeZgLoqMdiXiEcHo3ykhoUGegbjAwP9yb6-_sFjELqX-MjfCXxfz7HkQDIa7x-MDiaiff3J2KX_AlfSG4Y)

## 快速体验（CLI）

当前可用的体验入口是 `leonai`（TUI）：

- `leonai`：启动
- `leonai config`：配置 API key
- `leonai config show`：查看当前配置

## 截图

![LEON TUI Screenshot](./docs/assets/leon-tui.png)

## 最小基座

LEON 认为一个真正可工作的 Agent，至少应具备三类基础能力：

- Web
- Bash
- File System

## 架构方式

- Middleware-first：tool schema 注入、参数/路径校验（Fail Fast）、hooks/policy 拦截、结果整形、可观测性
- Profile-driven（推进中）：用 Profile 描述 Agent 的 `system_prompt` 与 tools/mcp/skill 开关

## 安装

```bash
# 使用 uv（推荐）
uv tool install leonai

# 或使用 pipx
pipx install leonai
```

## 配置

```bash
leonai config
```

配置会保存到 `~/.leon/config.env`。

## 核心特性

### Profile 配置系统

LEON 采用 Profile-driven 架构，通过 YAML/JSON/TOML 配置文件统一管理 Agent 能力：

```yaml
# ~/.leon/profile.yaml
agent:
  model: "claude-sonnet-4-5-20250929"
  workspace_root: null
  read_only: false
  enable_audit_log: true

tool:
  filesystem:
    enabled: true
    tools:
      read_file:
        enabled: true
        max_file_size: 10485760
      write_file: true
      edit_file: true
  search:
    enabled: true
    max_results: 50
  web:
    enabled: true
    tools:
      web_search:
        enabled: true
        tavily_api_key: ${TAVILY_API_KEY}
  command:
    enabled: true
    tools:
      run_command:
        enabled: true
        default_timeout: 120

mcp:
  enabled: true
  servers:
    filesystem:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]

skills:
  enabled: true
  paths:
    - ./skills
  skills:
    example-skill: true
```

**特性**：
- 支持 YAML/JSON/TOML 格式
- 环境变量展开 (`${VAR}`)
- Pydantic 强类型验证
- 工具级别的细粒度控制
- CLI 参数可覆盖 Profile 设置

### Skills 系统

渐进式能力披露机制，按需加载专业技能：

```
skills/
├── code-review/
│   └── SKILL.md
└── git-workflow/
    └── SKILL.md
```

**SKILL.md 格式**：
```markdown
---
name: code-review
description: 代码审查专家技能
---

# Code Review Skill

## Instructions
...
```

**特性**：
- Frontmatter 元数据解析
- 启用/禁用控制
- 多路径支持
- 动态加载（`load_skill` 工具）

### MCP (Model Context Protocol) 支持

集成外部 MCP 服务器，扩展 Agent 能力：

```yaml
mcp:
  servers:
    github:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_TOKEN: ${GITHUB_TOKEN}
      allowed_tools:
        - create_issue
        - list_issues
```

**特性**：
- 多服务器支持
- 工具白名单（`allowed_tools`）
- 环境变量配置
- 自动工具前缀处理（`mcp__server__tool`）

### TUI 界面

基于 Textual 的现代化终端界面：

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送消息 |
| `Shift+Enter` | 换行 |
| `Ctrl+↑/↓` | 浏览历史 |
| `Ctrl+Y` | 复制最后消息 |
| `Ctrl+E` | 导出对话 |
| `Ctrl+L` | 清空历史 |
| `Ctrl+T` | 切换对话 |
| `ESC ESC` | 显示历史浏览器 |

**特性**：
- 实时流式输出
- Markdown 渲染
- 工具调用可视化
- Thread 持久化与恢复
- 消息导出

### Middleware 架构

6 层中间件栈，统一处理工具注入、校验、拦截：

```
┌─────────────────────────────────────┐
│ 1. PromptCachingMiddleware (缓存)   │
│ 2. FileSystemMiddleware (文件)      │
│ 3. SearchMiddleware (搜索)          │
│ 4. WebMiddleware (Web)              │
│ 5. CommandMiddleware (命令)         │
│ 6. SkillsMiddleware (技能)          │
└─────────────────────────────────────┘
```

### 内置工具

| 类别 | 工具 | 说明 |
|------|------|------|
| **文件** | `read_file` | 读取文件（支持 PDF/PPTX/Notebook） |
| | `write_file` | 创建新文件 |
| | `edit_file` | 编辑文件（str_replace 模式） |
| | `multi_edit` | 批量编辑 |
| | `list_dir` | 列出目录 |
| **搜索** | `grep_search` | 内容搜索（ripgrep/Python） |
| | `find_by_name` | 文件名搜索（fd/Python） |
| **Web** | `web_search` | Web 搜索（Tavily/Exa/Firecrawl） |
| | `read_url_content` | 获取 URL 内容（Jina） |
| **命令** | `run_command` | 执行 Shell 命令 |
| | `command_status` | 查询命令状态 |
| **技能** | `load_skill` | 加载专业技能 |

### 安全机制

多层安全防护：

1. **命令拦截**：危险命令黑名单（`rm -rf`, `sudo` 等）
2. **路径安全**：强制绝对路径，Workspace 限制
3. **文件权限**：扩展名白名单，只读模式
4. **审计日志**：文件访问和命令执行记录

```yaml
agent:
  read_only: true                    # 只读模式
  allowed_extensions: [py, txt, md]  # 扩展名白名单
  block_dangerous_commands: true     # 拦截危险命令
  block_network_commands: true       # 拦截网络命令
  enable_audit_log: true             # 启用审计日志
```

### 多格式支持

| 格式 | 读取器 |
|------|--------|
| 文本 | TextReader |
| PDF | PDFReader (pymupdf) |
| PPTX | PPTXReader (python-pptx) |
| Notebook | NotebookReader |
| 二进制 | BinaryReader |

### 多搜索引擎

降级策略自动切换：

1. **Tavily**（主力）
2. **Exa**（备选）
3. **Firecrawl**（兜底）

### 多 Shell 支持

自动检测操作系统，选择合适的执行器：

- **macOS**: ZshExecutor
- **Linux**: BashExecutor
- **Windows**: PowerShellExecutor

## 路线

**已完成**：
- [x] Agent Profile：配置化、强类型校验、统一能力入口
- [x] TUI Resume：恢复 thread（仅 messages/thread）
- [x] MCP 集成：可配置加载、工具白名单
- [x] Skills 系统：渐进式能力披露

**进行中**：
- [ ] Hook 系统：工具调用前后的拦截与扩展
- [ ] Plugin 适配：第三方插件生态支持
- [ ] 评估系统：Agent 能力评测与基准测试
- [ ] 基于轨迹的自动优化：从执行轨迹学习，自动优化 Agent 框架
- [ ] Agent 协作与调度：多 Agent 协同工作与任务分配

## 许可证

MIT License
