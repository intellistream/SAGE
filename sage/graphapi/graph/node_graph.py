from typing import Type, TYPE_CHECKING, Union, Any

class NodeGraph:
    def __init__(self, name: str, config: dict = None):
        """
        Initialize the NodeGraph with a name and optional configuration.
        Args:
            name (str): The name of the node graph.
            config (dict, optional): Configuration parameters for the node graph.
        """
        self.name:str = name
        self.config:dict = config or {}
        self.nodes:OpNode = []