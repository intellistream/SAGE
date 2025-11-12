**Date**: 2025-11-12
**Author**: shuhao
**Summary**: Enhancement of CI import tests to comprehensively check package imports and address user concerns about undetected import issues.

# CI 导入测试增强

## 问题背景

用户提出问题：
> 我有一个CI/CD在检查是否有错误的从pip安装依赖的workflow "PyPI Installation Test"，
> 为什么没有检查出benchmark和data这里的导入问题？

## 问题分析

### 根本原因

CI workflow (`pip-installation-test.yml`) 中的验证代码**不够全面**，导致一些包的导入错误被忽略：

#### 原有验证逻辑的问题：

1. **Core 模式验证**：
   ```bash
   python -c "from sage.kernel import LocalEnvironment; print('✅ LocalEnvironment 可用')"
   python -c "from sage.middleware.operators.rag.pipeline import RAGPipeline; print('✅ RAGPipeline 可用')"
   ```
   - ✅ 验证了基础功能
   - ❌ 没有验证任何 L5 应用层包

2. **Standard 模式验证**：
   ```bash
   if [ -d "packages/sage-apps" ]; then
     python -c "import sage.apps; print('✅ sage.apps 可用')" 2>/dev/null || echo "ℹ️  sage.apps 可选"
   fi
   ```
   - ❌ 使用 `2>/dev/null || echo "可选"` 导致导入失败被静默忽略
   - ❌ **完全没有验证 `sage.benchmark` 或 `sage.data`**

3. **Full/Dev 模式验证**：
   - ❌ 只验证了 `sage.studio`、`sage.tools`、`pytest`
   - ❌ **同样没有验证 `sage.benchmark` 或 `sage.data`**

### 为什么没检测到问题？

虽然 `packages/sage-benchmark` 被安装了，但：
- CI 从未执行过 `import sage.benchmark`
- CI 从未执行过 `from sage.data import ...`
- 导入错误完全没有被触发

## 修复方案

### 增强验证逻辑

#### 1. Local Wheels 安装测试

**修改前**：
```bash
# 验证核心模块
python -c "from sage.common import config; print('✅ sage.common 可用')"
python -c "from sage.kernel import LocalEnvironment; print('✅ sage.kernel 可用')"

# 验证 CLI（如果包含）
if [ "${{ matrix.install-mode }}" != "core" ]; then
  if command -v sage >/dev/null 2>&1; then
    sage --version && echo "✅ sage CLI 可用"
  fi
fi
```

**修改后**：
```bash
# 验证核心模块
python -c "from sage.common import config; print('✅ sage.common 可用')"
python -c "from sage.kernel import LocalEnvironment; print('✅ sage.kernel 可用')"

# 根据安装模式验证相应的包
case "${{ matrix.install-mode }}" in
  standard|full|dev)
    # 验证 CLI
    if command -v sage >/dev/null 2>&1; then
      sage --version && echo "✅ sage CLI 可用"
    fi

    # 验证 sage-benchmark（必须验证，不能跳过）
    if pip show isage-benchmark >/dev/null 2>&1; then
      python -c "import sage.benchmark; print('✅ sage.benchmark 可用')" || {
        echo "❌ sage.benchmark 导入失败"
        exit 1
      }
      # 验证 sage.data 子包
      python -c "from sage.data import load_qa_dataset; print('✅ sage.data 可用')" || {
        echo "❌ sage.data 导入失败"
        exit 1
      }
    fi

    # 验证 sage-apps（如果已安装）
    if pip show isage-apps >/dev/null 2>&1; then
      python -c "import sage.apps; print('✅ sage.apps 可用')" || {
        echo "❌ sage.apps 导入失败"
        exit 1
      }
    fi
    ;;
esac
```

#### 2. Source 安装测试

为每个安装模式添加明确的包导入验证：

**Standard 模式**：
```bash
# 验证 sage-benchmark（必须验证）
if pip show isage-benchmark >/dev/null 2>&1; then
  python -c "import sage.benchmark; print('✅ sage.benchmark 可用')" || {
    echo "❌ sage.benchmark 导入失败"
    exit 1
  }
  # 验证 sage.data 子包
  python -c "from sage.data import load_qa_dataset; print('✅ sage.data 可用')" || {
    echo "❌ sage.data 导入失败"
    exit 1
  }
fi
```

**Dev 模式**：
```bash
# 验证 sage-benchmark（必须存在）
python -c "import sage.benchmark; print('✅ sage.benchmark 可用')" || {
  echo "❌ sage.benchmark 导入失败"
  exit 1
}
python -c "from sage.data import load_qa_dataset; print('✅ sage.data 可用')" || {
  echo "❌ sage.data 导入失败"
  exit 1
}
```

### 修复要点

1. **移除静默失败**：
   - ❌ 不再使用 `2>/dev/null || echo "可选"`
   - ✅ 导入失败直接 `exit 1`

2. **明确验证所有已安装的包**：
   - 使用 `pip show` 检查包是否安装
   - 如果安装了就必须验证导入成功

3. **验证子包**：
   - 不仅验证顶层包 `import sage.benchmark`
   - 还验证子包 `from sage.data import ...`

4. **按模式验证**：
   - Core: 基础功能
   - Standard/Full/Dev: 基础 + benchmark + apps + 其他

## 效果预期

### 修复前
```
✅ SAGE version: 0.5.0
✅ sage.common 可用
✅ sage.kernel 可用
✅ sage CLI 可用
ℹ️  sage.apps 可选  # ⚠️ 导入失败但被忽略
✅ 验证通过！        # ⚠️ 实际上有问题但 CI 通过
```

### 修复后
```
✅ SAGE version: 0.5.0
✅ sage.common 可用
✅ sage.kernel 可用
✅ sage CLI 可用
❌ sage.benchmark 导入失败  # ✅ 问题被检测到
Error: Process completed with exit code 1.
```

## 最佳实践建议

### 1. CI 验证原则
- **全覆盖**：验证所有已安装的包
- **零容忍**：导入失败必须导致 CI 失败
- **细粒度**：不仅验证顶层包，还要验证重要子包

### 2. 验证代码模板

```bash
# 检查包是否安装
if pip show package-name >/dev/null 2>&1; then
  # 验证导入（不静默错误）
  python -c "import package; print('✅ package 可用')" || {
    echo "❌ package 导入失败"
    exit 1  # 明确失败
  }

  # 验证关键子模块
  python -c "from package.submodule import key_function; print('✅ submodule 可用')" || {
    echo "❌ submodule 导入失败"
    exit 1
  }
fi
```

### 3. 添加新包时的 CI 更新清单

当添加新包时，必须更新 CI 验证：

- [ ] 在对应的安装模式中添加导入测试
- [ ] 验证顶层包导入
- [ ] 验证关键子模块导入
- [ ] 确保失败会导致 CI 退出
- [ ] 测试 CI 是否能检测到故意的导入错误

## 相关 Commits

- 主 Commit: 修复 Python 相对导入问题 (sage.data)
- CI 增强: 添加 benchmark/data 导入验证

## 参考

- Workflow 文件: `.github/workflows/pip-installation-test.yml`
- 相关问题: sage.data 相对导入错误未被 CI 检测
