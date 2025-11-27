# Agent Tool Benchmark - Task 1 Decomposition

## 子任务1：Agent 工具库数据源（`agent_tools`）

### 1. 子任务概述
- **子任务名称**：Agent Tool Corpus Source
- **核心目标**：构建包含 ≥1,000 个工具、分类索引与检索接口的 `agent_tools` 数据源，为 Top-K 工具选择评测提供统一语料。
- **独立性说明**：只在 `packages/sage-benchmark/src/sage/data/sources/agent_tools/` 范围内新增文件，输出统一 `tool_id`，不依赖其他子任务的实现即可交付。

### 2. 详细规格
#### 2.1 目录结构
```
packages/sage-benchmark/src/sage/data/sources/agent_tools/
├── __init__.py                     # 导出 Loader 工厂
├── dataset.yaml                    # 数据源元信息
├── README.md                       # 数据说明、字段定义、引用
├── dataloader.py                   # AgentToolsDataLoader 实现
├── schemas.py                      # 数据模型 & 校验逻辑
├── data/
│   ├── tool_catalog.jsonl          # 工具主体数据（≥1000 条）
│   ├── categories.json             # 分类层级树
│   ├── embeddings.npy (可选)       # 预计算向量
│   └── stats.json                  # 统计信息
└── tests/
    └── test_agent_tools_loader.py  # 单元测试
```
#### 2.2 数据格式设计
- **`tool_catalog.jsonl`**（UTF-8）：
  ```json
  {
    "tool_id": "weather_query_001",
    "name": "Weather Query",
    "category": "environment/weather",
    "capabilities": ["forecast", "historical"],
    "inputs": [{"name": "location", "type": "string", "required": true}],
    "outputs": [{"name": "forecast", "type": "json"}],
    "invoke_examples": [
      {"instruction": "Get 3-day forecast for Paris", "arguments": {"location": "Paris"}}
    ],
    "reliability_score": 0.97,
    "latency_ms_p50": 120,
    "metadata": {"owner": "MetAPI", "updated_at": "2025-10-15"}
  }
  ```
  - 约束：`tool_id` 正则 `^[a-z]+(_[a-z]+)*_[0-9]{3}$`，`name` 唯一，`capabilities` 非空，样本 ≥1,000。
- **`categories.json`**：
  ```json
  {
    "taxonomy": [
      {"path": "environment/weather", "description": "Weather & climate APIs"},
      {"path": "productivity/calendar", "description": "Calendar & scheduling"}
    ],
    "version": "1.0.0"
  }
  ```
- **`stats.json`**：记录工具数量、类别覆盖率、更新时间。

#### 2.3 代码实现清单
- `AgentToolRecord(BaseModel)`：负责字段验证与默认值。
- `AgentToolsDataLoader(BaseDataLoader)`：
  - `list_tool_ids() -> List[str]`
  - `get_tool(tool_id: str) -> AgentToolRecord`
  - `search_by_capability(keyword: str, top_k: int = 20) -> List[AgentToolRecord]`
  - `iter_category(category_path: str) -> Iterator[AgentToolRecord]`
- `dataset.yaml` 示例：
  ```yaml
  name: "agent_tools"
  description: "1000+ curated agent tools with categories and metadata"
  type: "tools"
  format: "jsonl"
  version: "1.0.0"
  maintainer: "SAGE Agent Benchmark Team"
  tags: ["tools", "catalog", "agent"]
  license: "CC-BY-4.0"
  size: "~15MB"
  ```

#### 2.4 集成接口
```python
manager = DataManager.get_instance()
tools_loader = manager.get_by_source("agent_tools")
top_weather = tools_loader.search_by_capability("weather", top_k=5)
```
- 与其他子任务约定：所有引用工具使用 `tool_id`；`category` 必须匹配 `categories.json` 定义。

