````markdown
⚠️ 目录已弃用（Deprecated）

本目录原先存放一些 CI/CD 诊断脚本，现已整合到统一入口：

This file has been deprecated. Please use tools/ci/ci.sh instead.
### `final_verification.sh` - 🎯 最终验证脚本 
全面验证SAGE构建系统的所有修复，确保GitHub Actions工作流能够正常运行。

**功能：**
- ✅ 验证关键文件存在
- ✅ 检查版本读取机制
- ✅ 验证子包结构完整性
- ✅ 确认移除了不需要的文件
- ✅ 检查pyproject.toml配置
- ✅ 验证GitHub Actions工作流语法
- ✅ 测试PyPI依赖替换逻辑
- ✅ 快速构建系统测试

### `test_actions_locally.sh` - 🧪 GitHub Actions本地模拟测试
增强的CI/CD测试工具，全面模拟GitHub Actions环境。

**功能：**
- 🔍 **依赖分析**: 检测file:路径依赖问题
- 🧪 **环境模拟**: 模拟CI环境变量和工作流
- 📦 **安装测试**: 验证子包安装顺序
- 📋 **语法检查**: 验证workflow YAML语法
- 💡 **修复建议**: 提供具体的CI改进方案

### `test_ci_install.sh` - ⚡ 轻量级CI验证工具
快速验证CI配置正确性，不进行耗时的实际安装。

**功能：**
- ⚡ **快速验证**: 检查workflow配置而非实际安装
- 🔧 **配置检查**: 验证CI workflow包含正确的安装步骤
- 📦 **结构验证**: 检查子包结构完整性
- 🚀 **性能优化**: 避免耗时的kernel安装测试

**使用方法：**
```bash
# 快速轻量级验证（推荐）
./tools/ci-cd/test_ci_install.sh

# 完整GitHub Actions模拟测试
./tools/ci-cd/test_actions_locally.sh
```

## 最近的CI修复

### 问题诊断
通过本地测试发现的关键问题：
1. **file:路径依赖**: pyproject.toml中的`file:./packages/package-name`在CI中不可用
2. **安装顺序**: 需要按正确顺序安装子包避免循环依赖
3. **版本提取**: 需要从pyproject.toml正确提取版本信息
4. **安装速度**: kernel包安装过慢，影响CI效率

### 解决方案
修改了GitHub Actions workflow：
```yaml
# 正确的CI安装顺序
pip install -e packages/sage-common     # 1. 基础工具
pip install -e packages/sage-kernel     # 2. 核心计算
pip install -e packages/sage-middleware # 3. API服务  
pip install -e packages/sage-libs       # 4. 应用示例
pip install -e .                        # 5. 主包
```

## 适用场景

- **开发前验证**: 在提交代码前验证构建流程
- **CI调试**: 诊断GitHub Actions构建问题
- **配置验证**: 验证pyproject.toml配置正确性
- **依赖分析**: 检查包依赖结构问题
- **快速检查**: 轻量级验证避免耗时测试

## 推荐工作流

1. **快速验证**: `./tools/ci-cd/test_ci_install.sh` (30秒)
2. **详细分析**: `./tools/ci-cd/test_actions_locally.sh` (如需深入诊断)
3. **修复问题**: 根据测试结果修复配置
4. **提交代码**: 确保验证通过后再推送
5. **CI验证**: 观察GitHub Actions运行结果

## 测试结果解读

### ✅ 成功标志
- CI workflow包含正确的安装步骤
- 子包结构完整
- quickstart.sh正常工作
- Workflow语法正确

### ⚠️ 警告标志
- 发现file:路径依赖（已在CI中修复）
- 部分功能可能需要进一步验证

### ❌ 错误标志
- CI workflow配置缺失
- 子包结构不完整
- YAML语法错误

## 性能优化

- ✅ **轻量级验证**: 避免耗时的实际安装
- ✅ **配置检查**: 专注于验证配置正确性
- ✅ **快速反馈**: 30秒内完成基础验证
- ✅ **智能分析**: 只在需要时进行深度测试

---

*这些工具帮助确保代码质量和部署的可靠性，同时优化了测试效率。*

````
