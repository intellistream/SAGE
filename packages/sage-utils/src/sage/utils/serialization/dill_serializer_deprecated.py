"""
⚠️ 此模块已被废弃！

原来的 dill_serializer.py 已经被重构为多个专门的模块以提高可维护性：

新的模块结构：
- sage.utils.serialization.exceptions         # 异常定义
- sage.utils.serialization.config            # 配置和常量
- sage.utils.serialization.preprocessor      # 对象预处理器
- sage.utils.serialization.universal_serializer  # 通用序列化器
- sage.utils.serialization.ray_trimmer       # Ray对象清理器

向后兼容性：
所有原有的导入和函数调用都继续有效，但建议迁移到新的模块结构。

示例：
    # 旧方式（仍然有效）
    from sage.utils.serialization.dill_serializer import serialize_object
    
    # 新方式（推荐）
    from sage.utils.serialization import serialize_object

更多信息请查看：
- REFACTOR_GUIDE.md: 详细的重构说明
- demo_serialization_usage.py: 使用示例
- test_serialization_refactor.py: 测试脚本

请逐步迁移到新的模块结构！
"""

# 为了向后兼容，重新导入所有原有的函数和类
import warnings

# 发出废弃警告
warnings.warn(
    "dill_serializer.py 已被废弃，请使用新的模块结构。"
    "参见 REFACTOR_GUIDE.md 获取详细信息。",
    DeprecationWarning,
    stacklevel=2
)

# 重新导入所有公共接口以保持向后兼容
try:
    from .exceptions import SerializationError
    from .universal_serializer import UniversalSerializer
    from .ray_trimmer import RayObjectTrimmer, trim_object_for_ray
    from .config import BLACKLIST as _BLACKLIST
    from .config import ATTRIBUTE_BLACKLIST as _ATTRIBUTE_BLACKLIST
    from .config import SKIP_VALUE as _SKIP_VALUE
    from .preprocessor import (
        gather_attrs as _gather_attrs,
        filter_attrs as _filter_attrs,
        should_skip as _should_skip,
        preprocess_for_dill as _preprocess_for_dill,
        postprocess_from_dill as _postprocess_from_dill
    )
    
    # 便捷函数
    def serialize_object(obj, include=None, exclude=None):
        """序列化对象的便捷函数"""
        return UniversalSerializer.serialize_object(obj, include, exclude)

    def deserialize_object(data):
        """反序列化对象的便捷函数"""
        return UniversalSerializer.deserialize_object(data)

    def save_object_state(obj, path, include=None, exclude=None):
        """保存对象状态的便捷函数"""
        return UniversalSerializer.save_object_state(obj, path, include, exclude)

    def load_object_from_file(path):
        """从文件加载对象的便捷函数"""
        return UniversalSerializer.load_object_from_file(path)

    def load_object_state(obj, path):
        """加载对象状态的便捷函数"""
        return UniversalSerializer.load_object_state(obj, path)

    # 向后兼容的函数
    def pack_object(obj, include=None, exclude=None):
        """打包对象的便捷函数（向后兼容）"""
        return serialize_object(obj, include, exclude)

    def unpack_object(data):
        """解包对象的便捷函数（向后兼容）"""
        return deserialize_object(data)

except ImportError as e:
    # 如果新模块导入失败，回退到原始实现
    warnings.warn(f"无法导入新模块，回退到原始实现: {e}", ImportWarning)
    
    # 这里应该包含原始的实现，但由于已经重构，
    # 我们建议修复导入问题而不是维护重复代码
    raise ImportError(
        "新的序列化模块导入失败，请检查模块安装。"
        "如果问题持续，请查看 REFACTOR_GUIDE.md"
    ) from e
