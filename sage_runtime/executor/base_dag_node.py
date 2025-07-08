from abc import ABC, abstractmethod
from sage_runtime.io.connection import Connection
from sage_utils.custom_logger import CustomLogger



class BaseDagNode(ABC):
    def __init__(self, name, transformation, session_folder=None):
        # Create logger first
        self.logger = CustomLogger(
            filename=f"{name}",
            session_folder=session_folder,
            console_output="WARNING",
            file_output="WARNING",
            global_output = "WARNING",
            name = f"{name}_{self.__class__.__name__}"
        )
        pass
    
    def add_connection(self, connection: Connection):
        """
        添加连接到DAG节点
        :param connection: Connection对象，包含连接信息
        """
        if not hasattr(self, 'connections'):
            self.connections = []
        self.connections.append(connection)
        