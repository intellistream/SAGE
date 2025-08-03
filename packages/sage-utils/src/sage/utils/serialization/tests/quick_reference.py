"""
测试快速参考和使用指南
"""

def run_all_tests():
    """
    运行所有序列化模块测试
    
    使用方法:
        python sage/utils/serialization/tests/run_tests.py
    """
    pass

def run_single_test():
    """
    运行单个测试模块
    
    使用方法:
        python sage/utils/serialization/tests/run_tests.py test_exceptions
        python sage/utils/serialization/tests/run_tests.py test_config
        python sage/utils/serialization/tests/run_tests.py test_preprocessor
        python sage/utils/serialization/tests/run_tests.py test_universal_serializer
        python sage/utils/serialization/tests/run_tests.py test_ray_trimmer
        python sage/utils/serialization/tests/run_tests.py test_main_api
    """
    pass

def run_with_pytest():
    """
    使用pytest直接运行测试
    
    使用方法:
        
        # 运行所有测试
        python -m pytest sage/utils/serialization/tests/ -v
        
        # 运行单个测试文件
        python -m pytest sage/utils/serialization/tests/test_exceptions.py -v
        
        # 运行特定测试类
        python -m pytest sage/utils/serialization/tests/test_ray_trimmer.py::TestRayObjectTrimmer -v
        
        # 运行特定测试方法
        python -m pytest sage/utils/serialization/tests/test_universal_serializer.py::TestUniversalSerializer::test_serialize_complex_object -v --tb=long
    """
    pass

# 测试状态
TEST_STATUS = {
    'test_exceptions.py': '✅ 6/6 通过',
    'test_config.py': '✅ 9/9 通过', 
    'test_preprocessor.py': '✅ 35/35 通过',
    'test_universal_serializer.py': '❌ 22/24 通过 (2个失败)',
    'test_ray_trimmer.py': '❌ 17/20 通过 (3个失败)',
    'test_main_api.py': '✅ 19/19 通过'
}

KNOWN_ISSUES = [
    "test_serialize_complex_object - 本地类的isinstance检查失败",
    "test_serialize_empty_object - 空类序列化类型不匹配", 
    "test_trim_object_with_include_list - include列表逻辑需要改进",
    "test_trim_for_remote_call_deep - 深度清理递归问题",
    "test_trim_operator_for_ray - __weakref__属性过滤问题"
]
