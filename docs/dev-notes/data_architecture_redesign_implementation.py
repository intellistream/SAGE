"""
SAGE Data Manager - Two-Layer Architecture Implementation
=========================================================

This module provides the core infrastructure for SAGE's two-layer data architecture:
- Layer 1 (Sources): Physical dataset storage and loaders
- Layer 2 (Usages): Logical views for different experimental scenarios

Example usage:
    # Access by usage (recommended for most users)
    from sage.data import DataManager

    # Get a usage-specific view
    libamm_data = DataManager.get_usage("libamm")
    sift_loader = libamm_data.load("sift")

    # Access source directly (advanced users)
    sift_loader = DataManager.get_source("sift")

Architecture:
    sources/            # Physical datasets
    ├── sift/          # SIFT vector dataset
    ├── mnist/         # MNIST images
    └── qa_base/       # QA knowledge base

    usages/            # Logical views
    ├── libamm/        # LibAMM experiments → [sift, mnist, ...]
    ├── rag/           # RAG experiments → [qa_base, mmlu, ...]
    └── neuromem/      # NeuroMem experiments → [...]
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class DatasetMetadata:
    """Metadata for a dataset in the sources layer."""

    def __init__(self, config: dict):
        self.name = config.get("name", "")
        self.description = config.get("description", "")
        self.type = config.get("type", "unknown")  # e.g., vector, text, image
        self.format = config.get("format", "")
        self.maintainer = config.get("maintainer", "")
        self.tags = config.get("tags", [])
        self.size = config.get("size", "")
        self.license = config.get("license", "")

    def __repr__(self):
        return f"Dataset({self.name}, type={self.type})"


class SourceRegistry:
    """Registry for managing dataset sources."""

    def __init__(self, sources_root: Path):
        self.sources_root = sources_root
        self._cache: Dict[str, DatasetMetadata] = {}

    def discover_sources(self) -> List[str]:
        """Discover all available dataset sources."""
        if not self.sources_root.exists():
            return []

        sources = []
        for item in self.sources_root.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                # Check for dataset.yaml or __init__.py
                if (item / "dataset.yaml").exists() or (item / "__init__.py").exists():
                    sources.append(item.name)
        return sorted(sources)

    def get_metadata(self, source_name: str) -> Optional[DatasetMetadata]:
        """Get metadata for a specific source."""
        if source_name in self._cache:
            return self._cache[source_name]

        source_dir = self.sources_root / source_name
        metadata_file = source_dir / "dataset.yaml"

        if metadata_file.exists():
            with open(metadata_file) as f:
                config = yaml.safe_load(f)
                metadata = DatasetMetadata(config)
                self._cache[source_name] = metadata
                return metadata

        # Fallback: create minimal metadata
        metadata = DatasetMetadata({"name": source_name})
        self._cache[source_name] = metadata
        return metadata

    def load_source(self, source_name: str) -> Any:
        """Dynamically load a source's loader module."""
        try:
            # Try importing from sage.data.sources.<name>
            module = importlib.import_module(f"sage.data.sources.{source_name}")
            return module
        except ImportError as e:
            raise ValueError(f"Cannot load source '{source_name}': {e}")


class UsageProfile:
    """A usage profile defines which datasets are relevant for a specific purpose."""

    def __init__(self, name: str, config: dict, registry: SourceRegistry):
        self.name = name
        self.description = config.get("description", "")
        self.datasets = config.get("datasets", {})
        self.registry = registry

    def load(self, dataset_name: str) -> Any:
        """Load a dataset that belongs to this usage profile."""
        if dataset_name not in self.datasets:
            raise ValueError(
                f"Dataset '{dataset_name}' not available in usage '{self.name}'. "
                f"Available: {list(self.datasets.keys())}"
            )

        source_name = self.datasets[dataset_name]
        return self.registry.load_source(source_name)

    def list_datasets(self) -> List[str]:
        """List all datasets in this usage profile."""
        return list(self.datasets.keys())


