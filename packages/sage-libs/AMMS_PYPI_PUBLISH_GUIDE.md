# 发布 isage-amms 到 PyPI 完整指南

## 📋 前置准备

### 1. 确认包结构

```
packages/sage-libs/
├── pyproject.toml          # ✓ 已配置 isage-amms
├── setup.py                # ✓ 已配置
├── src/sage/libs/amms/     # ✓ AMM 算法实现
│   ├── __init__.py
│   ├── interface/
│   ├── wrappers/
│   ├── implementations/
│   └── docs/
└── BUILD_PUBLISH.md        # ✓ 构建发布说明
```

### 2. 版本管理

检查并更新版本号：

```bash
# 在 packages/sage-libs/src/sage/libs/amms/__init__.py
__version__ = "0.1.0"  # 更新为新版本
```

### 3. PyPI 账号准备

- 注册 PyPI 账号: https://pypi.org/account/register/
- 生成 API Token: https://pypi.org/manage/account/token/
- 配置 `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-xxx  # 你的 PyPI API Token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-xxx  # TestPyPI API Token
```

## 🚀 发布流程

### 方式 1: 使用 sage-dev（推荐）

```bash
# 1. 测试构建（不上传）
cd /home/shuhao/SAGE
sage-dev package pypi build sage-libs --dry-run

# 2. 先上传到 TestPyPI 测试
sage-dev package pypi build sage-libs --upload --no-dry-run --test-pypi

# 3. 从 TestPyPI 安装测试
pip install -i https://test.pypi.org/simple/ isage-amms
python -c "from sage.libs.amms import create_amm_index; print('Success!')"

# 4. 确认无误后，正式发布到 PyPI
sage-dev package pypi build sage-libs --upload --no-dry-run

# 5. 验证安装
pip install isage-amms
python -c "from sage.libs.amms import create_amm_index; print('Success!')"
```

### 方式 2: 手动构建（传统方式）

```bash
cd /home/shuhao/SAGE/packages/sage-libs

# 1. 清理旧构建
rm -rf dist/ build/ *.egg-info/

# 2. 构建分发包
python -m build

# 3. 检查生成的包
ls -lh dist/
# 应该看到:
# isage_amms-0.1.0-py3-none-any.whl
# isage-amms-0.1.0.tar.gz

# 4. 上传到 TestPyPI（测试）
python -m twine upload --repository testpypi dist/*

# 5. 测试安装
pip install -i https://test.pypi.org/simple/ isage-amms

# 6. 确认无误后，上传到正式 PyPI
python -m twine upload dist/*
```

## ✅ 发布前检查清单

### 代码质量

- [ ] 所有测试通过: `sage-dev project test packages/sage-libs/tests/unit/amms/`
- [ ] 代码格式化: `sage-dev quality`
- [ ] 类型检查无错误: `mypy packages/sage-libs/src/sage/libs/amms/`

### 文档完整性

- [ ] README.md 更新
- [ ] API 文档完整: `packages/sage-libs/src/sage/libs/amms/docs/`
- [ ] CHANGELOG.md 记录变更

### 包配置

- [ ] `pyproject.toml` 中的版本号正确
- [ ] `__init__.py` 中的 `__version__` 匹配
- [ ] 依赖列表完整（numpy, pybind11 等）
- [ ] 包名正确: `isage-amms`

### 构建测试

- [ ] 本地构建成功: `python -m build`
- [ ] 检查包内容: `tar -tzf dist/isage-amms-*.tar.gz`
- [ ] TestPyPI 安装测试通过

## 📦 包内容验证

```bash
# 检查构建的 wheel 包内容
unzip -l dist/isage_amms-0.1.0-py3-none-any.whl

# 应该包含:
# sage/libs/amms/__init__.py
# sage/libs/amms/interface/
# sage/libs/amms/wrappers/
# sage/libs/amms/implementations/
# sage/libs/amms/docs/
```

## 🔄 版本更新流程

每次发布新版本：

```bash
# 1. 更新版本号
vim packages/sage-libs/src/sage/libs/amms/__init__.py
# __version__ = "0.1.1"  # 或 0.2.0

# 2. 更新 CHANGELOG
vim packages/sage-libs/CHANGELOG.md

# 3. 提交版本更新
git add packages/sage-libs/src/sage/libs/amms/__init__.py
git add packages/sage-libs/CHANGELOG.md
git commit -m "chore(amms): bump version to 0.1.1"

# 4. 打标签
git tag -a v0.1.1-amms -m "Release isage-amms 0.1.1"
git push origin v0.1.1-amms

# 5. 构建并发布
sage-dev package pypi build sage-libs --upload --no-dry-run
```

## 🐛 常见问题

### 1. 构建失败: "Module not found"

```bash
# 确保在正确的目录
cd packages/sage-libs
# 检查 PYTHONPATH
export PYTHONPATH=/home/shuhao/SAGE/packages/sage-libs/src:$PYTHONPATH
```

### 2. 上传失败: "Package already exists"

```bash
# 需要更新版本号
vim src/sage/libs/amms/__init__.py  # 增加版本号
```

### 3. TestPyPI 依赖问题

```bash
# TestPyPI 可能没有所有依赖，使用混合安装
pip install numpy pybind11  # 从正式 PyPI
pip install -i https://test.pypi.org/simple/ isage-amms
```

## 📚 参考文档

- SAGE PyPI 发布文档: `docs-public/docs_src/dev-notes/cross-layer/pypi-publishing.md`
- sage-libs BUILD_PUBLISH.md: `packages/sage-libs/BUILD_PUBLISH.md`
- sage-dev PyPI 工具: `sage-dev package pypi --help`
- Python 打包指南: https://packaging.python.org/

## 🎯 快速命令参考

```bash
# 完整发布流程（一键）
cd /home/shuhao/SAGE
sage-dev package pypi build sage-libs --upload --no-dry-run --test-pypi  # 测试
sage-dev package pypi build sage-libs --upload --no-dry-run              # 正式

# 验证发布
pip install isage-amms
python -c "from sage.libs.amms import create_amm_index; print('✓ Published!')"
```

## ⚠️ 重要提醒

1. **先测试后发布**: 总是先上传到 TestPyPI 测试
1. **版本不可覆盖**: PyPI 不允许覆盖已发布的版本
1. **依赖版本**: 确保依赖版本兼容性（Python 3.8-3.12）
1. **C++ 扩展**: AMM 算法如果有 C++ 扩展，需要单独处理编译
1. **文档同步**: 发布后更新 README 中的安装命令

## 🎉 发布后

1. 更新 LibAMM benchmark 的 requirements.txt:

   ```
   isage-amms>=0.1.0  # 取消注释
   ```

1. 更新文档中的安装说明

1. 在 SAGE README 中添加 PyPI 徽章:

   ```markdown
   [![PyPI](https://img.shields.io/pypi/v/isage-amms)](https://pypi.org/project/isage-amms/)
   ```

1. 公告发布:

   - GitHub Release
   - CHANGELOG.md
   - 项目文档更新
