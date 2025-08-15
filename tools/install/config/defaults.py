"""
SAGE安装系统默认配置
"""

# Python版本配置
DEFAULT_PYTHON_VERSION = "3.11"
MIN_PYTHON_VERSION = "3.8"
MAX_PYTHON_VERSION = "3.12"

# Conda配置
DEFAULT_CONDA_CHANNELS = [
    "conda-forge",
    "defaults"
]

# 核心SAGE包列表（本地开发安装的包名）
SAGE_PACKAGES = [
    "sage",
    "sage-common", 
    "sage-kernel",
    "sage-middleware",
    "sage-apps"
]

# 可选包列表
OPTIONAL_PACKAGES = [
    "numpy>=1.21.0",
    "pandas>=1.3.0",
    "matplotlib>=3.4.0",
    "scipy>=1.7.0",
    "scikit-learn>=1.0.0",
    "jupyter>=1.0.0",
    "ipykernel>=6.0.0"
]

# 开发环境额外包
DEVELOPMENT_PACKAGES = [
    "pytest>=6.0.0",
    "pytest-cov>=2.12.0",
    "black>=21.0.0",
    "flake8>=3.9.0",
    "mypy>=0.910",
    "pre-commit>=2.15.0",
    "sphinx>=4.0.0",
    "sphinx-rtd-theme>=0.5.0"
]

# 系统要求
SYSTEM_REQUIREMENTS = {
    "min_disk_space_gb": 5.0,
    "min_memory_gb": 4.0,
    "recommended_disk_space_gb": 10.0,
    "recommended_memory_gb": 8.0
}

# 安装超时配置（秒）
TIMEOUTS = {
    "package_install": 300,  # 5分钟
    "conda_create": 600,     # 10分钟
    "git_clone": 180,        # 3分钟
    "submodule_update": 300  # 5分钟
}

# 网络配置
NETWORK_URLS = {
    "pypi_test": "https://pypi.org",
    "conda_test": "https://anaconda.org", 
    "github_test": "https://github.com"
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}

# 安装模式配置
INSTALL_MODES = {
    "quick": {
        "name": "快速安装",
        "description": "仅安装核心SAGE包，适合快速体验",
        "packages": SAGE_PACKAGES,
        "conda_packages": [],
        "install_submodules": False
    },
    "standard": {
        "name": "标准安装", 
        "description": "安装SAGE核心包和常用科学计算库",
        "packages": SAGE_PACKAGES + OPTIONAL_PACKAGES,
        "conda_packages": ["numpy", "pandas", "matplotlib", "scipy"],
        "install_submodules": True
    },
    "development": {
        "name": "开发环境",
        "description": "完整开发环境，包含所有依赖和开发工具",
        "packages": SAGE_PACKAGES + OPTIONAL_PACKAGES + DEVELOPMENT_PACKAGES,
        "conda_packages": ["numpy", "pandas", "matplotlib", "scipy", "jupyter"],
        "install_submodules": True
    },
    "minimal": {
        "name": "最小安装",
        "description": "只安装必需的核心包",
        "packages": ["sage", "sage-common"],
        "conda_packages": [],
        "install_submodules": False
    }
}

# 环境变量模板
ENV_VARS_TEMPLATE = {
    "SAGE_ROOT": "",
    "SAGE_ENV": "",
    "PYTHONPATH": ""
}

# 文件路径配置
PATHS = {
    "project_root": ".",
    "packages_dir": "packages",
    "scripts_dir": "scripts", 
    "docs_dir": "docs",
    "tools_dir": "tools",
    "install_log": "install.log",
    "requirements_file": "requirements.txt"
}

# Git配置
GIT_CONFIG = {
    "default_branch": "main",
    "submodule_recursive": True,
    "submodule_timeout": 300
}

# 进度显示配置
PROGRESS_CONFIG = {
    "show_spinner": True,
    "update_interval": 0.1,
    "progress_bar_width": 50
}

# 错误处理配置
ERROR_CONFIG = {
    "max_retries": 3,
    "retry_delay": 2.0,
    "continue_on_error": False
}
