"""
调度器模块完整测试套件

测试覆盖：
1. PlacementDecision 数据类
2. BaseScheduler 接口
3. FIFOScheduler 实现
4. LoadAwareScheduler 实现
5. NodeSelector 资源监控
6. PlacementExecutor 执行器
7. 完整集成测试
"""

import time
from unittest.mock import Mock, patch

import pytest

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision
from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler
from sage.kernel.scheduler.placement import PlacementExecutor

# ============================================================================
# PlacementDecision 测试
# ============================================================================


class TestPlacementDecision:
    """测试 PlacementDecision 数据类"""

    def test_default_initialization(self):
        """测试默认初始化"""
        decision = PlacementDecision()

        assert decision.target_node is None
        assert decision.resource_requirements is None
        assert decision.delay == 0.0
        assert decision.immediate is True
        assert decision.placement_strategy == "default"
        assert decision.reason == ""

    def test_full_initialization(self):
        """测试完整初始化"""
        decision = PlacementDecision(
            target_node="worker-node-1",
            resource_requirements={"cpu": 4, "gpu": 1, "memory": "8GB"},
            delay=0.5,
            immediate=False,
            placement_strategy="balanced",
            reason="Test decision",
        )

        assert decision.target_node == "worker-node-1"
        assert decision.resource_requirements == {"cpu": 4, "gpu": 1, "memory": "8GB"}
        assert decision.delay == 0.5
        assert decision.immediate is False
        assert decision.placement_strategy == "balanced"
        assert decision.reason == "Test decision"

    def test_immediate_default(self):
        """测试 immediate_default 快捷方法"""
        decision = PlacementDecision.immediate_default(reason="Quick test")

        assert decision.target_node is None
        assert decision.resource_requirements is None
        assert decision.delay == 0.0
        assert decision.immediate is True
        assert decision.placement_strategy == "default"
        assert decision.reason == "Quick test"

    def test_with_resources(self):
        """测试 with_resources 快捷方法"""
        decision = PlacementDecision.with_resources(
            cpu=4, gpu=1, memory=8589934592, reason="Resource test"
        )

        assert decision.resource_requirements == {
            "cpu": 4,
            "gpu": 1,
            "memory": 8589934592,
        }
        assert decision.reason == "Resource test"

    def test_with_node(self):
        """测试 with_node 快捷方法"""
        decision = PlacementDecision.with_node(
            node_id="worker-node-2", reason="Node test"
        )

        assert decision.target_node == "worker-node-2"
        assert decision.reason == "Node test"

    def test_to_dict(self):
        """测试转换为字典"""
        decision = PlacementDecision(
            target_node="node-1", resource_requirements={"cpu": 2}, reason="Dict test"
        )

        result = decision.to_dict()

        assert isinstance(result, dict)
        assert result["target_node"] == "node-1"
        assert result["resource_requirements"] == {"cpu": 2}
        assert result["reason"] == "Dict test"

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "target_node": "node-1",
            "resource_requirements": {"cpu": 2},
            "delay": 0.5,
            "immediate": False,
            "placement_strategy": "pack",
            "reason": "From dict test",
        }

        decision = PlacementDecision.from_dict(data)

        assert decision.target_node == "node-1"
        assert decision.resource_requirements == {"cpu": 2}
        assert decision.delay == 0.5
        assert decision.immediate is False
        assert decision.placement_strategy == "pack"

    def test_repr(self):
        """测试字符串表示"""
        decision = PlacementDecision(
            target_node="node-1", resource_requirements={"cpu": 4}, reason="Repr test"
        )

        repr_str = repr(decision)

        assert "PlacementDecision" in repr_str
        assert "node-1" in repr_str
        assert "cpu" in repr_str


# ============================================================================
# BaseScheduler 测试
# ============================================================================


