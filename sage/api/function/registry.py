# sage/api/function/registry.py

from typing import Type
from sage.api.function.base import Function

_FUNCTIONS: dict[str, Type[Function]] = {}

def register_function(name: str):
    def deco(cls: Type[Function]):
        _FUNCTIONS[name] = cls
        return cls
    return deco

def get_function(name: str, config: dict) -> Function:
    if name not in _FUNCTIONS:
        raise KeyError(f"No function registered under '{name}'")
    fn = _FUNCTIONS[name](config)
    fn.open()
    return fn
