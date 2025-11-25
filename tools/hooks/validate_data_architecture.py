#!/usr/bin/env python3
"""
Pre-commit hook to validate SAGE data architecture compliance.

This hook ensures that new datasets follow the two-layer architecture:
- Layer 1 (sources/): Physical datasets with dataset.yaml
- Layer 2 (usages/): Usage profiles with config.yaml

Usage:
    As a pre-commit hook (configured in .pre-commit-config.yaml)
    Or run manually: python tools/hooks/validate_data_architecture.py
"""

import sys
from pathlib import Path

import yaml


class DataArchitectureValidator:
    """Validator for SAGE data architecture compliance."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.data_root = repo_root / "packages" / "sage-benchmark" / "src" / "sage" / "data"
        self.sources_dir = self.data_root / "sources"
        self.usages_dir = self.data_root / "usages"
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all(self) -> bool:
        """Run all validations. Returns True if all checks pass."""
        if not self.data_root.exists():
            print(f"⚠️  Data root not found: {self.data_root}")
            return True  # Not an error if sage-data doesn't exist

        print("🔍 Validating SAGE Data Architecture...")

        self.validate_clean_structure()
        self.validate_sources()
        self.validate_usages()
        self.validate_cross_references()

        return self.report_results()

    def validate_clean_structure(self):
        """Validate that only allowed items exist in data root (strict whitelist)."""
        if not self.data_root.exists():
            return

        # Strict whitelist of allowed items in data root
        allowed_items = {
            # New architecture - ONLY these directories for data
            "sources",  # Physical datasets
            "usages",  # Usage profiles
            "examples",  # Example scripts
            "tests",  # Test files
            # Python/Git infrastructure (必须)
            "__pycache__",
            ".git",
            ".gitignore",
            ".gitattributes",
            "__init__.py",
            # Core architecture files (必须)
            "manager.py",
            "ARCHITECTURE.md",
            "README.md",
            # Submodule metadata (必须)
            "SUBMODULE.md",
            "LICENSE",
            # Configuration files (必须)
            "pyproject.toml",
            "pytest.ini",
            "requirements.txt",
            "requirements-dev.txt",
            "setup.sh",
            # Testing (必须)
            "test_architecture.py",
        }

        # Find all violations (any directory/file not in whitelist)
        violations = []
        for item in self.data_root.iterdir():
            if item.name not in allowed_items:
                violations.append(item.name)

        if violations:
            self.errors.append(
                f"❌ Found unauthorized items in data root directory:\n"
                f"   {', '.join(sorted(violations))}\n"
                f"   \n"
                f"   ✅ Allowed directories: sources/, usages/, examples/, tests/\n"
                f"   ✅ Required files: __init__.py, manager.py, ARCHITECTURE.md, etc.\n"
                f"   \n"
                f"   Please migrate datasets to sources/ or delete unauthorized items."
            )

    def validate_sources(self):
        """Validate all datasets in sources/."""
        if not self.sources_dir.exists():
            self.errors.append(f"Sources directory not found: {self.sources_dir}")
            return

        for source_dir in self.sources_dir.iterdir():
            if not source_dir.is_dir() or source_dir.name.startswith("_"):
                continue

            self.validate_source(source_dir)

    def validate_source(self, source_dir: Path):
        """Validate a single data source."""
        source_name = source_dir.name
        dataset_yaml = source_dir / "dataset.yaml"
        init_py = source_dir / "__init__.py"

        # Check for dataset.yaml
        if not dataset_yaml.exists():
            self.errors.append(f"❌ Source '{source_name}' missing dataset.yaml")
            return

        # Validate dataset.yaml structure
        try:
            with open(dataset_yaml) as f:
                metadata = yaml.safe_load(f)

            required_fields = ["name", "description", "type", "format"]
            missing_fields = [f for f in required_fields if f not in metadata]

            if missing_fields:
                self.errors.append(
                    f"❌ Source '{source_name}' dataset.yaml missing fields: {', '.join(missing_fields)}"
                )

            # Validate name matches directory
            if metadata.get("name") != source_name:
                self.warnings.append(
                    f"⚠️  Source '{source_name}' has mismatched name in dataset.yaml: '{metadata.get('name')}'"
                )

            # Check recommended fields
            recommended_fields = ["maintainer", "tags", "license", "version"]
            missing_recommended = [f for f in recommended_fields if f not in metadata]
            if missing_recommended:
                self.warnings.append(
                    f"⚠️  Source '{source_name}' missing recommended fields: {', '.join(missing_recommended)}"
                )

        except yaml.YAMLError as e:
            self.errors.append(f"❌ Source '{source_name}' has invalid YAML: {e}")
        except Exception as e:
            self.errors.append(f"❌ Source '{source_name}' validation error: {e}")

        # Check for __init__.py
        if not init_py.exists():
            self.warnings.append(
                f"⚠️  Source '{source_name}' missing __init__.py (recommended for imports)"
            )

    def validate_usages(self):
        """Validate all usage profiles in usages/."""
        if not self.usages_dir.exists():
            self.warnings.append(f"Usages directory not found: {self.usages_dir}")
            return

        for usage_dir in self.usages_dir.iterdir():
            if not usage_dir.is_dir() or usage_dir.name.startswith("_"):
                continue

            self.validate_usage(usage_dir)

    def validate_usage(self, usage_dir: Path):
        """Validate a single usage profile."""
        usage_name = usage_dir.name
        config_yaml = usage_dir / "config.yaml"

        # Check for config.yaml
        if not config_yaml.exists():
            self.errors.append(f"❌ Usage '{usage_name}' missing config.yaml")
            return

        # Validate config.yaml structure
        try:
            with open(config_yaml) as f:
                config = yaml.safe_load(f)

            required_fields = ["description", "datasets"]
            missing_fields = [f for f in required_fields if f not in config]

            if missing_fields:
                self.errors.append(
                    f"❌ Usage '{usage_name}' config.yaml missing fields: {', '.join(missing_fields)}"
                )

            # Validate datasets is a dict
            if "datasets" in config and not isinstance(config["datasets"], dict):
                self.errors.append(f"❌ Usage '{usage_name}' datasets field must be a dictionary")

            # Check recommended fields
            if "maintainer" not in config:
                self.warnings.append(
                    f"⚠️  Usage '{usage_name}' missing recommended field: maintainer"
                )

        except yaml.YAMLError as e:
            self.errors.append(f"❌ Usage '{usage_name}' has invalid YAML: {e}")
        except Exception as e:
            self.errors.append(f"❌ Usage '{usage_name}' validation error: {e}")

    def validate_cross_references(self):
        """Validate that usage profiles reference existing sources."""
        if not self.usages_dir.exists():
            return

        # Get all valid sources
        valid_sources = set()
        if self.sources_dir.exists():
            valid_sources = {
                d.name
                for d in self.sources_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            }

        # Check each usage's dataset references
        for usage_dir in self.usages_dir.iterdir():
            if not usage_dir.is_dir() or usage_dir.name.startswith("_"):
                continue

            config_yaml = usage_dir / "config.yaml"
            if not config_yaml.exists():
                continue

            try:
                with open(config_yaml) as f:
                    config = yaml.safe_load(f)

                datasets = config.get("datasets", {})
                for alias, source_name in datasets.items():
                    if source_name not in valid_sources:
                        self.errors.append(
                            f"❌ Usage '{usage_dir.name}' references non-existent source: '{source_name}' (alias: '{alias}')"
                        )
            except Exception:
                pass  # Already reported in validate_usage

    def report_results(self) -> bool:
        """Report validation results. Returns True if no errors."""
        if not self.errors and not self.warnings:
            print("✅ All data architecture checks passed!")
            return True

        if self.warnings:
            print(f"\n⚠️  Found {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                print(f"  {warning}")

        if self.errors:
            print(f"\n❌ Found {len(self.errors)} error(s):")
            for error in self.errors:
                print(f"  {error}")
            print("\n💡 See docs/dev-notes/data_extension_guide.md for guidelines")
            return False

        print("\n✅ No errors found (only warnings)")
        return True


def find_repo_root() -> Path:
    """Find repository root by looking for .git directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


def main():
    """Main entry point for the validation hook."""
    repo_root = find_repo_root()
    validator = DataArchitectureValidator(repo_root)

    success = validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
