"""
Pytest配置和共享fixtures
======================
"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_dir():
    """提供临时目录的fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture 
def config_dir(temp_dir):
    """提供配置目录的fixture"""
    config_dir = temp_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def sample_config():
    """提供示例配置的fixture"""
    return {
        "app": {
            "name": "test_app",
            "version": "1.0.0",
            "debug": True
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "test_db"
        },
        "logging": {
            "level": "INFO",
            "handlers": ["console", "file"]
        }
    }


@pytest.fixture
def log_base_folder(temp_dir):
    """提供日志基础文件夹的fixture"""
    log_dir = temp_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return str(log_dir)
