"""
Workload 4 VDB 检索分支算子

实现双路 4-stage VDB 检索流水线，包括：
- VDBRetriever: VDB 检索算子
- VDBResultFilter: 低分结果过滤
- LocalReranker: Stage 内局部重排序(BM25)
- StageAggregator: Stage 结果汇聚
"""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from typing import TYPE_CHECKING, Any

from sage.common.core.functions.filter_function import FilterFunction
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.flatmap_function import FlatMapFunction

if TYPE_CHECKING:
    from .models import JoinedEvent, VDBRetrievalResult


try:
    from .models import JoinedEvent, VDBRetrievalResult
except ImportError:
    from models import JoinedEvent, VDBRetrievalResult


class VDBRetriever(MapFunction):
    """
    VDB 检索算子(通过 Service)。
    
    特点:
    - 支持两个独立的 VDB 实例(vdb1, vdb2)
    - 4-stage 级联检索
    - 通过 Service 调用避免序列化问题
    - 支持 top-k 可配置
    - 返回 VDBResultsWrapper 保持结果完整性(用于后续 join)
    
    Args:
        vdb_name: VDB 实例名称 ("vdb1" | "vdb2")
        top_k: 返回 top-k 结果
        stage: 当前 stage (1-4)
        **kwargs: 父类参数
    """
    
    def __init__(
        self,
        vdb_name: str,
        top_k: int = 20,
        stage: int = 1,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        assert vdb_name in ["vdb1", "vdb2"], f"Invalid vdb_name: {vdb_name}"
        assert 1 <= stage <= 4, f"Invalid stage: {stage}"
        assert top_k > 0, f"Invalid top_k: {top_k}"
        
        self.vdb_name = vdb_name
        self.top_k = top_k
        self.stage = stage
        

    
    def execute(self, data: "JoinedEvent | GraphEnrichedEvent | Any") -> "VDBResultsWrapper":
        """
        执行 VDB 检索。
        
        Args:
            data: JoinedEvent 或 GraphEnrichedEvent(graph 串行后)
        
        Returns:
            VDBResultsWrapper 包含检索结果列表
        """
        from sage.kernel.runtime.communication.packet import StopSignal
        from .models import VDBResultsWrapper
        
        self.logger.debug(f"[EXEC] Received data type: {type(data).__name__}")
        
        if isinstance(data, StopSignal):
            self.logger.debug("[EXEC] Received StopSignal, passing through")
            return data
        
        # 从不同数据类型提取 query
        from .models import GraphEnrichedEvent
        if isinstance(data, GraphEnrichedEvent):
            query_event = data.query
            source_event = data  # 保留完整的 GraphEnrichedEvent
        elif isinstance(data, JoinedEvent):
            query_event = data.query
            source_event = None
        else:
            # 尝试 TaggedEvent 兼容
            try:
                from .tag_utils import TaggedEvent
                if isinstance(data, TaggedEvent):
                    # 解包 TaggedEvent，获取内部的 GraphEnrichedEvent
                    inner_data = data.event
                    if isinstance(inner_data, GraphEnrichedEvent):
                        query_event = inner_data.query
                        source_event = inner_data  # 保留 GraphEnrichedEvent
                    elif isinstance(inner_data, JoinedEvent):
                        query_event = inner_data.query
                        source_event = None
                    else:
                        raise TypeError(f"Unexpected inner data type in TaggedEvent: {type(inner_data)}")
                else:
                    raise TypeError(f"Unexpected data type: {type(data)}")
            except ImportError:
                raise TypeError(f"Unexpected data type: {type(data)}")
        
        start_time = time.time()
        
        self.logger.info(
            f"[EXEC] Processing query_id={query_event.query_id}, "
            f"has_embedding={query_event.embedding is not None}, "
            f"source_event={type(source_event).__name__ if source_event else 'None'}"
        )
        
        # 使用查询的 embedding 进行检索
        query_embedding = query_event.embedding
        if query_embedding is None:
            self.logger.warning(f"[EXEC] Query {query_event.query_id} has no embedding, returning empty results")
            # 如果没有 embedding，返回空的 wrapper
            from .models import VDBResultsWrapper
            return VDBResultsWrapper(
                query_id=query_event.query_id,
                vdb_name=self.vdb_name,
                results=[],
                stage=self.stage,
                source_event=source_event,
            )
        
        # 通过 Service 调用 VDB 检索
        self.logger.debug(f"[EXEC] Calling service.search(top_k={self.top_k})")
        try:
            results = self.call_service(
                self.vdb_name,
                "search",
                query_embedding=query_embedding,
                top_k=self.top_k,
                filter_metadata={"category": query_event.category}
            )
            self.logger.info(f"[EXEC] Service returned {len(results)} results in {time.time()-start_time:.3f}s")
        except Exception as e:
            # 如果 Service 调用失败，返回空的 wrapper
            self.logger.error(f"[EXEC] Service call failed: {e}")
            print(f"[WARNING] VDB {self.vdb_name} stage {self.stage} failed: {e}")
            from .models import VDBResultsWrapper
            return VDBResultsWrapper(
                query_id=query_event.query_id,
                vdb_name=self.vdb_name,
                results=[],
                stage=self.stage,
            )
        
        # 转换为 VDBRetrievalResult
        vdb_results = []
        for idx, result in enumerate(results):
            vdb_result = VDBRetrievalResult(
                doc_id=result.get("id", f"{self.vdb_name}_stage{self.stage}_{idx}"),
                content=result.get("content", result.get("text", "")),
                score=float(result.get("score", 0.0)),
                source=self.vdb_name,
                stage=self.stage,
                query_id=query_event.query_id,  # 添加 query_id
                metadata={
                    "retrieval_time": time.time() - start_time,
                    "category": query_event.category,
                    **result.get("metadata", {})
                }
            )
            vdb_results.append(vdb_result)
        
        # 返回包装对象
        from .models import VDBResultsWrapper
        return VDBResultsWrapper(
            query_id=query_event.query_id,
            vdb_name=self.vdb_name,
            results=vdb_results,
            stage=self.stage,
            source_event=source_event,  # 保留 GraphEnrichedEvent
        )


class VDBResultFilter(FilterFunction):
    """
    过滤低分 VDB 结果。
    
    特点:
    - 阈值过滤，减少下游负载 30-40%
    - 支持自适应阈值(根据 stage)
    
    Args:
        threshold: 过滤阈值(score < threshold 将被过滤)
        adaptive: 是否根据 stage 自适应调整阈值
        **kwargs: 父类参数
    """
    
    def __init__(
        self,
        threshold: float = 0.6,
        adaptive: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        assert 0.0 <= threshold <= 1.0, f"Invalid threshold: {threshold}"
        
        self.threshold = threshold
        self.adaptive = adaptive
    
    def execute(self, result: VDBRetrievalResult) -> bool:
        """
        判断结果是否应该保留。
        
        Args:
            result: VDB 检索结果
        
        Returns:
            True 保留，False 过滤
        """
        from sage.kernel.runtime.communication.packet import StopSignal
        if isinstance(result, StopSignal):
            # FilterFunction 遇到 StopSignal 应该返回 True(让它通过)
            return True
        
        # 自适应阈值：后续 stage 提高阈值
        if self.adaptive:
            threshold = self.threshold + (result.stage - 1) * 0.05
        else:
            threshold = self.threshold
        
        # 标记是否被过滤
        is_filtered = result.score < threshold
        result.filtered = is_filtered
        
        return not is_filtered


class LocalReranker(MapFunction):
    """
    Stage 内局部重排序(BM25)。
    
    特点:
    - 使用 BM25 算法进行轻量级重排序
    - 避免重量级 Cross-Encoder
    - 返回 top-k 结果
    
    Args:
        top_k: 返回 top-k 结果
        k1: BM25 参数 k1(term saturation)
        b: BM25 参数 b(length normalization)
        **kwargs: 父类参数
    """
    
    def __init__(
        self,
        top_k: int = 10,
        k1: float = 1.5,
        b: float = 0.75,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        assert top_k > 0, f"Invalid top_k: {top_k}"
        
        self.top_k = top_k
        self.k1 = k1
        self.b = b
    
    def execute(self, results: list[VDBRetrievalResult]) -> list[VDBRetrievalResult]:
        """
        对结果进行 BM25 重排序。
        
        Args:
            results: VDB 检索结果列表
        
        Returns:
            重排序后的 top-k 结果
        """
        if not results:
            return []
        
        # 提取查询(假设所有结果来自同一查询)
        # 这里简化处理，使用第一个结果的 metadata 中的 query
        # 实际应该从上游传递 query_text
        query_text = results[0].metadata.get("query_text", "")
        
        # 如果没有 query_text，直接按原始分数排序返回
        if not query_text:
            sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
            return sorted_results[:self.top_k]
        
        # 计算 BM25 分数
        bm25_scores = self._compute_bm25(query_text, results)
        
        # 组合原始分数和 BM25 分数(加权)
        for idx, result in enumerate(results):
            original_score = result.score
            bm25_score = bm25_scores[idx]
            # 混合分数：70% 原始相似度 + 30% BM25
            combined_score = 0.7 * original_score + 0.3 * bm25_score
            result.rerank_score = combined_score
        
        # 按重排分数排序
        reranked = sorted(results, key=lambda x: x.rerank_score or x.score, reverse=True)
        
        return reranked[:self.top_k]
    
    def _compute_bm25(
        self,
        query: str,
        results: list[VDBRetrievalResult]
    ) -> list[float]:
        """
        计算 BM25 分数。
        
        BM25(q, d) = Σ IDF(qi) * [f(qi, d) * (k1 + 1)] / [f(qi, d) + k1 * (1 - b + b * |d| / avgdl)]
        
        Args:
            query: 查询文本
            results: 文档列表
        
        Returns:
            每个文档的 BM25 分数
        """
        # 分词
        query_terms = self._tokenize(query)
        doc_contents = [result.content for result in results]
        doc_terms_list = [self._tokenize(content) for content in doc_contents]
        
        # 计算平均文档长度
        total_len = sum(len(terms) for terms in doc_terms_list)
        avgdl = total_len / len(doc_terms_list) if doc_terms_list else 1.0
        
        # 计算 IDF
        N = len(doc_terms_list)
        idf_scores = {}
        for term in set(query_terms):
            # 包含该词的文档数
            df = sum(1 for terms in doc_terms_list if term in terms)
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0) if df > 0 else 0.0
            idf_scores[term] = idf
        
        # 计算每个文档的 BM25 分数
        bm25_scores = []
        for doc_terms in doc_terms_list:
            doc_len = len(doc_terms)
            term_freqs = Counter(doc_terms)
            
            score = 0.0
            for term in query_terms:
                if term not in idf_scores:
                    continue
                
                idf = idf_scores[term]
                tf = term_freqs.get(term, 0)
                
                # BM25 公式
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / avgdl)
                score += idf * (numerator / denominator)
            
            bm25_scores.append(score)
        
        # 归一化到 [0, 1]
        if bm25_scores:
            max_score = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
            bm25_scores = [s / max_score for s in bm25_scores]
        
        return bm25_scores
    
    def _tokenize(self, text: str) -> list[str]:
        """
        简单分词(小写 + 移除标点 + 分割)。
        
        Args:
            text: 输入文本
        
        Returns:
            分词列表
        """
        # 转小写
        text = text.lower()
        # 移除标点，保留字母数字
        text = re.sub(r'[^\w\s]', ' ', text)
        # 分词
        tokens = text.split()
        # 移除停用词(简化版)
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
            "of", "with", "is", "are", "was", "were", "be", "been", "being",
            "what", "which", "who", "when", "where", "why", "how", "its", "it"
        }
        tokens = [t for t in tokens if t not in stopwords and len(t) > 2]
        
        return tokens


