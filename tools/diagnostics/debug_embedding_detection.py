#!/usr/bin/env python3
"""
调试embedding模型检测逻辑
"""

import os
import sys
sys.path.append('/home/shuhao/SAGE')

import unittest.mock

def mock_model_load_failure(*args, **kwargs):
    raise Exception("Network error: Unable to download model")

# 覆盖AutoTokenizer和AutoModel的from_pretrained方法
with unittest.mock.patch('transformers.AutoTokenizer.from_pretrained', side_effect=mock_model_load_failure), \
     unittest.mock.patch('transformers.AutoModel.from_pretrained', side_effect=mock_model_load_failure):
    
    from sage.middleware.components.neuromem.memory_manager import MemoryManager

    def debug_embedding_model():
        print("🔍 调试embedding模型检测逻辑")
        
        manager = MemoryManager()
        config = {"name": "debug_collection", "backend_type": "VDB", "description": "调试集合"}
        vdb_collection = manager.create_collection(config)

        index_config = {
            "name": "debug_index",
            "embedding_model": "default",
            "dim": 384,
            "backend_type": "FAISS",
            "description": "调试索引",
            "index_parameter": {},
        }
        vdb_collection.create_index(config=index_config)

        # 获取embedding模型并检查所有属性
        embedding_model = vdb_collection.embedding_model_factory.get("default")
        
        print(f"🔬 Embedding模型类型: {type(embedding_model)}")
        print(f"🔬 Embedding模型属性:")
        for attr in dir(embedding_model):
            if not attr.startswith('_'):
                try:
                    value = getattr(embedding_model, attr)
                    print(f"  - {attr}: {value}")
                except:
                    print(f"  - {attr}: <无法访问>")
        
        # 检查method属性
        if hasattr(embedding_model, 'method'):
            print(f"✅ method属性: {embedding_model.method}")
        else:
            print("❌ 没有method属性")
            
        if hasattr(embedding_model, 'init_method'):
            print(f"✅ init_method属性: {embedding_model.init_method}")
        else:
            print("❌ 没有init_method属性")
        
        # 检查kwargs中的embed_model
        if hasattr(embedding_model, 'kwargs') and 'embed_model' in embedding_model.kwargs:
            embed_model = embedding_model.kwargs['embed_model']
            print(f"🔬 kwargs中的embed_model类型: {type(embed_model)}")
            if hasattr(embed_model, 'method_name'):
                print(f"✅ embed_model.method_name: {embed_model.method_name}")
            else:
                print("❌ embed_model没有method_name属性")
        
        manager.delete_collection("debug_collection")

    debug_embedding_model()