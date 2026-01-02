**Date**: 2025-11-12 **Author**: shuhao **Summary**: Implementation of comprehensive structured
logging system for SAGE installation to address debugging issues.

# SAGE 安装日志系统增强

## 概述

为了解决 "log太简单了，一些bug出现我压根不知道是怎么回事" 的问题，实现了全面的结构化日志系统。

## 实现的功能

### 1. 统一日志框架 (`tools/install/display_tools/logging.sh`)

#### 日志级别

- **DEBUG (0)**: 详细调试信息（命令、参数、路径等）
- **INFO (1)**: 一般信息（步骤开始/完成）
- **WARN (2)**: 警告（非致命错误）
- **ERROR (3)**: 错误（导致安装失败）

#### 核心函数

```bash
# 基础日志记录
log_debug "调试信息" "CONTEXT"
log_info "一般信息" "CONTEXT"
log_warn "警告信息" "CONTEXT"
log_error "错误信息" "CONTEXT"

# 命令执行跟踪
log_command "执行的命令" "CONTEXT"
# 特点：捕获命令输出、记录退出码、自动错误检测

# 阶段跟踪
log_phase_start "阶段名称" "CONTEXT"
log_phase_end "阶段名称" "success|failure|partial_success" "CONTEXT"

# 环境信息收集
log_environment "CONTEXT"
# 记录：OS、Python版本、Conda环境、PATH、工作目录等

# 包信息验证
log_pip_package_info "package-name" "CONTEXT"
# 验证包是否安装成功、版本、安装位置

# Python导入测试
log_python_import_test "module.name" "CONTEXT"
# 测试模块是否可导入、记录错误信息
```

### 2. 日志输出特性

#### 双重输出

- **控制台**: 彩色、简洁、用户友好
- **日志文件**: 完整、带时间戳、结构化

#### 自动时间戳

```
[2024-01-15 14:23:45] [INFO] [INSTALL] 开始安装: packages/sage-common
```

#### 上下文标签

- `INSTALL`: 包安装过程
- `MAIN`: 主安装流程
- `VLLM`: VLLM相关
- `ENV`: 环境配置
- 等等...

### 3. 已增强的安装脚本

#### `core_installer.sh` 增强内容

**日志初始化**:

```bash
# 在开始时记录完整环境信息
log_environment "INSTALL"
export SAGE_INSTALL_LOG="$log_file"
```

**包安装**（每个包）:

```bash
log_info "开始安装: $package" "INSTALL"
log_debug "PIP命令: $PIP_CMD install..." "INSTALL"
# 执行安装
log_info "安装成功: $package" "INSTALL"
log_pip_package_info "$pkg_name" "INSTALL"
```

**C++编译错误**:

```bash
if ! $PIP_CMD install sage-middleware ...; then
    log_error "安装 sage-middleware 失败！" "INSTALL"
    log_error "这通常是由于 C++ 编译错误" "INSTALL"

    # 提取编译错误摘要
    local error_context=$(grep -A 5 -i "error:" "$log_file" | tail -20)
    log_error "编译错误摘要:\n$error_context" "INSTALL"
fi
```

**外部依赖安装**:

```bash
log_phase_start "外部依赖安装" "INSTALL"
log_info "共提取 $dep_count 个外部依赖" "INSTALL"
log_debug "依赖列表:\n$(cat "$external_deps_file")" "INSTALL"
# 安装依赖
log_info "开始安装外部依赖包..." "INSTALL"
# 验证采样依赖
for dep in $sample_deps; do
    log_pip_package_info "$pkg_name" "INSTALL"
done
log_phase_end "外部依赖安装" "success" "INSTALL"
```

#### `main_installer.sh` 增强内容

**Phase级别跟踪**:

```bash
case "$mode" in
    "standard")
        log_phase_start "标准安装模式" "MAIN"

        install_core_packages "$mode"
        install_scientific_packages

        log_info "开始修复 C++ 扩展库安装" "MAIN"
        fix_middleware_cpp_extensions "$log_file"

        log_info "验证 C++ 扩展状态" "MAIN"
        if verify_cpp_extensions "$log_file"; then
            log_info "C++ 扩展验证成功" "MAIN"
            log_phase_end "标准安装模式" "success" "MAIN"
        else
            log_warn "C++ 扩展验证失败" "MAIN"
            log_phase_end "标准安装模式" "partial_success" "MAIN"
        fi
        ;;
esac
```

**环境配置**:

```bash
log_phase_start "环境配置" "MAIN"
configure_installation_environment "$environment" "$mode"
log_phase_end "环境配置" "success" "MAIN"
```

**CI检查**:

```bash
log_phase_start "依赖完整性检查" "MAIN"
if bash "$monitor_script" analyze "$log_file"; then
    log_info "依赖完整性检查通过" "MAIN"
    log_phase_end "依赖完整性检查" "success" "MAIN"
else
    log_error "检测到从 PyPI 下载了本地包" "MAIN"
    log_phase_end "依赖完整性检查" "failure" "MAIN"
fi
```

## 使用效果

### 日志文件示例

```log
========================================
SAGE 安装日志 - 2024-01-15 14:23:00
安装模式: dev
环境类型: conda
日志文件: /path/to/.sage/logs/install.log
========================================

[2024-01-15 14:23:01] [INFO] [INSTALL] ========== 环境信息 ==========
[2024-01-15 14:23:01] [INFO] [INSTALL] 操作系统: Linux 5.15.0-92-generic
[2024-01-15 14:23:01] [INFO] [INSTALL] Python版本: 3.10.13
[2024-01-15 14:23:01] [INFO] [INSTALL] Conda环境: ksage (/opt/conda/envs/ksage)
[2024-01-15 14:23:01] [INFO] [INSTALL] 工作目录: /home/zrc/develop_item/SAGE
[2024-01-15 14:23:01] [INFO] [INSTALL] =====================================

[2024-01-15 14:23:05] [INFO] [INSTALL] ========== 阶段开始: 基础包安装 (L1-L2) ==========
[2024-01-15 14:23:05] [INFO] [INSTALL] 开始安装: packages/sage-common
[2024-01-15 14:23:05] [DEBUG] [INSTALL] PIP命令: /opt/conda/envs/ksage/bin/pip install -e packages/sage-common --no-deps
[2024-01-15 14:23:10] [INFO] [INSTALL] 安装成功: packages/sage-common
[2024-01-15 14:23:10] [INFO] [INSTALL] 包信息验证: isage-common
[2024-01-15 14:23:10] [INFO] [INSTALL]   版本: 0.1.0
[2024-01-15 14:23:10] [INFO] [INSTALL]   位置: /home/zrc/develop_item/SAGE/packages/sage-common/src

[2024-01-15 14:23:15] [INFO] [INSTALL] 开始安装: packages/sage-middleware (包含 C++ 扩展)
[2024-01-15 14:23:15] [DEBUG] [INSTALL] 这一步会编译 C++ 扩展，可能较慢
[2024-01-15 14:23:15] [DEBUG] [INSTALL] PIP命令: /opt/conda/envs/ksage/bin/pip install -e packages/sage-middleware --no-deps
[执行 pip 安装命令，输出重定向到日志]
[2024-01-15 14:25:30] [INFO] [INSTALL] 安装成功: packages/sage-middleware

[2024-01-15 14:25:35] [INFO] [INSTALL] ========== 阶段开始: 外部依赖安装 ==========
[2024-01-15 14:25:35] [INFO] [INSTALL] 开始提取外部依赖（从 pyproject.toml 文件）
[2024-01-15 14:25:35] [DEBUG] [INSTALL] 外部依赖将保存到: .sage/external-deps-dev.txt
[2024-01-15 14:25:36] [INFO] [INSTALL] 共提取 117 个外部依赖
[2024-01-15 14:25:36] [DEBUG] [INSTALL] 依赖列表（前10个）:
numpy>=1.21.0
pandas>=1.3.0
torch>=2.0.0
...
[2024-01-15 14:25:36] [INFO] [INSTALL] 开始安装外部依赖包...
[执行 pip install -r external-deps.txt]
[2024-01-15 14:27:00] [INFO] [INSTALL] 外部依赖安装成功
[2024-01-15 14:27:01] [INFO] [INSTALL] ========== 阶段结束: 外部依赖安装 (success) ==========

[2024-01-15 14:27:05] [INFO] [MAIN] ========== 阶段开始: 开发者安装模式 ==========
[2024-01-15 14:27:10] [INFO] [MAIN] 验证 C++ 扩展状态
[2024-01-15 14:27:11] [INFO] [MAIN] C++ 扩展验证成功
[2024-01-15 14:27:15] [INFO] [MAIN] ========== 阶段结束: 开发者安装模式 (success) ==========

[2024-01-15 14:27:20] [INFO] [MAIN] SAGE 安装完成
```