#### 2.5 验证标准
- **单测**：数量检测、ID 正则、检索接口、重复校验。
- **数据质检**：schema 校验、类别覆盖率、空字段扫描。
- **验收**：DataManager 可成功加载，README、stats 完整。

### 3. 实施指导
#### 3.1 开发顺序
1. 定义 schema 与 `tool_id` 生成规则。
2. 构建/清洗工具数据并导出 JSONL。
3. 实现 loader 与注册逻辑。
4. 编写 README + tests + 质检脚本。

#### 3.2 技术要点
- 对大文件采用流式读取或懒加载 embeddings。
- 通过脚本确保 `tool_id` 全局唯一与分类一致。
- 保持 deterministic 数据生成，方便测试与审计。

#### 3.3 示例代码片段
```python
def search_by_capability(self, keyword: str, top_k: int = 20):
    keyword_lower = keyword.lower()
    matches = [
        rec for rec in self.records
        if any(keyword_lower in cap for cap in rec.capabilities)
    ]
    return matches[:top_k]
```

### 4. 交付清单
- [ ] 数据目录与 JSONL/metadata
- [ ] `AgentToolsDataLoader` 单测
- [ ] README（含格式与示例）
- [ ] 数据验证脚本 / notebook

---

## 子任务2：Agent Benchmark 测试数据源（`agent_benchmark`）

### 1. 子任务概述
- **子任务名称**：Agent Benchmark Task Packs
- **核心目标**：提供覆盖工具选择、任务规划、时机判断三大能力的评测样本，满足多层次难度需求。
- **独立性说明**：只操作 `agent_benchmark` 目录并引用 `agent_tools` 的 `tool_id` 约定，内部数据与 loader 自成体系，可独立验收。

### 2. 详细规格
#### 2.1 目录结构
```
packages/sage-benchmark/src/sage/data/sources/agent_benchmark/
├── __init__.py
├── dataset.yaml
├── README.md
├── dataloader.py
├── splits/
│   ├── tool_selection.jsonl      # ≥500 样本
│   ├── task_planning.jsonl       # ≥300 样本
│   └── timing_judgment.jsonl     # ≥300 样本
├── metadata/
│   ├── rubric.json               # 评分标准
│   ├── difficulty_map.json       # 难度定义
│   └── schema.json               # JSON Schema
└── tests/
    └── test_agent_benchmark_loader.py
```
#### 2.2 数据格式设计
- 通用样例：
  ```json
  {
    "sample_id": "ts_000123",
    "task_type": "tool_selection",
    "instruction": "Help plan a trip to Tokyo in March.",
    "context": "User has budget 2k USD...",
    "candidate_tools": ["travel_search_012", "weather_query_001", "currency_convert_045"],
    "ground_truth": {
      "top_k": ["weather_query_001", "currency_convert_045"],
      "explanation": "Need weather + exchange rate info"
    },
    "metadata": {
      "difficulty": "medium",
      "tags": ["travel", "multi-step"],
      "created_by": "heuristic_generator_v2"
    },
    "split": "dev"
  }
  ```
- `task_planning.jsonl` 额外字段：`plan_steps`（5-10 步）、`tool_sequence`（有序 `tool_id`）、`success_criteria`。
- `timing_judgment.jsonl` 字段：`should_call_tool`、`reasoning_chain`、`direct_answer`。
- **数据量级**：总 ≥1,100 样本，每类任务均含 train/dev/test。

#### 2.3 代码实现清单
- `AgentBenchmarkSample(BaseModel)` 及子类。
- `AgentBenchmarkDataLoader`：
  - `iter_split(task_type: str, split: str = "train")`
  - `get_sample(sample_id: str)`
  - `get_stats()`
- `dataset.yaml`：
  ```yaml
  name: "agent_benchmark"
  description: "Task packs for tool picking, planning, and timing evaluation"
  type: "benchmark"
  format: "jsonl"
  version: "0.1.0"
  maintainer: "SAGE Agent Benchmark Team"
  tags: ["agent", "benchmark", "planning"]
  license: "CC-BY-SA-4.0"
  size: "~20MB"
  ```

