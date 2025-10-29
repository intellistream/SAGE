# PyPI Installation Test - Shared Library Fix

**Date**: 2025-10-29  
**Author**: GitHub Copilot  
**Summary**: 修复 PyPI 安装测试中共享库缺失问题，确保 C++ 库正确打包到 wheel 中

**问题**: PyPI Installation Test 失败，报错 `libsageflow.so: cannot open shared object file`

## 问题描述

在 GitHub Actions 的 PyPI Installation Test 中，从 wheel 安装 `isage[standard]` 时出现以下错误：

```
ImportError: libsageflow.so: cannot open shared object file: No such file or directory
```

错误发生在导入 `sage.middleware.components.sage_flow` 时。

## 根本原因

使用 `scikit-build-core` 构建 wheel 包时，C++ 共享库（如 `libsageflow.so`、`libsage_db.so`、`libsage_tsdb_core.so` 等）没有被正确安装到 wheel 包中。

具体问题：
1. CMakeLists.txt 中使用了 `SKBUILD_PLATLIB_DIR` 变量来判断是否为 Python 包构建模式
2. 但在 editable install 和 wheel build 两种情况下，安装目标路径应该不同：
   - **Editable install**: 安装到源码树 `python/` 目录
   - **Wheel build**: 安装到 wheel 的 platlib 目录（与 Python 扩展同目录）
3. 原代码只检查 `SKBUILD_PLATLIB_DIR` 是否定义，在 wheel build 时错误地安装到了源码树，导致 wheel 包中缺少这些共享库

## 修复方案

### 1. 修复 sage_flow 的 CMakeLists.txt

**文件**: `packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow/src/CMakeLists.txt`

```cmake
# 修复前
if(DEFINED SKBUILD_PLATLIB_DIR)
    install(TARGETS sageflow
            LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/../python
            ...
    )
else()
    # 独立构建
endif()

# 修复后
if(DEFINED SKBUILD)
    if(SKBUILD_STATE STREQUAL "editable")
        # Editable install: install to source tree directly
        set(_lib_install_dest "${CMAKE_CURRENT_SOURCE_DIR}/../python")
    else()
        # Wheel build: install to wheel platlib (same directory as Python extension)
        set(_lib_install_dest "${SKBUILD_PLATLIB_DIR}/sage/middleware/components/sage_flow/python")
    endif()

    install(TARGETS sageflow
            LIBRARY DESTINATION ${_lib_install_dest}
            ARCHIVE DESTINATION ${_lib_install_dest}
            RUNTIME DESTINATION ${_lib_install_dest}
            COMPONENT python
    )
else()
    # 独立 C++ 构建模式
    ...
endif()
```

### 2. 修复 sage_db 的 CMakeLists.txt

**文件**: `packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB/CMakeLists.txt`

应用相同的修复模式：
- 检查 `SKBUILD` 变量而不是 `SKBUILD_PLATLIB_DIR`
- 根据 `SKBUILD_STATE` 变量区分 editable install 和 wheel build
- Wheel build 时安装到 `${SKBUILD_PLATLIB_DIR}/sage/middleware/components/sage_db/python`

### 3. 修复 sage_tsdb 的 CMakeLists.txt

**文件**: `packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB/CMakeLists.txt`

应用相同的修复模式。

### 4. 更新 MANIFEST.in 注释

**文件**: `packages/sage-middleware/MANIFEST.in`

更新注释以明确说明包含了 Python 扩展和原生库。

## 关键技术点

### scikit-build-core 变量

- `SKBUILD`: 在任何 scikit-build-core 构建中都定义（editable 或 wheel）
- `SKBUILD_STATE`:
  - `"editable"`: pip install -e 时
  - 其他值: 构建 wheel 时
- `SKBUILD_PLATLIB_DIR`: wheel 构建时的目标安装目录
- `SKBUILD_PLATLIB_DIR` 在 editable install 时也会定义，但不应该用于安装路径

### RPATH 设置

Python 扩展模块（如 `_sage_flow.*.so`）已经正确设置了 RPATH `$ORIGIN`：

```cmake
set_target_properties(_sage_flow PROPERTIES
    BUILD_RPATH_USE_ORIGIN TRUE
    INSTALL_RPATH "$ORIGIN"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)
```

这确保了 Python 扩展能在运行时找到同目录下的共享库（如 `libsageflow.so`）。

## 验证方法

### 本地测试

```bash
# 1. 构建 wheel
cd packages/sage-middleware
python -m build

# 2. 检查 wheel 内容
unzip -l dist/isage_middleware-*.whl | grep -E '\.so$'

# 应该看到：
# sage/middleware/components/sage_flow/python/_sage_flow.*.so
# sage/middleware/components/sage_flow/python/libsageflow.so
# sage/middleware/components/sage_db/python/_sage_db.*.so
# sage/middleware/components/sage_db/python/libsage_db.so
# sage/middleware/components/sage_tsdb/python/_sage_tsdb.*.so
# sage/middleware/components/sage_tsdb/python/libsage_tsdb_core.so
# sage/middleware/components/sage_tsdb/python/libsage_tsdb_algorithms.so

# 3. 测试安装
python -m venv /tmp/test_env
source /tmp/test_env/bin/activate
pip install dist/isage_middleware-*.whl
python -c "from sage.middleware.components.sage_flow.python.sage_flow import SageFlow; print('Success!')"
deactivate
```

### CI 测试

GitHub Actions workflow `pip-installation-test.yml` 会自动测试：
- 从 wheel 安装
- 从源码安装
- 多个 Python 版本 (3.10, 3.11, 3.12)
- 多种安装模式 (core, standard, full, dev)

## 影响范围

### 修改的文件

1. `packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow/src/CMakeLists.txt`
2. `packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB/CMakeLists.txt`
3. `packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB/CMakeLists.txt`
4. `packages/sage-middleware/MANIFEST.in`

### 受影响的组件

- sage-middleware (所有包含 C++ 扩展的组件)
  - sage_flow
  - sage_db
  - sage_tsdb

### 不受影响的包

- sage-common (纯 Python)
- sage-platform (纯 Python)
- sage-kernel (纯 Python)
- sage-libs (纯 Python)
- sage-tools (纯 Python)
- sage-apps (纯 Python)

## 后续工作

1. 确保所有 C++ 子模块遵循相同的安装模式
2. 考虑在 SAGE 根 CMakeLists.txt 中定义统一的安装宏
3. 在 CI 中添加 wheel 内容验证步骤

## 参考资料

- [scikit-build-core 文档](https://scikit-build-core.readthedocs.io/)
- [CMake RPATH 处理](https://cmake.org/cmake/help/latest/prop_tgt/INSTALL_RPATH.html)
- [Python Extension 打包最佳实践](https://packaging.python.org/guides/packaging-binary-extensions/)
