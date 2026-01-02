# LibAMM 迁移指南：从 Submodule 到 PyPI

## 📋 概述

本指南说明如何将 LibAMM 从 SAGE 仓库的 git submodule 迁移到独立的 PyPI 包。

### 目标架构

**迁移前**：

```
SAGE Repo
└── packages/sage-libs/
    └── src/sage/libs/
        └── libamm/ (git submodule → intellistream/LibAMM)
            ├── 源码
            └── 编译脚本
```

**迁移后**：

```
SAGE Repo
└── packages/sage-libs/
    └── pyproject.toml (依赖: isage-libamm>=0.1.0)

PyPI
├── isage-libs (自动安装 ↓)
└── isage-libamm (预编译 wheel)
```

## ✅ 前提条件检查清单

在执行迁移前，确保以下条件满足：

- [ ] `isage-libamm` 已成功编译
- [ ] `isage-libamm` 已上传到 PyPI
- [ ] 能够通过 `pip install isage-libamm` 安装
- [ ] 功能测试通过：`python -c "import PyAMM; print('OK')"`
- [ ] 已提交或暂存所有当前工作
- [ ] 了解 git submodule 的移除流程

## 🚀 迁移步骤

### 步骤 1：验证 isage-libamm 可用

```bash
# 检查 PyPI 上的版本
pip index versions isage-libamm

# 测试安装
python -m venv /tmp/test-libamm
source /tmp/test-libamm/bin/activate
pip install isage-libamm
python -c "import PyAMM; print('✅ LibAMM works')"
deactivate
rm -rf /tmp/test-libamm
```

### 步骤 2：执行自动移除脚本

```bash
cd /home/shuhao/SAGE

# 运行移除脚本
./tools/scripts/remove_libamm_submodule.sh

# 脚本会：
# 1. 验证 PyPI 上的 isage-libamm
# 2. 创建备份
# 3. 移除 git submodule 配置
# 4. 删除 libamm 目录
# 5. 清理 .git/modules
# 6. 显示待提交的更改
```

### 步骤 3：检查并提交更改

```bash
# 查看状态
git status

# 查看具体更改
git diff --cached

# 应该看到：
# - .gitmodules 被修改（移除 libamm section）
# - packages/sage-libs/src/sage/libs/libamm/ 被删除

# 提交更改
git commit -m "refactor: remove libamm submodule, use PyPI dependency

- Remove libamm submodule from sage-libs source tree
- LibAMM is now maintained independently at intellistream/LibAMM
- Users get libamm via PyPI: isage-libs → isage-libamm dependency
- Reduces SAGE repository complexity and size

Benefits:
- Clear separation of concerns
- Easier maintenance (no submodule sync issues)
- Faster clone/checkout (smaller repo)
- LibAMM can evolve independently

PyPI: https://pypi.org/project/isage-libamm/"
```

### 步骤 4：更新 sage-libs 版本

```bash
# 编辑版本号
vim packages/sage-libs/src/sage/libs/_version.py

# 修改为：
__version__ = "0.2.1"

# 提交版本更新
git add packages/sage-libs/src/sage/libs/_version.py
git commit -m "chore(sage-libs): bump version to 0.2.1

Changes in this release:
- LibAMM now automatically installed via PyPI dependency
- Removed libamm submodule for cleaner architecture
- Improved installation experience"
```

### 步骤 5：重新发布 sage-libs 到 PyPI

```bash
# 清理旧构建
rm -rf ~/.sage/dist/sage-libs

# 构建并上传
sage-dev package pypi build sage-libs --upload --no-dry-run

# 预期输出：
# ✓ 构建成功: isage_libs-0.2.1-py3-none-any.whl
# ✓ 已上传到 PyPI
```

### 步骤 6：验证完整安装流程

```bash
# 创建干净的测试环境
python -m venv /tmp/test-sage-libs-complete
source /tmp/test-sage-libs-complete/bin/activate

# 从 PyPI 安装 sage-libs
pip install isage-libs==0.2.1

# 验证 1：sage-libs 已安装
python -c "import sage.libs; print('✅ sage-libs OK')"

# 验证 2：libamm 自动安装
python -c "import PyAMM; print('✅ LibAMM auto-installed')"

# 验证 3：ANNS 算法可用
python -c "from sage.libs.anns import create; print('✅ ANNS OK')"

# 清理
deactivate
rm -rf /tmp/test-sage-libs-complete
```

