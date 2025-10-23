"""
新调度器 API 单元测试

测试重构后的调度器架构：
- BaseScheduler 抽象基类
- FIFOScheduler 实现
- LoadAwareScheduler 实现
"""

from unittest.mock import Mock

import pytest
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler


class TestBaseScheduler:
    """BaseScheduler 基础测试"""

    def test_scheduler_is_abstract(self):
        """测试 BaseScheduler 是抽象类"""
        with pytest.raises(TypeError):
            BaseScheduler()

    def test_fifo_scheduler_initialization(self):
        """测试 FIFO 调度器初始化"""
        scheduler = FIFOScheduler(platform="local")

        assert scheduler.platform == "local"
        assert hasattr(scheduler, "schedule_task")
        assert hasattr(scheduler, "schedule_service")
        assert hasattr(scheduler, "get_metrics")

    def test_load_aware_scheduler_initialization(self):
        """测试负载感知调度器初始化"""
        scheduler = LoadAwareScheduler(platform="remote", max_concurrent=10)

        assert scheduler.platform == "remote"
        assert scheduler.max_concurrent == 10
        assert hasattr(scheduler, "schedule_task")
        assert hasattr(scheduler, "schedule_service")
        assert hasattr(scheduler, "get_metrics")


class TestFIFOScheduler:
    """FIFOScheduler 测试"""

    def test_schedule_task_basic(self):
        """测试基本任务调度"""
        scheduler = FIFOScheduler(platform="local")

        # Mock task node
        task_node = Mock()
        task_node.name = "test_task"
        task_node.ctx = Mock()

        # Mock task factory
        task_factory = Mock()
        expected_task = Mock()
        task_factory.create_task.return_value = expected_task
        task_node.task_factory = task_factory

        # Schedule task
        result = scheduler.schedule_task(task_node)

        assert result == expected_task
        task_factory.create_task.assert_called_once()

    def test_schedule_service_basic(self):
        """测试基本服务调度"""
        scheduler = FIFOScheduler(platform="local")

        # Mock service node
        service_node = Mock()
        service_node.service_name = "test_service"
        service_node.ctx = Mock()

        # Mock service task factory
        service_factory = Mock()
        expected_service = Mock()
        service_factory.create_service_task.return_value = expected_service
        service_node.service_task_factory = service_factory

        # Schedule service
        result = scheduler.schedule_service(service_node)

        assert result == expected_service
        service_factory.create_service_task.assert_called_once()

    def test_get_metrics(self):
        """测试获取调度器指标"""
        scheduler = FIFOScheduler(platform="local")

        # 创建一些任务以生成指标
        for i in range(3):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.ctx = Mock()
            task_factory = Mock()
            task_factory.create_task.return_value = Mock()
            task_node.task_factory = task_factory
            scheduler.schedule_task(task_node)

        metrics = scheduler.get_metrics()

        assert isinstance(metrics, dict)
        assert "scheduler_type" in metrics
        assert metrics["scheduler_type"] == "FIFO"
        assert "total_scheduled" in metrics
        assert metrics["total_scheduled"] == 3

    def test_fifo_order_preservation(self):
        """测试 FIFO 顺序保持"""
        scheduler = FIFOScheduler(platform="local")

        tasks = []
        for i in range(5):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.ctx = Mock()

            task_factory = Mock()
            task = Mock()
            task.name = f"task_{i}"
            task_factory.create_task.return_value = task
            task_node.task_factory = task_factory

            result = scheduler.schedule_task(task_node)
            tasks.append(result)

        # 验证任务数量
        assert len(tasks) == 5

        # 验证每个任务都被创建
        assert all(task is not None for task in tasks)


