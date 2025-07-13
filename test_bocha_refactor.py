#!/usr/bin/env python3
"""
测试重构后的BochaSearchTool
验证新的分层搜索结构是否正常工作
"""

import sys
import os

# 添加项目路径
sys.path.append('/api-rework')

import json
from sage_library.context.model_context import ModelContext
from sage_library.tools.searcher_tool import BochaSearchTool, EnhancedBochaSearchTool

def test_basic_bocha_search_tool():
    """测试基础的BochaSearchTool"""
    print("=" * 60)
    print("Testing Basic BochaSearchTool")
    print("=" * 60)
    
    # 创建配置（使用mock配置避免真实API调用）
    config = {
        "url": "https://mock.api.com/search",
        "api_key": "mock_key_for_testing",
        "max_results_per_query": 3,
        "search_engine_name": "MockBocha"
    }
    
    try:
        # 初始化工具
        tool = BochaSearchTool(config)
        print(f"✅ BochaSearchTool initialized successfully")
        print(f"   Search engine: {tool.search_engine_name}")
        print(f"   Max results per query: {tool.max_results_per_query}")
        
        # 创建测试用的ModelContext
        context = ModelContext(
            raw_question="What is artificial intelligence?",
            uuid="test-uuid-123"
        )
        
        # 设置搜索查询
        test_queries = [
            "artificial intelligence definition",
            "AI applications in technology"
        ]
        context.set_search_queries(test_queries)
        
        print(f"✅ Created test ModelContext with {len(test_queries)} search queries")
        print(f"   UUID: {context.uuid}")
        print(f"   Queries: {test_queries}")
        
        # 检查搜索查询获取
        retrieved_queries = context.get_search_queries()
        print(f"✅ Retrieved queries: {retrieved_queries}")
        
        # 测试搜索会话创建
        context.create_search_session("Test search session")
        print(f"✅ Search session created with ID: {context.search_session.session_id}")
        
        print(f"✅ BochaSearchTool basic structure test completed")
        
    except Exception as e:
        print(f"❌ BochaSearchTool test failed: {e}")
        import traceback
        traceback.print_exc()

def test_enhanced_bocha_search_tool():
    """测试增强版的BochaSearchTool"""
    print("=" * 60)
    print("Testing Enhanced BochaSearchTool")
    print("=" * 60)
    
    # 创建增强版配置
    config = {
        "url": "https://mock.api.com/search",
        "api_key": "mock_key_for_testing",
        "max_results_per_query": 5,
        "search_engine_name": "EnhancedMockBocha",
        "deduplicate_results": True,
        "max_total_chunks": 15,
        "preserve_chunk_order": True,
        "min_relevance_score": 0.2,
        "diversity_threshold": 0.7
    }
    
    try:
        # 初始化增强版工具
        enhanced_tool = EnhancedBochaSearchTool(config)
        print(f"✅ EnhancedBochaSearchTool initialized successfully")
        print(f"   Deduplicate: {enhanced_tool.deduplicate_results}")
        print(f"   Max total chunks: {enhanced_tool.max_total_chunks}")
        print(f"   Min relevance score: {enhanced_tool.min_relevance_score}")
        print(f"   Diversity threshold: {enhanced_tool.diversity_threshold}")
        
        # 创建测试context
        context = ModelContext(
            raw_question="How does machine learning work?",
            uuid="enhanced-test-uuid-456"
        )
        
        # 设置多个搜索查询
        test_queries = [
            "machine learning algorithms",
            "neural networks basics",
            "deep learning applications"
        ]
        context.set_search_queries(test_queries)
        
        print(f"✅ Enhanced test setup completed")
        print(f"   Context UUID: {context.uuid}")
        print(f"   Test queries: {len(test_queries)}")
        
    except Exception as e:
        print(f"❌ EnhancedBochaSearchTool test failed: {e}")
        import traceback
        traceback.print_exc()

