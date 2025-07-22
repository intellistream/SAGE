import logging
import pytest
from dotenv import load_dotenv
import os
import tempfile

from sage_core.api.local_environment import LocalEnvironment
from sage_libs.io.sink import TerminalSink
from sage_libs.io.source import FileSource
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging
from sage_utils.serialization.dill_serializer import (
    serialize_object, deserialize_object, pack_object, unpack_object,
    save_object_state, load_object_state
)


@pytest.fixture(scope="function")
def config():
    configure_logging(level=logging.INFO)
    load_dotenv(override=False)
    cfg = load_config("config_mixed.yaml")
    api_key = os.environ.get("VLLM_API_KEY")
    if api_key:
        cfg.setdefault("generator", {})["api_key"] = api_key
    return cfg


@pytest.fixture(scope="function")
def env():
    env = LocalEnvironment()
    env.set_memory(config=None)
    # return env
    yield env
    # teardown: 主动清理资源
    try:
        if hasattr(env, "executor"):
            env.executor.shutdown(wait=False)
        if hasattr(env, "actors"):
            for a in env.actors:
                a.kill()
    except Exception as e:
        logging.warning(f"env teardown failed: {e}")


def test_env_serialization_and_reconstruction(env, config):
    """测试环境的序列化和重建"""
    
    # 1. 创建一个完整的pipeline
    query_stream = (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
        .sink(TerminalSink, config["sink"])
    )
    
    # 调试信息：检查pipeline是否正确构建
    logging.info(f"Original pipeline length: {len(env._pipeline)}")
    for i, trans in enumerate(env._pipeline):
        logging.info(f"Transformation {i}: {type(trans).__name__} - {trans.basename}")
    
    # 添加一些自定义属性来测试序列化
    env.custom_metadata = {
        "created_at": "2025-01-01",
        "version": "1.0.0",
        "description": "Test environment for serialization"
    }
    env.processing_stats = {
        "total_processed": 0,
        "errors": 0,
        # "last_run": None
    }
    
    # 2. 序列化环境
    logging.info("Serializing environment...")
    serialized_data = serialize_object(env)
    
    # # 验证序列化数据包含必要信息
    # assert '__class_path__' in serialized_data
    # assert '__attributes__' in serialized_data
    # assert serialized_data['__class_path__'] == 'sage_core.api.env.LocalEnvironment'
    
    # attributes = serialized_data['__attributes__']
    # assert 'name' in attributes
    # assert 'config' in attributes
    # assert 'platform' in attributes
    # assert '_pipeline' in attributes
    # assert 'custom_metadata' in attributes
    # assert 'processing_stats' in attributes
    
    # # 调试信息：检查序列化后的pipeline
    # pipeline_data = attributes['_pipeline']
    # logging.info(f"Serialized pipeline length: {len(pipeline_data)}")
    # for i, trans_data in enumerate(pipeline_data):
    #     if isinstance(trans_data, dict) and '__class_path__' in trans_data:
    #         logging.info(f"Serialized transformation {i}: {trans_data['__class_path__']}")
    
    # # 验证pipeline中的transformations也被序列化
    # assert len(pipeline_data) == 5, f"Expected 5 transformations, got {len(pipeline_data)}"
    
    # logging.info(f"Environment serialized successfully with {len(attributes)} attributes")
    # logging.info(f"Pipeline contains {len(pipeline_data)} transformations")
    
    # 3. 重建环境
    logging.info("Reconstructing environment from serialized data...")
    restored_env = deserialize_object(serialized_data)
    print(f"Restored environment name: {restored_env.name}")
    # 调试信息：检查恢复后的pipeline
    logging.info(f"Restored pipeline length: {len(restored_env._pipeline)}")
    for i, trans in enumerate(restored_env._pipeline):
        logging.info(f"Restored transformation {i}: {type(trans).__name__} - {trans.basename}")
    
    # 验证环境基本信息
    assert restored_env.name == "local_environment"
    assert restored_env.platform == env.platform
    assert restored_env.config == env.config
    assert restored_env.custom_metadata == env.custom_metadata
    print( restored_env.processing_stats)
    assert restored_env.processing_stats == env.processing_stats
    
    # 验证pipeline被正确重建
    assert len(restored_env._pipeline) == len(env._pipeline)
    
    # 验证每个transformation的基本信息
    for i, (original, restored) in enumerate(zip(env._pipeline, restored_env._pipeline)):
        assert type(original) == type(restored)
        assert original.basename == restored.basename
        assert original.parallelism == restored.parallelism
        assert original.function_class == restored.function_class
        logging.info(f"Transformation {i}: {original.basename} restored successfully")
    
    # ... 其余测试代码保持不变


