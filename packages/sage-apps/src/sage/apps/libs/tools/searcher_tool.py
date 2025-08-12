import os
import json
import requests
import time
from typing import Tuple, List, Any, Dict
from ..context.model_context import ModelContext
from ..context.search_result import SearchResult
from ..context.search_query_results import SearchQueryResults
from ..context.search_session import SearchSession
from sage.core.api.function.map_function import MapFunction
from sage.common.utils.logging.custom_logger import CustomLogger

class BochaSearchTool(MapFunction):
    """
    改进的Bocha搜索工具 - 使用新的分层搜索结果结构
    输入: ModelContext (包含搜索查询)
    输出: ModelContext (包含结构化的搜索结果)
    """

    def __init__(self, config: dict, **kwargs):
        super().__init__(**kwargs)
        
        self.url = config.get("url", "https://api.bochasearch.com/search")
        self.api_key = config.get("api_key", os.getenv("BOCHA_API_KEY"))
        self.max_results_per_query = config.get("max_results_per_query", 3)
        self.search_engine_name = config.get("search_engine_name", "Bocha")
        
        if not self.api_key:
            raise ValueError("BOCHA_API_KEY is required. Set it in environment variables or config.")
        
        self.headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
        self.search_count = 0
        
        self.logger.info(f"BochaSearchTool initialized with max_results_per_query: {self.max_results_per_query}")

    def _execute_single_search(self, query: str) -> Dict[str, Any]:
        """
        执行单个搜索查询
        
        Args:
            query: 搜索查询字符串
            
        Returns:
            Dict: 搜索API的原始响应
        """
        start_time = time.time()
        
        payload = json.dumps({
            "query": query,
            "summary": True,
            "count": max(10, self.max_results_per_query * 2),  # 请求更多结果以便筛选
            "page": 1
        })
        
        try:
            self.logger.debug(f"Executing search for query: '{query}'")
            response = requests.post(self.url, headers=self.headers, data=payload, timeout=30)
            response.raise_for_status()
            
            execution_time = int((time.time() - start_time) * 1000)
            result = response.json()
            result["_execution_time_ms"] = execution_time
            
            return result
            
        except requests.exceptions.RequestException as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.logger.error(f"Search API request failed for query '{query}': {e}")
            return {
                "error": str(e), 
                "data": {"webPages": {"value": []}},
                "_execution_time_ms": execution_time
            }
        except json.JSONDecodeError as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.logger.error(f"Failed to parse search API response for query '{query}': {e}")
            return {
                "error": "JSON decode error", 
                "data": {"webPages": {"value": []}},
                "_execution_time_ms": execution_time
            }

    def _convert_api_response_to_search_results(self, api_response: Dict[str, Any], query: str) -> List[SearchResult]:
        """
        将搜索API响应转换为SearchResult对象列表
        
        Args:
            api_response: 搜索API的响应
            query: 原始查询
            
        Returns:
            List[SearchResult]: 搜索结果对象列表
        """
        search_results = []
        
        try:
            # 检查是否有错误
            if "error" in api_response:
                error_result = SearchResult(
                    title=f"Search Error for '{query}'",
                    content=f"Error: {api_response['error']}",
                    source="Error",
                    rank=1,
                    relevance_score=0.0
                )
                search_results.append(error_result)
                return search_results
            
            # 提取网页结果
            web_pages = api_response.get("data", {}).get("webPages", {}).get("value", [])
            
            for i, page in enumerate(web_pages[:self.max_results_per_query]):
                title = page.get("name", "No Title").strip()
                content = page.get("snippet", "No content available").strip()
                source = page.get("url", "No URL").strip()
                
                # 计算相关性分数（简单的基于排名的分数）
                relevance_score = max(0.1, 1.0 - (i * 0.1))
                
                search_result = SearchResult(
                    title=title,
                    content=content,
                    source=source,
                    rank=i + 1,
                    relevance_score=relevance_score
                )
                
                search_results.append(search_result)
            
            # 如果没有找到结果
            if not search_results:
                no_results = SearchResult(
                    title=f"No Results for '{query}'",
                    content=f"No search results found for query: '{query}'",
                    source="Search Engine",
                    rank=1,
                    relevance_score=0.0
                )
                search_results.append(no_results)
                
        except Exception as e:
            self.logger.error(f"Error converting API response for query '{query}': {e}")
            error_result = SearchResult(
                title=f"Conversion Error for '{query}'",
                content=f"Error processing search results: {str(e)}",
                source="Error",
                rank=1,
                relevance_score=0.0
            )
            search_results.append(error_result)
        
        return search_results

    def _create_legacy_chunks_for_compatibility(self, search_session: SearchSession) -> List[str]:
        """
        为向后兼容性创建legacy格式的retriver_chunks
        
        Args:
            search_session: 搜索会话对象
            
        Returns:
            List[str]: legacy格式的搜索结果字符串列表
        """
        legacy_chunks = []
        
        for query_result in search_session.query_results:
            for result in query_result.results:
                legacy_chunk = f"""[Search Result {result.rank} for '{query_result.query}']
Title: {result.title}
Content: {result.content}
Source: {result.source}"""
                legacy_chunks.append(legacy_chunk)
        
        return legacy_chunks

    def _log_search_summary(self, context: ModelContext, total_queries: int, total_results: int):
        """记录搜索摘要信息"""
        original_chunks = len(context.retriver_chunks) if context.retriver_chunks else 0
        
        self.logger.info(f"Search completed: "
                        f"Queries={total_queries}, "
                        f"Total_results={total_results}, "
                        f"Original_chunks={original_chunks}, "
                        f"Context_UUID={context.uuid}")

    def execute(self, context: ModelContext) -> ModelContext:
        """
        执行搜索并将结果集成到ModelContext中
        
        Args:
            context: ModelContext对象，包含搜索查询
            
        Returns:
            ModelContext: 更新了搜索结果的上下文
        """
        try:
            # 获取搜索查询
            search_queries = context.get_search_queries()
            self.logger.debug(f"BochaSearchTool processing {len(search_queries)} queries for context {context.uuid}")
            
            # 如果没有搜索查询，直接返回原上下文
            if not search_queries:
                self.logger.info("No search queries provided, returning original context")
                return context
            
            # 创建搜索会话（如果还没有）
            if not context.search_session:
                context.create_search_session(context.raw_question)
            
            # 执行所有搜索查询
            total_results = 0
            
            for query in search_queries:
                self.logger.debug(f"Executing search for query: '{query}'")
                
                # 执行搜索
                api_response = self._execute_single_search(query)
                execution_time = api_response.get("_execution_time_ms", 0)
                
                # 转换为SearchResult对象
                search_results = self._convert_api_response_to_search_results(api_response, query)
                
                # 计算总结果数（从API响应中获取，如果可用）
                total_count_from_api = len(api_response.get("data", {}).get("webPages", {}).get("value", []))
                
                # 添加搜索结果到上下文
                context.add_search_results(
                    query=query,
                    results=search_results,
                    search_engine=self.search_engine_name,
                    execution_time_ms=execution_time,
                    total_results_count=total_count_from_api
                )
                
                total_results += len(search_results)
                
                self.logger.debug(f"Query '{query}' returned {len(search_results)} results")
            
            # 为向后兼容性更新retriver_chunks
            if context.search_session:
                legacy_chunks = self._create_legacy_chunks_for_compatibility(context.search_session)
                if context.retriver_chunks is None:
                    context.retriver_chunks = []
                context.retriver_chunks.extend(legacy_chunks)
            
            # 更新搜索计数
            self.search_count += 1
            
            # 记录搜索摘要
            self._log_search_summary(context, len(search_queries), total_results)
            
            # 更新工具配置记录搜索执行信息
            search_execution_info = {
                "bocha_search_executed": True,
                "queries_count": len(search_queries),
                "total_results": total_results,
                "search_engine": self.search_engine_name,
                "execution_timestamp": int(time.time() * 1000),
                "session_id": context.search_session.session_id if context.search_session else None
            }
            
            context.update_tool_config({"bocha_search_info": search_execution_info})
            
            return context
            
        except Exception as e:
            self.logger.error(f"BochaSearchTool execution failed: {e}", exc_info=True)
            
            # 错误处理：记录错误到工具配置中
            error_info = {
                "bocha_search_error": str(e),
                "error_timestamp": int(time.time() * 1000),
                "attempted_queries": search_queries if 'search_queries' in locals() else []
            }
            
            context.update_tool_config({"bocha_search_error": error_info})
            
            return context

