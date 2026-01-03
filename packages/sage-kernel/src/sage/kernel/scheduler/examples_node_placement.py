"""
示例：如何使用 PlacementDecision 指定物理节点

这个示例展示了：
1. 如何获取 Ray 集群中的物理节点信息
2. 如何在 Scheduler 中使用 NodeSelector 选择节点
3. 如何通过 PlacementDecision 指定目标节点
4. PlacementExecutor 如何将任务放置到指定节点
"""

from typing import Any

import ray

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision
from sage.kernel.scheduler.node_selector import NodeSelector
from sage.kernel.utils.ray.ray_utils import init_ray_with_sage_temp

# ============================================================
# 示例 1: 查看集群节点信息
# ============================================================


def example_inspect_cluster():
    """查看 Ray 集群中的所有物理节点"""

    # 初始化 Ray（如果还没初始化）
    if not ray.is_initialized():
        init_ray_with_sage_temp()

    # 获取所有节点
    nodes = ray.nodes()

    print(f"集群中有 {len(nodes)} 个节点：\n")

    for i, node in enumerate(nodes, 1):
        print(f"节点 {i}:")
        print(f"  NodeID: {node['NodeID']}")  # ← 这就是物理节点的唯一标识
        print(f"  地址: {node['NodeManagerAddress']}")
        print(f"  主机名: {node.get('NodeManagerHostname', 'N/A')}")
        print(f"  状态: {'活跃' if node['Alive'] else '离线'}")

        resources = node.get("Resources", {})
        print("  资源:")
        print(f"    CPU: {resources.get('CPU', 0)}")
        print(f"    GPU: {resources.get('GPU', 0)}")
        print(f"    内存: {resources.get('memory', 0) / (1024**3):.2f} GB")
        print()

    # 示例输出：
    # 节点 1:
    #   NodeID: a1b2c3d4e5f6789...
    #   地址: 192.168.1.100
    #   主机名: worker-node-1
    #   状态: 活跃
    #   资源:
    #     CPU: 32.0
    #     GPU: 0.0
    #     内存: 128.00 GB
    #
    # 节点 2:
    #   NodeID: f6e5d4c3b2a1098...
    #   地址: 192.168.1.101
    #   主机名: worker-node-2
    #   状态: 活跃
    #   资源:
    #     CPU: 32.0
    #     GPU: 4.0
    #     内存: 256.00 GB


# ============================================================
# 示例 2: 使用 NodeSelector 选择节点
# ============================================================


def example_node_selector():
    """使用 NodeSelector 根据策略选择节点"""

    selector = NodeSelector()

    # 策略 1: 选择负载最低的节点
    least_loaded = selector.select_least_loaded_node()
    print(f"负载最低的节点: {least_loaded}")

    # 策略 2: 选择有 GPU 的节点
    gpu_node = selector.select_node_with_gpu(min_gpu_count=1)
    print(f"有 GPU 的节点: {gpu_node}")

    # 策略 3: 选择满足资源需求的节点
    node_with_resources = selector.select_best_node(
        cpu_required=8,
        memory_required=16 * 1024**3,  # 16GB
    )
    print(f"满足资源需求的节点: {node_with_resources}")


# ============================================================
# 示例 3: Scheduler 返回指定节点的决策
# ============================================================


