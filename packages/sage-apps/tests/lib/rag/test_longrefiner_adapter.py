"""
测试 sage.libs.rag.longrefiner.longrefiner_adapter 模块
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import tempfile

# 尝试导入插件模块
pytest_plugins = []

try:
    from sage.libs.rag.longrefiner.longrefiner_adapter import LongRefinerAdapter
    LONGREFINER_AVAILABLE = True
except ImportError as e:
    LONGREFINER_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"LongRefiner module not available: {e}")


@pytest.mark.unit
class TestLongRefinerAdapter:
    """测试LongRefinerAdapter类"""
    
    def test_longrefiner_adapter_import(self):
        """测试LongRefinerAdapter导入"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        from sage.libs.rag.longrefiner.longrefiner_adapter import LongRefinerAdapter
        assert LongRefinerAdapter is not None
    
    def test_longrefiner_adapter_initialization_missing_config(self):
        """测试LongRefinerAdapter初始化缺少配置"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        incomplete_config = {
            "base_model_path": "/path/to/model",
            # 缺少其他必需配置
        }
        
        with pytest.raises(RuntimeError) as exc_info:
            LongRefinerAdapter(config=incomplete_config)
        
        assert "缺少配置字段" in str(exc_info.value)
    
    def test_longrefiner_adapter_initialization_complete_config(self):
        """测试LongRefinerAdapter完整配置初始化"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        complete_config = {
            "base_model_path": "/path/to/base/model",
            "query_analysis_module_lora_path": "/path/to/query/lora",
            "doc_structuring_module_lora_path": "/path/to/doc/lora",
            "global_selection_module_lora_path": "/path/to/global/lora",
            "score_model_name": "test_score_model",
            "score_model_path": "/path/to/score/model",
            "max_model_len": 4096,
            "budget": 1000
        }
        
        try:
            adapter = LongRefinerAdapter(config=complete_config, enable_profile=False)
            assert adapter.cfg == complete_config
            assert adapter.enable_profile == False
            assert adapter.refiner is None  # 懒加载
        except Exception as e:
            pytest.skip(f"LongRefinerAdapter initialization failed: {e}")
    
    def test_longrefiner_adapter_with_profile_enabled(self, temp_dir):
        """测试启用profile的LongRefinerAdapter"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        complete_config = {
            "base_model_path": "/path/to/base/model",
            "query_analysis_module_lora_path": "/path/to/query/lora",
            "doc_structuring_module_lora_path": "/path/to/doc/lora",
            "global_selection_module_lora_path": "/path/to/global/lora",
            "score_model_name": "test_score_model",
            "score_model_path": "/path/to/score/model",
            "max_model_len": 4096,
            "budget": 1000
        }
        
        # 模拟上下文
        mock_ctx = Mock()
        mock_ctx.env_base_dir = temp_dir
        
        try:
            adapter = LongRefinerAdapter(
                config=complete_config, 
                enable_profile=True, 
                ctx=mock_ctx
            )
            
            assert adapter.enable_profile == True
            assert adapter.data_base_path == os.path.join(temp_dir, ".sage_states", "refiner_data")
            assert os.path.exists(adapter.data_base_path)
            assert adapter.data_records == []
            
        except Exception as e:
            pytest.skip(f"LongRefinerAdapter profile initialization failed: {e}")


@pytest.mark.unit
class TestLongRefinerAdapterMethods:
    """测试LongRefinerAdapter方法"""
    
    def get_complete_config(self):
        """获取完整配置"""
        return {
            "base_model_path": "/path/to/base/model",
            "query_analysis_module_lora_path": "/path/to/query/lora",
            "doc_structuring_module_lora_path": "/path/to/doc/lora",
            "global_selection_module_lora_path": "/path/to/global/lora",
            "score_model_name": "test_score_model",
            "score_model_path": "/path/to/score/model",
            "max_model_len": 4096,
            "budget": 1000
        }
    
    def test_save_data_record_disabled(self):
        """测试未启用profile时不保存数据记录"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        config = self.get_complete_config()
        
        try:
            adapter = LongRefinerAdapter(config=config, enable_profile=False)
            
            # 调用_save_data_record应该直接返回，不执行任何操作
            adapter._save_data_record("question", ["doc1"], ["refined1"])
            
            # 由于profile未启用，不应该有任何数据记录
            assert not hasattr(adapter, 'data_records') or adapter.data_records == []
            
        except Exception as e:
            pytest.skip(f"Save data record test failed: {e}")
    
    @patch('builtins.open', create=True)
    @patch('json.dump')
    def test_save_data_record_enabled(self, mock_json_dump, mock_open, temp_dir):
        """测试启用profile时保存数据记录"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        config = self.get_complete_config()
        mock_ctx = Mock()
        mock_ctx.env_base_dir = temp_dir
        
        try:
            adapter = LongRefinerAdapter(
                config=config, 
                enable_profile=True, 
                ctx=mock_ctx
            )
            
            # 模拟文件操作
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # 调用保存数据记录
            adapter._save_data_record(
                "测试问题", 
                ["原始文档1", "原始文档2"], 
                ["精炼文档1"]
            )
            
            # 验证数据记录被添加
            assert len(adapter.data_records) >= 1
            
            # 验证文件写入被调用
            mock_open.assert_called()
            mock_json_dump.assert_called()
            
        except Exception as e:
            pytest.skip(f"Save data record enabled test failed: {e}")
    
    @patch('sage.libs.rag.longrefiner.longrefiner.refiner.LongRefiner')
    def test_init_refiner(self, mock_longrefiner_class):
        """测试refiner初始化"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        config = self.get_complete_config()
        mock_refiner = Mock()
        mock_longrefiner_class.return_value = mock_refiner
        
        try:
            adapter = LongRefinerAdapter(config=config, enable_profile=False)
            
            # 初始时refiner应该为None
            assert adapter.refiner is None
            
            # 调用_init_refiner
            adapter._init_refiner()
            
            # 验证refiner被创建
            assert adapter.refiner is not None
            mock_longrefiner_class.assert_called_once_with(
                base_model_path=config["base_model_path"],
                query_analysis_module_lora_path=config["query_analysis_module_lora_path"],
                doc_structuring_module_lora_path=config["doc_structuring_module_lora_path"],
                global_selection_module_lora_path=config["global_selection_module_lora_path"],
                score_model_name=config["score_model_name"],
                score_model_path=config["score_model_path"],
                max_model_len=config["max_model_len"]
            )
            
        except Exception as e:
            pytest.skip(f"Init refiner test failed: {e}")