#### 2.4 集成接口
```python
manager = DataManager.get_instance()
benchmark = manager.get_by_source("agent_benchmark")
for sample in benchmark.iter_split("timing_judgment", split="dev"):
    evaluate(sample)
```
- 与其他子任务约定：`candidate_tools`、`tool_sequence` 中的 ID 必须存在于 `agent_tools`。

#### 2.5 验证标准
- **单测**：不同 task_type/split 读取、schema 校验、tool_id 交叉验证。
- **数据质检**：JSON Schema、`ground_truth.top_k` 非空、plan step 数区间。
- **验收**：统计结果写入日志/README，DataManager 可加载。

### 3. 实施指导
#### 3.1 开发顺序
1. 定义 JSON Schema 与评分 rubric。
2. 准备/生成各 split 样本并打标签。
3. 编写 loader 与 tests。
4. 运行 cross-check（tool_id、步骤数、split 分布）并更新 README。

#### 3.2 技术要点
- 固定随机种子确保数据集稳定。
- 使用验证脚本保证 `tool_sequence` 与 `plan_steps` 一致。
- 大 JSONL 建议分块生成后合并再校验。

#### 3.3 示例代码片段
```python
def iter_split(self, task_type: str, split: str = "train"):
    path = self._split_paths[(task_type, split)]
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield AgentBenchmarkSample.parse_raw(line)
```

### 4. 交付清单
- [ ] `agent_benchmark` 数据与元数据
- [ ] Loader 单测
- [ ] README + rubric 文档
- [ ] Schema / 交叉验证脚本

---

## 子任务3：Agent SFT 数据源与评估 Usage（`agent_sft` + `agent_eval`）

### 1. 子任务概述
- **子任务名称**：Agent SFT + Evaluation Usage
- **核心目标**：构建面向 SFT 的对话语料 `agent_sft`，并提供 `agent_eval` 使用场景串联前述数据源，实现训练+评测统一入口。
- **独立性说明**：`agent_sft` 与 `agent_eval` 均位于独立目录，只需引用已知 source 名称；数据生成与使用配置可单独完成与测试。

### 2. 详细规格
#### 2.1 目录结构
```
packages/sage-benchmark/src/sage/data/sources/agent_sft/
├── __init__.py
├── dataset.yaml
├── README.md
├── dataloader.py
├── data/
│   ├── sft_conversations.jsonl     # ≥5k 对话
│   └── prompts_template.yaml       # few-shot 模板
└── tests/
    └── test_agent_sft_loader.py

packages/sage-benchmark/src/sage/data/usages/agent_eval/
├── __init__.py
├── usage.yaml
├── README.md
└── profiles/
    ├── quick_eval.yaml
    ├── full_eval.yaml
    └── sft_training.yaml
```
#### 2.2 数据格式设计
- **`sft_conversations.jsonl`**：
  ```json
  {
    "dialog_id": "sft_000045",
    "goal": "Plan hardware debugging using chip diagnostics tools",
    "turns": [
      {"role": "user", "content": "Diagnose chip timing issue"},
      {"role": "assistant", "content": "Step 1: call oscilloscope_log_014 ..."},
      {"role": "tool", "tool_id": "oscilloscope_log_014", "result": "..."}
    ],
    "target_tools": ["oscilloscope_log_014", "logic_analyzer_233"],
    "metadata": {"difficulty": "hard", "source": "self-play-v1"},
    "split": "train"
  }
  ```
  - turn 数 6-12，`tool_id` 必须存在于 `agent_tools`；总样本 ≥5,000。
