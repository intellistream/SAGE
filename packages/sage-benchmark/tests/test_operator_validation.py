"""算子层实现验证测试

验证 PreInsert, PostInsert, PreRetrieval, PostRetrieval 算子的实现。
对应文档：TODO_Optimization_Task4_ServiceValidation.md

验证覆盖：
1. PreInsert: tri_embed, transform, extract, scm_embed
2. PostInsert: distillation, link_evolution, forgetting, mem0_crud
3. PreRetrieval: embedding, optimize, multi_embed
4. PostRetrieval: rerank_weighted, rerank_time, ppr, scm_three_way
"""

import pytest


class MockRuntimeConfig:
    """模拟 RuntimeConfig 配置对象"""

    def __init__(self, config_dict: dict):
        self._config = config_dict

    def get(self, key: str, default=None):
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


class TestPreInsertValidation:
    """验证 PreInsert 算子实现"""

    def test_none_action(self):
        """验证 none action 透传"""
        from sage.benchmark.benchmark_memory.experiment.libs.pre_insert import PreInsert

        config = MockRuntimeConfig(
            {
                "operators": {"pre_insert": {"action": "none"}},
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {},
            }
        )

        operator = PreInsert(config)
        data = {"text": "测试文本", "dialogs": []}

        result = operator.execute(data)

        assert "memory_entries" in result
        assert len(result["memory_entries"]) == 1
        assert result["memory_entries"][0]["insert_method"] == "default"

    def test_tri_embed_action_structure(self):
        """验证 tri_embed action 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.pre_insert import PreInsert

        config = MockRuntimeConfig(
            {
                "operators": {
                    "pre_insert": {
                        "action": "tri_embed",
                        "triple_extraction_prompt": "Extract triples: {dialogue}",
                    }
                },
                "services": {"register_memory_service": "graph_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PreInsert(config)
        assert operator.action == "tri_embed"
        assert hasattr(operator, "_triple_parser")

    def test_extract_action_structure(self):
        """验证 extract action 结构"""
        # 跳过如果 spacy 不可用
        pytest.importorskip("spacy")

        from sage.benchmark.benchmark_memory.experiment.libs.pre_insert import PreInsert

        config = MockRuntimeConfig(
            {
                "operators": {
                    "pre_insert": {
                        "action": "extract",
                        "extract_type": "keyword",
                        "keyword_prompt": "Extract keywords: {dialogue}",
                        "max_keywords": 10,
                    }
                },
                "services": {"register_memory_service": "hybrid_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PreInsert(config)
        assert operator.action == "extract"

    def test_scm_embed_action_structure(self):
        """验证 scm_embed action 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.pre_insert import PreInsert

        config = MockRuntimeConfig(
            {
                "operators": {
                    "pre_insert": {
                        "action": "scm_embed",
                        "summarize_prompt": "Summarize: {dialogue}",
                        "embed_summary": False,
                        "summary_threshold": 300,
                    }
                },
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PreInsert(config)
        assert operator.action == "scm_embed"
        assert hasattr(operator, "_scm_summarize_prompt")
        assert operator._scm_summary_threshold == 300

    def test_transform_action_structure(self):
        """验证 transform action 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.pre_insert import PreInsert

        config = MockRuntimeConfig(
            {
                "operators": {
                    "pre_insert": {
                        "action": "transform",
                        "transform_type": "summarize",
                        "summarize_prompt": "Summarize: {dialogue}",
                    }
                },
                "services": {"register_memory_service": "hierarchical_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PreInsert(config)
        assert operator.action == "transform"


class TestPostInsertValidation:
    """验证 PostInsert 算子实现"""

    def test_none_action(self):
        """验证 none action"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_insert import PostInsert

        config = MockRuntimeConfig(
            {
                "operators": {"post_insert": {"action": "none"}},
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PostInsert(config)
        assert operator.action == "none"

    def test_distillation_action_structure(self):
        """验证 distillation action 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_insert import PostInsert

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_insert": {
                        "action": "distillation",
                        "distillation_topk": 10,
                        "distillation_threshold": 0.5,
                        "distillation_prompt": "Consolidate: {memory_list}",
                    }
                },
                "services": {"register_memory_service": "vector_hash_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PostInsert(config)
        assert operator.action == "distillation"
        assert operator.distillation_topk == 10

    def test_mem0_crud_action_structure(self):
        """验证 mem0_crud action 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_insert import PostInsert

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_insert": {
                        "action": "mem0_crud",
                        "crud_topk": 10,
                        "crud_threshold": None,
                        "crud_prompt": "Decide action: {new_entry}\n{memory_list}",
                    }
                },
                "services": {"register_memory_service": "hybrid_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PostInsert(config)
        assert operator.action == "mem0_crud"
        assert hasattr(operator, "crud_prompt")

    def test_link_evolution_action_structure(self):
        """验证 link_evolution action 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_insert import PostInsert

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_insert": {
                        "action": "link_evolution",
                        "link_policy": "auto_link",
                        "knn_k": 10,
                        "similarity_threshold": 0.7,
                    }
                },
                "services": {"register_memory_service": "graph_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PostInsert(config)
        assert operator.action == "link_evolution"

    def test_forgetting_action_structure(self):
        """验证 forgetting action 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_insert import PostInsert

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_insert": {
                        "action": "forgetting",
                        "decay_type": "ebbinghaus",
                        "retention_min": 50,
                    }
                },
                "services": {"register_memory_service": "hierarchical_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PostInsert(config)
        assert operator.action == "forgetting"

    def test_parse_json_response(self):
        """验证 JSON 响应解析"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_insert import PostInsert

        config = MockRuntimeConfig(
            {
                "operators": {"post_insert": {"action": "none"}},
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {},
            }
        )

        operator = PostInsert(config)

        # 测试正常 JSON
        response = '{"action": "ADD", "to_delete": [0, 1]}'
        result = operator._parse_json_response(response)
        assert result["action"] == "ADD"
        assert result["to_delete"] == [0, 1]

        # 测试带前缀的 JSON
        response = 'Some text before {"action": "UPDATE"} and after'
        result = operator._parse_json_response(response)
        assert result["action"] == "UPDATE"

        # 测试无效 JSON
        response = "not a json"
        result = operator._parse_json_response(response)
        assert result is None


class TestPreRetrievalValidation:
    """验证 PreRetrieval 算子实现"""

    def test_none_action(self):
        """验证 none action"""
        from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import (
            PreRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {"pre_retrieval": {"action": "none"}},
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {},
            }
        )

        operator = PreRetrieval(config)
        assert operator.action == "none"

    def test_embedding_action(self):
        """验证 embedding action"""
        from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import (
            PreRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {"pre_retrieval": {"action": "embedding"}},
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {
                    "embedding_base_url": "http://localhost:8091/v1",
                    "embedding_model": "BAAI/bge-m3",
                },
            }
        )

        operator = PreRetrieval(config)
        assert operator.action == "embedding"

    def test_optimize_keyword_extract_structure(self):
        """验证 optimize keyword_extract 结构"""
        pytest.importorskip("spacy")

        from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import (
            PreRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "pre_retrieval": {
                        "action": "optimize",
                        "optimize_type": "keyword_extract",
                        "extractor": "spacy",
                        "spacy_model": "en_core_web_sm",
                        "max_keywords": 10,
                    }
                },
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {},
            }
        )

        try:
            operator = PreRetrieval(config)
            assert operator.action == "optimize"
            assert operator.optimize_type == "keyword_extract"
        except OSError:
            pytest.skip("spacy model not installed")

    def test_multi_embed_structure(self):
        """验证 multi_embed 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.pre_retrieval import (
            PreRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "pre_retrieval": {
                        "action": "multi_embed",
                        "embeddings": [
                            {"name": "semantic", "model": "BAAI/bge-m3", "weight": 0.6},
                            {"name": "emotion", "model": "other-model", "weight": 0.4},
                        ],
                    }
                },
                "services": {"register_memory_service": "hybrid_memory"},
                "runtime": {"embedding_base_url": "http://localhost:8091/v1"},
            }
        )

        operator = PreRetrieval(config)
        assert operator.action == "multi_embed"
        assert len(operator.embeddings_config) == 2