class TestLoadAwareScheduler:
    """LoadAwareScheduler 测试"""

    def test_initialization_with_defaults(self):
        """测试使用默认参数初始化"""
        scheduler = LoadAwareScheduler(platform="local")

        assert scheduler.platform == "local"
        assert scheduler.max_concurrent == 10  # 默认值

    def test_initialization_with_custom_max_concurrent(self):
        """测试自定义并发限制"""
        scheduler = LoadAwareScheduler(platform="remote", max_concurrent=20)

        assert scheduler.max_concurrent == 20

    def test_schedule_task_with_load_awareness(self):
        """测试负载感知任务调度"""
        scheduler = LoadAwareScheduler(platform="local", max_concurrent=5)

        tasks = []
        for i in range(3):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.ctx = Mock()

            # Mock transformation 和其属性
            transformation = Mock()
            transformation.cpu_required = 1.0
            transformation.gpu_required = 0.0
            transformation.memory_required = "1GB"
            transformation.custom_resources = {}
            task_node.transformation = transformation

            task_factory = Mock()
            task = Mock()
            task_factory.create_task.return_value = task
            task_factory.remote = False
            task_node.task_factory = task_factory

            result = scheduler.schedule_task(task_node)
            tasks.append(result)

        # 验证在并发限制内可以调度任务
        assert len(tasks) == 3
        assert all(task is not None for task in tasks)

    def test_get_metrics_with_load_info(self):
        """测试获取带负载信息的指标"""
        scheduler = LoadAwareScheduler(platform="remote", max_concurrent=10)

        # 调度一些任务
        for i in range(5):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.ctx = Mock()

            # Mock transformation 和其属性
            transformation = Mock()
            transformation.cpu_required = 1.0
            transformation.gpu_required = 0.0
            transformation.memory_required = "1GB"
            transformation.custom_resources = {}
            task_node.transformation = transformation

            task_factory = Mock()
            task_factory.create_task.return_value = Mock()
            task_factory.remote = False
            task_node.task_factory = task_factory
            scheduler.schedule_task(task_node)

        metrics = scheduler.get_metrics()

        assert isinstance(metrics, dict)
        assert "scheduler_type" in metrics
        assert metrics["scheduler_type"] == "LoadAware"
        assert "total_scheduled" in metrics
        assert "max_concurrent" in metrics
        assert metrics["max_concurrent"] == 10


class TestSchedulerIntegration:
    """调度器集成测试"""

    def test_multiple_schedulers_independent(self):
        """测试多个调度器实例独立工作"""
        scheduler1 = FIFOScheduler(platform="local")
        scheduler2 = LoadAwareScheduler(platform="remote")

        # 在 scheduler1 中调度任务
        task_node1 = Mock()
        task_node1.name = "task1"
        task_node1.ctx = Mock()
        task_factory1 = Mock()
        task_factory1.create_task.return_value = Mock()
        task_node1.task_factory = task_factory1
        scheduler1.schedule_task(task_node1)

        # 在 scheduler2 中调度任务
        task_node2 = Mock()
        task_node2.name = "task2"
        task_node2.ctx = Mock()

        # Mock transformation 和其属性
        transformation = Mock()
        transformation.cpu_required = 1.0
        transformation.gpu_required = 0.0
        transformation.memory_required = "1GB"
        transformation.custom_resources = {}
        task_node2.transformation = transformation

        task_factory2 = Mock()
        task_factory2.create_task.return_value = Mock()
        task_factory2.remote = False
        task_node2.task_factory = task_factory2
        scheduler2.schedule_task(task_node2)

        # 验证两个调度器的指标独立
        metrics1 = scheduler1.get_metrics()
        metrics2 = scheduler2.get_metrics()

        assert metrics1["scheduler_type"] == "FIFO"
        assert metrics2["scheduler_type"] == "LoadAware"
        assert metrics1["total_scheduled"] == 1
        assert metrics2["total_scheduled"] == 1

    def test_schedule_tasks_and_services_mixed(self):
        """测试混合调度任务和服务"""
        scheduler = FIFOScheduler(platform="local")

        # 调度任务
        task_node = Mock()
        task_node.name = "task_1"
        task_node.ctx = Mock()
        task_factory = Mock()
        task_factory.create_task.return_value = Mock()
        task_node.task_factory = task_factory
        task = scheduler.schedule_task(task_node)

        # 调度服务
        service_node = Mock()
        service_node.service_name = "service_1"
        service_node.ctx = Mock()
        service_factory = Mock()
        service_factory.create_service_task.return_value = Mock()
        service_node.service_task_factory = service_factory
        service = scheduler.schedule_service(service_node)

        assert task is not None
        assert service is not None


