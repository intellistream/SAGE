# Intelligent LLM Client 重构文档

## 背景

**问题：** `sage-gateway` (L6) 直接依赖 `sage-tools` (L6) 的 LLM 检测工具，违反了架构规则（L6 不能依赖 L6）。

**错误示例：**
```python
# ❌ 架构违规：L6 -> L6 依赖
from sage.tools.cli.utils.llm_detection import detect_vllm
```

## 解决方案

### 1. 在 L1 层创建智能 LLM 客户端

**位置：** `packages/sage-common/src/sage/common/components/sage_llm/client.py`

**核心功能：**
- ✅ 自动检测本地 vLLM 服务（端口 8001, 8000）
- ✅ 自动降级到云端 API（如 DashScope）
- ✅ 支持用户显式配置（环境变量）
- ✅ 缓存检测结果，避免重复探测
- ✅ 统一的 OpenAI 兼容接口
- 🎯 **集成 Control Plane** - 高级多实例调度（可选）

**架构优势：**
- L1 层组件，所有层都可使用
- 零依赖其他 SAGE 包（仅依赖 `openai` 外部库）
- 自包含的服务发现逻辑
- 可选的 Control Plane 集成，无需强制依赖

### 2. 两种使用模式

#### 模式 1: Simple Mode（简单模式 - 默认）

**适用场景：**
- 单实例 vLLM 服务或云端 API
- 快速启动，低开销
- 基本的请求/响应

**使用示例：**

```python
from sage.common.components.sage_llm.client import IntelligentLLMClient

# 自动检测并使用最佳服务
client = IntelligentLLMClient.create_auto()

# 生成响应
response = client.chat([
    {"role": "user", "content": "Hello!"}
])
print(response)
```

#### 模式 2: Control Plane Mode（控制平面模式 - 高级）

**适用场景：**
- 多实例 vLLM 部署
- 需要 SLO 保证（延迟、优先级）
- 需要负载均衡和故障转移
- 需要 Prefilling/Decoding 分离优化
- 需要性能监控和指标

**使用示例：**

```python
from sage.common.components.sage_llm.client import IntelligentLLMClient

# 配置多实例 Control Plane
client = IntelligentLLMClient.create_with_control_plane(
    instances=[
        {
            "host": "localhost",
            "port": 8001,
            "model_name": "llama-2-7b",
            "instance_type": "PREFILL",  # 专门处理预填充
            "gpu_count": 2,
        },
        {
            "host": "localhost",
            "port": 8002,
            "model_name": "llama-2-7b",
            "instance_type": "DECODE",   # 专门处理解码
            "gpu_count": 1,
        },
        {
            "host": "192.168.1.100",
            "port": 8001,
            "model_name": "llama-2-13b",  # 不同机器、不同模型
            "gpu_count": 4,
        },
    ],
    scheduling_policy="slo_aware",      # SLO 感知调度
    routing_strategy="topology_aware",   # 拓扑感知路由
    enable_pd_separation=True,           # 启用 P/D 分离
)

# 高优先级请求，1秒 SLO
response = client.chat(
    messages=[{"role": "user", "content": "Urgent query!"}],
    priority="HIGH",
    slo_deadline_ms=1000,
    max_tokens=500,
)

# 查看性能指标
metrics = client.get_metrics()
print(f"P95 延迟: {metrics['p95_latency_ms']}ms")
print(f"SLO 合规率: {metrics['slo_compliance_rate']}%")

# 查看实例状态
instances = client.get_instances()
for inst in instances:
    print(f"{inst['instance_id']}: 负载={inst['current_load']}, "
          f"健康={inst['is_healthy']}")

# 清理资源（重要！）
client.cleanup()
```

**Control Plane 调度策略：**
- `fifo`: 先进先出（最简单）
- `priority`: 基于优先级（HIGH > NORMAL > LOW）
- `slo_aware`: SLO 感知（考虑截止时间）
- `cost_optimized`: 成本优化（选择最经济的实例）
- `adaptive`: 自适应（根据负载动态调整）