class EnhancedBochaSearchTool(BochaSearchTool):
    """
    增强版Bocha搜索工具，支持更多定制化选项和结果优化
    使用新的分层搜索结构和ModelContext
    """
    
    def __init__(self, config: dict, **kwargs):
        super().__init__(config, **kwargs)
        
        self.deduplicate_results = config.get("deduplicate_results", True)
        self.max_total_chunks = config.get("max_total_chunks", 20)
        self.preserve_chunk_order = config.get("preserve_chunk_order", True)
        self.min_relevance_score = config.get("min_relevance_score", 0.1)
        self.diversity_threshold = config.get("diversity_threshold", 0.8)  # 多样性阈值
        
        self.logger.info(f"EnhancedBochaSearchTool initialized: "
                        f"deduplicate={self.deduplicate_results}, "
                        f"max_total={self.max_total_chunks}, "
                        f"min_relevance={self.min_relevance_score}")

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """计算两个内容的相似度（简单的词汇重叠）"""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def _deduplicate_search_results(self, search_results: List[SearchResult]) -> List[SearchResult]:
        """去重和多样性优化搜索结果"""
        if not self.deduplicate_results or not search_results:
            return search_results
        
        # 按相关性分数排序
        sorted_results = sorted(search_results, key=lambda x: x.relevance_score, reverse=True)
        
        deduplicated = []
        seen_sources = set()
        
        for result in sorted_results:
            # 检查是否已有相同源
            if result.source in seen_sources:
                continue
            
            # 检查与已选结果的相似度
            is_diverse = True
            for existing in deduplicated:
                similarity = self._calculate_content_similarity(result.content, existing.content)
                if similarity > self.diversity_threshold:
                    is_diverse = False
                    break
            
            # 检查相关性分数阈值
            if result.relevance_score >= self.min_relevance_score and is_diverse:
                deduplicated.append(result)
                seen_sources.add(result.source)
        
        # 保持原有排名顺序（如果要求保持顺序）
        if self.preserve_chunk_order:
            # 按原来的rank排序
            deduplicated = sorted(deduplicated, key=lambda x: x.rank)
        
        return deduplicated

    def _optimize_search_session(self, context: ModelContext) -> None:
        """优化搜索会话结果"""
        if not context.search_session or not context.search_session.query_results:
            return
        
        total_optimized = 0
        
        for query_result in context.search_session.query_results:
            original_count = len(query_result.results)
            
            # 应用去重和多样性优化
            query_result.results = self._deduplicate_search_results(query_result.results)
            
            optimized_count = len(query_result.results)
            total_optimized += (original_count - optimized_count)
            
            if original_count != optimized_count:
                self.logger.debug(f"Query '{query_result.query}': "
                                f"optimized from {original_count} to {optimized_count} results")
        
        if total_optimized > 0:
            self.logger.info(f"Search optimization removed {total_optimized} duplicate/low-quality results")

    def _limit_total_results(self, context: ModelContext) -> None:
        """限制总的搜索结果数量"""
        if not context.search_session:
            return
        
        total_results = context.search_session.get_total_results_count()
        
        if total_results <= self.max_total_chunks:
            return
        
        # 收集所有结果并按相关性排序
        all_results = []
        for query_result in context.search_session.query_results:
            for result in query_result.results:
                all_results.append((query_result, result))
        
        # 按相关性分数排序
        all_results.sort(key=lambda x: x[1].relevance_score, reverse=True)
        
        # 清空现有结果
        for query_result in context.search_session.query_results:
            query_result.results = []
        
        # 重新分配最佳结果，保持每个查询至少有一个结果
        results_per_query = self.max_total_chunks // len(context.search_session.query_results)
        remaining_slots = self.max_total_chunks % len(context.search_session.query_results)
        
        query_result_counts = {qr: 0 for qr in context.search_session.query_results}
        
        for query_result, result in all_results:
            current_count = query_result_counts[query_result]
            max_for_this_query = results_per_query + (1 if remaining_slots > 0 else 0)
            
            if current_count < max_for_this_query:
                query_result.results.append(result)
                query_result_counts[query_result] += 1
                
                if current_count + 1 == max_for_this_query and remaining_slots > 0:
                    remaining_slots -= 1
                
                if sum(query_result_counts.values()) >= self.max_total_chunks:
                    break
        
        new_total = context.search_session.get_total_results_count()
        self.logger.info(f"Limited search results from {total_results} to {new_total}")

    def _update_legacy_chunks(self, context: ModelContext) -> None:
        """更新legacy格式的retriver_chunks以反映优化后的结果"""
        if not context.search_session:
            return
        
        # 重新生成legacy chunks
        optimized_chunks = self._create_legacy_chunks_for_compatibility(context.search_session)
        
        # 合并到现有chunks中（保持之前可能存在的非搜索chunks）
        non_search_chunks = []
        if context.retriver_chunks:
            # 尝试识别非搜索chunks（不包含"[Search Result"标记的）
            for chunk in context.retriver_chunks:
                if not chunk.strip().startswith("[Search Result"):
                    non_search_chunks.append(chunk)
        
        context.retriver_chunks = non_search_chunks + optimized_chunks

    def execute(self, context: ModelContext) -> ModelContext:
        """增强版执行逻辑，包含结果优化"""
        try:
            # 先执行基础搜索
            context = super().execute(context)
            
            # 应用增强功能
            if context.search_session and context.search_session.query_results:
                # 1. 优化搜索会话结果（去重、多样性）
                self._optimize_search_session(context)
                
                # 2. 限制总结果数量
                self._limit_total_results(context)
                
                # 3. 更新legacy chunks以反映优化
                self._update_legacy_chunks(context)
                
                # 4. 更新工具配置记录优化信息
                optimization_info = {
                    "enhanced_search_applied": True,
                    "deduplicate_results": self.deduplicate_results,
                    "max_total_chunks": self.max_total_chunks,
                    "min_relevance_score": self.min_relevance_score,
                    "final_results_count": context.search_session.get_total_results_count(),
                    "final_chunks_count": len(context.retriver_chunks) if context.retriver_chunks else 0
                }
                
                context.update_tool_config({"enhanced_search_info": optimization_info})
                
                self.logger.info(f"Enhanced search completed: {optimization_info['final_results_count']} results, "
                               f"{optimization_info['final_chunks_count']} chunks")
            
            return context
            
        except Exception as e:
            self.logger.error(f"EnhancedBochaSearchTool execution failed: {e}", exc_info=True)
            
            # 错误处理：记录错误并继续基础搜索结果
            error_info = {
                "enhanced_search_error": str(e),
                "error_timestamp": int(time.time() * 1000),
                "fallback_to_basic": True
            }
            
            context.update_tool_config({"enhanced_search_error": error_info})
            
            return context