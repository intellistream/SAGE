import os
import json
import requests
from typing import Tuple, List, Any, Dict
from .tools.template import AI_Template
from sage_core.function.map_function import MapFunction
from sage_core.function.flatmap_function import FlatMapFunction
from sage_utils.custom_logger import CustomLogger

class BochaSearchTool(MapFunction):
    """
    改进的Bocha搜索工具 - 与AI_Template深度集成
    输入: Tuple[AI_Template, List[str]] (来自SearchBot的输出)
    输出: AI_Template (将搜索结果整合到retriver_chunks中)
    """

    def __init__(self, api_key: str = None, max_results_per_query: int = 3, **kwargs):
        super().__init__(**kwargs)
        
        self.url = "https://api.bochaai.com/v1/web-search"
        self.api_key = api_key or "sk-455d6a2c79464dd2959197477a908e53"
        self.max_results_per_query = max_results_per_query
        
        self.headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
        self.search_count = 0
        
        self.logger.info(f"BochaSearchTool initialized with max_results_per_query: {max_results_per_query}")

    def _execute_single_search(self, query: str) -> Dict[str, Any]:
        """
        执行单个搜索查询
        
        Args:
            query: 搜索查询字符串
            
        Returns:
            Dict: 搜索API的原始响应
        """
        payload = json.dumps({
            "query": query,
            "summary": True,
            "count": 10,
            "page": 1
        })
        
        try:
            response = requests.post(self.url, headers=self.headers, data=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Search API request failed for query '{query}': {e}")
            return {"error": str(e), "data": {"webPages": {"value": []}}}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse search API response for query '{query}': {e}")
            return {"error": "JSON decode error", "data": {"webPages": {"value": []}}}

    def _extract_search_results(self, api_response: Dict[str, Any], query: str) -> List[str]:
        """
        从搜索API响应中提取有用的文本片段
        
        Args:
            api_response: 搜索API的响应
            query: 原始查询（用于标记来源）
            
        Returns:
            List[str]: 提取的文本片段列表
        """
        extracted_chunks = []
        
        try:
            # 检查是否有错误
            if "error" in api_response:
                error_chunk = f"[Search Error for '{query}']: {api_response['error']}"
                extracted_chunks.append(error_chunk)
                return extracted_chunks
            
            # 提取网页结果
            web_pages = api_response.get("data", {}).get("webPages", {}).get("value", [])
            
            for i, page in enumerate(web_pages[:self.max_results_per_query]):
                # 构建结构化的搜索结果片段
                title = page.get("name", "No Title")
                snippet = page.get("snippet", "No content available")
                url = page.get("url", "No URL")
                
                # 创建格式化的搜索结果
                result_chunk = f"""[Search Result {i+1} for '{query}']
Title: {title}
Content: {snippet}
Source: {url}"""
                
                extracted_chunks.append(result_chunk)
            
            # 如果没有找到结果
            if not extracted_chunks:
                no_results_chunk = f"[No search results found for query: '{query}']"
                extracted_chunks.append(no_results_chunk)
                
        except Exception as e:
            self.logger.error(f"Error extracting search results for query '{query}': {e}")
            error_chunk = f"[Extraction Error for '{query}']: {str(e)}"
            extracted_chunks.append(error_chunk)
        
        return extracted_chunks

    def _log_search_summary(self, template: AI_Template, queries: List[str], total_new_chunks: int):
        """记录搜索摘要信息"""
        original_chunks = len(template.retriver_chunks) if template.retriver_chunks else 0
        
        self.logger.info(f"Search completed: "
                        f"Queries={len(queries)}, "
                        f"Original_chunks={original_chunks}, "
                        f"New_chunks={total_new_chunks}, "
                        f"Template_UUID={template.uuid}")

    def execute(self, data: Tuple[AI_Template, List[str]]) -> AI_Template:
        """
        执行搜索并将结果集成到AI_Template中
        
        Args:
            data: (AI_Template, List[str]) 来自SearchBot的输出
            
        Returns:
            AI_Template: 更新了retriver_chunks的模板
        """
        try:
            template, search_queries = data
            
            self.logger.debug(f"BochaSearchTool processing {len(search_queries)} queries for template {template.uuid}")
            
            # 如果没有搜索查询，直接返回原模板
            if not search_queries:
                self.logger.info("No search queries provided, returning original template")
                return template
            
            # 保存原始的retriver_chunks数量
            original_chunks_count = len(template.retriver_chunks) if template.retriver_chunks else 0
            
            # 确保retriver_chunks被初始化
            if template.retriver_chunks is None:
                template.retriver_chunks = []
            
            # 执行所有搜索查询
            all_new_chunks = []
            
            for i, query in enumerate(search_queries, 1):
                self.logger.debug(f"Executing search {i}/{len(search_queries)}: {query}")
                
                # 执行单个搜索
                api_response = self._execute_single_search(query)
                
                # 提取搜索结果
                query_chunks = self._extract_search_results(api_response, query)
                
                # 添加到新片段列表
                all_new_chunks.extend(query_chunks)
                
                self.logger.debug(f"Query '{query}' returned {len(query_chunks)} chunks")
            
            # 将新的搜索结果添加到template的retriver_chunks中
            template.retriver_chunks.extend(all_new_chunks)
            
            # 更新搜索计数
            self.search_count += 1
            
            # 记录搜索摘要
            self._log_search_summary(template, search_queries, len(all_new_chunks))
            
            # 可选：将搜索查询也保存到response字段作为记录
            search_summary = {
                "search_queries_executed": search_queries,
                "results_count": len(all_new_chunks),
                "original_chunks_count": original_chunks_count,
                "search_timestamp": template.timestamp
            }
            
            template.response = json.dumps(search_summary, indent=2, ensure_ascii=False)
            
            return template
            
        except Exception as e:
            self.logger.error(f"BochaSearchTool execution failed: {e}")
            
            # 错误处理：在response字段记录错误信息
            error_info = {
                "error": str(e),
                "search_queries": search_queries if 'search_queries' in locals() else [],
                "error_timestamp": template.timestamp if 'template' in locals() else None
            }
            
            if 'template' in locals():
                template.response = json.dumps(error_info, indent=2, ensure_ascii=False)
                return template
            else:
                # 如果连template都无法访问，创建一个错误template
                error_template = AI_Template(raw_question="Error in search processing")
                error_template.response = json.dumps(error_info, indent=2, ensure_ascii=False)
                return error_template

class EnhancedBochaSearchTool(BochaSearchTool):
    """
    增强版Bocha搜索工具，支持更多定制化选项
    """
    
    def __init__(self, api_key: str = None, max_results_per_query: int = 3, 
                 deduplicate_results: bool = True, 
                 max_total_chunks: int = 20,
                 preserve_chunk_order: bool = True, **kwargs):
        super().__init__(api_key, max_results_per_query, **kwargs)
        
        self.deduplicate_results = deduplicate_results
        self.max_total_chunks = max_total_chunks
        self.preserve_chunk_order = preserve_chunk_order
        
        self.logger.info(f"EnhancedBochaSearchTool initialized: "
                        f"deduplicate={deduplicate_results}, "
                        f"max_total={max_total_chunks}")

    def _deduplicate_chunks(self, chunks: List[str]) -> List[str]:
        """去重处理，保持顺序"""
        if not self.deduplicate_results:
            return chunks
        
        seen = set()
        deduplicated = []
        
        for chunk in chunks:
            # 使用内容的hash来判断重复
            chunk_hash = hash(chunk.strip().lower())
            if chunk_hash not in seen:
                seen.add(chunk_hash)
                deduplicated.append(chunk)
        
        return deduplicated

    def _limit_total_chunks(self, template: AI_Template) -> None:
        """限制总的chunk数量"""
        if len(template.retriver_chunks) > self.max_total_chunks:
            if self.preserve_chunk_order:
                # 保持原有顺序，截取最新的chunks
                template.retriver_chunks = template.retriver_chunks[-self.max_total_chunks:]
            else:
                # 随机保留
                import random
                template.retriver_chunks = random.sample(template.retriver_chunks, self.max_total_chunks)
            
            self.logger.info(f"Limited chunks to {self.max_total_chunks} items")

    def execute(self, data: Tuple[AI_Template, List[str]]) -> AI_Template:
        """增强版执行逻辑"""
        # 先执行基础搜索
        template = super().execute(data)
        
        # 应用增强功能
        if template.retriver_chunks:
            # 去重处理
            original_count = len(template.retriver_chunks)
            template.retriver_chunks = self._deduplicate_chunks(template.retriver_chunks)
            
            if len(template.retriver_chunks) < original_count:
                self.logger.info(f"Deduplicated {original_count - len(template.retriver_chunks)} chunks")
            
            # 限制总数量
            self._limit_total_chunks(template)
        
        return template