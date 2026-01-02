"""
API Docs Tool - API 文档查询工具

Layer: L6 (sage-studio)

This tool provides dynamic API documentation lookup for SAGE framework,
allowing users to query docstrings, function signatures, and class information.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from sage.studio.tools.base import BaseTool

logger = logging.getLogger(__name__)


class APIDocsInput(BaseModel):
    """API 文档查询工具的输入参数

    Attributes:
        symbol: 要查询的符号，支持模块、类、函数、方法
    """

    symbol: str = Field(
        ...,
        description=(
            "要查询的 Python 符号路径，如 'sage.llm.UnifiedInferenceClient' "
            "或 'sage.studio.tools.BaseTool'"
        ),
        min_length=1,
        max_length=500,
    )
    include_source: bool = Field(
        default=False,
        description="是否包含源代码（仅对函数和方法有效）",
    )


class APIDocsTool(BaseTool):
    """API 文档查询工具

    动态查询 SAGE 框架的 API 文档，包括：
    - 模块、类、函数、方法的 docstring
    - 函数/方法签名和参数说明
    - 类的继承关系和属性

    Example:
        >>> tool = APIDocsTool()
        >>> result = await tool.run(symbol="sage.studio.tools.BaseTool")
        >>> print(result["result"]["docstring"])
    """

    name: ClassVar[str] = "api_docs_lookup"
    description: ClassVar[str] = (
        "查询 SAGE 框架的 API 文档，获取类、函数、方法的文档字符串、参数说明和签名信息。"
        "当需要了解某个 SAGE API 的使用方法、参数含义时使用此工具。"
    )
    args_schema: ClassVar[type[BaseModel]] = APIDocsInput

    # SAGE 相关的模块前缀白名单
    ALLOWED_PREFIXES: ClassVar[tuple[str, ...]] = (
        "sage.",
        "examples.",
    )

    async def _run(
        self,
        symbol: str,
        include_source: bool = False,
    ) -> dict[str, Any]:
        """执行 API 文档查询

        Args:
            symbol: Python 符号路径
            include_source: 是否包含源代码

        Returns:
            包含文档信息的字典

        Raises:
            ValueError: 符号不在允许的前缀范围内
            ImportError: 无法导入模块
            AttributeError: 无法找到指定的属性
        """
        # 安全检查：只允许查询 SAGE 相关的符号
        if not any(symbol.startswith(prefix) for prefix in self.ALLOWED_PREFIXES):
            raise ValueError(
                f"Only SAGE-related symbols are allowed. "
                f"Symbol must start with one of: {self.ALLOWED_PREFIXES}"
            )

        logger.debug(f"Looking up API docs for: {symbol}")

        # 解析符号路径
        obj, obj_type = self._resolve_symbol(symbol)

        # 根据对象类型获取文档
        if obj_type == "module":
            return self._get_module_docs(obj, symbol)
        elif obj_type == "class":
            return self._get_class_docs(obj, symbol)
        elif obj_type in ("function", "method"):
            return self._get_function_docs(obj, symbol, include_source)
        else:
            return self._get_generic_docs(obj, symbol, obj_type)

    def _resolve_symbol(self, symbol: str) -> tuple[Any, str]:
        """解析符号路径，返回对象和类型

        Args:
            symbol: 符号路径，如 'sage.common.config.ports.SagePorts'

        Returns:
            (对象, 类型字符串)

        Raises:
            ImportError: 无法导入模块
            AttributeError: 无法找到属性
        """
        parts = symbol.split(".")

        # 尝试逐级导入，找到模块边界
        module = None
        attr_parts: list[str] = []

        for i in range(len(parts), 0, -1):
            try_path = ".".join(parts[:i])
            try:
                module = importlib.import_module(try_path)
                attr_parts = parts[i:]
                break
            except ImportError:
                continue

        if module is None:
            raise ImportError(f"Cannot import any module from path: {symbol}")

        # 如果没有属性部分，返回模块
        if not attr_parts:
            return module, "module"

        # 逐级获取属性
        obj = module
        for attr_name in attr_parts:
            if not hasattr(obj, attr_name):
                raise AttributeError(
                    f"'{type(obj).__name__}' has no attribute '{attr_name}' (full path: {symbol})"
                )
            obj = getattr(obj, attr_name)

        # 确定对象类型
        if inspect.ismodule(obj):
            obj_type = "module"
        elif inspect.isclass(obj):
            obj_type = "class"
        elif inspect.isfunction(obj):
            obj_type = "function"
        elif inspect.ismethod(obj):
            obj_type = "method"
        elif callable(obj):
            obj_type = "callable"
        else:
            obj_type = "attribute"

        return obj, obj_type

    def _get_module_docs(self, module: Any, symbol: str) -> dict[str, Any]:
        """获取模块文档"""
        docstring = inspect.getdoc(module) or "No documentation available."

        # 获取模块中的公开成员
        members = []
        for name, obj in inspect.getmembers(module):
            if name.startswith("_"):
                continue
            member_type = self._get_member_type(obj)
            members.append({"name": name, "type": member_type})

        return {
            "symbol": symbol,
            "type": "module",
            "docstring": docstring,
            "members": members[:50],  # 限制数量
            "file": getattr(module, "__file__", None),
        }

    def _get_class_docs(self, cls: type, symbol: str) -> dict[str, Any]:
        """获取类文档"""
        docstring = inspect.getdoc(cls) or "No documentation available."

        # 获取类签名（__init__ 参数）
        try:
            sig = inspect.signature(cls)
            signature = f"{cls.__name__}{sig}"
        except (ValueError, TypeError):
            signature = f"{cls.__name__}(...)"

        # 获取基类
        bases = [base.__name__ for base in cls.__bases__ if base is not object]

        # 获取方法和属性
        methods = []
        class_attrs = []

        for name, obj in inspect.getmembers(cls):
            if name.startswith("_") and not name.startswith("__"):
                continue  # 跳过私有成员，保留魔术方法

            if inspect.isfunction(obj) or inspect.ismethod(obj):
                # 获取方法签名
                try:
                    method_sig = str(inspect.signature(obj))
                except (ValueError, TypeError):
                    method_sig = "(...)"

                method_doc = inspect.getdoc(obj)
                methods.append(
                    {
                        "name": name,
                        "signature": method_sig,
                        "docstring": (method_doc[:200] + "...")
                        if method_doc and len(method_doc) > 200
                        else method_doc,
                    }
                )
            elif not callable(obj) and not name.startswith("__"):
                class_attrs.append({"name": name, "type": type(obj).__name__})

        return {
            "symbol": symbol,
            "type": "class",
            "signature": signature,
            "docstring": docstring,
            "bases": bases,
            "methods": methods[:30],  # 限制数量
            "attributes": class_attrs[:20],
            "file": self._get_source_file(cls),
        }

    def _get_function_docs(self, func: Any, symbol: str, include_source: bool) -> dict[str, Any]:
        """获取函数/方法文档"""
        docstring = inspect.getdoc(func) or "No documentation available."

        # 获取签名
        try:
            sig = inspect.signature(func)
            signature = f"{func.__name__}{sig}"

            # 解析参数
            parameters = []
            for param_name, param in sig.parameters.items():
                param_info: dict[str, Any] = {
                    "name": param_name,
                    "kind": str(param.kind).split(".")[-1],
                }
                if param.annotation != inspect.Parameter.empty:
                    param_info["type"] = self._format_annotation(param.annotation)
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = repr(param.default)
                parameters.append(param_info)

            # 返回类型
            return_annotation = None
            if sig.return_annotation != inspect.Signature.empty:
                return_annotation = self._format_annotation(sig.return_annotation)

        except (ValueError, TypeError):
            signature = f"{func.__name__}(...)"
            parameters = []
            return_annotation = None

        result: dict[str, Any] = {
            "symbol": symbol,
            "type": "function",
            "signature": signature,
            "docstring": docstring,
            "parameters": parameters,
            "return_type": return_annotation,
            "file": self._get_source_file(func),
        }

        # 可选：包含源代码
        if include_source:
            try:
                source = inspect.getsource(func)
                # 限制源代码长度
                if len(source) > 2000:
                    source = source[:2000] + "\n# ... (truncated)"
                result["source"] = source
            except (OSError, TypeError):
                result["source"] = None

        return result

    def _get_generic_docs(self, obj: Any, symbol: str, obj_type: str) -> dict[str, Any]:
        """获取通用对象文档"""
        docstring = inspect.getdoc(obj) or "No documentation available."

        return {
            "symbol": symbol,
            "type": obj_type,
            "value_type": type(obj).__name__,
            "docstring": docstring,
            "repr": repr(obj)[:500],  # 限制长度
        }

    def _get_member_type(self, obj: Any) -> str:
        """获取成员类型字符串"""
        if inspect.ismodule(obj):
            return "module"
        elif inspect.isclass(obj):
            return "class"
        elif inspect.isfunction(obj):
            return "function"
        elif callable(obj):
            return "callable"
        else:
            return type(obj).__name__

    def _get_source_file(self, obj: Any) -> str | None:
        """获取对象的源文件路径"""
        try:
            return inspect.getfile(obj)
        except (TypeError, OSError):
            return None

    def _format_annotation(self, annotation: Any) -> str:
        """格式化类型注解"""
        if hasattr(annotation, "__name__"):
            return annotation.__name__
        return str(annotation)
