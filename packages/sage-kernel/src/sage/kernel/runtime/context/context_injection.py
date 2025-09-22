"""
Context Injection Utilities

提供通用的上下文注入工具函数，用于在对象构造时注入运行时上下文。
主要解决在构造函数中无法使用上下文提供的服务（如logger）的问题。
"""

from typing import Type, Any, Tuple, Dict, Optional, TypeVar, Union
import logging

# 定义类型变量
T = TypeVar('T')
ContextType = TypeVar('ContextType')


def create_with_context(
    target_class: Type[T],
    context: Optional[ContextType],
    context_attr_name: str = 'ctx',
    *args,
    **kwargs
) -> T:
    """
    使用上下文注入方式创建对象实例
    
    使用 __new__ + __init__ 分离的方式，在调用 __init__ 之前注入上下文，
    这样构造函数就能使用上下文提供的服务（如logger）。
    
    Args:
        target_class: 要创建的目标类
        context: 要注入的上下文对象
        context_attr_name: 上下文属性名称，默认为 'ctx'
        *args: 传递给构造函数的位置参数
        **kwargs: 传递给构造函数的关键字参数
        
    Returns:
        创建的实例，上下文已注入
        
    Example:
        # 创建服务实例并注入 ServiceContext
        service = create_with_context(
            MyService, 
            service_context, 
            'ctx',
            config_param="value"
        )
        
        # 创建任务实例并注入 TaskContext
        task = create_with_context(
            MyTask,
            task_context,
            'ctx', 
            input_data=data
        )
    """
    if context is not None:
        # 方案1: 使用 __new__ + __init__ 分离的方式
        # 先调用 __new__ 创建实例，但不调用 __init__
        instance = target_class.__new__(target_class)
        
        # 在调用 __init__ 之前注入上下文
        if hasattr(instance, '__dict__'):
            setattr(instance, context_attr_name, context)
        else:
            # 对于某些特殊类型（如某些内置类型或使用 __slots__ 的类），使用 setattr
            try:
                setattr(instance, context_attr_name, context)
            except (AttributeError, TypeError) as e:
                logging.warning(f"Failed to inject context into {target_class.__name__}: {e}")
                # 如果无法注入上下文，回退到普通构造方式
                instance = target_class(*args, **kwargs)
                # 尝试在构造后注入上下文
                try:
                    setattr(instance, context_attr_name, context)
                except (AttributeError, TypeError):
                    logging.warning(f"Failed to inject context after construction for {target_class.__name__}")
                return instance
        
        # 现在调用 __init__，此时上下文已经可用
        instance.__init__(*args, **kwargs)
    else:
        # 没有上下文时，使用正常的构造方式
        instance = target_class(*args, **kwargs)
    
    return instance


def create_service_with_context(
    service_class: Type[T],
    service_context: Optional['ServiceContext'],
    *args,
    **kwargs
) -> T:
    """
    使用 ServiceContext 创建服务实例的便捷方法
    
    Args:
        service_class: 服务类
        service_context: 服务上下文
        *args: 传递给构造函数的位置参数
        **kwargs: 传递给构造函数的关键字参数
        
    Returns:
        创建的服务实例
    """
    return create_with_context(service_class, service_context, 'ctx', *args, **kwargs)


def create_task_with_context(
    task_class: Type[T],
    task_context: Optional['TaskContext'],
    *args,
    **kwargs
) -> T:
    """
    使用 TaskContext 创建任务实例的便捷方法
    
    Args:
        task_class: 任务类
        task_context: 任务上下文
        *args: 传递给构造函数的位置参数
        **kwargs: 传递给构造函数的关键字参数
        
    Returns:
        创建的任务实例
    """
    return create_with_context(task_class, task_context, 'ctx', *args, **kwargs)


# 为了类型检查，导入相关类型
if __name__ != '__main__':
    try:
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from sage.kernel.runtime.context.service_context import ServiceContext
            from sage.kernel.runtime.context.task_context import TaskContext
    except ImportError:
        pass
