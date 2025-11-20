# Memory Test Pipeline - Output Format

## 文件结构

```
.sage/benchmarks/benchmark_memory/
└── {dataset_name}/
    └── {timestamp}/          # 例如: 251120_1430
        └── {task_id}.json    # 例如: 0000.json
```

## JSON 格式示例

```json
{
  "experiment_info": {
    "dataset": "locomo",
    "task_id": "0000"
  },
  "dataset_statistics": {
    "total_sessions": 3,
    "total_dialogs": 56,
    "total_questions": 100,
    "valid_questions": 98,
    "invalid_questions": [
      {
        "question_index": 15,
        "question": "What color is mentioned?",
        "reason": "no_evidence"
      },
      {
        "question_index": 42,
        "question": "When did this happen?",
        "reason": "no_evidence"
      }
    ]
  },
  "test_summary": {
    "total_tests": 10,
    "test_threshold": "1/10 of total questions"
  },
  "test_results": [
    {
      "test_index": 1,
      "question_range": {
        "start": 1,
        "end": 10
      },
      "dialogs_inserted_count": 8,
      "questions": [
        {
          "question_index": 1,
          "question_text": "What is the main topic?",
          "predicted_answer": "Technology",
          "reference_answer": "Technology and AI",
          "evidence": ["D1:3", "D1:5"],
          "category": "factoid"
        },
        {
          "question_index": 2,
          "question_text": "Who is the speaker?",
          "predicted_answer": "John",
          "reference_answer": "John Smith",
          "evidence": ["D1:1"],
          "category": "entity"
        }
      ]
    },
    {
      "test_index": 2,
      "question_range": {
        "start": 1,
        "end": 20
      },
      "dialogs_inserted_count": 16,
      "questions": [...]
    }
  ]
}
```

## 字段说明

### experiment_info
- `dataset`: 数据集名称
- `task_id`: 任务/样本ID

### dataset_statistics
- `total_sessions`: 总会话数
- `total_dialogs`: 总对话数
- `total_questions`: 问题总数（包含无效问题）
- `valid_questions`: 有效问题数（有 evidence 的）
- `invalid_questions`: 无效问题列表
  - `question_index`: 问题序号
  - `question`: 问题文本
  - `reason`: 无效原因（如 "no_evidence"）

### test_summary
- `total_tests`: 总测试次数（触发测试的次数）
- `test_threshold`: 测试阈值说明

### test_results
每次测试包含：
- `test_index`: 测试序号（第几次测试）
- `question_range`: 测试的问题范围
  - `start`: 起始问题序号
  - `end`: 结束问题序号
- `dialogs_inserted_count`: 测试时已插入的对话总数
- `questions`: 问题列表
  - `question_index`: 问题序号
  - `question_text`: 问题文本
  - `predicted_answer`: 模型预测的答案
  - `reference_answer`: 参考答案（来自数据集）
  - `evidence`: 证据位置（可选，数据集特定）
  - `category`: 问题分类（可选，数据集特定）
  - `error`: 错误信息（如果生成失败）

## 通用性设计

该格式设计为通用格式，支持不同数据集：

1. **必需字段**（所有数据集）：
   - `question_index`, `question_text`, `predicted_answer`

2. **可选字段**（数据集特定）：
   - `reference_answer`, `evidence`, `category` 等
   - 这些字段从 `question_metadata` 中提取，不同数据集可能有不同的元数据

3. **扩展性**：
   - 新数据集只需在 `PipelineCaller._get_dataset_stats()` 中实现统计逻辑
   - metadata 自动传递，Sink 自动提取可用字段
