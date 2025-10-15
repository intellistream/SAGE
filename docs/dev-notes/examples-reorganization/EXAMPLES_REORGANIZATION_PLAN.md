# Examples 目录重组计划

## 目标

1. **教程示例** (examples/tutorials/) - 简单的学习示例
2. **应用示例** (examples/apps/) - 完整应用的入口点（指向 sage-apps）
3. **确保 CI/CD 通过** - 所有测试正常运行

## 当前状态分析

### 目录结构
```
examples/
├── __init__.py
├── README.md
├── requirements.txt
├── fault_tolerance_demo.py         # 独立demo
├── apps/                           # ✅ 应用入口（已整理）
│   ├── run_medical_diagnosis.py
│   └── run_video_intelligence.py
├── tutorials/                      # ✅ 教程示例（已存在）
│   ├── hello_world.py
│   ├── embedding_demo.py
│   └── ...
├── agents/                         # 📦 需要整理
│   ├── agent.py
│   ├── agent_workflow_demo.py
│   └── tools/
├── memory/                         # 📦 需要整理
│   ├── rag_memory_*.py (3个)
│   └── README files
├── multimodal/                     # 📦 需要整理
│   ├── cross_modal_search.py
│   └── text_image_quickstart.py
├── rag/                           # 📦 需要整理（最大的类别）
│   ├── qa_*.py (15+ 文件)
│   ├── build_*_index.py (4个)
│   └── loaders/
├── sage_db/                       # 📦 需要整理
│   └── workflow_dag_demo.py
├── scheduler/                     # 📦 需要整理
│   ├── remote_environment_simple.py
│   └── scheduler_comparison.py
├── service/                       # 📦 需要整理
│   ├── embedding_service_demo.py
│   ├── pipeline_as_service/
│   ├── sage_db/
│   └── sage_flow/
├── config/                        # ⚠️ 部分废弃
│   └── (各种yaml配置文件)
└── data/                          # ✅ 保留
```

## 重组方案

### Phase 1: 分类决策

#### 1.1 移动到 tutorials/ (教程性质)
```
简单、独立、教学性强的示例
- agents/agent.py → tutorials/agents/basic_agent.py
- agents/agent_workflow_demo.py → tutorials/agents/workflow_demo.py
- multimodal/text_image_quickstart.py → tutorials/multimodal/quickstart.py
- multimodal/cross_modal_search.py → tutorials/multimodal/cross_modal_search.py
- rag/rag_simple.py → tutorials/rag/simple_rag.py
- rag/qa_without_retrieval.py → tutorials/rag/qa_no_retrieval.py
- rag/qa_without_retrieval_local.py → tutorials/rag/qa_local_llm.py
- sage_db/workflow_dag_demo.py → tutorials/sage_db/workflow_demo.py
- scheduler/remote_environment_simple.py → tutorials/scheduler/remote_env.py
- fault_tolerance_demo.py → tutorials/fault_tolerance.py
```

#### 1.2 移动到 sage-apps 作为真实应用
```
完整、生产级的应用
- memory/rag_memory_pipeline.py → packages/sage-apps/src/sage/apps/memory/rag_memory_pipeline.py
- memory/rag_memory_service.py → packages/sage-apps/src/sage/apps/memory/rag_memory_service.py
- rag/qa_multimodal_fusion.py → packages/sage-apps/src/sage/apps/rag/multimodal_fusion.py

并在 examples/apps/ 创建对应的运行脚本:
- examples/apps/run_rag_memory.py
- examples/apps/run_multimodal_fusion.py
```

#### 1.3 保留在 examples/ (作为高级示例)
```
复杂但不适合作为独立应用的示例
- rag/qa_dense_retrieval*.py (6个) → examples/rag/
- rag/qa_*_retrieval.py → examples/rag/
- rag/build_*_index.py → examples/rag/
- service/* → examples/service/
- scheduler/scheduler_comparison.py → examples/scheduler/
```

#### 1.4 清理删除
```
废弃或重复的内容
- config/config_video_intelligence.yaml (已删除)
- examples/medical_diagnosis/ (已删除)
- agents/tools/ (如果是重复的工具示例)
```

### Phase 2: 创建应用入口点 (Pointers)

在 `examples/apps/` 为每个真实应用创建简洁的运行脚本:

```python
# examples/apps/run_rag_memory.py
"""
RAG Memory Pipeline - AI Agent with Long-term Memory

This script runs the RAG Memory application from sage-apps.
For full source code, see: packages/sage-apps/src/sage/apps/memory/
"""

from sage.apps.memory import run_rag_memory_pipeline

if __name__ == "__main__":
    run_rag_memory_pipeline()
```

### Phase 3: 更新 CI/CD 测试

#### 3.1 更新测试配置
- 更新 `tools/tests/test_examples.py` 的路径
- 确保跳过需要用户输入的示例
- 确保跳过需要长时间运行的示例

#### 3.2 测试分类标记
```python
# 在每个示例文件头部添加测试标记
"""
@test_category: tutorial
@test_speed: quick
@test_requires: []
@test_skip_ci: false
"""
```

### Phase 4: 文档更新

#### 4.1 更新 README
- examples/README.md - 总览
- examples/apps/README.md - 应用入口说明
- examples/tutorials/README.md - 教程说明
- examples/rag/README.md - 高级RAG示例

#### 4.2 更新主 README
- 更新示例引用路径
- 更新快速开始部分

## 执行计划

### Step 1: 备份和准备 ✅
```bash
git status
git add -A
git commit -m "checkpoint: before examples reorganization"
```

### Step 2: 移动教程示例 ✅ COMPLETED
1. 创建新的 tutorials 子目录
2. 移动简单示例
3. 更新导入路径

**已完成:**
- ✅ 移动 agents → tutorials/agents/
- ✅ 移动 multimodal → tutorials/multimodal/
- ✅ 移动简单 RAG → tutorials/rag/
- ✅ 移动 memory → tutorials/memory/
- ✅ 移动 scheduler → tutorials/scheduler/
- ✅ 移动 sage_db → tutorials/sage_db/
- ✅ 移动 fault_tolerance_demo.py
- ✅ 创建所有子目录的 README
- ✅ 修复配置文件路径
- ✅ 修复 import 路径
- ✅ 删除空目录

**成果:**
- tutorials/ 现在包含 50+ 个学习示例
- 清晰的分类结构
- 完善的文档

### Step 3: 创建应用
1. 将完整应用移动到 sage-apps
2. 创建配置目录
3. 创建入口点脚本

### Step 4: 清理
1. 删除废弃文件
2. 整理配置文件
3. 清理重复代码

### Step 5: 测试验证
1. 运行 tools/tests/test_examples.py
2. 修复失败的测试
3. 更新跳过规则

### Step 6: 文档和提交
1. 更新所有 README
2. 更新文档链接
3. 提交所有更改

## 注意事项

1. **保持向后兼容**: 旧的导入路径应该继续工作（通过 __init__.py 重定向）
2. **测试优先**: 每次移动后立即测试
3. **逐步进行**: 一次处理一个类别
4. **文档同步**: 确保文档与代码同步更新

## 风险评估

- **低风险**: tutorials 内部移动（独立性强）
- **中风险**: 创建新应用（需要完善配置）
- **高风险**: 删除文件（可能被其他地方引用）

## 成功标准

1. ✅ 所有 CI 测试通过
2. ✅ 目录结构清晰易懂
3. ✅ 文档完整准确
4. ✅ 应用可独立运行
5. ✅ 教程简单易学