class UsageRegistry:
    """Registry for managing usage profiles."""

    def __init__(self, usages_root: Path, source_registry: SourceRegistry):
        self.usages_root = usages_root
        self.source_registry = source_registry
        self._cache: Dict[str, UsageProfile] = {}

    def discover_usages(self) -> List[str]:
        """Discover all available usage profiles."""
        if not self.usages_root.exists():
            return []

        usages = []
        for item in self.usages_root.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                if (item / "config.yaml").exists():
                    usages.append(item.name)
        return sorted(usages)

    def get_usage(self, usage_name: str) -> UsageProfile:
        """Get a usage profile by name."""
        if usage_name in self._cache:
            return self._cache[usage_name]

        usage_dir = self.usages_root / usage_name
        config_file = usage_dir / "config.yaml"

        if not config_file.exists():
            raise ValueError(f"Usage profile '{usage_name}' not found")

        with open(config_file) as f:
            config = yaml.safe_load(f)

        profile = UsageProfile(usage_name, config, self.source_registry)
        self._cache[usage_name] = profile
        return profile


class DataManager:
    """
    Central manager for SAGE's two-layer data architecture.

    Usage:
        # Initialize (typically done once)
        manager = DataManager.get_instance()

        # Access via usage (recommended)
        rag_data = manager.get_usage("rag")
        qa_loader = rag_data.load("qa_base")

        # Direct source access (advanced)
        sift_loader = manager.get_source("sift")
    """

    _instance: Optional["DataManager"] = None

    def __init__(self, data_root: Optional[Path] = None):
        if data_root is None:
            # Auto-detect data root
            data_root = self._find_data_root()

        self.data_root = data_root
        self.sources_root = data_root / "sources"
        self.usages_root = data_root / "usages"

        self.source_registry = SourceRegistry(self.sources_root)
        self.usage_registry = UsageRegistry(self.usages_root, self.source_registry)

    @classmethod
    def get_instance(cls, data_root: Optional[Path] = None) -> "DataManager":
        """Get singleton instance of DataManager."""
        if cls._instance is None:
            cls._instance = cls(data_root)
        return cls._instance

    def _find_data_root(self) -> Path:
        """Auto-detect data root directory."""
        # Check environment variable
        import os

        if data_root := os.getenv("SAGE_DATA_ROOT"):
            return Path(data_root)

        # Check relative to this file
        current = Path(__file__).parent
        if (current / "sources").exists():
            return current

        # Default fallback
        return current

    # --- Source Layer API ---

    def list_sources(self) -> List[str]:
        """List all available data sources."""
        return self.source_registry.discover_sources()

    def get_source(self, source_name: str) -> Any:
        """Load a data source directly."""
        return self.source_registry.load_source(source_name)

    def get_source_metadata(self, source_name: str) -> Optional[DatasetMetadata]:
        """Get metadata for a data source."""
        return self.source_registry.get_metadata(source_name)

    # --- Usage Layer API ---

    def list_usages(self) -> List[str]:
        """List all available usage profiles."""
        return self.usage_registry.discover_usages()

    def get_usage(self, usage_name: str) -> UsageProfile:
        """Get a usage profile."""
        return self.usage_registry.get_usage(usage_name)

    # --- Utility Methods ---

    def print_structure(self):
        """Print the data architecture structure."""
        print("SAGE Data Architecture")
        print("=" * 60)

        print("\n📦 Sources (Data Marketplace):")
        for source in self.list_sources():
            metadata = self.get_source_metadata(source)
            print(f"  - {source}: {metadata.description if metadata else 'N/A'}")

        print("\n🎯 Usages (Purpose Marketplace):")
        for usage in self.list_usages():
            profile = self.get_usage(usage)
            print(f"  - {usage}: {profile.description}")
            for ds_name in profile.list_datasets():
                print(f"      → {ds_name}")


# Convenience functions for backward compatibility
def load_dataset(source_name: str) -> Any:
    """
    Load a dataset by source name (backward compatible).

    Args:
        source_name: Name of the dataset source

    Returns:
        Dataset loader module
    """
    manager = DataManager.get_instance()
    return manager.get_source(source_name)


def get_usage_view(usage_name: str) -> UsageProfile:
    """
    Get a usage-specific view of datasets.

    Args:
        usage_name: Name of the usage profile (e.g., 'libamm', 'rag')

    Returns:
        UsageProfile instance
    """
    manager = DataManager.get_instance()
    return manager.get_usage(usage_name)
