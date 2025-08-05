# SAGE Core API Tests

This directory contains comprehensive unit tests for the `sage.core.api` module, following the testing organization structure outlined in the project issue.

## Test Structure

The test organization follows the source code structure exactly:

```
tests/core/api/
├── conftest.py                    # Shared test configuration and fixtures
├── test_base_environment.py       # Tests for base_environment.py
├── test_local_environment.py      # Tests for local_environment.py
├── test_remote_environment.py     # Tests for remote_environment.py
├── test_datastream.py             # Tests for datastream.py
└── test_connected_streams.py      # Tests for connected_streams.py
```

## Test Categories

All tests are properly marked with pytest markers:
- 错误处理和恢复机制

### `test_remote_env_serialization.py`  
测试远程环境的序列化功能：
- 环境配置的序列化和反序列化
- 跨进程/跨节点的环境状态传输
- 序列化数据的完整性验证

### `test_remote_environment_server.py`
测试远程环境服务器功能：
- 远程环境服务器的启动和停止
- 客户端与服务器的通信协议
- 多客户端并发访问测试

## 运行测试

```bash
# 运行所有API测试
python -m pytest tests/core/api/

# 运行特定测试文件
python -m pytest tests/core/api/test_new_remote_env.py
```

## 测试环境要求

- Python 3.8+
- pytest
- 网络连接（用于远程环境测试）
- Ray 集群（可选，用于分布式测试）
