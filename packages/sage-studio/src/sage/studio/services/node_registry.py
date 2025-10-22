"""
Node Registry - Maps Studio UI node types to SAGE Operators
"""

from typing import Dict, Optional, Type

from sage.kernel.operators import MapOperator


class NodeRegistry:
    """Node Registry - Mapping from Studio UI node types to SAGE Operator classes"""
    
    def __init__(self):
        """Initialize Registry and register all available node types"""
        self._registry: Dict[str, Type[MapOperator]] = {}
        self._register_default_operators()
    
    def _register_default_operators(self):
        """Register default Operator mappings"""
        
        # RAG Operators
        try:
            from sage.middleware.operators.rag import RefinerOperator
            self._registry["refiner"] = RefinerOperator
        except ImportError:
            pass
        
        # Generic map operator
        self._registry["map"] = MapOperator
    
    def register(self, node_type: str, operator_class: Type[MapOperator]):
        """Register a new node type"""
        self._registry[node_type] = operator_class
    
    def get_operator(self, node_type: str) -> Optional[Type[MapOperator]]:
        """Get the Operator class for a node type"""
        return self._registry.get(node_type)
    
    def list_types(self) -> list[str]:
        """List all registered node types"""
        return sorted(self._registry.keys())


# Singleton instance
_default_registry = None


def get_node_registry() -> NodeRegistry:
    """Get the default NodeRegistry instance (singleton pattern)"""
    global _default_registry
    if _default_registry is None:
        _default_registry = NodeRegistry()
    return _default_registry
