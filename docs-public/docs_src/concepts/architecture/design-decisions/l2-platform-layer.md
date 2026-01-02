# SAGE 架构层级：L2 平台层落地记录

> **最后更新**：2025-12-02（配合任务 A-E 文档刷新）

本文件记录了 SAGE 在 2025 Q1-Q4 期间对 L2 层（平台服务层）的演进过程、设计决策与最终结论，便于后续审查或再次调整。

## 背景回顾

- 2024 年底前的架构仅显式定义 L1（sage-common）与 L3（sage-kernel / sage-libs），L2 被视为“暂未需要”。
- 随着 RPC 队列、KV 存储、服务基类等组件在多处重复出现，跨层依赖问题逐渐放大：
  - `sage-common` 引入了对 `sage-kernel.runtime` 的隐式引用，违反“向下依赖”原则。
  - `sage-kernel` 与 `sage-middleware` 对 Queue/KV 抽象实现不一致，难以在 C++ 扩展和 Python 层复用。
- 2025-01 发起 **RPC Queue Refactoring**，提出将通用平台能力下沉到独立层。

## 决策 1：创建 `sage-platform` 包（L2）

- **时间**：2025-01-22，commit `1da88c0a`
- **目标**：提供 *单向向下* 的平台服务层，复用所有队列、存储、服务生命周期抽象。
- **迁移内容**：
  - `sage-kernel.runtime.communication.rpc_queue_descriptor` → `sage-platform.queue`
  - `sage-middleware.components.sage_db.backends` → `sage-platform.storage`
  - `sage-kernel.runtime.service.base_service` → `sage-platform.service`
- **影响**：
  - `pip install` 多了一个包（已包含在 meta-package `isage` 中）。
  - 所有 L3-L6 包继续仅依赖 L1-L2，未引入循环。

## 决策 2：采用工厂注册模式解决 L2→L3 反向依赖

### 问题

`sage-platform.queue.RPCQueueDescriptor` 需要实例化 `sage-kernel.runtime.communication.rpc.RPCQueue`，但 L2
不能直接 import L3。

### 方案

1. L2 暴露注册入口：

```python
# packages/sage-platform/src/sage/platform/queue/rpc_queue_descriptor.py
_rpc_queue_factory: QueueFactory | None = None

def register_rpc_queue_factory(factory: QueueFactory) -> None:
    global _rpc_queue_factory
    _rpc_queue_factory = factory
```

2. L3 初始化时注册真实实现：

```python
# packages/sage-kernel/src/sage/kernel/__init__.py
from sage.platform.queue import register_rpc_queue_factory
from sage.kernel.runtime.communication.rpc import RPCQueue


def _rpc_queue_factory(**kwargs):
    return RPCQueue(**kwargs)


register_rpc_queue_factory(_rpc_queue_factory)
```

3. 运行期由 L2 调用 `_rpc_queue_factory` 创建实例，保持 ABI/接口稳定。

**收益**：

- Leaky dependency 修复；`sage-common`、`sage-platform` 不再引入 L3。
- 可插拔：实验性 RPC/消息队列实现可在 L3/L4 注册。

## 决策 3：定义 L2 职责边界

| 模块                    | 说明                                   | 下游使用者                                         |
| ----------------------- | -------------------------------------- | -------------------------------------------------- |
| `sage.platform.queue`   | Python/Ray/RPC Queue 描述符、注册 API  | `sage-kernel.runtime`, `sage-middleware.operators` |
| `sage.platform.storage` | KV 抽象：Dict/Redis/RocksDB            | RAG 组件、控制面缓存                               |
| `sage.platform.service` | `BaseService`、生命周期 hook、健康检查 | CLI JobManager、Gateway、Studio 后端               |

> **不属于 L2 的内容**：LLM/Embedding 服务（仍在 L1 `sage-common.components`），任何算子/业务逻辑（L3+）。

## 决策 4：文档与工具链同步

- `docs-public/docs_src/dev-notes/package-architecture.md`、`concepts/architecture/*.md` 更新为“11 个包 +
  meta-package”。
- `docs-public/docs_src/concepts/architecture/package-structure.md` 显式标注 L2 及其 C++ 依赖（无）。
- `docs-public/docs_src/guides/packages/sage-platform/overview.md`（新增）覆盖 API。
- `sage-dev quality` 检查新增 `layer.yaml` 规则：确保任何新包声明的层级不违反 L1→L6 单向依赖。

## 仍需关注的事项

1. **文档一致性**：所有层级描述都应提及 L2；本文件为历史记录，不再将 “缺失 L2” 作为现状。
1. **扩展接口**：若未来需要统一 Streaming Storage / Scheduler，可继续在 L2 扩展子模块。
1. **CI 检查**：`tools/install/check_tool_versions.sh` 已纳入 `sage-platform` 依赖的版本锁定，防止缺包。

## TL;DR

- L2 层已经正式存在，包名 `sage-platform`，职责是复用 Queue/Storage/Service 基础设施。
- 通过工厂注册模式避免 L2 → L3 直接依赖，确保分层单体架构的单向性。
- 所有文档/示例现已同步，若发现仍有“L2 缺失”描述，请直接更新引用或提 Issue。

## 检查清单

### ✅ sage-common 职责清晰

- [x] 只包含基础组件
- [x] 无执行引擎代码
- [x] 无领域逻辑

### ✅ sage-kernel 职责清晰

- [x] 执行引擎核心
- [x] 运行时基础设施属于执行引擎
- [x] 无领域算子

### ✅ 依赖关系正确

- [x] sage-common 无依赖
- [x] sage-kernel 只依赖 sage-common
- [x] 无循环依赖

## 结论

**建议采用方案 1：保持现状，更新文档说明。**

SAGE 的两层基础架构（L1: common + L3: kernel）是合理的：

- sage-common 提供共享基础设施
- sage-kernel 提供执行引擎（包含运行时基础设施）

这种设计符合 SAGE 作为流式处理系统的特点，无需强行引入 L2 层。

______________________________________________________________________

**日期**: 2025-10-22\
**作者**: SAGE Architecture Review