**路由策略：**
- `load_balanced`: 负载均衡（默认）
- `affinity`: 会话亲和性
- `locality`: 数据局部性
- `topology_aware`: 拓扑感知（NVLINK、NUMA）

### 3. 使用示例

#### 自动检测模式（推荐）

```python
from sage.common.components.sage_llm.client import IntelligentLLMClient

# 自动检测并使用最佳服务
client = IntelligentLLMClient.create_auto()

# 生成响应
response = client.chat([
    {"role": "user", "content": "Hello!"}
])
print(response)
```

#### 手动配置模式

```python
# 使用本地 vLLM
client = IntelligentLLMClient(
    model_name="meta-llama/Llama-2-7b-chat-hf",
    base_url="http://localhost:8001/v1",
    api_key="empty"
)

# 或使用云端 API
client = IntelligentLLMClient(
    model_name="qwen-max",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="your-api-key"
)
```

### 4. 环境变量配置

```bash
# 显式配置云端服务
export SAGE_CHAT_MODEL="qwen-max"
export SAGE_CHAT_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export SAGE_CHAT_API_KEY="sk-xxx"

# 显式配置本地 vLLM
export SAGE_CHAT_MODEL="meta-llama/Llama-2-7b-chat-hf"
export SAGE_CHAT_BASE_URL="http://localhost:8001/v1"
# SAGE_CHAT_API_KEY 可省略（本地服务）
```

## 服务检测逻辑

**优先级（从高到低）：**

1. **用户显式配置** - 环境变量 `SAGE_CHAT_BASE_URL` 存在
   - 跳过自动检测，直接使用配置的端点

2. **本地 vLLM 自动检测** - 探测本地端点
   - `http://localhost:8001/v1` （推荐，避免与 Gateway 8000 冲突）
   - `http://127.0.0.1:8001/v1`
   - `http://localhost:8000/v1` （vLLM 默认端口）
   - `http://127.0.0.1:8000/v1`

3. **云端 API 降级** - 本地服务不可用时
   - 使用 DashScope 默认端点
   - 需要设置 `SAGE_CHAT_API_KEY`

**探测机制：**
- HTTP GET `/v1/models` 端点
- 超时时间：1.5 秒
- 失败静默处理（继续尝试下一个端点）

## 架构改进

### Before (违规)

```
┌──────────────┐
│ sage-gateway │ (L6)
└──────┬───────┘
       │ ❌ 非法依赖
       ↓
┌──────────────┐
│ sage-tools   │ (L6)
│ llm_detection│
└──────────────┘
```

### After (合规)

```
┌──────────────┐
│ sage-gateway │ (L6)
└──────┬───────┘
       │ ✅ 合法依赖
       ↓
┌──────────────┐
│ sage-common  │ (L1)
│ sage_llm     │
│ client.py    │
└──────────────┘
```

## Gateway 重构

**文件：** `packages/sage-gateway/src/sage/gateway/rag_pipeline.py`

**变更：**

```python
# Before: 手动检测 + 配置逻辑
def _detect_local_vllm(self) -> tuple[str | None, str | None]:
    from sage.tools.cli.utils.llm_detection import detect_vllm  # ❌ L6 -> L6
    # ... 50+ 行检测逻辑

# After: 简单调用 L1 客户端
def _get_llm_client(self):
    from sage.common.components.sage_llm.client import IntelligentLLMClient
    if self._llm_client is None:
        self._llm_client = IntelligentLLMClient.create_auto()  # ✅ 自动检测
    return self._llm_client
```

**代码减少：** ~100 行 → ~10 行

## 未来规划

### sage-libs 集成重构

`sage-libs/integrations/openaiclient.py` 应该：
1. ~~自己实现 OpenAI 客户端~~ → 依赖 L1 的 `IntelligentLLMClient`
2. 保留高级集成逻辑（如 ChromaDB、Milvus 集成）

