"""
Result Aggregation Join Functions for Workload 4
=================================================

使用 Join 算子合并多个检索结果流。

流汇聚策略：
1. VDB1 + VDB2 → MergeVDBResultsJoin → 合并的 VDB 结果
2. (VDB1+VDB2) + Graph → MergeAllResultsJoin → 最终检索结果

Join 语义：
- 按 query_id 分组
- 累积每个 query 的所有检索结果
- 当所有分支都到达时输出合并结果
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from sage.common.core.functions.join_function import BaseJoinFunction

if TYPE_CHECKING:
    try:
        from .models import VDBRetrievalResult, GraphMemoryResult, ClusteringResult, VDBResultsWrapper
    except ImportError:
        from models import VDBRetrievalResult, GraphMemoryResult, ClusteringResult, VDBResultsWrapper
        from models import VDBRetrievalResult, GraphMemoryResult, ClusteringResult


class MergeVDBResultsJoin(BaseJoinFunction):
    """
    合并 VDB1 和 VDB2 的检索结果。
    
    Join 策略：
    - tag=0: VDB1 结果（VDBResultsWrapper）
    - tag=1: VDB2 结果（VDBResultsWrapper）
    - 输出：合并后的结果列表（list[VDBRetrievalResult]）
    """
    
    is_join = True
    join_type = "inner"  # 两个 VDB 结果都必须到达
    
    def __init__(self):
        """初始化 Join 算子"""
        super().__init__()
        # 缓存：key → {0: VDB1_wrapper, 1: VDB2_wrapper}
        self.buffer: dict[str, dict[int, "VDBResultsWrapper"]] = {}

    
    def execute(self, payload: "VDBResultsWrapper", key: str, tag: int) -> list:
        """
        执行 Join 逻辑。
        
        Args:
            payload: 检索结果包装器（VDBResultsWrapper）
            key: query_id（用于分组）
            tag: 流标识（0=VDB1, 1=VDB2）
        
        Returns:
            如果两个 VDB 结果都到达，返回合并后的结果列表；否则返回空列表
        """
        self.logger.debug(f"[EXEC] Received vdb={payload.vdb_name}, key={key}, tag={tag}")
        
        # 初始化该 key 的 buffer
        if key not in self.buffer:
            self.buffer[key] = {}
        
        # 存储当前结果
        self.buffer[key][tag] = payload
        
        self.logger.debug(f"[EXEC] Buffer for key={key} now has {len(self.buffer[key])} entries")
        
        # 检查是否两个分支都到达了
        if len(self.buffer[key]) == 2:
            vdb1_wrapper = self.buffer[key][0]
            vdb2_wrapper = self.buffer[key][1]
            
            self.logger.info(
                f"[EXEC] Merging key={key}: "
                f"{vdb1_wrapper.vdb_name}({len(vdb1_wrapper.results)}) + "
                f"{vdb2_wrapper.vdb_name}({len(vdb2_wrapper.results)})"
            )
            
            # 合并两个 VDB 的检索结果列表
            merged_vdb_results = vdb1_wrapper.results + vdb2_wrapper.results
            
            # 从任一 wrapper 恢复 GraphEnrichedEvent（两个应该相同）
            source_event = vdb1_wrapper.source_event or vdb2_wrapper.source_event
            
            # 清理 buffer
            del self.buffer[key]
            
            # 返回元组：(joined_event, graph_results, vdb_results)
            if source_event:
                return (source_event.joined_event, source_event.graph_results, merged_vdb_results)
            else:
                # 如果没有 source_event（不应该发生），返回空的占位符
                return (None, [], merged_vdb_results)
        
        # 还没有收集齐所有分支，返回空列表
        return []


class MergeAllResultsJoin(BaseJoinFunction):
    """
    合并所有检索结果（VDB + Graph）。
    
    Join 策略：
    - tag=0: 合并的 VDB 结果（来自 MergeVDBResultsJoin）
    - tag=1: Graph Memory 结果
    - 输出：ClusteringResult（包含所有检索结果，准备进入聚类阶段）
    """
    
    is_join = True
    join_type = "inner"  # 两个结果都必须到达
    
    def __init__(self):
        """初始化 Join 算子"""
        super().__init__()
        # 缓存：key → {0: VDB_merged, 1: Graph_result}
        self.buffer: dict[str, dict[int, VDBRetrievalResult | GraphMemoryResult]] = {}
    
    def execute(
        self,
        payload: VDBRetrievalResult | GraphMemoryResult,
        key: str,
        tag: int
    ) -> list[ClusteringResult]:
        """
        执行最终 Join 逻辑。
        
        Args:
            payload: VDB 合并结果或 Graph 结果
            key: query_id（用于分组）
            tag: 流标识（0=VDB merged, 1=Graph）
        
        Returns:
            如果所有结果都到达，返回 ClusteringResult 列表；否则返回空列表
        """
        # 初始化该 key 的 buffer
        if key not in self.buffer:
            self.buffer[key] = {}
        
        # 存储当前结果
        self.buffer[key][tag] = payload
        
        # 检查是否两个分支都到达了
        if len(self.buffer[key]) == 2:
            vdb_merged = self.buffer[key][0]  # VDBRetrievalResult
            graph_result = self.buffer[key][1]  # GraphMemoryResult
            
            # 合并所有检索结果到 ClusteringResult
            # 注意：这里直接传递数据，实际的聚类逻辑在 DBSCANClusteringOperator 中
            from .models import ClusteringResult
            
            # 合并所有文档和嵌入
            all_docs = vdb_merged.retrieved_docs + [
                {"text": node.get("text", ""), "source": "graph"}
                for node in graph_result.retrieved_nodes
            ]
            all_embeddings = []  # TODO: 从文档中提取嵌入（如果有）
            
            clustering_result = ClusteringResult(
                query=vdb_merged.query,
                all_docs=all_docs,
                all_embeddings=all_embeddings,
                cluster_labels=[],  # 空列表，待聚类算子填充
                cluster_centers=[],
                num_clusters=0,
                duplicates_removed=0,
                clustering_time=0.0,
            )
            
            # 清理 buffer
            del self.buffer[key]
            
            return [clustering_result]
        
        # 还没有收集到所有分支的数据
        return []
