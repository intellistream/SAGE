#!/usr/bin/env python3
"""
展示重构后序列化模块的使用示例
"""
import sys
sys.path.insert(0, '/api-rework')

def demo_basic_usage():
    """展示基本使用方法"""
    print("📝 基本使用示例")
    print("=" * 50)
    
    # 方式1: 使用便捷函数（推荐）
    from sage.utils.serialization import serialize_object, deserialize_object
    
    data = {
        'name': 'SAGE Framework',
        'version': '2.0',
        'features': ['serialization', 'ray_support', 'modular_design']
    }
    
    # 序列化
    serialized = serialize_object(data)
    print(f"✅ 序列化成功，大小: {len(serialized)} bytes")
    
    # 反序列化
    restored = deserialize_object(serialized)
    print(f"✅ 反序列化成功: {restored['name']}")
    

def demo_file_operations():
    """展示文件操作"""
    print("\n📁 文件操作示例")
    print("=" * 50)
    
    from sage.utils.serialization import save_object_state, load_object_from_file
    import tempfile
    import os
    
    # 创建测试对象
    class MyApp:
        def __init__(self):
            self.config = {'debug': True, 'port': 8080}
            self.state = 'running'
    
    app = MyApp()
    
    # 保存到临时文件
    temp_file = os.path.join(tempfile.gettempdir(), 'sage_demo.pkl')
    save_object_state(app, temp_file)
    print(f"✅ 对象状态已保存到: {temp_file}")
    
    # 从文件加载
    loaded_app = load_object_from_file(temp_file)
    print(f"✅ 从文件加载成功: {loaded_app.config}")
    
    # 清理
    os.remove(temp_file)
    

def demo_ray_trimming():
    """展示Ray对象清理"""
    print("\n🚀 Ray对象清理示例")
    print("=" * 50)
    
    from sage.utils.serialization import trim_object_for_ray, RayObjectTrimmer
    import threading
    
    # 模拟一个包含不可序列化内容的复杂对象
    class ComplexTransformation:
        def __init__(self):
            self.name = "DataProcessor"
            self.config = {'batch_size': 100}
            self.logger = "fake_logger_object"  # 会被清理
            self.env = "environment_reference"  # 会被清理
            self.thread = threading.Thread()   # 会被清理
            self.data = [1, 2, 3, 4, 5]
    
    transform = ComplexTransformation()
    
    # 方式1: 通用清理
    cleaned = trim_object_for_ray(transform)
    print(f"✅ 通用清理完成，保留属性: {list(cleaned.__dict__.keys())}")
    
    # 方式2: 专用清理器
    cleaned_specialized = RayObjectTrimmer.trim_transformation_for_ray(transform)
    print(f"✅ 专用清理完成，保留属性: {list(cleaned_specialized.__dict__.keys())}")
    
    # 方式3: 自定义排除列表
    cleaned_custom = trim_object_for_ray(transform, exclude=['thread', 'env'])
    print(f"✅ 自定义清理完成，保留属性: {list(cleaned_custom.__dict__.keys())}")


def demo_advanced_features():
    """展示高级功能"""
    print("\n🔧 高级功能示例")
    print("=" * 50)
    
    from sage.utils.serialization import UniversalSerializer
    
    # 创建有自定义序列化配置的类
    class ConfigurableClass:
        # 类级别配置：排除某些属性
        __state_exclude__ = ['temp_data', 'cache']
        
        def __init__(self):
            self.important_data = "must_serialize"
            self.temp_data = "should_not_serialize"
            self.cache = {}
            self.config = {'setting': 'value'}
    
    obj = ConfigurableClass()
    
    # 使用类的自定义配置
    serialized = UniversalSerializer.serialize_object(obj)
    restored = UniversalSerializer.deserialize_object(serialized)
    
    print(f"✅ 自定义配置序列化:")
    print(f"   原始属性: {list(obj.__dict__.keys())}")
    print(f"   恢复属性: {list(restored.__dict__.keys())}")
    
    # 动态排除属性
    serialized_custom = UniversalSerializer.serialize_object(obj, exclude=['config'])
    restored_custom = UniversalSerializer.deserialize_object(serialized_custom)
    
    print(f"✅ 动态排除序列化:")
    print(f"   恢复属性: {list(restored_custom.__dict__.keys())}")


def demo_error_handling():
    """展示错误处理"""
    print("\n⚠️ 错误处理示例")
    print("=" * 50)
    
    from sage.utils.serialization import SerializationError, serialize_object
    
    try:
        # 尝试序列化一个可能有问题的对象
        import threading
        problematic_obj = {
            'safe_data': 'ok',
            'thread': threading.Thread()  # 这会被自动清理
        }
        
        result = serialize_object(problematic_obj)
        print("✅ 问题对象被自动清理并序列化成功")
        
    except SerializationError as e:
        print(f"❌ 序列化错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")


def demo_backward_compatibility():
    """展示向后兼容性"""
    print("\n🔄 向后兼容性示例")
    print("=" * 50)
    
    # 这些是旧版本的函数名，仍然可用
    from sage.utils.serialization import pack_object, unpack_object
    
    data = {'legacy': 'support'}
    
    packed = pack_object(data)
    unpacked = unpack_object(packed)
    
    print(f"✅ 旧版本函数仍然可用: {unpacked}")


if __name__ == "__main__":
    print("🎯 SAGE 序列化模块使用示例")
    print("=" * 60)
    
    demo_basic_usage()
    demo_file_operations()
    demo_ray_trimming()
    demo_advanced_features()
    demo_error_handling()
    demo_backward_compatibility()
    
    print("\n" + "=" * 60)
    print("🎉 所有示例运行完成！")
    print("📚 更多信息请查看 REFACTOR_GUIDE.md")
