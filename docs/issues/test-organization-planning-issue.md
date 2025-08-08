# Issue: 完善 packages 目录中各包的测试组织架构

## 问题描述

当前 SAGE 项目中 `packages/` 目录包含多个核心包（sage-kernel、sage-middleware、sage-userspace、tools等），但测试覆盖不够完整和系统化。为了确保代码质量和可靠性，需要建立完善的测试组织架构，对每个文件（类）和接口都有相应的单元测试。

## 现状分析

### 当前包结构
```
packages/
├── sage-kernel/           # 核心内核包
│   ├── src/sage/
│   │   ├── core/         # 核心功能
│   │   ├── runtime/      # 运行时
│   │   ├── utils/        # 工具函数
│   │   └── cli/          # 命令行接口
│   └── tests/            # 部分测试覆盖
├── sage-middleware/       # 中间件包
│   ├── src/sage/
│   │   ├── llm/          # LLM相关
│   │   └── service/      # 服务层
│   └── tests/            # 测试覆盖不完整
├── sage-userspace/       # 用户空间包
│   ├── src/sage/
│   │   ├── lib/          # 库函数
│   │   ├── plugins/      # 插件系统
│   │   └── userspace/    # 用户空间功能
│   └── tests/            # 测试覆盖不完整
├── commercial/           # 商业版本
└── tools/               # 工具包
    ├── sage-cli/        # CLI工具
    └── sage-frontend/   # 前端工具
```

### 测试覆盖现状
1. **sage-kernel**: 有部分测试，但不够系统化
2. **sage-middleware**: 测试覆盖度低
3. **sage-userspace**: 测试覆盖度低
4. **tools**: 缺乏测试

## 目标和要求

### 1. 测试组织原则
- **每个源文件都有对应的测试文件**
- **每个公共类和方法都有单元测试**
- **每个公共接口都有集成测试**
- **测试结构与源码结构保持一致**

### 2. 测试命名规范
```
src/sage/core/pipeline.py           → tests/core/test_pipeline.py
src/sage/core/api/environment.py    → tests/core/api/test_environment.py
src/sage/llm/service/embedding.py   → tests/llm/service/test_embedding.py
```

### 3. 测试分类标记
- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.slow`: 耗时测试
- `@pytest.mark.external`: 需要外部依赖的测试

## 实施计划

### Phase 1: 基础架构完善（Week 1-2）
1. **统一测试配置**
   - 为每个包完善 `pyproject.toml` 中的测试配置
   - 统一 pytest 配置和标记系统
   - 配置代码覆盖率报告

2. **建立测试模板**
   - 创建单元测试模板
   - 创建集成测试模板
   - 创建 Mock 和 Fixture 的标准模式

### Phase 2: sage-kernel 测试完善（Week 3-4）
1. **核心模块测试**
   - `src/sage/core/`: 管道、算子、函数测试
   - `src/sage/runtime/`: 运行时环境测试
   - `src/sage/utils/`: 工具函数测试
   - `src/sage/cli/`: CLI命令测试

2. **目标测试文件**
   ```
   tests/
   ├── core/
   │   ├── test_pipeline.py
   │   ├── api/
   │   │   ├── test_environment.py
   │   │   └── test_remote_environment.py
   │   ├── function/
   │   │   ├── test_comap_function.py
   │   │   ├── test_sink_function.py
   │   │   └── test_source_function.py
   │   ├── operator/
   │   │   └── test_operators.py
   │   └── service/
   │       └── test_service_registry.py
   ├── runtime/
   │   ├── test_ray_runtime.py
   │   └── test_local_runtime.py
   ├── utils/
   │   ├── test_config.py
   │   ├── test_logging.py
   │   └── test_serialization.py
   └── cli/
       ├── test_main.py
       ├── test_setup.py
       └── test_head_manager.py
   ```

### Phase 3: sage-middleware 测试完善（Week 5-6）
1. **LLM模块测试**
   - 嵌入模型测试
   - 推理引擎测试
   - 模型管理测试

2. **服务层测试**
   - 服务注册和发现
   - 服务调用和通信
   - 服务生命周期管理

### Phase 4: sage-userspace 测试完善（Week 7-8）
1. **库函数测试**
   - 数据处理函数
   - 工具类函数
   - 算法实现

2. **插件系统测试**
   - 插件加载和卸载
   - 插件接口兼容性
   - 插件生命周期管理

### Phase 5: tools 包测试完善（Week 9-10）
1. **CLI工具测试**
   - 命令解析测试
   - 参数验证测试
   - 输出格式测试

2. **前端工具测试**
   - API接口测试
   - 用户界面测试
   - 数据交互测试

## 测试质量要求

### 1. 代码覆盖率目标
- **单元测试覆盖率**: ≥ 80%
- **集成测试覆盖率**: ≥ 60%
- **关键路径覆盖率**: = 100%

### 2. 测试质量标准
- 每个测试函数只测试一个功能点
- 测试用例包含正常情况、边界情况和异常情况
- 使用合适的 Mock 和 Fixture 减少测试依赖
- 测试名称清晰描述测试目的

### 3. 性能测试要求
- 单元测试执行时间 < 1秒
- 集成测试执行时间 < 10秒
- 使用 `@pytest.mark.slow` 标记耗时测试

## 自动化和CI/CD集成

### 1. 预提交钩子
- 运行快速单元测试
- 代码格式检查
- 类型检查

### 2. CI管道
- 完整测试套件执行
- 代码覆盖率报告
- 测试结果通知

### 3. 测试报告
- 每日测试报告
- 覆盖率趋势监控
- 失败测试分析

## 工具和依赖

### 测试框架
- `pytest`: 主要测试框架
- `pytest-cov`: 代码覆盖率
- `pytest-asyncio`: 异步测试支持
- `pytest-mock`: Mock支持

### 测试工具
- `black`: 代码格式化
- `mypy`: 类型检查
- `ruff`: 代码检查

## 预期收益

1. **提高代码质量**: 通过全面测试发现和修复潜在问题
2. **增强开发信心**: 重构和修改时有测试保障
3. **改善文档**: 测试用例作为代码使用示例
4. **加速开发**: 自动化测试减少手动验证时间
5. **降低维护成本**: 早期发现问题，减少生产环境故障

## 成功指标

- [ ] 所有包都有完整的测试结构
- [ ] 代码覆盖率达到目标值
- [ ] CI/CD管道集成测试
- [ ] 开发团队采用测试驱动开发实践
- [ ] 生产环境缺陷数量下降

## 负责人和时间线

- **项目负责人**: 待分配
- **开发团队**: 全体开发人员参与
- **总时间**: 10周
- **里程碑检查**: 每2周一次进度回顾

---

**优先级**: 高
**估算工作量**: 10周
**影响范围**: 全部packages
**风险评估**: 中等（需要团队配合和时间投入）
