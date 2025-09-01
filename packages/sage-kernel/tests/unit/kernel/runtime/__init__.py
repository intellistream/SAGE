"""
Test suite for sage.kernels.runtime module

This module contains comprehensive unit and integration tests
for the SAGE runtime components including:

- Dispatcher: Task and service execution management
- TaskContext & ServiceContext: Runtime context management  
- Distributed components: Ray integration and actor wrapping
- Factory components: Task and service creation
- Serialization: Universal serialization utilities
- Communication: Queue and routing components
- Task execution: Local and remote task implementations
- Service execution: Service task implementations

Test Organization:
- Unit tests: Fast, isolated tests for individual components
- Integration tests: Tests for component interactions
- Performance tests: Benchmarks and stress tests
- Edge case tests: Error conditions and boundary cases

Markers:
- @pytest.mark.unit: Unit tests (fast, no external dependencies)
- @pytest.mark.integration: Integration tests (moderate speed)
- @pytest.mark.slow: Performance/stress tests (slow execution)
- @pytest.mark.external: Tests requiring external services (Ray, etc.)

Usage:
    # Run all runtime tests
    pytest tests/runtime/
    
    # Run only unit tests
    pytest tests/runtime/ -m unit
    
    # Run tests excluding slow ones
    pytest tests/runtime/ -m "not slow"
    
    # Run specific component tests
    pytest tests/runtime/test_dispatcher.py
    pytest tests/runtime/distributed/
    pytest tests/runtime/factory/
"""

def _load_version():
    """从项目根目录动态加载版本信息"""
    from pathlib import Path
    
    # 计算到项目根目录的路径 (测试文件位于: packages/sage-kernel/tests/unit/kernel/runtime/)
    current_file = Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent.parent.parent  # 向上5层到项目根目录
    version_file = root_dir / "_version.py"
    
    if version_file.exists():
        version_globals = {}
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                exec(f.read(), version_globals)
            return version_globals.get('__version__', '0.1.4')
        except Exception:
            pass
    
    # 默认值（找不到_version.py时使用）
    return '0.1.4'

__version__ = _load_version()