## 📊 迁移前后对比

| 指标            | 迁移前                   | 迁移后                   |
| --------------- | ------------------------ | ------------------------ |
| **仓库大小**    | ~XXX MB                  | ~YYY MB (减少)           |
| **克隆时间**    | 较长（包含子模块）       | 较短                     |
| **构建复杂度**  | 高（处理 submodule）     | 低（纯 Python）          |
| **libamm 更新** | 需更新 submodule ref     | 自动（PyPI 版本）        |
| **依赖管理**    | Git + PyPI               | 仅 PyPI                  |
| **用户安装**    | `pip install isage-libs` | `pip install isage-libs` |

## 🔧 手动回滚（如果需要）

如果需要回滚到 submodule 模式：

```bash
# 1. 恢复备份
BACKUP_DIR="/tmp/sage-libamm-backup-YYYYMMDD-HHMMSS"  # 从脚本输出获取
cp -r "$BACKUP_DIR/libamm" packages/sage-libs/src/sage/libs/

# 2. 重新添加 submodule
git submodule add https://github.com/intellistream/LibAMM.git \
    packages/sage-libs/src/sage/libs/libamm

# 3. 回退 pyproject.toml 更改
git checkout HEAD~1 -- packages/sage-libs/pyproject.toml

# 4. 提交
git add .
git commit -m "Revert: restore libamm submodule"
```

## 📝 更新相关文档

迁移完成后，需要更新以下文档：

### 1. packages/sage-libs/README.md

- ✅ 已更新安装说明
- ✅ 已说明 LibAMM 自动安装

### 2. DEVELOPER.md

```markdown
## LibAMM 开发

LibAMM 现在作为独立项目维护：
- 仓库：https://github.com/intellistream/LibAMM
- PyPI：https://pypi.org/project/isage-libamm/

如需开发 LibAMM：
1. 克隆 LibAMM 独立仓库
2. 本地修改和测试
3. 发布到 PyPI
4. sage-libs 自动获取更新
```

### 3. .gitmodules

- ✅ 自动清理（脚本完成）

## 🎯 验证检查清单

迁移完成后，确认以下项目：

- [ ] `.gitmodules` 中无 libamm 条目
- [ ] `packages/sage-libs/src/sage/libs/libamm/` 不存在
- [ ] `.git/modules/` 中无 libamm 数据
- [ ] `pyproject.toml` 包含 `isage-libamm>=0.1.0` 依赖
- [ ] 版本号已更新为 0.2.1
- [ ] 已发布到 PyPI
- [ ] 能够从 PyPI 安装并使用
- [ ] CI/CD 测试通过
- [ ] 文档已更新

## ❓ 常见问题

### Q1: 移除后如何开发 libamm？

**A:** 克隆独立的 LibAMM 仓库：

```bash
git clone https://github.com/intellistream/LibAMM.git
cd LibAMM
# 开发和测试
pip install -e .
```

### Q2: 如何更新 libamm 版本？

**A:** LibAMM 维护者发布新版本到 PyPI 后，用户自动获取：

```bash
pip install --upgrade isage-libamm
```

### Q3: SAGE 开发者还能本地编译 libamm 吗？

**A:** 可以，但需要从独立仓库：

```bash
git clone https://github.com/intellistream/LibAMM.git
cd LibAMM
./buildCPUOnly.sh
pip install -e .
```

### Q4: 这会影响现有用户吗？

**A:** 不会。对于 PyPI 用户：

- 安装命令不变：`pip install isage-libs`
- LibAMM 自动安装
- 使用方式不变

## 📞 支持

如有问题，请：

1. 检查 PyPI 上的 isage-libamm 是否可用
1. 查看备份目录（脚本会显示路径）
1. 联系 SAGE 维护团队

## 📚 相关资源

- LibAMM 仓库：https://github.com/intellistream/LibAMM
- isage-libamm PyPI：https://pypi.org/project/isage-libamm/
- isage-libs PyPI：https://pypi.org/project/isage-libs/
- SAGE 文档：https://intellistream.github.io/SAGE-Pub/