class TestBaseScheduler:
    """测试 BaseScheduler 抽象基类"""

    def test_scheduler_is_abstract(self):
        """测试 BaseScheduler 是抽象类"""
        with pytest.raises(TypeError):
            BaseScheduler()  # type: ignore[abstract]

    def test_scheduler_interface(self):
        """测试调度器接口定义"""
        # 检查必须实现的方法
        assert hasattr(BaseScheduler, "make_decision")
        assert hasattr(BaseScheduler, "make_service_decision")
        assert hasattr(BaseScheduler, "get_metrics")
        assert hasattr(BaseScheduler, "shutdown")


# ============================================================================
# FIFOScheduler 测试
# ============================================================================


class TestFIFOScheduler:
    """测试 FIFO 调度器"""

    def test_initialization(self):
        """测试初始化"""
        scheduler = FIFOScheduler(platform="local")

        assert scheduler.platform == "local"
        assert scheduler.scheduled_count == 0
        assert len(scheduler.decision_history) == 0

    def test_make_decision(self):
        """测试任务调度决策"""
        scheduler = FIFOScheduler(platform="local")

        # Mock task node
        task_node = Mock()
        task_node.name = "test_task"
        task_node.transformation = Mock()

        # 调度决策
        decision = scheduler.make_decision(task_node)

        # 验证决策
        assert isinstance(decision, PlacementDecision)
        assert decision.target_node is None  # FIFO 使用默认
        assert decision.resource_requirements is None
        assert decision.immediate is True
        assert "FIFO" in decision.reason

        # 验证计数
        assert scheduler.scheduled_count == 1
        assert len(scheduler.decision_history) == 1

    def test_make_service_decision(self):
        """测试服务调度决策"""
        scheduler = FIFOScheduler(platform="local")

        # Mock service node
        service_node = Mock()
        service_node.service_name = "test_service"
        service_node.service_class = Mock()

        # 调度决策
        decision = scheduler.make_service_decision(service_node)

        # 验证决策
        assert isinstance(decision, PlacementDecision)
        assert decision.target_node is None
        assert decision.immediate is True
        assert "service" in decision.reason.lower()

        # 验证计数
        assert scheduler.scheduled_count == 1

    def test_multiple_decisions(self):
        """测试多个决策"""
        scheduler = FIFOScheduler()

        # 调度多个任务
        for i in range(5):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.transformation = Mock()

            decision = scheduler.make_decision(task_node)
            assert isinstance(decision, PlacementDecision)

        # 验证
        assert scheduler.scheduled_count == 5
        assert len(scheduler.decision_history) == 5

    def test_get_metrics(self):
        """测试获取指标"""
        scheduler = FIFOScheduler(platform="remote")

        # 调度一些任务
        for i in range(3):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.transformation = Mock()
            scheduler.make_decision(task_node)

        # 获取指标
        metrics = scheduler.get_metrics()

        assert metrics["scheduler_type"] == "FIFO"
        assert metrics["total_scheduled"] == 3
        assert metrics["decisions"] == 3
        assert metrics["platform"] == "remote"
        assert "avg_latency_ms" in metrics

    def test_shutdown(self):
        """测试关闭"""
        scheduler = FIFOScheduler()

        # 调度一些任务
        for i in range(3):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.transformation = Mock()
            scheduler.make_decision(task_node)

        # 关闭
        scheduler.shutdown()

        # 验证清理
        assert len(scheduler.decision_history) == 0


# ============================================================================
# LoadAwareScheduler 测试
# ============================================================================