def test_model_context_search_structures():
    """测试ModelContext的搜索结构功能"""
    print("=" * 60)
    print("Testing ModelContext Search Structures")
    print("=" * 60)
    
    try:
        from sage_library.context.search_result import SearchResult
        from sage_library.context.search_query_results import SearchQueryResults
        from sage_library.context.search_session import SearchSession
        
        # 创建测试搜索结果
        search_results = [
            SearchResult(
                title="AI Introduction",
                content="Artificial Intelligence is the simulation of human intelligence...",
                source="https://example.com/ai-intro",
                rank=1,
                relevance_score=0.95
            ),
            SearchResult(
                title="Machine Learning Basics",
                content="Machine learning is a subset of AI that enables...",
                source="https://example.com/ml-basics", 
                rank=2,
                relevance_score=0.87
            )
        ]
        
        # 创建查询结果
        query_result = SearchQueryResults(
            query="artificial intelligence basics",
            results=search_results,
            search_engine="TestEngine",
            execution_time_ms=250,
            total_results_count=10
        )
        
        # 创建搜索会话
        search_session = SearchSession(
            original_question="What is AI?",
            query_results=[query_result]
        )
        
        # 创建包含分层搜索结构的ModelContext
        context = ModelContext(
            raw_question="What is AI?",
            search_session=search_session,
            uuid="search-structure-test-789"
        )
        
        print(f"✅ Search structures created successfully")
        print(f"   Search results count: {len(search_results)}")
        print(f"   Query results count: {context.search_session.get_total_results_count()}")
        print(f"   All queries: {context.get_search_queries()}")
        
        # 测试搜索结果访问方法
        all_results = context.get_all_search_results()
        print(f"✅ Retrieved {len(all_results)} search results")
        
        # 测试legacy兼容性
        if context.retriver_chunks:
            print(f"✅ Legacy chunks: {len(context.retriver_chunks)}")
        else:
            print(f"✅ No legacy chunks (using new structure)")
            
        # 显示context
        print(f"✅ Context summary:")
        print(f"   Has search results: {context.has_search_results()}")
        print(f"   Search results count: {context.get_search_results_count()}")
        print(f"   Has search queries: {context.has_search_queries()}")
        
    except Exception as e:
        print(f"❌ ModelContext search structures test failed: {e}")
        import traceback
        traceback.print_exc()

def test_json_serialization():
    """测试JSON序列化功能"""
    print("=" * 60)
    print("Testing JSON Serialization")
    print("=" * 60)
    
    try:
        from sage_library.context.search_result import SearchResult
        
        # 创建包含搜索结果的完整context
        context = ModelContext(raw_question="Test question")
        context.create_search_session("Test session")
        
        # 添加一些搜索结果
        test_results = [
            SearchResult(
                title="Test Result 1",
                content="This is test content 1",
                source="https://test1.com",
                rank=1,
                relevance_score=0.9
            )
        ]
        
        context.add_search_results(
            query="test query",
            results=test_results,
            search_engine="TestEngine"
        )
        
        # 测试JSON序列化
        json_str = context.to_json()
        print(f"✅ JSON serialization successful")
        print(f"   JSON length: {len(json_str)} characters")
        
        # 测试JSON反序列化
        restored_context = ModelContext.from_json(json_str)
        print(f"✅ JSON deserialization successful")
        print(f"   Restored UUID: {restored_context.uuid}")
        print(f"   Restored search results: {restored_context.get_search_results_count()}")
        
        # 验证数据完整性
        original_queries = context.get_search_queries()
        restored_queries = restored_context.get_search_queries()
        
        if original_queries == restored_queries:
            print(f"✅ Data integrity verified - queries match")
        else:
            print(f"❌ Data integrity issue - queries don't match")
            
    except Exception as e:
        print(f"❌ JSON serialization test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """运行所有测试"""
    print("🚀 Starting BochaSearchTool Refactor Tests")
    print("=" * 80)
    
    test_basic_bocha_search_tool()
    print()
    
    test_enhanced_bocha_search_tool()
    print()
    
    test_model_context_search_structures()
    print()
    
    test_json_serialization()
    print()
    
    print("=" * 80)
    print("🎉 BochaSearchTool Refactor Tests Completed")

if __name__ == "__main__":
    main()
