from typing import Type, Any, Tuple, TYPE_CHECKING
from sage.kernel.runtime.context.context_injection import create_service_with_context

if TYPE_CHECKING:
    from sage.kernel import ServiceContext


class ServiceFactory:
    """服务工厂类，用于创建原始服务实例，类似FunctionFactory"""
    
    def __init__(
        self,
        service_name: str,
        service_class: Type,
        service_args: Tuple[Any, ...] = (),
        service_kwargs: dict = None,
    ):
        """
        初始化服务工厂
        
        Args:
            service_name: 服务名称
            service_class: 服务类
            service_args: 服务构造参数
            service_kwargs: 服务构造关键字参数
        """
        if not service_name:
            raise ValueError("service_name cannot be empty")
        if not service_class:
            raise ValueError("service_class cannot be None")
            
        self.service_name = service_name or service_class.__name__
        self.service_class = service_class
        print(f"ServiceFactory initialized for {self.service_name} with class {self.service_class}")
        self.service_args = service_args
        self.service_kwargs = service_kwargs or {}
    
    def create_service(self, ctx: 'ServiceContext' = None) -> Any:
        """
        创建服务实例
        
        Args:
            ctx: 服务运行时上下文
            
        Returns:
            创建的服务实例
        """
        # 检查 service_class 是否可用
        if self.service_class is None:
            raise ValueError(f"ServiceFactory for '{self.service_name}': service_class is None. "
                           "This may be due to serialization issues in distributed environments.")
        
        # 使用通用的上下文注入工具函数
        service = create_service_with_context(
            self.service_class,
            ctx,
            *self.service_args,
            **self.service_kwargs
        )
        
        return service
    
    def __repr__(self) -> str:
        service_name = getattr(self, 'service_name', 'Unknown')
        service_class = getattr(self, 'service_class', None)
        if service_class is not None:
            service_class_name = service_class.__name__
        else:
            service_class_name = 'Unknown'
        return f"<ServiceFactory {service_name}: {service_class_name}>"
    
    def __getstate__(self):
        """为 pickle/Ray 序列化准备状态"""
        return {
            'service_name': getattr(self, 'service_name', None),
            'service_class': getattr(self, 'service_class', None),
            'service_args': getattr(self, 'service_args', ()),
            'service_kwargs': getattr(self, 'service_kwargs', {})
        }
    
    def __setstate__(self, state):
        """从 pickle/Ray 反序列化恢复状态"""
        self.service_name = state.get('service_name')
        self.service_class = state.get('service_class')
        self.service_args = state.get('service_args', ())
        self.service_kwargs = state.get('service_kwargs', {})
        
        # 验证必需的属性
        if self.service_name is None:
            self.service_name = "Unknown"
        if self.service_class is None:
            import logging
            logging.warning("ServiceFactory: service_class is None after deserialization")
