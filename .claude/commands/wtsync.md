# 同步 Worktree 本地配置

将主仓库的 `CLAUDE.local.md` 链接到当前 worktree。

> `.claude/` 已纳入 Git 管理，worktree checkout 后自动包含，无需手动处理。

## 使用场景

- worktree 中找不到 `CLAUDE.local.md`（本地配置不在 Git 里，不会随 checkout 复制）

## Step 0：确定位置

```bash
MAIN_REPO=$(git worktree list | head -1 | awk '{print $1}')
CWD=$(pwd)
```

- `CWD == MAIN_REPO` → 提示"你在主仓库，不需要 sync"，退出
- `CWD` 在某个 worktree 下 → 继续（无论是 `~/worktrees/` 还是旧路径 `$MAIN_REPO/worktrees/`）

## Step 1：链接本地配置

```bash
TARGET="CLAUDE.local.md"
if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
  echo "错误：$TARGET 是普通文件，不覆盖，请手动确认后再操作"
  exit 1
fi
ln -sf "$MAIN_REPO/CLAUDE.local.md" "$TARGET"
```

**若目标已存在且不是 symlink（即普通文件），直接报错退出**，绝不强制覆盖。

## Step 2：验证

确认符号链接存在且指向正确目标，输出结果：

```
✅ 已同步：
  CLAUDE.local.md → /path/to/main/CLAUDE.local.md
```

链接已存在且正确 → 提示"已是最新，无需重复同步"。