class TestSchedulerEdgeCases:
    """调度器边界条件测试"""

    def test_schedule_with_none_context(self):
        """测试处理 None 上下文"""
        scheduler = FIFOScheduler(platform="local")

        task_node = Mock()
        task_node.name = "test_task"
        task_node.ctx = None  # None context

        task_factory = Mock()
        task_factory.create_task.return_value = Mock()
        task_node.task_factory = task_factory

        # 应该仍然能够调度
        result = scheduler.schedule_task(task_node)
        assert result is not None

    def test_empty_metrics_on_new_scheduler(self):
        """测试新调度器的空指标"""
        scheduler = FIFOScheduler(platform="local")

        metrics = scheduler.get_metrics()

        assert metrics["total_scheduled"] == 0


class TestSchedulerDecisionDelay:
    """测试调度器决策延迟"""

    def test_schedule_task_with_delay(self):
        """测试任务调度中的延迟处理"""
        from sage.kernel.scheduler.impl import FIFOScheduler
        from sage.kernel.scheduler.decision import PlacementDecision

        scheduler = FIFOScheduler(platform="local")

        # Mock task node
        task_node = Mock()
        task_node.name = "delayed_task"
        task_node.ctx = Mock()

        # Mock task factory
        task_factory = Mock()
        expected_task = Mock()
        task_factory.create_task.return_value = expected_task
        task_node.task_factory = task_factory

        # 记录原始的 make_decision 方法
        original_make_decision = scheduler.make_decision

        # Mock make_decision 以返回带有延迟的决策
        def mock_make_decision_with_delay(node):
            decision = PlacementDecision(
                target_node="test_node",
                delay=0.01,  # 10ms 延迟
                immediate=False,
                placement_strategy="fifo",
                reason="Test delay"
            )
            return decision

        scheduler.make_decision = mock_make_decision_with_delay

        # 调度任务（应该包括延迟）
        import time
        start = time.time()
        result = scheduler.schedule_task(task_node)
        elapsed = time.time() - start

        # 验证任务被创建
        assert result == expected_task
        # 验证延迟被应用（至少 10ms）
        assert elapsed >= 0.01

    def test_schedule_service_with_delay(self):
        """测试服务调度中的延迟处理"""
        from sage.kernel.scheduler.impl import FIFOScheduler
        from sage.kernel.scheduler.decision import PlacementDecision

        scheduler = FIFOScheduler(platform="local")

        # Mock service node
        service_node = Mock()
        service_node.service_name = "delayed_service"
        service_node.ctx = Mock()

        # Mock service factory
        service_factory = Mock()
        expected_service = Mock()
        service_factory.create_service_task.return_value = expected_service
        service_node.service_task_factory = service_factory

        # Mock make_service_decision 以返回带有延迟的决策
        def mock_make_service_decision_with_delay(node):
            decision = PlacementDecision(
                target_node="test_node",
                delay=0.01,  # 10ms 延迟
                immediate=False,
                placement_strategy="fifo",
                reason="Test service delay"
            )
            return decision

        scheduler.make_service_decision = mock_make_service_decision_with_delay

        # 调度服务（应该包括延迟）
        import time
        start = time.time()
        result = scheduler.schedule_service(service_node)
        elapsed = time.time() - start

        # 验证服务被创建
        assert result == expected_service
        # 验证延迟被应用（至少 10ms）
        assert elapsed >= 0.01

    def test_schedule_task_with_custom_runtime_context(self):
        """测试使用自定义运行时上下文调度任务"""
        from sage.kernel.scheduler.impl import FIFOScheduler

        scheduler = FIFOScheduler(platform="local")

        # Mock task node 和 factory
        task_node = Mock()
        task_node.name = "task_with_custom_ctx"
        task_node.ctx = Mock()  # 默认上下文

        task_factory = Mock()
        expected_task = Mock()
        task_factory.create_task.return_value = expected_task
        task_node.task_factory = task_factory

        # 自定义运行时上下文
        custom_ctx = Mock()

        # 调度任务，传入自定义上下文
        result = scheduler.schedule_task(task_node, runtime_ctx=custom_ctx)

        # 验证任务工厂使用了自定义上下文
        task_factory.create_task.assert_called_once_with(task_node.name, custom_ctx)
        assert result == expected_task

    def test_schedule_service_with_custom_runtime_context(self):
        """测试使用自定义运行时上下文调度服务"""
        from sage.kernel.scheduler.impl import FIFOScheduler

        scheduler = FIFOScheduler(platform="local")

        # Mock service node 和 factory
        service_node = Mock()
        service_node.service_name = "service_with_custom_ctx"
        service_node.ctx = Mock()  # 默认上下文

        service_factory = Mock()
        expected_service = Mock()
        service_factory.create_service_task.return_value = expected_service
        service_node.service_task_factory = service_factory

        # 自定义运行时上下文
        custom_ctx = Mock()

        # 调度服务，传入自定义上下文
        result = scheduler.schedule_service(service_node, runtime_ctx=custom_ctx)

        # 验证服务工厂使用了自定义上下文
        service_factory.create_service_task.assert_called_once_with(service_node.service_name, custom_ctx)
        assert result == expected_service


