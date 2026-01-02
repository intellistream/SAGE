# sageLLM Control Plane 增强 - 任务书

> **版本**: v1.0\
> **创建日期**: 2025-12-02\
> **目标**: 统一 Control Plane 入口，增强引擎管理能力，完善测试覆盖

______________________________________________________________________

## 📋 任务总览

```
┌─────────────────────────────────────────────────────────────────┐
│                     可并行执行的任务                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Task A    │    │   Task B    │    │   Task C    │        │
│  │             │    │             │    │             │        │
│  │ 统一入口    │    │ 健康检查   │    │ Embedding   │        │
│  │ + 删除旧API │    │ + 自动重启 │    │ GPU 支持    │        │
│  │ + 代码清理  │    │            │    │             │        │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
│         │                  │                  │                │
│         └──────────────────┼──────────────────┘                │
│                            ↓                                    │
│                   ┌─────────────────┐                          │
│                   │     Task D      │                          │
│                   │                 │                          │
│                   │   测试 + 文档   │                          │
│                   │                 │                          │
│                   └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

| 任务       | 描述                                   | 可并行     | 预计时间 |
| ---------- | -------------------------------------- | ---------- | -------- |
| **Task A** | 统一客户端入口 + 删除旧 API + 代码清理 | ✅         | 3-4 天   |
| **Task B** | 引擎健康检查 + 自动重启                | ✅         | 2 天     |
| **Task C** | Embedding 引擎 GPU 支持                | ✅         | 1 天     |
| **Task D** | 单元测试 + 文档更新                    | 等待 A/B/C | 2-3 天   |

______________________________________________________________________

## Task A: 统一客户端入口重构

````
【AI 提示词】
你正在为 SAGE 项目重构 UnifiedInferenceClient，实现统一的 Control Plane 入口。

## 背景
当前 UnifiedInferenceClient 有三种创建方式（create_auto、直接构造、create_with_control_plane），
这违反了"所有请求必须通过 Control Plane 管理"的设计原则。需要统一为单一入口。

## 任务目标

### 1. 实现新的 `create()` 方法
```python
@classmethod
def create(
    cls,
    *,
    control_plane_url: str | None = None,  # 连接已运行的 Control Plane
    embedded: bool = False,                 # 内嵌模式
    default_llm_model: str | None = None,
    default_embedding_model: str | None = None,
    scheduling_policy: str = "adaptive",
    timeout: float = 60.0,
) -> UnifiedInferenceClient:
    """唯一入口：连接外部 CP 或启动内嵌 CP"""
````

### 2. 删除旧 API（完全移除，不是 deprecated）

- 删除 `create_auto()` 方法
- 删除 `create_with_control_plane()` 方法
- 删除 `UnifiedClientMode.SIMPLE` 及相关代码路径
- 将 `__init__()` 改为私有（只能通过 `create()` 调用）

### 3. 代码清理

- 补充 `control_plane/__init__.py` 导出：GPUResourceManager, EngineLifecycleManager 等
- 统一端口管理：移除 EngineLifecycleManager 中的重复端口逻辑，集中到 ControlPlaneManager
- 更新所有调用方（examples/, tests/, 其他包）

## 修改文件

- `packages/sage-llm-core/src/sage/llm/unified_client.py`
- `packages/sage-llm-core/src/sage/llm/control_plane/__init__.py`
- `packages/sage-llm-core/src/sage/llm/control_plane/engine_lifecycle.py`
- `packages/sage-llm-core/src/sage/llm/control_plane/manager.py`
- 所有使用旧 API 的文件（搜索 create_auto, create_with_control_plane）

## 验收标准

```python
# ✅ 唯一正确用法
client = UnifiedInferenceClient.create()
client = UnifiedInferenceClient.create(control_plane_url="http://localhost:8000/v1")
client = UnifiedInferenceClient.create(embedded=True)

# ❌ 以下应该报错
client = UnifiedInferenceClient.create_auto()  # AttributeError
client = UnifiedInferenceClient(...)           # 被阻止
```

```

**涉及文件**:
- `unified_client.py` - 核心重构
- `control_plane/__init__.py` - 补充导出
- `engine_lifecycle.py` - 移除重复端口逻辑
- `manager.py` - 统一端口管理
- 所有调用方文件

**验收标准**:
- 只有 `create()` 一个入口
- 旧 API 完全删除
- 所有现有测试通过

---

## Task B: 引擎健康检查与自动重启

```

【AI 提示词】 你正在为 SAGE 项目的 Control Plane 添加引擎健康检查和自动重启功能。

## 背景

当前 EngineLifecycleManager 只通过 psutil 检查进程存活，无法检测服务实际可用性， 且引擎崩溃后不会自动恢复。

## 任务目标

### 1. EngineLifecycleManager 添加健康检查

```python
async def health_check(self, engine_id: str, timeout: float = 5.0) -> bool:
    """HTTP 检查引擎健康状态"""
    # LLM: GET /health 或 /v1/models
    # Embedding: GET /health

async def health_check_all(self) -> dict[str, bool]:
    """检查所有引擎"""
```

### 2. ControlPlaneManager 添加自动重启

- 配置项: `auto_restart=True`, `max_restart_attempts=3`
- 后台循环定期检查引擎健康
- 连续 N 次失败后触发重启
- 指数退避重试（1s, 2s, 4s...）
- 超过最大重试次数后标记为 FAILED

## 修改文件

- `packages/sage-common/.../control_plane/engine_lifecycle.py`
- `packages/sage-common/.../control_plane/manager.py`

## 验收标准

