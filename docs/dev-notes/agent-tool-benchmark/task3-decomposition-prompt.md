# 任务3拆分提示词 - 给Claude Sonnet 4.5

## 背景信息

你正在参与 SAGE 框架的 Agent 工具选择 Benchmark 项目开发。目前：
- **任务1**（数据层）已完成：在 `packages/sage-benchmark/src/sage/data/` 下提供 `agent_tools`、`agent_benchmark` 等数据源与使用场景。
- **任务2**（Benchmark 框架）正在构建：在 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/` 提供配置、实验运行器、指标等。

接下来需要完成 **任务3：核心算法 & Runtime 能力建设**。该任务主要涉及 `packages/sage-libs`（L3）与 `packages/sage-middleware`（L4）层，目标是实现高性能的工具选择、层次化规划、时机判断等核心能力，为 Benchmark 提供可评估的被测系统，也可直接嵌入 SAGE Agent runtime。

## 现有框架概览

### L3 - `packages/sage-libs/src/sage/libs/agentic/`
```
agentic/
├── agents/
│   ├── runtime/agent.py          # AgentRuntime 主循环
│   ├── planning/llm_planner.py   # 现有 Planner（需增强）
│   ├── action/mcp_registry.py    # 工具注册表
│   └── profile/...
└── tools/
    └── ...
