# SAGE PyPI发布准备验证工具使用指南

## 概述

SAGE PyPI发布准备验证工具提供了完整的PyPI发布前验证功能，确保代码已准备好发布到PyPI，并且用户在pip安装后能够正常使用SAGE的所有功能。

## 工具用途

⚠️ **重要说明**：这个工具不是用来验证现有SAGE安装，而是用来验证代码是否准备好发布到PyPI！

### 🎯 主要用途
- **发布前验证**：确保代码准备好发布到PyPI
- **用户体验测试**：模拟用户pip install过程
- **质量保证**：验证发布后用户能正常使用所有功能
- **CI/CD集成**：自动化发布前检查

### 🔍 验证内容
1. **构建验证**：wheel包能否正确构建
2. **安装模拟**：模拟用户pip install isage流程
3. **功能验证**：安装后所有核心功能正常
4. **工具验证**：命令行工具和开发工具可用
5. **示例验证**：示例代码能正常运行

## 功能特性

### 🚀 快速验证模式
- **用时**: 约10-15秒
- **测试内容**: 核心导入、基本功能、CLI可用性
- **适用场景**: 日常开发自检、快速确认核心功能、CI/CD流水线

### 🔬 完整验证模式  
- **用时**: 约3-5分钟
- **测试内容**: 完整的发布流程、示例代码、单元测试、开发工具
- **适用场景**: 正式发布前验证、全面质量检查、发布准备确认

## 使用方法

### 通过sage dev命令使用（推荐）

```bash
# 快速发布准备验证（推荐日常使用）
sage dev pypi validate --fast

# 完整发布准备验证  
sage dev pypi validate

# 跳过wheel构建（使用现有包）
sage dev pypi validate --fast --skip-wheel

# 指定测试目录并保留环境以便调试
sage dev pypi validate --test-dir /tmp/my_test --no-cleanup

# 显示详细输出
sage dev pypi validate --verbose
```

### 其他PyPI发布管理命令

```bash
# 构建wheel包
sage dev pypi build

# 检查现有wheel包状态
sage dev pypi check

# 清理构建文件
sage dev pypi clean

# 清理所有包的构建文件
sage dev pypi clean --all
```

### 直接运行脚本

```bash
# 快速发布准备验证
python test_pip_validate_fast.py --skip-wheel

# 完整发布准备验证
python test_pip_install_complete.py --skip-wheel
```

## 验证流程

### 快速验证流程
1. **环境设置** - 创建隔离的虚拟环境
2. **包构建** - 构建或查找wheel包  
3. **模拟安装** - 在虚拟环境中pip安装
4. **导入测试** - 验证核心模块导入
5. **功能测试** - 测试基本数据流
6. **CLI测试** - 验证命令行接口

### 完整验证流程
在快速验证基础上增加：
7. **命令行工具** - 测试sage命令可用性
8. **开发工具** - 验证sage dev功能
9. **示例执行** - 运行完整示例代码
10. **单元测试** - 执行核心单元测试

💡 **重要**：整个流程都在隔离环境中进行，不会影响您当前的SAGE安装！

## 输出说明

### 成功标识
- ✅ **通过**: 测试项目成功
- 🎉 **完成**: 整体验证通过

### 警告和错误
- ⚠️ **警告**: 部分功能不可用（通常可接受）
- ❌ **失败**: 关键功能失败（需要修复）

### 进度指示
- ⠋ **旋转**: 正在执行长时间操作
- 📊 **结果**: 显示测试结果汇总
- ⏱️ **时间**: 显示总耗时

## 故障排除

### 常见问题

1. **wheel包未找到**
   ```bash
   # 先构建包
   sage dev pypi build
   # 然后验证
   sage dev pypi validate --skip-wheel
   ```

2. **导入失败**
   - 检查SAGE包是否正确构建
   - 确认所有依赖包都已安装

3. **验证超时**
   ```bash
   # 使用快速模式
   sage dev pypi validate --fast
   ```

4. **环境问题**
   ```bash
   # 清理旧环境
   sage dev pypi clean --all
   # 重新验证
   sage dev pypi validate
   ```

### 调试模式

```bash
# 保留测试环境以便手动检查
sage dev pypi validate --no-cleanup --verbose

# 查看测试环境
ls /tmp/sage_*_test_*/
```

## 最佳实践

### 开发阶段
- 使用快速验证进行日常自检
- 在重要功能开发后运行验证
- 定期运行完整验证确保发布质量

### 发布前准备
- **必须**运行完整验证并通过所有测试
- 在不同Python版本上进行验证
- 清理所有构建文件后重新测试

### CI/CD集成
```yaml
# GitHub Actions示例
- name: PyPI发布准备验证
  run: |
    sage dev pypi build
    sage dev pypi validate --fast
```

### 发布时机确认
✅ 完整验证全部通过  
✅ 代码已合并到主分支  
✅ 版本号已正确更新  
✅ 文档已同步更新  
🚀 可以安全发布到PyPI

## 性能优化

### 加速技巧
1. 使用`--skip-wheel`跳过重复构建
2. 使用`--fast`模式进行快速验证  
3. 使用`--system-site-packages`共享系统包
4. 并行运行多个验证任务

### 资源使用
- **快速模式**: ~50MB磁盘空间，10秒
- **完整模式**: ~200MB磁盘空间，3-5分钟
- **虚拟环境**: 自动清理，无长期占用

## 版本兼容性

- **Python**: 3.8+
- **操作系统**: Linux, macOS, Windows  
- **依赖**: typer, rich, pathlib (标准库)

## 更新记录

- **v1.0**: 基础验证功能
- **v1.1**: 添加快速模式
- **v1.2**: 集成到sage dev命令
- **v1.3**: 优化安装进度显示

---

如有问题，请查看SAGE项目文档或提交Issue。