# Git 规范

## Commit 风格

小步快跑，每个 commit 单一职责。遵循 Conventional Commits：

- `feat`: 新功能 | `fix`: Bug 修复 | `refactor`: 重构 | `test`: 测试 | `docs`: 文档 | `chore`: 构建/依赖

❌ 避免：大而全的提交、混合多个功能、跳过测试
✅ 推荐：相关文件一起提交、每个 commit 可独立运行、message 清晰（动词开头、<50 字符）

## PR 规范

- title/body 必须用英文
- 基于 commit 历史认真总结，不糊弄
- push 前清理 untracked 文件（截图、临时文件），避免 warning

## 推送规则

- ✅ Commit 可以随意提交（Claude 可自主 commit）
- ❌ Push 必须用户授权（Claude 不能主动 push）

**技术细节：**
- push 被拒时，优先 `git rebase origin/<branch>` 对齐远程，保持 fast-forward
- ❌ 避免 `git reset --hard origin/<branch>`：会丢弃本地未推送的 commit
- ❌ 避免 `git pull --rebase`：分叉历史下会逐个 replay 已存在的提交，大量冲突

**安全检查（破坏性操作前必须执行）：**
- `reset --hard` 前 → `git log HEAD --not --remotes` 确认本地无独有 commit
- PR 目标分支 → 默认 `main`
- push 前 → `git log origin/<branch>..HEAD` 确认要推送的内容符合预期

## Worktree 规范

新功能开发使用 worktree 隔离，存放在全局目录，避免与主仓库混淆：

```bash
# 在全局 ~/worktrees/ 目录创建
git worktree add ~/worktrees/<项目名>--<feature> -b <feature> origin/main
cd ~/worktrees/<项目名>--<feature>
```

规则：
- 统一使用 `~/worktrees/`，命名 `<项目名>--<目录名>`（目录名 = 分支名 `/` → `-`）
- 创建时自动分配端口对（写入 `git config --worktree`），避免多 worktree 端口冲突
- 开发完成后用 `git worktree remove` 清理
