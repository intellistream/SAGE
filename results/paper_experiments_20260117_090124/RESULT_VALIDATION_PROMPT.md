# SAGE 论文实验结果验证 Prompt

## 任务目标

你需要验证 SAGE 分布式 LLM 推理编排系统的论文实验结果是否存在异常。实验结果位于：
`/home/sage/SAGE/results/paper_experiments_20260117_090124/`

## 实验背景

该实验套件包含 5 个主要实验，在 16 节点集群上运行（每节点 8 CPU 核心，32GB 内存，独立 A100 GPU 服务器提供 LLM 推理）。

## 验证任务清单

### 1. 检查实验完成状态

查看 `experiment_log.txt`，确认：
- [ ] 实验 1-5 是否全部完成
- [ ] 是否有 `[ERROR]` 记录（已知问题：`exp5_heterogeneous_concurrent` 和 `exp5_large_scale_heterogeneous` 失败）
- [ ] 时间线是否合理（总耗时约 6 小时是正常的）

### 2. 实验 1：横向扩展性验证 (`exp1_scalability/`)

**预期行为**：节点数增加时，吞吐量应近线性增长，加速比应在 0.85N-0.95N 之间。

**检查项**：

| 子目录 | 检查内容 |
|--------|---------|
| `compute_nodes{1,4,8,16}/` | 比较吞吐量是否随节点数增长 |
| `rag_nodes{1,4,8,16}/` | 比较 RAG 工作负载的扩展性 |
| `mixed_nodes{4,8,16}/` | 异构工作负载的扩展性 |

**异常判断标准**：
- ❌ 吞吐量为 0.00/s
- ❌ 加速比 < 0.5N（严重线性度不足）
- ❌ failed_tasks > 0
- ❌ 节点分布严重不均（balance_score < 0.8）
- ⚠️ 16 节点吞吐量反而低于 1 节点（参考 compute_nodes16 的 18.5/s vs compute_nodes1 的 38.3/s，这是**已知异常**，需重点关注）

**需要查看的文件**：
- `*_metrics.json` - 详细指标
- `node_scaling_comparison.txt` - 对比报告

### 3. 实验 2：调度策略对比验证 (`exp2_scheduling/`)

**预期行为**：LoadAware(spread) 应在负载均衡和尾延迟上表现最佳。

**检查项**：

| 子目录 | 检查内容 |
|--------|---------|
| `high_schedulers/` | 4 种调度器在 high 级别的对比 |
| `extreme_schedulers/` | 4 种调度器在 extreme 级别的对比 |

**已知问题（需确认）**：
- `load_aware_spread`, `load_aware_pack`, `priority` 调度器**结果全为 0**
- 只有 `fifo` 调度器有有效结果

**异常判断标准**：
- ❌ 多个调度器吞吐量为 0（**已观察到，确认为异常**）
- ❌ round_robin 调度器数据缺失
- ❌ FIFO balance_score < 60%（观察到 52.4%-57.3%，负载严重不均）

### 4. 实验 3：负载级别验证 (`exp3_load_levels/`)

**预期行为**：负载级别从低到高，延迟应逐渐上升，吞吐量先增后可能饱和。

**检查项**：

| 子目录 | 检查内容 |
|--------|---------|
| `load_levels/` | low/medium/high/extreme 四个级别对比 |
| `pipeline_depths/` | shallow/medium/deep 三个流水线深度对比 |

**已知问题（需确认）**：
- `low`, `high`, `extreme` 级别**结果全为 0**
- 只有 `medium` 级别有有效结果（11.99/s）

**异常判断标准**：
- ❌ 多个负载级别吞吐量为 0（**已观察到，确认为异常**）
- ⚠️ 如果 low 级别延迟高于 medium，是异常

### 5. 实验 4：并发与延迟验证 (`exp4_concurrency/`)

**预期行为**：存在最优并发度，低并发延迟低但吞吐量受限，高并发延迟急剧上升。

**检查项**：

| 子目录 | 检查内容 |
|--------|---------|
| `concurrency_compute/` | 并发度 1-64 的 compute pipeline |
| `concurrency_rag/` | 并发度 1-32 的 RAG pipeline |
| `latency_breakdown/` | 延迟分解（调度/排队/执行） |
| `scheduler_overhead/` | 调度器开销对比 |

