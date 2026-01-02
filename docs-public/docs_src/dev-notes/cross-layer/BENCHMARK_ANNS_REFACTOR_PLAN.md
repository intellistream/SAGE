# benchmark_anns 目录重构计划

## 问题诊断

当前 `packages/sage-benchmark/src/sage/benchmark/benchmark_anns/` 结构混乱：

```
benchmark_anns/ (submodule: SAGE-DB-Bench)
├── DiskANN/              ← 问题：Microsoft 官方版本，应该在 algorithms_impl 下
├── algorithms_impl/      ← 正确位置
│   ├── DiskANN/          ← 不同版本的 DiskANN (非 submodule)
│   ├── ipdiskann/        ← submodule
│   ├── faiss/            ← 包含大量测试文件
│   ├── vsag/
│   └── ...
```

### 根本原因

1. `benchmark_anns/DiskANN/` 作为 submodule 直接放在根目录，不符合规范
1. 第三方算法库的测试文件被 pytest 自动收集
1. 这些测试依赖未安装的库 (diskannpy, faiss.contrib)

## 解决方案

### 方案 1：临时方案（pytest 配置排除）✅ 已实施

在 `tools/pytest.ini` 中排除第三方测试：

```ini
addopts =
    --ignore-glob=**/benchmark_anns/**/test_*.py
    --ignore-glob=**/algorithms_impl/**/test_*.py
    --ignore-glob=**/DiskANN/**/test_*.py
    --ignore-glob=**/faiss/**/test_*.py
```

**优点**: 快速解决 CI 问题 **缺点**: 治标不治本

### 方案 2：重构 SAGE-DB-Bench 仓库（推荐）

在 `SAGE-DB-Bench` 仓库中进行以下重构：

#### 步骤 1: 移动 DiskANN submodule

```bash
cd packages/sage-benchmark/src/sage/benchmark/benchmark_anns

# 移除根目录的 DiskANN submodule
git submodule deinit DiskANN
git rm DiskANN
git commit -m "refactor: remove DiskANN from root, prepare for reorganization"

# 添加到 algorithms_impl 下（如果需要 Microsoft 官方版本）
cd algorithms_impl
git submodule add https://github.com/microsoft/DiskANN.git diskann-official
git commit -m "refactor: add Microsoft DiskANN to algorithms_impl"
```

#### 步骤 2: 重命名现有的 DiskANN

```bash
cd algorithms_impl
git mv DiskANN diskann-sage  # 或其他区分性名称
git commit -m "refactor: rename DiskANN to diskann-sage for clarity"
```

#### 步骤 3: 统一命名规范

建议的目录结构：

```
benchmark_anns/
├── algorithms_impl/           # 所有第三方算法实现
│   ├── diskann-official/      # Microsoft 官方版本 (submodule)
│   ├── diskann-sage/          # SAGE 修改版本
│   ├── ipdiskann/             # IntelliStream IP-DiskANN (submodule)
│   ├── faiss/                 # Facebook FAISS
│   ├── vsag/                  # Vector Search Algorithm Gateway
│   ├── sptag/                 # SPTAG
│   └── ...
├── benchmarks/                # SAGE 的 benchmark 代码（不是算法本身）
│   ├── anns_benchmark.py
│   ├── recall_benchmark.py
│   └── ...
└── tests/                     # SAGE-DB-Bench 自己的测试（不是第三方算法测试）
    ├── test_benchmark_runner.py
    └── test_metrics.py
```

#### 步骤 4: 添加 pytest.ini 到 SAGE-DB-Bench

在 `benchmark_anns/pytest.ini`:

```ini
[pytest]
# 排除第三方算法库的测试
norecursedirs =
    algorithms_impl
    extern
    third_party
    vendors

addopts =
    --ignore-glob=**/algorithms_impl/**/test_*.py
```

### 方案 3：使用 conftest.py 动态跳过

在 `benchmark_anns/conftest.py`:

```python
import pytest

def pytest_configure(config):
    """跳过所有 algorithms_impl 下的测试"""
    config.addinivalue_line(
        "markers", "third_party: tests from third-party algorithm libraries"
    )

def pytest_collection_modifyitems(config, items):
    """自动标记并跳过第三方测试"""
    for item in items:
        if "algorithms_impl" in str(item.fspath) or "DiskANN" in str(item.fspath):
            item.add_marker(pytest.mark.skip(reason="Third-party algorithm test"))
```

## 实施计划

### 短期（本次修复）✅ 完成

- [x] 在 `tools/pytest.ini` 中排除第三方测试文件
- [x] 验证 CI 测试通过

### 中期（下个版本）

- [ ] 在 SAGE-DB-Bench 仓库提 Issue 讨论重构方案
- [ ] 实施方案 2 的目录重构
- [ ] 更新 SAGE-DB-Bench 文档

### 长期（架构改进）

- [ ] 考虑将 algorithms_impl 作为可选依赖
- [ ] 提供安装脚本选择性编译算法库
- [ ] 建立 Docker 镜像包含预编译的算法库

## 相关文件

- **SAGE 主项目**: `tools/pytest.ini`
- **SAGE-DB-Bench 仓库**: `packages/sage-benchmark/src/sage/benchmark/benchmark_anns/.gitmodules`
- **相关 Issue**: (待创建)

## 参考

- Microsoft DiskANN: https://github.com/microsoft/DiskANN
- SAGE-DB-Bench: https://github.com/intellistream/SAGE-DB-Bench
- IntelliStream IP-DiskANN: https://github.com/intellistream/IP-DiskANN
