#!/bin/bash
# 为外迁模块生成接口层模板

set -e

if [ $# -lt 1 ]; then
    echo "用法: $0 <module_name>"
    echo "示例: $0 agentic"
    exit 1
fi

MODULE_NAME="$1"
SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INTERFACE_DIR="$SAGE_ROOT/packages/sage-libs/src/sage/libs/$MODULE_NAME/interface"

echo "🏗️  为 $MODULE_NAME 生成接口层模板"
echo "================================"
echo ""

# 创建目录
mkdir -p "$INTERFACE_DIR"

# 1. 创建 __init__.py
echo "📝 创建 interface/__init__.py..."
cat > "$INTERFACE_DIR/__init__.py" << 'EOF'
"""Interface definitions for {MODULE_NAME}.

This module defines the abstract interfaces and registry for {MODULE_NAME}.
Concrete implementations are provided by the external package 'isage-{MODULE_NAME}'.

Architecture:
- Interface layer (here): Abstract base classes, factory pattern
- Implementation layer (isage-{MODULE_NAME}): Concrete implementations

Usage:
    # In SAGE code, use the interface
    from sage.libs.{MODULE_NAME}.interface import create

    # In isage-{MODULE_NAME}, register implementations
    from sage.libs.{MODULE_NAME}.interface import register
    register("my_impl", MyImplementation)
"""

from .base import *  # noqa: F401, F403
from .factory import *  # noqa: F401, F403

__all__ = [
    # Base classes will be defined in base.py
    # Factory functions will be defined in factory.py
]
EOF

# 替换占位符
sed -i "s/{MODULE_NAME}/$MODULE_NAME/g" "$INTERFACE_DIR/__init__.py"

# 2. 创建 base.py
echo "📝 创建 interface/base.py..."
cat > "$INTERFACE_DIR/base.py" << 'EOF'
"""Base classes and interfaces for {MODULE_NAME}.

Define your abstract base classes here. These should be:
- Minimal: Only essential methods
- Stable: Changes affect all implementations
- Well-documented: Clear contracts

Example:
    from abc import ABC, abstractmethod

    class MyComponent(ABC):
        """Base class for {MODULE_NAME} components."""

        @abstractmethod
        def process(self, data: str) -> str:
            """Process input data.

            Args:
                data: Input data

            Returns:
                Processed result
            """
            pass
"""

from abc import ABC, abstractmethod

# TODO: Define your base classes here
# Example:
# class {MODULE_NAME_UPPER}Component(ABC):
#     @abstractmethod
#     def execute(self, **kwargs):
#         pass

EOF

# 替换占位符
MODULE_NAME_UPPER="$(echo $MODULE_NAME | tr '[:lower:]' '[:upper:]')"
sed -i "s/{MODULE_NAME}/$MODULE_NAME/g" "$INTERFACE_DIR/base.py"
sed -i "s/{MODULE_NAME_UPPER}/$MODULE_NAME_UPPER/g" "$INTERFACE_DIR/base.py"

# 3. 创建 factory.py
echo "📝 创建 interface/factory.py..."
cat > "$INTERFACE_DIR/factory.py" << 'EOF'
"""Factory and registry for {MODULE_NAME} implementations.

This module provides a registry pattern for {MODULE_NAME} implementations.
External packages (like isage-{MODULE_NAME}) can register their implementations here.

Example:
    # Register an implementation
    from sage.libs.{MODULE_NAME}.interface import register
    register("my_impl", MyImplementation)

    # Create an instance
    from sage.libs.{MODULE_NAME}.interface import create
    instance = create("my_impl", param1="value1")
"""

from typing import Any

# TODO: Import your base class
# from .base import {MODULE_NAME_UPPER}Component

_REGISTRY: dict[str, type] = {}


def register(name: str, cls: type) -> None:
    """Register a {MODULE_NAME} implementation.

    Args:
        name: Unique identifier for this implementation
        cls: Implementation class (should inherit from base class)

    Raises:
        ValueError: If name already registered
    """
    if name in _REGISTRY:
        raise ValueError(f"{MODULE_NAME} implementation '{name}' already registered")

    # TODO: Validate that cls inherits from your base class
    # if not issubclass(cls, {MODULE_NAME_UPPER}Component):
    #     raise TypeError(f"Class must inherit from {MODULE_NAME_UPPER}Component")

    _REGISTRY[name] = cls


def create(name: str, **kwargs: Any) -> Any:
    """Create an instance of a registered implementation.

    Args:
        name: Name of the registered implementation
        **kwargs: Arguments to pass to the constructor

    Returns:
        Instance of the implementation

    Raises:
        KeyError: If implementation not found
    """
    if name not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys()) if _REGISTRY else "none"
        raise KeyError(
            f"{MODULE_NAME} implementation '{name}' not found. "
            f"Available: {available}. "
            f"Did you install 'isage-{MODULE_NAME}'?"
        )

    cls = _REGISTRY[name]
    return cls(**kwargs)


