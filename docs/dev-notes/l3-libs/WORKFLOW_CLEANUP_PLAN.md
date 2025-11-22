# Workflow Generation 代码清理方案

## 📋 当前状态分析

### ✅ 已迁移到 sage-libs 的代码

**新位置**: `packages/sage-libs/src/sage/libs/agentic/workflow/generators/`

- ✅ `rule_based_generator.py` - 规则生成器（基于关键词匹配）
- ✅ `llm_generator.py` - LLM 生成器（使用 Pipeline Builder）
- ✅ `base.py` - 统一接口和数据结构

### ⚠️ 需要处理的旧代码

#### 1. **chat_pipeline_recommender.py** （保留，但功能重叠）

**位置**: `packages/sage-studio/src/sage/studio/services/chat_pipeline_recommender.py`

**当前用途**:
- `/api/chat/sessions/{session_id}/convert` 端点仍在使用
- 基于简单的意图识别生成推荐

**问题**:
- 功能与 `RuleBasedWorkflowGenerator` 重叠
- 更简单、更轻量（不依赖 sage-cli）
- 目前是 **默认的转换方法**

**建议**:
- **选项 A（推荐）**: 迁移到使用 `RuleBasedWorkflowGenerator`
- **选项 B**: 保留作为快速推荐，但标注为简化版本

#### 2. **sage-gateway/rag_pipeline.py 中的 _generate_workflow()** （需要迁移）

**位置**: `packages/sage-gateway/src/sage/gateway/rag_pipeline.py`

**当前用途**:
- 在 Chat 中检测到工作流创建意图时调用
- 直接使用 Pipeline Builder

**问题**:
- 与 `LLMWorkflowGenerator` 功能完全重复
- 应该调用 sage-libs 的生成器

**建议**:
- **替换为调用 `LLMWorkflowGenerator`**

## 🎯 推荐的清理方案

### 方案 1: 完全迁移（推荐）

**目标**: 所有工作流生成都使用 sage-libs generators

**步骤**:

1. **更新 chat_pipeline_recommender.py**
   ```python
   # 改为调用 RuleBasedWorkflowGenerator
   from sage.libs.agentic.workflow import GenerationContext
   from sage.libs.agentic.workflow.generators import RuleBasedWorkflowGenerator

   def generate_pipeline_recommendation(session):
       context = GenerationContext(...)
       generator = RuleBasedWorkflowGenerator()
       result = generator.generate(context)
       return _convert_to_old_format(result)  # 兼容现有 API
   ```

2. **更新 sage-gateway/rag_pipeline.py**
   ```python
   # 改为调用 LLMWorkflowGenerator
   from sage.libs.agentic.workflow import GenerationContext
   from sage.libs.agentic.workflow.generators import LLMWorkflowGenerator

   def _generate_workflow(self, requirements):
       context = GenerationContext(user_input=requirements['goal'], ...)
       generator = LLMWorkflowGenerator()
       result = generator.generate(context)
       return result.visual_pipeline
   ```

3. **删除重复的格式转换代码**
   - `_convert_to_visual_pipeline()` 已在 generators 中实现

### 方案 2: 渐进式迁移

**目标**: 保留旧代码但标注为 deprecated

**步骤**:

1. **标注旧函数**
   ```python
   @deprecated("请使用 sage.libs.agentic.workflow.generators.RuleBasedWorkflowGenerator")
   def generate_pipeline_recommendation(session):
       ...
   ```

2. **添加新端点使用新 generators**
3. **逐步废弃旧端点**

## 📊 当前默认行为

### Studio 默认使用什么？

**两个端点并存**:

1. **`/api/chat/sessions/{session_id}/convert`** （旧）
   - ✅ 当前使用：`chat_pipeline_recommender.generate_pipeline_recommendation()`
   - ✅ 策略：简单的关键词匹配
   - ✅ 特点：快速、轻量、无需 API
   - ⚠️ 问题：功能有限

2. **`/api/chat/generate-workflow`** （新）
   - ✅ 当前使用：`workflow_generator.generate_workflow_from_chat()`
   - ✅ 策略：默认 `use_llm=True`（LLM 生成器）
   - ✅ 特点：智能、灵活
   - ⚠️ 问题：需要 API 密钥

**结论**:
- **旧端点默认用规则匹配（简化版）**
- **新端点默认用 LLM 生成（高级版）**

## 🔧 建议的配置选项

在 Studio API 中添加配置：

```python
# api.py
class WorkflowGenerateRequest(BaseModel):
    user_input: str
    session_id: str | None = None
    use_llm: bool = True  # 默认用 LLM
    use_simple_recommender: bool = False  # 是否用简化推荐器
    enable_optimization: bool = False
```

## 📝 清理清单

### 立即执行

- [x] 修复 workflow_generator.py 格式错误
- [ ] 更新 chat_pipeline_recommender.py 改为调用 RuleBasedWorkflowGenerator
- [ ] 更新 sage-gateway/rag_pipeline.py 改为调用 LLMWorkflowGenerator
- [ ] 删除重复的 _convert_to_visual_pipeline() 实现

### 后续优化

- [ ] 统一两个端点为一个（带参数选择策略）
- [ ] 添加策略选择 UI
- [ ] 添加性能对比测试
- [ ] 更新文档

## 🎯 最终建议

**对于你的问题**:

1. **旧代码是否删除？**
   - **chat_pipeline_recommender**: 建议保留但改为调用 RuleBasedWorkflowGenerator
   - **gateway 中的 _generate_workflow**: 建议改为调用 LLMWorkflowGenerator
   - 不要直接删除，以保证向后兼容

2. **Studio 默认用什么？**
   - **旧端点** (`/convert`): 简单规则匹配（类似 RuleBasedWorkflowGenerator）
   - **新端点** (`/generate-workflow`): LLM 生成（默认 `use_llm=True`）
   - **建议**: 统一默认为 **规则生成器**（快速、无需 API），提供选项切换到 LLM

3. **推荐配置**:
   ```python
   # 默认策略配置
   DEFAULT_WORKFLOW_STRATEGY = "rule_based"  # 或 "llm"
   ALLOW_STRATEGY_SWITCH = True
   ```
