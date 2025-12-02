# SAGE Studio 问题修复方案

## 问题诊断结果

### 问题1: chat生成的工作流导入进studio是空壳
**根本原因**: `chat_pipeline_recommender.py` 生成的节点缺少 `config` 字段

**问题代码** (`packages/sage-studio/src/sage/studio/services/chat_pipeline_recommender.py:45-58`):
```python
def _make_node(node_id: str, label: str, node_type: str, description: str, order: int) -> dict:
    return {
        "id": node_id,
        "type": "custom",
        "position": {"x": 160, "y": 120 * order},
        "data": {
            "label": label,
            "nodeId": node_type,  # 节点类型
            "description": description,
            "status": "idle",
            # ❌ 缺少 "config": {} 字段！
        },
    }
```

**Studio Playground 期望的格式**:
```python
{
    "type": "OpenAIGenerator",  # 操作符类型
    "config": {                  # ❌ 这个字段是必须的！
        "model_name": "gpt-3.5-turbo",
        "api_base": "https://api.openai.com/v1",
        "api_key": "",
        ...
    }
}
```

### 问题2: 新建聊天时好时坏
**诊断结果**: ✅ SessionManager 后端工作正常

**可能原因**:
1. 前端 API 调用失败（网络/超时）
2. Gateway 索引构建阻塞初始化（`_ensure_index_ready()` 耗时）
3. 并发创建导致竞态条件

### 问题3: studio playground输入问题回答报错
**诊断结果**: ✅ PlaygroundExecutor 基础逻辑正确

**可能原因**:
1. 节点缺少必需的 `config` 参数
2. API Key 未正确加载
3. 模型端点配置错误

## 修复方案

### 修复1: 为推荐的节点添加默认配置

**文件**: `packages/sage-studio/src/sage/studio/services/chat_pipeline_recommender.py`

**修改**: 添加 `_make_default_config()` 函数并更新 `_make_node()`

### 修复2: 优化 Gateway 索引构建

**文件**: `packages/sage-gateway/src/sage/gateway/adapters/openai.py`

**修改**: 将 `_ensure_index_ready()` 移到后台线程，避免阻塞启动

### 修复3: 增强 Playground 错误处理

**文件**: `packages/sage-studio/src/sage/studio/services/playground_executor.py`

**修改**: 添加更详细的错误信息和配置验证

## 实施步骤

1. ✅ 诊断问题根源
2. ⏳ 实施修复代码
3. ⏳ 运行测试验证
4. ⏳ 提交代码和文档

## 详细修复代码

见下方修复文件...
