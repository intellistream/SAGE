#!/usr/bin/env python3
"""
SimpleRemoteEnvironment 测试脚本
测试简化版远程环境的序列化和发送功能
"""

import logging
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 导入SAGE的序列化工具和SimpleRemoteEnvironment
try:
    from sage.utils.serialization.dill_serializer import serialize_object, deserialize_object
    from simple_remote_environment import SimpleRemoteEnvironment
    print("✅ Successfully imported SAGE components")
    has_sage_imports = True
except ImportError as e:
    print(f"❌ Could not import SAGE components: {e}")
    has_sage_imports = False
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_functionality():
    """测试基本功能"""
    print("\n=== 测试基本功能 ===")
    
    # 1. 创建远程环境
    env = SimpleRemoteEnvironment(
        name="test_env",
        config={"batch_size": 32, "timeout": 10},
        jobmanager_port=19002  # 使用测试服务器端口
    )
    
    print(f"✅ 创建环境: {env}")
    
    # 2. 添加到流水线
    env.add_to_pipeline("data_loader")
    env.add_to_pipeline("model_processor") 
    env.add_to_pipeline("output_writer")
    
    print(f"✅ 流水线长度: {len(env.pipeline)}")
    
    # 3. 获取环境信息
    info = env.get_environment_info()
    print(f"✅ 环境信息: {info}")
    
    return env

def test_serialization():
    """测试序列化功能"""
    print("\n=== 测试序列化功能 ===")
    
    # 创建测试环境
    env = SimpleRemoteEnvironment(
        name="serialize_test_env",
        config={"model": "bert", "max_length": 512}
    )
    env.add_to_pipeline("tokenizer")
    env.add_to_pipeline("encoder")
    
    try:
        # 序列化环境
        serialized_data = env.serialize_environment()
        print(f"✅ 序列化成功: {len(serialized_data)} bytes")
        
        # 反序列化测试
        deserialized_env = deserialize_object(serialized_data)
        print(f"✅ 反序列化成功: {deserialized_env}")
        
        # 验证数据完整性
        assert deserialized_env.name == env.name
        assert deserialized_env.config == env.config
        assert deserialized_env.platform == env.platform
        assert len(deserialized_env.pipeline) == len(env.pipeline)
        
        print("✅ 数据完整性验证通过")
        
        # 检查排除的属性
        assert deserialized_env.client is None or deserialized_env.client == env.client
        assert deserialized_env.jobmanager is None or deserialized_env.jobmanager == env.jobmanager
        print("✅ 属性排除验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 序列化测试失败: {e}")
        return False

def test_send_to_server():
    """测试发送到服务器"""
    print("\n=== 测试发送到服务器 ===")
    print("⚠️  请确保测试服务器正在运行：python3 test_remote_environment_server.py --mode server")
    
    try:
        # 创建测试环境
        env = SimpleRemoteEnvironment(
            name="server_test_env",
            config={"test": True, "version": "1.0"},
            jobmanager_port=19002  # 确保使用正确的测试端口
        )
        env.add_to_pipeline("preprocessor")
        env.add_to_pipeline("model")
        env.add_to_pipeline("postprocessor")
        
        # 发送到服务器
        response = env.send_to_jobmanager()
        print(f"✅ 服务器响应: {response}")
        
        # 检查响应状态
        if response.get("status") == "success":
            print("✅ 服务器成功接收并验证了环境")
            return True
        else:
            print(f"❌ 服务器返回错误: {response.get('message', 'Unknown error')}")
            return False
            
    except ConnectionRefusedError:
        print("❌ 无法连接到服务器，请确保测试服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 发送测试失败: {e}")
        return False

def test_with_exclusions():
    """测试带排除属性的序列化"""
    print("\n=== 测试属性排除功能 ===")
    
    try:
        # 创建环境
        env = SimpleRemoteEnvironment(
            name="exclusion_test_env",
            config={"sensitive_data": "should_be_excluded"}
        )
        
        # 添加一些测试数据
        env.test_attribute = "should_be_included"
        env.sensitive_attribute = "should_be_excluded"
        
        # 使用排除列表进行序列化
        serialized_data = env.serialize_environment(
            exclude=["sensitive_attribute", "config"]
        )
        
        # 反序列化并检查
        deserialized_env = deserialize_object(serialized_data)
        
        # 验证排除效果
        assert hasattr(deserialized_env, "test_attribute")
        assert not hasattr(deserialized_env, "sensitive_attribute") or getattr(deserialized_env, "sensitive_attribute", None) is None
        
        print("✅ 属性排除功能正常工作")
        return True
        
    except Exception as e:
        print(f"❌ 属性排除测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("SimpleRemoteEnvironment 测试")
    print("=" * 60)
    
    # 测试结果统计
    test_results = []
    
    # 基本功能测试
    try:
        test_basic_functionality()
        test_results.append(("基本功能", True))
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        test_results.append(("基本功能", False))
    
    # 序列化测试
    serialization_result = test_serialization()
    test_results.append(("序列化功能", serialization_result))
    
    # 属性排除测试
    exclusion_result = test_with_exclusions()
    test_results.append(("属性排除", exclusion_result))
    
    # 服务器发送测试
    server_result = test_send_to_server()
    test_results.append(("服务器发送", server_result))
    
    # 打印测试结果摘要
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} : {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return True
    else:
        print(f"⚠️  有 {total - passed} 个测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
