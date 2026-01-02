# SAGE Middleware - scikit-build-core 迁移

## 迁移状态

**日期**: 2025-10-28 **状态**: 🚧 进行中 **分支**: `feature/package-restructuring-1032`

## 为什么迁移？

C++ 项目(sageDB, sageFlow, sageTSDB)正在快速迭代开发中，频繁的重新编译非常耗时。迁移到 `scikit-build-core` 可以获得：

1. ✅ **增量编译** - 只重新编译修改的文件
1. ✅ **CMake 缓存** - 避免重新配置
1. ✅ **更好的跨平台支持** - 标准化的构建流程
1. ✅ **现代 Python 打包** - 符合 PEP 517/518
1. ✅ **Editable installs** - 开发模式下也能使用 CMake

## 已完成

- [x] 更新 `CMakeLists.txt` 以支持 scikit-build-core

  - 使用 `SKBUILD_PROJECT_NAME` 和 `SKBUILD_PROJECT_VERSION`
  - 添加对所有三个 C++ 扩展的支持 (sage_db, sage_flow, sage_tsdb)
  - 增强的配置摘要输出

- [x] 更新 `pyproject.toml`

  - 切换到 `scikit-build-core` 作为 build-backend
  - 配置 CMake 选项和 wheel 打包
  - 添加开发模式 (editable) 配置

- [x] 创建 `MANIFEST.in`

  - 定义需要包含的额外文件
  - .so 文件、.pyi 类型存根、CMake 配置等

- [x] 备份旧的 `setup.py`

  - 移动到 `setup.py.backup`
  - 保留以供参考

## 待解决

### 1. 子模块 CMake 配置问题

**问题**: 子模块 (sageDB, sageFlow, sageTSDB) 的 `CMakeLists.txt` 可能需要调整以兼容 scikit-build-core。

**当前错误**:

```
/usr/lib/x86_64-linux-gnu/libopenblas.so: undefined reference to `_gfortran_etime@GFORTRAN_8'
```

这是 BLAS 链接问题，需要在子模块的 CMake 中修复。

**解决方案**:

1. 检查子模块的 CMakeLists.txt 中 BLAS/LAPACK 的查找逻辑
1. 确保正确链接 gfortran 库
1. 或者使用 conda 提供的 openblas

### 2. Install Rules

子模块需要正确配置 `install()` 命令，将 .so 文件安装到正确的位置：

```cmake
# 在子模块的 CMakeLists.txt 中：
install(
    TARGETS _sage_db
    LIBRARY DESTINATION sage/middleware/components/sage_db/python
    COMPONENT python
)
```

### 3. 版本号传递

确保版本号从 `_version.py` 正确传递到 CMake：

```toml
[tool.scikit-build]
cmake.version = "${version}"
```

## 测试计划

### Phase 1: 本地开发环境

```bash
# 1. 清理旧构建
rm -rf build/ dist/ *.egg-info

# 2. 开发模式安装
pip install -e . -v

# 3. 验证 C++ 扩展
python -c "from sage.middleware.components.sage_db.python import _sage_db; print(_sage_db.__version__)"
python -c "from sage.middleware.components.sage_flow.python import _sage_flow; print('OK')"
python -c "from sage.middleware.components.sage_tsdb.python import _sage_tsdb; print('OK')"

# 4. 测试增量编译
# 修改一个 C++ 文件
touch src/sage/middleware/components/sage_db/sageDB/src/some_file.cpp
# 重新安装 - 应该只重新编译修改的文件
pip install -e . -v
```

### Phase 2: Wheel 构建

```bash
# 构建 wheel
python -m build --wheel

# 安装并测试
pip install dist/*.whl
```

### Phase 3: CI/CD

更新 `.github/workflows/pip-installation-test.yml` 以使用新的构建系统。

## 回滚计划

如果迁移遇到不可解决的问题：

```bash
# 1. 恢复 setup.py
mv setup.py.backup setup.py

# 2. 恢复 pyproject.toml
git checkout HEAD -- pyproject.toml

# 3. 恢复 CMakeLists.txt (如果需要)
git checkout HEAD -- CMakeLists.txt
```

## 参考资料

- [scikit-build-core 文档](https://scikit-build-core.readthedocs.io/)
- [pybind11 + scikit-build-core 示例](https://github.com/pybind/scikit_build_example)
- [CMake 最佳实践](https://cliutils.gitlab.io/modern-cmake/)

## 下一步

1. **修复子模块链接问题**

   - 检查 sageDB/sageFlow/sageTSDB 的 CMakeLists.txt
   - 添加正确的 BLAS/Fortran 链接

1. **测试增量编译**

   - 修改一个 C++ 文件
   - 验证只重新编译该文件

1. **更新 CI/CD**

   - 确保 GitHub Actions 可以构建

1. **文档更新**

   - DEVELOPER.md
   - README.md
   - CONTRIBUTING.md

## 注意事项

- 🔧 **开发效率优先**: 增量编译可以节省大量时间
- 📦 **保持向后兼容**: 旧的安装方式应该还能工作
- 🧪 **充分测试**: 所有 C++ 扩展都要验证
- 📝 **文档同步**: 更新所有相关文档
