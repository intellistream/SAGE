"""
SAGE Test Configuration

This file defines the test structure and configuration for the SAGE project.
Tests are organized by module to enable targeted testing based on git diff.
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 测试模块映射
TEST_MODULE_MAP = {
    # Core module tests
    "sage/core/": "sage/core/tests/",
    
    # Service module tests  
    "sage/service/memory/": "sage/service/memory/tests/",
    "sage/service/": "sage/service/tests/",
    
    # Runtime module tests
    "sage/runtime/": "sage/runtime/tests/",
    
    # Utils module tests
    "sage/utils/": "sage/utils/tests/",
    
    # Function tests (more specific mapping)
    "sage/core/function/": "sage/core/function/tests/",
    
    # Frontend tests
    "frontend/": "frontend/tests/",
    
    # CLI tests (if any)
    "sage/cli/": "sage/cli/tests/",  # 如果需要的话
    
    # Jobmanager tests
    "sage/jobmanager/": "sage/jobmanager/tests/",  # 如果需要的话
}

# 测试类别定义
TEST_CATEGORIES = {
    "unit": {
        "description": "Unit tests for individual components",
        "patterns": ["test_*.py", "*_test.py"],
        "timeout": 30,
    },
    "integration": {
        "description": "Integration tests for component interactions", 
        "patterns": ["integration_*.py", "*_integration.py"],
        "timeout": 120,
    },
    "e2e": {
        "description": "End-to-end tests for complete workflows",
        "patterns": ["e2e_*.py", "*_e2e.py"],
        "timeout": 300,
    }
}

# 测试依赖
TEST_DEPENDENCIES = {
    "sage/core/tests/": ["sage.core"],
    "sage/service/tests/": ["sage.service", "sage.core"],
    "sage/service/memory/tests/": ["sage.service.memory", "sage.core"],
    "sage/runtime/tests/": ["sage.runtime", "sage.core"],
    "sage/utils/tests/": ["sage.utils"],
    "sage/core/function/tests/": ["sage.core.function", "sage.core"],
    "frontend/tests/": ["frontend"],
}

def get_test_modules_for_changed_files(changed_files):
    """
    根据git diff中变更的文件，确定需要运行的测试模块
    
    Args:
        changed_files: 变更文件列表
        
    Returns:
        需要运行的测试模块路径列表
    """
    test_modules = set()
    
    for changed_file in changed_files:
        # 标准化路径
        changed_file = changed_file.replace("\\", "/")
        
        # 查找匹配的测试模块
        for source_pattern, test_path in TEST_MODULE_MAP.items():
            if changed_file.startswith(source_pattern):
                test_modules.add(test_path)
                
                # 添加依赖的测试模块
                if test_path in TEST_DEPENDENCIES:
                    for dep in TEST_DEPENDENCIES[test_path]:
                        dep_path = dep.replace(".", "/") + "/tests/"
                        if (PROJECT_ROOT / dep_path).exists():
                            test_modules.add(dep_path)
    
    return list(test_modules)

def get_all_test_modules():
    """获取所有测试模块"""
    return list(TEST_MODULE_MAP.values())

if __name__ == "__main__":
    # 测试配置
    print("SAGE Test Configuration")
    print("=" * 50)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Test modules: {len(TEST_MODULE_MAP)}")
    
    for source, test in TEST_MODULE_MAP.items():
        test_path = PROJECT_ROOT / test
        exists = "✅" if test_path.exists() else "❌"
        print(f"  {source} → {test} {exists}")
