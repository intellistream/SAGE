# SAGE 已知问题追踪

> 最后更新：2025-01-10
>
> 分支：feature/package-restructuring-1032

## ✅ 已修复的问题

### 1. 包导出不完整
**问题**：许多包的 `__init__.py` 只导出版本号，缺少公共 API

**修复**：
- ✅ 更新了所有 8 个包的 `__init__.py`
- ✅ 正确导出所有公共模块和类

### 2. Embedding 命名不一致
**问题**：`mock_embedder` vs `mockembedder` 命名不统一

**修复**：
- ✅ 统一使用 `mockembedder`
- ✅ test_phase2_wrappers.py 测试通过

### 3. 旧导入路径
**问题**：部分代码使用 `sage.core.api` 等旧路径

**修复**：
- ✅ sage_refiner/adapter.py: `sage.core.api` → `sage.kernel.api`
- ✅ sage_refiner/examples/rag_integration.py: 同上
- ✅ sage_studio/pipeline_builder.py: `LocalStreamEnvironment` → `LocalEnvironment`

### 4. 缺失的 _version.py
**问题**：sage-benchmark 缺少 `_version.py` 文件

**修复**：
- ✅ 创建了 `packages/sage-benchmark/src/sage/benchmark/_version.py`

---

## ⚠️ 已知遗留问题

### 1. sage-studio 架构问题
**描述**：
- `adapters/__init__.py` 和 `nodes/builtin.py` 引用不存在的 `core.node_interface` 模块
- 这些模块无法正常导入

**影响**：
- sage-studio 无法完整导入
- 不影响其他 7 个核心包的功能

**临时解决方案**：
- 在 sage.studio.__init__.py 中不导出 adapters
- 需要时手动导入：`from sage.studio import adapters`

**推荐修复方案**：
1. 创建 `packages/sage-studio/src/sage/studio/core/` 目录
2. 实现 `node_interface.py` 模块，定义：
   - `NodeInterface` 基类
   - `NodeMetadata`, `NodeCategory` 等类型
   - `ExecutionContext`, `ExecutionResult` 等
   - `register_node` 装饰器
3. 或者重构 adapters 和 nodes，使用其他架构

**优先级**：低（不影响核心功能）

### 2. 依赖警告
**描述**：
- GitHub 报告 45 个依赖漏洞（3 critical, 9 high, 23 moderate, 10 low）

**影响**：
- 可能存在安全风险
- 需要更新依赖版本

**推荐修复**：
1. 运行 `pip list --outdated` 检查过时依赖
2. 更新关键依赖到最新安全版本
3. 运行完整测试套件验证兼容性

**优先级**：中（安全问题）

### 3. vLLM 导入警告
**描述**：
- 每次导入 sage.common 时出现 vLLM 警告
- `libcuda.so.1: cannot open shared object file`

**影响**：
- 仅警告信息，不影响功能
- 在没有 GPU 的环境中正常

**推荐修复**：
- 延迟加载 vLLM 组件
- 只在实际使用时导入

**优先级**：低（仅影响日志输出）

---

## 🔍 需要验证的问题

### 1. 完整测试套件
**待验证**：
```bash
# 运行所有包的测试
pytest packages/*/tests/ -v --tb=short

# 或使用 sage 命令
sage dev test-all
```

**期望结果**：
- 所有测试通过（除了 studio 的部分测试）
- 无导入错误

### 2. 示例程序运行
**待验证**：
```bash
# 运行 hello world
python examples/tutorials/hello_world.py

# 运行 RAG 示例
python examples/tutorials/rag/qa_local_llm.py

# 运行其他关键示例
bash tools/tests/run_examples_tests.sh
```

### 3. 循环依赖检查
**待验证**：
```bash
# 使用 pydeps 或类似工具检查
pip install pydeps
pydeps packages/sage-libs --max-bacon=2
pydeps packages/sage-middleware --max-bacon=2
```

---

## 📋 技术债务

### 1. 类型注解不完整
**描述**：
- 许多函数缺少类型注解
- 影响 IDE 自动完成和类型检查

**推荐**：
- 逐步添加类型注解
- 使用 mypy 进行类型检查

### 2. 文档字符串不统一
**描述**：
- 部分模块使用 Google 风格
- 部分使用 NumPy 风格
- 部分缺少文档

**推荐**：
- 统一使用 Google 风格
- 为所有公共 API 添加文档

### 3. 测试覆盖率未知
**描述**：
- 未生成测试覆盖率报告
- 不清楚哪些代码缺少测试

**推荐**：
```bash
pytest --cov=packages --cov-report=html
# 查看 htmlcov/index.html
```

---

## 🚀 后续优化建议

### 短期（1-2 周）

1. **修复 sage-studio 架构**
   - 创建 core.node_interface 模块
   - 或重构 adapters/nodes 架构

2. **更新依赖**
   - 修复安全漏洞
   - 更新到最新稳定版本

3. **完整测试**
   - 运行全部测试套件
   - 修复失败的测试

### 中期（1-2 月）

1. **类型注解**
   - 为核心 API 添加类型注解
   - 启用 mypy 检查

2. **文档改进**
   - 统一文档风格
   - 添加更多示例

3. **性能优化**
   - 分析包加载时间
   - 优化延迟导入

### 长期（3-6 月）

1. **API 稳定化**
   - 确定 1.0 API
   - 编写兼容性指南

2. **插件系统**
   - 设计扩展机制
   - 建立插件注册中心

3. **独立发布**
   - 准备 PyPI 发布
   - 建立版本管理策略

---

## 📊 问题统计

| 类别 | 已修复 | 遗留 | 待验证 | 技术债务 |
|------|--------|------|--------|----------|
| **包结构** | 4 | 1 | 0 | 0 |
| **导入路径** | 3 | 0 | 0 | 0 |
| **测试** | 1 | 0 | 3 | 1 |
| **文档** | 3 | 0 | 0 | 2 |
| **依赖** | 0 | 1 | 1 | 0 |
| **总计** | **11** | **2** | **4** | **3** |

---

## 🔗 相关文档

- [包架构](../PACKAGE_ARCHITECTURE.md) - 完整的包结构说明
- [重构总结](./PACKAGE_RESTRUCTURING_FINAL.md) - 重构完成总结
- [架构评审](./ARCHITECTURE_REVIEW_2025.md) - 问题分析和解决方案

---

**维护说明**：
- 修复问题后，请更新本文档
- 将已修复的问题移到"已修复"部分
- 添加修复日期和 commit hash
- 更新问题统计表格
