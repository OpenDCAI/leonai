# 创建 Worktree

基于最新 `origin/main` 创建隔离的 worktree 开发环境。

## 参数

`$ARGUMENTS` = 分支名（如 `feat/eval`、`yyh/fix-bug`）

## Step 0：定位主仓库

```bash
MAIN_REPO=$(git worktree list | head -1 | awk '{print $1}')
```

在主仓库或任意 worktree 下执行均可，自动找到主仓库根目录。

## Step 1：同步远端

```bash
git fetch origin
```

确保基于最新的 `origin/main` 创建，避免从过时的 base 分叉。

## Step 2：创建 worktree

目录名规则：分支名中的 `/` 替换为 `-`（如 `feat/eval` → `feat-eval`）

```bash
git worktree add "$MAIN_REPO/worktrees/<目录名>" -b $ARGUMENTS origin/main
```

- `worktrees/` 统一放在主仓库内
- 必须确认 `worktrees/` 在 `.gitignore` 中，不在则自动添加

## Step 3：链接本地配置

`.claude/` 已纳入 Git 管理，worktree checkout 后自动包含。  
只需链接不在 Git 里的本地配置文件：

```bash
cd "$MAIN_REPO/worktrees/<目录名>"
ln -s "$MAIN_REPO/CLAUDE.local.md" CLAUDE.local.md 2>/dev/null
```

## Step 4：确认结果

输出：
- worktree 路径
- 分支名
- `CLAUDE.local.md` 符号链接状态

询问用户：是否在新 worktree 中打开新的 Claude 会话？

如果是，用 osascript 打开新终端并启动 claude（**必须将路径替换为实际计算出的完整绝对路径，不得使用变量或占位符**）：

```bash
osascript -e 'tell app "Terminal" to do script "cd \"/actual/absolute/path/to/worktrees/<目录名>\" && claude"'
```

关键：`cd` 和 `claude` 必须写在 osascript 的 `do script` 字符串内部，不是写在外层 Bash 命令里。
