#!/usr/bin/env python3
"""
Migrate all package extras to the simplified scheme (Plan B).

New extras scheme:
- dev: Development dependencies (pytest, ruff, mypy, pre-commit)
- gpu: GPU acceleration (vllm, torch with CUDA)
- cpu: CPU-only (torch CPU version)
- all: All optional features

No backward compatibility - clean break.
"""

import re
import sys
from pathlib import Path

# Package-specific extras configuration
EXTRAS_CONFIG = {
    "sage": {
        "dev": [
            "isage[all]",
            "isage-tools>=0.1.0",
            "pytest>=7.4.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
            "pre-commit>=3.5.0",
        ],
        "all": [
            "isage-common>=0.1.0",
            "isage-platform>=0.1.0",
            "isage-kernel>=0.1.0",
            "isage-libs>=0.1.0",
            "isage-middleware>=0.1.0",
            "isage-cli>=0.1.0",
            "isage-studio>=0.1.0",
            "isage-llm-gateway>=0.1.0",
            "isage-edge>=0.1.0",
        ],
    },
    "sage-common": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.0.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "embedding": [
            "python-dotenv>=1.1.0,<2.0.0",
            "nvidia-ml-py>=12.535.108",
            "torch>=2.7.0,<3.0.0",
            "sentence-transformers>=3.1.0,<4.0.0",
            "transformers>=4.52.0,<4.54.0",
            "requests>=2.32.0,<3.0.0",
        ],
        "all": [
            "isage-common[embedding]",
        ],
    },
    "sage-platform": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "all": [],  # No optional runtime deps
    },
    "sage-kernel": {
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-benchmark>=4.0.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "gpu": [
            "# PyTorch GPU will be installed via torch>=2.7.0",
            "# Ensure CUDA is properly configured on your system",
        ],
        "cpu": [
            "# For CPU-only: pip install isage-kernel[cpu]",
            "# PyTorch CPU will be installed via torch>=2.7.0",
        ],
        "all": [],  # Basic package, no heavy optionals
    },
    "sage-libs": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "all": [],  # Dependencies managed via sage-middleware
    },
    "sage-middleware": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
            "pybind11>=2.10.0",  # For C++ extensions
        ],
        "vdb": [
            "isage-vdb>=0.2.0",
        ],
        "neuromem": [
            "isage-neuromem>=0.2.0.1",
        ],
        "all": [
            "isage-middleware[vdb,neuromem]",
        ],
    },
    "sage-llm-core": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.28.0,<1.0.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "gpu": [
            "vllm>=0.9.2,<0.10",  # WSL2-compatible
            "torch>=2.7.0,<3.0.0",
        ],
        "cpu": [
            "vllm>=0.9.2,<0.10",  # Minimal version
            "# For CPU: Install torch CPU separately if needed",
        ],
        "all": [
            "isage-llm-core[gpu]",
        ],
    },
    "sage-llm-gateway": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.28.0,<1.0.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "all": [
            "redis>=5.0.0",
            "prometheus-client>=0.19.0",
        ],
    },
    "sage-edge": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "all": [],  # Simple aggregator
    },
    "sage-cli": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.0.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "all": [],  # CLI has all deps in main dependencies
    },
    "sage-studio": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "all": [],  # Frontend build managed separately
    },
    "sage-tools": {
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.0.0",
            "ruff==0.14.6",
            "mypy>=1.7.0",
        ],
        "all": [],  # Dev tools, all deps in main
    },
}


def format_deps_list(deps: list[str], indent: str = "    ") -> str:
    """Format dependency list for TOML."""
    if not deps:
        return "[]"

    lines = ["["]
    for dep in deps:
        # Handle comments
        if dep.startswith("#"):
            lines.append(f"{indent}{dep}")
        else:
            lines.append(f'{indent}"{dep}",')
    lines.append("]")
    return "\n".join(lines)


def generate_extras_section(package_name: str) -> str:
    """Generate the new [project.optional-dependencies] section."""
    config = EXTRAS_CONFIG.get(package_name, {})

    if not config:
        # Default minimal config for packages not explicitly listed
        config = {
            "dev": [
                "pytest>=7.4.0",
                "ruff==0.14.6",
                "mypy>=1.7.0",
            ],
            "all": [],
        }

    lines = ["[project.optional-dependencies]"]

    # Always include dev first
    if "dev" in config:
        lines.append(f"dev = {format_deps_list(config['dev'])}")

    # Add other extras in order: gpu, cpu, vdb, neuromem, embedding, all
    extra_order = ["gpu", "cpu", "vdb", "neuromem", "embedding", "all"]
    for extra in extra_order:
        if extra in config:
            lines.append(f"{extra} = {format_deps_list(config[extra])}")

    return "\n".join(lines)


def update_pyproject(file_path: Path) -> bool:
    """Update a single pyproject.toml file."""
    package_name = file_path.parent.name

    print(f"Processing {package_name}...")

    content = file_path.read_text()

    # Find the [project.optional-dependencies] section
    pattern = r"\[project\.optional-dependencies\].*?(?=\n\[|\Z)"

    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"  ⚠️  No [project.optional-dependencies] section found in {package_name}")
        return False

    # Generate new section
    new_section = generate_extras_section(package_name)

    # Replace old section with new
    new_content = content[: match.start()] + new_section + content[match.end() :]

    # Write back
    file_path.write_text(new_content)
    print(f"  ✅ Updated {package_name}")
    return True


def main():
    """Main migration logic."""
    repo_root = Path(__file__).parent.parent.parent
    packages_dir = repo_root / "packages"

    if not packages_dir.exists():
        print("❌ packages/ directory not found")
        sys.exit(1)

    print("🚀 Migrating all package extras to simplified scheme (Plan B)")
    print("=" * 70)

    updated = []
    failed = []

    # Find all pyproject.toml files
    for pyproject_file in packages_dir.glob("*/pyproject.toml"):
        try:
            if update_pyproject(pyproject_file):
                updated.append(pyproject_file.parent.name)
            else:
                failed.append(pyproject_file.parent.name)
        except Exception as e:
            print(f"  ❌ Error processing {pyproject_file.parent.name}: {e}")
            failed.append(pyproject_file.parent.name)

    print("\n" + "=" * 70)
    print(f"✅ Successfully updated {len(updated)} packages:")
    for pkg in sorted(updated):
        print(f"   - {pkg}")

    if failed:
        print(f"\n⚠️  Failed to update {len(failed)} packages:")
        for pkg in sorted(failed):
            print(f"   - {pkg}")
        sys.exit(1)

    print("\n🎉 Migration complete!")
    print("\nNext steps:")
    print("1. Review changes: git diff packages/*/pyproject.toml")
    print("2. Test installation: pip install -e packages/sage-llm-core[dev]")
    print("3. Update documentation: docs-public/docs_src/getting-started/installation.md")
    print("4. Commit changes: git commit -m 'refactor: simplify package extras (Plan B)'")


if __name__ == "__main__":
    main()
