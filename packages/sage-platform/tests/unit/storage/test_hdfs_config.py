"""Unit tests for HDFS Configuration

Tests for sage.platform.storage.hdfs_config module
"""

import os

import pytest

from sage.platform.storage.hdfs_config import HDFSConfig


class TestHDFSConfig:
    """Test HDFS configuration management"""

    def test_basic_config_creation(self):
        """Test creating basic HDFS config"""
        config = HDFSConfig(
            namenode_host="localhost",
            namenode_port=9000,
            user="testuser",
        )

        assert config.namenode_host == "localhost"
        assert config.namenode_port == 9000
        assert config.user == "testuser"
        assert config.use_kerberos is False

    def test_config_with_kerberos(self):
        """Test HDFS config with Kerberos authentication"""
        config = HDFSConfig(
            namenode_host="localhost",
            namenode_port=9000,
            user="testuser",
            use_kerberos=True,
            keytab_path="/path/to/keytab",
            principal="user@REALM",
        )

        assert config.use_kerberos is True
        assert config.keytab_path == "/path/to/keytab"
        assert config.principal == "user@REALM"

    def test_get_namenode_url(self):
        """Test namenode URL generation"""
        config = HDFSConfig(
            namenode_host="namenode.example.com",
            namenode_port=9000,
            user="hdfs",
        )

        url = config.get_namenode_url()
        assert url == "hdfs://namenode.example.com:9000"

    def test_config_from_env_variables(self):
        """Test loading config from environment variables"""
        # Set environment variables
        os.environ["HDFS_NAMENODE_HOST"] = "env-namenode"
        os.environ["HDFS_NAMENODE_PORT"] = "9001"
        os.environ["HDFS_USER"] = "envuser"

        try:
            config = HDFSConfig.from_env()
            assert config.namenode_host == "env-namenode"
            assert config.namenode_port == 9001
            assert config.user == "envuser"
        finally:
            # Clean up
            os.environ.pop("HDFS_NAMENODE_HOST", None)
            os.environ.pop("HDFS_NAMENODE_PORT", None)
            os.environ.pop("HDFS_USER", None)

    def test_config_validation(self):
        """Test config validation"""
        # Test invalid port
        with pytest.raises(ValueError, match=".*port.*"):
            HDFSConfig(
                namenode_host="localhost",
                namenode_port=-1,
                user="testuser",
            )

        # Test empty host
        with pytest.raises(ValueError, match=".*host.*"):
            HDFSConfig(
                namenode_host="",
                namenode_port=9000,
                user="testuser",
            )

    def test_config_string_representation(self):
        """Test config string representation"""
        config = HDFSConfig(
            namenode_host="localhost",
            namenode_port=9000,
            user="testuser",
        )

        config_str = str(config)
        assert "localhost" in config_str
        assert "9000" in config_str
        assert "testuser" in config_str
