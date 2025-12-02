# 任务2拆分提示词 - 给Claude Sonnet 4.5

## 背景信息

你正在参与SAGE框架的Agent工具选择Benchmark项目开发。SAGE是一个Python 3.10+的AI/LLM数据处理框架，采用严格的分层架构（L1-L6），其benchmark能力集中在 `packages/sage-benchmark/`。

任务1已经完成数据层建设（sources/usages）。现在需要在任务2中构建**Agent能力Benchmark框架**，以便针对「工具选择 / 复杂规划 / 时机判断」三大能力运行可重复的实验、输出指标和报告。

## 现有架构（参考）

```
packages/sage-benchmark/
├── README.md
├── pyproject.toml
└── src/
    └── sage/
        └── benchmark/
            ├── benchmark_rag/         # 已有 RAG benchmark
            │   ├── implementations/
            │   ├── evaluation/
            │   └── config/
            ├── benchmark_memory/
            ├── benchmark_libamm/
            └── ...
```

### 数据接入方式
- 数据层（任务1）已经在 `packages/sage-benchmark/src/sage/data/` 中建立：
  - `sources/agent_tools/`：工具库
  - `sources/agent_benchmark/`：测试数据
  - `usages/agent_eval/`：逻辑场景
- 本任务只需**通过 DataManager API 读取数据**，无需直接读写原始文件。

### 目标能力
1. **工具选择**：评估Agent从1000+工具中选择Top-K工具的准确率（目标≥95%）
2. **复杂规划**：评估多步任务（5-10步）规划成功率（目标≥90%）
3. **时机判断**：评估是否需要调用工具的F1（目标≥0.93）

---

## 任务2：Benchmark框架建设概述

**目标**：在 `packages/sage-benchmark/src/sage/benchmark/` 下新增 `benchmark_agent/` 模块，提供：
- 标准化实验配置（YAML）
- 实验运行器（工具选择 / 规划 / 时机判断）
- 评估指标与报告生成
- 基线方法实现（关键词、嵌入、随机等）
- 可插拔被测系统（未来接入任务3算法）

**预期目录结构（草案）**：
```
packages/sage-benchmark/src/sage/benchmark/
└── benchmark_agent/
    ├── __init__.py
    ├── README.md
    ├── config/
    │   ├── default_config.yaml
    │   ├── tool_selection_exp.yaml
    │   ├── planning_exp.yaml
    │   └── timing_detection_exp.yaml
    ├── evaluation/
    │   ├── metrics.py
    │   ├── evaluator.py
    │   └── analyzers/
    │       ├── tool_selection_analyzer.py
    │       ├── planning_analyzer.py
    │       └── timing_analyzer.py
    ├── experiments/
    │   ├── base_experiment.py
    │   ├── tool_selection_exp.py
    │   ├── planning_exp.py
    │   └── timing_detection_exp.py
    └── implementations/
        ├── baseline_selector.py
        ├── embedding_selector.py
        └── random_selector.py
```

> 注意：以上目录仅供参考，拆分任务时可进一步细化或调整，但需说明理由。

---

## 拆分要求

请将**任务2（Benchmark框架建设）**拆分成**3个可以完全并行执行的独立子任务**。

### 拆分原则
1. **完全独立**：每个子任务的代码文件夹互不重叠，可在不同分支并行开发
2. **接口清晰**：子任务之间通过明确的接口/配置对接（例如：实验runner依赖metrics接口）
3. **可独立测试**：每个子任务都能编写自己的单元测试，使用mock数据即可
4. **可独立交付**：子任务完成后可以单独merge，且不会阻塞其他子任务
5. **架构合规**：遵循SAGE分层架构和benchmark模块约定

### 输出格式要求

对于每个子任务，请提供：

#### 1. 子任务概述
- **子任务名称**
- **核心目标**（1-2句话）
- **独立性说明**（说明与其他子任务的接口）

#### 2. 详细规格

**2.1 目录结构**
```
给出完整目录树（包含文件名）。标注每个文件的作用。
```

**2.2 接口与数据流**
- 关键类/函数的接口签名
- 输入/输出数据结构（以Python字典或pydantic模型描述）
- 配置文件（YAML）示例

**2.3 代码实现清单**
- 需要实现的类、函数、脚本一览
- 每个元素的职责与依赖

**2.4 集成方式**
- 如何被其他子任务调用（如：实验runner调用metrics）
- 如何访问DataManager（示例代码）
- 可插拔策略（例如被测系统Adapter接口）

**2.5 验证标准**
- 单元测试清单（覆盖点、mock策略）
- 功能验证步骤（可使用小型假数据）
- 性能或可扩展性要求（如并发、批量评估）

#### 3. 实施指导

**3.1 开发顺序建议**
- 任务内的Recommended步骤（Step 1/2/3...）

**3.2 技术要点**
- 关键技术难点（如：指标统计、配置加载、报告输出）
- 复用现有组件的建议（例如借鉴benchmark_rag模块的模式）

**3.3 示例代码片段**
- 提供最关键的代码示例（如：Experiment基类、Metrics计算函数、报告生成）

#### 4. 交付清单
- [ ] 代码文件列表
- [ ] 测试文件（单元+集成）
- [ ] 配置/示例文件
- [ ] 文档（README/开发笔记）
- [ ] Demo脚本（可选）

---

## 参考示例

### 示例1：benchmark_rag 实验模式

```
benchmark_rag/
├── implementations/
│   └── pipelines/qa_dense_retrieval_milvus.py
├── evaluation/
│   ├── pipeline_experiment.py
│   ├── evaluate_results.py
│   └── config/
│       └── qa_eval.yaml
└── data/
```

**特点**：
- `config/` 定义实验参数
- `evaluation/` 提供统一的Experiment基类和评估入口
- `implementations/` 存放具体策略
- 可通过 `python -m sage.benchmark.benchmark_rag ...` 运行

### 示例2：benchmark_memory
- 参考其 `analyzer/`、`metrics/`、`runner/` 的划分方式

> 提醒：任务2最好复制这些成熟模式，确保后期维护成本低。

---

## 约束条件
1. **语言**：Python 3.10+
2. **依赖**：仅使用仓库已有依赖；如需新增请在提示词中说明并提供理由
3. **配置格式**：YAML + pydantic验证（若使用）
4. **指标输出**：JSON + Markdown报告
5. **日志**：统一使用 `sage.common.utils.logging`
6. **路径**：所有新模块放在 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/`
7. **测试**：使用 `pytest`，并放入 `packages/sage-benchmark/tests/benchmark_agent/`

---

## 期望输出

请按照以下结构输出拆分方案：

### 子任务1: [名称]
- 按照“输出格式要求”逐条回答

### 子任务2: [名称]
- 按照“输出格式要求”逐条回答

### 子任务3: [名称]
- 按照“输出格式要求”逐条回答

### 并行开发建议
- Git分支命名（建议：`feat/benchmark-agent-config`, `feat/benchmark-agent-eval`, ...）
- 合并顺序（如：先合并基线实现，再集成评估）
- 集成测试策略（如：使用mock结果跑通全链路）

---

## 评估标准
1. ✅ **独立性**：三个子任务互不依赖（或仅依赖稳定接口）
2. ✅ **完整性**：涵盖配置、运行器、评估、基线实现等需求
3. ✅ **可执行性**：开发者拿到子任务即可开工
4. ✅ **扩展性**：方便在任务3中接入新的工具选择/规划算法
5. ✅ **可测试性**：每个子任务都定义了明确的测试与验收方式

开始输出你的拆分方案吧！
