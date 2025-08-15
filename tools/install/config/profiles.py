"""
SAGE安装配置文件管理
提供不同安装场景的预定义配置
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .defaults import INSTALL_MODES, DEFAULT_PYTHON_VERSION, SAGE_PACKAGES


@dataclass
class InstallationProfile:
    """安装配置文件数据类"""
    name: str
    description: str
    python_version: str
    packages: List[str]
    conda_packages: List[str]
    install_submodules: bool
    environment_suffix: str = ""
    additional_config: Dict[str, Any] = None
    local_packages = SAGE_PACKAGES
    def __post_init__(self):
        if self.additional_config is None:
            self.additional_config = {}


# 预定义的安装配置文件
INSTALLATION_PROFILES = {
    "quick": InstallationProfile(
        name="快速安装",
        description="仅安装核心SAGE包，适合快速体验和测试",
        python_version=DEFAULT_PYTHON_VERSION,
        packages=[],  # 使用requirements文件
        conda_packages=[],
        
        install_submodules=False,
        environment_suffix="quick",
        additional_config={
            "use_requirements": "requirements.txt",  # 快速安装使用精简的requirements
            "skip_optional_deps": True,
            "minimal_validation": True
        }
    ),
    
    "standard": InstallationProfile(
        name="标准安装",
        description="推荐的标准安装，包含SAGE核心包和常用科学计算库",
        python_version=DEFAULT_PYTHON_VERSION,
        packages=[],  # 使用requirements文件
        conda_packages=[],  # 基础包由conda环境创建时安装
        install_submodules=True,
        environment_suffix="standard",
        additional_config={
            "use_requirements": "requirements-dev.txt",  # 标准安装也使用开发环境，保证功能完整
            "install_jupyter_extensions": True,
            "setup_ipython_profile": True
        }
    ),
    
    "development": InstallationProfile(
        name="开发环境",
        description="完整的开发环境，包含所有依赖、开发工具和测试框架",
        python_version=DEFAULT_PYTHON_VERSION,
        packages=[],  # 使用requirements文件
        conda_packages=[],  # 基础包由conda环境创建时安装
        install_submodules=True,
        environment_suffix="dev",
        additional_config={
            "use_requirements": "requirements-dev.txt",
            "install_dev_tools": True,
            "setup_pre_commit": True,
            "install_jupyter_extensions": True,
            "setup_ipython_profile": True,
            "build_docs": True
        }
    ),
    
    "minimal": InstallationProfile(
        name="最小安装",
        description="只安装必需的核心包",
        python_version=DEFAULT_PYTHON_VERSION,
        packages=[],  # 使用requirements文件，不从PyPI安装
        conda_packages=[],
        install_submodules=False,
        environment_suffix="minimal",
        additional_config={
            "use_requirements": "requirements.txt",
            "skip_optional_deps": True,
            "minimal_validation": True,
            "skip_jupyter": True
        }
    ),
    
    "research": InstallationProfile(
        name="科研环境",
        description="面向科研工作的安装配置，包含数据科学和机器学习工具",
        python_version=DEFAULT_PYTHON_VERSION,
        packages=[
            "numpy>=1.21.0",
            "pandas>=1.3.0",
            "matplotlib>=3.4.0",
            "scipy>=1.7.0", 
            "scikit-learn>=1.0.0",
            "seaborn>=0.11.0",
            "plotly>=5.0.0",
            "jupyter>=1.0.0",
            "jupyterlab>=3.0.0",
            "notebook>=6.4.0",
            "ipykernel>=6.0.0",
            "ipywidgets>=7.6.0",
            "statsmodels>=0.12.0",
            "networkx>=2.6.0"
        ],
        conda_packages=[
            "numpy", "pandas", "matplotlib", "scipy", "scikit-learn",
            "seaborn", "jupyter", "jupyterlab", "statsmodels", "networkx"
        ],
        
        install_submodules=True,
        environment_suffix="research",
        additional_config={
            "install_jupyter_extensions": True,
            "setup_jupyterlab": True,
            "install_research_tools": True
        }
    ),
    
    "production": InstallationProfile(
        name="生产环境",
        description="生产环境安装，优化性能和稳定性",
        python_version=DEFAULT_PYTHON_VERSION,
        packages=[],  # 使用requirements文件
        conda_packages=[],
        install_submodules=True,
        environment_suffix="prod",
        additional_config={
            "use_requirements": "requirements.txt",  # 生产环境使用精简的requirements
            "optimize_for_production": True,
            "skip_dev_tools": True,
            "skip_jupyter": True,
            "enable_logging": True
        }
    )
}


def get_profile(profile_name: str) -> Optional[InstallationProfile]:
    """
    获取安装配置文件
    
    Args:
        profile_name: 配置文件名称
        
    Returns:
        安装配置文件对象，如果不存在则返回None
    """
    return INSTALLATION_PROFILES.get(profile_name.lower())


def list_profiles() -> List[str]:
    """
    列出所有可用的安装配置文件
    
    Returns:
        配置文件名称列表
    """
    return list(INSTALLATION_PROFILES.keys())


def get_profile_info(profile_name: str) -> Dict[str, Any]:
    """
    获取配置文件详细信息
    
    Args:
        profile_name: 配置文件名称
        
    Returns:
        配置文件信息字典
    """
    profile = get_profile(profile_name)
    if not profile:
        return {}
    
    return {
        "name": profile.name,
        "description": profile.description,
        "python_version": profile.python_version,
        "package_count": len(profile.packages),
        "conda_package_count": len(profile.conda_packages),
        "install_submodules": profile.install_submodules,
        "environment_suffix": profile.environment_suffix,
        "additional_features": list(profile.additional_config.keys())
    }


def create_custom_profile(name: str,
                         description: str,
                         packages: List[str],
                         **kwargs) -> InstallationProfile:
    """
    创建自定义安装配置文件
    
    Args:
        name: 配置文件名称
        description: 描述信息
        packages: 包列表
        **kwargs: 其他配置参数
        
    Returns:
        自定义安装配置文件
    """
    return InstallationProfile(
        name=name,
        description=description,
        python_version=kwargs.get("python_version", DEFAULT_PYTHON_VERSION),
        packages=packages,
        conda_packages=kwargs.get("conda_packages", []),
        install_submodules=kwargs.get("install_submodules", True),
        environment_suffix=kwargs.get("environment_suffix", "custom"),
        additional_config=kwargs.get("additional_config", {})
    )


def get_profile_recommendations(use_case: str) -> List[str]:
    """
    根据使用场景推荐合适的配置文件
    
    Args:
        use_case: 使用场景 ("learning", "research", "development", "production")
        
    Returns:
        推荐的配置文件名称列表
    """
    recommendations = {
        "learning": ["quick", "standard"],
        "research": ["research", "standard"],
        "development": ["development", "standard"],
        "production": ["production", "minimal"],
        "testing": ["quick", "minimal"],
        "demo": ["quick", "standard"]
    }
    
    return recommendations.get(use_case.lower(), ["standard"])


def validate_profile(profile: InstallationProfile) -> Dict[str, Any]:
    """
    验证安装配置文件的有效性
    
    Args:
        profile: 安装配置文件
        
    Returns:
        验证结果字典
    """
    validation_result = {
        "valid": True,
        "warnings": [],
        "errors": []
    }
    
    # 检查Python版本格式
    try:
        version_parts = profile.python_version.split('.')
        if len(version_parts) < 2:
            validation_result["errors"].append("Python版本格式无效")
            validation_result["valid"] = False
    except Exception:
        validation_result["errors"].append("Python版本格式无效")
        validation_result["valid"] = False
    
    # 检查包列表
    if not profile.packages:
        validation_result["warnings"].append("包列表为空")
    
    # 检查SAGE核心包是否包含
    core_packages = ["sage", "sage-common"]
    missing_core = [pkg for pkg in core_packages if pkg not in profile.packages]
    if missing_core:
        validation_result["warnings"].append(f"缺少核心包: {', '.join(missing_core)}")
    
    # 检查包版本格式
    for package in profile.packages:
        if not any(op in package for op in ["==", ">=", "<=", ">", "<"]):
            # 没有版本约束，这是一个警告
            validation_result["warnings"].append(f"包 {package} 没有版本约束")
    
    return validation_result
