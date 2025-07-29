# SAGE CI/CD 测试策略 (更新版)

## 概述

SAGE 使用统一的 `install.py` 脚本进行安装，CI/CD 直接使用 `install.py --minimal` 进行最小化安装和测试。

## 安装架构

### 1. Minimal Setup (`install.py --minimal`)
**用途**: 快速开发和测试
**特点**:
- ✅ 纯 Python 安装，**不编译任何 C++ 扩展**
- ✅ 使用 Ray 队列后端
- ✅ 在 CI 中自动跳过用户交互
- ✅ 快速安装，适合开发和测试

### 2. Full Setup (`install.py --full`) 
**用途**: 生产环境部署
**特点**:
- ✅ Docker 容器化安装
- ✅ **完整的 C++ 扩展编译** (sage_db, sage_queue)
- ✅ 使用 SAGE 队列后端
- ✅ 包含所有高性能组件

## 清晰的分工

| 特性 | Minimal Setup | Full Setup |
|------|---------------|------------|
| 安装速度 | 🚀 快速 (5-10分钟) | 🐌 较慢 (20-30分钟) |
| C++ 扩展 | ❌ 无 | ✅ 完整 |
| Docker 需求 | ❌ 不需要 | ✅ 必需 |
| 队列后端 | Ray | SAGE (高性能) |
| 适用场景 | 开发/测试/CI | 生产/性能测试 |

## CI/CD 流程

### GitHub Actions 配置
```yaml
# 直接使用官方安装脚本
- name: Install SAGE (Minimal Mode)
  run: python install.py --minimal

# 测试基本功能
- name: Run Basic Tests  
  run: |
    eval "$(conda shell.bash hook)"
    conda activate sage
    python -c "import sage; print('✅ SAGE ready')"
```

### 环境变量控制
- `CI=true` - 自动检测 CI 环境，跳过交互
- `SAGE_SKIP_CPP_EXTENSIONS=true` - 明确跳过 C++ 扩展（在 minimal_setup 中已默认）

## 测试工作流

### 1. 开发阶段
```bash
# 本地快速测试 (跳过 C++ 编译)
export SAGE_SKIP_CPP_EXTENSIONS=true
python install.py --minimal

# 代码质量检查
black sage/
isort sage/
flake8 sage/
```

### 2. 提交前验证
```bash
# 运行完整本地集成测试
./scripts/local_integration_test.sh

# 检查测试报告
cat test_results/integration_test_report.md
```

### 3. 推送到 GitHub
- GitHub Actions 自动运行 CI 测试
- 检查 CI 状态和 Docker 测试提醒
- 如果 CI 通过，代码质量符合要求

### 4. 发布前验证  
```bash
# 完整 Docker 测试
python install.py --docker --full

# 性能回归测试
python scripts/performance_test.py --full
```

## 测试覆盖范围

### GitHub Actions 覆盖
| 组件 | 状态 | 说明 |
|------|------|------|
| sage.core | ✅ 完全覆盖 | Python 核心功能 |
| sage.lib | ✅ 完全覆盖 | Python 库功能 |
| sage.cli | ✅ 完全覆盖 | 命令行工具 |
| sage.utils (Ray 后端) | ✅ 完全覆盖 | 使用 Ray 队列 |
| sage_ext.sage_db | ❌ 跳过 | C++ 扩展 |
| sage_ext.sage_queue | ❌ 跳过 | C++ 扩展 |

### 本地集成测试覆盖
| 组件 | 状态 | 说明 |
|------|------|------|
| 所有 Python 组件 | ✅ 完全覆盖 | 包含 CI 的所有测试 |
| sage_ext.sage_db | ✅ 完全覆盖 | Docker 内编译和测试 |
| sage_ext.sage_queue | ✅ 完全覆盖 | Docker 内编译和测试 |
| 跨后端切换 | ✅ 完全覆盖 | Ray ↔ Sage 切换测试 |
| 性能基准 | ✅ 完全覆盖 | 端到端性能验证 |

## 故障排查

### CI 测试失败
1. **Python 语法错误**: 运行 `black` 和 `flake8` 修复
2. **导入错误**: 检查 Python 依赖和模块结构
3. **Ray 后端问题**: 验证 Ray 安装和配置

### 本地集成测试失败
1. **C++ 编译失败**: 
   ```bash
   # 单独测试每个扩展
   cd sage_ext/sage_db && ./build.sh --debug
   cd sage_ext/sage_queue && ./build.sh --debug
   ```

2. **Docker 问题**:
   ```bash
   # 重建 Docker 环境
   python install.py --docker --clean --full
   ```

3. **性能回归**:
   ```bash
   # 对比性能基准
   python scripts/performance_test.py --compare-baseline
   ```

## 最佳实践

### 开发者工作流
1. **日常开发**: 使用 minimal 模式进行快速迭代
2. **功能测试**: 定期运行本地集成测试
3. **提交代码**: 确保 CI 通过且本地集成测试通过
4. **发布准备**: 运行完整的 Docker 和性能测试

### CI/CD 维护
1. **定期更新**: 保持 CI 环境与开发环境同步
2. **监控性能**: 跟踪 CI 执行时间，优化测试效率
3. **文档维护**: 更新测试策略文档，保持与实际流程一致

## 未来改进

### 可能的增强
1. **部分 C++ 测试**: 研究在 CI 中进行轻量级 C++ 编译测试
2. **Docker 镜像缓存**: 优化 Docker 构建速度
3. **并行测试**: 进一步优化测试执行时间
4. **自动性能监控**: 集成性能回归检测