def test_env_binary_serialization(env, config):
    """测试环境的二进制序列化和重建"""
    
    # 创建pipeline
    query_stream = (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .print()
    )
    
    # 添加测试数据
    env.test_data = {
        "numbers": [1, 2, 3, 4, 5],
        "settings": {"batch_size": 100, "timeout": 30}
    }
    
    # 二进制序列化
    logging.info("Binary serializing environment...")
    packed_data = pack_object(env)
    
    assert isinstance(packed_data, bytes)
    assert len(packed_data) > 0
    
    logging.info(f"Environment packed to {len(packed_data)} bytes")
    
    # 二进制反序列化
    logging.info("Unpacking environment from binary data...")
    restored_env = unpack_object(packed_data)
    
    # 验证重建结果
    assert restored_env.test_data == env.test_data
    assert len(restored_env._pipeline) == len(env._pipeline)
    
    # 测试运行
    restored_env.set_memory(config=None)
    restored_env.submit()
    
    try:
        restored_env.run_once()
        logging.info("Binary restored environment executed successfully")
        restored_env.stop()
    except Exception as e:
        pytest.fail(f"Binary restored environment execution failed: {e}")
    
    restored_env.close()


def test_env_file_persistence(env, config):
    """测试环境的文件持久化"""
    
    # 创建简单的pipeline
    query_stream = (env
        .from_source(FileSource, config["source"])
        .map(QAPromptor, config["promptor"])
        .print()
    )
    
    # 添加持久化数据
    env.persistent_data = {
        "session_id": "test_session_123",
        "user_preferences": {"theme": "dark", "language": "en"},
        "cache_settings": {"enabled": True, "size": 1000}
    }
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        logging.info(f"Saving environment state to {tmp_path}")
        save_object_state(env, tmp_path)
        
        # 验证文件存在
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0
        
        # 创建新环境并加载状态
        new_env = LocalEnvironment("new_env")
        new_env.set_memory(config=None)
        
        logging.info(f"Loading environment state from {tmp_path}")
        load_success = load_object_state(new_env, tmp_path)
        
        assert load_success == True
        assert new_env.persistent_data == env.persistent_data
        assert len(new_env.pipeline) == len(env._pipeline)
        
        # 测试加载状态后的运行
        new_env.submit()
        
        try:
            new_env.run_once()
            logging.info("Environment with loaded state executed successfully")
            new_env.stop()
        except Exception as e:
            pytest.fail(f"Environment with loaded state execution failed: {e}")
        
        new_env.close()
        
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

# 创建一个自定义的环境类，带有序列化配置
class CustomTestEnvironment(LocalEnvironment):
    # __state_include__ = ['name', 'config', 'platform', '_pipeline', 'important_data']
    
    def __init__(self, name: str = "custom_test_env", config: dict = None):
        super().__init__(name, config)
        self.important_data = "must be serialized"
        self.temp_data = "should be ignored"
        self.secret_key = "confidential"


def test_env_serialization_with_custom_attributes(env, config):
    """测试带有自定义序列化配置的环境"""
    

    
    # 创建自定义环境
    custom_env = CustomTestEnvironment("custom_test")
    custom_env.set_memory(config=None)
    
    # 创建pipeline
    query_stream = (custom_env
        .from_source(FileSource, config["source"])
        .print()
    )
    
    # 序列化
    serialized_data = serialize_object(custom_env)
    # attributes = serialized_data['__attributes__']
    
    # # 验证只有include的属性被序列化
    # assert 'important_data' in attributes
    # assert 'temp_data' not in attributes
    # assert 'secret_key' not in attributes
    
    # 重建
    restored_env = deserialize_object(serialized_data)
    
    assert restored_env.important_data == "must be serialized"
    # assert not hasattr(restored_env, 'temp_data')
    # assert not hasattr(restored_env, 'secret_key')
    assert hasattr(restored_env, 'is_running')
    
    # 测试运行
    restored_env.set_memory(config=None)
    restored_env.submit()
    
    try:
        restored_env.run_once()
        logging.info("Custom environment executed successfully")
        restored_env.stop()
    except Exception as e:
        pytest.fail(f"Custom environment execution failed: {e}")
    
    restored_env.close()
    custom_env.close()


def test_env_serialization_error_handling():
    """测试序列化过程中的错误处理"""
    
    # 测试无效数据的反序列化
    invalid_data = {'invalid': 'data'}
    
    with pytest.raises(Exception):
        deserialize_object(invalid_data)
    
    # 测试不存在的类路径
    invalid_class_data = {
        '__class_path__': 'non.existent.Class',
        '__attributes__': {}
    }
    
    with pytest.raises(Exception):
        deserialize_object(invalid_class_data)
    
    logging.info("Error handling tests completed successfully")


if __name__ == "__main__":
    # test_env_serialization_with_custom_attributes(env(), config())
    # 运行测试
    pytest.main([__file__, "-v"])