"""
TaskScheduler 单元测试
"""

from unittest.mock import MagicMock, Mock

import pytest
from sage.kernel.scheduler.placement import SimplePlacementStrategy
from sage.kernel.scheduler.resource_manager import ResourceManager
from sage.kernel.scheduler.task_scheduler import TaskScheduler


class TestTaskScheduler:
    """TaskScheduler 基础测试"""

    def test_scheduler_initialization_local(self):
        """测试本地平台调度器初始化"""
        scheduler = TaskScheduler(platform="local")

        assert scheduler.platform == "local"
        assert scheduler.resource_manager is not None
        assert scheduler.placement_strategy is not None
        assert isinstance(scheduler.placement_strategy, SimplePlacementStrategy)

    def test_scheduler_initialization_remote(self):
        """测试远程平台调度器初始化"""
        scheduler = TaskScheduler(platform="remote")

        assert scheduler.platform == "remote"
        assert scheduler.resource_manager is not None
        assert scheduler.placement_strategy is not None

    def test_scheduler_with_custom_placement_strategy(self):
        """测试使用自定义放置策略"""
        custom_strategy = Mock(spec=SimplePlacementStrategy)
        scheduler = TaskScheduler(platform="local", placement_strategy=custom_strategy)

        assert scheduler.placement_strategy == custom_strategy

    def test_scheduler_with_custom_resource_manager(self):
        """测试使用自定义资源管理器"""
        custom_manager = Mock(spec=ResourceManager)
        scheduler = TaskScheduler(platform="local", resource_manager=custom_manager)

        assert scheduler.resource_manager == custom_manager

    def test_schedule_task_basic(self):
        """测试基本任务调度"""
        scheduler = TaskScheduler(platform="local")

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
        task_factory.create_task.assert_called_once_with(task_node.name, task_node.ctx)

    def test_schedule_task_with_runtime_ctx(self):
        """测试使用运行时上下文调度任务"""
        scheduler = TaskScheduler(platform="local")

        # Mock task node
        task_node = Mock()
        task_node.name = "test_task"
        task_node.ctx = Mock()

        # Mock runtime context
        runtime_ctx = Mock()

        # Mock task factory
        task_factory = Mock()
        expected_task = Mock()
        task_factory.create_task.return_value = expected_task
        task_node.task_factory = task_factory

        # Schedule task with runtime context
        result = scheduler.schedule_task(task_node, runtime_ctx=runtime_ctx)

        assert result == expected_task
        # Should use runtime_ctx instead of task_node.ctx
        task_factory.create_task.assert_called_once_with(task_node.name, runtime_ctx)

    def test_schedule_service_basic(self):
        """测试基本服务调度"""
        scheduler = TaskScheduler(platform="local")

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
        service_factory.create_service_task.assert_called_once_with(service_node.ctx)

    def test_schedule_service_with_runtime_ctx(self):
        """测试使用运行时上下文调度服务"""
        scheduler = TaskScheduler(platform="local")

        # Mock service node
        service_node = Mock()
        service_node.service_name = "test_service"
        service_node.ctx = Mock()

        # Mock runtime context
        runtime_ctx = Mock()

        # Mock service task factory
        service_factory = Mock()
        expected_service = Mock()
        service_factory.create_service_task.return_value = expected_service
        service_node.service_task_factory = service_factory

        # Schedule service with runtime context
        result = scheduler.schedule_service(service_node, runtime_ctx=runtime_ctx)

        assert result == expected_service
        # Should use runtime_ctx instead of service_node.ctx
        service_factory.create_service_task.assert_called_once_with(runtime_ctx)

    def test_get_placement_decision(self):
        """测试获取放置决策"""
        scheduler = TaskScheduler(platform="local")

        # Mock node
        node = Mock()

        # Mock placement strategy
        scheduler.placement_strategy = Mock()
        scheduler.placement_strategy.decide_placement.return_value = "local"

        result = scheduler.get_placement_decision(node)

        assert result == "local"
        scheduler.placement_strategy.decide_placement.assert_called_once_with(node)

    def test_get_resource_status(self):
        """测试获取资源状态"""
        scheduler = TaskScheduler(platform="remote")

        # Mock resource manager
        scheduler.resource_manager = Mock()
        scheduler.resource_manager.get_available_resources.return_value = {"cpu": 4}
        scheduler.resource_manager.get_resource_usage.return_value = {"cpu": 2}

        status = scheduler.get_resource_status()

        assert status["platform"] == "remote"
        assert status["available_resources"] == {"cpu": 4}
        assert status["resource_usage"] == {"cpu": 2}

    def test_shutdown(self):
        """测试调度器关闭"""
        scheduler = TaskScheduler(platform="local")

        # Should not raise any exceptions
        scheduler.shutdown()


class TestTaskSchedulerEdgeCases:
    """TaskScheduler 边界条件测试"""

    def test_schedule_task_with_none_runtime_ctx(self):
        """测试 runtime_ctx 为 None 时使用节点上下文"""
        scheduler = TaskScheduler(platform="local")

        task_node = Mock()
        task_node.name = "test_task"
        node_ctx = Mock()
        task_node.ctx = node_ctx

        task_factory = Mock()
        task_factory.create_task.return_value = Mock()
        task_node.task_factory = task_factory

        scheduler.schedule_task(task_node, runtime_ctx=None)

        # Should use node_ctx
        task_factory.create_task.assert_called_once_with(task_node.name, node_ctx)

    def test_schedule_service_with_none_runtime_ctx(self):
        """测试 runtime_ctx 为 None 时使用节点上下文"""
        scheduler = TaskScheduler(platform="local")

        service_node = Mock()
        node_ctx = Mock()
        service_node.ctx = node_ctx

        service_factory = Mock()
        service_factory.create_service_task.return_value = Mock()
        service_node.service_task_factory = service_factory

        scheduler.schedule_service(service_node, runtime_ctx=None)

        # Should use node_ctx
        service_factory.create_service_task.assert_called_once_with(node_ctx)

    def test_multiple_schedulers_independent(self):
        """测试多个调度器实例独立工作"""
        scheduler1 = TaskScheduler(platform="local")
        scheduler2 = TaskScheduler(platform="remote")

        assert scheduler1.platform == "local"
        assert scheduler2.platform == "remote"
        assert scheduler1.resource_manager is not scheduler2.resource_manager


class TestTaskSchedulerIntegration:
    """TaskScheduler 集成测试"""

    def test_schedule_multiple_tasks(self):
        """测试调度多个任务"""
        scheduler = TaskScheduler(platform="local")

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

        assert len(tasks) == 5
        assert all(isinstance(t, Mock) for t in tasks)

    def test_schedule_tasks_and_services(self):
        """测试同时调度任务和服务"""
        scheduler = TaskScheduler(platform="remote")

        # Schedule a task
        task_node = Mock()
        task_node.name = "task_1"
        task_node.ctx = Mock()
        task_factory = Mock()
        task_factory.create_task.return_value = Mock()
        task_node.task_factory = task_factory

        task = scheduler.schedule_task(task_node)

        # Schedule a service
        service_node = Mock()
        service_node.ctx = Mock()
        service_factory = Mock()
        service_factory.create_service_task.return_value = Mock()
        service_node.service_task_factory = service_factory

        service = scheduler.schedule_service(service_node)

        assert task is not None
        assert service is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
