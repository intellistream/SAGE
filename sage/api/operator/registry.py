# sage/api/operator/registry.py

from typing import Any, Dict, Type

from sage.api.operator.base import Operator
from sage.api.operator.map_operator import MapOperator
from sage.api.operator.sink_operator import SinkOperator

# 内置 Operator 注册表，key 为算子名称，value 为对应的 Operator 类
OPERATOR_REGISTRY: Dict[str, Type[Operator]] = {
    "map": MapOperator,
    "sink": SinkOperator,
}


def register_operator(name: str):
    """
    Decorator to register a custom Operator under a given name.
    Usage:
        @register_operator("my_op")
        class MyOperator(Operator):
            ...
    """
    def decorator(cls: Type[Operator]) -> Type[Operator]:
        OPERATOR_REGISTRY[name] = cls
        return cls
    return decorator


def get_operator(name: str, function: Any, config: Dict) -> Operator:
    """
    根据注册名构造并返回一个 Operator 实例。
    :param name: 在 OPERATOR_REGISTRY 中注册的算子名称
    :param function: 已 open() 的 Function 实例，将被此 Operator 包装
    :param config: 通用配置（如果 Operator.setup 需要，可在此使用）
    :return: 完成 setup() 的 Operator 实例
    :raises KeyError: 如果指定名称未在注册表中找到
    """
    if name not in OPERATOR_REGISTRY:
        raise KeyError(f"No operator registered under name '{name}'")

    OperatorClass = OPERATOR_REGISTRY[name]
    op: Operator = OperatorClass(function)
    op.setup()
    return op
