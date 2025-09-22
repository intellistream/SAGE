"""
兼容性层：处理开源代码与闭源包之间的兼容性问题
"""

import warnings
from typing import Optional, Any

class MissingModuleError(ImportError):
    """当闭源模块缺失时抛出的自定义错误"""
    pass

class CompatibilityLayer:
    """兼容性层，用于处理闭源依赖的缺失"""
    
    @staticmethod
    def import_with_fallback(module_name: str, class_name: str, fallback_class: Optional[Any] = None):
        """
        尝试导入闭源模块中的类，如果失败则使用回退方案
        
        Args:
            module_name: 模块名称
            class_name: 类名称
            fallback_class: 回退类（如果提供）
        
        Returns:
            导入的类或回退类
        
        Raises:
            MissingModuleError: 如果导入失败且没有回退方案
        """
        try:
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            if fallback_class is not None:
                warnings.warn(
                    f"闭源模块 {module_name}.{class_name} 不可用，使用开源替代实现。"
                    f"某些企业级功能可能不可用。原始错误: {e}",
                    UserWarning
                )
                return fallback_class
            else:
                raise MissingModuleError(
                    f"闭源模块 {module_name}.{class_name} 不可用，且没有开源替代实现。"
                    f"请检查闭源包是否正确安装，或者使用开源模式。原始错误: {e}"
                ) from e

    @staticmethod
    def check_closed_source_availability() -> dict:
        """
        检查闭源模块的可用性
        
        Returns:
            包含各个模块可用性状态的字典
        """
        status = {}
        
        # 检查各个闭源模块
        modules_to_check = [
            ('sage.kernel', 'JobManagerClient'),
            ('sage.common.utils.logging.custom_logger', 'CustomLogger'),
            ('sage.middleware', 'MiddlewareManager'),
        ]
        
        for module_name, class_name in modules_to_check:
            try:
                CompatibilityLayer.import_with_fallback(module_name, class_name)
                status[f"{module_name}.{class_name}"] = "available"
            except MissingModuleError:
                status[f"{module_name}.{class_name}"] = "missing"
        
        return status

# 便利函数
def safe_import_kernel_client():
    """安全导入 JobManagerClient"""
    from .fallbacks import MockJobManagerClient
    return CompatibilityLayer.import_with_fallback(
        'sage.kernel', 'JobManagerClient', MockJobManagerClient
    )

def safe_import_job_manager():
    """安全导入 JobManager"""
    from .fallbacks import MockJobManagerClient
    return CompatibilityLayer.import_with_fallback(
        'sage.kernel', 'JobManager', MockJobManagerClient
    )

def safe_import_task_context():
    """安全导入 TaskContext"""
    from .fallbacks import MockTaskContext
    return CompatibilityLayer.import_with_fallback(
        'sage.kernel', 'TaskContext', MockTaskContext
    )

def safe_import_service_context():
    """安全导入 ServiceContext"""
    from .fallbacks import MockServiceContext
    return CompatibilityLayer.import_with_fallback(
        'sage.kernel', 'ServiceContext', MockServiceContext
    )

def safe_import_custom_logger():
    """安全导入 CustomLogger"""
    from .fallbacks import MockCustomLogger
    return CompatibilityLayer.import_with_fallback(
        'sage.common.utils.logging.custom_logger', 'CustomLogger', MockCustomLogger
    )

def safe_import_openai_client():
    """安全导入 OpenAIClient"""
    from .fallbacks import MockOpenAIClient
    return CompatibilityLayer.import_with_fallback(
        'sage.lib.utils.OpenAIClient', 'OpenAIClient', MockOpenAIClient
    )

def safe_import_dill_functions():
    """安全导入 dill 序列化函数"""
    from .fallbacks import serialize_object, deserialize_object, trim_object_for_ray
    try:
        from sage.common.utils.serialization.dill import serialize_object as real_serialize, deserialize_object as real_deserialize, trim_object_for_ray as real_trim
        return real_serialize, real_deserialize, real_trim
    except ImportError:
        import warnings
        warnings.warn("使用 dill 序列化的模拟实现", UserWarning)
        return serialize_object, deserialize_object, trim_object_for_ray
