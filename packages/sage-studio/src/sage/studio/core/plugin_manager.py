"""
插件管理器

负责加载、注册和管理节点插件
这是实现解耦的核心组件
"""

import importlib
import inspect
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.node_interface import NodeInterface, NodeMetadata, node_factory


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.loaded_plugins: Dict[str, Dict[str, Any]] = {}
        self._initialize_builtin_plugins()
    
    def _initialize_builtin_plugins(self):
        """初始化内置插件"""
        try:
            # 加载内置节点
            from ..nodes import builtin
            self.loaded_plugins["builtin"] = {
                "name": "Built-in Nodes",
                "version": "1.0.0",
                "description": "Core built-in nodes",
                "type": "builtin",
                "module": builtin
            }
            print("✅ Loaded built-in nodes plugin")
        except Exception as e:
            print(f"❌ Failed to load built-in nodes: {e}")
        
        try:
            # 尝试加载 SAGE 适配器
            from ..adapters import is_sage_available
            if is_sage_available():
                from ..adapters import FileSourceAdapter, SimpleRetrieverAdapter
                self.loaded_plugins["sage"] = {
                    "name": "SAGE Integration",
                    "version": "1.0.0", 
                    "description": "SAGE operator adapters",
                    "type": "sage",
                    "available": True
                }
                print("✅ Loaded SAGE integration plugin")
            else:
                self.loaded_plugins["sage"] = {
                    "name": "SAGE Integration",
                    "version": "1.0.0",
                    "description": "SAGE operator adapters (SAGE not available)",
                    "type": "sage",
                    "available": False
                }
                print("⚠️ SAGE integration plugin loaded but SAGE not available")
        except Exception as e:
            print(f"❌ Failed to load SAGE integration: {e}")
    
    def register_plugin_module(self, module_name: str, plugin_info: Optional[Dict[str, Any]] = None) -> bool:
        """注册插件模块
        
        Args:
            module_name: 模块名或路径
            plugin_info: 插件信息（可选）
            
        Returns:
            bool: 是否注册成功
        """
        try:
            # 动态导入模块
            if module_name.startswith('.'):
                # 相对导入
                module = importlib.import_module(module_name, package='sage.studio')
            else:
                # 绝对导入
                module = importlib.import_module(module_name)
            
            # 查找模块中的 NodeInterface 子类
            node_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, NodeInterface) and 
                    obj != NodeInterface):
                    node_classes.append(obj)
            
            # 注册找到的节点类
            for node_class in node_classes:
                node_factory.register_node_class(node_class)
            
            # 记录插件信息
            if plugin_info is None:
                plugin_info = {
                    "name": module_name,
                    "version": "1.0.0",
                    "description": f"Plugin from module {module_name}",
                    "type": "external"
                }
            
            plugin_info["module"] = module
            plugin_info["node_count"] = len(node_classes)
            self.loaded_plugins[module_name] = plugin_info
            
            print(f"✅ Registered plugin: {plugin_info['name']} ({len(node_classes)} nodes)")
            return True
            
        except Exception as e:
            print(f"❌ Failed to register plugin {module_name}: {e}")
            return False
    
    def register_plugin_directory(self, plugin_dir: Path) -> bool:
        """从目录注册插件
        
        Args:
            plugin_dir: 插件目录路径
            
        Returns:
            bool: 是否注册成功
        """
        try:
            # 查找插件配置文件
            plugin_config_file = plugin_dir / "plugin.yaml"
            if not plugin_config_file.exists():
                plugin_config_file = plugin_dir / "plugin.json"
            
            if plugin_config_file.exists():
                # 读取插件配置
                if plugin_config_file.suffix == ".yaml":
                    import yaml
                    with open(plugin_config_file, 'r') as f:
                        plugin_config = yaml.safe_load(f)
                else:
                    with open(plugin_config_file, 'r') as f:
                        plugin_config = json.load(f)
                
                # 注册插件模块
                for node_info in plugin_config.get("nodes", []):
                    module_path = node_info["module"]
                    self.register_plugin_module(module_path, plugin_config)
                
                return True
            else:
                # 没有配置文件，尝试直接导入目录中的 Python 文件
                for py_file in plugin_dir.glob("*.py"):
                    if py_file.name == "__init__.py":
                        continue
                    
                    module_name = f"{plugin_dir.name}.{py_file.stem}"
                    self.register_plugin_module(module_name)
                
                return True
                
        except Exception as e:
            print(f"❌ Failed to register plugin directory {plugin_dir}: {e}")
            return False
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有已加载的插件"""
        return list(self.loaded_plugins.values())
    
    def list_nodes(self) -> List[NodeMetadata]:
        """列出所有可用节点"""
        return node_factory.list_available_nodes()
    
    def get_node_by_id(self, node_id: str) -> Optional[NodeInterface]:
        """根据 ID 获取节点实例"""
        try:
            return node_factory.create_node(node_id)
        except ValueError:
            return None
    
    def get_nodes_by_category(self, category: str) -> List[NodeMetadata]:
        """根据分类获取节点"""
        all_nodes = self.list_nodes()
        return [node for node in all_nodes if node.category == category]
    
    def search_nodes(self, query: str) -> List[NodeMetadata]:
        """搜索节点"""
        query = query.lower()
        all_nodes = self.list_nodes()
        
        matching_nodes = []
        for node in all_nodes:
            if (query in node.name.lower() or 
                query in node.description.lower() or
                any(tag.lower().find(query) >= 0 for tag in node.tags)):
                matching_nodes.append(node)
        
        return matching_nodes
    
    def get_plugin_status(self) -> Dict[str, Any]:
        """获取插件系统状态"""
        node_count_by_category = {}
        all_nodes = self.list_nodes()
        
        for node in all_nodes:
            category = node.category
            node_count_by_category[category] = node_count_by_category.get(category, 0) + 1
        
        return {
            "total_plugins": len(self.loaded_plugins),
            "total_nodes": len(all_nodes),
            "nodes_by_category": node_count_by_category,
            "plugins": {name: {
                "name": plugin["name"],
                "version": plugin["version"],
                "type": plugin["type"], 
                "available": plugin.get("available", True),
                "node_count": plugin.get("node_count", 0)
            } for name, plugin in self.loaded_plugins.items()}
        }


# 全局插件管理器实例
plugin_manager = PluginManager()


# 便捷函数

def get_available_nodes() -> List[NodeMetadata]:
    """获取所有可用节点"""
    return plugin_manager.list_nodes()


def create_node(node_id: str) -> Optional[NodeInterface]:
    """创建节点实例"""
    return plugin_manager.get_node_by_id(node_id)


def search_nodes(query: str) -> List[NodeMetadata]:
    """搜索节点"""
    return plugin_manager.search_nodes(query)


def get_plugin_status() -> Dict[str, Any]:
    """获取插件状态"""
    return plugin_manager.get_plugin_status()


# 初始化插件系统
def initialize_plugin_system():
    """初始化插件系统"""
    print("🚀 Initializing SAGE Studio Plugin System...")
    
    status = get_plugin_status()
    print(f"📦 Loaded {status['total_plugins']} plugins")
    print(f"⚙️  Available {status['total_nodes']} nodes")
    
    for category, count in status['nodes_by_category'].items():
        print(f"   • {category}: {count} nodes")
    
    # 显示插件状态
    for plugin_name, plugin_info in status['plugins'].items():
        if plugin_info['available']:
            print(f"✅ {plugin_info['name']} v{plugin_info['version']} ({plugin_info['node_count']} nodes)")
        else:
            print(f"⚠️  {plugin_info['name']} v{plugin_info['version']} (unavailable)")
    
    print("🎉 Plugin system initialized successfully!")


if __name__ == "__main__":
    # 测试插件系统
    initialize_plugin_system()
    
    # 列出所有节点
    print("\n📝 Available Nodes:")
    for node in get_available_nodes():
        print(f"   • {node.name} ({node.id}) - {node.category}")
    
    # 测试创建节点
    print("\n🧪 Testing node creation:")
    file_reader = create_node("file_reader")
    if file_reader:
        print(f"✅ Created {file_reader.metadata.name}")
    else:
        print("❌ Failed to create file_reader node")