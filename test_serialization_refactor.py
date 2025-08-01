#!/usr/bin/env python3
"""
测试重构后的序列化模块
"""
import sys
import os
sys.path.insert(0, '/api-rework')

def test_imports():
    """测试所有模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        from sage.utils.serialization.exceptions import SerializationError
        print("✅ exceptions.py 导入成功")
    except Exception as e:
        print(f"❌ exceptions.py 导入失败: {e}")
    
    try:
        from sage.utils.serialization.config import BLACKLIST, ATTRIBUTE_BLACKLIST, SKIP_VALUE
        print(f"✅ config.py 导入成功 (BLACKLIST有 {len(BLACKLIST)} 项)")
    except Exception as e:
        print(f"❌ config.py 导入失败: {e}")
    
    try:
        from sage.utils.serialization.preprocessor import preprocess_for_dill, postprocess_from_dill
        print("✅ preprocessor.py 导入成功")
    except Exception as e:
        print(f"❌ preprocessor.py 导入失败: {e}")
    
    try:
        from sage.utils.serialization.universal_serializer import UniversalSerializer
        print("✅ universal_serializer.py 导入成功")
    except Exception as e:
        print(f"❌ universal_serializer.py 导入失败: {e}")
    
    try:
        from sage.utils.serialization.ray_trimmer import RayObjectTrimmer, trim_object_for_ray
        print("✅ ray_trimmer.py 导入成功")
    except Exception as e:
        print(f"❌ ray_trimmer.py 导入失败: {e}")


def test_basic_functionality():
    """测试基本功能"""
    print("\n🔍 测试基本功能...")
    
    try:
        # 检查dill是否可用
        import dill
        print(f"✅ dill 库可用，版本: {dill.__version__}")
    except ImportError:
        print("❌ dill 库不可用，将跳过序列化测试")
        return
    
    try:
        from sage.utils.serialization import serialize_object, deserialize_object
        
        # 测试基础序列化
        test_data = {
            'string': 'hello world',
            'number': 42,
            'list': [1, 2, 3],
            'nested': {'key': 'value'}
        }
        
        serialized = serialize_object(test_data)
        deserialized = deserialize_object(serialized)
        
        if deserialized == test_data:
            print("✅ 基础序列化/反序列化测试通过")
        else:
            print(f"❌ 序列化结果不匹配: {deserialized} != {test_data}")
            
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_ray_trimming():
    """测试Ray对象清理功能"""
    print("\n🔍 测试Ray对象清理...")
    
    try:
        from sage.utils.serialization import trim_object_for_ray
        
        # 创建一个包含不可序列化内容的测试对象
        import threading
        
        class TestObject:
            def __init__(self):
                self.data = "safe data"
                self.logger = "fake logger"  # 会被过滤
                self.thread = threading.Thread()  # 会被过滤
                self.number = 42
        
        test_obj = TestObject()
        cleaned_obj = trim_object_for_ray(test_obj)
        
        if cleaned_obj is not None:
            print("✅ Ray对象清理基础功能正常")
            if hasattr(cleaned_obj, 'data') and not hasattr(cleaned_obj, 'logger'):
                print("✅ 对象属性过滤功能正常")
            else:
                print("⚠️ 对象属性过滤可能有问题")
        else:
            print("❌ Ray对象清理返回None")
            
    except Exception as e:
        print(f"❌ Ray对象清理测试失败: {e}")


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n🔍 测试向后兼容性...")
    
    try:
        # 测试旧的函数名
        from sage.utils.serialization import pack_object, unpack_object
        
        test_data = {'test': 'backward compatibility'}
        packed = pack_object(test_data)
        unpacked = unpack_object(packed)
        
        if unpacked == test_data:
            print("✅ 向后兼容性测试通过")
        else:
            print("❌ 向后兼容性测试失败")
            
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")


if __name__ == "__main__":
    print("🚀 开始测试重构后的序列化模块\n")
    
    test_imports()
    test_basic_functionality()
    test_ray_trimming()
    test_backward_compatibility()
    
    print("\n✨ 测试完成!")
