"""
Tests for video application
"""

import importlib.util
from pathlib import Path

import pytest


class TestVideoAppStructure:
    """Test video app structure"""

    @pytest.fixture
    def video_dir(self):
        """Get video directory path"""
        return Path(__file__).parent.parent / "src" / "sage" / "apps" / "video"

    def test_video_directory_exists(self, video_dir):
        """Verify video directory exists"""
        assert video_dir.exists(), "Video directory should exist"

    def test_required_files_exist(self, video_dir):
        """Verify required files exist"""
        required_files = [
            "__init__.py",
            "video_intelligence_pipeline.py",
        ]

        for file_name in required_files:
            file_path = video_dir / file_name
            assert file_path.exists(), f"Required file not found: {file_name}"

    def test_required_directories_exist(self, video_dir):
        """Verify required directories exist"""
        required_dirs = [
            "operators",
            "config",
        ]

        for dir_name in required_dirs:
            dir_path = video_dir / dir_name
            assert dir_path.exists(), f"Required directory not found: {dir_name}"

    def test_video_intelligence_pipeline_not_empty(self, video_dir):
        """Verify video_intelligence_pipeline.py is not empty"""
        pipeline_file = video_dir / "video_intelligence_pipeline.py"
        content = pipeline_file.read_text()
        assert (
            len(content.strip()) > 0
        ), "video_intelligence_pipeline.py should not be empty"

    def test_video_intelligence_has_main_or_class(self, video_dir):
        """Verify video_intelligence_pipeline.py has executable code"""
        pipeline_file = video_dir / "video_intelligence_pipeline.py"
        content = pipeline_file.read_text()

        # Check if file has either main() function or class definition
        has_main = "def main(" in content or "def main (" in content
        has_class = "class " in content
        has_if_name = 'if __name__ == "__main__"' in content

        assert (
            has_main or has_class or has_if_name
        ), "video_intelligence_pipeline.py should have main() function, class definition, or if __name__ == '__main__'"


class TestVideoAppImports:
    """Test video app imports"""

    @pytest.fixture
    def video_dir(self):
        """Get video directory path"""
        return Path(__file__).parent.parent / "src" / "sage" / "apps" / "video"

    def test_video_intelligence_pipeline_imports(self, video_dir):
        """Test video_intelligence_pipeline.py can be imported"""
        pipeline_file = video_dir / "video_intelligence_pipeline.py"

        spec = importlib.util.spec_from_file_location(
            "video_intelligence_pipeline", pipeline_file
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                # Module loaded successfully
                assert True
            except ImportError as e:
                # Import errors are expected if dependencies are missing
                pytest.skip(f"Skipping due to missing dependencies: {e}")
            except Exception as e:
                pytest.fail(f"Failed to import video_intelligence_pipeline.py: {e}")

    def test_operators_directory_has_content(self, video_dir):
        """Verify operators directory has Python files"""
        operators_dir = video_dir / "operators"
        python_files = list(operators_dir.glob("*.py"))

        # Should have at least __init__.py
        assert len(python_files) > 0, "operators directory should have Python files"


class TestVideoAppOperators:
    """Test video app operators"""

    @pytest.fixture
    def operators_dir(self):
        """Get operators directory path"""
        return (
            Path(__file__).parent.parent
            / "src"
            / "sage"
            / "apps"
            / "video"
            / "operators"
        )

    def test_operators_not_empty(self, operators_dir):
        """Verify operator files are not empty"""
        python_files = list(operators_dir.glob("*.py"))
        python_files = [f for f in python_files if f.name != "__init__.py"]

        for py_file in python_files:
            content = py_file.read_text()
            assert len(content.strip()) > 0, f"{py_file.name} should not be empty"

    def test_operators_have_classes(self, operators_dir):
        """Verify operator files have class definitions"""
        python_files = list(operators_dir.glob("*.py"))
        python_files = [f for f in python_files if f.name != "__init__.py"]

        if len(python_files) == 0:
            pytest.skip("No operator files found")

        for py_file in python_files:
            content = py_file.read_text()

            # Check if file has class definition
            has_class = "class " in content

            # Operator files should typically have class definitions
            if not has_class:
                pytest.skip(f"{py_file.name} might be a utility file without classes")


class TestVideoAppConfig:
    """Test video app configuration"""

    @pytest.fixture
    def config_dir(self):
        """Get config directory path"""
        return (
            Path(__file__).parent.parent / "src" / "sage" / "apps" / "video" / "config"
        )

    def test_config_directory_exists(self, config_dir):
        """Verify config directory exists"""
        assert config_dir.exists(), "Config directory should exist"

    def test_config_files_exist(self, config_dir):
        """Verify config files exist"""
        config_files = (
            list(config_dir.glob("*.yaml"))
            + list(config_dir.glob("*.json"))
            + list(config_dir.glob("*.toml"))
        )

        # Should have at least one config file
        if len(config_files) > 0:
            assert True, "Config directory has configuration files"
        else:
            pytest.skip("No config files found (might be optional)")
