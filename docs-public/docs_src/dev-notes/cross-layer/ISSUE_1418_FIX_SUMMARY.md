# Issue #1418 修复：上游算子并行度不为 1 时导致的任务丢失

## 问题概述

**Bug**: 当上游算子有多个并行实例（并行度 ≥ 2）时，会导致下游的任务丢失

**根本原因**: 多个并行实例异步完成，其中任意一个先完成时会广播 StopSignal 给下游，导致下游提前停止接收其他未完成的上游实例的数据。

**触发条件**: 任何上游并行度 ≥ 2 的配置（N:1, N:N, N:M）都会 100% 触发

## 修复方案

实现了**方案 1：追踪上游并行度**，核心思路：

1. **初始化阶段**: 在接收第一个 StopSignal 时，初始化上游并行度跟踪
1. **接收阶段**: 按照源算子实例来追踪 StopSignal（记录哪些实例已发送 StopSignal）
1. **决策阶段**: 只有当**所有**上游实例都发送了 StopSignal 后，才向下游转发 StopSignal

## 修改文件

### 1. `packages/sage-kernel/src/sage/kernel/runtime/context/task_context.py`

**修改内容**:

#### (1) 添加新的实例变量（行 77-80）

```python
# 跟踪上游并行实例的停止信号 - 解决Issue #1418
# 当上游并行度 >= 2 时，需要等待所有上游实例都发送 StopSignal
self._upstream_parallelism_map: dict[str, int] = {}  # 上游算子名称 -> 并行度
self._upstream_stop_signals_received: dict[str, set[int]] = {}  # 上游算子名称 -> 已接收的平行索引集合
```

#### (2) 更新序列化排除列表（行 33）

添加 `_upstream_stop_signals_received` 到 `__state_exclude__`，避免序列化问题

#### (3) 重写 `handle_stop_signal()` 方法（行 268-350）

- 添加详细的文档说明问题和解决方案
- 实现上游并行度的自动检测和追踪
- 等待所有上游实例的 StopSignal 后再停止

#### (4) 添加 `_initialize_upstream_tracking()` 方法（行 352-386）

- 从路由器信息初始化上游并行度映射
- 支持从执行图获取上游操作符信息

## 技术细节

### StopSignal 处理流程

**修复前**（有问题）:

```
T1: A0 完成 → 发送 StopSignal
T2: B0 收到 StopSignal → 立即停止 ❌
T3: A1, A2 继续发送数据
T4: B0 已停止，数据丢失 ❌
```

**修复后**（正确）:

```
T1: A0 完成 → 发送 StopSignal
T2: B0 收到 StopSignal(来自A0) → 记录: {A: {0}}，等待更多
T3: A1 完成 → 发送 StopSignal  
T4: B0 收到 StopSignal(来自A1) → 记录: {A: {0, 1}}，继续等待
T5: A2 完成 → 发送 StopSignal
T6: B0 收到 StopSignal(来自A2) → 记录: {A: {0, 1, 2}}，全部收齐 ✅
T7: B0 停止并向下游转发 StopSignal ✅
```

### 上游并行度检测

支持两种方式：

1. **自动检测**: 从Router的upstream_groups信息自动提取上游算子的并行度
1. **运行时追踪**: 通过 StopSignal 源名称的格式解析（如 "OperatorA_0" 表示 OperatorA 的第 0 个实例）

## 测试用例

创建了 `test_parallel_stop_signal_fix.py`，包含以下测试场景：

1. **3:1 并行度** - 最常见的问题场景
1. **3:3 并行度** - 处理速度不匹配的场景
1. **2:5 并行度** - 上游少于下游的场景
1. **1:3 并行度** - 安全基线场景（验证不破坏现有功能）

每个测试都验证接收到的记录数等于发送的记录数。

## 影响范围

✅ **正面影响**:

- 修复数据丢失bug，提高系统可靠性
- 支持任意并行度的配置组合
- 保持向后兼容

⚠️ **潜在影响**:

- 对于上游并行度 > 1 的场景，性能可能略有变化（等待所有实例完成）
- 这是正确的语义，之前的"快速失败"是错误的

## 相关文件

- Issue: https://github.com/intellistream/SAGE/issues/1418
- 修复PR: (待创建)
- 相关测试: `packages/sage-kernel/tests/integration/test_parallel_stop_signal_fix.py`

## 临时解决方案（修复前）

如果需要在修复前保证数据不丢失，唯一的方式是配置上游并行度 = 1：

- ✅ 1:1 (safe)
- ✅ 1:3 (safe)
- ✅ 1:N (safe)
- ❌ 其他所有配置 (unsafe - 会丢失数据)

## 后续工作

1. 运行集成测试验证修复
1. 创建PR并请求review
1. 性能基准测试（确保性能不退化）
1. 更新文档和最佳实践指南