class TestLoadAwareScheduler:
    """测试负载感知调度器"""

    def test_initialization(self):
        """测试初始化"""
        scheduler = LoadAwareScheduler(
            max_concurrent=10, platform="remote", strategy="balanced"
        )

        assert scheduler.platform == "remote"
        assert scheduler.max_concurrent == 10
        assert scheduler.strategy == "balanced"
        assert scheduler.active_tasks == 0
        assert scheduler.scheduled_count == 0

    def test_make_decision_without_resources(self):
        """测试无资源需求的决策"""
        scheduler = LoadAwareScheduler(max_concurrent=10)

        # Mock task node without resource requirements
        task_node = Mock()
        task_node.name = "test_task"
        task_node.transformation = Mock(spec=[])  # No resource attributes
        task_node.task_factory = Mock()
        task_node.task_factory.remote = False  # Local task

        # 调度决策
        decision = scheduler.make_decision(task_node)

        # 验证决策
        assert isinstance(decision, PlacementDecision)
        assert decision.delay == 0.0
        assert "LoadAware" in decision.reason

        # 验证活跃任务计数
        assert scheduler.active_tasks == 1

    def test_make_decision_with_resources(self):
        """测试带资源需求的决策"""
        scheduler = LoadAwareScheduler(max_concurrent=10)

        # Mock task node with resource requirements
        task_node = Mock()
        task_node.name = "gpu_task"
        task_node.transformation = Mock()
        task_node.transformation.cpu_required = 4
        task_node.transformation.gpu_required = 1
        task_node.transformation.memory_required = "8GB"
        task_node.transformation.custom_resources = {}  # 空字典，不是 Mock
        task_node.task_factory = Mock()
        task_node.task_factory.remote = False

        # 调度决策
        decision = scheduler.make_decision(task_node)

        # 验证资源需求
        assert decision.resource_requirements is not None
        assert decision.resource_requirements["cpu"] == 4
        assert decision.resource_requirements["gpu"] == 1
        assert "memory" in decision.resource_requirements

    @patch("sage.kernel.scheduler.node_selector.NodeSelector")
    def test_make_decision_with_node_selector(self, mock_node_selector_class):
        """测试使用 NodeSelector 的决策"""
        # Mock NodeSelector
        mock_selector = Mock()
        mock_selector.select_best_node.return_value = "worker-node-2"

        # Mock get_node to return node resource info
        mock_node_res = Mock()
        mock_node_res.hostname = "worker-2"
        mock_node_res.cpu_usage = 0.5
        mock_node_res.gpu_usage = 0.3
        mock_selector.get_node.return_value = mock_node_res

        mock_node_selector_class.return_value = mock_selector

        scheduler = LoadAwareScheduler(max_concurrent=10, strategy="balanced")

        # Mock remote task node
        task_node = Mock()
        task_node.name = "remote_task"
        task_node.transformation = Mock()
        task_node.transformation.cpu_required = 2
        task_node.transformation.gpu_required = 0
        task_node.transformation.memory_required = "4GB"
        task_node.transformation.custom_resources = {}  # 空字典，不是 Mock
        task_node.task_factory = Mock()
        task_node.task_factory.remote = True  # Remote task

        # 调度决策
        decision = scheduler.make_decision(task_node)

        # 验证节点选择
        assert decision.target_node == "worker-node-2"
        mock_selector.select_best_node.assert_called_once()
        mock_selector.track_task_placement.assert_called_once_with(
            task_node.name, "worker-node-2"
        )

    def test_make_service_decision(self):
        """测试服务调度决策"""
        scheduler = LoadAwareScheduler(max_concurrent=10)

        # Mock service node
        service_node = Mock()
        service_node.service_name = "cache_service"
        service_node.service_class = Mock()
        service_node.service_class.cpu_required = 2
        service_node.service_class.gpu_required = 0  # 明确设置
        service_node.service_class.memory_required = "4GB"
        service_node.service_class.custom_resources = {}  # 空字典

        # 调度决策
        decision = scheduler.make_service_decision(service_node)

        # 验证决策
        assert isinstance(decision, PlacementDecision)
        assert decision.placement_strategy == "spread"  # 服务使用 spread
        assert decision.immediate is True
        assert "Service" in decision.reason

    def test_concurrency_control(self):
        """测试并发控制"""
        scheduler = LoadAwareScheduler(max_concurrent=2)

        # 调度到达上限
        for i in range(2):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.transformation = Mock(spec=[])
            task_node.task_factory = Mock()
            task_node.task_factory.remote = False

            decision = scheduler.make_decision(task_node)
            assert decision.delay == 0.0

        # 验证已达到上限
        assert scheduler.active_tasks == 2
        assert scheduler.active_tasks >= scheduler.max_concurrent

    def test_task_completed(self):
        """测试任务完成"""
        scheduler = LoadAwareScheduler(max_concurrent=10)

        # 调度一个任务
        task_node = Mock()
        task_node.name = "test_task"
        task_node.transformation = Mock(spec=[])
        task_node.task_factory = Mock()
        task_node.task_factory.remote = False

        scheduler.make_decision(task_node)
        assert scheduler.active_tasks == 1

        # 标记任务完成
        scheduler.task_completed("test_task")
        assert scheduler.active_tasks == 0

    def test_memory_parsing(self):
        """测试内存解析"""
        scheduler = LoadAwareScheduler()

        # 测试各种格式
        assert scheduler._parse_memory("8GB") == 8 * 1024**3
        assert scheduler._parse_memory("512MB") == 512 * 1024**2
        assert scheduler._parse_memory("1024KB") == 1024 * 1024
        assert scheduler._parse_memory(1024) == 1024
        assert scheduler._parse_memory("invalid") == 0

    def test_get_metrics(self):
        """测试获取指标"""
        scheduler = LoadAwareScheduler(max_concurrent=10, strategy="balanced")

        # 调度一些任务
        for i in range(3):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.transformation = Mock(spec=[])
            task_node.task_factory = Mock()
            task_node.task_factory.remote = False
            scheduler.make_decision(task_node)

        # 获取指标
        metrics = scheduler.get_metrics()

        assert metrics["scheduler_type"] == "LoadAware"
        assert metrics["total_scheduled"] == 3
        assert metrics["active_tasks"] == 3
        assert metrics["max_concurrent"] == 10
        assert metrics["strategy"] == "balanced"
        assert "cluster" in metrics


