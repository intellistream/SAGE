"""
SAGE - Streaming Analytics and Graph Engine

SAGE is a comprehensive framework for streaming analytics, graph processing,
and distributed computing. It provides both open source and enterprise features.

Enterprise features require a valid commercial license.
"""

import warnings
import os
import sys
from pathlib import Path

__version__ = "1.0.1"
__author__ = "SAGE Team"
__email__ = "team@sage.com"

# Global enterprise status tracking
_ENTERPRISE_LICENSE_CHECKED = False
_ENTERPRISE_LICENSED = False

def _check_enterprise_license():
    """Check enterprise license status once per session."""
    global _ENTERPRISE_LICENSE_CHECKED, _ENTERPRISE_LICENSED
    
    if _ENTERPRISE_LICENSE_CHECKED:
        return _ENTERPRISE_LICENSED
    
    try:
        # Try to find and load license tools
        project_root = None
        current = Path.cwd()
        
        # Check common locations for project root
        possible_roots = [
            current,
            current.parent,
            current.parent.parent,
            Path(__file__).parent.parent.parent.parent.parent,  # From package location
            Path(os.environ.get("SAGE_PROJECT_ROOT", "")),
        ]
        
        for root in possible_roots:
            if root and root.exists():
                if (root / "tools" / "license").exists():
                    project_root = root
                    break
        
        if project_root:
            sys.path.insert(0, str(project_root / "tools" / "license"))
            from sage_license import LicenseValidator
            
            validator = LicenseValidator(project_root / "tools" / "license")
            license_info = validator.validate_license()
            _ENTERPRISE_LICENSED = license_info.get("commercial_enabled", False)
            
        _ENTERPRISE_LICENSE_CHECKED = True
        
        # Show warning if not licensed
        if not _ENTERPRISE_LICENSED:
            warnings.warn(
                "SAGE Enterprise features require a valid commercial license. "
                "Enterprise functionality will be disabled. "
                "Please contact your SAGE vendor for licensing information.",
                UserWarning,
                stacklevel=2
            )
        
        return _ENTERPRISE_LICENSED
        
    except Exception:
        _ENTERPRISE_LICENSE_CHECKED = True
        _ENTERPRISE_LICENSED = False
        
        warnings.warn(
            "SAGE Enterprise features require a valid commercial license. "
            "Enterprise functionality will be disabled. "
            "Please contact your SAGE vendor for licensing information.",
            UserWarning,
            stacklevel=2
        )
        
        return False

# Check enterprise license on import
_check_enterprise_license()

def get_version():
    """Get SAGE version."""
    return __version__

def is_enterprise_licensed():
    """Check if enterprise features are licensed."""
    return _ENTERPRISE_LICENSED

def check_features():
    """Check available SAGE features."""
    features = {
        "version": __version__,
        "open_source": True,
        "enterprise_licensed": _ENTERPRISE_LICENSED
    }
    
    return features

def info():
    """Print SAGE information."""
    features = check_features()
    
    print("🏗️  SAGE - Streaming Analytics and Graph Engine")
    print("=" * 50)
    print(f"Version: {features['version']}")
    print(f"Open Source: {'✅ Available' if features['open_source'] else '❌ Not Available'}")
    print(f"Enterprise: {'✅ Licensed' if features.get('enterprise_licensed') else '❌ Not Licensed'}")
    
    print("\n📚 Documentation: https://sage-docs.example.com")
    print("🎯 Support: support@sage.ai")
    
    if not features.get("enterprise_licensed"):
        print("\n💡 For enterprise features, contact: sales@sage.ai")

def install_open_source():
    """Install open source SAGE packages."""
    print("Please use 'pip install -r requirements-dev.txt' to install SAGE")
    return False

# Main exports
__all__ = [
    "get_version",
    "check_features", 
    "install_open_source",
    "is_enterprise_licensed",
    "info",
]
