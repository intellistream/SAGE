from typing import Type, TYPE_CHECKING, Union, Any

class OpNode:
    def __init__(self):
        self.name: str
        self.inputs: list[str] = []
        self.outputs: list[str] = []
        self.operator: Any
        pass