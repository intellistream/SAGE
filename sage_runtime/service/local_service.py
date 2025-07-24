from sage_runtime.service.base_service import BaseService
from typing import Any


class LocalService(BaseService):
    """本地服务实现，直接在当前进程中运行"""
    
    def __init__(self, service_name: str, service_instance: Any):
        """
        初始化本地服务
        
        Args:
            service_name: 服务名称
            service_instance: 实际的服务实例
        """
        super().__init__(service_name, service_instance)
        self.logger.debug(f"Local service '{service_name}' initialized")

    def call_method(self, method_name: str, *args, **kwargs) -> Any:
        """
        直接调用本地服务方法
        
        Args:
            method_name: 方法名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            方法调用结果
        """
        return super().call_method(method_name, *args, **kwargs)

    def get_attribute(self, attr_name: str) -> Any:
        """
        直接获取本地服务属性
        
        Args:
            attr_name: 属性名称
            
        Returns:
            属性值
        """
        return super().get_attribute(attr_name)

    def set_attribute(self, attr_name: str, value: Any):
        """
        直接设置本地服务属性
        
        Args:
            attr_name: 属性名称
            value: 属性值
        """
        super().set_attribute(attr_name, value)

    def __repr__(self) -> str:
        return f"<LocalService {self.service_name}: {type(self.service_instance).__name__}>"
