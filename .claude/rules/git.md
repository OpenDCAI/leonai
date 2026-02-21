# Git 规范

## Commit 风格

小步快跑，每个 commit 单一职责。遵循 Conventional Commits：

- `feat`: 新功能 | `fix`: Bug 修复 | `refactor`: 重构 | `test`: 测试 | `docs`: 文档 | `chore`: 构建/依赖

❌ 避免：大而全的提交、混合多个功能、跳过测试
✅ 推荐：相关文件一起提交、每个 commit 可独立运行、message 清晰（动词开头、<50 字符）

## 推送规则

- ✅ Commit 可以随意提交（Claude 可自主 commit）
- ❌ Push 必须用户授权（Claude 不能主动 push）

**技术细节：**
- push 被拒时，优先 `git rebase origin/<branch>` 对齐远程，保持 fast-forward
- ❌ 避免 `git reset --hard origin/<branch>`：会丢弃本地未推送的 commit
- ❌ 避免 `git pull --rebase`：分叉历史下会逐个 replay 已存在的提交，大量冲突

**安全检查（破坏性操作前必须执行）：**
- `reset --hard` 前 → `git log HEAD --not --remotes` 确认本地无独有 commit
- PR 目标分支 → 默认 `dev`（master 只接受 dev 合入）
- push 前 → `git log origin/<branch>..HEAD` 确认要推送的内容符合预期

## Worktree 规范

新功能开发使用 worktree 隔离：

```bash
# 在项目内的 worktrees/ 文件夹创建 worktree
git worktree add worktrees/<feature> -b <feature>
cd worktrees/<feature>
```

规则：
- 统一使用项目内的 `worktrees/` 文件夹（不是同级目录 `../`）
- 确保 `worktrees/` 已加入 `.gitignore`
- 开发完成后用 `git worktree remove` 清理
