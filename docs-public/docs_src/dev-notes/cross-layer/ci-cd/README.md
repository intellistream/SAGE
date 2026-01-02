# CI/CD Documentation

**Date**: 2025-11-29\
**Author**: SAGE Team\
**Summary**: CI/CD pipeline fixes, build issues, and deployment notes for the SAGE project

This directory contains documentation for CI/CD pipeline fixes, build issues, and deployment notes.

## Overview

Documentation of continuous integration and continuous deployment issues, fixes, and improvements
for the SAGE project.

## Documents

### Core CI/CD Guides

- **[CICD_MIGRATION_TO_SAGE_DEV.md](CICD_MIGRATION_TO_SAGE_DEV.md)** - CI/CD 迁移到 sage-dev 命令
- **[VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md)** - 版本管理策略
- **[CODECOV_SETUP_GUIDE.md](CODECOV_SETUP_GUIDE.md)** - Codecov 设置指南
- **[DEV_INFRASTRUCTURE_SETUP.md](DEV_INFRASTRUCTURE_SETUP.md)** - 开发基础设施设置

### Build & Quality

- **[FIX_LIBSTDCXX_CI_869.md](FIX_LIBSTDCXX_CI_869.md)** - Fix for libstdc++ CI issue #869
- **[CODE_QUALITY_GUIDE.md](CODE_QUALITY_GUIDE.md)** - 代码质量指南
- **[PRE_COMMIT_TROUBLESHOOTING.md](PRE_COMMIT_TROUBLESHOOTING.md)** - Pre-commit 故障排除
- **[QUALITY_CHECK_INCONSISTENCY_ISSUE.md](QUALITY_CHECK_INCONSISTENCY_ISSUE.md)** - 质量检查一致性问题

### Documentation Management

- **[DOCUMENTATION_MAINTENANCE_QUICKREF.md](DOCUMENTATION_MAINTENANCE_QUICKREF.md)** - 文档维护快速参考
- **[DOCUMENTATION_CHECK_REPORT.md](DOCUMENTATION_CHECK_REPORT.md)** - 文档检查报告
- **[PACKAGE_README_GUIDELINES.md](PACKAGE_README_GUIDELINES.md)** - 包 README 指南

### Git & Submodules

- **[GIT_SUBMODULE_OPTIMIZATION.md](GIT_SUBMODULE_OPTIMIZATION.md)** - Git Submodule 优化

## Common CI/CD Topics

1. **Build Issues**: Compilation errors, dependency issues
1. **Test Failures**: Test environment issues, flaky tests
1. **Deployment**: Deployment scripts and configurations
1. **Pipeline Optimization**: CI/CD performance improvements

## Related Documentation

- [GitHub Workflows](../../../../../.github/workflows/) - CI/CD 工作流定义
- [Cross-Layer README](../README.md) - 跨层级文档索引
- [Main Dev Notes](../../../README.md) - 开发文档主索引

## See Also

- [Copilot Instructions](../../../../../.github/copilot-instructions.md) - 包含 CI/CD 使用说明
