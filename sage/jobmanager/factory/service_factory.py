from typing import Type, Any, Tuple, TYPE_CHECKING
from sage.jobmanager.utils.name_server import get_name

if TYPE_CHECKING:
    from sage.runtime.runtime_context import RuntimeContext


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
        self.service_name = get_name(service_name)
        self.service_class = service_class
        self.service_args = service_args
        self.service_kwargs = service_kwargs or {}
    
    def create_service(self, ctx: 'RuntimeContext' = None) -> Any:
        """
        创建服务实例
        
        Args:
            ctx: 运行时上下文
            
        Returns:
            创建的服务实例
        """
        # 创建服务实例
        service = self.service_class(
            *self.service_args, 
            **self.service_kwargs
        )
        
        # 如果服务有ctx属性，设置运行时上下文
        if hasattr(service, 'ctx') and ctx is not None:
            service.ctx = ctx
        
        return service
    
    def __repr__(self) -> str:
        return f"<ServiceFactory {self.service_name}: {self.service_class.__name__}>"
