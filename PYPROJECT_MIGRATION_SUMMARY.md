# SAGE Monorepo pyproject.toml 迁移总结

## 🔄 迁移概述

根据新的三层架构重构了根目录的 `pyproject.toml` 配置文件，以匹配新的包结构。

## 📦 新的包结构

### 开源包
- **sage-kernel**: 统一内核层 (原 sage-core + sage-utils + sage-kernel-*)
- **sage-middleware**: 中间件层 (LLM服务、数据库、内存管理)
- **sage-userspace**: 用户空间层 (原 sage-lib + sage-plugins)
- **sage-cli**: 命令行工具包

### 商业版包
- **sage-kernel-commercial**: 企业级内核扩展
- **sage-middleware-commercial**: 企业级中间件扩展  
- **sage-userspace-commercial**: 企业级用户空间扩展

## 🎯 主要变更

### 1. 安装选项重新设计
```toml
# 基础安装选项
minimal = ["sage-kernel"]                                     # 仅内核
core = ["sage-kernel", "sage-middleware"]                    # 内核 + 中间件
standard = ["sage-kernel", "sage-middleware", "sage-userspace"]  # 完整开源版

# 商业化安装选项
community = ["sage-kernel", "sage-middleware", "sage-userspace"]
professional = [..., "sage-kernel-commercial", "sage-middleware-commercial"]
enterprise = [...全部包...]
```

### 2. 工具配置路径更新
- **isort**: 更新 `src_paths` 指向新的包目录
- **mypy**: 更新 `mypy_path` 指向新的源码目录
- **pytest**: 更新 `testpaths` 指向新的测试目录

### 3. 项目描述优化
- 更新了项目描述以反映三层架构
- 添加了新的关键词 (`kernel`, `middleware`, `userspace`)
- 增加了架构说明注释

## 📋 安装示例

```bash
# 最小安装 - 仅内核功能
pip install sage-workspace[minimal]

# 核心安装 - 内核 + 中间件
pip install sage-workspace[core]

# 标准安装 - 完整开源版
pip install sage-workspace[standard]

# 社区版 (与standard相同)
pip install sage-workspace[community]

# 完整版 - 包含CLI工具
pip install sage-workspace[full]

# 专业版 - 包含部分商业组件
pip install sage-workspace[professional]

# 企业版 - 包含所有商业组件 (需要许可)
pip install sage-workspace[enterprise]
```

## ✅ 验证完成

- [x] TOML语法正确性验证通过
- [x] 包依赖关系与实际包结构匹配
- [x] 工具配置路径正确更新
- [x] 商业化策略选项完整

## 🔄 后续步骤

1. 测试各安装选项是否正常工作
2. 验证CI/CD流程是否需要相应调整
3. 更新相关文档和安装指南
4. 考虑添加包版本约束以确保兼容性

---
*迁移完成时间: 2025-08-04*
*新架构: Kernel → Middleware → Userspace*
