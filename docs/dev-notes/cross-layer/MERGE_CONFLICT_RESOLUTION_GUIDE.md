# sage_vllm → sage_llm 重命名导致的合并冲突解决方案

## 问题描述

在 `feat/unified-chat-canvas-rebased` 分支中，我们将 `sage_vllm` 重命名为 `sage_llm`（提交 f78318b6c）。
但是 `main-dev` 分支在此之后仍然更新了 `packages/sage-common/src/sage/common/components/sage_vllm/sageLLM` submodule。

当尝试将 `feat/unified-chat-canvas-rebased` 合并回 `main-dev` 时，会出现冲突：

```
CONFLICT (modify/delete): packages/sage-common/src/sage/common/components/sage_vllm/sageLLM
deleted in HEAD and modified in origin/main-dev.
```

## 冲突原因

- **我们的分支 (HEAD)**: 删除了 `sage_vllm/` 目录，创建了 `sage_llm/` 目录
- **main-dev**: 更新了 `sage_vllm/sageLLM` submodule 的 commit hash

Git 无法自动处理这种"删除 vs 修改"的冲突。

## 解决方案

### 方案 1: 推荐 - Rebase 策略 ✅

这是最干净的方案，保持线性历史：

```bash
# 1. 确保工作区干净
cd /home/shuhao/SAGE
git status
# 如有未提交的更改，先暂存或提交

# 2. 切换到最新的 main-dev
git fetch origin main-dev
git checkout main-dev
git pull origin main-dev

# 3. 创建临时备份分支（以防万一）
git checkout feat/unified-chat-canvas-rebased
git branch feat/unified-chat-canvas-rebased-backup

# 4. Rebase 到 main-dev
git rebase origin/main-dev

# 5. 解决冲突
# Git 会在遇到 sage_vllm 冲突时暂停，此时运行：
git rm packages/sage-common/src/sage/common/components/sage_vllm/sageLLM
git rebase --continue

# 6. 如果还有其他冲突，逐个解决后继续
# git add <resolved-files>
# git rebase --continue

# 7. Rebase 完成后，强制推送（因为改变了历史）
git push origin feat/unified-chat-canvas-rebased --force-with-lease
```

**优点**:
- 线性历史，干净整洁
- 所有提交都在 main-dev 之上
- 后续合并到 main-dev 会非常顺畅

**缺点**:
- 需要 force push（使用 --force-with-lease 更安全）
- 如果团队有人基于旧分支工作，需要他们重新 pull

### 方案 2: Merge 策略

保留完整的分支历史：

```bash
# 1. 确保工作区干净
cd /home/shuhao/SAGE
git checkout feat/unified-chat-canvas-rebased

# 2. 合并 main-dev
git merge origin/main-dev

# 3. 解决冲突
# Git 会提示：deleted by us: packages/sage-common/src/sage/common/components/sage_vllm/sageLLM
# 这是因为我们已经重命名，所以删除旧路径是正确的
git rm packages/sage-common/src/sage/common/components/sage_vllm/sageLLM

# 4. 确认新路径存在且正确
ls packages/sage-common/src/sage/common/components/sage_llm/sageLLM

# 5. 完成合并
git add -A
git commit -m "Merge main-dev: resolve sage_vllm→sage_llm rename conflict

The conflict was caused by main-dev updating sage_vllm/sageLLM submodule
while we renamed sage_vllm to sage_llm. Resolution: keep the rename,
remove old sage_vllm path."

# 6. 推送
git push origin feat/unified-chat-canvas-rebased
```

**优点**:
- 保留完整的分支历史
- 不需要 force push
- 团队成员可以正常 pull

**缺点**:
- 非线性历史，有 merge commit
- PR 看起来会有更多提交

### 方案 3: 交互式 Rebase（最精细）

如果想精细控制每个提交：

```bash
# 1. 找到共同祖先
git merge-base feat/unified-chat-canvas-rebased origin/main-dev
# 输出: a40cbd2d5e9fb9e1aaf5ff1abfe144c2fa312d1c

# 2. 交互式 rebase
git rebase -i origin/main-dev

# 3. 在编辑器中，可以：
#    - 重新排序提交
#    - 合并(squash)某些提交
#    - 编辑(edit)提交消息
#    - 删除(drop)不需要的提交

# 4. 对于 sage_vllm 冲突，按方案 1 处理
git rm packages/sage-common/src/sage/common/components/sage_vllm/sageLLM
git rebase --continue

# 5. 强制推送
git push origin feat/unified-chat-canvas-rebased --force-with-lease
```