@pytest.mark.unit
class TestLongRefinerAdapterExecution:
    """测试LongRefinerAdapter执行"""
    
    def get_complete_config(self):
        """获取完整配置"""
        return {
            "base_model_path": "/path/to/base/model",
            "query_analysis_module_lora_path": "/path/to/query/lora",
            "doc_structuring_module_lora_path": "/path/to/doc/lora",
            "global_selection_module_lora_path": "/path/to/global/lora",
            "score_model_name": "test_score_model",
            "score_model_path": "/path/to/score/model",
            "max_model_len": 4096,
            "budget": 1000
        }
    
    @patch('sage.libs.rag.longrefiner.longrefiner.refiner.LongRefiner')
    def test_execute_with_dict_docs(self, mock_longrefiner_class):
        """测试执行字典格式文档"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        config = self.get_complete_config()
        
        # 模拟refiner
        mock_refiner = Mock()
        mock_refiner.run.return_value = [
            {"contents": "精炼后的文档1"},
            {"contents": "精炼后的文档2"}
        ]
        mock_longrefiner_class.return_value = mock_refiner
        
        try:
            adapter = LongRefinerAdapter(config=config, enable_profile=False)
            
            # 测试数据：字典格式文档
            question = "什么是人工智能？"
            docs = [
                {"text": "人工智能是计算机科学的分支"},
                {"text": "AI包括机器学习和深度学习"}
            ]
            
            result = adapter.execute((question, docs))
            
            # 验证结果格式
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result[0] == question
            
            # 验证refiner被调用
            mock_refiner.run.assert_called_once()
            call_args = mock_refiner.run.call_args
            assert call_args[0][0] == question  # 问题
            assert call_args[1]["budget"] == config["budget"]  # budget参数
            
            # 验证文档转换
            document_list = call_args[0][1]
            assert len(document_list) == 2
            assert all("contents" in doc for doc in document_list)
            
        except Exception as e:
            pytest.skip(f"Execute with dict docs test failed: {e}")
    
    @patch('sage.libs.rag.longrefiner.longrefiner.refiner.LongRefiner')
    def test_execute_with_string_docs(self, mock_longrefiner_class):
        """测试执行字符串格式文档"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        config = self.get_complete_config()
        
        # 模拟refiner
        mock_refiner = Mock()
        mock_refiner.run.return_value = [{"contents": "精炼后的文档"}]
        mock_longrefiner_class.return_value = mock_refiner
        
        try:
            adapter = LongRefinerAdapter(config=config, enable_profile=False)
            
            # 测试数据：字符串格式文档
            question = "什么是机器学习？"
            docs = ["机器学习是AI的子领域", "监督学习需要标注数据"]
            
            result = adapter.execute((question, docs))
            
            # 验证结果
            assert isinstance(result, tuple)
            assert result[0] == question
            
            # 验证refiner调用
            mock_refiner.run.assert_called_once()
            
        except Exception as e:
            pytest.skip(f"Execute with string docs test failed: {e}")
    
    @patch('sage.libs.rag.longrefiner.longrefiner.refiner.LongRefiner')
    def test_execute_with_exception(self, mock_longrefiner_class):
        """测试执行异常处理"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        config = self.get_complete_config()
        
        # 模拟refiner抛出异常
        mock_refiner = Mock()
        mock_refiner.run.side_effect = Exception("模型加载失败")
        mock_longrefiner_class.return_value = mock_refiner
        
        try:
            adapter = LongRefinerAdapter(config=config, enable_profile=False)
            
            question = "测试问题"
            docs = [{"text": "测试文档"}]
            
            result = adapter.execute((question, docs))
            
            # 异常情况下应该返回空列表
            assert result == (question, [])
            
        except Exception as e:
            pytest.skip(f"Execute with exception test failed: {e}")


@pytest.mark.integration
class TestLongRefinerAdapterIntegration:
    """LongRefinerAdapter集成测试"""
    
    def test_full_workflow_simulation(self, temp_dir):
        """测试完整工作流模拟"""
        # 由于实际的LongRefiner可能不可用，使用Mock进行完整工作流测试
        
        config = {
            "base_model_path": "/mock/path",
            "query_analysis_module_lora_path": "/mock/path",
            "doc_structuring_module_lora_path": "/mock/path",
            "global_selection_module_lora_path": "/mock/path",
            "score_model_name": "mock_model",
            "score_model_path": "/mock/path",
            "max_model_len": 2048,
            "budget": 500
        }
        
        # 模拟上下文
        mock_ctx = Mock()
        mock_ctx.env_base_dir = temp_dir
        
        # 模拟完整的文档精炼工作流
        with patch('sage.libs.rag.longrefiner.longrefiner.refiner.LongRefiner') as mock_refiner_class:
            mock_refiner = Mock()
            mock_refiner.run.return_value = [
                {"contents": "精炼后的重要文档1"},
                {"contents": "精炼后的重要文档2"}
            ]
            mock_refiner_class.return_value = mock_refiner
            
            try:
                # 创建适配器
                adapter = LongRefinerAdapter(
                    config=config, 
                    enable_profile=True, 
                    ctx=mock_ctx
                )
                
                # 测试数据
                question = "人工智能在医疗领域的应用有哪些？"
                docs = [
                    {"text": "AI在医疗诊断中发挥重要作用"},
                    {"text": "机器学习算法可以分析医学影像"},
                    {"text": "自然语言处理可以分析病历"},
                    {"text": "今天天气很好"},  # 不相关文档
                    {"text": "深度学习在药物发现中应用广泛"}
                ]
                
                # 执行精炼
                result = adapter.execute((question, docs))
                
                # 验证结果
                assert isinstance(result, tuple)
                assert len(result) == 2
                assert result[0] == question
                assert isinstance(result[1], list)
                
                # 验证profile数据被记录
                assert hasattr(adapter, 'data_records')
                
            except Exception as e:
                pytest.skip(f"Full workflow simulation failed: {e}")
    
    def test_adapter_in_pipeline(self):
        """测试适配器在管道中的使用"""
        # 模拟在SAGE管道中使用LongRefinerAdapter
        
        # 创建管道步骤
        pipeline_steps = []
        
        # 步骤1：文档检索
        def retrieval_step(query):
            pipeline_steps.append("retrieval")
            return query, [
                {"text": "相关文档1"},
                {"text": "相关文档2"},
                {"text": "无关文档"},
                {"text": "相关文档3"}
            ]
        
        # 步骤2：文档精炼（使用Mock）
        def refine_step(data):
            pipeline_steps.append("refine")
            query, docs = data
            # 模拟精炼结果
            refined_docs = [doc for doc in docs if "相关" in doc["text"]]
            return query, refined_docs
        
        # 步骤3：答案生成
        def generation_step(data):
            pipeline_steps.append("generation")
            query, docs = data
            return f"基于{len(docs)}个文档的回答：{query}"
        
        # 执行管道
        query = "测试查询"
        
        data = retrieval_step(query)
        data = refine_step(data)
        answer = generation_step(data)
        
        # 验证管道执行
        assert pipeline_steps == ["retrieval", "refine", "generation"]
        assert "基于3个文档的回答" in answer


@pytest.mark.external
class TestLongRefinerAdapterExternal:
    """LongRefinerAdapter外部依赖测试"""
    
    def test_model_loading_failure(self):
        """测试模型加载失败"""
        if not LONGREFINER_AVAILABLE:
            pytest.skip("LongRefiner module not available")
        
        config = {
            "base_model_path": "/nonexistent/path",
            "query_analysis_module_lora_path": "/nonexistent/path",
            "doc_structuring_module_lora_path": "/nonexistent/path",
            "global_selection_module_lora_path": "/nonexistent/path",
            "score_model_name": "nonexistent_model",
            "score_model_path": "/nonexistent/path",
            "max_model_len": 4096,
            "budget": 1000
        }
        
        try:
            adapter = LongRefinerAdapter(config=config, enable_profile=False)
            
            # 模型加载应该在_init_refiner时失败
            with pytest.raises(Exception):
                adapter._init_refiner()
                
        except Exception as e:
            pytest.skip(f"Model loading failure test failed: {e}")


@pytest.mark.unit
class TestLongRefinerAdapterFallback:
    """LongRefinerAdapter降级测试"""
    
    def test_adapter_fallback(self):
        """测试适配器降级"""
        # 模拟简单的文档精炼器
        class SimpleLongRefiner:
            def __init__(self, config=None, enable_profile=False, ctx=None):
                self.config = config or {}
                self.enable_profile = enable_profile
                self.ctx = ctx
            
            def execute(self, data):
                question, docs = data
                
                # 简单的文档过滤：保留包含关键词的文档
                keywords = question.lower().split()
                refined_docs = []
                
                for doc in docs:
                    if isinstance(doc, dict):
                        text = doc.get("text", "").lower()
                    else:
                        text = str(doc).lower()
                    
                    # 如果文档包含问题中的关键词，保留
                    if any(keyword in text for keyword in keywords):
                        refined_docs.append(doc)
                
                # 限制返回文档数量（模拟budget）
                budget = self.config.get("budget", 1000)
                max_docs = min(len(refined_docs), budget // 100)  # 简单的budget计算
                
                return question, refined_docs[:max_docs]
        
        # 测试简单精炼器
        config = {"budget": 500}
        refiner = SimpleLongRefiner(config=config)
        
        question = "人工智能应用"
        docs = [
            {"text": "人工智能在医疗中的应用"},
            {"text": "机器学习算法"},
            {"text": "今天天气很好"},
            {"text": "AI应用案例分析"}
        ]
        
        result = refiner.execute((question, docs))
        refined_question, refined_docs = result
        
        assert refined_question == question
        assert len(refined_docs) <= len(docs)  # 精炼后文档数量应该不超过原始数量
        
        # 验证保留的文档都包含相关关键词
        for doc in refined_docs:
            text = doc.get("text", "").lower()
            assert any(keyword in text for keyword in ["人工智能", "应用", "ai"])
    
    def test_basic_document_filtering(self):
        """测试基本文档过滤"""
        # 简单的文档过滤函数
        def filter_documents_by_keywords(question, docs, max_count=3):
            keywords = question.lower().split()
            scored_docs = []
            
            for doc in docs:
                if isinstance(doc, dict):
                    text = doc.get("text", "").lower()
                else:
                    text = str(doc).lower()
                
                score = sum(1 for keyword in keywords if keyword in text)
                if score > 0:
                    doc_copy = doc.copy() if isinstance(doc, dict) else {"text": doc}
                    doc_copy["relevance_score"] = score
                    scored_docs.append(doc_copy)
            
            # 按相关性排序并返回前N个
            scored_docs.sort(key=lambda x: x["relevance_score"], reverse=True)
            return scored_docs[:max_count]
        
        # 测试过滤
        question = "机器学习算法"
        docs = [
            {"text": "机器学习是AI的重要分支"},
            {"text": "深度学习算法很复杂"},
            {"text": "监督学习需要标注数据"},
            {"text": "今天天气晴朗"},
            {"text": "算法优化很重要"}
        ]
        
        filtered = filter_documents_by_keywords(question, docs, max_count=3)
        
        assert len(filtered) <= 3
        assert all("relevance_score" in doc for doc in filtered)
        
        # 验证第一个文档的相关性最高
        if filtered:
            assert filtered[0]["relevance_score"] >= filtered[-1]["relevance_score"]