class StageAggregator(MapFunction):
    """
    汇聚同一 VDB 不同 stage 的结果。
    
    特点:
    - 合并多个 stage 的结果
    - 去重(基于 doc_id)
    - 保留最高分
    
    Args:
        num_stages: Stage 数量(默认 4)
        **kwargs: 父类参数
    """
    
    def __init__(
        self,
        num_stages: int = 4,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        assert num_stages > 0, f"Invalid num_stages: {num_stages}"
        
        self.num_stages = num_stages
    
    def execute(self, stage_results: list[list[VDBRetrievalResult]]) -> list[VDBRetrievalResult]:
        """
        汇聚多个 stage 的结果。
        
        Args:
            stage_results: 多个 stage 的结果列表
        
        Returns:
            去重并合并后的结果
        """
        # 展平所有结果
        all_results = []
        for stage_res in stage_results:
            if isinstance(stage_res, list):
                all_results.extend(stage_res)
            else:
                all_results.append(stage_res)
        
        if not all_results:
            return []
        
        # 去重：保留每个 doc_id 的最高分
        doc_map: dict[str, VDBRetrievalResult] = {}
        for result in all_results:
            doc_id = result.doc_id
            
            if doc_id not in doc_map:
                doc_map[doc_id] = result
            else:
                # 保留分数更高的
                existing = doc_map[doc_id]
                if result.score > existing.score:
                    doc_map[doc_id] = result
        
        # 转换为列表并排序
        aggregated = list(doc_map.values())
        aggregated.sort(key=lambda x: x.rerank_score or x.score, reverse=True)
        
        return aggregated


class VDBBranchRouter(MapFunction):
    """
    VDB 分支路由器。
    
    根据查询特征将请求路由到不同的 VDB 分支。
    
    Args:
        routing_strategy: 路由策略 ("round_robin" | "category" | "hash")
        **kwargs: 父类参数
    """
    
    def __init__(
        self,
        routing_strategy: str = "round_robin",
        **kwargs
    ):
        super().__init__(**kwargs)
        
        assert routing_strategy in ["round_robin", "category", "hash"], \
            f"Invalid routing_strategy: {routing_strategy}"
        
        self.routing_strategy = routing_strategy
        self._counter = 0
    
    def execute(self, data: JoinedEvent) -> tuple[str, JoinedEvent]:
        """
        路由到 VDB 分支。
        
        Args:
            data: JoinedEvent
        
        Returns:
            (branch_name, data) 元组
        """
        if self.routing_strategy == "round_robin":
            # 轮询
            branch = "vdb1" if self._counter % 2 == 0 else "vdb2"
            self._counter += 1
        
        elif self.routing_strategy == "category":
            # 按类别路由
            # finance/healthcare -> vdb1
            # technology/general -> vdb2
            if data.query.category in ["finance", "healthcare"]:
                branch = "vdb1"
            else:
                branch = "vdb2"
        
        elif self.routing_strategy == "hash":
            # 基于 query_id 哈希
            hash_val = hash(data.query.query_id)
            branch = "vdb1" if hash_val % 2 == 0 else "vdb2"
        
        else:
            branch = "vdb1"  # 默认
        
        return (branch, data)


class VDBResultMerger(MapFunction):
    """
    合并两个 VDB 分支的结果。
    
    Args:
        merge_strategy: 合并策略 ("interleave" | "score_based")
        top_k: 返回 top-k 结果
        **kwargs: 父类参数
    """
    
    def __init__(
        self,
        merge_strategy: str = "score_based",
        top_k: int = 30,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        assert merge_strategy in ["interleave", "score_based"], \
            f"Invalid merge_strategy: {merge_strategy}"
        
        self.merge_strategy = merge_strategy
        self.top_k = top_k
    
    def execute(
        self,
        vdb1_results: list[VDBRetrievalResult],
        vdb2_results: list[VDBRetrievalResult]
    ) -> list[VDBRetrievalResult]:
        """
        合并两个 VDB 的结果。
        
        Args:
            vdb1_results: VDB1 结果
            vdb2_results: VDB2 结果
        
        Returns:
            合并后的结果
        """
        if self.merge_strategy == "score_based":
            # 按分数合并并排序
            all_results = vdb1_results + vdb2_results
            
            # 去重
            doc_map: dict[str, VDBRetrievalResult] = {}
            for result in all_results:
                doc_id = result.doc_id
                if doc_id not in doc_map:
                    doc_map[doc_id] = result
                else:
                    # 保留分数更高的
                    if result.score > doc_map[doc_id].score:
                        doc_map[doc_id] = result
            
            merged = list(doc_map.values())
            merged.sort(key=lambda x: x.rerank_score or x.score, reverse=True)
        
        elif self.merge_strategy == "interleave":
            # 交替合并
            merged = []
            max_len = max(len(vdb1_results), len(vdb2_results))
            
            for i in range(max_len):
                if i < len(vdb1_results):
                    merged.append(vdb1_results[i])
                if i < len(vdb2_results):
                    merged.append(vdb2_results[i])
            
            # 去重
            seen = set()
            deduplicated = []
            for result in merged:
                if result.doc_id not in seen:
                    seen.add(result.doc_id)
                    deduplicated.append(result)
            
            merged = deduplicated
        
        else:
            merged = vdb1_results + vdb2_results
        
        return merged[:self.top_k]


# ===== 辅助函数 =====

def build_vdb_pipeline_stage(
    vdb_name: str,
    stage: int,
    top_k: int,
    filter_threshold: float,
    rerank_top_k: int
) -> tuple[VDBRetriever, VDBResultFilter, LocalReranker]:
    """
    构建单个 VDB stage 的算子链。
    
    Args:
        vdb_name: VDB 名称
        stage: Stage 编号
        top_k: 检索 top-k
        filter_threshold: 过滤阈值
        rerank_top_k: 重排序 top-k
    
    Returns:
        (retriever, filter, reranker) 元组
    """
    retriever = VDBRetriever(
        vdb_name=vdb_name,
        top_k=top_k,
        stage=stage
    )
    
    result_filter = VDBResultFilter(
        threshold=filter_threshold,
        adaptive=True
    )
    
    reranker = LocalReranker(
        top_k=rerank_top_k
    )
    
    return retriever, result_filter, reranker


def build_vdb_4stage_pipeline(
    vdb_name: str,
    config: dict[str, Any] | None = None
) -> list[tuple[VDBRetriever, VDBResultFilter, LocalReranker]]:
    """
    构建完整的 4-stage VDB 检索流水线。
    
    Pipeline 结构:
    Stage 1: top_k=20, filter=0.6, rerank=15
    Stage 2: top_k=15, filter=0.65, rerank=10
    Stage 3: top_k=10, filter=0.7, rerank=8
    Stage 4: top_k=5, no filter, no rerank
    
    Args:
        vdb_name: VDB 名称 ("vdb1" | "vdb2")
        config: 可选配置字典
    
    Returns:
        4 个 stage 的算子链列表
    """
    if config is None:
        config = {}
    
    # Stage 1
    stage1 = build_vdb_pipeline_stage(
        vdb_name=vdb_name,
        stage=1,
        top_k=config.get("stage1_top_k", 20),
        filter_threshold=config.get("stage1_threshold", 0.6),
        rerank_top_k=config.get("stage1_rerank", 15)
    )
    
    # Stage 2
    stage2 = build_vdb_pipeline_stage(
        vdb_name=vdb_name,
        stage=2,
        top_k=config.get("stage2_top_k", 15),
        filter_threshold=config.get("stage2_threshold", 0.65),
        rerank_top_k=config.get("stage2_rerank", 10)
    )
    
    # Stage 3
    stage3 = build_vdb_pipeline_stage(
        vdb_name=vdb_name,
        stage=3,
        top_k=config.get("stage3_top_k", 10),
        filter_threshold=config.get("stage3_threshold", 0.7),
        rerank_top_k=config.get("stage3_rerank", 8)
    )
    
    # Stage 4 (final)
    stage4_retriever = VDBRetriever(
        vdb_name=vdb_name,
        top_k=config.get("stage4_top_k", 5),
        stage=4
    )
    # Stage 4 没有 filter 和 rerank
    stage4 = (stage4_retriever, None, None)
    
    return [stage1, stage2, stage3, stage4]
