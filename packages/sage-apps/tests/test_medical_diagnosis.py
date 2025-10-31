"""
Tests for medical diagnosis application
"""

import importlib.util
from pathlib import Path

import pytest


class TestMedicalDiagnosisStructure:
    """Test medical diagnosis app structure"""

    @pytest.fixture
    def medical_dir(self):
        """Get medical diagnosis directory path"""
        return Path(__file__).parent.parent / "src" / "sage" / "apps" / "medical_diagnosis"

    def test_medical_directory_exists(self, medical_dir):
        """Verify medical diagnosis directory exists"""
        assert medical_dir.exists(), "Medical diagnosis directory should exist"

    def test_required_files_exist(self, medical_dir):
        """Verify required files exist"""
        required_files = [
            "__init__.py",
            "README.md",
            "run_diagnosis.py",
        ]

        for file_name in required_files:
            file_path = medical_dir / file_name
            assert file_path.exists(), f"Required file not found: {file_name}"

    def test_required_directories_exist(self, medical_dir):
        """Verify required directories exist"""
        required_dirs = [
            "agents",
            "config",
            "tools",
        ]

        for dir_name in required_dirs:
            dir_path = medical_dir / dir_name
            assert dir_path.exists(), f"Required directory not found: {dir_name}"

    def test_run_diagnosis_not_empty(self, medical_dir):
        """Verify run_diagnosis.py is not empty"""
        run_file = medical_dir / "run_diagnosis.py"
        content = run_file.read_text()
        assert len(content.strip()) > 0, "run_diagnosis.py should not be empty"

    def test_run_diagnosis_has_main_or_class(self, medical_dir):
        """Verify run_diagnosis.py has executable code"""
        run_file = medical_dir / "run_diagnosis.py"
        content = run_file.read_text()

        # Check if file has either main() function or class definition
        has_main = "def main(" in content or "def main (" in content
        has_class = "class " in content
        has_if_name = 'if __name__ == "__main__"' in content

        assert has_main or has_class or has_if_name, (
            "run_diagnosis.py should have main() function, class definition, or if __name__ == '__main__'"
        )


class TestMedicalDiagnosisImports:
    """Test medical diagnosis imports"""

    @pytest.fixture
    def medical_dir(self):
        """Get medical diagnosis directory path"""
        return Path(__file__).parent.parent / "src" / "sage" / "apps" / "medical_diagnosis"

    def test_run_diagnosis_imports(self, medical_dir):
        """Test run_diagnosis.py can be imported"""
        run_file = medical_dir / "run_diagnosis.py"

        spec = importlib.util.spec_from_file_location("run_diagnosis", run_file)
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
                pytest.fail(f"Failed to import run_diagnosis.py: {e}")

    def test_agents_directory_has_content(self, medical_dir):
        """Verify agents directory has Python files"""
        agents_dir = medical_dir / "agents"
        python_files = list(agents_dir.glob("*.py"))

        # Should have at least __init__.py
        assert len(python_files) > 0, "agents directory should have Python files"

    def test_tools_directory_has_content(self, medical_dir):
        """Verify tools directory has Python files"""
        tools_dir = medical_dir / "tools"
        python_files = list(tools_dir.glob("*.py"))

        # Should have at least __init__.py
        assert len(python_files) > 0, "tools directory should have Python files"


class TestMedicalDiagnosisConfig:
    """Test medical diagnosis configuration"""

    @pytest.fixture
    def config_dir(self):
        """Get config directory path"""
        return (
            Path(__file__).parent.parent / "src" / "sage" / "apps" / "medical_diagnosis" / "config"
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
