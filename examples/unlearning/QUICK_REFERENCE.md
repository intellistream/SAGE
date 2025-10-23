# SAGE Unlearning - Quick Reference

## 五分钟快速入门

### 场景 1️⃣: 研究/原型验证
```
你想快速测试想法，不需要完整的 SAGE 环境

→ 使用: usage_1_direct_library.py
→ 命令: python usage_1_direct_library.py
→ 示例函数:
   - example_basic_unlearning()          # 最简单的例子
   - example_custom_mechanism()          # 自定义隐私机制
   - example_batch_unlearning()          # 批量遗忘
   - example_similarity_based_unlearning()  # 基于相似性的遗忘
   - example_privacy_budget_management() # 隐私预算管理
```

**依赖**: `numpy`, `sage-libs`  
**复杂度**: ⭐ (简单)  
**VDB 集成**: ✗

---

### 场景 2️⃣: SAGE Pipeline 集成
```
你想在 SAGE Pipeline 中使用 unlearning

→ 使用: usage_2_sage_function.py
→ 命令: python usage_2_sage_function.py
→ 关键类:
   - VectorGenerator (SourceFunction)       # 生成向量数据
   - UnlearningProcessor (BaseFunction)     # 执行遗忘
   - ResultCollector (SinkFunction)         # 收集结果
   - UnlearningWithStateFunction (stateful) # 有状态处理
   - StateSink (state collector)            # 状态收集

→ 示例 Pipeline:
   - example_basic_pipeline()          # 基础 Pipeline
   - example_stateful_pipeline()       # 有状态处理
   - example_conditional_unlearning()  # 条件遗忘
```

**依赖**: SAGE framework, numpy  
**复杂度**: ⭐⭐ (中等)  
**VDB 集成**: ✗  
**流式处理**: ✓

---

### 场景 3️⃣: VDB/MemoryService 集成
```
你想将 unlearning 集成到向量数据库系统

→ 使用: usage_3_memory_service.py
→ 命令: python usage_3_memory_service.py
→ 关键类:
   - DPMemoryService (extends BaseService)

→ 关键方法:
   - create_collection(name)
   - store_memory(collection, vector_id, vector)
   - retrieve_memories(collection, query_vector)
   - forget_with_dp(collection, vector_ids)
   - get_privacy_status(collection)

→ 示例场景:
   - example_basic_dp_memory()          # 基础 VDB 遗忘
   - example_privacy_budget_management() # 隐私预算追踪
   - example_multi_collection()        # 多 collection 管理
```

**依赖**: SAGE middleware, NeuroMem, numpy  
**复杂度**: ⭐⭐ (中等)  
**VDB 集成**: ✓  
**生产就绪**: ～ (部分)

---

### 场景 4️⃣: 完整 RAG 系统 (生产)
```
你需要一个生产就绪的 RAG 系统，支持用户隐私和合规性

→ 使用: usage_4_complete_rag.py
→ 命令: python usage_4_complete_rag.py
→ 关键类:
   - RAGUnlearningSystem (extends BaseService)

→ 关键方法:
   - initialize_rag_corpus(corpus_path)
   - retrieve_relevant_documents(query, top_k)
   - forget_documents(doc_ids)
   - handle_user_deletion_request(collection, user_id)    # GDPR
   - handle_malicious_content_removal(content_patterns)   # 恶意内容
   - get_audit_log()                                      # 审计追踪

→ 示例场景:
   - example_basic_rag()            # 基础 RAG
   - example_malicious_content()    # 恶意内容删除
   - example_audit_log()            # 审计日志
```

**依赖**: 完整 SAGE 环境, 检索系统  
**复杂度**: ⭐⭐⭐ (复杂)  
**VDB 集成**: ✓  
**审计日志**: ✓  
**GDPR 支持**: ✓  
**生产就绪**: ✓

---

## 使用场景决策树

```
┌─────────────────────────────────────────┐
│    选择合适的使用方式                    │
└─────────────────────────────────────────┘
                   │
                   ▼
     ┌──────────────────────────┐
     │  需要 VDB/向量存储 吗？   │
     └───────┬──────────────┬───┘
             │NO             │YES
             ▼               ▼
        ┌────────────┐   ┌──────────────┐
        │ 使用流式   │   │ 需要生产级   │
        │ Pipeline? │   │ 功能吗？     │
        └─┬──────┬──┘   └───┬──────┬────┘
      YES │  │NO           YES│ │NO
         ▼  ▼                ▼  ▼
      ┌─────────────┐    ┌────────────────┐
      │ usage_2     │    │ usage_3        │
      │ SAGE        │    │ MemService     │
      │ Function    │    │ (VDB only)     │
      └─────────────┘    └────────────────┘

      ┌──────────────────────────────┐
      │ 需要审计/GDPR/合规 吗？     │
      └───────┬──────────────┬───────┘
          YES │              │ NO
             ▼               ▼
         ┌─────────────┐  ┌─────────────┐
         │ usage_4     │  │ usage_1/2/3 │
         │ RAG System  │  │             │
         │ (Production)│  │ Research    │
         └─────────────┘  └─────────────┘

    ┌──────────────────────────────────────┐
    │ 完全不使用 SAGE 框架？              │
    └───────┬──────────────────────────┬───┘
        YES │                          │ NO
           ▼                           ▼
      ┌─────────────┐          ┌────────────┐
      │ usage_1     │          │ usage_2/3/4│
      │ Direct Lib  │          │ with SAGE  │
      │ (Pure Algo) │          │            │
      └─────────────┘          └────────────┘
```

