# spdlog 兼容性修复说明

## 问题描述

n2 库（GTI 的依赖）使用 `spdlog::stdout_color_mt()` API，但其头文件 `include/n2/hnsw_build.h` 中只包含了
`spdlog/spdlog.h`，缺少必要的 `spdlog/sinks/stdout_color_sinks.h`。

在 spdlog 1.9.2+ 版本中，`stdout_color_mt` 函数定义在 `spdlog/sinks/stdout_color_sinks.h` 中，因此必须显式包含该头文件。

## 解决方案

**采用构建时自动修复的方式**，而不是修改第三方库的源代码：

1. 在 `build_all.sh` 脚本中，构建 n2 库之前自动添加缺失的头文件包含
1. 使用 `sed` 命令在构建时临时修改 `hnsw_build.h`
1. 修改只存在于构建过程中，不会提交到 git 仓库

## 实现细节

在 `algorithms_impl/build_all.sh` 的 GTI 构建部分：

```bash
# 修复 spdlog 头文件包含问题（构建时临时修复，不提交到 git）
if ! grep -q "stdout_color_sinks.h" include/n2/hnsw_build.h 2>/dev/null; then
    print_info "  Applying spdlog include fix..."
    sed -i '/#include "spdlog\/spdlog.h"/a #include "spdlog/sinks/stdout_color_sinks.h"' include/n2/hnsw_build.h
fi
```

## 版本要求

- 本地开发环境：spdlog 1.9.2+
- CI 环境：Ubuntu 22.04 默认的 `libspdlog-dev` (版本 1.9.2)
- 两个环境使用相同版本，确保一致性

## 优点

1. **不修改第三方源码**：保持 n2 子模块的原始状态
1. **自动化**：构建脚本自动处理，无需手动干预
1. **幂等性**：多次构建不会重复添加头文件
1. **兼容性好**：适用于 spdlog 1.9.x 及以上版本
