# 移除 Worktree

清理并移除指定的 worktree。

## 参数

`$ARGUMENTS` = 分支名或目录名（如 `feat/eval`、`feat-eval`）。可省略，自动识别。

## Step 0：确定目标

优先级：命令参数 → 当前所在 worktree → 列出所有 worktree 询问用户

```bash
MAIN_REPO=$(git worktree list | head -1 | awk '{print $1}')
```

- 当前目录是某个 worktree → 默认操作当前 worktree，确认后执行
- 当前目录是主仓库且无参数 → 列出所有 worktree，询问移除哪个
- 提供了参数 → 匹配分支名或目录名

## Step 1：检查未提交改动

```bash
git -C <worktree路径> status --short
```

有未提交改动 → 列出改动内容，询问用户：**继续移除（改动会丢失）？还是先处理？**

## Step 2：清理 untracked 文件

先移除已知的 symlink（`CLAUDE.local.md` 由 `wtnew` 创建，不在 Git 里）：

```bash
TARGET="$MAIN_REPO/worktrees/<目录名>/CLAUDE.local.md"
[ -L "$TARGET" ] && rm "$TARGET" || echo "跳过：$TARGET 不是符号链接，不删除"
```

**必须用 `[ -L ]` 确认是 symlink 再删**，绝不对普通文件执行 `rm`，防止误删原始文件。

## Step 3：移除 worktree

```bash
git worktree remove "$MAIN_REPO/worktrees/<目录名>"
```

如果仍然失败（`.venv`、`__pycache__` 等其他 untracked 文件残留）：

```bash
rm -rf "$MAIN_REPO/worktrees/<目录名>"
git worktree prune
```

## Step 4：询问是否删除本地分支

先 fetch 远程 main，确保合并判断基于最新状态：

```bash
git fetch origin main
git branch -d <分支名>   # 基于最新 origin/main 判断是否已合并
```

如果 `-d` 报"未合并"：先检查远程 main 是否包含该分支内容（可能是 rebase merge 导致 hash 不同）：

```bash
git log --oneline origin/main | grep -i <关键词>
```

- 远程已合并 → 安全删除 `git branch -D <分支名>`
- 远程未合并 → 告知用户，确认后再 `-D` 强删
- 不删除远程分支，除非用户明确要求
