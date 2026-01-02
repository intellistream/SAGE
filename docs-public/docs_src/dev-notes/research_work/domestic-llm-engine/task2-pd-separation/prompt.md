# Prompt · 课题二扩展 / PR5：scheduler_ir（PD 分离 + IR/策略迁移）

你是负责 **scheduler_ir** 的架构师。请实现 Prefill/Decode 解耦的执行图 IR、策略迁移、事件循环精简，并与 LMDeploy patched 引擎完成指令/IR
下发，替换旧的 `pd_routing.py`/`control_plane/strategies/*` 路径。

______________________________________________________________________

## 前置依赖

- 协议/类型：`IRNode`, `IRGraph`, `ExecutionPlan`, `ExecutorAPI`,
  `PDSeparator`（需在本课题落地）；`CapabilityDescriptor`, `KVCacheSchema` 来自 PR1。
- 上游：`core` 精简管理器；`kv_runtime/kv_policy/prefix_reuse` 提供 KV 预算/淘汰建议；`comm_backend` 负责传输；`accel` 负责
  kv_precision/加速策略。
- 引擎 Hook：LMDeploy `scheduler` 补丁已允许外部 IR/决策注入。

______________________________________________________________________

## 背景与目标

- 目标：策略输出 → IR → 执行计划 → 引擎，支持 PD 分离、策略可插拔、IR 优化（融合/拓扑/设备选择）。
- 取代：旧的 `control_plane/strategies/*`、`pd_routing.py`、`parallelism.py`、`topology.py` 等全部迁移到
  `scheduler_ir/`。

______________________________________________________________________

## 研究内容（Scope）

1. **IR 定义与构建**

- 数据结构：`IRNode{type, inputs, outputs, config, device}`, `IRGraph`,
  `ExecutionPlan{plan_id, ir_graph, request_ids, target_instance_id}`。
- `IRBuilder.build(requests)`：接收请求/策略结果，生成带 PD 分离标签的 IRGraph。

2. **IR 优化与 PD 分离**

- `IROptimizer`: 拓扑排序、循环检测、算子融合（prefill chunking, decode micro-batch）、设备/并行策略选择。
- `PDSeparator.split`: Prefill/Decode 解耦（可扩展 AF）；输出子图与资源需求。

3. **执行接口与策略迁移**

- `ExecutorAPI.submit_plan/cancel/status`：将 ExecutionPlan 下发给引擎（LMDeploy patched scheduler）。
- 策略迁移：将 `control_plane/strategies/` 中 fifo/priority/slo_aware/adaptive/aegaeon/hybrid 迁移为
  `scheduler_ir/strategies/`，适配 IR。

4. **与其他模块协同**

- `kv_runtime/kv_policy`: IR 构建时获取 KV 预算/淘汰建议；执行计划可包含迁移/复用指令。
- `comm_backend`: 提供通信代价/拓扑信息，辅助设备/融合决策。
- `accel`: 提供 kv_precision/投机解码/CoT 加速控制字段。

5. **事件循环与观测**

- 精简 Control Plane 事件循环：队列管理、计划分发、超时/重试；暴露遥测（plan latency, success rate）。
- 日志/trace：IR 生成、优化、下发的决策路径可追踪。

______________________________________________________________________

## 目录结构（硬约束）

```
scheduler_ir/
├── __init__.py
├── ir_types.py          # IRNode/IRGraph/ExecutionPlan
├── builder.py           # IRBuilder
├── optimizer.py         # IROptimizer
├── pd_separation.py     # PDSeparator
├── executor_api.py      # ExecutorAPI
├── strategies/          # 迁移自 control_plane/strategies/*
│   ├── fifo.py
│   ├── priority.py
│   ├── slo_aware.py
│   ├── adaptive.py
│   ├── aegaeon.py
│   └── hybrid.py
└── benchmarks/
```

______________________________________________________________________

## Success Criteria

- 功能：
  - IR 可构建/优化/下发；PD 分离生效；策略迁移完整。
  - 与 LMDeploy patched 引擎联调通过，计划可执行。
- 性能：IR 构建/优化延迟可量化；PD 分离后吞吐/TTFT/TPOT 无回退（或提升）。
- 工程化：
  - 单测覆盖 IR 拓扑、融合、PD 分离、策略迁移；集成测验证下发路径。
  - 目录与接口仅使用 `scheduler_ir/`，不再引用旧 control_plane 文件。
  - 观测：暴露 plan latency/queue 延迟/策略命中率。

______________________________________________________________________

## 交付物

1. 设计文档：IR 定义、优化规则、PD 分离、策略迁移、与其他模块协同。
1. 核心代码：`scheduler_ir/` 全量实现 + 策略迁移 + ExecutorAPI。
1. 测试：单测（IR 构建/优化/分离/策略），集成测（LMDeploy patched 下发），bench（队列延迟/吞吐）。
1. Benchmark：多策略对比（fifo/priority/slo_aware/adaptive/aegaeon/hybrid），输出 JSON/Markdown。