```python
# 未来重构建议
# sage-libs/integrations/openaiclient.py
from sage.common.components.sage_llm.client import IntelligentLLMClient

class OpenAIClient(IntelligentLLMClient):
    """高级 OpenAI 客户端（L3）

    基于 L1 的 IntelligentLLMClient，添加：
    - 高级重试逻辑
    - 流式处理优化
    - 与 sage-libs 其他组件集成
    """
    pass
```

## 测试验证

### 单元测试

```bash
# 测试配置检测
python -c "
from sage.common.components.sage_llm.client import IntelligentLLMClient
config = IntelligentLLMClient._detect_llm_config()
print(config)
"
```

### 架构检查

```bash
# 运行架构合规性检查
sage-dev architecture check

# 预期结果：✅ 架构合规性检查通过！
```

## 迁移指南

### 对于使用 `sage.tools.cli.utils.llm_detection` 的代码

**替换前：**
```python
from sage.tools.cli.utils.llm_detection import detect_vllm

vllm_info = detect_vllm()
if vllm_info:
    base_url = vllm_info.base_url
    model = vllm_info.default_model
```

**替换后：**
```python
from sage.common.components.sage_llm.client import IntelligentLLMClient

# 方式 1: 直接使用客户端（推荐）
client = IntelligentLLMClient.create_auto()

# 方式 2: 仅获取配置
config = IntelligentLLMClient._detect_llm_config()
base_url = config["base_url"]
model = config["model_name"]
```

### 对于使用 `sage.libs.integrations.openaiclient.OpenAIClient` 的代码

**替换前：**
```python
from sage.libs.integrations.openaiclient import OpenAIClient

client = OpenAIClient(
    model_name=model,
    base_url=base_url,
    api_key=api_key,
    seed=42
)
response = client.generate(messages)
```

**替换后：**
```python
from sage.common.components.sage_llm.client import IntelligentLLMClient

# 自动检测（推荐）
client = IntelligentLLMClient.create_auto()
response = client.chat(messages)

# 或手动配置
client = IntelligentLLMClient(
    model_name=model,
    base_url=base_url,
    api_key=api_key
)
response = client.chat(messages)
```

**兼容性：** `IntelligentLLMClient` 同时提供 `chat()` 和 `generate()` 方法

## 相关文件

**新增：**
- `packages/sage-common/src/sage/common/components/sage_llm/client.py`

**修改：**
- `packages/sage-common/src/sage/common/components/sage_llm/__init__.py`
- `packages/sage-gateway/src/sage/gateway/__init__.py` (添加 `__layer__` 标记)
- `packages/sage-gateway/src/sage/gateway/rag_pipeline.py` (重构)

**待弃用：**
- `packages/sage-tools/src/sage/tools/cli/utils/llm_detection.py` (L6 CLI 工具保留)
- `packages/sage-libs/src/sage/libs/integrations/openaiclient.py` (待重构为依赖 L1)

## 架构合规性

✅ **检查结果：** 无违规

```
📊 架构合规性检查报告
═══════════════════════════════════════
📈 统计信息:
  • 检查文件数: 213
  • 导入语句数: 0
  • 非法依赖: 0
  • 模块位置错误: 0
  • 内部导入: 0
  • 缺少标记: 0
═══════════════════════════════════════
✅ 架构合规性检查通过！
```

## 总结

这次重构实现了：

1. ✅ **解决架构违规** - 消除 L6 → L6 非法依赖
2. ✅ **代码复用** - L1 层组件可被所有层使用
3. ✅ **简化代码** - Gateway 代码从 ~150 行减少到 ~50 行
4. ✅ **智能化** - 自动检测本地服务，无缝降级
5. ✅ **可配置** - 支持环境变量显式配置
6. ✅ **统一接口** - OpenAI 兼容，易于迁移

**设计原则：**
- 📦 **关注点分离** - LLM 客户端逻辑在 L1，业务逻辑在 L6
- 🔄 **可扩展性** - 未来可轻松添加更多服务类型
- 🛡️ **架构合规** - 严格遵守 SAGE 分层架构
- 🎯 **开发体验** - 简单的 API，合理的默认配置
