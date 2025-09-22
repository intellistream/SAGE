import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Tuple, Optional
from enum import Enum
from uuid import uuid4
import time
from pathlib import Path

from .search_result import SearchResult
from .search_session import SearchSession
from .search_query_results import SearchQueryResults
from .critic_evaluation import CriticEvaluation
from .quality_label import QualityLabel


@dataclass
class ModelContext:
    # Packet metadata
    sequence: int = 0
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    # Generator content
    raw_question: str = None
    # 保留原有的retriver_chunks用于向后兼容，但优先使用search_session
    retriver_chunks: List[str] = field(default_factory=list)
    # 新的分层搜索结果结构
    search_session: Optional[SearchSession] = None
    prompts: List[Dict[str, str]] = field(default_factory=list)
    response: str = None
    uuid: str = field(default_factory=lambda: str(uuid4()))
    tool_name: str = None
    evaluation: CriticEvaluation = None
    # Tool configuration - 存储工具相关的配置和中间结果
    tool_config: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """格式化显示ModelContext内容"""
        # 时间格式化
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', 
                                     time.localtime(self.timestamp / 1000))
        
        # 构建输出字符串
        output_lines = []
        output_lines.append("=" * 80)
        
        # 标题行
        title_parts = [f"🤖 AI Processing Result [ID: {self.uuid[:8]}]"]
        if self.tool_name:
            tool_emoji = self._get_tool_emoji(self.tool_name)
            title_parts.append(f"{tool_emoji} Tool: {self.tool_name}")
        
        output_lines.append(" | ".join(title_parts))
        output_lines.append(f"📅 Time: {timestamp_str} | Sequence: {self.sequence}")
        
        # 评估状态行
        if self.evaluation:
            quality_emoji = self._get_quality_emoji(self.evaluation.label)
            status_parts = [
                f"{quality_emoji} Quality: {self.evaluation.label.value}",
                f"Confidence: {self.evaluation.confidence:.2f}",
                f"Output Ready: {'✅' if self.evaluation.ready_for_output else '❌'}"
            ]
            output_lines.append("📊 " + " | ".join(status_parts))
        
        output_lines.append("=" * 80)
        
        # 原始问题
        if self.raw_question:
            output_lines.append(f"❓ Original Question:")
            output_lines.append(f"   {self.raw_question}")
            output_lines.append("")
        
        # 工具配置信息
        if self.tool_config:
            output_lines.append(f"🔧 Tool Configuration:")
            self._format_tool_config(output_lines)
            output_lines.append("")
        
        # 搜索结果信息（优先使用新的search_session结构）
        if self.search_session and self.search_session.query_results:
            output_lines.append(f"🔍 Search Results ({self.search_session.get_total_results_count()} total):")
            self._format_search_session(output_lines)
            output_lines.append("")
        elif self.retriver_chunks:
            # 向后兼容：显示老格式的检索结果
            output_lines.append(f"📚 Retrieved Information ({len(self.retriver_chunks)} sources):")
            for i, chunk in enumerate(self.retriver_chunks[:3], 1):
                preview = chunk[:150] + "..." if len(chunk) > 150 else chunk
                output_lines.append(f"   [{i}] {preview}")
            
            if len(self.retriver_chunks) > 3:
                output_lines.append(f"   ... and {len(self.retriver_chunks) - 3} more sources")
            output_lines.append("")
        
        # 处理步骤信息
        if self.prompts:
            output_lines.append(f"⚙️  Processing Steps:")
            system_prompts = [p for p in self.prompts if p.get('role') == 'system']
            user_prompts = [p for p in self.prompts if p.get('role') == 'user']
            
            if system_prompts:
                output_lines.append(f"   • System instructions: {len(system_prompts)} phases")
            if user_prompts:
                last_user_prompt = user_prompts[-1].get('content', '')
                if last_user_prompt and last_user_prompt != self.raw_question:
                    preview = last_user_prompt[:100] + "..." if len(last_user_prompt) > 100 else last_user_prompt
                    output_lines.append(f"   • Specific task: {preview}")
            output_lines.append("")
        
        # AI响应
        if self.response:
            output_lines.append(f"🎯 AI Response:")
            response_lines = self.response.split('\n')
            for line in response_lines:
                output_lines.append(f"   {line}")
            output_lines.append("")
        
        # 评估详情
        if self.evaluation:
            output_lines.append(f"🔍 Evaluation Details:")
            output_lines.append(f"   • Reasoning: {self.evaluation.reasoning}")
            
            if self.evaluation.specific_issues:
                output_lines.append(f"   • Issues: {', '.join(self.evaluation.specific_issues)}")
            
            if self.evaluation.suggestions:
                output_lines.append(f"   • Suggestions: {', '.join(self.evaluation.suggestions)}")
            
            if self.evaluation.should_return_to_chief:
                output_lines.append(f"   • ⚠️  Should return to Chief for reprocessing")
            output_lines.append("")
        
        # 状态指示
        status_indicators = []
        if self.tool_name:
            status_indicators.append(f"Tool: {self.tool_name}")
        if self.response:
            status_indicators.append("✅ Response Generated")
        else:
            status_indicators.append("⏳ Processing")
        
        # 搜索结果状态
        total_results = 0
        if self.search_session:
            total_results = self.search_session.get_total_results_count()
            status_indicators.append(f"🔍 {total_results} search results")
        elif self.retriver_chunks:
            total_results = len(self.retriver_chunks)
            status_indicators.append(f"📊 {total_results} chunks")
        
        if self.evaluation:
            status_indicators.append(f"🔍 Evaluated ({self.evaluation.label.value})")
        if self.tool_config:
            status_indicators.append(f"🔧 Tool Config")
        
        if status_indicators:
            output_lines.append(f"📋 Status: {' | '.join(status_indicators)}")
            output_lines.append("")
        
        output_lines.append("=" * 80)
        return '\n'.join(output_lines)

    def _format_search_session(self, output_lines: List[str]) -> None:
        """格式化搜索会话的显示"""
        for i, query_result in enumerate(self.search_session.query_results, 1):
            output_lines.append(f"   Query {i}: '{query_result.query}' ({query_result.get_results_count()} results)")
            
            # 显示前3个结果
            for j, result in enumerate(query_result.get_top_results(3), 1):
                title_preview = result.title[:80] + "..." if len(result.title) > 80 else result.title
                content_preview = result.content[:100] + "..." if len(result.content) > 100 else result.content
                output_lines.append(f"     [{j}] {title_preview}")
                output_lines.append(f"         {content_preview}")
                output_lines.append(f"         Source: {result.source}")
            
            if query_result.get_results_count() > 3:
                output_lines.append(f"     ... and {query_result.get_results_count() - 3} more results")

    def _format_tool_config(self, output_lines: List[str]) -> None:
        """格式化工具配置信息的显示"""
        for key, value in self.tool_config.items():
            if key == "search_queries":
                if isinstance(value, list) and value:
                    output_lines.append(f"   • Search Queries ({len(value)}):")
                    for i, query in enumerate(value[:5], 1):
                        preview = query[:80] + "..." if len(query) > 80 else query
                        output_lines.append(f"     [{i}] {preview}")
                    if len(value) > 5:
                        output_lines.append(f"     ... and {len(value) - 5} more queries")
                else:
                    output_lines.append(f"   • Search Queries: {value}")
            
            elif key == "search_analysis":
                if isinstance(value, dict):
                    output_lines.append(f"   • Search Analysis:")
                    if "analysis" in value:
                        analysis_text = value["analysis"][:100] + "..." if len(str(value["analysis"])) > 100 else value["analysis"]
                        output_lines.append(f"     - Analysis: {analysis_text}")
                    if "reasoning" in value:
                        reasoning_text = value["reasoning"][:100] + "..." if len(str(value["reasoning"])) > 100 else value["reasoning"]
                        output_lines.append(f"     - Reasoning: {reasoning_text}")
                else:
                    output_lines.append(f"   • Search Analysis: {value}")
            
            elif key == "optimization_metadata":
                if isinstance(value, dict):
                    output_lines.append(f"   • Optimization Metadata:")
                    for meta_key, meta_value in value.items():
                        if isinstance(meta_value, (str, int, float, bool)):
                            output_lines.append(f"     - {meta_key}: {meta_value}")
                        else:
                            output_lines.append(f"     - {meta_key}: {type(meta_value).__name__}")
                else:
                    output_lines.append(f"   • Optimization Metadata: {value}")
            
            else:
                if isinstance(value, (list, dict)):
                    output_lines.append(f"   • {key.replace('_', ' ').title()}: {type(value).__name__}({len(value)} items)")
                else:
                    value_str = str(value)
                    if len(value_str) > 50:
                        value_str = value_str[:50] + "..."
                    output_lines.append(f"   • {key.replace('_', ' ').title()}: {value_str}")

    def _get_tool_emoji(self, tool_name: str) -> str:
        """根据工具名称返回对应的emoji"""
        tool_emojis = {
            "web_search": "🔍",
            "knowledge_retrieval": "📖",
            "calculator": "🧮",
            "code_executor": "💻",
            "data_analyzer": "📊",
            "translation": "🌐",
            "summarizer": "📝",
            "fact_checker": "✅",
            "image_analyzer": "🖼️",
            "weather_service": "🌤️",
            "stock_market": "📈",
            "news_aggregator": "📰",
            "direct_response": "💭",
            "error_handler": "⚠️"
        }
        return tool_emojis.get(tool_name, "🔧")

    def _get_quality_emoji(self, quality_label: QualityLabel) -> str:
        """根据质量标签返回对应的emoji"""
        quality_emojis = {
            QualityLabel.COMPLETE_EXCELLENT: "🌟",
            QualityLabel.COMPLETE_GOOD: "✅",
            QualityLabel.PARTIAL_NEEDS_IMPROVEMENT: "⚡",
            QualityLabel.INCOMPLETE_MISSING_INFO: "❓",
            QualityLabel.FAILED_POOR_QUALITY: "❌",
            QualityLabel.ERROR_INVALID: "⚠️"
        }
        return quality_emojis.get(quality_label, "❔")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {}
        
        # 基础字段
        result['sequence'] = self.sequence
        result['timestamp'] = self.timestamp
        result['raw_question'] = self.raw_question
        result['retriver_chunks'] = self.retriver_chunks.copy() if self.retriver_chunks else []
        result['prompts'] = self.prompts.copy() if self.prompts else []
        result['response'] = self.response
        result['uuid'] = self.uuid
        result['tool_name'] = self.tool_name
        result['tool_config'] = self._deep_copy_tool_config(self.tool_config) if self.tool_config else {}
        
        # 搜索会话
        if self.search_session:
            result['search_session'] = self.search_session.to_dict()
        else:
            result['search_session'] = None
        
        # 处理evaluation字段
        if self.evaluation:
            eval_dict = {
                'label': self.evaluation.label.value,
                'confidence': self.evaluation.confidence,
                'reasoning': self.evaluation.reasoning,
                'specific_issues': self.evaluation.specific_issues.copy(),
                'suggestions': self.evaluation.suggestions.copy(),
                'should_return_to_chief': self.evaluation.should_return_to_chief,
                'ready_for_output': self.evaluation.ready_for_output
            }
            result['evaluation'] = eval_dict
        else:
            result['evaluation'] = None
        
        return result

    def _deep_copy_tool_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """深拷贝tool_config"""
        import copy
        return copy.deepcopy(config)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelContext':
        """从字典创建ModelContext实例"""
        data = data.copy()
        
        # 处理evaluation字段
        evaluation = None
        if data.get('evaluation'):
            eval_data = data['evaluation']
            label = QualityLabel(eval_data['label'])
            
            evaluation = CriticEvaluation(
                label=label,
                confidence=eval_data.get('confidence', 0.0),
                reasoning=eval_data.get('reasoning', ''),
                specific_issues=eval_data.get('specific_issues', []),
                suggestions=eval_data.get('suggestions', []),
                should_return_to_chief=eval_data.get('should_return_to_chief', False),
                ready_for_output=eval_data.get('ready_for_output', False)
            )
        
        # 处理search_session字段
        search_session = None
        if data.get('search_session'):
            search_session = SearchSession.from_dict(data['search_session'])
        
        return cls(
            sequence=data.get('sequence', 0),
            timestamp=data.get('timestamp', int(time.time() * 1000)),
            raw_question=data.get('raw_question'),
            retriver_chunks=data.get('retriver_chunks', []),
            search_session=search_session,
            prompts=data.get('prompts', []),
            response=data.get('response'),
            uuid=data.get('uuid', str(uuid4())),
            tool_name=data.get('tool_name'),
            evaluation=evaluation,
            tool_config=data.get('tool_config', {})
        )

    # 搜索结果相关方法
    def create_search_session(self, original_question: str = None) -> SearchSession:
        """创建新的搜索会话"""
        if not self.search_session:
            self.search_session = SearchSession(
                original_question=original_question or self.raw_question or ""
            )
        return self.search_session

    def add_search_results(self, query: str, results: List[SearchResult], 
                          search_engine: str = "unknown", 
                          execution_time_ms: int = 0,
                          total_results_count: int = None) -> None:
        """添加搜索结果"""
        if not self.search_session:
            self.create_search_session()
        
        query_results = SearchQueryResults(
            query=query,
            results=results,
            search_engine=search_engine,
            execution_time_ms=execution_time_ms,
            total_results_count=total_results_count or len(results)
        )
        
        self.search_session.add_query_results(query_results)

    def get_search_queries(self) -> List[str]:
        """获取所有搜索查询"""
        if self.search_session:
            return self.search_session.get_all_queries()
        return self.get_tool_config("search_queries", [])

    def get_all_search_results(self) -> List[SearchResult]:
        """获取所有搜索结果"""
        if self.search_session:
            return self.search_session.get_all_results()
        return []

    def get_results_by_query(self, query: str) -> List[SearchResult]:
        """根据查询获取结果"""
        if self.search_session:
            query_results = self.search_session.get_results_by_query(query)
            return query_results.results if query_results else []
        return []

    def get_search_results_count(self) -> int:
        """获取搜索结果总数"""
        if self.search_session:
            return self.search_session.get_total_results_count()
        return len(self.retriver_chunks)

    def has_search_results(self) -> bool:
        """检查是否有搜索结果"""
        return (self.search_session and self.search_session.get_total_results_count() > 0) or \
               (self.retriver_chunks and len(self.retriver_chunks) > 0)

    # 向后兼容的方法
    def set_search_queries(self, queries: List[str], analysis: Dict[str, Any] = None) -> None:
        """设置搜索查询（向后兼容）"""
        self.set_tool_config("search_queries", queries)
        if analysis:
            self.set_tool_config("search_analysis", analysis)

    def get_search_analysis(self) -> Dict[str, Any]:
        """获取搜索分析结果"""
        return self.get_tool_config("search_analysis", {})

    def has_search_queries(self) -> bool:
        """检查是否有搜索查询"""
        queries = self.get_search_queries()
        return bool(queries and len(queries) > 0)

    # Tool Configuration相关方法保持不变...
    def set_tool_config(self, key: str, value: Any) -> None:
        """设置工具配置项"""
        if self.tool_config is None:
            self.tool_config = {}
        self.tool_config[key] = value

    def get_tool_config(self, key: str, default: Any = None) -> Any:
        """获取工具配置项"""
        if not self.tool_config:
            return default
        return self.tool_config.get(key, default)

    def update_tool_config(self, config_dict: Dict[str, Any]) -> None:
        """批量更新工具配置"""
        if self.tool_config is None:
            self.tool_config = {}
        self.tool_config.update(config_dict)

    def remove_tool_config(self, key: str) -> Any:
        """移除工具配置项"""
        if not self.tool_config:
            return None
        return self.tool_config.pop(key, None)

    def has_tool_config(self, key: str) -> bool:
        """检查是否存在指定的工具配置项"""
        return bool(self.tool_config and key in self.tool_config)

    # JSON序列化方法保持不变...
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'ModelContext':
        """从JSON字符串创建ModelContext实例"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Failed to create ModelContext from JSON: {e}")

    def save_to_file(self, file_path: str) -> None:
        """保存到文件"""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
        except Exception as e:
            raise IOError(f"Failed to save ModelContext to {file_path}: {e}")

    @classmethod
    def load_from_file(cls, file_path: str) -> 'ModelContext':
        """从文件加载"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return cls.from_json(f.read())
        except FileNotFoundError:
            raise FileNotFoundError(f"ModelContext file not found: {file_path}")
        except Exception as e:
            raise IOError(f"Failed to load ModelContext from {file_path}: {e}")

    def clone(self) -> 'ModelContext':
        """创建当前模板的深拷贝"""
        return self.from_dict(self.to_dict())

    def update_evaluation(self, label: QualityLabel, confidence: float, 
                         reasoning: str, issues: List[str] = None, 
                         suggestions: List[str] = None) -> None:
        """更新或创建评估信息"""
        self.evaluation = CriticEvaluation(
            label=label,
            confidence=confidence,
            reasoning=reasoning,
            specific_issues=issues or [],
            suggestions=suggestions or [],
            should_return_to_chief=label in [QualityLabel.FAILED_POOR_QUALITY, 
                                           QualityLabel.INCOMPLETE_MISSING_INFO],
            ready_for_output=label in [QualityLabel.COMPLETE_EXCELLENT, 
                                     QualityLabel.COMPLETE_GOOD]
        )

    # 其他方法保持不变...
    def has_complete_response(self) -> bool:
        """检查是否有完整的响应"""
        return bool(self.response and self.response.strip())

    def is_ready_for_output(self) -> bool:
        """检查是否准备好输出"""
        return (self.evaluation and 
                self.evaluation.ready_for_output and 
                self.has_complete_response())

    def get_processing_summary(self) -> Dict[str, Any]:
        """获取处理摘要信息"""
        return {
            "uuid": self.uuid,
            "tool_name": self.tool_name,
            "has_response": self.has_complete_response(),
            "has_evaluation": self.evaluation is not None,
            "evaluation_label": self.evaluation.label.value if self.evaluation else None,
            "confidence": self.evaluation.confidence if self.evaluation else None,
            "ready_for_output": self.is_ready_for_output(),
            "search_results_count": self.get_search_results_count(),
            "prompts_count": len(self.prompts),
            "has_tool_config": bool(self.tool_config),
            "tool_config_keys": list(self.tool_config.keys()) if self.tool_config else [],
            "has_search_queries": self.has_search_queries(),
            "search_queries_count": len(self.get_search_queries()),
            "timestamp": self.timestamp
        }