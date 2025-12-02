# 任务1拆分提示词 - 给Claude Sonnet 4.5

## 背景信息

你正在参与SAGE框架的Agent工具选择Benchmark项目开发。SAGE是一个Python 3.10+的AI/LLM数据处理框架，采用严格的分层架构（L1-L6）。

### SAGE数据架构（两层设计）

```
packages/sage-benchmark/src/sage/data/
├── sources/           # Layer 1: 物理数据集（实际数据文件）
│   ├── qa_base/      # QA知识库
│   ├── bbh/          # BIG-Bench Hard
│   ├── mmlu/         # MMLU数据集
│   ├── locomo/       # 长上下文记忆数据集
│   └── ...
│
└── usages/            # Layer 2: 使用场景（逻辑视图配置）
    ├── rag/          # RAG实验场景
    ├── libamm/       # LibAMM基准测试场景
    └── neuromem/     # NeuroMem实验场景
```

**核心概念**：
- **sources/**: 存放原始数据文件、数据集元信息(dataset.yaml)、数据加载器(loader.py)
- **usages/**: 定义实验场景配置(usage.yaml)、指定使用哪些sources、如何组合使用
- **DataManager**: 统一数据访问接口，支持通过`get_source()`或`get_usage()`访问数据

### 项目目标：Agent工具选择Benchmark

我们要构建一个评估Agent从1000+工具中准确选择工具的能力的benchmark系统，支持：
1. **工具选择**：从大规模工具库中准确选择Top-K工具（目标准确率≥95%）
2. **任务规划**：复杂多步任务规划能力（5-10步，目标成功率≥90%）
3. **时机判断**：准确判断何时调用工具vs直接回复（目标F1≥0.93）

---

## 任务1：数据层建设概述

**目标**：构建Agent工具库与Benchmark数据集，包括：
- 1000+工具库及分类索引
- 多层次测试数据集（简单/复杂/时机判断）
- 可选的SFT训练数据
- 完整的数据加载器和文档

**预期目录结构**：
```
packages/sage-benchmark/src/sage/data/
├── sources/
│   ├── agent_tools/          # 工具库数据源
│   ├── agent_benchmark/      # Benchmark测试数据
│   └── agent_sft/           # SFT训练数据（可选）
└── usages/
    └── agent_eval/          # Agent评估场景
```

---

## 拆分要求

请将**任务1（数据层建设）**拆分成**3个可以完全并行执行的独立子任务**。

### 拆分原则

1. **完全独立**：每个子任务可以由不同的开发者在不同分支上同时开发，无代码冲突
2. **清晰边界**：文件路径、数据格式、接口定义明确，无交叉依赖
3. **可独立测试**：每个子任务可以独立编写单元测试和验证脚本
4. **可独立交付**：每个子任务完成后可以单独merge，不影响其他子任务
5. **符合架构**：严格遵循SAGE的两层数据架构（sources + usages）

### 输出格式要求

对于每个子任务，请提供：

#### 1. 子任务概述
- **子任务名称**：简洁明确的名称
- **核心目标**：1-2句话说明要完成什么
- **独立性说明**：为什么这个子任务可以独立完成

#### 2. 详细规格

**2.1 目录结构**
```
完整的目录树，包含所有文件（精确到文件名）
注明每个文件的作用
```

**2.2 数据格式设计**
- 每个数据文件的JSON/JSONL格式示例
- 字段说明和约束条件
- 数据量级要求（如：至少100个样本）

**2.3 代码实现清单**
- 需要实现的类和函数列表
- 每个类/函数的职责和接口签名
- dataset.yaml的内容示例

**2.4 集成接口**
- 如何通过DataManager访问（示例代码）
- 与其他子任务的数据约定（如：工具ID格式统一）

**2.5 验证标准**
- 单元测试覆盖的关键点
- 数据质量检查项
- 独立验收标准

#### 3. 实施指导

**3.1 开发顺序建议**
1. 第一步做什么
2. 第二步做什么
3. ...

**3.2 技术要点**
- 需要注意的技术细节
- 可能的坑和解决方案
- 性能考虑（如果适用）

**3.3 示例代码片段**
提供关键部分的代码示例（如：loader核心逻辑、数据生成脚本等）

#### 4. 交付清单

- [ ] 具体的文件列表
- [ ] 测试文件
- [ ] 文档文件
- [ ] 验证脚本

---

## 参考示例：现有数据源结构

### 示例1：locomo数据源

```
sources/locomo/
├── __init__.py
├── dataset.yaml          # 元信息
├── README.md            # 说明文档
├── dataloader.py        # LocomoDataLoader类
└── data/                # 实际数据（或下载说明）
```

**dataset.yaml示例**：
```yaml
name: "locomo"
description: "Long-context memory dataset for testing agent memory capabilities"
type: "qa"
version: "1.0.0"
maintainer: "SAGE Team"
license: "MIT"
size: "~500MB"
format: "json"
tags: ["long-context", "memory", "qa"]
```

**Loader接口示例**：
```python
class LocomoDataLoader:
    def get_sample_id(self) -> List[str]:
        """返回所有样本ID"""

    def iter_qa(self, sample_id: str) -> Iterator[dict]:
        """迭代指定样本的QA对"""
```

### 示例2：RAG使用场景

```
usages/rag/
├── __init__.py
├── usage.yaml           # 场景配置
└── README.md
```

**usage.yaml示例**：
```yaml
name: "rag"
description: "RAG experiments using QA datasets"
sources:
  - qa_base
  - mmlu
  - bbh
profiles:
  default:
    source: qa_base
    split: dev
  comprehensive:
    sources: [qa_base, mmlu, bbh]
```

---

## 约束条件

1. **数据格式**：统一使用JSON/JSONL，UTF-8编码
2. **工具ID格式**：`category_name_###`，如`weather_query_001`
3. **文件命名**：使用小写下划线分隔，如`tool_selection_benchmark.jsonl`
4. **Python版本**：Python 3.10+
5. **依赖库**：仅使用SAGE现有依赖，避免引入新的外部库
6. **文档**：每个README.md必须包含：简介、数据格式、使用示例、引用
7. **测试**：每个loader必须有对应的单元测试文件

---

## 期望输出

请提供一个**完整的、可直接执行的拆分方案**，包含：

### 子任务1: [名称]
（按照上述"输出格式要求"的结构详细描述）

### 子任务2: [名称]
（按照上述"输出格式要求"的结构详细描述）

### 子任务3: [名称]
（按照上述"输出格式要求"的结构详细描述）

### 并行开发建议
- Git分支策略（如：`feat/agent-tools-corpus`, `feat/agent-benchmark-data`, `feat/agent-usage-config`）
- 合并顺序建议
- 集成测试方案

---

## 评估标准

你的拆分方案将根据以下标准评估：
1. ✅ **独立性**：3个子任务无文件冲突，可完全并行开发
2. ✅ **完整性**：覆盖任务1的所有需求（工具库、测试集、SFT数据、使用场景）
3. ✅ **可执行性**：规格足够详细，开发者可以直接按照方案实施
4. ✅ **架构合规**：严格遵循SAGE两层数据架构
5. ✅ **可测试性**：每个子任务有明确的验收标准和测试方法

开始输出你的拆分方案吧！
