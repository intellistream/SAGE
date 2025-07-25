import ray
import time
from typing import Type, Any, TYPE_CHECKING
from sage.runtime.service.base_service import BaseService
from sage.utils.actor_wrapper import ActorWrapper

if TYPE_CHECKING:
    from ray.actor import ActorHandle

if TYPE_CHECKING:
    from ray.actor import ActorHandle


@ray.remote
class RayService(BaseService):
    """Ray远程服务实现，作为Ray Actor运行，提供分布式服务能力"""
    
    def __init__(self, service_name: str, service_class: Type, service_args: tuple = (), service_kwargs: dict = None, ctx=None):
        """
        初始化Ray服务Actor - 参考task_factory的做法
        
        Args:
            service_name: 服务名称
            service_class: 服务类
            service_args: 服务构造参数
            service_kwargs: 服务构造关键字参数
            ctx: 运行时上下文
        """
        # 在Ray Actor内部创建实际的服务实例
        service_kwargs = service_kwargs or {}
        service_instance = service_class(*service_args, **service_kwargs)
        
        # 如果服务有ctx属性，设置运行时上下文
        if hasattr(service_instance, 'ctx') and ctx is not None:
            service_instance.ctx = ctx
        
        # 初始化基类
        super().__init__(service_name, service_instance)
        self.logger.debug(f"Ray service actor '{service_name}' initialized with {service_class.__name__}")

    def call_method(self, method_name: str, *args, **kwargs) -> Any:
        """
        调用服务方法
        
        Args:
            method_name: 方法名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            方法调用结果
        """
        try:
            self._request_count += 1
            self._last_activity_time = time.time()
            
            if not hasattr(self.service_instance, method_name):
                raise AttributeError(f"Service {self.service_name} does not have method '{method_name}'")
            
            method = getattr(self.service_instance, method_name)
            result = method(*args, **kwargs)
            
            self.logger.debug(f"Called method {method_name} on service {self.service_name}")
            return result
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error calling method {method_name} on service {self.service_name}: {e}")
            raise

    def get_attribute(self, attr_name: str) -> Any:
        """
        获取服务属性
        
        Args:
            attr_name: 属性名称
            
        Returns:
            属性值
        """
        try:
            if not hasattr(self.service_instance, attr_name):
                raise AttributeError(f"Service {self.service_name} does not have attribute '{attr_name}'")
            
            return getattr(self.service_instance, attr_name)
            
        except Exception as e:
            self.logger.error(f"Error getting attribute {attr_name} from service {self.service_name}: {e}")
            raise

    def set_attribute(self, attr_name: str, value: Any):
        """
        设置服务属性
        
        Args:
            attr_name: 属性名称
            value: 属性值
        """
        try:
            setattr(self.service_instance, attr_name, value)
            self.logger.debug(f"Set attribute {attr_name} on service {self.service_name}")
            
        except Exception as e:
            self.logger.error(f"Error setting attribute {attr_name} on service {self.service_name}: {e}")
            raise

    def get_statistics(self) -> dict:
        """获取服务统计信息"""
        base_stats = super().get_statistics()
        base_stats.update({
            "service_type": "RayService",
            "actor_id": f"ray_actor_{self.service_name}"  # 简化的actor标识
        })
        return base_stats

    def cleanup(self):
        """清理服务资源"""
        self.logger.info(f"Cleaning up Ray service actor {self.service_name}")
        
        try:
            # 调用基类清理
            super().cleanup()
            
            self.logger.debug(f"Ray service actor {self.service_name} cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup of Ray service actor {self.service_name}: {e}")

    def _needs_background_worker(self) -> bool:
        """Ray服务Actor可以支持后台工作线程"""
        return hasattr(self.service_instance, '_background_process') or \
               hasattr(self.service_instance, 'background_worker')

    def __repr__(self) -> str:
        return f"<RayService Actor {self.service_name}: {type(self.service_instance).__name__}>"
