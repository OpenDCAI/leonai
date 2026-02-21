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

## Step 2：移除 worktree

```bash
git worktree remove "$MAIN_REPO/worktrees/<目录名>"
```

如果失败（`.venv`、`__pycache__` 等 untracked 文件残留）：

```bash
rm -rf "$MAIN_REPO/worktrees/<目录名>"
git worktree prune
```

## Step 3：询问是否删除本地分支

```bash
git branch -d <分支名>   # 已合并分支
git branch -D <分支名>   # 未合并分支（需用户确认）
```

- 不删除远程分支，除非用户明确要求
- 未合并分支用 `-D` 强删前需额外确认
