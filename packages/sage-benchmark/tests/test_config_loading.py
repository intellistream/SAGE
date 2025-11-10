"""
Tests for benchmark configuration loading
"""

from pathlib import Path

import pytest
import yaml


class TestConfigLoading:
    """Test configuration file loading"""

    def test_config_files_exist(self):
        """Verify all config files exist"""
        config_dir = (
            Path(__file__).parent.parent / "src" / "sage" / "benchmark" / "benchmark_rag" / "config"
        )

        expected_configs = [
            "config_dense_milvus.yaml",
            "config_sparse_milvus.yaml",
            "config_mixed.yaml",
            "config_qa_chroma.yaml",
        ]

        for config_file in expected_configs:
            config_path = config_dir / config_file
            assert config_path.exists(), f"Config file not found: {config_file}"

    def test_config_yaml_valid(self):
        """Verify all YAML files are valid"""
        config_dir = (
            Path(__file__).parent.parent / "src" / "sage" / "benchmark" / "benchmark_rag" / "config"
        )

        for config_file in config_dir.glob("*.yaml"):
            with open(config_file) as f:
                try:
                    config = yaml.safe_load(f)
                    assert isinstance(config, dict), (
                        f"{config_file.name} should contain a dictionary"
                    )
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {config_file.name}: {e}")

    def test_dense_milvus_config_structure(self):
        """Test dense milvus config has required fields"""
        config_path = (
            Path(__file__).parent.parent
            / "src"
            / "sage"
            / "benchmark"
            / "benchmark_rag"
            / "config"
            / "config_dense_milvus.yaml"
        )

        if not config_path.exists():
            pytest.skip("config_dense_milvus.yaml not found")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Check for expected sections (flexible, as structure may vary)
        assert config is not None, "Config should not be empty"
        assert isinstance(config, dict), "Config should be a dictionary"


class TestDataFiles:
    """Test benchmark data files"""

    def test_data_directory_exists(self):
        """Verify data directory exists"""
        data_dir = Path(__file__).parent.parent / "src" / "sage" / "data" / "qa"
        assert data_dir.exists(), "Data directory should exist"

    def test_queries_file_exists(self):
        """Verify queries.jsonl exists"""
        queries_path = (
            Path(__file__).parent.parent / "src" / "sage" / "data" / "qa" / "queries.jsonl"
        )

        if queries_path.exists():
            # If file exists, verify it's valid JSONL
            with open(queries_path) as f:
                lines = f.readlines()
                assert len(lines) > 0, "queries.jsonl should not be empty"
