# Build Cache Management

## Overview

SAGE 包含自动构建缓存检测和清理功能，用于防止版本不一致问题。这个功能会在安装过程中自动运行，也可以手动调用。

## 问题背景

在开发过程中，Python 包的元数据会缓存在 `*.egg-info` 目录中。当源代码中的版本号更新（例如在 `_version.py` 中），但 egg-info 缓存未清理时，会导致：

- `pip list` 显示的版本与源代码不一致
- 安装后的版本号混乱
- CI/CD 和本地环境版本不一致

### 示例场景

```bash
# 源代码版本
$ cat packages/sage-common/src/sage/common/_version.py
__version__ = "0.1.10.7"

# 但 pip 显示的是缓存的旧版本
$ pip list | grep isage-common
isage-common  0.1.8.8  /path/to/packages/sage-common

# 根本原因：egg-info 中缓存了旧版本
$ cat packages/sage-common/src/isage_common.egg-info/PKG-INFO
Version: 0.1.8.8
```

## 解决方案

### 自动清理（推荐）

`quickstart.sh` 在安装过程中会自动检测和清理版本不一致的缓存：

```bash
./quickstart.sh --dev --yes
```

输出示例：
```
🧹 检查构建缓存...
 检查 egg-info 缓存...
  发现 10 个 egg-info 缓存目录
  检查版本一致性...
  ⚠️  版本不一致: isage_common
     缓存: 0.1.8.8 | 源码: 0.1.10.7
  检测到版本不一致，清理 egg-info 缓存...
 ✓ egg-info 缓存已清理
```

### 手动清理

如果需要手动清理缓存：

```bash
# 方法 1: 使用 Makefile（推荐）
make clean-cache

# 方法 2: 直接调用清理工具
bash tools/install/fixes/build_cache_cleaner.sh clean

# 方法 3: 仅检测和清理有问题的缓存（自动模式）
bash tools/install/fixes/build_cache_cleaner.sh detect
```

### 清理选项

清理工具支持多种模式：

| 命令 | 说明 | 清理内容 |
|------|------|----------|
| `detect` | 自动检测并清理（默认） | 仅清理版本不一致的 egg-info |
| `clean` | 强制清理所有缓存 | egg-info + build + dist |
| `egg-info` | 仅清理 egg-info | 所有 egg-info 目录 |
| `build` | 仅清理 build | 所有 build 目录 |
| `dist` | 仅清理 dist | 所有 dist 目录 |

## 工作原理

### 检测逻辑

1. 扫描 `packages/*/src/*.egg-info/` 目录
2. 读取每个 egg-info 中的 `PKG-INFO` 文件获取缓存版本
3. 查找对应包的 `_version.py` 文件获取源码版本
4. 比较两个版本号
5. 如果发现不一致，删除所有 egg-info 缓存

### 集成点

清理功能集成在以下位置：

**安装流程** (`tools/install/installation_table/main_installer.sh`):
```bash
# 配置安装环境（包含所有检查）
configure_installation_environment "$environment" "$mode"

# 清理构建缓存（检测版本不一致的 egg-info）
detect_and_clean_cache false

# 清理 pip 缓存（如果启用）
clean_pip_cache "$log_file"
```

**命令行工具** (`Makefile`):
```makefile
clean-cache:
	@bash tools/install/fixes/build_cache_cleaner.sh clean
```

## 使用场景

### 何时需要手动清理

虽然 `quickstart.sh` 会自动处理，但在以下情况下可能需要手动清理：

1. **更新代码后版本显示错误**
   ```bash
   git pull origin main-dev
   make clean-cache
   ./quickstart.sh --dev --yes
   ```

2. **版本升级前**
   ```bash
   # 修改所有 _version.py 后
   make clean-cache
   ```

3. **排查安装问题**
   ```bash
   make clean-cache
   pip uninstall -y isage-common isage-kernel ...
   ./quickstart.sh --dev --yes
   ```

### 何时不需要清理

- 正常开发过程中的代码修改（非版本号修改）
- 首次安装
- 版本号未变化的情况

## 日志和调试

清理工具会输出详细的日志信息，并集成到 SAGE 的日志系统中：

```bash
# 查看安装日志（包含缓存清理信息）
tail -f .sage/logs/install.log

# 搜索缓存相关日志
grep "BuildCache" .sage/logs/install.log
```

日志级别：
- `[INFO]`: 正常操作信息
- `[WARN]`: 发现问题但可以处理
- `[DEBUG]`: 详细的调试信息

## 相关文件

| 文件 | 说明 |
|------|------|
| `tools/install/fixes/build_cache_cleaner.sh` | 缓存清理工具主脚本 |
| `tools/install/installation_table/main_installer.sh` | 集成点：安装流程 |
| `Makefile` | 集成点：make clean-cache |
| `DEVELOPER.md` | 用户文档 |

## 最佳实践

1. **使用 quickstart.sh 安装**：自动处理缓存问题
2. **版本升级后检查**：运行 `pip list | grep isage` 验证版本一致性
3. **遇到版本问题时**：先运行 `make clean-cache`
4. **CI/CD 环境**：已自动集成，无需额外配置

## 故障排除

### 问题：清理后仍然显示旧版本

```bash
# 完全重装
make clean-cache
pip uninstall -y $(pip list | grep isage | awk '{print $1}')
./quickstart.sh --dev --yes
```

### 问题：清理工具报错

```bash
# 检查权限
ls -la packages/*/src/*.egg-info/

# 手动删除
find packages -type d -name "*.egg-info" -exec rm -rf {} +
```

### 问题：版本号格式不支持

清理工具使用正则表达式匹配版本号：`[0-9.]+`

如果使用非标准版本号（如 `0.1.10.7-dev`），可能需要修改匹配规则。

## 参考

- [Installation Consistency Guide](./INSTALLATION_CONSISTENCY.md)
- [Package Architecture](../package-architecture.md)
- [CI/CD Documentation](./ci-cd/README.md)
