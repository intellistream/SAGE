"""
Import smoke tests for sage-middleware package.

Tests are categorized into:
- Release tests: For packaged/installed environment (pip install isage-middleware)
- Develop tests: For development environment (pip install -e .)

Run release tests:
    pytest tests/smoke/test_imports.py -m release

Run develop tests:
    pytest tests/smoke/test_imports.py -m develop

Run all smoke tests:
    pytest tests/smoke/test_imports.py
"""
import os
import sys
import pytest


def is_release_environment():
    """
    Check if we're running in a release (installed) environment.
    
    Returns:
        bool: True if installed package, False if development mode
    """
    try:
        import sage.middleware
        # In development mode, __file__ will point to the source directory
        # In release mode, it will point to site-packages
        middleware_path = sage.middleware.__file__
        return 'site-packages' in middleware_path or 'dist-packages' in middleware_path
    except (ImportError, AttributeError):
        return False


# Mark tests based on environment
pytestmark = pytest.mark.smoke


class TestCoreImports:
    """Test core sage.middleware imports."""

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_sage_middleware(self):
        """Test importing the main sage.middleware package."""
        import sage.middleware
        assert sage.middleware is not None
        assert hasattr(sage.middleware, '__version__')

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_version(self):
        """Test importing version information."""
        from sage.middleware._version import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)
        print(f"sage-middleware version: {__version__}")


class TestAgentImports:
    """Test sage.middleware.agent imports."""

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_runtime(self):
        """Test importing agent runtime."""
        from sage.middleware.operators.agent import runtime
        assert runtime is not None

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_planning(self):
        """Test importing planning modules."""
        from sage.middleware.operators.agent.planning import router
        from sage.middleware.operators.agent.planning import planner_adapter
        from sage.middleware.operators.agent.planning import llm_adapter
        assert router is not None
        assert planner_adapter is not None
        assert llm_adapter is not None


class TestComponentsImports:
    """Test sage.middleware.components imports."""

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_components(self):
        """Test importing components package."""
        import sage.middleware.components
        assert sage.middleware.components is not None

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_extensions_compat(self):
        """Test importing extensions compatibility layer."""
        from sage.middleware.components import extensions_compat
        assert extensions_compat is not None

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_sage_db(self):
        """Test importing sage_db component."""
        try:
            from sage.middleware.components import sage_db
            assert sage_db is not None
            print(f"sage_db backend available: {hasattr(sage_db, 'backend')}")
        except ImportError as e:
            pytest.skip(f"sage_db not available (requires isage-vdb): {e}")

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_sage_flow(self):
        """Test importing sage_flow component."""
        try:
            from sage.middleware.components import sage_flow
            assert sage_flow is not None
            print(f"sage_flow available")
        except ImportError as e:
            pytest.skip(f"sage_flow not available (requires isage-flow): {e}")

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_sage_mem(self):
        """Test importing sage_mem component."""
        try:
            from sage.middleware.components import sage_mem
            assert sage_mem is not None
            print(f"sage_mem available")
        except ImportError as e:
            pytest.skip(f"sage_mem not available (requires isage-neuromem): {e}")

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_sage_refiner(self):
        """Test importing sage_refiner component."""
        try:
            from sage.middleware.components import sage_refiner
            assert sage_refiner is not None
            print(f"sage_refiner available")
        except ImportError as e:
            pytest.skip(f"sage_refiner not available (requires isage-refiner): {e}")


class TestOperatorsImports:
    """Test sage.middleware.operators imports."""

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_operators(self):
        """Test importing operators package."""
        try:
            import sage.middleware.operators
            assert sage.middleware.operators is not None
        except ImportError as e:
            pytest.skip(f"operators module structure may have changed: {e}")


class TestContextImports:
    """Test sage.middleware.context imports."""

    @pytest.mark.release
    @pytest.mark.develop
    def test_import_context(self):
        """Test importing context package."""
        try:
            import sage.middleware.operators.context
            assert sage.middleware.operators.context is not None
        except ImportError as e:
            pytest.skip(f"context module structure may have changed: {e}")


class TestEnvironmentInfo:
    """Display environment information for debugging."""

    @pytest.mark.release
    @pytest.mark.develop
    def test_environment_info(self):
        """Display environment information."""
        import sage.middleware
        
        env_type = "RELEASE" if is_release_environment() else "DEVELOP"
        print(f"\n{'='*60}")
        print(f"Environment Type: {env_type}")
        print(f"Python Version: {sys.version}")
        print(f"Python Executable: {sys.executable}")
        print(f"sage.middleware location: {sage.middleware.__file__}")
        print(f"sage.middleware version: {sage.middleware.__version__}")
        print(f"{'='*60}")


class TestReleaseOnly:
    """Tests that should only run in release (installed) environment."""

    @pytest.mark.release
    def test_release_package_structure(self):
        """Verify release package has correct structure."""
        import sage.middleware
        
        if not is_release_environment():
            pytest.skip("This test only runs in release environment")
        
        middleware_path = sage.middleware.__file__
        assert 'site-packages' in middleware_path or 'dist-packages' in middleware_path
        print(f"Release package location verified: {middleware_path}")


class TestDevelopOnly:
    """Tests that should only run in development environment."""

    @pytest.mark.develop
    def test_develop_package_structure(self):
        """Verify development package has correct structure."""
        import sage.middleware
        
        if is_release_environment():
            pytest.skip("This test only runs in development environment")
        
        middleware_path = sage.middleware.__file__
        assert 'src/sage/middleware' in middleware_path or 'sage-middleware' in middleware_path
        print(f"Development package location verified: {middleware_path}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