### 错误调试示例

当出现 C++ 编译错误时：

```log
[2024-01-15 14:24:30] [ERROR] [INSTALL] 安装 sage-middleware 失败！
[2024-01-15 14:24:30] [ERROR] [INSTALL] 这通常是由于 C++ 编译错误，请检查日志: /path/to/install.log
[2024-01-15 14:24:30] [ERROR] [INSTALL] 编译错误摘要:
error: 'GLIBCXX_3.4.30' not found (required by ...)
collect2: error: ld returned 1 exit status
[end of output]
note: This error originates from a subprocess, and is likely not a problem with pip.
ERROR: Failed building wheel for sage-middleware
```

当外部依赖部分失败时：

```log
[2024-01-15 14:26:45] [WARN] [INSTALL] 部分外部依赖安装失败，但继续...
[2024-01-15 14:26:45] [WARN] [INSTALL] 失败详情:
ERROR: Could not find a version that satisfies the requirement package-x>=1.0.0
ERROR: No matching distribution found for package-x>=1.0.0
```

## 调试建议

### 1. 实时查看日志

```bash
tail -f .sage/logs/install.log
```

### 2. 搜索特定日志级别

```bash
# 查看所有错误
grep "\[ERROR\]" .sage/logs/install.log

# 查看所有警告
grep "\[WARN\]" .sage/logs/install.log

# 查看特定阶段
grep "阶段开始\|阶段结束" .sage/logs/install.log
```

### 3. 查看特定上下文

```bash
# 查看安装过程
grep "\[INSTALL\]" .sage/logs/install.log

# 查看主流程
grep "\[MAIN\]" .sage/logs/install.log
```

### 4. 查看包安装详情

```bash
# 查看某个包的安装
grep "sage-middleware" .sage/logs/install.log
```

## 后续改进建议

1. **日志分析工具**: 创建脚本自动分析日志、提取错误摘要
1. **日志压缩**: 对于成功的安装，可以压缩旧日志
1. **日志上传**: CI失败时自动上传日志到artifacts
1. **可视化**: 生成HTML格式的日志报告
1. **性能追踪**: 记录每个阶段的耗时

## 文件清单

- `tools/install/display_tools/logging.sh` - 日志框架（新增）
- `tools/install/installation_table/core_installer.sh` - 核心安装器（已增强）
- `tools/install/installation_table/main_installer.sh` - 主安装器（已增强）

## 兼容性

- ✅ 完全向后兼容现有安装脚本
- ✅ 不影响用户界面输出
- ✅ 可选功能（日志级别可配置）
- ✅ 支持 CI/CD 环境

## 测试验证

```bash
# 语法检查
bash -n tools/install/display_tools/logging.sh
bash -n tools/install/installation_table/core_installer.sh
bash -n tools/install/installation_table/main_installer.sh

# 功能测试
./quickstart.sh --mode dev
tail -f .sage/logs/install.log  # 查看日志
```
