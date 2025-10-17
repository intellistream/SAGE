#!/usr/bin/env python3
"""
SAGE Studio v2.0 - 集成运行模式

这个脚本启动 SAGE Studio 的完整版本，集成所有 SAGE 操作符，
提供完整的 SAGE 生态系统功能。
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目路径
studio_root = Path(__file__).parent
sys.path.insert(0, str(studio_root / "src"))

# 尝试导入 SAGE 相关模块
SAGE_AVAILABLE = False
try:
    # 这里可以添加更多 SAGE 模块的导入检查
    import sage
    SAGE_AVAILABLE = True
    print("✅ SAGE Kernel detected")
except ImportError:
    print("⚠️  SAGE Kernel not found - some features will be limited")

from src.sage.studio.core.plugin_manager import initialize_plugin_system, get_plugin_status
from src.sage.studio.core.flow_engine import FlowEngine, create_simple_flow, execute_flow


class IntegratedStudioServer:
    """集成 Studio 服务器"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.flow_engine = FlowEngine()
        self.sage_available = SAGE_AVAILABLE
        
    async def initialize(self):
        """初始化系统"""
        print("🚀 SAGE Studio v2.0 - Integrated Mode")
        print("=" * 50)
        
        if self.sage_available:
            print("🔗 SAGE Kernel integration: ENABLED")
        else:
            print("⚠️  SAGE Kernel integration: DISABLED (running in limited mode)")
        
        # 初始化插件系统
        initialize_plugin_system()
        
        # 获取状态
        status = get_plugin_status()
        
        print(f"\n📊 System Status:")
        print(f"   • Total available nodes: {status['total_nodes']}")
        
        builtin_count = (status['nodes_by_category'].get('data_source', 0) + 
                        status['nodes_by_category'].get('processing', 0) + 
                        status['nodes_by_category'].get('output', 0))
        print(f"   • Built-in nodes: {builtin_count}")
        
        if status['plugins']['sage']['available']:
            sage_nodes = status['nodes_by_category'].get('sage', 0)
            print(f"   • SAGE operator nodes: {sage_nodes}")
            print("   • SAGE features: AVAILABLE ✅")
        else:
            print(f"   • SAGE operator nodes: 0 (SAGE not installed)")
            print("   • SAGE features: UNAVAILABLE ⚠️")
        
        print(f"\n✅ Integrated Studio initialized successfully!")
        
    async def run_interactive_mode(self):
        """运行交互模式"""
        print("\n" + "=" * 50)
        print("🎮 Interactive Mode - Create and Run Flows")
        print("=" * 50)
        
        while True:
            print("\nAvailable commands:")
            print("  1. List available nodes")
            print("  2. Create simple flow (builtin nodes)")
            if self.sage_available:
                print("  3. Create SAGE-enhanced flow")
                print("  4. Run SAGE integration demo")
            print("  5. Run flow")
            print("  6. View execution history")
            print("  0. Exit")
            
            try:
                choice = input(f"\nEnter your choice (0-{'6' if self.sage_available else '4'}): ").strip()
                
                if choice == "1":
                    await self._list_nodes()
                elif choice == "2":
                    await self._create_builtin_flow()
                elif choice == "3" and self.sage_available:
                    await self._create_sage_flow()
                elif choice == "4" and self.sage_available:
                    await self._run_sage_demo()
                elif choice == "5" or (choice == "3" and not self.sage_available):
                    await self._run_flow_demo()
                elif choice == "6" or (choice == "4" and not self.sage_available):
                    self._view_history()
                elif choice == "0":
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def _list_nodes(self):
        """列出可用节点"""
        from src.sage.studio.core.plugin_manager import get_available_nodes
        
        nodes = get_available_nodes()
        print(f"\n📝 Available Nodes ({len(nodes)}):")
        
        categories = {}
        for node in nodes:
            category = node.category.value if hasattr(node.category, 'value') else str(node.category)
            if category not in categories:
                categories[category] = []
            categories[category].append(node)
        
        for category, category_nodes in categories.items():
            icon = "🔗" if category == "sage" else "⚙️"
            availability = " (requires SAGE)" if category == "sage" and not self.sage_available else ""
            print(f"\n  {icon} {category.upper()}{availability}:")
            for node in category_nodes:
                status_icon = "✅" if category != "sage" or self.sage_available else "⚠️"
                print(f"     {status_icon} {node.name} ({node.id}) - {node.description}")
    
    async def _create_builtin_flow(self):
        """创建内置节点流程"""
        print("\n📋 Creating Built-in Flow...")
        print("This flow uses only built-in nodes, no SAGE dependency")
        
        flow = create_simple_flow("Built-in Demo Flow", [
            {
                "node_id": "json_parser",
                "name": "Parse Configuration",
                "inputs": {"json_string": '{"app": "SAGE Studio", "version": "2.0", "features": ["visual-editing", "plugin-system", "sage-integration"]}'}
            },
            {
                "node_id": "logger",
                "name": "Log Configuration",
                "inputs": {"level": "info", "message": "System configuration"}
            }
        ])
        
        print(f"✅ Created flow: {flow.name}")
        return flow
    
    async def _create_sage_flow(self):
        """创建 SAGE 集成流程"""
        if not self.sage_available:
            print("❌ SAGE is not available. Cannot create SAGE-enhanced flow.")
            return None
            
        print("\n🔗 Creating SAGE-Enhanced Flow...")
        print("This flow combines built-in nodes with SAGE operators")
        
        # 这里可以创建使用 SAGE 操作符的流程
        # 目前由于 SAGE 适配器是示例实现，我们创建一个演示版本
        flow = create_simple_flow("SAGE Integration Demo", [
            {
                "node_id": "sage_filesource", 
                "name": "SAGE File Source",
                "inputs": {"file_path": "/tmp/demo.txt"}
            },
            {
                "node_id": "json_parser",
                "name": "Parse Result",
                "inputs": {}
            },
            {
                "node_id": "logger",
                "name": "Log SAGE Result",
                "inputs": {"level": "info", "message": "SAGE processing result"}
            }
        ])
        
        print(f"✅ Created SAGE-enhanced flow: {flow.name}")
        return flow
    
    async def _run_sage_demo(self):
        """运行 SAGE 集成演示"""
        if not self.sage_available:
            print("❌ SAGE is not available.")
            return
            
        print("\n🔗 Running SAGE Integration Demo...")
        
        try:
            # 这里可以展示如何使用 SAGE 的实际功能
            print("🚀 Demonstrating SAGE Studio v2.0 integration capabilities:")
            print("   • SAGE operators available as nodes")
            print("   • Seamless data flow between SAGE and built-in nodes")
            print("   • Unified execution context")
            
            # 创建并运行 SAGE 流程
            flow = await self._create_sage_flow()
            if flow:
                execution = await execute_flow(flow)
                print(f"\n📊 SAGE Integration Results:")
                print(f"   • Status: {execution.status.value}")
                print(f"   • Duration: {execution.execution_time:.3f}s")
                
        except Exception as e:
            print(f"❌ SAGE demo error: {e}")
    
    async def _run_flow_demo(self):
        """运行演示流程"""
        print("\n🚀 Running Demo Flow...")
        
        # 创建演示流程
        flow = await self._create_builtin_flow()
        
        # 执行流程
        execution = await execute_flow(flow)
        
        print(f"\n📊 Execution Results:")
        print(f"   • Status: {execution.status.value}")
        print(f"   • Duration: {execution.execution_time:.3f}s")
        
        if execution.status.value == "completed":
            print("✅ Flow executed successfully!")
            
            print(f"\n📋 Node Execution Details:")
            for node in flow.nodes:
                status_icon = "✅" if node.status.value == "completed" else "❌"
                print(f"   {status_icon} {node.name}: {node.status.value} ({node.execution_time:.3f}s)")
                if node.error_message:
                    print(f"      Error: {node.error_message}")
        else:
            print(f"❌ Flow execution failed: {execution.error_message}")
    
    def _view_history(self):
        """查看执行历史"""
        history = self.flow_engine.get_execution_history(10)
        
        if not history:
            print("\n📝 No execution history yet.")
            return
        
        print(f"\n📚 Recent Executions ({len(history)}):")
        for i, execution in enumerate(reversed(history), 1):
            status_icon = "✅" if execution.status.value == "completed" else "❌"
            print(f"   {i}. {status_icon} {execution.flow_id} - {execution.status.value} ({execution.execution_time:.3f}s)")


async def run_integrated_api_server(host: str = "localhost", port: int = 8080):
    """运行集成 API 服务器（未来实现）"""
    print(f"🌐 Starting Integrated API server on http://{host}:{port}")
    print("🔗 SAGE integration: ENABLED" if SAGE_AVAILABLE else "⚠️  SAGE integration: LIMITED")
    print("⚠️  Web API not implemented yet. This will be added in Phase 2.")
    print("📝 For now, use interactive mode instead.")


async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SAGE Studio v2.0 - Integrated Mode")
    parser.add_argument("--mode", choices=["interactive", "server"], default="interactive",
                        help="Run mode: interactive CLI or web server")
    parser.add_argument("--host", default="localhost", help="Server host (for server mode)")
    parser.add_argument("--port", type=int, default=8080, help="Server port (for server mode)")
    
    args = parser.parse_args()
    
    # 创建服务器实例
    server = IntegratedStudioServer(args.host, args.port)
    await server.initialize()
    
    if args.mode == "interactive":
        await server.run_interactive_mode()
    elif args.mode == "server":
        await run_integrated_api_server(args.host, args.port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 SAGE Studio stopped.")
    except Exception as e:
        print(f"❌ Error starting SAGE Studio: {e}")
        sys.exit(1)