# sageTSDB Submodule Setup Guide

本指南说明如何将 sageTSDB C++ 核心设置为独立的 Git 仓库，并作为 submodule 集成到 SAGE 中。

## 📋 概述

sageTSDB 采用以下架构：

1. **C++ 核心** - 独立的 Git 仓库 (https://github.com/intellistream/sageTSDB)
   - 高性能时序数据库引擎
   - 可插拔算法框架
   - 独立构建和测试

2. **Python 服务层** - SAGE 仓库的一部分
   - Python 包装和服务接口
   - SAGE 工作流集成
   - 微服务封装

## 🚀 完整设置流程

### Step 1: 准备 sageTSDB 仓库

当前 sageTSDB 目录已包含完整的 C++ 实现，运行设置脚本初始化 Git 仓库：

```bash
cd /home/shuhao/SAGE/packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB

# 运行设置脚本
./setup_repo.sh
```

这个脚本会：
- 初始化 Git 仓库
- 添加所有文件
- 创建初始提交
- 配置 remote 为 https://github.com/intellistream/sageTSDB.git

### Step 2: 在 GitHub 上创建仓库

1. 访问 https://github.com/intellistream
2. 点击 "New repository"
3. 仓库名称: `sageTSDB`
4. 描述: "High-performance time series database with C++ core"
5. **重要**: 不要勾选 "Initialize this repository with a README"
6. 点击 "Create repository"

### Step 3: 推送代码到 GitHub

```bash
cd /home/shuhao/SAGE/packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB

# 推送到 GitHub
git push -u origin main
```

### Step 4: 移除当前目录（准备作为 submodule）

**重要**: 在执行此步骤前，确保代码已成功推送到 GitHub！

```bash
# 回到 SAGE 根目录
cd /home/shuhao/SAGE

# 移除当前的 sageTSDB 目录（它将被 submodule 替换）
rm -rf packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB

# 提交这个变更
git add packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Prepare for sageTSDB submodule integration"
```

### Step 5: 添加 sageTSDB 作为 Submodule

```bash
# 在 SAGE 根目录
cd /home/shuhao/SAGE

# 添加 submodule
git submodule add https://github.com/intellistream/sageTSDB.git \
    packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB

# 初始化 submodule
git submodule update --init --recursive

# 提交 submodule 配置
git add .gitmodules packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Add sageTSDB as submodule"
git push
```

### Step 6: 验证设置

```bash
# 检查 submodule 状态
git submodule status

# 应该看到类似输出:
# +<commit-hash> packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB (heads/main)

# 构建 sageTSDB
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
./build.sh --test

# 测试 Python 集成
cd ..
python examples/basic_usage.py
```

## 🔄 日常开发工作流

### 更新 sageTSDB C++ 核心

```bash
# 1. 进入 submodule 目录
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB

# 2. 确保在正确的分支
git checkout main
git pull origin main

# 3. 进行修改
vim src/core/time_series_db.cpp

# 4. 测试
./build.sh --test

# 5. 提交到 sageTSDB 仓库
git add .
git commit -m "Update: feature description"
git push origin main

# 6. 返回 SAGE 根目录，更新 submodule 引用
cd /home/shuhao/SAGE
git add packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Update sageTSDB submodule to latest version"
git push
```

### 在其他机器上克隆 SAGE (含 submodules)

```bash
# 克隆时包含 submodules
git clone --recursive https://github.com/intellistream/SAGE.git

# 或者先克隆，然后初始化 submodules
git clone https://github.com/intellistream/SAGE.git
cd SAGE
git submodule update --init --recursive
```

### 更新 submodule 到最新版本

```bash
# 在 SAGE 根目录
cd /home/shuhao/SAGE

# 更新所有 submodules
git submodule update --remote --recursive

# 或者只更新 sageTSDB
git submodule update --remote packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB

# 提交更新
git add packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Update sageTSDB submodule"
git push
```

## 📁 目录结构

设置完成后的目录结构：

```
SAGE/
├── .gitmodules                                      # submodule 配置
├── packages/
│   └── sage-middleware/
│       └── src/
│           └── sage/
│               └── middleware/
│                   └── components/
│                       └── sage_tsdb/
│                           ├── __init__.py          # SAGE 组件入口
│                           ├── service.py           # SAGE 服务接口
│                           ├── README.md            # 集成文档
│                           ├── python/              # Python 服务层
│                           │   ├── sage_tsdb.py (wrapper)
│                           │   ├── algorithms/
│                           │   └── micro_service/
│                           ├── examples/            # 示例代码
│                           └── sageTSDB/            # Git submodule ⬅️
│                               ├── .git/            # 独立的 Git 仓库
│                               ├── include/         # C++ 头文件
│                               ├── src/             # C++ 实现
│                               ├── python/          # pybind11 绑定
│                               ├── CMakeLists.txt
│                               └── README.md        # C++ 核心文档
```

## 🛠️ 构建配置

### CMake 配置 (sageTSDB 内部)

C++ 核心使用 CMake 构建系统：

```cmake
# sageTSDB/CMakeLists.txt
cmake_minimum_required(VERSION 3.15)
project(sageTSDB)

# 构建库
add_library(sage_tsdb ${SOURCES})

# Python 绑定
if(BUILD_PYTHON_BINDINGS)
    add_subdirectory(python)
endif()
```

### SAGE 集成

SAGE 的 Python 层直接导入构建的库：

```python
# sage_tsdb/python/sage_tsdb.py
from ..sageTSDB.build.lib import _sage_tsdb  # C++ 绑定

class SageTSDB:
    def __init__(self):
        self._cpp_db = _sage_tsdb.TimeSeriesDB()
```

## ⚠️ 常见问题

### 问题 1: Submodule 目录为空

**症状**: 克隆 SAGE 后，`sageTSDB/` 目录存在但是空的

**解决**:
```bash
git submodule update --init --recursive
```

### 问题 2: Submodule 处于 detached HEAD 状态

**症状**: 进入 submodule 目录后，`git branch` 显示 detached HEAD

**解决**:
```bash
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git checkout main
git pull origin main
```

### 问题 3: 推送时提示 submodule 有未提交的更改

**症状**: `git push` 失败，提示 submodule 有更改

**解决**:
```bash
# 进入 submodule
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB

# 提交更改到 sageTSDB
git add .
git commit -m "Update"
git push origin main

# 返回 SAGE，更新引用
cd /home/shuhao/SAGE
git add packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Update sageTSDB reference"
git push
```

### 问题 4: 构建失败找不到头文件

**症状**: 编译时报错找不到 `sage_tsdb/*.h`

**解决**:
```bash
# 确保 submodule 已初始化
git submodule update --init --recursive

# 重新构建
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
./build.sh
```

## 📚 参考资料

- [Git Submodules 官方文档](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [sageTSDB C++ 文档](sageTSDB/README.md)
- [SAGE 开发指南](../../../../DEVELOPER.md)

## ✅ 检查清单

设置完成后，确认以下内容：

- [ ] sageTSDB 已推送到 GitHub
- [ ] SAGE 中已添加 submodule 配置
- [ ] `.gitmodules` 文件存在且正确
- [ ] C++ 核心可以成功构建
- [ ] Python 示例可以运行
- [ ] Submodule 状态正常（`git submodule status`）

## 📮 获取帮助

如果遇到问题：

1. 查看本文档的"常见问题"部分
2. 提交 Issue: https://github.com/intellistream/SAGE/issues
3. 联系维护者: shuhao_zhang@hust.edu.cn

---

**祝开发顺利！🚀**
