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

            task_factory = Mock()
            task = Mock()
            task_factory.create_task.return_value = task
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
            task_factory = Mock()
            task_factory.create_task.return_value = Mock()
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
        task_factory2 = Mock()
        task_factory2.create_task.return_value = Mock()
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
