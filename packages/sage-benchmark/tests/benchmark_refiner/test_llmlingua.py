"""
LLMLingua Compressor Tests
==========================

测试 LLMLingua 压缩器的功能。
"""



class TestLLMLinguaCompressor:
    """LLMLinguaCompressor 单元测试"""

    def test_import(self):
        """测试模块可以正常导入"""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua import (
            LLMLinguaCompressor,
        )

        assert LLMLinguaCompressor is not None

    def test_compressor_initialization(self):
        """测试压缩器初始化"""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua import (
            LLMLinguaCompressor,
        )

        compressor = LLMLinguaCompressor(
            model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
            use_llmlingua2=True,
            device="cpu",  # 使用 CPU 避免 GPU 依赖
        )

        assert compressor.model_name == "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
        assert compressor.use_llmlingua2 is True
        assert compressor.device == "cpu"

    def test_compress_short_text(self):
        """测试短文本压缩（应该直接返回原文）"""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua import (
            LLMLinguaCompressor,
        )

        compressor = LLMLinguaCompressor(device="cpu")

        short_text = "This is a short text."
        question = "What is this?"

        result = compressor.compress(
            context=short_text,
            question=question,
            budget=1000,  # 预算远大于文本长度
        )

        # 短文本应该直接返回原文
        assert result.compressed_context == short_text
        assert result.compression_rate == 1.0

    def test_compress_returns_valid_result(self):
        """测试压缩返回有效的结果结构"""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua import (
            LLMLinguaCompressor,
        )

        compressor = LLMLinguaCompressor(device="cpu")

        # 较长的文本
        long_text = " ".join([f"This is sentence number {i}." for i in range(100)])
        question = "What is the content about?"

        result = compressor.compress(
            context=long_text,
            question=question,
            budget=50,  # 很小的预算
        )

        # 检查结果结构
        assert hasattr(result, "compressed_context")
        assert hasattr(result, "original_tokens")
        assert hasattr(result, "compressed_tokens")
        assert hasattr(result, "compression_rate")
        assert hasattr(result, "processing_time_ms")

        # 检查值类型
        assert isinstance(result.compressed_context, str)
        assert isinstance(result.original_tokens, int)
        assert isinstance(result.compressed_tokens, int)
        assert isinstance(result.compression_rate, float)
        assert isinstance(result.processing_time_ms, float)

        # 检查合理值
        assert result.original_tokens > 0
        assert result.processing_time_ms >= 0

    def test_compression_result_to_dict(self):
        """测试 CompressionResult.to_dict()"""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua.compressor import (
            CompressionResult,
        )

        result = CompressionResult(
            compressed_context="compressed text",
            original_tokens=100,
            compressed_tokens=50,
            compression_rate=0.5,
            processing_time_ms=100.0,
        )

        d = result.to_dict()

        assert d["compressed_context"] == "compressed text"
        assert d["original_tokens"] == 100
        assert d["compressed_tokens"] == 50
        assert d["compression_rate"] == 0.5
        assert d["processing_time_ms"] == 100.0

    def test_batch_compress(self):
        """测试批量压缩"""
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua import (
            LLMLinguaCompressor,
        )

        compressor = LLMLinguaCompressor(device="cpu")

        contexts = [
            "First context about topic A.",
            "Second context about topic B.",
        ]
        questions = [
            "What is topic A?",
            "What is topic B?",
        ]

        results = compressor.batch_compress(
            contexts=contexts,
            questions=questions,
            budget=1000,
        )

        assert len(results) == 2
        assert all(hasattr(r, "compressed_context") for r in results)


class TestLLMLinguaRefinerOperator:
    """LLMLinguaRefinerOperator 单元测试"""

    def test_import(self):
        """测试 Operator 可以正常导入"""
        from sage.middleware.components.sage_refiner import LLMLinguaRefinerOperator

        assert LLMLinguaRefinerOperator is not None

    def test_operator_initialization_enabled(self):
        """测试 Operator 启用模式初始化"""
        from sage.middleware.components.sage_refiner import LLMLinguaRefinerOperator

        config = {
            "enabled": True,
            "device": "cpu",
            "budget": 2048,
        }

        operator = LLMLinguaRefinerOperator(config)
        assert operator.enabled is True

    def test_operator_initialization_disabled(self):
        """测试 Operator 禁用模式初始化"""
        from sage.middleware.components.sage_refiner import LLMLinguaRefinerOperator

        config = {
            "enabled": False,
        }

        operator = LLMLinguaRefinerOperator(config)
        assert operator.enabled is False

    def test_execute_empty_retrieval(self):
        """测试空检索结果处理"""
        from sage.middleware.components.sage_refiner import LLMLinguaRefinerOperator

        config = {
            "enabled": True,
            "device": "cpu",
        }

        operator = LLMLinguaRefinerOperator(config)

        data = {
            "query": "What is quantum computing?",
            "retrieval_results": [],
        }

        result = operator.execute(data)

        assert result["refining_results"] == []
        assert result["compressed_context"] == ""
        assert result["compression_rate"] == 1.0

    def test_execute_disabled_passthrough(self):
        """测试禁用模式的直通处理"""
        from sage.middleware.components.sage_refiner import LLMLinguaRefinerOperator

        config = {
            "enabled": False,
        }

        operator = LLMLinguaRefinerOperator(config)

        data = {
            "query": "What is AI?",
            "retrieval_results": [
                {"text": "AI is artificial intelligence."},
                {"contents": "Machine learning is a subset of AI."},
            ],
        }

        result = operator.execute(data)

        # 禁用模式应该直接返回原始文档
        assert len(result["refining_results"]) == 2
        assert "AI is artificial intelligence." in result["refining_results"][0]

    def test_execute_with_dict_results(self):
        """测试处理字典格式的检索结果"""
        from sage.middleware.components.sage_refiner import LLMLinguaRefinerOperator

        config = {
            "enabled": True,
            "device": "cpu",
            "budget": 2048,
        }

        operator = LLMLinguaRefinerOperator(config)

        data = {
            "query": "What is machine learning?",
            "retrieval_results": [
                {"text": "Machine learning is a type of AI.", "title": "ML Intro"},
                {"contents": "Deep learning uses neural networks."},
            ],
        }

        result = operator.execute(data)

        # 检查结果结构
        assert "refining_results" in result
        assert "compressed_context" in result
        assert "compression_rate" in result


class TestRefinerAlgorithmEnum:
    """测试 RefinerAlgorithm 枚举"""

    def test_llmlingua_in_available(self):
        """测试 llmlingua 在可用算法列表中"""
        from sage.benchmark.benchmark_refiner.experiments.base_experiment import RefinerAlgorithm

        available = RefinerAlgorithm.available()

        assert "llmlingua" in available
        assert RefinerAlgorithm.LLMLINGUA.value == "llmlingua"

    def test_adaptive_in_available(self):
        """测试 adaptive 在可用算法列表中"""
        from sage.benchmark.benchmark_refiner.experiments.base_experiment import RefinerAlgorithm

        available = RefinerAlgorithm.available()

        assert "adaptive" in available