**已知问题（需确认）**：
- `concurrency_64` 结果为 0
- 并发度增加时吞吐量**不单调**（concurrency_8=40.31/s 最高，之后下降）

**异常判断标准**：
- ❌ 高并发度结果全为 0
- ⚠️ 并发度 2/4 的延迟（0.5ms）异常低于并发度 1（50.5ms），**疑似数据错误**
- ⚠️ 吞吐量非单调变化（可接受，但需解释）

### 6. 实验 5：多管道隔离验证 (`exp5_isolation/`)

**预期行为**：交错启动可降低资源竞争，各 pipeline 吞吐量方差应较小。

**检查项**：

| 子目录 | 检查内容 |
|--------|---------|
| `homogeneous_concurrent/` | 同构 pipeline（rag×3）竞争 |
| `job_scaling/` | 作业数量扩展性（1/2/4/8 并发） |
| `staggered_comparison/` | 交错启动 vs 同时启动 |

**已知问题（需确认）**：
- `heterogeneous_concurrent` 和 `large_scale_heterogeneous` **目录缺失**（执行失败）
- `homogeneous_concurrent` 中 job1_rag 结果为 0
- job0_rag 和 job2_rag 的 successful_tasks=13773 **远超配置的 5000**

**异常判断标准**：
- ❌ 部分 job 吞吐量为 0（**已观察到**）
- ❌ successful_tasks != config.num_tasks（**严重异常**）
- ⚠️ balance_score < 90%（88.1% 略低但可接受）

---

## 综合异常总结（需要你确认）

### 严重异常（影响论文结论）

1. **调度器失效**：load_aware_spread, load_aware_pack, priority 调度器在多个实验中结果为 0
2. **任务数不匹配**：exp5 中 successful_tasks (13773) 与配置的 num_tasks (5000) 严重不符
3. **扩展性反转**：16 节点 compute 吞吐量 (18.5/s) 低于单节点 (38.3/s)

### 中等异常（需要解释）

4. **延迟数据异常**：concurrency_2/4 的延迟 (0.5ms) 远低于 concurrency_1 (50.5ms)
5. **高并发失效**：concurrency_64 结果为 0
6. **负载级别缺失**：load low/high/extreme 全部为 0

### 执行失败（已知）

7. `exp5_heterogeneous_concurrent` 执行失败
8. `exp5_large_scale_heterogeneous` 执行失败

---

## 验证输出要求

请按以下格式输出验证报告：

```markdown
# 实验结果验证报告

## 1. 实验完成度
- 实验 1-5 完成状态：[完成/部分完成/失败]
- 已知失败项：...

## 2. 数据完整性检查
| 实验 | 预期配置数 | 实际有效结果数 | 状态 |
|------|-----------|---------------|------|
| exp1 | 11 | ? | |
| exp2 | 8 | ? | |
| exp3 | 7 | ? | |
| exp4 | 12+ | ? | |
| exp5 | 7 | ? | |

## 3. 异常详情
[列出所有发现的异常，包括已确认和新发现的]

## 4. 数据一致性问题
[检查 tasks 数量、节点分布、时间戳等是否一致]

## 5. 结论
- [ ] 数据可用于论文
- [ ] 需要重新运行部分实验
- [ ] 需要完全重新实验

## 6. 建议
[提供具体的修复/重跑建议]
```

---

## 文件访问提示

你可以直接读取以下类型的文件：
- `*_metrics.json` - 完整指标（JSON 格式，包含 config、latency_details）
- `*_comparison.txt` / `*_report.txt` - 汇总对比表
- `*_summary.txt` - 单次实验摘要
- `*.csv` - 原始延迟数据

**建议的检查顺序**：
1. 先读取各目录的 `*_comparison.txt` 或 `*_report.txt` 获取概览
2. 对异常项深入查看 `*_metrics.json` 确认细节
3. 必要时检查 `*.csv` 验证原始数据

---

## 附录：实验配置参考

| 参数 | 论文级别值 | 快速测试值 |
|------|-----------|-----------|
| SCALABILITY_TASKS | 5000 | 500 |
| SCHEDULER_TASKS | 5000 | 500 |
| CONCURRENCY_TASKS | 5000 | 500 |
| ISOLATION_TASKS | 5000 | 500 |
| 集群规模 | 16 节点 | 16 节点 |

本次实验使用**论文级别**参数运行（QUICK_MODE=false）。