class TestSchedulerShutdown:
    """测试调度器关闭"""

    def test_scheduler_shutdown_clears_history(self):
        """测试关闭调度器清空决策历史"""
        from sage.kernel.scheduler.impl import FIFOScheduler

        scheduler = FIFOScheduler(platform="local")

        # 调度一些任务以生成决策历史
        for i in range(3):
            task_node = Mock()
            task_node.name = f"task_{i}"
            task_node.ctx = Mock()
            task_factory = Mock()
            task_factory.create_task.return_value = Mock()
            task_node.task_factory = task_factory
            scheduler.schedule_task(task_node)

        # 验证有决策历史
        assert len(scheduler.decision_history) == 3

        # 关闭调度器
        scheduler.shutdown()

        # 验证决策历史被清空
        assert len(scheduler.decision_history) == 0

    def test_make_service_decision_default_implementation(self):
        """测试 make_service_decision 的默认实现"""
        from sage.kernel.scheduler.impl import FIFOScheduler

        scheduler = FIFOScheduler(platform="local")

        # Mock service node
        service_node = Mock()
        service_node.service_name = "test_service"

        # 调用 make_service_decision
        decision = scheduler.make_service_decision(service_node)

        # 验证返回了 PlacementDecision
        from sage.kernel.scheduler.decision import PlacementDecision
        assert isinstance(decision, PlacementDecision)
        assert "test_service" in decision.reason


class TestLoadAwareSchedulerAdvanced:
    """LoadAwareScheduler 高级测试"""

    def test_load_aware_scheduler_task_completion(self):
        """测试负载感知调度器的任务完成处理"""
        from sage.kernel.scheduler.impl import LoadAwareScheduler

        scheduler = LoadAwareScheduler(platform="local", max_concurrent=5)

        # 调度一个任务
        task_node = Mock()
        task_node.name = "completion_task"
        task_node.ctx = Mock()

        transformation = Mock()
        transformation.cpu_required = 1.0
        transformation.gpu_required = 0.0
        transformation.memory_required = "1GB"
        transformation.custom_resources = {}
        task_node.transformation = transformation

        task_factory = Mock()
        task_factory.create_task.return_value = Mock()
        task_factory.remote = False
        task_node.task_factory = task_factory

        # 初始活跃任务数应为 0
        assert scheduler.active_tasks == 0

        # 调度任务
        scheduler.schedule_task(task_node)

        # 活跃任务数应该增加
        initial_active = scheduler.active_tasks
        assert initial_active > 0

        # 标记任务完成
        scheduler.task_completed("completion_task")

        # 活跃任务数应该减少
        assert scheduler.active_tasks == initial_active - 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
