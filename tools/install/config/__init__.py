"""SAGE安装系统配置模块"""

from .defaults import *
from .profiles import InstallationProfile, get_profile, list_profiles, get_profile_info, get_profile_recommendations

__all__ = [
    "DEFAULT_PYTHON_VERSION",
    "DEFAULT_CONDA_CHANNELS", 
    "SAGE_PACKAGES",
    "OPTIONAL_PACKAGES",
    "InstallationProfile",
    "get_profile",
    "list_profiles",
    "get_profile_info", 
    "get_profile_recommendations"
]