class NodeAwareScheduler(BaseScheduler):
    """
    节点感知调度器：根据任务需求选择合适的节点
    """

    def __init__(self):
        super().__init__()
        self.node_selector = NodeSelector()

    def make_decision(self, task_node):
        """
        根据任务特性选择合适的节点
        """

        # 检查任务是否需要 GPU
        gpu_required = (
            getattr(task_node.transformation, "gpu_required", 0)
            if hasattr(task_node, "transformation")
            else 0
        )
        needs_gpu = gpu_required > 0

        if needs_gpu:
            # GPU 任务：选择有 GPU 的节点
            target_node = self.node_selector.select_node_with_gpu()
            gpu_count = gpu_required

            decision = PlacementDecision(
                target_node=target_node,  # ← 指定目标节点
                resource_requirements={"cpu": 4, "gpu": gpu_count, "memory": "16GB"},
                placement_strategy="gpu",
                reason=f"GPU task: selected node {target_node} with GPU",
            )
        else:
            # CPU 任务：选择负载最低的节点
            target_node = self.node_selector.select_least_loaded_node()

            # 提取资源需求
            cpu = (
                getattr(task_node.transformation, "cpu_required", 1)
                if hasattr(task_node, "transformation")
                else 1
            )
            memory = (
                getattr(task_node.transformation, "memory_required", "1GB")
                if hasattr(task_node, "transformation")
                else "1GB"
            )

            decision = PlacementDecision(
                target_node=target_node,  # ← 指定目标节点
                resource_requirements={"cpu": cpu, "memory": memory},
                placement_strategy="load_aware",
                reason=f"CPU task: selected least loaded node {target_node}",
            )

        # 记录决策
        self.scheduled_count += 1
        self.decision_history.append(decision)

        return decision


# ============================================================
# 示例 4: 完整的调度流程
# ============================================================


def example_full_scheduling_flow():
    """
    展示完整的调度流程：从决策到执行

    注意：这是伪代码示例，实际使用时需要根据项目结构调整导入
    """

    # from sage.kernel.api import LocalEnvironment
    # from sage.kernel.operators import MapOperator
    # from sage.kernel.sources import ListSource
    # from sage.kernel.sinks import PrintSink

    print("这是伪代码示例，展示调度流程概念")
    return

    # 下面是伪代码，展示概念
    # """
    # # 创建自定义调度器
    # scheduler = NodeAwareScheduler()
    #
    # # 创建 Environment（使用自定义调度器）
    # env = LocalEnvironment(
    #     name="node_aware_demo",
    #     platform="remote",
    #     scheduler=scheduler
    # )
    #
    # # 定义一个需要 GPU 的 Operator
    # class GPUOperator:
    #     gpu_required = 1
    #     def process(self, record):
    #         return record * 2
    #
    # # 构建 Pipeline
    # env.from_source(...).map(GPUOperator, parallelism=2).sink(...)
    # """
    #
    # # 提交作业
    # # 内部流程：
    # # 1. Dispatcher.submit() 被调用
    # # 2. 对每个任务：
    # #    - scheduler.make_decision(task_node) 返回决策
    # #      → decision = PlacementDecision(target_node="gpu-node-id", ...)
    # #    - placement_executor.place_task(task_node, decision)
    # #      → 创建 Actor 到指定的 GPU 节点
    # #    - task.start_running()
    # #      → 启动数据处理
    # env.submit()
    #
    # # 等待完成
    # env.wait_for_completion()
    #
    # # 查看调度指标
    # metrics = scheduler.get_metrics()
    # print(f"调度统计: {metrics}")
    #
    # # 查看决策历史
    # print("\n决策历史:")
    # for i, decision in enumerate(scheduler.decision_history, 1):
    #     print(f"{i}. {decision}")


# ============================================================
# 示例 5: 手动指定节点（调试用）
# ============================================================


class DebugScheduler(BaseScheduler):
    """
    调试调度器：强制所有任务到指定节点
    用于调试和测试
    """

    def __init__(self, debug_node_id: str):
        super().__init__()
        self.debug_node_id = debug_node_id

    def make_decision(self, task_node):
        """所有任务都放到调试节点"""

        self.scheduled_count += 1

        decision = PlacementDecision(
            target_node=self.debug_node_id,  # ← 强制指定节点
            resource_requirements=None,  # 使用默认资源
            placement_strategy="debug",
            reason=f"Debug mode: all tasks on node {self.debug_node_id}",
        )

        self.decision_history.append(decision)
        return decision


def example_debug_scheduling():
    """调试示例：所有任务到同一节点"""

    # 假设我们知道调试节点的 ID
    debug_node_id = "a1b2c3d4e5f6..."  # 从 ray.nodes() 获取

    # 创建调试调度器
    DebugScheduler(debug_node_id)

    print(f"创建调试调度器，所有任务将被放置到节点: {debug_node_id}")
    print("(这是示例概念，实际使用需要配置 Environment)")

    # 伪代码：
    # env = LocalEnvironment(name="debug_demo", platform="remote", scheduler=scheduler)
    # env.submit()


