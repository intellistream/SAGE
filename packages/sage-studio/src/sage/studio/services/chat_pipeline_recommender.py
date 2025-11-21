"""Utilities for generating pipeline recommendations from chat history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class PipelineNodeSuggestion:
    """Lightweight description of a Flow node."""

    id: str
    label: str
    node_type: str
    description: str


INTENT_KEYWORDS = {
    "rag": {"vector", "retrieval", "knowledge base", "rag", "文档", "资料", "搜索"},
    "summarize": {"总结", "概括", "summary", "summarize"},
    "analytics": {"统计", "分析", "report", "指标"},
}


def _detect_intents(user_messages: Sequence[str]) -> set[str]:
    lowered = " \n".join(m.lower() for m in user_messages)
    matches = {
        intent
        for intent, keywords in INTENT_KEYWORDS.items()
        if any(k in lowered for k in keywords)
    }
    if not matches:
        matches.add("general")
    return matches


def _make_node(node_id: str, label: str, node_type: str, description: str, order: int) -> dict:
    return {
        "id": node_id,
        "type": "custom",
        "position": {"x": 160, "y": 120 * order},
        "data": {
            "label": label,
            "nodeId": node_type,
            "description": description,
            "status": "idle",
        },
    }


def _link(source: str, target: str, index: int) -> dict:
    return {
        "id": f"e{source}-{target}-{index}",
        "source": source,
        "target": target,
        "type": "smoothstep",
        "animated": True,
    }


def _build_graph(intents: set[str]) -> tuple[list[dict], list[dict], list[str]]:
    nodes: list[dict] = []
    edges: list[dict] = []
    explanations: list[str] = []
    order = 0
    previous_node_id: str | None = None

    def append_node(suggestion: PipelineNodeSuggestion) -> str:
        nonlocal order, previous_node_id
        node = _make_node(
            suggestion.id, suggestion.label, suggestion.node_type, suggestion.description, order
        )
        nodes.append(node)
        if previous_node_id:
            edges.append(_link(previous_node_id, suggestion.id, len(edges)))
        previous_node_id = suggestion.id
        order += 1
        return suggestion.id

    input_node = PipelineNodeSuggestion("node-input", "User Prompt", "UserInput", "接收聊天输入")
    append_node(input_node)

    if "rag" in intents:
        rag_chain = [
            PipelineNodeSuggestion("node-loader", "Document Loader", "FileSource", "加载知识文档"),
            PipelineNodeSuggestion("node-split", "Text Splitter", "SimpleSplitter", "切分文本"),
            PipelineNodeSuggestion("node-embed", "Embeddings", "Embedding", "嵌入向量"),
            PipelineNodeSuggestion("node-vector", "Vector Search", "Retriever", "向量检索"),
        ]
        for item in rag_chain:
            append_node(item)
        explanations.append("检测到检索增强需求，建议引入文档加载与向量检索节点。")

    llm_node = PipelineNodeSuggestion("node-llm", "LLM", "LLM", "核心推理模型")
    append_node(llm_node)

    if "summarize" in intents:
        summary = PipelineNodeSuggestion(
            "node-summary", "Summarizer", "PostProcessor", "对长文本进行总结"
        )
        append_node(summary)
        explanations.append("用户多次提及总结需求，添加 Summarizer 节点用于压缩输出。")

    if "analytics" in intents:
        analytics = PipelineNodeSuggestion(
            "node-analytics", "Analytics", "Analytics", "结构化分析输出"
        )
        append_node(analytics)
        explanations.append("包含统计/分析类语句，附加 Analytics 节点。")

    output_node = PipelineNodeSuggestion("node-output", "Answer", "TerminalSink", "输出回答结果")
    append_node(output_node)

    return nodes, edges, explanations


def generate_pipeline_recommendation(session: dict[str, Any]) -> dict[str, Any]:
    """Create a lightweight pipeline suggestion from chat history."""

    messages = session.get("messages", [])
    user_messages = [m.get("content", "") for m in messages if m.get("role") == "user"]
    intents = _detect_intents(user_messages)
    nodes, edges, explanations = _build_graph(intents)

    confidence = min(0.5 + 0.1 * len(intents), 0.9)
    title = session.get("metadata", {}).get("title") or session.get("id", "Chat Session")

    return {
        "session_id": session.get("id"),
        "suggested_name": title,
        "summary": f"识别到 {', '.join(intents)} 的需求，已生成 {len(nodes)} 个节点的推荐管道。",
        "confidence": round(confidence, 2),
        "nodes": nodes,
        "edges": edges,
        "insights": explanations,
    }


__all__ = ["generate_pipeline_recommendation"]
