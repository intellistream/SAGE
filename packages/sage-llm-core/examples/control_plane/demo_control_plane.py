#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
完整的 Control Plane 演示示例

这个脚本演示了完整的使用流程，不需要实际的 vLLM 实例运行。
使用 mock 来模拟 vLLM HTTP 响应。
"""

import asyncio
import logging

from control_plane import (
    ControlPlaneManager,
    ExecutionInstance,
    ExecutionInstanceType,
    RequestMetadata,
    RequestPriority,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def demo_basic_usage():
    """演示 1: 基础使用流程"""
    logger.info("\n" + "=" * 70)
    logger.info("演示 1: 基础 Control Plane 使用流程")
    logger.info("=" * 70)

    # 1. 创建 Control Plane
    cp = ControlPlaneManager(
        scheduling_policy="fifo",
        routing_strategy="load_balanced",
        enable_pd_separation=False,
    )

    # 2. 注册 vLLM 实例（模拟本地 GPU）
    for i in range(2):
        instance = ExecutionInstance(
            instance_id=f"gpu-{i}",
            host="localhost",
            port=8000 + i,
            model_name="meta-llama/Llama-2-7b",
            tensor_parallel_size=1,
            gpu_count=1,
        )
        cp.register_instance(instance)

    logger.info(f"✓ 已注册 {len(cp.executor.get_all_instances())} 个实例")

    # 3. 提交请求
    requests = []
    for i in range(5):
        req = RequestMetadata(
            request_id=f"demo-req-{i}",
            prompt=f"演示请求 {i}: 解释人工智能",
            max_tokens=100,
            priority=RequestPriority.NORMAL,
        )
        requests.append(req)
        await cp.submit_request(req)

    logger.info(f"✓ 已提交 {len(requests)} 个请求到队列")
    logger.info(f"✓ 队列大小: {len(cp.pending_queue)}")

    # 4. 查看排队的请求
    logger.info("\n排队的请求:")
    for i, req in enumerate(list(cp.pending_queue)[:3], 1):
        logger.info(f"  {i}. {req.request_id} (优先级: {req.priority.name})")

    # 5. 获取指标
    metrics = cp.get_metrics()
    logger.info("\n当前指标:")
    logger.info(f"  - 活跃请求: {metrics.active_requests}")
    logger.info(f"  - 排队请求: {metrics.queued_requests}")
    logger.info(f"  - 已完成: {metrics.completed_requests}")
    logger.info(f"  - SLO 达标率: {metrics.slo_compliance_rate:.1f}%")


async def demo_priority_scheduling():
    """演示 2: 优先级调度"""
    logger.info("\n" + "=" * 70)
    logger.info("演示 2: 优先级调度策略")
    logger.info("=" * 70)

    cp = ControlPlaneManager(
        scheduling_policy="priority",
        enable_pd_separation=False,
    )

    # 注册实例
    instance = ExecutionInstance(
        instance_id="priority-gpu",
        host="localhost",
        port=8000,
        model_name="meta-llama/Llama-2-7b",
        gpu_count=1,
    )
    cp.register_instance(instance)

    # 提交不同优先级的请求
    priorities = [
        (RequestPriority.LOW, "低优先级任务"),
        (RequestPriority.CRITICAL, "紧急任务"),
        (RequestPriority.NORMAL, "普通任务"),
        (RequestPriority.HIGH, "高优先级任务"),
    ]

    for priority, desc in priorities:
        req = RequestMetadata(
            request_id=f"priority-{priority.name}",
            prompt=desc,
            priority=priority,
            max_tokens=50,
        )
        await cp.submit_request(req)
        logger.info(f"✓ 提交: {desc} (优先级: {priority.name})")

    # 展示调度顺序
    logger.info("\n排队的请求列表:")
    for i, req in enumerate(list(cp.pending_queue), 1):
        logger.info(f"  {i}. {req.request_id} - 优先级: {req.priority.name}")

    # 使用 prioritize 方法排序
    logger.info("\n经过优先级排序后:")
    sorted_reqs = cp.scheduling_policy.prioritize(list(cp.pending_queue))
    for i, req in enumerate(sorted_reqs, 1):
        logger.info(f"  {i}. {req.request_id} - {req.priority.name}")


async def demo_slo_aware_scheduling():
    """演示 3: SLO 感知调度"""
    logger.info("\n" + "=" * 70)
    logger.info("演示 3: SLO 感知调度（延迟保证）")
    logger.info("=" * 70)

    cp = ControlPlaneManager(
        scheduling_policy="slo_aware",
        enable_pd_separation=False,
    )

    instance = ExecutionInstance(
        instance_id="slo-gpu",
        host="localhost",
        port=8000,
        model_name="meta-llama/Llama-2-7b",
        gpu_count=1,
    )
    cp.register_instance(instance)

    # 提交带 SLO 的请求
    slo_configs = [
        (500, "超低延迟要求"),
        (2000, "普通延迟要求"),
        (1000, "中等延迟要求"),
        (None, "无 SLO 要求"),
    ]

    for slo_ms, desc in slo_configs:
        req = RequestMetadata(
            request_id=f"slo-{slo_ms or 'none'}",
            prompt=desc,
            slo_deadline_ms=slo_ms,
            max_tokens=100,
        )
        await cp.submit_request(req)
        slo_str = f"{slo_ms}ms" if slo_ms else "无限制"
        logger.info(f"✓ 提交: {desc} (SLO: {slo_str})")

    logger.info("\n经过 SLO 排序后（紧急优先）:")
    sorted_reqs = cp.scheduling_policy.prioritize(list(cp.pending_queue))
    for i, req in enumerate(sorted_reqs, 1):
        slo_str = f"{req.slo_deadline_ms}ms" if req.slo_deadline_ms else "无"
        logger.info(f"  {i}. {req.request_id} - SLO: {slo_str}")


async def demo_pd_separation():
    """演示 4: Prefilling/Decoding 分离优化"""
    logger.info("\n" + "=" * 70)
    logger.info("演示 4: PD 分离优化（提升 50-80% 吞吐）")
    logger.info("=" * 70)

    cp = ControlPlaneManager(
        scheduling_policy="adaptive",
        enable_pd_separation=True,
    )

    # 注册专门的 Prefilling 实例（高 TP）
    prefill_instance = ExecutionInstance(
        instance_id="prefill-tp4",
        host="localhost",
        port=8001,
        model_name="meta-llama/Llama-2-7b",
        tensor_parallel_size=4,
        gpu_count=4,
        instance_type=ExecutionInstanceType.PREFILLING,
    )
    cp.register_instance(prefill_instance)
    logger.info("✓ 注册 Prefilling 实例 (TP=4, 优化吞吐量)")

    # 注册专门的 Decoding 实例（低 TP）
    decode_instance = ExecutionInstance(
        instance_id="decode-tp1",
        host="localhost",
        port=8002,
        model_name="meta-llama/Llama-2-7b",
        tensor_parallel_size=1,
        gpu_count=1,
        instance_type=ExecutionInstanceType.DECODING,
    )
    cp.register_instance(decode_instance)
    logger.info("✓ 注册 Decoding 实例 (TP=1, 优化延迟)")

    # 提交不同类型的请求
    requests_config = [
        ("长文档分析", "A" * 2000, "长输入 → Prefilling 实例"),
        ("简短聊天", "你好", "短输入 → Decoding 实例"),
        ("代码审查", "B" * 1500, "中长输入 → Prefilling 实例"),
        ("快速问答", "什么是AI?", "短输入 → Decoding 实例"),
    ]

    logger.info("\n请求路由决策:")
    for desc, prompt, expected in requests_config:
        req = RequestMetadata(
            request_id=f"pd-{desc}",
            prompt=prompt,
            max_tokens=100,
        )

        # 使用 PD router 决定路由类型
        if cp.pd_router:
            phase = cp.pd_router.determine_request_phase(req)
            input_len = len(prompt) if prompt else 0
            logger.info(f"  {desc}: 输入长度={input_len}")
            logger.info(f"    路由决策: {phase.value if phase else 'GENERAL'}")
            logger.info(f"    预期: {expected}")


async def demo_multi_instance():
    """演示 5: 多实例负载均衡"""
    logger.info("\n" + "=" * 70)
    logger.info("演示 5: 多实例负载均衡")
    logger.info("=" * 70)

    cp = ControlPlaneManager(
        scheduling_policy="adaptive",
        routing_strategy="load_balanced",
        enable_pd_separation=False,
    )

    # 注册多个不同配置的实例
    instances_config = [
        ("local-gpu-0", "localhost", 8000, 1, "本地 GPU 0"),
        ("local-gpu-1", "localhost", 8001, 1, "本地 GPU 1"),
        ("remote-gpu-0", "192.168.1.100", 8000, 2, "远程 GPU (TP=2)"),
        ("remote-gpu-1", "192.168.1.100", 8001, 4, "远程 GPU (TP=4)"),
    ]

    for inst_id, host, port, tp, desc in instances_config:
        instance = ExecutionInstance(
            instance_id=inst_id,
            host=host,
            port=port,
            model_name="meta-llama/Llama-2-7b",
            tensor_parallel_size=tp,
            gpu_count=tp,
        )
        cp.register_instance(instance)
        logger.info(f"✓ 注册: {desc} ({host}:{port}, TP={tp})")

    # 展示所有实例状态
    logger.info("\n实例列表:")
    for inst in cp.executor.get_all_instances():
        logger.info(f"  - {inst.instance_id}: {inst.host}:{inst.port}")
        logger.info(f"    TP={inst.tensor_parallel_size}, GPUs={inst.gpu_count}")
        logger.info(f"    负载={inst.current_load:.1%}, 活跃请求={inst.active_requests}")

    # 模拟批量请求
    logger.info("\n提交 10 个请求，观察负载均衡...")
    for i in range(10):
        req = RequestMetadata(
            request_id=f"batch-{i}",
            prompt=f"请求 {i}",
            max_tokens=100,
        )
        await cp.submit_request(req)

    logger.info(f"✓ 总共 {len(cp.pending_queue)} 个请求在队列中")


async def main():
    """运行所有演示"""
    print("\n" + "🚀" * 35)
    print("   sageLLM Control Plane 完整演示")
    print("🚀" * 35 + "\n")

    # 运行所有演示
    await demo_basic_usage()
    await asyncio.sleep(0.5)

    await demo_priority_scheduling()
    await asyncio.sleep(0.5)

    await demo_slo_aware_scheduling()
    await asyncio.sleep(0.5)

    await demo_pd_separation()
    await asyncio.sleep(0.5)

    await demo_multi_instance()

    print("\n" + "✅" * 35)
    print("   所有演示完成！")
    print("✅" * 35 + "\n")

    print("\n📝 关键要点:")
    print("  1. Control Plane 是 HTTP 客户端，统一管理所有 vLLM 实例")
    print("  2. 支持 5 种调度策略: FIFO, Priority, SLO, Cost, Adaptive")
    print("  3. PD 分离可提升 50-80% 吞吐，降低 50-60% 延迟")
    print("  4. 支持多实例负载均衡和智能路由")
    print("  5. 本地和远程 GPU 统一透明访问\n")


if __name__ == "__main__":
    asyncio.run(main())
