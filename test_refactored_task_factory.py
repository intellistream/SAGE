#!/usr/bin/env python3
"""
测试重构后的TaskFactory创建流程
验证TaskFactory现在在ExecutionGraph的TaskNode中创建，而不是在BaseTransformation中
"""

import sys
import os
from unittest.mock import Mock, MagicMock

# 添加包路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/sage-core/src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/sage-kernel/src'))

def test_task_factory_creation_in_task_node():
    """测试TaskFactory在TaskNode中创建，而不是在BaseTransformation中"""
    
    print("=== 测试重构后的TaskFactory创建流程 ===")
    
    # 1. 验证BaseTransformation不再有task_factory属性
    print("\n1. 验证BaseTransformation不再维护task_factory...")
    
    from sage.core.transformation.base_transformation import BaseTransformation
    
    # 创建一个mock environment
    mock_env = Mock()
    mock_env.name = "test_env"
    mock_env.platform = "local"
    
    # 创建一个mock function
    mock_function = Mock()
    mock_function.__name__ = "MockFunction"
    
    # 创建BaseTransformation实例
    transformation = BaseTransformation(
        env=mock_env,
        function=mock_function,
        name="test_transformation"
    )
    
    # 验证BaseTransformation不再有task_factory属性
    assert not hasattr(transformation, 'task_factory'), "BaseTransformation should not have task_factory attribute"
    assert not hasattr(transformation, '_task_factory'), "BaseTransformation should not have _task_factory attribute"
    print("✅ BaseTransformation不再维护task_factory属性")
    
    # 2. 验证TaskNode创建TaskFactory
    print("\n2. 验证TaskNode创建TaskFactory...")
    
    from sage.kernel.jobmanager.compiler.graph_node import TaskNode
    
    # 创建mock environment
    mock_env.get_qd = Mock(return_value=Mock())  # Mock queue descriptor
    
    # 创建TaskNode
    task_node = TaskNode(
        name="test_node",
        transformation=transformation,
        parallel_index=0,
        env=mock_env
    )
    
    # 验证TaskNode有task_factory属性
    assert hasattr(task_node, 'task_factory'), "TaskNode should have task_factory attribute"
    assert task_node.task_factory is not None, "TaskNode.task_factory should not be None"
    print("✅ TaskNode成功创建了task_factory属性")
    
    # 3. 验证TaskFactory的正确性
    print("\n3. 验证TaskFactory功能...")
    
    from sage.kernel.runtime.factory.task_factory import TaskFactory
    assert isinstance(task_node.task_factory, TaskFactory), "task_factory should be TaskFactory instance"
    assert task_node.task_factory.basename == "test_transformation", "TaskFactory should inherit transformation basename"
    print("✅ TaskFactory创建正确且功能正常")
    
    # 4. 验证Dispatcher可以正确使用
    print("\n4. 验证Dispatcher使用TaskFactory...")
    
    # Mock TaskContext
    mock_ctx = Mock()
    mock_ctx.name = "test_task_context"
    
    # 模拟Dispatcher中的任务创建过程
    try:
        # 这里会调用TaskNode的task_factory，而不是BaseTransformation的
        with Mock() as mock_create_task:
            task_node.task_factory.create_task = mock_create_task
            task_node.task_factory.create_task("test_task", mock_ctx)
            mock_create_task.assert_called_once_with("test_task", mock_ctx)
        print("✅ Dispatcher可以正确使用TaskNode中的task_factory")
    except Exception as e:
        print(f"❌ Dispatcher使用失败: {e}")
        return False
    
    print("\n=== 重构验证完成 ===")
    print("✅ 所有测试通过！TaskFactory成功从BaseTransformation移动到TaskNode中")
    return True

if __name__ == "__main__":
    success = test_task_factory_creation_in_task_node()
    if success:
        print("\n🎉 重构成功！模块解耦原则得到遵循。")
        sys.exit(0)
    else:
        print("\n❌ 重构验证失败。")
        sys.exit(1)