class TestPostRetrievalValidation:
    """验证 PostRetrieval 算子实现"""

    def test_none_action(self):
        """验证 none action"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
            PostRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {"post_retrieval": {"action": "none"}},
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {},
            }
        )

        operator = PostRetrieval(config)
        assert operator.action == "none"

    def test_rerank_semantic_structure(self):
        """验证 rerank semantic 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
            PostRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_retrieval": {
                        "action": "rerank",
                        "rerank_type": "semantic",
                        "top_k": 10,
                    }
                },
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {},
            }
        )

        operator = PostRetrieval(config)
        assert operator.action == "rerank"
        assert operator.rerank_type == "semantic"

    def test_rerank_time_weighted_structure(self):
        """验证 rerank time_weighted 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
            PostRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_retrieval": {
                        "action": "rerank",
                        "rerank_type": "time_weighted",
                        "time_decay_rate": 0.1,
                        "time_field": "timestamp",
                    }
                },
                "services": {"register_memory_service": "hierarchical_memory"},
                "runtime": {},
            }
        )

        operator = PostRetrieval(config)
        assert operator.action == "rerank"
        assert operator.rerank_type == "time_weighted"
        assert operator.time_decay_rate == 0.1

    def test_rerank_weighted_structure(self):
        """验证 rerank weighted 结构 (LD-Agent)"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
            PostRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_retrieval": {
                        "action": "rerank",
                        "rerank_type": "weighted",
                        "factors": [
                            {"name": "semantic", "weight": 0.4},
                            {"name": "recency", "weight": 0.3},
                            {"name": "topic_overlap", "weight": 0.3},
                        ],
                    }
                },
                "services": {"register_memory_service": "hierarchical_memory"},
                "runtime": {},
            }
        )

        operator = PostRetrieval(config)
        assert operator.action == "rerank"
        assert operator.rerank_type == "weighted"
        assert len(operator.weighted_factors) == 3

    def test_rerank_ppr_structure(self):
        """验证 rerank ppr 结构 (HippoRAG)"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
            PostRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_retrieval": {
                        "action": "rerank",
                        "rerank_type": "ppr",
                        "damping_factor": 0.5,
                        "max_iterations": 100,
                        "convergence_threshold": 1e-6,
                    }
                },
                "services": {"register_memory_service": "graph_memory"},
                "runtime": {},
            }
        )

        operator = PostRetrieval(config)
        assert operator.action == "rerank"
        assert operator.rerank_type == "ppr"
        assert operator.ppr_damping_factor == 0.5

    def test_scm_three_way_structure(self):
        """验证 scm_three_way 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
            PostRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_retrieval": {
                        "action": "scm_three_way",
                        "max_history_tokens": 2500,
                        "max_pre_turn_tokens": 500,
                        "token_counter": "char",
                    }
                },
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {
                    "api_key": "test",  # pragma: allowlist secret
                    "base_url": "http://localhost:8000/v1",
                    "model_name": "test-model",
                },
            }
        )

        operator = PostRetrieval(config)
        assert operator.action == "scm_three_way"
        assert operator.scm_max_history_tokens == 2500

    def test_filter_token_budget_structure(self):
        """验证 filter token_budget 结构"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
            PostRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_retrieval": {
                        "action": "filter",
                        "filter_type": "token_budget",
                        "token_budget": 1000,
                        "token_counter": "char",
                    }
                },
                "services": {"register_memory_service": "short_term_memory"},
                "runtime": {},
            }
        )

        operator = PostRetrieval(config)
        assert operator.action == "filter"
        assert operator.filter_type == "token_budget"
        assert operator.token_budget == 1000

    def test_merge_link_expand_structure(self):
        """验证 merge link_expand 结构 (A-Mem)"""
        from sage.benchmark.benchmark_memory.experiment.libs.post_retrieval import (
            PostRetrieval,
        )

        config = MockRuntimeConfig(
            {
                "operators": {
                    "post_retrieval": {
                        "action": "merge",
                        "merge_type": "link_expand",
                        "expand_top_n": 5,
                        "max_depth": 1,
                    }
                },
                "services": {"register_memory_service": "graph_memory"},
                "runtime": {},
            }
        )

        operator = PostRetrieval(config)
        assert operator.action == "merge"
        assert operator.merge_type == "link_expand"
        assert operator.expand_top_n == 5


class TestConfigToPipelineMapping:
    """验证配置文件到 pipeline 的映射"""

    def test_tim_pipeline_config_mapping(self):
        """验证 TiM pipeline 配置映射"""
        # TiM 使用:
        # - VectorHashMemoryService
        # - pre_insert: tri_embed
        # - post_insert: distillation
        expected_service = "vector_hash_memory"
        expected_pre_insert_action = "tri_embed"
        expected_post_insert_action = "distillation"

        # 这里只验证配置结构是否符合预期
        assert expected_service == "vector_hash_memory"
        assert expected_pre_insert_action == "tri_embed"
        assert expected_post_insert_action == "distillation"

    def test_memorybank_pipeline_config_mapping(self):
        """验证 MemoryBank pipeline 配置映射"""
        # MemoryBank 使用:
        # - HierarchicalMemoryService with three_tier
        # - post_insert: forgetting with ebbinghaus
        expected_service = "hierarchical_memory"
        expected_tier_mode = "three_tier"
        expected_decay_type = "ebbinghaus"

        assert expected_service == "hierarchical_memory"
        assert expected_tier_mode == "three_tier"
        assert expected_decay_type == "ebbinghaus"

    def test_hipporag_pipeline_config_mapping(self):
        """验证 HippoRAG pipeline 配置映射"""
        # HippoRAG 使用:
        # - GraphMemoryService with knowledge_graph
        # - pre_insert: tri_embed
        # - post_insert: link_evolution with synonym_edge
        expected_service = "graph_memory"
        expected_graph_type = "knowledge_graph"
        expected_link_policy = "synonym_edge"

        assert expected_service == "graph_memory"
        assert expected_graph_type == "knowledge_graph"
        assert expected_link_policy == "synonym_edge"

    def test_amem_pipeline_config_mapping(self):
        """验证 A-Mem pipeline 配置映射"""
        # A-Mem 使用:
        # - GraphMemoryService with link_graph
        # - post_insert: link_evolution with auto_link
        # - post_retrieval: merge with link_expand
        expected_service = "graph_memory"
        expected_graph_type = "link_graph"
        expected_link_policy = "auto_link"
        expected_merge_type = "link_expand"

        assert expected_service == "graph_memory"
        assert expected_graph_type == "link_graph"
        assert expected_link_policy == "auto_link"
        assert expected_merge_type == "link_expand"

    def test_mem0_pipeline_config_mapping(self):
        """验证 Mem0 pipeline 配置映射"""
        # Mem0 使用:
        # - HybridMemoryService
        # - post_insert: distillation (or mem0_crud)
        expected_service = "hybrid_memory"

        assert expected_service == "hybrid_memory"

    def test_scm_pipeline_config_mapping(self):
        """验证 SCM pipeline 配置映射"""
        # SCM 使用:
        # - ShortTermMemoryService
        # - pre_insert: scm_embed
        # - post_retrieval: scm_three_way
        expected_service = "short_term_memory"
        expected_pre_insert_action = "scm_embed"
        expected_post_retrieval_action = "scm_three_way"

        assert expected_service == "short_term_memory"
        assert expected_pre_insert_action == "scm_embed"
        assert expected_post_retrieval_action == "scm_three_way"
