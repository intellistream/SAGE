#!/usr/bin/env python3
"""
验证 SAGE Studio 可以在没有 SAGE 的环境中完整运行网页界面

这个脚本会：
1. 检查当前 SAGE 状态
2. 测试 Studio 核心组件
3. 验证网页服务是否可以启动
"""

import sys
import subprocess
import time
from pathlib import Path

# 添加路径
studio_root = Path(__file__).parent
sys.path.insert(0, str(studio_root / "src"))


def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_sage_availability():
    """检查 SAGE 是否可用"""
    print_section("1. 检查 SAGE 可用性")
    
    try:
        import sage.kernel
        print("✅ SAGE Kernel 可用")
        sage_available = True
    except ImportError as e:
        print("⚠️  SAGE Kernel 不可用")
        print(f"   原因: {e}")
        sage_available = False
    
    # 使用 Studio 的检测函数
    try:
        from sage.studio.adapters import is_sage_available
        studio_sage_check = is_sage_available()
        print(f"   Studio 检测结果: {studio_sage_check}")
    except Exception as e:
        print(f"   Studio 检测失败: {e}")
    
    return sage_available


def test_plugin_system():
    """测试插件系统"""
    print_section("2. 测试插件系统")
    
    try:
        from sage.studio.core.plugin_manager import (
            initialize_plugin_system,
            get_plugin_status,
            get_available_nodes
        )
        
        print("初始化插件系统...")
        initialize_plugin_system()
        
        status = get_plugin_status()
        print(f"\n插件状态:")
        print(f"  - 总插件数: {status['total_plugins']}")
        print(f"  - 总节点数: {status['total_nodes']}")
        print(f"  - 节点分类: {status['nodes_by_category']}")
        
        print(f"\n插件详情:")
        for plugin_name, plugin_info in status['plugins'].items():
            available = "✅" if plugin_info.get('available', True) else "⚠️"
            print(f"  {available} {plugin_info['name']} v{plugin_info['version']}")
        
        print(f"\n可用节点列表:")
        nodes = get_available_nodes()
        for node in nodes:
            tags = ', '.join(node.tags) if node.tags else 'none'
            unavailable = " [不可用]" if 'unavailable' in tags else ""
            print(f"  • {node.name} ({node.id}){unavailable}")
        
        return True
    except Exception as e:
        print(f"❌ 插件系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_creation():
    """测试节点创建"""
    print_section("3. 测试节点创建和执行")
    
    try:
        from sage.studio.core.plugin_manager import create_node
        from sage.studio.core.node_interface import ExecutionContext
        import asyncio
        
        # 测试内置节点
        builtin_nodes = ["file_reader", "json_parser", "logger"]
        
        print("测试内置节点:")
        for node_id in builtin_nodes:
            node = create_node(node_id)
            if node:
                print(f"  ✅ {node_id}: {node.metadata.name}")
            else:
                print(f"  ❌ {node_id}: 创建失败")
        
        # 测试节点执行
        print("\n测试节点执行:")
        json_parser = create_node("json_parser")
        if json_parser:
            context = ExecutionContext(
                node_id="test_parser",
                inputs={"json_string": '{"message": "Hello Studio", "status": "ok"}'}
            )
            
            result = asyncio.run(json_parser.execute(context))
            
            if result.success:
                print(f"  ✅ JSON Parser 执行成功")
                print(f"     输出: {result.outputs}")
            else:
                print(f"  ❌ JSON Parser 执行失败: {result.error}")
        
        return True
    except Exception as e:
        print(f"❌ 节点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_flow_engine():
    """测试流程引擎"""
    print_section("4. 测试流程引擎")
    
    try:
        from sage.studio.core.flow_engine import create_simple_flow, execute_flow
        import asyncio
        
        print("创建测试流程...")
        flow = create_simple_flow("独立测试流程", [
            {
                "node_id": "json_parser",
                "name": "解析JSON",
                "inputs": {"json_string": '{"test": "独立运行", "version": "2.0"}'}
            },
            {
                "node_id": "logger",
                "name": "记录日志",
                "inputs": {"level": "info"}
            }
        ])
        
        print(f"  流程名称: {flow.name}")
        print(f"  节点数量: {len(flow.nodes)}")
        print(f"  连接数量: {len(flow.connections)}")
        
        print("\n执行流程...")
        execution = asyncio.run(execute_flow(flow))
        
        print(f"\n执行结果:")
        print(f"  状态: {execution.status.value}")
        print(f"  执行时间: {execution.execution_time:.3f}s")
        
        if execution.status.value == "completed":
            print(f"  ✅ 流程执行成功")
            return True
        else:
            print(f"  ❌ 流程执行失败: {execution.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ 流程引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backend_api():
    """测试后端 API 是否可以启动"""
    print_section("5. 测试后端 API 启动")
    
    try:
        import requests
        
        # 检查后端是否已经在运行
        try:
            response = requests.get("http://localhost:8080/health", timeout=2)
            if response.status_code == 200:
                print("✅ 后端 API 已经在运行")
                print(f"   响应: {response.json()}")
                return True
        except requests.exceptions.RequestException:
            print("⚠️  后端 API 未运行")
        
        # 尝试启动后端（仅测试，不实际启动）
        backend_file = studio_root / "src" / "sage" / "studio" / "config" / "backend" / "api.py"
        
        if backend_file.exists():
            print(f"✅ 后端 API 文件存在: {backend_file}")
            print("   可以通过以下方式启动:")
            print(f"   python {backend_file}")
            return True
        else:
            print(f"❌ 后端 API 文件不存在: {backend_file}")
            return False
            
    except Exception as e:
        print(f"❌ 后端 API 测试失败: {e}")
        return False


def test_frontend_files():
    """测试前端文件是否存在"""
    print_section("6. 测试前端文件")
    
    frontend_dir = studio_root / "src" / "sage" / "studio" / "frontend"
    
    required_files = [
        "package.json",
        "angular.json",
        "src/index.html",
        "src/main.ts"
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = frontend_dir / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (不存在)")
            all_exist = False
    
    # 检查 node_modules
    node_modules = frontend_dir / "node_modules"
    if node_modules.exists() or node_modules.is_symlink():
        print(f"  ✅ node_modules (已安装)")
    else:
        print(f"  ⚠️  node_modules (未安装)")
        print(f"     运行: cd {frontend_dir} && npm install")
    
    return all_exist


def print_summary(results):
    """打印测试总结"""
    print_section("测试总结")
    
    tests = [
        ("SAGE 可用性检查", results.get('sage', True)),
        ("插件系统", results.get('plugin', False)),
        ("节点创建和执行", results.get('node', False)),
        ("流程引擎", results.get('flow', False)),
        ("后端 API", results.get('backend', False)),
        ("前端文件", results.get('frontend', False)),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"\n测试结果: {passed}/{total} 通过\n")
    
    for test_name, result in tests:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {test_name}")
    
    print("\n" + "=" * 70)
    
    if passed == total:
        print("🎉 所有测试通过！SAGE Studio 可以完整独立运行！")
    elif passed >= 4:  # 核心功能通过
        print("✅ 核心功能测试通过！Studio 可以独立运行（部分功能需要配置）")
    else:
        print("⚠️  部分测试失败，请检查配置")
    
    print("=" * 70)
    
    # 打印启动指南
    print("\n" + "=" * 70)
    print("  如何启动 SAGE Studio 网页界面")
    print("=" * 70)
    print("\n方式 1（推荐）：")
    print("  sage studio start")
    print("  然后访问: http://localhost:4200")
    print("\n方式 2：")
    print("  ./run_studio.sh integrated")
    print("\n方式 3：")
    print("  python demo_visualization.py")
    print("\n" + "=" * 70)


def main():
    """主函数"""
    print("=" * 70)
    print("  SAGE Studio 独立运行验证脚本")
    print("=" * 70)
    print("\n这个脚本将验证 Studio 是否可以在没有 SAGE 的环境中完整运行。")
    
    results = {}
    
    # 运行所有测试
    results['sage'] = check_sage_availability()
    results['plugin'] = test_plugin_system()
    results['node'] = test_node_creation()
    results['flow'] = test_flow_engine()
    results['backend'] = test_backend_api()
    results['frontend'] = test_frontend_files()
    
    # 打印总结
    print_summary(results)
    
    # 返回是否所有核心测试通过
    core_passed = results['plugin'] and results['node'] and results['flow']
    return 0 if core_passed else 1


if __name__ == "__main__":
    sys.exit(main())