def registered() -> list[str]:
    """Get list of registered implementation names.

    Returns:
        List of registered names
    """
    return list(_REGISTRY.keys())


def unregister(name: str) -> None:
    """Unregister an implementation (for testing).

    Args:
        name: Name of the implementation to unregister
    """
    _REGISTRY.pop(name, None)


__all__ = [
    "register",
    "create",
    "registered",
    "unregister",
]
EOF

# 替换占位符
sed -i "s/{MODULE_NAME}/$MODULE_NAME/g" "$INTERFACE_DIR/factory.py"
sed -i "s/{MODULE_NAME_UPPER}/$MODULE_NAME_UPPER/g" "$INTERFACE_DIR/factory.py"

# 4. 更新父级 __init__.py
PARENT_INIT="$SAGE_ROOT/packages/sage-libs/src/sage/libs/$MODULE_NAME/__init__.py"
if [ ! -f "$PARENT_INIT" ]; then
    echo "📝 创建 $MODULE_NAME/__init__.py..."
    cat > "$PARENT_INIT" << 'EOF'
"""{MODULE_NAME} compatibility layer.

⚠️ DEPRECATION NOTICE:
{MODULE_NAME} implementations have been externalized to isage-{MODULE_NAME}.

Installation:
    pip install isage-{MODULE_NAME}

Usage:
    # Use the interface layer
    from sage.libs.{MODULE_NAME}.interface import create, register

    # Or import from external package
    from isage_{MODULE_NAME} import *

Repository: https://github.com/intellistream/sage-{MODULE_NAME}
PyPI: https://pypi.org/project/isage-{MODULE_NAME}/
"""

import warnings

# Re-export interface
from .interface import *  # noqa: F401, F403

warnings.warn(
    "sage.libs.{MODULE_NAME} implementations have been externalized. "
    "Install 'isage-{MODULE_NAME}' for concrete implementations: "
    "pip install isage-{MODULE_NAME}",
    DeprecationWarning,
    stacklevel=2,
)

EOF
    sed -i "s/{MODULE_NAME}/$MODULE_NAME/g" "$PARENT_INIT"
fi

echo ""
echo "✅ 完成！接口层模板已创建："
echo "  📁 $INTERFACE_DIR/"
echo "     ├── __init__.py"
echo "     ├── base.py         (TODO: 定义抽象基类)"
echo "     └── factory.py      (注册和工厂函数)"
echo ""
echo "📝 下一步："
echo "  1. 编辑 base.py - 定义你的抽象基类"
echo "  2. 编辑 factory.py - 如果需要自定义注册逻辑"
echo "  3. 在 isage-$MODULE_NAME 中实现具体类并注册"
echo ""
echo "📖 参考示例："
echo "  packages/sage-libs/src/sage/libs/anns/interface/"
