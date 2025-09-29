# 解决sage_db子模块冲突指南

## 问题描述
ZeroJustMe的fork在提PR时，在`packages/sage-middleware/src/sage/middleware/components/sage_db`子模块位置出现冲突。

## 解决方案：保留主仓库版本

### 方法1：命令行解决（推荐）

当遇到子模块冲突时：

```bash
# 1. 查看冲突状态
git status

# 2. 使用主仓库的版本（我们的版本）
git checkout --ours packages/sage-middleware/src/sage/middleware/components/sage_db

# 3. 更新子模块到正确状态
git submodule update --init --recursive packages/sage-middleware/src/sage/middleware/components/sage_db

# 4. 标记冲突已解决
git add packages/sage-middleware/src/sage/middleware/components/sage_db

# 5. 完成合并
git commit
```

### 方法2：使用提供的脚本

```bash
# 运行自动解决脚本
./resolve_submodule_conflict.sh
```

### 方法3：重置子模块到主分支版本

```bash
# 确保在正确的分支
git checkout main-dev

# 获取最新的子模块状态
git submodule update --init --recursive

# 检查子模块状态
git submodule status

# 如果需要强制重置
cd packages/sage-middleware/src/sage/middleware/components/sage_db
git checkout stable
git pull origin stable
cd ../../../../../../../../..

# 提交子模块更新
git add packages/sage-middleware/src/sage/middleware/components/sage_db
git commit -m "fix: 更新sage_db子模块到稳定版本"
```

## 为什么选择保留主仓库版本？

1. **稳定性**：主仓库的子模块指向经过测试的稳定版本
2. **一致性**：确保所有开发者使用相同的子模块版本
3. **CI/CD**：避免构建环境不一致导致的问题
4. **依赖管理**：主仓库对子模块版本有严格的兼容性要求

## 预防措施

### 对于贡献者（如ZeroJustMe）：

1. **在开始开发前同步子模块**：
```bash
git submodule update --init --recursive
```

2. **避免直接修改子模块**：
- 不要在子模块目录内进行git操作
- 如需修改子模块，应该在对应的子模块仓库提PR

3. **提PR前检查子模块状态**：
```bash
git submodule status
```

### 对于维护者：

1. **定期更新子模块版本**：
```bash
git submodule foreach git pull origin stable
git add .
git commit -m "update: 更新所有子模块到最新稳定版本"
```

2. **在merge PR前检查子模块变更**：
```bash
git diff --submodule
```

## 注意事项

- 子模块冲突通常表示不同分支指向了子模块的不同commit
- 总是检查子模块的分支是否正确（应该是stable分支）
- 如果不确定，优先使用主仓库的子模块版本