```

### L4 - `packages/sage-middleware/src/sage/middleware/operators/agentic/`
- `runtime.py`：将 `AgentRuntime` 封装成 Operator
- 目标：新增/增强 Tool Selection Operator、Planning Operator 等

### 任务3的总体目标
1. **高准确率工具选择**（≥95%）：实现关键词、嵌入、两阶段、层次化、自适应等策略
2. **复杂任务规划**（成功率≥90%）：支持 5-10 步显性 + 隐性任务、依赖关系解析
3. **时机判断**（F1≥0.93）：判断何时需要调用工具 vs 直接回复
4. **Runtime 集成**：可插拔地集成到 `AgentRuntime` 和 Middleware Operator 中
5. **对接 Benchmark**：提供稳定 API 供任务2的 benchmark runner 调用

## 需遵循的架构原则
- **层次隔离**：L3 不能向上依赖 L4，L4 只包装 L3 能力
- **可插拔设计**：工具选择器、规划器、时机判断器均应通过接口/抽象类注入
- **配置驱动**：支持 YAML/Dict 配置构造实例
- **性能可扩展**：能处理 1000+ 工具、复杂多轮规划，响应 <2s（参考目标）
- **可测试**：提供单元测试（L3）、集成测试（L3+L4）、性能/回归测试脚本

---

## 任务3：核心算法建设（需拆分）

请将任务3拆分成 **3 个可以并行执行的独立子任务**。每个子任务应专注于一个模块或能力面向：比如“工具选择策略库”、“层次化规划 & 时机判断”、“Runtime & Middleware 集成”，也可以按照你认为更合理的维度拆分，只要满足独立性和可交付性。

### 拆分原则
1. **模块边界清晰**：不同子任务修改的顶层目录/文件尽量不同（或仅通过接口对接）
2. **接口契约明确**：定义清晰的输入输出与抽象类，便于并行开发
3. **可独立测试**：每个子任务都有自己的测试目录与样例
4. **Benchmark 可调用**：各子任务需说明如何被任务2的 benchmark runner 调用
5. **扩展友好**：接口设计允许未来加入新算法或策略

### 输出格式要求

对于每个子任务，请提供：

#### 1. 子任务概述
- **子任务名称**
- **核心目标**（1-2句话）
- **独立性说明**（描述与其他子任务的接口和依赖界面）

#### 2. 详细规格

**2.1 目录结构**
```
完整目录树（包含文件名）。注明每个文件的职责。
```

**2.2 接口设计**
- 类/函数签名（Python 类型注解）
- 输入输出结构（dict / dataclass / pydantic / TypedDict）
- 配置加载方式（例如：`from_config(cls, config: dict)` 工厂方法）
- 与 `AgentRuntime`、Benchmark Runner 的集成点

**2.3 功能清单**
- 需要实现的核心算法（例如：`EmbeddingToolSelector`、`HierarchicalPlanner`）
- 算法步骤或流程图描述
- 性能/复杂度要求（如：Top-K 搜索 O(log N)）

**2.4 数据与依赖**
- 使用的数据来源（引用任务1中的数据接口，如 `AgentToolsDataLoader`）
- 依赖的内部工具（如向量化模型、索引结构）
- 是否需要新增第三方依赖（如需，必须注明理由与版本）

**2.5 测试与验证**
- 单元测试范围（模块级）
- 集成测试策略（如：结合 middleware operator）
- 基准测试/性能测试（如果适用）
- 验收标准（定量指标 + 通过条件）

#### 3. 实施指导

**3.1 开发步骤建议**
- Step 1/2/3… 的开发顺序建议

**3.2 技术要点**
- 需要注意的算法细节（如相似度计算、Top-K剪枝、依赖图拓扑排序）
- 错误处理和异常路径
- 调试建议

**3.3 示例代码片段**
- 关键接口示例（如：`ToolSelector.select()` 的伪代码）
- Planner 与 ToolSelector 协作示例

#### 4. 交付清单
- [ ] 核心源文件列表
- [ ] 配置样例（如 YAML/JSON）
- [ ] 单元/集成测试文件
- [ ] 性能或对照评估脚本（若适用）
- [ ] 文档（README / 开发笔记 / API 文档）
- [ ] Demo/运行脚本（可选）

---

## 参考资料

1. **现有 Planner**：`packages/sage-libs/src/sage/libs/agentic/agents/planning/llm_planner.py`
   - 了解现有 prompt 构造、top-k 工具过滤、JSON 修复逻辑
2. **AgentRuntime**：`packages/sage-libs/src/sage/libs/agentic/agents/runtime/agent.py`
   - 看清如何注入 planner、tools、summarizer
3. **Middleware Operator**：`packages/sage-middleware/src/sage/middleware/operators/agentic/runtime.py`
   - 确保新能力可通过 Operator 暴露
4. **Benchmark Runner（任务2）**：将调用 Task3 提供的 API，请设计适配层

---

## 约束条件
1. **语言**：Python 3.10+
2. **依赖**：除非绝对必要，不新增第三方依赖；如需引入，请在方案中说明
3. **向量模型**：若需嵌入/相似度，优先复用现有 `sage.libs.embedding` 或 `sage.middleware.operators.rag.generator`
4. **配置体系**：支持从 dict/YAML 构造，遵循 SAGE config 约定
5. **日志与监控**：使用 `sage.common.utils.logging`；如需度量指标，可挂钩 benchmark 统计
6. **文档**：在 `docs/` 或 `README.md` 中提供使用说明，面向内部开发者
7. **质量门槛**：PR 前必须通过 `pytest packages/sage-libs/tests/lib/agents/...` 相关测试

---

## 期望输出格式

```
### 子任务1: [名称]
1. 概述
2. 详细规格（目录结构、接口设计、功能清单、数据依赖、测试）
3. 实施指导
4. 交付清单

### 子任务2: [名称]
...（同上）

### 子任务3: [名称]
...（同上）

### 并行开发建议
- 分支策略
- 合并顺序
- 集成测试计划
```

---

## 评估标准
1. ✅ **独立性**：三个子任务文件边界清晰，可并行开发
2. ✅ **完整性**：覆盖工具选择、规划/时机、runtime 集成等核心需求
3. ✅ **可执行性**：开发者凭拆分方案即可开工
4. ✅ **性能/准确率目标**：明确各子任务需达到的指标或基准
5. ✅ **测试闭环**：每个子任务都定义了足够的测试与验收标准

开始输出你的拆分方案吧！
