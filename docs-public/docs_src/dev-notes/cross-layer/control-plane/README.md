```markdown
# Control Plane 开发与路由修复

跨层 Control Plane 文档汇总，涵盖引擎调度任务规划与关键路由修复记录，方便从开发视角整体理解 sageLLM 控制平面的演进。

## 快速索引

- [Control Plane 任务规划](#control-plane-任务规划)
- [路由与请求分发修复](#路由与请求分发修复)

---

## Control Plane 任务规划

> 对应历史任务文档：`LLM_CONTROL_PLANE_TASKS.md`

该部分聚焦于 LLM Control Plane 的总体演进方向，包括：

- 引擎生命周期管理与状态机设计
- GPU 资源调度与监控
- 控制面 API 统一化与可观测性

### 目标概览

- 提供统一的引擎启动 / 停止 / 状态查询接口
- 支持多类型引擎（LLM / Embedding）的一致管理
- 通过统一的 REST API 与 CLI 命令暴露控制能力

### 关键设计点（节选）

- 使用 `EngineState` 枚举对引擎生命周期进行建模，例如：`STARTING → READY → DRAINING → STOPPED → ERROR`
- 在控制平面中集中维护引擎元数据（模型、端口、运行时类型、资源占用等），避免各服务各自维护状态。
- 引入 GPU 资源管理器，对显存占用进行估算与预留，确保新引擎启动不会压垮现有负载。

完整的任务拆解与 AI 提示词保留在原始文档 `LLM_CONTROL_PLANE_TASKS.md` 中，可用于追溯每一阶段的实现背景和开发上下文。

---

## 路由与请求分发修复

> 对应历史任务文档：`CONTROL_PLANE_ROUTING_FIX.md`

该部分记录了 Control Plane 在请求路由与后端发现方面的关键修复点，确保：

- 控制平面能正确感知各引擎实例的可用性
- LLM 与 Embedding 请求被路由到合适的后端
- 在引擎上下线、失败恢复等场景下具备稳定的故障转移能力

### 修复背景

- 早期实现中，请求路由逻辑分散在多个模块中，导致：
  - 新增引擎后，某些路径无法正确发现
  - 部分健康检查结果没有反馈到具体路由决策中
- 统一路由修复的目标是让 Control Plane 成为唯一的真源（source of truth）：
  - 后端可用性由 Control Plane 决定
  - 客户端与 Gateway 通过统一 API 获取后端列表

### 关键改动思路（节选）

- 在 Control Plane Manager 中集中实现后端注册、心跳与摘除逻辑。
- 为 LLM / Embedding 请求分别建模，避免路由混淆。
- 为客户端提供统一的后端发现接口（例如 `/v1/management/backends`），使客户端无需关心具体路由细节。

更多细节（包括具体的修复案例与相关代码路径）可参考 `CONTROL_PLANE_ROUTING_FIX.md`，该文件保留了完整的调试记录与边界场景分析。

---

## 关联文档

- L1 层 Control Plane 增强与 Gateway 统一任务：`dev-notes/l1-common/control-plane-roadmap-tasks.md`、`dev-notes/l1-common/unified-gateway-tasks.md`、`dev-notes/l1-common/control-plane-enhancement.md`、`dev-notes/l1-common/PR-unified-gateway.md`
- 包架构与层级说明：`dev-notes/package-architecture.md`
- Gateway 与 Control Plane 公开接口说明：参见 `packages/sage-llm-gateway/src/sage/gateway/` 与相关指南文档。

```