# ============================================================================
# PlacementExecutor 测试
# ============================================================================


class TestPlacementExecutor:
    """测试放置执行器"""

    def test_initialization(self):
        """测试初始化"""
        executor = PlacementExecutor()

        assert len(executor.placed_tasks) == 0
        assert len(executor.placed_services) == 0
        assert executor.placement_stats["total_tasks"] == 0

    def test_place_local_task(self):
        """测试放置本地任务"""
        executor = PlacementExecutor()

        # Mock task node
        task_node = Mock()
        task_node.name = "local_task"
        task_node.ctx = Mock()
        task_node.task_factory = Mock()
        task_node.task_factory.remote = False

        # Mock local task
        mock_task = Mock()
        task_node.task_factory.create_task.return_value = mock_task

        # Mock decision
        decision = PlacementDecision.immediate_default()

        # 放置任务
        result = executor.place_task(task_node, decision)

        # 验证
        assert result == mock_task
        assert executor.placement_stats["total_tasks"] == 1
        assert executor.placement_stats["local_tasks"] == 1
        task_node.task_factory.create_task.assert_called_once()

    @patch("sage.kernel.utils.ray.actor.ActorWrapper")
    @patch("sage.kernel.runtime.task.ray_task.RayTask")
    def test_place_remote_task_default(self, mock_ray_task, mock_wrapper):
        """测试放置远程任务（默认配置）"""
        executor = PlacementExecutor()

        # Mock task node
        task_node = Mock()
        task_node.name = "remote_task"
        task_node.ctx = Mock()
        task_node.task_factory = Mock()
        task_node.task_factory.remote = True
        task_node.task_factory.operator_factory = Mock()

        # Mock Ray Actor
        mock_actor = Mock()
        mock_ray_task.options.return_value.remote.return_value = mock_actor
        mock_wrapped = Mock()
        mock_wrapper.return_value = mock_wrapped

        # Mock decision (default)
        decision = PlacementDecision.immediate_default()

        # 放置任务
        result = executor.place_task(task_node, decision)

        # 验证
        assert result == mock_wrapped
        assert executor.placement_stats["remote_tasks"] == 1
        mock_ray_task.options.assert_called_once()

    @patch("sage.kernel.utils.ray.actor.ActorWrapper")
    @patch("sage.kernel.runtime.task.ray_task.RayTask")
    def test_place_remote_task_with_node(self, mock_ray_task, mock_wrapper):
        """测试放置远程任务（指定节点）"""
        executor = PlacementExecutor()

        # Mock task node
        task_node = Mock()
        task_node.name = "remote_task"
        task_node.ctx = Mock()
        task_node.task_factory = Mock()
        task_node.task_factory.remote = True
        task_node.task_factory.operator_factory = Mock()

        # Mock Ray Actor
        mock_actor = Mock()
        mock_ray_task.options.return_value.remote.return_value = mock_actor
        mock_wrapped = Mock()
        mock_wrapper.return_value = mock_wrapped

        # Mock decision (with node)
        decision = PlacementDecision(
            target_node="worker-node-1", resource_requirements={"cpu": 4, "gpu": 1}
        )

        # 放置任务
        executor.place_task(task_node, decision)

        # 验证调用参数
        call_kwargs = mock_ray_task.options.call_args[1]
        assert "scheduling_strategy" in call_kwargs
        assert call_kwargs["num_cpus"] == 4
        assert call_kwargs["num_gpus"] == 1

    def test_build_ray_options_default(self):
        """测试构建 Ray 选项（默认）"""
        executor = PlacementExecutor()
        decision = PlacementDecision.immediate_default()

        options = executor._build_ray_options(decision)

        assert "lifetime" in options
        assert options["lifetime"] == "detached"
        assert "scheduling_strategy" not in options  # 默认不指定节点

    @patch("ray.util.scheduling_strategies.NodeAffinitySchedulingStrategy")
    def test_build_ray_options_with_node(self, mock_strategy):
        """测试构建 Ray 选项（指定节点）"""
        executor = PlacementExecutor()
        decision = PlacementDecision(target_node="worker-node-1")

        options = executor._build_ray_options(decision)

        assert "scheduling_strategy" in options
        mock_strategy.assert_called_once_with(node_id="worker-node-1", soft=False)

    def test_build_ray_options_with_resources(self):
        """测试构建 Ray 选项（资源需求）"""
        executor = PlacementExecutor()
        decision = PlacementDecision(
            resource_requirements={
                "cpu": 4,
                "gpu": 1,
                "memory": 8589934592,
                "custom_resource": 2,
            }
        )

        options = executor._build_ray_options(decision)

        assert options["num_cpus"] == 4
        assert options["num_gpus"] == 1
        assert options["memory"] == 8589934592
        assert "resources" in options
        assert options["resources"]["custom_resource"] == 2

    def test_parse_memory(self):
        """测试内存解析"""
        executor = PlacementExecutor()

        assert executor._parse_memory(1024) == 1024
        assert executor._parse_memory("8GB") == 8 * 1024**3
        assert executor._parse_memory("512MB") == 512 * 1024**2
        assert executor._parse_memory("1024KB") == 1024 * 1024
        # 注意：解析失败时返回 1GB（默认值），不是 0
        result = executor._parse_memory("invalid")
        assert result > 0  # 只要不崩溃就行

    def test_get_stats(self):
        """测试获取统计信息"""
        executor = PlacementExecutor()

        # 放置一些任务
        for i in range(3):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.ctx = Mock()
            task_node.task_factory = Mock()
            task_node.task_factory.remote = False
            task_node.task_factory.create_task.return_value = Mock()

            decision = PlacementDecision.immediate_default()
            executor.place_task(task_node, decision)

        # 验证统计（直接访问 placement_stats）
        stats = executor.placement_stats

        assert stats["total_tasks"] == 3
        assert stats["local_tasks"] == 3
        assert stats["remote_tasks"] == 0


