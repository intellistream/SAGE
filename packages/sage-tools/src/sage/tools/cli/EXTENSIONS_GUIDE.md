# SAGE 扩展管理系统

## 📋 概述

SAGE框架现在将C++扩展管理完全集成到CLI中，提供了优雅而强大的扩展管理体验。

## 🚀 使用方式

### 基础安装
```bash
# 标准Python包安装 - 适合大多数用户
pip install -e .

# 这会安装:
# ✅ SAGE核心框架
# ✅ 所有Python依赖
# ✅ CLI命令工具
# ✅ 基础扩展模块
```

### C++扩展管理
```bash
# 检查扩展状态
sage extensions status

# 安装所有扩展
sage extensions install

# 安装特定扩展
sage extensions install sage_db

# 查看扩展详细信息
sage extensions info

# 清理构建文件
sage extensions clean
```

## 🔧 支持的扩展

### sage_db  
- **描述**: 数据库接口扩展
- **特性**: 原生C++接口, 高性能查询, 内存优化
- **状态**: experimental
- **用途**: 加速数据存储和检索

## 💡 设计优势

### 用户体验
- **统一界面**: 所有功能通过`sage`命令访问
- **智能检测**: 自动发现项目结构和扩展
- **详细反馈**: 彩色输出和进度提示
- **故障处理**: 友好的错误信息和解决建议

### 开发者友好
- **模块化设计**: 每个扩展独立管理
- **构建灵活性**: 支持单独构建和强制重建
- **调试支持**: 详细的构建日志和错误信息

## 🎯 安装流程

### 标准用户流程
1. `pip install -e .` - 基础安装
2. `sage doctor` - 系统诊断
3. `sage extensions status` - 检查扩展
4. `sage extensions install` - 按需安装扩展

### 开发者流程
1. `pip install -e .` - 基础安装
2. `sage extensions clean` - 清理旧构建
3. `sage extensions install --force` - 强制重建
4. `sage extensions status` - 验证安装

## 🔄 与旧系统对比

| 方面 | 旧方式 | 新方式 |
|------|--------|--------|
| 接口 | 独立脚本 | 集成CLI |
| 发现 | 手动指定路径 | 自动检测 |
| 管理 | 一次性安装 | 精细化管理 |
| 体验 | 基础功能 | 丰富交互 |
| 维护 | 重复代码 | 统一架构 |

## 📁 文件组织

```
sage/
├── cli/
│   ├── main.py           # 主CLI入口
│   ├── extensions.py     # 扩展管理模块
│   └── ...              # 其他CLI模块
├── ...                  # 核心代码
sage_ext/                # C++扩展目录
├── sage_queue/          # 队列扩展
└── sage_db/             # 数据库扩展
```

## 🎉 总结

新的扩展管理系统实现了:
- ✅ **完全集成**: 扩展管理成为SAGE CLI的一部分
- ✅ **用户友好**: 直观的命令和丰富的反馈
- ✅ **开发便利**: 灵活的构建和管理选项
- ✅ **向后兼容**: 保留原有的quick_install.py作为备选方案
- ✅ **面向未来**: 可扩展的架构支持更多扩展类型

现在用户可以通过简单的`sage extensions`命令来管理所有C++扩展，真正实现了"一键管理"的目标！
