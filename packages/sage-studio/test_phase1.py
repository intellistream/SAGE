#!/usr/bin/env python3
"""
SAGE Studio v2.0 测试脚本

验证核心接口抽象是否正常工作
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sage.studio.core.plugin_manager import initialize_plugin_system, get_available_nodes, create_node, get_plugin_status
from src.sage.studio.core.flow_engine import create_simple_flow, execute_flow, FlowStatus


async def test_plugin_system():
    """测试插件系统"""
    print("=" * 60)
    print("🧪 Testing Plugin System")
    print("=" * 60)
    
    # 初始化插件系统
    initialize_plugin_system()
    
    # 获取插件状态
    status = get_plugin_status()
    print(f"\n📊 Plugin Status:")
    print(json.dumps(status, indent=2))
    
    # 列出所有节点
    print(f"\n📝 Available Nodes ({status['total_nodes']}):")
    nodes = get_available_nodes()
    for node in nodes:
        print(f"   • {node.name} ({node.id})")
        print(f"     Category: {node.category}")
        print(f"     Description: {node.description}")
        print(f"     Tags: {', '.join(node.tags)}")
        print()
    
    return status['total_nodes'] > 0


async def test_node_creation():
    """测试节点创建"""
    print("=" * 60)
    print("🔧 Testing Node Creation")
    print("=" * 60)
    
    test_nodes = ["file_reader", "http_request", "json_parser", "logger"]
    
    success_count = 0
    for node_id in test_nodes:
        try:
            node = create_node(node_id)
            if node:
                print(f"✅ Created {node.metadata.name}")
                print(f"   ID: {node_id}")
                print(f"   Description: {node.metadata.description}")
                success_count += 1
            else:
                print(f"❌ Failed to create node: {node_id}")
        except Exception as e:
            print(f"❌ Error creating {node_id}: {e}")
    
    print(f"\n📊 Node Creation Results: {success_count}/{len(test_nodes)} successful")
    return success_count == len(test_nodes)


async def test_node_execution():
    """测试节点执行"""
    print("=" * 60)
    print("⚙️  Testing Node Execution")
    print("=" * 60)
    
    from src.sage.studio.core.node_interface import ExecutionContext
    
    # 测试 Logger 节点
    try:
        logger_node = create_node("logger")
        if logger_node:
            context = ExecutionContext(
                node_id="test_logger",
                inputs={"data": "Hello from SAGE Studio v2.0!", "level": "info", "message": "Test log"},
                config={}
            )
            
            result = await logger_node.execute(context)
            
            if result.success:
                print("✅ Logger node executed successfully")
                print(f"   Result: {result.outputs}")
            else:
                print(f"❌ Logger node failed: {result.error}")
                return False
        else:
            print("❌ Failed to create logger node")
            return False
    except Exception as e:
        print(f"❌ Error testing logger node: {e}")
        return False
    
    # 测试 JSON Parser 节点
    try:
        json_parser = create_node("json_parser")
        if json_parser:
            context = ExecutionContext(
                node_id="test_parser",
                inputs={"json_string": '{"name": "SAGE Studio", "version": "2.0"}'},
                config={}
            )
            
            result = await json_parser.execute(context)
            
            if result.success:
                print("✅ JSON Parser node executed successfully")
                print(f"   Parsed data: {result.outputs}")
            else:
                print(f"❌ JSON Parser node failed: {result.error}")
                return False
        else:
            print("❌ Failed to create JSON parser node")
            return False
    except Exception as e:
        print(f"❌ Error testing JSON parser node: {e}")
        return False
    
    return True


async def test_flow_engine():
    """测试流程引擎"""
    print("=" * 60)
    print("🚀 Testing Flow Engine")
    print("=" * 60)
    
    try:
        # 创建测试流程
        flow = create_simple_flow("Test Workflow", [
            {
                "node_id": "json_parser",
                "name": "Parse JSON",
                "inputs": {"json_string": '{"message": "Hello World", "number": 42}'}
            },
            {
                "node_id": "logger", 
                "name": "Log Result",
                "inputs": {"level": "info"}
            }
        ])
        
        print(f"📋 Created flow: {flow.name}")
        print(f"   Nodes: {len(flow.nodes)}")
        print(f"   Connections: {len(flow.connections)}")
        print(f"   Entry nodes: {flow.entry_nodes}")
        
        # 执行流程
        print(f"\n🚀 Executing flow...")
        execution = await execute_flow(flow)
        
        print(f"\n📊 Flow Execution Results:")
        print(f"   Status: {execution.status.value}")
        print(f"   Execution time: {execution.execution_time:.3f}s")
        
        if execution.status == FlowStatus.COMPLETED:
            print("✅ Flow executed successfully")
            
            # 显示节点执行结果
            print(f"\n📋 Node Results:")
            for node in flow.nodes:
                print(f"   • {node.name}: {node.status.value}")
                if node.error_message:
                    print(f"     Error: {node.error_message}")
                print(f"     Execution time: {node.execution_time:.3f}s")
            
            return True
        else:
            print(f"❌ Flow execution failed")
            if execution.error_message:
                print(f"   Error: {execution.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing flow engine: {e}")
        return False


async def test_sage_adapter():
    """测试 SAGE 适配器"""
    print("=" * 60)
    print("🔌 Testing SAGE Adapter")
    print("=" * 60)
    
    try:
        from src.sage.studio.adapters import is_sage_available
        
        if is_sage_available():
            print("✅ SAGE is available, testing adapters...")
            
            # 尝试加载 SAGE 适配器节点
            from src.sage.studio.adapters import FileSourceAdapter
            
            adapter = FileSourceAdapter()
            print(f"✅ Created SAGE adapter: {adapter.metadata.name}")
            print(f"   Description: {adapter.metadata.description}")
            
            return True
        else:
            print("⚠️  SAGE not available, skipping adapter tests")
            print("   This is expected if SAGE kernel is not installed")
            return True
            
    except Exception as e:
        print(f"❌ Error testing SAGE adapter: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    print("🎯 SAGE Studio v2.0 - Interface Abstraction Tests")
    print("=" * 60)
    
    test_results = {}
    
    # 运行各项测试
    test_results["plugin_system"] = await test_plugin_system()
    test_results["node_creation"] = await test_node_creation()
    test_results["node_execution"] = await test_node_execution()
    test_results["flow_engine"] = await test_flow_engine()
    test_results["sage_adapter"] = await test_sage_adapter()
    
    # 统计结果
    passed = sum(test_results.values())
    total = len(test_results)
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! SAGE Studio v2.0 Phase 1 is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(run_all_tests())
    
    if success:
        print("\n✨ Phase 1 (Interface Abstraction) is complete and validated!")
        print("\n🚀 Next Steps:")
        print("   1. Implement visual flow editor (React Flow)")
        print("   2. Add more builtin nodes")
        print("   3. Enhance SAGE adapters")
        print("   4. Add flow persistence")
        print("   5. Implement AI-assisted features")
    else:
        print("\n❌ Tests failed. Please fix the issues before proceeding.")
        sys.exit(1)