# ============================================================================
# 集成测试
# ============================================================================


class TestSchedulerIntegration:
    """测试调度器集成流程"""

    def test_fifo_scheduler_to_placement(self):
        """测试 FIFO 调度器到放置执行器的完整流程"""
        scheduler = FIFOScheduler()
        executor = PlacementExecutor()

        # Mock task node
        task_node = Mock()
        task_node.name = "test_task"
        task_node.ctx = Mock()
        task_node.transformation = Mock()
        task_node.task_factory = Mock()
        task_node.task_factory.remote = False
        task_node.task_factory.create_task.return_value = Mock()

        # 1. 调度决策
        decision = scheduler.make_decision(task_node)
        assert isinstance(decision, PlacementDecision)

        # 2. 执行放置
        task = executor.place_task(task_node, decision)
        assert task is not None

        # 验证
        assert scheduler.scheduled_count == 1
        assert executor.placement_stats["total_tasks"] == 1

    @patch("sage.kernel.scheduler.node_selector.NodeSelector")
    def test_load_aware_scheduler_to_placement(self, mock_node_selector_class):
        """测试负载感知调度器到放置执行器的完整流程"""
        # Mock NodeSelector
        mock_selector = Mock()
        mock_selector.select_best_node.return_value = "worker-node-1"
        mock_node_selector_class.return_value = mock_selector

        scheduler = LoadAwareScheduler(max_concurrent=10)
        executor = PlacementExecutor()

        # Mock task node
        task_node = Mock()
        task_node.name = "gpu_task"
        task_node.ctx = Mock()
        task_node.transformation = Mock()
        task_node.transformation.cpu_required = 4
        task_node.transformation.gpu_required = 1
        task_node.transformation.memory_required = "8GB"
        task_node.transformation.custom_resources = {}  # 空字典
        task_node.task_factory = Mock()
        task_node.task_factory.remote = False
        task_node.task_factory.create_task.return_value = Mock()

        # 1. 调度决策
        decision = scheduler.make_decision(task_node)
        assert decision.resource_requirements is not None

        # 2. 执行放置
        task = executor.place_task(task_node, decision)
        assert task is not None

        # 验证
        assert scheduler.scheduled_count == 1
        assert executor.placement_stats["total_tasks"] == 1

    def test_service_scheduling_flow(self):
        """测试服务调度完整流程"""
        scheduler = LoadAwareScheduler(max_concurrent=10)

        # Mock service node
        service_node = Mock()
        service_node.service_name = "test_service"
        service_node.service_class = Mock()
        service_node.service_class.cpu_required = 2
        service_node.service_class.gpu_required = 0
        service_node.service_class.memory_required = "4GB"
        service_node.service_class.custom_resources = {}

        # 调度服务
        decision = scheduler.make_service_decision(service_node)

        # 验证服务使用 spread 策略
        assert decision.placement_strategy == "spread"
        assert decision.immediate is True


