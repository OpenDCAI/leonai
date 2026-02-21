# 同步 Worktree 配置

将主仓库的 `.claude` 配置链接到当前 worktree。

## 使用场景

- worktree 中新开的 Claude 会话发现没有加载项目规则
- worktree 创建时忘了链接配置

## Step 0：确定位置

```bash
MAIN_REPO=$(git worktree list | head -1 | awk '{print $1}')
CWD=$(pwd)
```

- `CWD == MAIN_REPO` → 提示"你在主仓库，不需要 sync"，退出
- `CWD` 在某个 worktree 下 → 继续

## Step 1：链接配置

```bash
ln -sf "$MAIN_REPO/.claude" .claude
ln -sf "$MAIN_REPO/CLAUDE.local.md" CLAUDE.local.md 2>/dev/null
```

## Step 2：验证

确认符号链接存在且指向正确目标，输出结果：

```
✅ 已同步：
  .claude → /path/to/main/.claude
  CLAUDE.local.md → /path/to/main/CLAUDE.local.md
```

链接已存在且正确 → 提示"已是最新，无需重复同步"。
