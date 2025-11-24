# SAGE Studio 问题修复 - 完整记录

**日期**: 2025-11-21\
**状态**: ✅ 全部修复完成并测试通过

______________________________________________________________________

## 问题总结

### 原始报告的3个问题

1. ✅ **Chat 生成的工作流导入 Studio 是空壳**
1. ✅ **新建聊天时好时坏**
1. ✅ **Studio Playground 输入问题回答报错**

### 修复过程中发现的额外问题

4. ✅ **Gateway 导入路径错误** (`sage.libs.io` 不存在)
1. ✅ **ChromaRetriever 配置格式错误**

______________________________________________________________________

## 完整修复列表

### 修复 #1: Chat Pipeline 推荐节点缺少配置

**文件**: `packages/sage-studio/src/sage/studio/services/chat_pipeline_recommender.py`

**问题**: 生成的节点没有 `config` 字段

**修复** (+62 行):

```python
def _make_default_config(node_type: str) -> dict[str, Any]:
    """为指定节点类型生成默认配置"""
    configs = {
        "UserInput": {},
        "FileSource": {"file_path": ""},
        "SimpleSplitter": {"chunk_size": 500, "overlap": 50},
        "Embedding": {"model_name": "BAAI/bge-small-zh-v1.5"},
        "Retriever": {
            "top_k": 5,
            "persist_directory": str(Path.home() / ".sage" / "vector_db"),
        },
        "ChromaRetriever": {
            "persist_directory": str(Path.home() / ".sage" / "vector_db"),
            "collection_name": "sage_docs",
            "top_k": 5,
        },
        "LLM": {
            "model_name": "qwen-max",
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        },
        "OpenAIGenerator": {
            "model_name": "gpt-3.5-turbo",
            "api_base": "https://api.openai.com/v1",
            "api_key": "",
            "temperature": 0.7,
        },
        "QAPromptor": {"template": ""},
        "PostProcessor": {},
        "Analytics": {},
        "TerminalSink": {},
    }
    return configs.get(node_type, {})

def _make_node(...):
    return {
        "data": {
            "label": label,
            "nodeId": node_type,
            "config": _make_default_config(node_type),  # ✅ 添加配置
        }
    }
```

______________________________________________________________________

### 修复 #2: Gateway 启动阻塞

**文件**: `packages/sage-gateway/src/sage/gateway/adapters/openai.py`

**问题**: `__init__` 中同步构建 RAG 索引，阻塞启动

**修复** (+27 行):

```python
import threading
from pathlib import Path

def __init__(self):
    self.session_manager = get_session_manager()

    # ✅ 后台线程构建索引（不阻塞启动）
    self._index_thread = threading.Thread(
        target=self._ensure_index_ready_background,
        daemon=True,
        name="RAGIndexBuilder"
    )
    self._index_thread.start()

def _ensure_index_ready_background(self):
    """后台构建RAG索引（不阻塞主线程）"""
    try:
        self._ensure_index_ready()
    except Exception as e:
        logger.error(f"Background index building failed: {e}")
```

______________________________________________________________________

### 修复 #3: Playground 配置验证

**文件**: `packages/sage-studio/src/sage/studio/services/playground_executor.py`

**问题**: 缺少配置验证，错误信息不清晰

**修复** (+45 行):

```python
def _validate_operator_configs(self, operator_configs: list[dict]) -> list[str]:
    """验证算子配置，返回错误列表"""
    errors = []
    for idx, op_config in enumerate(operator_configs, start=1):
        op_type = op_config.get("type", "Unknown")

        # 检查必需字段
        if "type" not in op_config:
            errors.append(f"节点 {idx}: 缺少 'type' 字段")

        if "config" not in op_config:
            errors.append(f"节点 {idx} ({op_type}): 缺少 'config' 字段")
            errors.append(f"  提示: 从 Chat 推荐生成的工作流可能缺少配置，请手动添加或重新生成")
        else:
            config = op_config["config"]
            # 检查特定算子的必需参数
            if op_type == "OpenAIGenerator" and "model_name" not in config:
                errors.append(f"节点 {idx} ({op_type}): 缺少 'model_name' 配置")
            # ... 更多验证

    return errors

def execute_simple_query(self, ...):
    # ✅ 执行前验证配置
    errors = self._validate_operator_configs(operator_configs)
    if errors:
        error_msg = "配置验证失败：\n" + "\n".join(errors)
        return {"error": error_msg, "success": False}
    # ... 执行逻辑
```

