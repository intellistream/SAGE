#!/usr/bin/env python3
"""
分析MockEmbedder生成的向量相似度
"""

import os
import sys
sys.path.append('/home/shuhao/SAGE')

import unittest.mock
import numpy as np

def mock_model_load_failure(*args, **kwargs):
    raise Exception("Network error: Unable to download model")

# 覆盖AutoTokenizer和AutoModel的from_pretrained方法  
with unittest.mock.patch('transformers.AutoTokenizer.from_pretrained', side_effect=mock_model_load_failure), \
     unittest.mock.patch('transformers.AutoModel.from_pretrained', side_effect=mock_model_load_failure):
    
    from sage.middleware.utils.embedding.embedding_api import apply_embedding_model

    def analyze_mock_similarity():
        print("🔬 分析MockEmbedder向量相似度")
        
        # 创建embedding模型（会回退到MockEmbedder）
        embedding_model = apply_embedding_model("default")
        
        # 生成测试向量
        text1 = "想吃广东菜"
        text2 = "广东菜"
        
        vec1 = embedding_model.encode(text1)
        vec2 = embedding_model.encode(text2)
        
        # 转换为numpy数组
        if hasattr(vec1, "detach"):
            vec1 = vec1.detach().cpu().numpy()
        if hasattr(vec2, "detach"):
            vec2 = vec2.detach().cpu().numpy()
        
        vec1 = np.array(vec1, dtype=np.float32)
        vec2 = np.array(vec2, dtype=np.float32)
        
        # L2归一化
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)
        
        # 计算内积相似度
        similarity = np.dot(vec1_norm, vec2_norm)
        
        print(f"📊 文本1: '{text1}'")
        print(f"📊 文本2: '{text2}'")
        print(f"📊 向量1 norm: {np.linalg.norm(vec1)}")
        print(f"📊 向量2 norm: {np.linalg.norm(vec2)}")
        print(f"📊 归一化后内积相似度: {similarity}")
        print(f"📊 建议阈值: {max(0.001, similarity - 0.1)}")
        
        return float(similarity)

    similarity = analyze_mock_similarity()