- 引擎启动后健康检查返回 True
- 手动 kill 引擎进程后，Control Plane 在配置时间内自动重启
- 超过重试次数后，引擎状态变为 FAILED 并记录日志

```

**涉及文件**:
- `engine_lifecycle.py` - 健康检查方法
- `manager.py` - 自动重启循环

**验收标准**:
- `health_check()` 正确检测引擎状态
- 引擎崩溃后自动重启
- 重试耗尽后正确标记 FAILED

---

## Task C: Embedding 引擎 GPU 支持

```

【AI 提示词】 你正在为 SAGE 项目的 Embedding 引擎添加可选的 GPU 支持。

## 背景

当前 `engine_kind="embedding"` 时强制跳过 GPU 分配，但某些 Embedding 模型 （如 BGE-M3）在 GPU 上运行效果更好。需要支持可选 GPU。

## 任务目标

### API 变更

在以下位置添加 `use_gpu: bool | None = None` 参数：

- `ControlPlaneManager.request_engine_startup()`
- `EngineStartRequest` (REST API Pydantic 模型)
- `PresetEngine` (预设系统)
- CLI `sage llm engine start --use-gpu / --no-gpu`

### 行为定义

- `use_gpu=None` (默认): LLM 用 GPU，Embedding 不用
- `use_gpu=True`: 强制使用 GPU
- `use_gpu=False`: 强制不用 GPU

### 实现要点

- 修改 `manager.py` 中的 `needs_gpu` 判断逻辑
- Embedding 服务器启动时传递 `--device cuda` 参数
- 预设 YAML 支持 `use_gpu` 字段

## 修改文件

- `packages/sage-common/.../control_plane/manager.py`
- `packages/sage-common/.../unified_api_server.py`
- `packages/sage-common/.../presets/models.py`
- `packages/sage-cli/.../commands/apps/llm.py`

## 验收标准

```bash
# 默认不用 GPU
sage llm engine start BAAI/bge-m3 --engine-kind embedding

# 显式使用 GPU
sage llm engine start BAAI/bge-m3 --engine-kind embedding --use-gpu

# 预设文件支持
engines:
  - name: embed
    kind: embedding
    model: BAAI/bge-m3
    use_gpu: true
```

```

**涉及文件**:
- `manager.py` - 核心逻辑
- `unified_api_server.py` - REST API
- `presets/models.py` - 预设模型
- `llm.py` (CLI) - 命令行参数

**验收标准**:
- `--use-gpu` 选项可用
- 预设支持 `use_gpu` 字段
- GPU 正确分配给 Embedding 引擎

---

## Task D: 测试与文档

```

【AI 提示词】 你正在为 SAGE 项目的 Control Plane 增强功能编写测试和更新文档。

## 前置条件

Task A/B/C 已完成。

## 任务目标

### 1. 单元测试

创建以下测试文件：

**test_gpu_manager.py** (使用 Mock 模式)

- 初始化、状态获取、资源分配/释放、显存估算

**test_engine_lifecycle.py** (mock subprocess)

- spawn/stop 引擎、状态转换、健康检查

**test_unified_client.py**

- create() 各种模式、旧 API 已删除确认

**test_presets.py**

- YAML 解析、内置预设、use_gpu 字段

### 2. 文档更新

更新以下文档，移除旧 API 示例，添加新 `create()` 用法：

- `.github/copilot-instructions.md` - sageLLM 架构部分
- `docs/dev-notes/l1-common/README.md` - 使用示例
- `docs/dev-notes/l1-common/control-plane-enhancement.md` - 添加统一入口章节

## 测试位置

- `packages/sage-common/tests/unit/components/sage_llm/`

## 验收标准

```bash
pytest packages/sage-common/tests/unit/components/sage_llm/ -v
# 所有测试通过

sage-dev quality --check-only
# 无 lint 错误
```

- 文档中无旧 API (create_auto, create_with_control_plane) 引用

```

**涉及文件**:
- `tests/unit/components/sage_llm/test_*.py` (新建)
- `.github/copilot-instructions.md`
- `docs/dev-notes/l1-common/*.md`

**验收标准**:
- 所有测试通过
- 文档示例使用新 API
- `sage-dev quality` 通过

---

## 📅 执行计划

```

并行执行 (Week 1): ├── 开发者 1: Task A (统一入口重构) ────────────────► 3-4 天 ├── 开发者 2: Task B (健康检查) ──────► 2
天 └── 开发者 3: Task C (Embedding GPU) ─► 1 天

顺序执行 (Week 2): └── Task D (测试 + 文档) ─────────────────────────► 2-3 天

```

**总计**: 约 **1.5 周** (如果并行) 或 **2 周** (如果串行)

---

## ✅ 完成检查清单

- [x] **Task A: 统一入口重构**
  - [x] `create()` 方法实现
  - [x] 旧 API 完全删除
  - [x] `__init__.py` 导出补充
  - [x] 端口管理统一
  - [x] 所有调用方更新

- [x] **Task B: 健康检查**
  - [x] `health_check()` 方法
  - [x] 自动重启循环
  - [x] 指数退避重试

- [x] **Task C: Embedding GPU**
  - [x] `use_gpu` 参数贯穿
  - [x] CLI 选项
  - [x] 预设支持

- [x] **Task D: 测试与文档**
  - [x] 单元测试通过
  - [x] 文档更新完成
  - [x] `sage-dev quality` 通过

- [x] **最终验收**
  - [x] `sage-dev project test --coverage` 通过
  - [x] 所有示例可运行

---

## 🔗 相关资源

- Issue: #1284
- 分支: `feature/control-plane-enhancement`
- 原始设计: `docs/dev-notes/l1-common/control-plane-enhancement.md`
```