______________________________________________________________________

### 修复 #4: Gateway 导入路径错误

**文件**: `packages/sage-gateway/src/sage/gateway/adapters/openai.py`

**问题**: 尝试导入不存在的 `sage.libs.io.source` 和 `sage.libs.io.sink`

**修复** (简化实现):

```python
# ❌ 旧实现：使用 DataStream Pipeline
async def _execute_sage_pipeline(self, request, session):
    from sage.libs.foundation.io.source import TextSource  # ❌ 错误路径
    from sage.libs.foundation.io.sink import RetriveSink

    env = LocalEnvironment()
    env.from_source(source).map(retriever).map(promptor).map(generator).add_sink(sink)
    job = env.submit(autostop=True)
    # ...

# ✅ 新实现：直接调用算子
async def _execute_sage_pipeline(self, request, session):
    """执行 SAGE RAG Pipeline（简化版 - 直接调用算子）"""
    user_input = request.messages[-1].content

    # 1. 检索
    retriever = ChromaRetriever(retriever_config)
    retrieval_result = retriever.execute(user_input)

    # 2. 构建 Prompt
    promptor = QAPromptor(promptor_config)
    prompt_result = promptor.execute(retrieval_result)

    # 3. 生成回答
    generator = OpenAIGenerator(generator_config)
    final_result = generator.execute(prompt_result)

    return final_result["generated"]
```

______________________________________________________________________

### 修复 #5: ChromaRetriever 配置格式错误

**文件**: `packages/sage-gateway/src/sage/gateway/adapters/openai.py`

**问题**: 配置格式不匹配 `ChromaRetriever` 的期望

**根因**:

- `ChromaRetriever.__init__` 从 `config.get("chroma", {})` 获取配置
- 但我们直接传了顶层配置

**修复**:

```python
# ❌ 错误的配置
chroma_config = {
    "persist_directory": str(Path.home() / ".sage" / "vector_db"),
    "collection_name": "sage_docs",
    "top_k": 5,
    "embedding_model": "BAAI/bge-small-zh-v1.5",
}
retriever = ChromaRetriever(chroma_config)  # ❌ 配置验证失败

# ✅ 正确的配置
retriever_config = {
    "chroma": {  # ✅ 嵌套在 "chroma" 键下
        "persist_directory": str(Path.home() / ".sage" / "vector_db"),
        "persistence_path": str(Path.home() / ".sage" / "vector_db"),
        "collection_name": "sage_docs",
    },
    "top_k": 5,
    "embedding": {
        "model_name": "BAAI/bge-small-zh-v1.5",
    },
}
retriever = ChromaRetriever(retriever_config)  # ✅ 成功
```

______________________________________________________________________

## 测试验证

### 自动化测试

**验证脚本 1**: `verify_studio_fixes.py`

```bash
python verify_studio_fixes.py

# 结果:
#   workflow_config: ✅ PASS
#   gateway_startup: ✅ PASS  
#   playground_validation: ✅ PASS
#   通过率: 3/3 (100%)
```

**验证脚本 2**: `test_chat_rag.py`

```bash
python test_chat_rag.py

# 结果:
#   [步骤 1] 测试模块导入... ✅
#   [步骤 2] ChromaRetriever 配置... ✅
#   [步骤 3] 测试检索功能... ✅
#   [步骤 4] 测试 Promptor... ✅
#   [步骤 5] 测试 Generator... ✅
```

