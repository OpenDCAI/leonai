# 创建 Worktree

基于最新 `origin/main` 创建隔离的 worktree 开发环境。

## 参数

`$ARGUMENTS` = 分支名（如 `feat/eval`、`yyh/fix-bug`）

## Step 0：定位主仓库

```bash
MAIN_REPO=$(git worktree list | head -1 | awk '{print $1}')
PROJECT_NAME=$(basename "$MAIN_REPO")
```

在主仓库或任意 worktree 下执行均可，自动找到主仓库根目录。

## Step 1：同步远端

```bash
git fetch origin
```

确保基于最新的 `origin/main` 创建，避免从过时的 base 分叉。

## Step 2：启用 worktreeConfig

```bash
git config extensions.worktreeConfig true
```

幂等操作，已启用不报错。启用后每个 worktree 可拥有独立的 `config.worktree` 配置。

## Step 3：创建 worktree

目录名规则：分支名中的 `/` 替换为 `-`（如 `feat/eval` → `feat-eval`）

路径规则：`~/worktrees/<项目名>--<目录名>`（如 `~/worktrees/leon--feat-eval`）

```bash
git worktree add "$HOME/worktrees/$PROJECT_NAME--<目录名>" -b $ARGUMENTS origin/main
```

- worktree 存放在 `~/worktrees/`，与主仓库完全隔离
- 确保 `~/worktrees/` 目录存在（`mkdir -p ~/worktrees`）

## Step 4：端口分配

为 worktree 分配独立的 backend + frontend 端口对，避免多 worktree 同时开发时端口冲突。

端口 8001/5173 保留给 main，worktree 从 offset=1 开始。

分配逻辑（**必须严格按以下脚本执行，不要自行简化，不要用 `&&` 把 while 和 for 串成一条命令**）：

```bash
# 用 git worktree list 获取所有 worktree 路径，逐个读取已声明端口
MAIN_REPO=$(git worktree list | head -1 | awk '{print $1}')
declared_ports=""
while read -r wt_path _rest; do
  [ "$wt_path" = "$MAIN_REPO" ] && continue
  bp=$(git -C "$wt_path" config --worktree --get worktree.ports.backend 2>/dev/null) || true
  fp=$(git -C "$wt_path" config --worktree --get worktree.ports.frontend 2>/dev/null) || true
  [ -n "$bp" ] && declared_ports="$declared_ports $bp"
  [ -n "$fp" ] && declared_ports="$declared_ports $fp"
  true  # 确保循环退出码为 0，避免 && 链断裂
done < <(git worktree list | tail -n +2)
echo "已声明端口: $declared_ports"

# 从 offset=1 开始找第一组未冲突的端口对
for offset in $(seq 1 20); do
  bp=$((8001 + offset))
  fp=$((5173 + offset))
  # 检查 1：是否已被其他 worktree 声明
  if echo "$declared_ports" | grep -qw "$bp" || echo "$declared_ports" | grep -qw "$fp"; then
    echo "跳过 $bp/$fp（已声明）"
    continue
  fi
  # 检查 2：系统层是否占用
  if lsof -i :"$bp" >/dev/null 2>&1 || lsof -i :"$fp" >/dev/null 2>&1; then
    echo "跳过 $bp/$fp（端口占用）"
    continue
  fi
  echo "分配: backend=$bp frontend=$fp"
  break
done
```

## Step 5：写入 worktree config

```bash
cd "$HOME/worktrees/$PROJECT_NAME--<目录名>"
git config --worktree worktree.ports.backend <backend_port>
git config --worktree worktree.ports.frontend <frontend_port>
git config --worktree worktree.description "<AI 生成的描述>"
git config --worktree worktree.created "$(date +%Y-%m-%d)"
git config --worktree worktree.project "$PROJECT_NAME"
```

description 由 AI 根据分支名和用户提供的上下文自动推断，简短描述这个分支的目的（中文，10-20 字）。

前后端代码会自动从 `git config --worktree` 读取端口，无需手动修改代码：
- `backend/web/main.py` → `_resolve_port()` 读取 `worktree.ports.backend`
- `frontend/app/vite.config.ts` → `getWorktreePort()` 读取 `worktree.ports.backend` 和 `worktree.ports.frontend`

## Step 6：链接本地配置

`.claude/` 已纳入 Git 管理，worktree checkout 后自动包含。
只需链接不在 Git 里的本地配置文件：

```bash
cd "$HOME/worktrees/$PROJECT_NAME--<目录名>"
ln -s "$MAIN_REPO/CLAUDE.local.md" CLAUDE.local.md 2>/dev/null
```

## Step 7：确认结果

输出：
- worktree 路径
- 分支名
- 分配的端口（backend / frontend）
- 自动生成的描述
- `CLAUDE.local.md` 符号链接状态

询问用户：是否在新 worktree 中打开新的 Claude 会话？

如果是，用 osascript 打开新终端并启动 claude（**必须将路径替换为实际计算出的完整绝对路径，不得使用变量或占位符**）：

```bash
osascript -e 'tell app "Terminal" to do script "cd \"/Users/apple/worktrees/<项目名>--<目录名>\" && claude"'
```

关键：`cd` 和 `claude` 必须写在 osascript 的 `do script` 字符串内部，不是写在外层 Bash 命令里。
