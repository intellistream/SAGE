#!/usr/bin/env python3
"""
SAGE Studio v2.0 - 独立运行模式

这个脚本启动 SAGE Studio 的独立版本，只依赖内置节点，
不需要完整的 SAGE 系统。适合轻量级使用场景。
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目路径
studio_root = Path(__file__).parent
sys.path.insert(0, str(studio_root / "src"))

from src.sage.studio.core.plugin_manager import initialize_plugin_system, get_plugin_status
from src.sage.studio.core.flow_engine import FlowEngine, create_simple_flow, execute_flow


class StandaloneStudioServer:
    """独立 Studio 服务器"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.flow_engine = FlowEngine()
        
    async def initialize(self):
        """初始化系统"""
        print("🚀 SAGE Studio v2.0 - Standalone Mode")
        print("=" * 50)
        
        # 初始化插件系统
        initialize_plugin_system()
        
        # 获取状态
        status = get_plugin_status()
        
        print(f"\n📊 System Status:")
        print(f"   • Available nodes: {status['total_nodes']}")
        print(f"   • Built-in nodes: {status['nodes_by_category'].get('data_source', 0) + status['nodes_by_category'].get('processing', 0) + status['nodes_by_category'].get('output', 0)}")
        
        if status['plugins']['sage']['available']:
            sage_nodes = status['nodes_by_category'].get('sage', 0)
            print(f"   • SAGE nodes: {sage_nodes} (optional)")
        else:
            print(f"   • SAGE nodes: Not available (running in standalone mode)")
        
        print(f"\n✅ Standalone Studio initialized successfully!")
        
    async def run_interactive_mode(self):
        """运行交互模式"""
        print("\n" + "=" * 50)
        print("🎮 Interactive Mode - Create and Run Flows")
        print("=" * 50)
        
        while True:
            print("\nAvailable commands:")
            print("  1. List available nodes")
            print("  2. Create simple flow")
            print("  3. Run flow")
            print("  4. View execution history")
            print("  5. Exit")
            
            try:
                choice = input("\nEnter your choice (1-5): ").strip()
                
                if choice == "1":
                    await self._list_nodes()
                elif choice == "2":
                    await self._create_flow()
                elif choice == "3":
                    await self._run_flow_demo()
                elif choice == "4":
                    self._view_history()
                elif choice == "5":
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice. Please enter 1-5.")
                    
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
            print(f"\n  📁 {category.upper()}:")
            for node in category_nodes:
                print(f"     • {node.name} ({node.id}) - {node.description}")
    
    async def _create_flow(self):
        """创建简单流程"""
        print("\n📋 Creating a Simple Flow...")
        print("This will create a demo flow: JSON Parser -> Text Splitter -> Logger")
        
        flow = create_simple_flow("Demo Flow", [
            {
                "node_id": "json_parser",
                "name": "Parse JSON Data",
                "inputs": {"json_string": '{"message": "Hello from Standalone SAGE Studio!", "items": ["apple", "banana", "cherry"]}'}
            },
            {
                "node_id": "logger",
                "name": "Log Parsed Data",
                "inputs": {"level": "info", "message": "Parsed result"}
            }
        ])
        
        print(f"✅ Created flow: {flow.name}")
        print(f"   • Nodes: {len(flow.nodes)}")
        print(f"   • Connections: {len(flow.connections)}")
        
        return flow
    
    async def _run_flow_demo(self):
        """运行演示流程"""
        print("\n🚀 Running Demo Flow...")
        
        # 创建演示流程
        flow = await self._create_flow()
        
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


async def run_api_server(host: str = "localhost", port: int = 8080):
    """运行 API 服务器（未来实现）"""
    print(f"🌐 Starting API server on http://{host}:{port}")
    print("⚠️  Web API not implemented yet. This will be added in Phase 2.")
    print("📝 For now, use interactive mode instead.")


async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SAGE Studio v2.0 - Standalone Mode")
    parser.add_argument("--mode", choices=["interactive", "server"], default="interactive",
                        help="Run mode: interactive CLI or web server")
    parser.add_argument("--host", default="localhost", help="Server host (for server mode)")
    parser.add_argument("--port", type=int, default=8080, help="Server port (for server mode)")
    
    args = parser.parse_args()
    
    # 创建服务器实例
    server = StandaloneStudioServer(args.host, args.port)
    await server.initialize()
    
    if args.mode == "interactive":
        await server.run_interactive_mode()
    elif args.mode == "server":
        await run_api_server(args.host, args.port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 SAGE Studio stopped.")
    except Exception as e:
        print(f"❌ Error starting SAGE Studio: {e}")
        sys.exit(1)