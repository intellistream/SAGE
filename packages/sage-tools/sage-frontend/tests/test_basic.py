"""
Basic tests for SAGE Frontend package
"""

import pytest
import sys
from pathlib import Path

def test_package_import():
    """Test that the package can be imported"""
    try:
        import sage_frontend
        assert sage_frontend.__version__ == "1.0.0"
        assert sage_frontend.__author__ == "IntelliStream Team"
    except ImportError:
        pytest.skip("Package not installed or not in path")

def test_package_structure():
    """Test that the package has the expected structure"""
    try:
        import sage_frontend
        package_path = Path(sage_frontend.__file__).parent
        
        # Check if the package directory exists
        assert package_path.exists()
        assert package_path.is_dir()
        
    except ImportError:
        pytest.skip("Package not installed or not in path")

def test_version_string():
    """Test that the version string is properly formatted"""
    try:
        import sage_frontend
        version = sage_frontend.__version__
        
        # Check version format (should be like "1.0.0")
        parts = version.split(".")
        assert len(parts) >= 2  # At least major.minor
        for part in parts:
            assert part.isdigit()
            
    except ImportError:
        pytest.skip("Package not installed or not in path")

@pytest.mark.api
def test_server_module_availability():
    """Test that the server module is available"""
    try:
        import sage_frontend.sage_server
        # If import succeeds, the module structure is correct
        assert True
    except ImportError:
        # This is expected if dependencies are not installed
        pytest.skip("Server module dependencies not available")

if __name__ == "__main__":
    pytest.main([__file__])
