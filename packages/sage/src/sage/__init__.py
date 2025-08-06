"""
SAGE - Streaming Analytics and Graph Engine

SAGE is a comprehensive framework for streaming analytics, graph processing,
and distributed computing. It provides both open source and enterprise features.

Enterprise features require a valid commercial license.
"""

__version__ = "1.0.0"
__author__ = "SAGE Team"
__email__ = "team@sage.com"

# Core imports
# from .install import install_packages, check_installation

# Enterprise management
try:
    from .enterprise_manager import (
        check_enterprise_features,
        install_enterprise,
        SAGEEnterpriseInstaller
    )
    _ENTERPRISE_MANAGER_AVAILABLE = True
except ImportError:
    _ENTERPRISE_MANAGER_AVAILABLE = False


def get_version():
    """Get SAGE version."""
    return __version__


def check_features():
    """Check available SAGE features."""
    features = {
        "version": __version__,
        "open_source": True,
        "enterprise_manager": _ENTERPRISE_MANAGER_AVAILABLE
    }
    
    if _ENTERPRISE_MANAGER_AVAILABLE:
        try:
            enterprise_status = check_enterprise_features()
            features.update({
                "enterprise_licensed": enterprise_status["license"]["commercial_enabled"],
                "enterprise_features": enterprise_status["license"]["features"],
                "enterprise_components": enterprise_status["summary"]["components_available"]
            })
        except Exception:
            features["enterprise_licensed"] = False
    else:
        features["enterprise_licensed"] = False
    
    return features


def info():
    """Print SAGE information."""
    features = check_features()
    
    print("🏗️  SAGE - Streaming Analytics and Graph Engine")
    print("=" * 50)
    print(f"Version: {features['version']}")
    print(f"Open Source: {'✅ Available' if features['open_source'] else '❌ Not Available'}")
    print(f"Enterprise: {'✅ Licensed' if features.get('enterprise_licensed') else '❌ Not Licensed'}")
    
    if features.get("enterprise_licensed"):
        print(f"Enterprise Features: {', '.join(features.get('enterprise_features', []))}")
        print(f"Enterprise Components: {features.get('enterprise_components', '0/0')}")
    
    print("\n📚 Documentation: https://sage-docs.example.com")
    print("🎯 Support: support@sage.ai")
    
    if not features.get("enterprise_licensed"):
        print("\n💡 For enterprise features, contact: sales@sage.ai")


# Convenience functions for package management
def install_open_source():
    """Install open source SAGE packages."""
    print("Please use 'pip install -r requirements-dev.txt' to install SAGE")
    return False


def install_enterprise_edition(license_key=None):
    """Install enterprise SAGE packages."""
    if not _ENTERPRISE_MANAGER_AVAILABLE:
        raise ImportError("Enterprise manager not available")
    
    return install_enterprise(license_key)


# Main exports
__all__ = [
    "get_version",
    "check_features", 
    "install_open_source",
    "install_enterprise_edition",
]

# Add enterprise exports if available
if _ENTERPRISE_MANAGER_AVAILABLE:
    __all__.extend([
        "check_enterprise_features",
        "install_enterprise",
        "SAGEEnterpriseInstaller"
    ])
