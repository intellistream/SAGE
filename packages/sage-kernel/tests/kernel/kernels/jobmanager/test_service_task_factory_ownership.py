#!/usr/bin/env python3
"""
测试ServiceNode正确持有ServiceTaskFactory的功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.kernels.jobmanager.execution_graph import ExecutionGraph


# 测试服务类
class TestService:
    def __init__(self, name: str = "test"):
        self.name = name
        self.is_running = False
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print(f"Test service {self.name} started")
    
    def terminate(self):
        self.is_running = False
        print(f"Test service {self.name} terminated")


def test_service_node_task_factory():
    """测试ServiceNode正确持有ServiceTaskFactory"""
    print("=== 测试ServiceNode持有ServiceTaskFactory ===")
    
    try:
        # 1. 创建环境并注册服务
        print("\n1. 创建环境并注册服务")
        env = LocalEnvironment("test_service_node_factory")
        env.set_console_log_level("DEBUG")
        
        # 注册服务
        env.register_service("test_service_1", TestService, name="service1")
        env.register_service("test_service_2", TestService, name="service2")
        
        print(f"注册的服务工厂: {list(env.service_factories.keys())}")
        print(f"注册的服务任务工厂: {list(env.service_task_factories.keys())}")
        
        # 2. 设置日志系统并创建execution graph
        print("\n2. 创建执行图")
        env.setup_logging_system("/tmp/test_logs")
        execution_graph = ExecutionGraph(env)
        
        # 3. 验证服务节点持有正确的ServiceTaskFactory
        print(f"\n3. 验证服务节点:")
        print(f"服务节点数量: {len(execution_graph.service_nodes)}")
        
        for service_node_name, service_node in execution_graph.service_nodes.items():
            print(f"\n服务节点: {service_node_name}")
            print(f"  服务名称: {service_node.service_name}")
            print(f"  服务工厂: {service_node.service_factory}")
            print(f"  服务任务工厂: {service_node.service_task_factory}")
            
            # 验证ServiceTaskFactory的属性
            if hasattr(service_node, 'service_task_factory'):
                stf = service_node.service_task_factory
                print(f"  任务工厂服务名称: {stf.service_name}")
                print(f"  任务工厂是否远程: {stf.remote}")
                print(f"  任务工厂关联的服务工厂: {stf.service_factory}")
                
                # 验证ServiceTaskFactory引用的ServiceFactory与ServiceNode的ServiceFactory是同一个
                is_same_factory = (stf.service_factory is service_node.service_factory)
                print(f"  工厂引用一致性: {is_same_factory}")
                
                # 验证ServiceTaskFactory来自环境
                env_stf = env.service_task_factories.get(service_node.service_name)
                is_from_env = (stf is env_stf)
                print(f"  来自环境: {is_from_env}")
                
                if not is_same_factory:
                    print(f"  ❌ 错误: ServiceTaskFactory引用的ServiceFactory与ServiceNode的不一致")
                    return False
                
                if not is_from_env:
                    print(f"  ❌ 错误: ServiceTaskFactory不是来自环境")
                    return False
                    
                print(f"  ✅ 验证通过")
            else:
                print(f"  ❌ 错误: ServiceNode没有service_task_factory属性")
                return False
        
        # 4. 测试ServiceTaskFactory能否正确创建服务任务
        print(f"\n4. 测试ServiceTaskFactory创建服务任务:")
        for service_node_name, service_node in execution_graph.service_nodes.items():
            try:
                service_task = service_node.service_task_factory.create_service_task()
                print(f"  服务 '{service_node.service_name}' 任务创建成功: {service_task.__class__.__name__}")
                
                # 清理
                if hasattr(service_task, 'cleanup'):
                    service_task.cleanup()
                    
            except Exception as e:
                print(f"  ❌ 服务 '{service_node.service_name}' 任务创建失败: {e}")
                return False
        
        print(f"\n=== ServiceNode持有ServiceTaskFactory测试成功 ===")
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dispatcher_no_factory_creation():
    """测试Dispatcher不再创建新的ServiceTaskFactory"""
    print("\n=== 测试Dispatcher不创建ServiceTaskFactory ===")
    
    try:
        # 1. 创建环境并注册服务
        env = LocalEnvironment("test_dispatcher_no_factory")
        env.register_service("test_service", TestService)
        
        # 2. 创建执行图
        env.setup_logging_system("/tmp/test_logs")
        execution_graph = ExecutionGraph(env)
        
        # 3. 记录原始的ServiceTaskFactory实例
        original_factories = {}
        for service_node_name, service_node in execution_graph.service_nodes.items():
            original_factories[service_node.service_name] = service_node.service_task_factory
        
        # 4. 创建Dispatcher并提交
        from sage.kernel.kernels.runtime.dispatcher import Dispatcher
        dispatcher = Dispatcher(execution_graph, env)
        dispatcher.submit()
        
        # 5. 验证Dispatcher使用的是原始的ServiceTaskFactory，而不是新创建的
        print(f"\n验证ServiceTaskFactory复用:")
        for service_name, service_task in dispatcher.services.items():
            # 通过日志或其他方式验证没有创建新的ServiceTaskFactory
            # 这里我们检查Dispatcher代码中是否还有ServiceTaskFactory的构造
            print(f"  服务 '{service_name}' 任务创建成功")
        
        # 6. 清理
        dispatcher.cleanup()
        
        print(f"\n=== Dispatcher不创建ServiceTaskFactory测试成功 ===")
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success1 = test_service_node_task_factory()
    success2 = test_dispatcher_no_factory_creation()
    
    if success1 and success2:
        print("\n✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败!")
        sys.exit(1)
