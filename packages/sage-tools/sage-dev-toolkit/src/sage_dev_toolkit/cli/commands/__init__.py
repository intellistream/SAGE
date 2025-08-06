"""
CLI Commands package for SAGE Development Toolkit.

This package contains modular command implementations organized by functionality.
"""

# 延迟导入以避免循环依赖
def get_apps():
    """延迟导入并返回所有应用"""
    from . import core, package_mgmt, maintenance, commercial, development, reporting, home
    
    return {
        'core': core.app,
        'package_mgmt': package_mgmt.app,
        'maintenance': maintenance.app,
        'commercial': commercial.app,
        'development': development.app,
        'reporting': reporting.app,
        'home': home.app
    }

__all__ = [
    'get_apps'
]
