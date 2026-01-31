# LEON (Lane Runtime)

LEON 是一个面向企业级生产可用的 Agent Runtime：用于构建、运行与治理一组可长期运行的 Agent，并把它们当作可持续协作的 co-workers 来管理与调度。

LEON 以 LangChain Middleware 为核心架构：通过统一的 middleware 管线完成 tool 注入、运行时校验、安全拦截、上下文装载/卸载与可观测性。

[![](https://mermaid.ink/img/pako:eNqtWntz00gS_yoqU1SxVSIPO0_XHVXBSSBHQlLYbLb2cuUaW2NbFVlySXKCD6iC5QIhEBKOhcACd8DCbm5rSWBrl0ce8GUi2_kW1zMjjSRbMsmd_QfMo_s3Mz3dPf0TXIxkNQlH4pG8jkoFIXVyRhXgd_So8OewH5cYx5oqDOWxagpDerYgmzhrlnUsHDtfkpCJpa8OgsVkjHKGbWDoXOL0X2ciIdAzkb8xefKj0yDLxBKajv-U0TtPEFU65BOe0rWcrGBH3O5ShamKhFRTzu4vLNd2N6iWq8c3NjE2DMoTsiQpeB7BKcdRBevCsT7r7Xdf-ZaylyuWzATKFsiSbk9W8y4EXX1INQu6VpKztZ171uuHezsPrdsPmvBGYbPJimHiIsC5nQas6oMbe9vvqveW93afNEEkMQJLgjprNKjubf9Ye3a1uvqk9vuLJtVpnAE9-LNBCUaYxt6HO9b1BWvjY_3Oe2ulefsJrVhEqgQgdqsByLq7u7f9snrz5_rz280bn5UVxSAbp43GMy9dqV_brX5YrX9-bO2sWEvP6ru7PgysSoE3Opr02VJIaZpiNK1-DiNplHmODs00dxvr5Q_VZzuwZH1zG87MXGl4tHNqKvVN51nNxBlNm202pQ6-bOPNk7YHcPGxtb1VffCGXWOT6ogkm7YmhqZH8fVa7def9j78Vn38ubr8orbzoP7pbpP6RFkxZYIB-kXSThMUZsObH_dvrITojcuGOSzroKVAKy3Jur3bNevGVu3xhrV7_0DmTqa474WY-pSOS9xL89BJG7TH1qP-xdyNDuhyicgIncJUxSxoakDMqNLJyllUJBbLQSedqaRV6HpixVpd9kDmpGC0sCNNp1hYhJwHZvhx5nHGdxpwnq3VkHAjLndeVxyPK-tKOqupJqQtqnv-3HjLYPtaxvMJJg8Qc9BLk9W9ENbidevpmm3Sf7-qPbnVkPZ8x5w6N_n12PDIuSRLZXOyBIlvFClKBmVnhUQByc3G91_9CEnrDICdubqyuvfpcf3KQqAi-aXQnKxUQIE1WK4cY-kxxG48UC4g0IM_qVJ98_Xex5tfUBmVdZzV0bxCU4Ldpuq13bv7z_-oLt0LMjV3jtCjj46knJPb5v7iyf8iq2T_5C_nvkEpbHka2kiflbR5Vc4Rg3l6VP90amK8vvsrZIaD7d83EOb6iZSbzMMyZ1lNFEnO18sqeB8VpRvaf7htPf9Xp7XzXfX1q5CkD5pJE5llkvdt3bRBB5gDU93a0rvqlavgwPXNF60ceOSbkQTgTCbBNXC2bGq6EWiKb40CEQBRu0VE6XpFlJ1MBuqcRFzJaXKtcVktXwjUmkraOlPaPNaTBawoPs1pSFfafPMuD3Q3yTP8sRTY29ac1DUkUQmS1qGdNkjH86AGvKP8LR7GOfocnxkbH-8osjsd1SG9FJFpYt1auFa9_6a6vHGgHDqRmCI-m5gSxiA_wZgpB-RymE8oMsto9CFLYn0O63yYJ9Uny9bSc-vRem3jeW31ehAOdVbyBmZLaUjJBCadNmHQxniwf23dev_KWnhff3Ot9v16EwYBgHcYTkqyE3QE1oPajkJAYoRLlSimUXu0C2-MtXywN_L05OQZkipOQ-kQendkktwfXZ90BNZj2e7GL9bSOru96so_nToiJDCSNC6S4HhQilQocnBkDCM1j3WtbLCIdrssNA2iyey3_Hb_0X_seu7WT9XFX-hwSZc1skRc6A2OB2QWnG2QqPB0OXT9_ab16R_Wxk1rYb364xUI-0AoUiJNYb0oGwZ4kl3iuQMczi6Wn17bf7QaAtdwTT7TjU-eIjxFy-fh3ltYDgxGhOhl2dZifddkzFhrr6zPa_WNN431lPdcHIl0hrJZbBgNYOxU9Y3P-2sbDPJ_yyGp82PEu4nZVKQI58eEYyl8wSwjpZnsgOxQqWSzNmgxQvFh29r63omfECNOjw2fGkkRj5-WpTw2Q0xYQOaYWiqT4Odtdtp3i9Wrm_VP96yFYGeYMPI2MkkcYC6Ux4I94kGw3t6vvdwKRDgNRa-mV07qkI5ZxPkG2A3euW6t_Fb9Y6X-82IgSKpAKjkXw9dnZcbW59r6LWvxRtAz3coPkyPJ5NjkWRrG1MGhGlDhlMVGBuzyQCo2kdddHabCdrK380N982n19tW9jwtBVJTxOTUn5xmE3fYgMCIdkoFbed_Ro8Jx-FEuL4wq5AH0s32YPuFQ-aApIOlBeB7WzqpVNYCnUwCXDroyHopIRFhJ707blIZMQcHvjhNeQAbtoHcnnKqJgtFX-gt7NjW7wgrbksNRQwU46wyVcMhlqACnj6ESNlH0HsZjG5fcBU67ZM2r79iQM6nmKZssNU94aJBv0rMooxbuLOsLxzuOn7iUs_nNJUInXBHoNM5zvuBK2Zuii5A63p0hvUYAT8HuPbzXT1gtHTzHS2XP-lScztqVbOCcU7AGTrIS1XebrKSkd-3Uj-4sH3IdmxSKgb7dUO0FRbJT2bmTfMgRaAgK_7xbpQXtgL3XgeZ0yyt33h2jIt5qKFTIW8OECvlrk1AxXkS0BHJEXCHvRpnXzSFFJh9nLzW5lHe_X5L1b7tROiiJ8hMwYVSGTBKMGyDmBWy-Syg_PCFMaxFqEvYROGiGFxGBs27NEDjtf_8DRXzPe6CE-wgHb9B5X9ms55k80If5YUgosAmoAYSkWVGgQD34l3iQSSB1DhlCp0A-GcFz6ZzBACxMv9AL8AAr8SNdme5otEs0TF2bxfEjsVhPd2-v3T0-L0tmIR4tXRCzmqLp8SO4F_c7DySDgufaQcp190dRS6Tujt5WWKPJtkElU22Dmm4fVKJ9UMkzbYMiqbxdWJT9tg0NwqltWPwLqOv4sWiPi5jpQX09jYgtXZ9_Ej0EYkv3t78ztgmOfDFr41nbhwW0u21YNvts4zkpFfs_8XgaPoMrgqpJ2H6GsgoyDKioICsDJ2BrdHd3Z2MxvkZfF-rNoQMlYI5WYmwqGDAalWIYHw6w6BIXG7OrG0Uxx0T9A5nDbpJ8SjsLpgh-dwZ7UCwzcMCA5pjzOBMOGRvISLlDQ5bsfxwJx41KUk8md1jcAtR64Zi5zGA0lj0sZjFbagHZ0x_N9B0W0izL4ZAohvtivYeFxMVSARmyEXJLPVJscPCLruTBtBkGCSHvqP1JwQmGhinnC4Ho1qEiY5Ei8EnRJg-iTY9c__fCOBRd5FRcdCi3yKm1aFNo0SXLokuMRVYti5zviZxyiZxu8VDxLs5Zr2gTU9FDjp1A8CowIiwC2RU5uxUJdRU9XNXn7l5tm3KKDr0UGZUM3JqXoYheCiL6OYbICYToIQlOYHgROQ0UHYooulzQcXvfYWndLXJSILoEQPQX-6KvsBfdIl7kBbsTBN4FPFTN8WfHKaE2n03Sx0PCOQR-ILROauDdETFSBLMgWYrEIxcJzEzEJLX-TCQOTQkuaCYyo14GOVQ2tWRFzUbipl7GYqRM_1_OsIyAeBedQTB-vuB0Skj9VtP4XF4nq9hywEKwntDKqhmJRweobCR-MXIhEh_s7ugiv1h3T29_V89gtxipROL9vR0D0Vg0NtA3MNA32Nvfe1mM_J2Cd3UM9PdSDZjq6RocjF3-LyTtGyU?type=png)](https://mermaid.live/edit#pako:eNqtWntz00gS_yoqU1SxVSIPO0_XHVXBSSBHQlLYbLb2cuUaW2NbFVlySXKCD6iC5QIhEBKOhcACd8DCbm5rSWBrl0ce8GUi2_kW1zMjjSRbMsmd_QfMo_s3Mz3dPf0TXIxkNQlH4pG8jkoFIXVyRhXgd_So8OewH5cYx5oqDOWxagpDerYgmzhrlnUsHDtfkpCJpa8OgsVkjHKGbWDoXOL0X2ciIdAzkb8xefKj0yDLxBKajv-U0TtPEFU65BOe0rWcrGBH3O5ShamKhFRTzu4vLNd2N6iWq8c3NjE2DMoTsiQpeB7BKcdRBevCsT7r7Xdf-ZaylyuWzATKFsiSbk9W8y4EXX1INQu6VpKztZ171uuHezsPrdsPmvBGYbPJimHiIsC5nQas6oMbe9vvqveW93afNEEkMQJLgjprNKjubf9Ye3a1uvqk9vuLJtVpnAE9-LNBCUaYxt6HO9b1BWvjY_3Oe2ulefsJrVhEqgQgdqsByLq7u7f9snrz5_rz280bn5UVxSAbp43GMy9dqV_brX5YrX9-bO2sWEvP6ru7PgysSoE3Opr02VJIaZpiNK1-DiNplHmODs00dxvr5Q_VZzuwZH1zG87MXGl4tHNqKvVN51nNxBlNm202pQ6-bOPNk7YHcPGxtb1VffCGXWOT6ogkm7YmhqZH8fVa7def9j78Vn38ubr8orbzoP7pbpP6RFkxZYIB-kXSThMUZsObH_dvrITojcuGOSzroKVAKy3Jur3bNevGVu3xhrV7_0DmTqa474WY-pSOS9xL89BJG7TH1qP-xdyNDuhyicgIncJUxSxoakDMqNLJyllUJBbLQSedqaRV6HpixVpd9kDmpGC0sCNNp1hYhJwHZvhx5nHGdxpwnq3VkHAjLndeVxyPK-tKOqupJqQtqnv-3HjLYPtaxvMJJg8Qc9BLk9W9ENbidevpmm3Sf7-qPbnVkPZ8x5w6N_n12PDIuSRLZXOyBIlvFClKBmVnhUQByc3G91_9CEnrDICdubqyuvfpcf3KQqAi-aXQnKxUQIE1WK4cY-kxxG48UC4g0IM_qVJ98_Xex5tfUBmVdZzV0bxCU4Ldpuq13bv7z_-oLt0LMjV3jtCjj46knJPb5v7iyf8iq2T_5C_nvkEpbHka2kiflbR5Vc4Rg3l6VP90amK8vvsrZIaD7d83EOb6iZSbzMMyZ1lNFEnO18sqeB8VpRvaf7htPf9Xp7XzXfX1q5CkD5pJE5llkvdt3bRBB5gDU93a0rvqlavgwPXNF60ceOSbkQTgTCbBNXC2bGq6EWiKb40CEQBRu0VE6XpFlJ1MBuqcRFzJaXKtcVktXwjUmkraOlPaPNaTBawoPs1pSFfafPMuD3Q3yTP8sRTY29ac1DUkUQmS1qGdNkjH86AGvKP8LR7GOfocnxkbH-8osjsd1SG9FJFpYt1auFa9_6a6vHGgHDqRmCI-m5gSxiA_wZgpB-RymE8oMsto9CFLYn0O63yYJ9Uny9bSc-vRem3jeW31ehAOdVbyBmZLaUjJBCadNmHQxniwf23dev_KWnhff3Ot9v16EwYBgHcYTkqyE3QE1oPajkJAYoRLlSimUXu0C2-MtXywN_L05OQZkipOQ-kQendkktwfXZ90BNZj2e7GL9bSOru96so_nToiJDCSNC6S4HhQilQocnBkDCM1j3WtbLCIdrssNA2iyey3_Hb_0X_seu7WT9XFX-hwSZc1skRc6A2OB2QWnG2QqPB0OXT9_ab16R_Wxk1rYb364xUI-0AoUiJNYb0oGwZ4kl3iuQMczi6Wn17bf7QaAtdwTT7TjU-eIjxFy-fh3ltYDgxGhOhl2dZifddkzFhrr6zPa_WNN431lPdcHIl0hrJZbBgNYOxU9Y3P-2sbDPJ_yyGp82PEu4nZVKQI58eEYyl8wSwjpZnsgOxQqWSzNmgxQvFh29r63omfECNOjw2fGkkRj5-WpTw2Q0xYQOaYWiqT4Odtdtp3i9Wrm_VP96yFYGeYMPI2MkkcYC6Ux4I94kGw3t6vvdwKRDgNRa-mV07qkI5ZxPkG2A3euW6t_Fb9Y6X-82IgSKpAKjkXw9dnZcbW59r6LWvxRtAz3coPkyPJ5NjkWRrG1MGhGlDhlMVGBuzyQCo2kdddHabCdrK380N982n19tW9jwtBVJTxOTUn5xmE3fYgMCIdkoFbed_Ro8Jx-FEuL4wq5AH0s32YPuFQ-aApIOlBeB7WzqpVNYCnUwCXDroyHopIRFhJ707blIZMQcHvjhNeQAbtoHcnnKqJgtFX-gt7NjW7wgrbksNRQwU46wyVcMhlqACnj6ESNlH0HsZjG5fcBU67ZM2r79iQM6nmKZssNU94aJBv0rMooxbuLOsLxzuOn7iUs_nNJUInXBHoNM5zvuBK2Zuii5A63p0hvUYAT8HuPbzXT1gtHTzHS2XP-lScztqVbOCcU7AGTrIS1XebrKSkd-3Uj-4sH3IdmxSKgb7dUO0FRbJT2bmTfMgRaAgK_7xbpQXtgL3XgeZ0yyt33h2jIt5qKFTIW8OECvlrk1AxXkS0BHJEXCHvRpnXzSFFJh9nLzW5lHe_X5L1b7tROiiJ8hMwYVSGTBKMGyDmBWy-Syg_PCFMaxFqEvYROGiGFxGBs27NEDjtf_8DRXzPe6CE-wgHb9B5X9ms55k80If5YUgosAmoAYSkWVGgQD34l3iQSSB1DhlCp0A-GcFz6ZzBACxMv9AL8AAr8SNdme5otEs0TF2bxfEjsVhPd2-v3T0-L0tmIR4tXRCzmqLp8SO4F_c7DySDgufaQcp190dRS6Tujt5WWKPJtkElU22Dmm4fVKJ9UMkzbYMiqbxdWJT9tg0NwqltWPwLqOv4sWiPi5jpQX09jYgtXZ9_Ej0EYkv3t78ztgmOfDFr41nbhwW0u21YNvts4zkpFfs_8XgaPoMrgqpJ2H6GsgoyDKioICsDJ2BrdHd3Z2MxvkZfF-rNoQMlYI5WYmwqGDAalWIYHw6w6BIXG7OrG0Uxx0T9A5nDbpJ8SjsLpgh-dwZ7UCwzcMCA5pjzOBMOGRvISLlDQ5bsfxwJx41KUk8md1jcAtR64Zi5zGA0lj0sZjFbagHZ0x_N9B0W0izL4ZAohvtivYeFxMVSARmyEXJLPVJscPCLruTBtBkGCSHvqP1JwQmGhinnC4Ho1qEiY5Ei8EnRJg-iTY9c__fCOBRd5FRcdCi3yKm1aFNo0SXLokuMRVYti5zviZxyiZxu8VDxLs5Zr2gTU9FDjp1A8CowIiwC2RU5uxUJdRU9XNXn7l5tm3KKDr0UGZUM3JqXoYheCiL6OYbICYToIQlOYHgROQ0UHYooulzQcXvfYWndLXJSILoEQPQX-6KvsBfdIl7kBbsTBN4FPFTN8WfHKaE2n03Sx0PCOQR-ILROauDdETFSBLMgWYrEIxcJzEzEJLX-TCQOTQkuaCYyo14GOVQ2tWRFzUbipl7GYqRM_1_OsIyAeBedQTB-vuB0Skj9VtP4XF4nq9hywEKwntDKqhmJRweobCR-MXIhEh_s7ugiv1h3T29_V89gtxipROL9vR0D0Vg0NtA3MNA32Nvfe1mM_J2Cd3UM9PdSDZjq6RocjF3-LyTtGyU)

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
