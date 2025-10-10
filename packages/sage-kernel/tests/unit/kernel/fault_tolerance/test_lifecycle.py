"""
LifecycleManagerImpl 单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from sage.kernel.fault_tolerance.impl.lifecycle_impl import LifecycleManagerImpl


class TestLifecycleManagerImpl:
    """LifecycleManagerImpl 基础测试"""

    def test_lifecycle_manager_initialization(self):
        """测试生命周期管理器初始化"""
        manager = LifecycleManagerImpl()
        
        assert manager.logger is None

    def test_lifecycle_manager_with_logger(self):
        """测试设置日志器"""
        manager = LifecycleManagerImpl()
        logger = Mock()
        
        manager.logger = logger
        
        assert manager.logger == logger

    def test_cleanup_actor_basic(self):
        """测试基本 Actor 清理"""
        manager = LifecycleManagerImpl()
        
        actor = Mock()
        actor.is_ray_actor.return_value = False
        actor.cleanup = Mock()
        
        cleanup_success, kill_success = manager.cleanup_actor(
            actor, 
            cleanup_timeout=5.0
        )
        
        assert cleanup_success is True
        assert kill_success is True
        actor.cleanup.assert_called_once()

    def test_cleanup_all_tasks_only(self):
        """测试只清理任务"""
        manager = LifecycleManagerImpl()
        
        tasks = {
            "task_1": Mock(),
            "task_2": Mock(),
        }
        
        for task in tasks.values():
            task.is_ray_actor.return_value = False
            task.cleanup = Mock()
        
        results = manager.cleanup_all(tasks, cleanup_timeout=5.0)
        
        assert len(results) == 2
        assert all(results[task_id][1] for task_id in tasks)  # All kill_success

    def test_cleanup_all_tasks_and_services(self):
        """测试清理任务和服务"""
        manager = LifecycleManagerImpl()
        
        tasks = {
            "task_1": Mock(),
        }
        
        services = {
            "service_1": Mock(),
        }
        
        for item in list(tasks.values()) + list(services.values()):
            item.is_ray_actor.return_value = False
            item.cleanup = Mock()
        
        results = manager.cleanup_all(
            tasks, 
            services=services,
            cleanup_timeout=5.0
        )
        
        assert len(results) == 2
        assert "task_1" in results
        assert "service_1" in results

    def test_cleanup_all_empty_tasks(self):
        """测试清理空任务字典"""
        manager = LifecycleManagerImpl()
        manager.logger = Mock()
        
        # Should not raise any exception
        results = manager.cleanup_all({}, cleanup_timeout=5.0)
        
        assert results == {}


class TestLifecycleManagerImplEdgeCases:
    """LifecycleManagerImpl 边界条件测试"""

    def test_cleanup_actor_with_no_cleanup_method(self):
        """测试清理没有 cleanup 方法的 Actor"""
        manager = LifecycleManagerImpl()
        
        actor = Mock(spec=['is_ray_actor'])
        actor.is_ray_actor.return_value = False
        
        cleanup_success, kill_success = manager.cleanup_actor(actor)
        
        # No cleanup method, so cleanup_success is False
        # But kill_success should be True for local actor
        assert cleanup_success is False
        assert kill_success is True


class TestLifecycleManagerImplIntegration:
    """LifecycleManagerImpl 集成测试"""

    def test_complete_cleanup_workflow(self):
        """测试完整的清理流程"""
        manager = LifecycleManagerImpl()
        manager.logger = Mock()
        
        # Create tasks and services
        tasks = {}
        services = {}
        
        for i in range(3):
            task = Mock()
            task.is_ray_actor.return_value = False
            task.cleanup = Mock()
            tasks[f"task_{i}"] = task
            
            service = Mock()
            service.is_ray_actor.return_value = False
            service.cleanup = Mock()
            services[f"service_{i}"] = service
        
        # Cleanup all
        results = manager.cleanup_all(tasks, services=services, cleanup_timeout=5.0)
        
        assert len(results) == 6  # 3 tasks + 3 services
        assert all(results[item_id][1] for item_id in results)  # All kill_success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
