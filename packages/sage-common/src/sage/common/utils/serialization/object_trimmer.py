"""
对象清理器 - 用于远程调用的对象预处理（cloudpickle / dill 兼容）

不依赖 Ray，适用于任何分布式运行时（Flownet、gRPC、TCP 等）。
"""

from typing import Any

from .config import (
    ATTRIBUTE_BLACKLIST,
    OPERATOR_EXCLUDE_ATTRS,
    SKIP_VALUE,
    TRANSFORMATION_EXCLUDE_ATTRS,
)
from .exceptions import SerializationError
from .preprocessor import filter_attrs, gather_attrs, preprocess_for_dill, should_skip


def trim_object_for_remote(
    obj: Any, include: list[str] | None = None, exclude: list[str] | None = None
) -> Any:
    """
    为远程调用预处理对象，移除不可序列化的内容。

    只做清理工作，不进行实际序列化，让调用方自己选择序列化方式（cloudpickle / dill）。
    适用于在 Flownet / gRPC / TCP 远程调用前清理对象，避免序列化错误。

    Args:
        obj: 要预处理的对象
        include: 包含的属性列表（如果指定，只保留这些属性）
        exclude: 排除的属性列表（这些属性将被移除）

    Returns:
        清理后的对象，可以安全地用于远程传输序列化

    Example:
        cleaned_env = trim_object_for_remote(env, exclude=['logger', 'runtime_context'])
        serialized = cloudpickle.dumps(cleaned_env)
    """
    try:
        # 如果指定了 include 或 exclude，直接使用用户的过滤规则
        if include or exclude:
            attrs = gather_attrs(obj)
            filtered_attrs = filter_attrs(attrs, include, exclude)

            obj_class = type(obj)
            try:
                final_obj = obj_class.__new__(obj_class)  # type: ignore[call-overload]
                for attr_name, attr_value in filtered_attrs.items():
                    try:
                        setattr(final_obj, attr_name, attr_value)
                    except Exception:
                        pass  # 忽略设置失败的属性
                return final_obj
            except Exception:
                pass  # 无法创建新实例，回退到预处理

        # 无特殊 include/exclude 需求，使用标准预处理
        cleaned_obj = preprocess_for_dill(obj)
        return cleaned_obj if cleaned_obj is not SKIP_VALUE else None

    except Exception as e:
        raise SerializationError(f"Object trimming for remote call failed: {e}")


class ObjectTrimmer:
    """用于远程调用的对象预处理器（运行时无关）"""

    @staticmethod
    def trim_for_remote_call(
        obj: Any,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        deep_clean: bool = True,
    ) -> Any:
        """
        为远程调用准备对象。

        Args:
            obj: 要清理的对象
            include: 只保留这些属性
            exclude: 排除这些属性
            deep_clean: 是否进行深度清理（递归处理嵌套对象）

        Returns:
            清理后可以安全传输的对象
        """
        if not deep_clean:
            # 浅层清理：只处理顶层对象属性
            if hasattr(obj, "__dict__"):
                attrs = gather_attrs(obj)
                filtered_attrs = filter_attrs(attrs, include, exclude)

                obj_class = type(obj)
                try:
                    cleaned_obj = obj_class.__new__(obj_class)  # type: ignore[call-overload]
                    for attr_name, attr_value in filtered_attrs.items():
                        if not should_skip(attr_value):
                            try:
                                setattr(cleaned_obj, attr_name, attr_value)
                            except Exception:
                                pass
                    return cleaned_obj
                except Exception:
                    return obj
            return obj
        else:
            # 深度清理：使用完整预处理流程，并递归处理嵌套对象
            cleaned = trim_object_for_remote(obj, include, exclude)

            if cleaned and hasattr(cleaned, "__dict__"):
                for attr_name, attr_value in list(cleaned.__dict__.items()):
                    if hasattr(attr_value, "__dict__"):
                        nested_cleaned = ObjectTrimmer.trim_for_remote_call(
                            attr_value,
                            include=None,
                            exclude=list(ATTRIBUTE_BLACKLIST),
                            deep_clean=True,
                        )
                        setattr(cleaned, attr_name, nested_cleaned)

            return cleaned

    @staticmethod
    def trim_transformation(transformation_obj: Any) -> Any:
        """
        专门为 Transformation 对象定制的清理方法，移除常见不可序列化属性。
        """
        return ObjectTrimmer.trim_for_remote_call(
            transformation_obj, exclude=TRANSFORMATION_EXCLUDE_ATTRS
        )

    @staticmethod
    def trim_operator(operator_obj: Any) -> Any:
        """
        专门为 Operator 对象定制的清理方法。
        """
        return ObjectTrimmer.trim_for_remote_call(operator_obj, exclude=OPERATOR_EXCLUDE_ATTRS)

    @staticmethod
    def validate_serializable(obj: Any, max_depth: int = 3) -> dict[str, Any]:
        """
        验证对象是否可以被 cloudpickle 序列化。

        Args:
            obj: 要验证的对象
            max_depth: 最大检查深度（当前未使用，保留扩展）

        Returns:
            验证结果字典：is_serializable, issues, size_estimate
        """
        import cloudpickle  # type: ignore[import-untyped]

        result: dict[str, Any] = {"is_serializable": False, "issues": [], "size_estimate": 0}

        try:
            serialized = cloudpickle.dumps(obj)
            result["is_serializable"] = True
            result["size_estimate"] = len(serialized)
        except Exception as e:
            result["issues"].append(f"Serialization failed: {str(e)}")
            if hasattr(obj, "__dict__"):
                for attr_name, attr_value in obj.__dict__.items():
                    if should_skip(attr_value):
                        result["issues"].append(
                            f"Problematic attribute: {attr_name} = {type(attr_value)}"
                        )

        return result
