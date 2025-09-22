"""
SAGE sage-kernel Enterprise Edition
企业版功能需要有效的商业许可证
"""

import os
import sys
from pathlib import Path

# 添加license工具到路径
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent.parent
_LICENSE_TOOLS = _PROJECT_ROOT / "tools" / "license"

if _LICENSE_TOOLS.exists():
    sys.path.insert(0, str(_LICENSE_TOOLS))
    sys.path.insert(0, str(_LICENSE_TOOLS / "shared"))


def _check_enterprise_license():
    """检查企业版license"""
    try:
        from shared.validation import LicenseValidator
        
        validator = LicenseValidator()
        if not validator.has_valid_license():
            return False
            
        features = validator.get_license_features()
        # 检查是否有企业版功能
        required_features = ["enterprise", "high-performance", "enterprise-db", "advanced-analytics"]
        return any(feature in features for feature in required_features)
        
    except ImportError:
        # License工具不可用，检查环境变量
        return os.getenv("SAGE_ENTERPRISE_ENABLED", "").lower() in ["true", "1", "yes"]
    except Exception:
        return False


# 企业版功能可用性检查
_ENTERPRISE_AVAILABLE = _check_enterprise_license()

if not _ENTERPRISE_AVAILABLE:
    import warnings
    warnings.warn(
        f"SAGE sage-kernel Enterprise features require a valid commercial license. "
        "Enterprise functionality will be disabled. "
        "Please contact your SAGE vendor for licensing information.",
        UserWarning,
        stacklevel=2
    )


def require_enterprise_license(func):
    """装饰器：要求企业版license"""
    def wrapper(*args, **kwargs):
        if not _ENTERPRISE_AVAILABLE:
            raise RuntimeError(
                f"SAGE sage-kernel Enterprise feature requires a valid commercial license. "
                f"This functionality is not available with your current license."
            )
        return func(*args, **kwargs)
    return wrapper


# 根据license状态导入功能
if _ENTERPRISE_AVAILABLE:
    # 导入所有企业版功能
    try:
        # 这里会根据实际的企业版模块来调整
        pass
    except ImportError as e:
        print(f"Warning: Failed to import some enterprise features: {e}")
else:
    # 企业版功能不可用时的占位符
    pass


__all__ = [
    "_ENTERPRISE_AVAILABLE",
    "require_enterprise_license"
]
