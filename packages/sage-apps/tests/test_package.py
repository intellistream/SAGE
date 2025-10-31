"""Test sage.apps package metadata."""

from sage.apps import __version__


def test_version():
    """Test package version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_package_imports():
    """Test basic package imports work."""
    import sage.apps

    assert hasattr(sage.apps, "__version__")
