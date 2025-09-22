# SAGE Issues Manager 测试套件

本目录包含了针对 SAGE Issues Manager 的完整测试套件，确保所有功能都能正常工作。

## � 快速开始 (推荐使用 Makefile)

### 1. 快速验证 (开发时推荐)
```bash
make test          # 或 make quick-test
```

### 2. 完整测试 (发布前推荐)  
```bash
make full-test
```

### 3. 查看所有可用命令
```bash
make help
```

### 4. 清理测试产物
```bash
make clean
```

## �📋 测试脚本概览

### 1. 完整自动化测试 (`test_issues_manager.sh`)

**用途**: 全面测试所有功能模块，适合开发和部署前的完整验证

**特性**:
- ✅ 测试所有核心功能模块
- 🧹 自动备份和恢复原有数据
- 📊 生成详细测试报告
- 🛡️ 异常退出时自动清理
- ⏱️ 预计运行时间: 2-5分钟

**使用方法**:
```bash
# 使用Makefile (推荐)
make full-test

# 直接运行脚本
cd tools/issues-management
./test_issues_manager.sh
```

### 2. 快速验证测试 (`quick_test.sh`)

**用途**: 快速检查核心功能，适合CI/CD或开发过程中的快速验证

**特性**:
- ⚡ 30秒内完成
- 🔍 检查关键文件和语法
- 📦 验证依赖可用性
- 🎯 专注核心功能

**使用方法**:
```bash
# 使用Makefile (推荐)
make test

# 直接运行脚本
cd tools/issues-management  
./quick_test.sh
```

## 🧪 测试覆盖范围

### 完整测试覆盖的功能模块

| 模块 | 测试内容 | 说明 |
|------|----------|------|
| **目录结构** | 目录存在性、权限检查 | 验证工作环境 |
| **Python脚本** | 语法检查、导入测试 | 确保代码质量 |
| **配置功能** | 路径获取、配置管理 | 验证配置系统 |
| **Metadata管理** | 团队配置、项目信息 | 测试元数据处理 |
| **Issues管理** | 统计、历史记录 | 验证Issues操作 |
| **AI分析** | Copilot格式化、时间过滤 | 测试AI助手功能 |
| **智能分配** | 预览、执行分配 | 验证自动分配 |
| **下载功能** | 参数解析、脚本结构 | 检查下载逻辑 |
| **同步功能** | 预览模式、项目同步 | 验证上传逻辑 |
| **主脚本** | 语法、函数定义 | 确保主程序完整 |

### 快速测试覆盖的检查点

- ✅ 核心文件存在性和权限
- ✅ Python脚本语法正确性  
- ✅ 基础功能可用性
- ✅ 依赖环境完整性

## 🛠️ 测试环境要求

### 必需依赖
- Python 3.8+
- Bash 4.0+
- 基础Unix工具 (grep, find, wc等)

### 可选依赖
- GitHub Token (用于API功能测试)
- 网络连接 (用于远程功能测试)

## 📊 测试报告

### 完整测试报告
完整测试会生成详细报告，包含：
- 📈 测试统计信息
- 🔍 每个测试的详细结果
- 🌍 环境信息
- 📁 文件结构信息
- 💡 失败原因分析

报告位置: `test_results_YYYYMMDD_HHMMSS.log`

### 快速测试输出
快速测试提供实时反馈：
```
⚡ SAGE Issues Manager 快速测试
==============================

📁 检查核心文件...
🧪 主脚本存在 ... ✅
🧪 主脚本可执行 ... ✅
🧪 主脚本语法正确 ... ✅

🐍 检查Python脚本...
🧪 get_paths.py ... ✅
🧪 copilot_issue_formatter.py ... ✅

📊 测试结果
============
运行测试: 15
通过测试: 15
成功率: 100%
🎉 所有快速测试通过！
```

## 🔧 高级用法

### 在CI/CD中使用

```yaml
# GitHub Actions 示例
- name: Quick Test Issues Manager
  run: |
    cd tools/issues-management
    ./quick_test.sh

- name: Full Test Issues Manager  
  run: |
    cd tools/issues-management
    ./test_issues_manager.sh
```

### 开发过程中的测试流程

1. **日常开发**: 使用 `quick_test.sh` 快速验证
2. **功能完成**: 使用 `test_issues_manager.sh` 全面测试
3. **发布前**: 运行完整测试并检查报告

### 故障排除

**常见问题**:

1. **Python模块缺失**
   ```bash
   pip install -r requirements.txt
   ```

2. **权限问题**
   ```bash
   chmod +x *.sh
   ```

3. **路径配置问题**
   - 检查 `_scripts/helpers/get_paths.py`
   - 验证配置文件格式

## 📝 测试数据说明

### 自动生成的测试数据
测试脚本会自动创建以下测试数据：

**测试Issues**:
- `open_test_1001.md` - Kernel团队的增强请求
- `open_test_1002.md` - Middleware团队的Bug  
- `closed_test_1003.md` - Apps团队的文档Issue

**测试Metadata**:
- `boards_metadata.json` - 项目板配置
- `team_config.py` - 团队成员配置

### 数据安全保证
- 🛡️ 所有原始数据都会自动备份
- 🧹 测试完成后自动清理测试产物
- 🔄 异常退出时自动恢复原始状态

## 🚀 最佳实践

### 开发阶段
1. 每次提交前运行快速测试
2. 功能模块完成后运行完整测试
3. 关注测试报告中的警告信息

### 部署阶段  
1. 在目标环境运行完整测试
2. 验证所有依赖都已正确安装
3. 检查GitHub Token配置

### 维护阶段
1. 定期运行测试确保功能正常
2. 更新测试用例覆盖新功能
3. 监控测试成功率变化

## 🤝 贡献测试用例

如果您添加了新功能，请相应更新测试脚本：

1. 在 `test_issues_manager.sh` 中添加新的测试函数
2. 更新 `quick_test.sh` 包含关键检查点
3. 更新本README文档说明新的测试覆盖

---

**💡 提示**: 测试脚本设计遵循"fail-fast"原则，遇到关键错误时会立即停止并提供详细的错误信息。
