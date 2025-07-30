# SAGE 安装架构总结

## 🎯 核心原则：简洁分离

SAGE 提供两种清晰分离的安装模式，各自专注于特定的使用场景。

## 📦 安装模式

### 模式一：Minimal Setup
```bash
python install.py --minimal
```

**特点**：
- ✅ **纯 Python** - 不编译任何 C++ 扩展
- ✅ **快速安装** - 5-10 分钟完成
- ✅ **无 Docker 依赖** - 只需要 conda
- ✅ **Ray 后端** - 使用 Ray 作为队列实现
- ✅ **CI 友好** - 适合自动化测试

**适用场景**：
- 🧪 **开发和测试**
- 🚀 **CI/CD 流水线**
- 📚 **快速原型和学习**
- 💻 **开发环境搭建**

### 模式二：Full Setup  
```bash
python install.py --full
```

**特点**：
- ✅ **完整 C++ 扩展** - sage_db, sage_queue 等
- ✅ **Docker 容器化** - 统一的运行环境
- ✅ **高性能队列** - SAGE 原生队列实现
- ✅ **生产就绪** - 所有优化组件

**适用场景**：
- 🏭 **生产环境部署**
- ⚡ **性能关键应用**
- 📊 **大规模数据处理**
- 🔬 **完整功能验证**

## 🔄 开发工作流

### 日常开发
```bash
# 快速开始
make install-minimal
make test-ci

# 开发测试
python -c "import sage; print('Ready!')"
```

### 发布前验证
```bash
# 完整测试
make install-full
make test-local

# 性能验证
python install.py --full
./scripts/local_integration_test.sh
```

## 🚦 CI/CD 策略

### GitHub Actions
- **使用**: `python install.py --minimal`
- **测试**: Python 核心功能 + Ray 后端
- **速度**: 快速反馈（~10 分钟）

### 本地集成测试
- **使用**: `python install.py --full`
- **测试**: 完整 C++ 扩展 + Docker 集成
- **完整性**: 生产环境模拟

## 💡 关键优势

1. **清晰分离** - 两种模式职责明确，不混淆
2. **统一接口** - 都通过 `install.py` 安装
3. **适应性强** - 适合不同的使用场景
4. **维护简单** - 减少配置复杂性

## 🚀 快速选择指南

**我应该用哪种模式？**

| 场景 | 推荐模式 | 原因 |
|------|----------|------|
| 学习 SAGE | Minimal | 快速上手，简单易用 |
| 开发新功能 | Minimal | 快速迭代，即时反馈 |
| 运行 CI 测试 | Minimal | 速度快，稳定性高 |
| 性能测试 | Full | 完整功能，真实性能 |
| 生产部署 | Full | 高性能，完整特性 |
| 功能验收 | Full | 端到端验证 |

这种设计确保了：**开发简单，部署强大** 🎯