- **`usage.yaml`**：
  ```yaml
  name: "agent_eval"
  description: "Unified usage linking tools, benchmark, and SFT data"
  sources:
    - agent_tools
    - agent_benchmark
    - agent_sft
  profiles:
    quick_eval:
      sources: {benchmark: agent_benchmark}
      filters:
        task_types: ["tool_selection"]
        split: "dev"
    full_eval:
      sources:
        benchmark: agent_benchmark
        tools: agent_tools
      filters:
        task_types: ["tool_selection", "task_planning", "timing_judgment"]
        split: "test"
    sft_training:
      sources: {sft: agent_sft}
      parameters:
        max_turns: 12
  ```

#### 2.3 代码实现清单
- `AgentSFTDialog(BaseModel)` & `Turn` 数据类。
- `AgentSFTDataLoader`：
  - `iter_dialogs(split: str = "train")`
  - `sample_batch(batch_size: int)`
  - `get_tools_coverage() -> Dict[str, int]`
- Usage 注册：`USAGES_REGISTRY["agent_eval"] = AgentEvalUsageFactory`。
- `dataset.yaml`：
  ```yaml
  name: "agent_sft"
  description: "SFT dialogs aligned with tool benchmark"
  type: "sft"
  format: "jsonl"
  version: "0.1.0"
  maintainer: "SAGE Agent Benchmark Team"
  tags: ["sft", "dialogs", "agent"]
  license: "CC-BY-4.0"
  size: "~30MB"
  ```

#### 2.4 集成接口
```python
manager = DataManager.get_instance()
agent_eval = manager.get_by_usage("agent_eval")
full_profile = agent_eval.load_profile("full_eval")
benchmark_loader = full_profile["benchmark"]
tools_loader = full_profile["tools"]
```
- 约定：SFT 对话中的 `tool_id` 必须在 `agent_tools` 中存在，usage `sources` 名称与 DataManager 注册名一致。

#### 2.5 验证标准
- **单测**：SFT loader 批采样、工具覆盖率、split 切分；usage profile 解析。
- **数据质检**：对话 turn 顺序（user→assistant→tool）、tool ID 校验、最大 turn 数。
- **验收**：`DataManager.get_by_usage("agent_eval")` 可加载各 profile 并访问对应 loader。

### 3. 实施指导
#### 3.1 开发顺序
1. 设计对话 schema 与模板。
2. 构建对话数据并执行 tool ID 校验。
3. 实现 SFT loader + tests。
4. 编写 usage 配置、profiles、README。

#### 3.2 技术要点
- Loader 支持流式迭代，避免一次性载入全部对话。
- Usage filters 允许覆盖 split/任务类型，宜 declarative。
- 注意多语言文本 UTF-8，避免 BOM。

#### 3.3 示例代码片段
```python
class AgentSFTDataLoader:
    def sample_batch(self, batch_size: int = 8):
        return random.sample(self.dialogs, batch_size)
```

### 4. 交付清单
- [ ] `agent_sft` 数据与 loader
- [ ] Usage 配置 + README
- [ ] Tests（SFT loader + usage profiles）
- [ ] 验证脚本：tool ID & turn 结构校验

---

## 并行开发建议
- **Git 分支策略**：
  - `feat/agent-tools-corpus`（子任务1）
  - `feat/agent-benchmark-data`（子任务2）
  - `feat/agent-sft-usage`（子任务3）
- **合并顺序**：子任务1与2可并行并任意先 merge；子任务3 仅依赖前两者的 source 名称与 `tool_id` 规范，可在确认接口后并行开发，最终合并前验证工具 ID 对齐。
- **集成测试方案**：
  1. 各子任务提交前运行对应 tests，例如 `pytest packages/sage-benchmark/src/sage/data/sources/agent_tools/tests -v`。
  2. 集成阶段运行 `sage-dev project test --quick -k agent_eval` 验证 usage 组合。
  3. 提供 `tools/scripts/validate_agent_tool_ids.py`（可复用）在 CI 中校验跨数据源 `tool_id` 一致性。