### 手动测试步骤

1. **重启服务**

   ```bash
   # 停止旧服务
   pkill -f sage-gateway
   sage studio stop

   # 启动新服务
   nohup sage-gateway --host localhost --port 8000 > ~/.sage/gateway.log 2>&1 &
   sage studio start
   ```

1. **测试新建聊天**

   - 访问 http://localhost:4200
   - 点击 "+ New Chat"
   - ✅ 应立即创建成功（\<1秒）

1. **测试 Chat 回答**

   - 输入: "什么是sage"
   - ✅ 应正常返回回答（无配置错误）

1. **测试工作流导出**

   - 在 Chat 中触发 Pipeline 推荐
   - 导出并导入到 Studio
   - ✅ 节点应包含默认配置

1. **测试 Playground 验证**

   - 尝试运行缺少配置的工作流
   - ✅ 应显示清晰的中文错误提示

______________________________________________________________________

## 修改文件统计

| 文件                           | 修改行数         | 说明                    |
| ------------------------------ | ---------------- | ----------------------- |
| `chat_pipeline_recommender.py` | +62              | 默认配置生成            |
| `openai.py` (Gateway)          | +27, -78         | 后台索引 + 简化Pipeline |
| `playground_executor.py`       | +45              | 配置验证                |
| **总计**                       | **~56 行净增加** | 3个文件                 |

**辅助文件**:

- `verify_studio_fixes.py`: 综合验证脚本
- `test_chat_rag.py`: RAG Pipeline 测试
- `diagnose_studio_issues.py`: 问题诊断工具
- `STUDIO_FIXES_FINAL.md`: 用户文档
- `studio-issues-fix.md`: 技术分析
- `studio-issues-fix-summary.md`: 详细总结

______________________________________________________________________

## 关键教训

### 1. **配置格式要仔细检查**

- 不同组件期望的配置结构可能不同
- 使用测试脚本快速验证配置格式

### 2. **后台任务不要阻塞启动**

- 耗时操作（如索引构建）应在后台线程执行
- 使用 `daemon=True` 确保主程序退出时清理

### 3. **错误信息要清晰友好**

- 配置错误应明确指出缺少什么字段
- 提供修复建议（如"请手动添加配置"）

### 4. **简化优于复杂**

- Gateway 中直接调用算子比构建完整 Pipeline 更简单
- 减少依赖和中间层，降低出错风险

### 5. **增量测试很重要**

- 每修复一个问题就测试
- 创建独立的测试脚本快速验证
- 避免"大爆炸"式修复导致新问题

______________________________________________________________________

## 现在可以做什么

### 用户视角

1. **正常使用 Chat**

   - 提问会得到 RAG 增强的回答
   - 响应速度快（索引在后台）

1. **导入工作流**

   - 从 Chat 推荐的工作流可以直接运行
   - 节点有合理的默认配置

1. **Playground 调试**

   - 配置错误会得到清晰提示
   - 知道如何修复问题

### 开发者视角

1. **扩展配置模板**

   - 在 `_make_default_config()` 添加新节点类型
   - 参考现有节点的配置结构

1. **增强验证逻辑**

   - 在 `_validate_operator_configs()` 添加更多检查
   - 为常见错误提供修复建议

1. **优化索引构建**

   - 监控 `~/.sage/gateway.log` 了解索引状态
   - 考虑添加索引构建进度UI

______________________________________________________________________

## 总结

🎉 **所有问题已彻底修复！**

- ✅ 5个问题全部解决
- ✅ 自动化测试 100% 通过
- ✅ Gateway 重启并加载新代码
- ✅ Studio 可正常使用

**下次遇到问题时**:

1. 先用 `test_chat_rag.py` 测试单个组件
1. 查看 `~/.sage/gateway.log` 了解后端错误
1. 使用浏览器开发者工具查看前端错误
1. 参考本文档了解常见问题和解决方案
