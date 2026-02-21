
## osascript vs Task

| 场景 | 工具 | 说明 |
|------|------|------|
| 相约（找人聊） | osascript | 启动新终端，用户主导交互 |
| worktree 初始化 | osascript | 启动新终端，用户主导交互 |
| 干活（执行任务） | Task | 子代理执行，返回结果 |

❌ 干活时禁止用 osascript 启动 Agent,禁止任何子 agent使用此命令。

## 相约 vs 代办

| 说法 | 含义 | 工具 |
|------|------|------|
| "把 [WHO] 叫过来" | 他来我这儿，用户主导交互 | osascript |
| "去找 [WHO]" / "我想跟 [WHO] 聊" | 用户去他那儿，用户主导交互 | osascript |
| "你跟 [WHO] 聊一下" / "你去问问 [WHO]" | Claude 代办，获取信息后汇报 | Task |

### 相约（osascript）

用户想亲自交流 → 启动新终端，用户主导

流程：
1. 读取 `~/.claude/agents/<WHO>.md` 获取工位路径（在 description 里）
2. AppleScript 启动新终端，进入对应目录，启动 claude
3. 用 `--agent` 参数指定 agent，附带唤醒 prompt
4. 默认 `--model opus`（相约是主动交流，用最强模型）

唤醒 prompt 要求：
- 告诉他为什么被叫来（用户说了就转达，没说就说"用户有事找你"）
- ❌ 不要追问用户具体什么事
- ❌ 不要说"有什么需要帮忙的吗"这种反问

```bash
osascript -e 'tell app "Terminal" to do script "cd <目录> && claude --agent <WHO> --model opus \"<唤醒prompt>\""'
```

### 代办（Task）

用户让 Claude 去获取信息并汇报 → 用 Task 工具调用对应 agent

```
Task(subagent_type=<WHO>, prompt="<任务描述>")
```