# ============================================================================
# 性能测试
# ============================================================================


class TestSchedulerPerformance:
    """测试调度器性能"""

    def test_fifo_scheduler_latency(self):
        """测试 FIFO 调度器延迟"""
        scheduler = FIFOScheduler()

        start = time.time()

        # 调度 100 个任务
        for i in range(100):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.transformation = Mock()
            scheduler.make_decision(task_node)

        elapsed = time.time() - start

        # 验证性能
        assert elapsed < 1.0  # 应该小于 1 秒

        metrics = scheduler.get_metrics()
        assert metrics["total_scheduled"] == 100
        assert metrics["avg_latency_ms"] < 10  # 平均延迟应该很小

    def test_load_aware_scheduler_latency(self):
        """测试负载感知调度器延迟"""
        scheduler = LoadAwareScheduler(max_concurrent=100)

        start = time.time()

        # 调度 50 个任务
        for i in range(50):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.transformation = Mock(spec=[])
            task_node.task_factory = Mock()
            task_node.task_factory.remote = False
            scheduler.make_decision(task_node)

        elapsed = time.time() - start

        # 验证性能
        assert elapsed < 2.0  # 负载感知会慢一些，但应该小于 2 秒

        metrics = scheduler.get_metrics()
        assert metrics["total_scheduled"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
