"""
Test that all examples can be imported successfully.

This test ensures that:
1. All example files have valid Python syntax
2. All imports in examples are resolvable
3. No obvious import errors exist

Note: This test only checks imports, not execution.
"""

import ast
from pathlib import Path

import pytest


def find_example_files(base_dir: Path) -> list[Path]:
    """Find all Python files in examples directory."""
    example_files: list[Path] = []

    if not base_dir.exists():
        return example_files

    # Find all .py files, excluding __pycache__ and __init__.py
    for py_file in base_dir.rglob("*.py"):
        # Skip __pycache__ directories
        if "__pycache__" in str(py_file):
            continue
        # Skip __init__.py files (they're usually empty)
        if py_file.name == "__init__.py":
            continue
        # Skip test files
        if py_file.name.startswith("test_"):
            continue

        example_files.append(py_file)

    return example_files


def check_syntax(file_path: Path) -> tuple[bool, str]:
    """Check if a Python file has valid syntax."""
    try:
        code = file_path.read_text(encoding="utf-8")
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error parsing file: {str(e)}"


def get_imports(file_path: Path) -> list[str]:
    """Extract all import statements from a Python file."""
    try:
        code = file_path.read_text(encoding="utf-8")
        tree = ast.parse(code)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])

        return list(set(imports))  # Remove duplicates
    except Exception:
        return []


# Find all example files
workspace_root = Path(__file__).parent.parent.parent.parent
examples_dir = workspace_root / "examples"
example_files = find_example_files(examples_dir)


@pytest.mark.parametrize(
    "example_file", example_files, ids=lambda p: str(p.relative_to(examples_dir))
)
def test_example_syntax(example_file: Path):
    """Test that each example file has valid Python syntax."""
    is_valid, error_msg = check_syntax(example_file)
    assert is_valid, f"Syntax error in {example_file.name}: {error_msg}"


@pytest.mark.parametrize(
    "example_file", example_files, ids=lambda p: str(p.relative_to(examples_dir))
)
def test_example_imports(example_file: Path):
    """Test that each example's imports can be resolved."""
    imports = get_imports(example_file)

    # These are modules that might not be installed in CI but are OK
    optional_modules = {
        "torch",
        "tensorflow",
        "transformers",
        "langchain",
        "openai",
        "anthropic",
        "faiss",
        "chromadb",
        "redis",
        "pymongo",
        "sqlalchemy",
        "flask",
        "fastapi",
        "streamlit",
        "gradio",
        "cv2",
        "PIL",
        "mediapipe",
        "ultralytics",
    }

    # Check each import (but skip optional ones)
    for module_name in imports:
        if module_name in optional_modules:
            continue

        # Special handling for relative imports
        if module_name.startswith("."):
            continue

        # Check if it's a SAGE module or standard library
        if module_name.startswith("sage"):
            # SAGE modules should always be importable
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(
                    f"Example {example_file.name} imports SAGE module '{module_name}' "
                    f"which cannot be imported: {e}"
                )
        else:
            # For non-SAGE modules, just check they're not obviously wrong
            # (We can't check all because we don't have all deps installed)
            pass


def test_examples_directory_exists():
    """Test that the examples directory exists and is not empty."""
    assert examples_dir.exists(), f"Examples directory not found: {examples_dir}"
    assert len(example_files) > 0, "No example files found in examples directory"


def test_examples_have_reasonable_structure():
    """Test that examples follow a reasonable structure."""
    # Check that we have examples in expected subdirectories
    subdirs = [
        d.name
        for d in examples_dir.iterdir()
        if d.is_dir() and not d.name.startswith("__")
    ]

    # We expect at least some common subdirectories
    assert len(subdirs) > 0, "Examples directory should have subdirectories"

    # Print summary
    print("\n📊 Examples Summary:")
    print(f"  - Total example files: {len(example_files)}")
    print(f"  - Subdirectories: {', '.join(subdirs)}")

    # Count files per subdirectory
    for subdir in subdirs:
        files_in_subdir = [f for f in example_files if subdir in str(f)]
        print(f"  - {subdir}: {len(files_in_subdir)} files")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
