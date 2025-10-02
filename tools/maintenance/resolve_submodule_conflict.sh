#!/bin/bash

# 解决sage_db子模块冲突的脚本
# 使用主仓库的版本（保留我们的版本）

echo "=== 解决sage_db子模块冲突 ==="

# 1. 检查当前冲突状态
echo "检查当前git状态..."
git status

# 2. 对于子模块冲突，直接使用我们的版本（HEAD）
echo "使用我们的版本解决冲突..."
git checkout --ours packages/sage-middleware/src/sage/middleware/components/sage_db

# 3. 更新子模块到正确的commit
echo "更新子模块..."
git submodule update --init --recursive packages/sage-middleware/src/sage/middleware/components/sage_db

# 4. 添加解决后的文件
echo "添加解决后的子模块..."
git add packages/sage-middleware/src/sage/middleware/components/sage_db

# 5. 检查状态
echo "检查解决后的状态..."
git status

echo "=== 冲突解决完成 ==="
echo "现在可以运行 'git commit' 来完成合并"