# ============================================================
# 示例 6: 查看 PlacementExecutor 如何使用决策
# ============================================================


def example_placement_execution():
    """
    PlacementExecutor 如何根据决策执行放置
    """

    # 这是 PlacementExecutor 内部的实现（简化版）
    def build_ray_options(decision: PlacementDecision):
        """将决策转换为 Ray Actor 选项"""

        options: dict[str, Any] = {"lifetime": "detached"}

        # === 关键：指定目标节点 ===
        if decision.target_node:
            from ray.util.scheduling_strategies import NodeAffinitySchedulingStrategy

            options["scheduling_strategy"] = NodeAffinitySchedulingStrategy(
                node_id=decision.target_node,  # ← 使用决策中的节点 ID
                soft=False,  # 硬要求：必须放到这个节点
            )

            print(f"✓ 将 Actor 放置到节点: {decision.target_node}")

        # === 指定资源需求 ===
        if decision.resource_requirements:
            if "cpu" in decision.resource_requirements:
                options["num_cpus"] = decision.resource_requirements["cpu"]
                print(f"✓ 要求 CPU: {options['num_cpus']}")

            if "gpu" in decision.resource_requirements:
                options["num_gpus"] = decision.resource_requirements["gpu"]
                print(f"✓ 要求 GPU: {options['num_gpus']}")

            if "memory" in decision.resource_requirements:
                memory_value = decision.resource_requirements["memory"]
                memory_bytes = parse_memory(memory_value)  # type: ignore[arg-type]
                options["memory"] = memory_bytes
                print(f"✓ 要求内存: {memory_value}")

        return options

    def parse_memory(memory_str: str) -> int:
        """解析内存字符串"""
        if isinstance(memory_str, int):
            return memory_str

        memory_str = memory_str.upper()
        if "GB" in memory_str:
            return int(float(memory_str.replace("GB", "")) * 1024**3)
        elif "MB" in memory_str:
            return int(float(memory_str.replace("MB", "")) * 1024**2)
        return 1024**3

    # 示例决策
    decision = PlacementDecision(
        target_node="f6e5d4c3b2a1098...",
        resource_requirements={"cpu": 4, "gpu": 1, "memory": "16GB"},
        reason="GPU task on worker-node-2",
    )

    print("决策:")
    print(f"  目标节点: {decision.target_node}")
    print(f"  资源需求: {decision.resource_requirements}")
    print(f"  原因: {decision.reason}")
    print()

    print("执行放置:")
    ray_options = build_ray_options(decision)
    print()

    print("Ray Actor 选项:")
    for key, value in ray_options.items():
        print(f"  {key}: {value}")

    # 输出:
    # 决策:
    #   目标节点: f6e5d4c3b2a1098...
    #   资源需求: {'cpu': 4, 'gpu': 1, 'memory': '16GB'}
    #   原因: GPU task on worker-node-2
    #
    # 执行放置:
    # ✓ 将 Actor 放置到节点: f6e5d4c3b2a1098...
    # ✓ 要求 CPU: 4
    # ✓ 要求 GPU: 1
    # ✓ 要求内存: 16GB
    #
    # Ray Actor 选项:
    #   lifetime: detached
    #   scheduling_strategy: NodeAffinitySchedulingStrategy(node_id='f6e5d4c3b2a1098...', soft=False)
    #   num_cpus: 4
    #   num_gpus: 1
    #   memory: 17179869184


# ============================================================
# 运行示例
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("示例 1: 查看集群节点信息")
    print("=" * 60)
    example_inspect_cluster()

    print("\n" + "=" * 60)
    print("示例 2: 使用 NodeSelector")
    print("=" * 60)
    example_node_selector()

    print("\n" + "=" * 60)
    print("示例 6: PlacementExecutor 执行")
    print("=" * 60)
    example_placement_execution()