---

## 性能对比

| 特性 | usage_1 | usage_2 | usage_3 | usage_4 |
|------|---------|---------|---------|---------|
| 初始化时间 | 毫秒 | 秒 | 秒 | 秒+ |
| 每个遗忘操作 | 毫秒 | 毫秒 | 秒 | 秒+ |
| 内存开销 | 低 | 中 | 中 | 高 |
| 吞吐量 | 高 | 中高 | 中 | 中 |
| 可扩展性 | ✗ | ✓ | ✓ | ✓✓ |

---

## 代码片段速查

### 最小化 Direct Library 示例
```python
from sage.libs.unlearning import UnlearningEngine
import numpy as np

engine = UnlearningEngine(epsilon=1.0)

# 准备数据
vectors = np.random.randn(100, 128).astype(np.float32)
forget_vectors = vectors[:10]

# 执行遗忘
result = engine.unlearn_vectors(
    vectors_to_forget=forget_vectors,
    all_vectors=vectors,
    perturbation_strategy="adaptive"
)

print(f"Privacy cost: {result.privacy_cost}")
```

### 最小化 SAGE Function 示例
```python
from sage.kernel.api.function.base_function import BaseFunction

class MyUnlearningFunction(BaseFunction):
    def __init__(self):
        super().__init__()
        self.engine = UnlearningEngine(epsilon=1.0)

    def execute(self, data):
        if data.get('should_forget'):
            result = self.engine.unlearn_vectors(...)
            return {'vector': result.metadata['perturbed_vectors'][0]}
        return data
```

### 最小化 MemService 示例
```python
from sage.kernel.api.service.base_service import BaseService

class MyMemService(BaseService):
    def __init__(self):
        super().__init__()
        self.manager = MemoryManager()
        self.engine = UnlearningEngine(epsilon=1.0)

    def forget(self, collection_name, vector_ids):
        collection = self.manager.get_collection(collection_name)
        # 获取向量、执行遗忘、更新 VDB
```

### 最小化 RAG 示例
```python
class MyRAGSystem(BaseService):
    def handle_deletion_request(self, user_id):
        # 1. 查找用户的所有向量
        # 2. 执行 DP 遗忘
        # 3. 更新 VDB
        # 4. 记录审计日志
```

---

## 学习建议

### 🚀 快速开始 (10分钟)
1. 阅读本文档
2. 运行 `basic_unlearning_demo.py`
3. 查看 `usage_1_direct_library.py` 的前 3 个函数

### 📚 深入学习 (1小时)
1. 运行所有 `usage_1_*` 示例
2. 理解隐私预算和扰动策略
3. 尝试修改参数看效果

### 🏗️ 开发集成 (1天)
1. 学习 `usage_2` 或 `usage_3`
2. 根据你的用例选择合适的模式
3. 实现自己的业务逻辑

### 🔬 研究扩展 (1周+)
1. 学习 `usage_4` 的完整实现
2. 探索 EMBEDDING_README.md 中的向量系统
3. 实现自己的隐私机制或评估指标

---

## 常见问题

**Q: 哪个示例最适合我？**  
A: 查看上面的决策树，或根据你的需求选择：
- 快速实验 → usage_1
- Pipeline 集成 → usage_2
- VDB 系统 → usage_3
- 生产应用 → usage_4

**Q: 需要修改哪些参数？**  
A: 最常见的是 `epsilon`（隐私预算，越小越隐私）和 `perturbation_strategy`（扰动策略）

**Q: 如何添加自定义隐私机制？**  
A: 参考 `usage_1_direct_library.py` 中的 `example_custom_mechanism()`

**Q: 如何评估遗忘效果？**  
A: 使用 `sage.libs.unlearning.metrics` 中的评估函数，示例见各文件

**Q: 生产环境需要注意什么？**  
A: 使用 `usage_4` 的 RAG 系统模板，包括审计日志、错误处理、隐私预算监控

---

## 文件导航

```
examples/unlearning/
├── README.md                      # 完整文档
├── USAGE_GUIDE.md                 # 详细用途指南
├── QUICK_REFERENCE.md             # 本文档
├── basic_unlearning_demo.py        # 入门演示
├── usage_1_direct_library.py       # 直接库用法
├── usage_2_sage_function.py        # SAGE Function 集成
├── usage_3_memory_service.py       # VDB 集成
└── usage_4_complete_rag.py         # 完整 RAG 系统
```

---

**下一步**: 选择合适的示例文件开始学习或开发！
