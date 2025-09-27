#!/usr/bin/env python3
"""
CICD环境中的embedding模型预缓存脚本
"""

import os
import sys
from pathlib import Path

def cache_embedding_models():
    """缓存CICD环境需要的embedding模型"""
    print("🔄 开始缓存embedding模型...")
    
    try:
        from transformers import AutoTokenizer, AutoModel
        
        # 默认使用的模型
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        
        print(f"📥 下载并缓存模型: {model_name}")
        
        # 下载tokenizer
        print("  - 下载tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # 下载模型
        print("  - 下载模型...")
        model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        
        print("✅ 模型缓存完成!")
        
        # 验证模型可用性
        print("🧪 验证模型可用性...")
        test_text = "测试文本"
        inputs = tokenizer(test_text, return_tensors="pt", padding=True, truncation=True)
        outputs = model(**inputs)
        
        print(f"  - 模型输出维度: {outputs.last_hidden_state.shape}")
        print("✅ 模型验证通过!")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型缓存失败: {e}")
        return False

def check_model_availability():
    """检查模型是否已经可用"""
    try:
        from transformers import AutoTokenizer, AutoModel
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        
        print(f"🔍 检查模型可用性: {model_name}")
        
        # 尝试加载
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        
        print("✅ 模型已可用!")
        return True
        
    except Exception as e:
        print(f"❌ 模型不可用: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CICD embedding模型管理")
    parser.add_argument("--check", action="store_true", help="检查模型可用性")
    parser.add_argument("--cache", action="store_true", help="缓存模型")
    
    args = parser.parse_args()
    
    if args.check:
        available = check_model_availability()
        sys.exit(0 if available else 1)
    elif args.cache:
        success = cache_embedding_models()
        sys.exit(0 if success else 1)
    else:
        # 默认先检查，如果不可用则缓存
        if not check_model_availability():
            print("模型不可用，开始缓存...")
            success = cache_embedding_models()
            sys.exit(0 if success else 1)
        else:
            print("模型已可用，无需缓存")
            sys.exit(0)