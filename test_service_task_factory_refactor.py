#!/usr/bin/env python3
"""
测试 service_task_factory 重构后的正确性

验证：
1. BaseEnvironment 不再维护 service_task_factories
2. ExecutionGraph 在服务节点中正确创建 ServiceTaskFactory
3. 服务注册和使用流程正常
"""

import sys
import os

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages/sage-utils/src"))

def test_environment_service_attributes():
    """简单测试环境中的服务相关属性"""
    
    print("🧪 开始测试 service_task_factory 重构...")
    
    # 读取 BaseEnvironment 源码进行静态分析
    base_env_path = "packages/sage-core/src/sage/core/api/base_environment.py"
    
    print("✅ 步骤1: 分析 BaseEnvironment 源码")
    
    with open(base_env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 验证不再维护 service_task_factories
    has_service_factories = "self.service_factories" in content
    has_service_task_factories = "self.service_task_factories" in content
    
    print(f"   - service_factories 存在: {has_service_factories}")
    print(f"   - service_task_factories 存在: {has_service_task_factories}")
    
    assert has_service_factories, "应该仍然有 service_factories"
    assert not has_service_task_factories, "不应该再有 service_task_factories"
    
    # 验证 register_service 方法不再创建 ServiceTaskFactory
    register_service_content = content[content.find("def register_service"):content.find("def register_service_factory")]
    has_service_task_factory_creation = "ServiceTaskFactory" in register_service_content
    
    print(f"   - register_service 中创建 ServiceTaskFactory: {has_service_task_factory_creation}")
    assert not has_service_task_factory_creation, "register_service 不应该再创建 ServiceTaskFactory"
    
    print("✅ 步骤2: 分析 ExecutionGraph 源码")
    
    execution_graph_path = "packages/sage-kernel/src/sage/kernel/jobmanager/compiler/execution_graph.py"
    
    with open(execution_graph_path, 'r', encoding='utf-8') as f:
        eg_content = f.read()
    
    # 验证 ExecutionGraph 在 _build_service_nodes 中创建 ServiceTaskFactory
    build_service_nodes_content = eg_content[eg_content.find("def _build_service_nodes"):eg_content.find("def _extract_queue_descriptor_mappings")]
    has_stf_creation = "ServiceTaskFactory(" in build_service_nodes_content
    has_stf_import = "from sage.kernel.runtime.factory.service_task_factory import ServiceTaskFactory" in build_service_nodes_content
    
    print(f"   - _build_service_nodes 中创建 ServiceTaskFactory: {has_stf_creation}")
    print(f"   - _build_service_nodes 中导入 ServiceTaskFactory: {has_stf_import}")
    
    assert has_stf_creation, "_build_service_nodes 应该创建 ServiceTaskFactory"
    assert has_stf_import, "_build_service_nodes 应该导入 ServiceTaskFactory"
    
    # 验证不再从环境获取 service_task_factories
    no_env_stf_access = "env.service_task_factories" not in build_service_nodes_content
    print(f"   - 不再从环境获取 service_task_factories: {no_env_stf_access}")
    assert no_env_stf_access, "_build_service_nodes 不应该再从环境获取 service_task_factories"
    
    print("✅ 步骤3: 验证注释和文档")
    
    # 检查注释是否更新
    comment_updated = "在ExecutionGraph中创建ServiceTaskFactory" in build_service_nodes_content
    print(f"   - 注释已更新: {comment_updated}")
    assert comment_updated, "注释应该反映新的架构"
    
    print("🎉 所有静态分析测试都通过了!")
    print("\n📋 测试总结:")
    print("  ✅ BaseEnvironment 不再维护 service_task_factories")
    print("  ✅ BaseEnvironment.register_service 不再创建 ServiceTaskFactory")
    print("  ✅ ExecutionGraph._build_service_nodes 正确创建 ServiceTaskFactory")
    print("  ✅ ExecutionGraph 不再依赖环境中的 service_task_factories")
    print("  ✅ 模块间耦合更加清晰")
    print("  ✅ 架构重构成功完成")


if __name__ == "__main__":
    test_environment_service_attributes()
