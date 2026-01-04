# LibAMM 迁移 - 快速参考

> **⚠️ DEPRECATED**: The `sage-dev package pypi` command has been removed. Please use the standalone
> [sage-pypi-publisher](https://github.com/intellistream/sage-pypi-publisher) tool instead.
>
> **Migration**:
>
> ```bash
> git clone https://github.com/intellistream/sage-pypi-publisher.git
> cd sage-pypi-publisher
> ./publish.sh <package-name> --auto-bump patch
> ```

## 🎯 一句话总结

将 libamm 从 SAGE 的 git submodule 迁移到独立的 PyPI 包，通过依赖关系自动安装。

## ✅ 前提条件

```bash
# 1. 确认 isage-libamm 在 PyPI 上可用
pip index versions isage-libamm

# 2. 测试安装
pip install isage-libamm
python -c "import PyAMM; print('OK')"
```

## 🚀 执行迁移（3 步）

### 步骤 1：运行自动脚本

```bash
cd /home/shuhao/SAGE
./tools/scripts/remove_libamm_submodule.sh
```

### 步骤 2：提交更改

```bash
git status
git commit -m "refactor: remove libamm submodule, use PyPI dependency"
```

### 步骤 3：发布新版本

```bash
# 编辑版本号 → 0.2.1
vim packages/sage-libs/src/sage/libs/_version.py

# 清理并重新构建
rm -rf ~/.sage/dist/sage-libs
sage-dev package pypi build sage-libs --upload --no-dry-run
```

## 🔍 验证

```bash
# 创建干净环境测试
python -m venv /tmp/test
source /tmp/test/bin/activate
pip install isage-libs==0.2.1
python -c "import PyAMM; print('✅ Success')"
deactivate && rm -rf /tmp/test
```

## 📂 文件位置

- **自动脚本**：`tools/scripts/remove_libamm_submodule.sh`
- **详细指南**：`docs-public/docs_src/dev-notes/cross-layer/libamm-migration-guide.md`
- **备份位置**：`/tmp/sage-libamm-backup-<timestamp>/`（脚本会显示）

## ⏪ 快速回滚

```bash
git revert HEAD  # 回退提交
# 或从备份恢复（见脚本输出的备份路径）
```

## 📞 问题排查

1. **PyPI 找不到 isage-libamm** → 先上传 libamm 到 PyPI
1. **脚本失败** → 检查 git 状态，手动执行脚本中的命令
1. **安装失败** → 检查 pyproject.toml 依赖配置

## 🎓 核心原理

```
用户安装：pip install isage-libs
         ↓
    自动安装：isage-libamm (预编译 wheel)
         ↓
    可用：import PyAMM
```

## 📊 效果

- ✅ SAGE 仓库更小、更快
- ✅ 无需管理 submodule
- ✅ libamm 独立迭代
- ✅ 用户体验不变
