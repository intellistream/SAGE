"""
SAGE - Streaming Analytics and Graph Engine

SAGE is a comprehensive framework for streaming analytics, graph processing,
and distributed computing. It provides both open source and enterprise features.
"""

# This is a namespace package - allow extension by other packages
__path__ = __import__('pkgutil').extend_path(__path__, __name__)

import warnings

__version__ = "1.0.1"
__author__ = "SAGE Team"
__email__ = "team@sage.com"

def get_version():
    """Get SAGE version."""
    return __version__

def check_features():
    """Check available SAGE features."""
    features = {
        "version": __version__,
        "open_source": True,
    }
    
    return features

def info():
    """Print SAGE information."""
    features = check_features()
    
    print("🏗️  SAGE - Streaming Analytics and Graph Engine")
    print("=" * 50)
    print(f"Version: {features['version']}")
    print(f"Open Source: {'✅ Available' if features['open_source'] else '❌ Not Available'}")
    
    print("\n📚 Documentation: https://sage-docs.example.com")
    print("🎯 Support: support@sage.ai")

def install_open_source():
    """Install open source SAGE packages."""
    print("Please use 'pip install -r requirements-dev.txt' to install SAGE")
    return False

# Main exports
__all__ = [
    "get_version",
    "check_features", 
    "install_open_source",
    "info",
    # Core API exports
    "LocalEnvironment",
    "RemoteEnvironment", 
    "DataStream",
    "ConnectedStreams",
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "SinkFunction",
    "SourceFunction",
]