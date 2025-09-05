# SAGE Flow 代码质量和风格指南

本文档描述了SAGE Flow项目的代码质量工具和使用方法。

## 📋 概述

项目集成了以下代码质量工具：
- **clang-format**: 自动代码格式化
- **cpplint**: Google C++风格检查
- **clang-tidy**: 静态代码分析

## 🛠️ 可用工具

### CMake集成目标

配置项目后，可以使用以下make目标：

```bash
# 自动格式化所有源文件
make format

# 检查代码格式（不修改文件）
make format-check

# CI/CD格式检查（发现问题时失败）
make format-check-ci

# 运行cpplint检查（如果启用）
make cpplint
```

### 独立脚本

#### 代码风格检查脚本
```bash
# 运行完整的代码风格检查
./scripts/check_code_style.sh

# 批量添加版权信息
./scripts/add_copyright.sh
```

## ⚙️ 配置

### clang-format配置
- 配置文件: `.clang-format`
- 基于Google C++风格
- 行长度限制: 80字符
- 缩进: 2个空格

### cpplint配置
- 过滤规则在`cmake/Cpplint.cmake`中定义
- 默认过滤版权、包含顺序等检查

### clang-tidy配置
- 配置文件: `.clang-tidy`
- 基于Google C++风格指南

## 🚀 使用方法

### 1. 初始设置
```bash
# 克隆项目
git clone <repository>
cd sage-flow

# 配置构建
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release

# 可选：禁用clang-format集成
cmake .. -DSAGE_FLOW_ENABLE_CLANG_FORMAT=OFF
```

### 2. 代码开发流程

#### 新功能开发
```bash
# 编写代码
# ...

# 格式化代码
make format

# 检查格式
make format-check

# 运行风格检查
./scripts/check_code_style.sh
```

#### 提交代码前
```bash
# 确保所有检查通过
make format-check
./scripts/check_code_style.sh

# 如果有问题，自动修复
make format
./scripts/add_copyright.sh  # 如果需要添加版权
```

### 3. CI/CD集成

在CI/CD流水线中添加：

```yaml
# GitHub Actions示例
- name: Check code formatting
  run: |
    mkdir build && cd build
    cmake ..
    make format-check-ci

- name: Run cpplint
  run: ./scripts/check_code_style.sh
```

## 📝 代码风格规则

### 基本规则
- 使用Google C++风格指南
- 行长度不超过80字符
- 使用2个空格缩进
- 文件末尾必须有换行符

### 命名约定
- 类名: `CamelCase`
- 函数名: `camelBack`
- 变量名: `lower_case`
- 成员变量: `lower_case_` (带下划线)
- 常量: `kCamelCase`

### 文件结构
```cpp
/*
 * Copyright 2024 SAGE Flow Team
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * ...
 */

#pragma once

#include <memory>
#include <string>

namespace sage_flow {

class MyClass {
 public:
  explicit MyClass(std::shared_ptr<Dependency> dep)
      : dep_(std::move(dep)) {}

  auto Process() -> bool;

 private:
  std::shared_ptr<Dependency> dep_;
};

}  // namespace sage_flow
```

## 🔧 故障排除

### clang-format未找到
```bash
# Ubuntu/Debian
sudo apt-get install clang-format

# macOS
brew install clang-format

# 手动指定路径
export CLANG_FORMAT_EXE=/path/to/clang-format
```

### cpplint未找到
```bash
# 安装cpplint
pip install cpplint

# 或使用conda
conda install -c conda-forge cpplint
```

### 格式检查失败
```bash
# 查看具体问题
./scripts/check_code_style.sh

# 自动修复格式
make format

# 检查修复结果
make format-check
```

## 📚 相关链接

- [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html)
- [clang-format文档](https://clang.llvm.org/docs/ClangFormat.html)
- [cpplint文档](https://github.com/cpplint/cpplint)

## 🤝 贡献

提交代码前请确保：
1. 运行`make format`格式化代码
2. 通过`make format-check`检查
3. 通过`./scripts/check_code_style.sh`风格检查
4. 所有测试通过

---

*最后更新: 2024年*