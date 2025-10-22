#!/usr/bin/env python3
"""
批量更新算子导入路径的脚本
将 sage.libs.rag.*, sage.libs.operators.*, sage.libs.tools.* 
更新为 sage.middleware.operators.rag.*, sage.middleware.operators.llm.*, sage.middleware.operators.tools.*
"""

import os
import re
from pathlib import Path

# 定义需要搜索的目录
SEARCH_DIRS = [
    "examples",
    "packages/sage-apps",
    "packages/sage-studio",
    "packages/sage-benchmark",
    "packages/sage-middleware/src/sage/middleware/components",
]

# 定义替换规则
REPLACEMENTS = [
    # RAG operators
    (r'from sage\.libs\.rag\.generator import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.retriever import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.reranker import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.promptor import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.evaluate import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.chunk import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.refiner import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.writer import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.arxiv import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.searcher import', 'from sage.middleware.operators.rag import'),
    (r'from sage\.libs\.rag\.milvusRetriever import', 'from sage.middleware.operators.rag import'),
    
    # LLM operators
    (r'from sage\.libs\.operators\.vllm_service import VLLMServiceGenerator', 'from sage.middleware.operators.llm import VLLMGenerator'),
    (r'from sage\.libs\.operators\.vllm_service import VLLMEmbeddingOperator', 'from sage.middleware.operators.llm import VLLMEmbedding'),
    (r'from sage\.libs\.operators\.vllm_service import', 'from sage.middleware.operators.llm import'),
    
    # Tool operators
    (r'from sage\.libs\.tools\.searcher_tool import', 'from sage.middleware.operators.tools import'),
]

def update_file(file_path):
    """更新单个文件的导入语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 应用所有替换规则
        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error updating {file_path}: {e}")
        return False

def main():
    """主函数"""
    project_root = Path(__file__).parent
    updated_count = 0
    
    print("🔍 Searching for files with old operator imports...")
    print()
    
    for search_dir in SEARCH_DIRS:
        dir_path = project_root / search_dir
        if not dir_path.exists():
            print(f"⚠ Directory not found: {dir_path}")
            continue
        
        # 查找所有 Python 文件
        for py_file in dir_path.rglob("*.py"):
            if update_file(py_file):
                updated_count += 1
    
    print()
    print(f"✅ Updated {updated_count} file(s)")

if __name__ == "__main__":
    main()