## 推荐方案总结

**对于当前情况，推荐使用方案 1 (Rebase)**，原因：

1. **线性历史**: 你的分支本身就是从 main-dev rebased 而来，继续保持线性最合理
2. **干净的 PR**: 合并回 main-dev 时只会是 fast-forward merge
3. **易于 code review**: 审查者看到的是清晰的提交序列
4. **符合项目习惯**: 从分支名 `feat/unified-chat-canvas-rebased` 可见项目倾向 rebase

## 详细步骤（方案 1）

```bash
# Step 1: 保存当前工作
cd /home/shuhao/SAGE
git stash  # 如有未提交的更改

# Step 2: 创建备份
git branch feat/unified-chat-canvas-rebased-before-merge

# Step 3: 获取最新 main-dev
git fetch origin main-dev

# Step 4: Rebase
git rebase origin/main-dev

# Step 5: 解决冲突（Git 会自动暂停）
# 此时会看到：
# CONFLICT (modify/delete): packages/sage-common/src/sage/common/components/sage_vllm/sageLLM

# 删除旧路径（因为我们已重命名为 sage_llm）
git rm packages/sage-common/src/sage/common/components/sage_vllm/sageLLM

# 继续 rebase
git rebase --continue

# Step 6: 如果还有其他冲突，重复步骤 5

# Step 7: 验证结果
git log --oneline -10
git status

# Step 8: 推送（使用 --force-with-lease 更安全）
git push origin feat/unified-chat-canvas-rebased --force-with-lease

# Step 9: 恢复之前的工作
git stash pop  # 如有
```

## 验证合并成功

```bash
# 1. 检查目录结构
ls -la packages/sage-common/src/sage/common/components/
# 应该只有 sage_llm，没有 sage_vllm

# 2. 检查所有导入是否正确
grep -r "sage_vllm" packages/ --include="*.py" | grep -v ".pyc" | grep -v "__pycache__"
# 应该没有结果（除了可能的注释）

# 3. 检查 submodule 状态
git submodule status
# sage_llm/sageLLM 应该显示正确的 commit hash

# 4. 运行测试
sage-dev project test --quick
```

## 后续注意事项

1. **通知团队成员**: 如果使用了 force push，需要通知其他开发者
   ```bash
   # 其他开发者需要：
   git fetch origin
   git reset --hard origin/feat/unified-chat-canvas-rebased
   ```

2. **更新 PR**: 如果已有 PR，GitHub 会自动更新，但需要重新请求 review

3. **CI/CD**: 推送后检查 CI 是否通过，特别是：
   - 构建测试
   - 导入测试
   - Submodule 一致性检查

4. **文档更新**: 更新相关文档中的 `sage_vllm` 引用为 `sage_llm`

## 预防未来冲突

1. **及时同步**: 定期 rebase main-dev，避免分支分叉太久
2. **重命名沟通**: 大规模重命名前先在 main-dev 完成，或通知团队
3. **子模块管理**: 使用 `./manage.sh` 统一管理 submodule 更新

## 常见问题

### Q1: Rebase 过程中出现其他冲突怎么办？

```bash
# 查看冲突文件
git status

# 手动编辑解决冲突，然后：
git add <resolved-files>
git rebase --continue

# 如果想跳过某个提交：
git rebase --skip

# 如果想中止 rebase：
git rebase --abort
```

### Q2: Force push 会丢失代码吗？

使用 `--force-with-lease` 很安全，它会检查远程分支是否被他人更新：

```bash
git push origin feat/unified-chat-canvas-rebased --force-with-lease
# 如果有人推送了新提交，这个命令会失败，保护你不会覆盖别人的工作
```

### Q3: 如何验证 sage_llm 重命名完整？

```bash
# 搜索所有 Python 文件中的 sage_vllm
find packages -name "*.py" -type f -exec grep -l "sage_vllm" {} \; 2>/dev/null

# 搜索配置文件
find . -name "*.yaml" -o -name "*.yml" -o -name "*.toml" -exec grep -l "sage_vllm" {} \; 2>/dev/null

# 检查导入语句
grep -r "from sage.*sage_vllm" packages/ --include="*.py"
grep -r "import sage.*sage_vllm" packages/ --include="*.py"
```

## 参考资料

- Git Rebase 官方文档: https://git-scm.com/docs/git-rebase
- 处理冲突: https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging
- Submodule 管理: `docs/dev-notes/cross-layer/ci-cd/submodule-management.md`
