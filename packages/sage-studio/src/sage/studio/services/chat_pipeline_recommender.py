"""Utilities for generating pipeline recommendations from chat history.

这个模块现在使用 sage-libs 的 RuleBasedWorkflowGenerator，
保持向后兼容的 API 格式。

迁移说明:
- 旧版本: 使用本地的关键词匹配和图构建逻辑
- 新版本: 调用 sage.libs.agentic.workflow.generators.RuleBasedWorkflowGenerator
- 保持 API 兼容: generate_pipeline_recommendation() 返回相同格式
"""

from __future__ import annotations

from typing import Any

from sage.common.logging.logger import get_logger

logger = get_logger(__name__)


logger = get_logger(__name__)


def generate_pipeline_recommendation(session: dict[str, Any]) -> dict[str, Any]:
    """Create a lightweight pipeline suggestion from chat history.

    现在使用 sage-libs 的 RuleBasedWorkflowGenerator 实现。
    保持向后兼容的返回格式。

    Args:
        session: 会话信息，包含 messages 和 metadata

    Returns:
        推荐结果，格式:
        {
            "session_id": str,
            "suggested_name": str,
            "summary": str,
            "confidence": float,
            "nodes": list,
            "edges": list,
            "insights": list
        }
    """
    try:
        from sage.libs.agentic.workflow import GenerationContext
        from sage.libs.agentic.workflow.generators import RuleBasedWorkflowGenerator

        # 提取消息
        messages = session.get("messages", [])
        user_messages = [m.get("content", "") for m in messages if m.get("role") == "user"]

        if not user_messages:
            # 如果没有用户消息，返回默认推荐
            return _generate_fallback_recommendation(session)

        # 创建生成上下文
        context = GenerationContext(
            user_input=" ".join(user_messages),
            conversation_history=messages,
        )

        # 使用 sage-libs 生成器
        generator = RuleBasedWorkflowGenerator()
        result = generator.generate(context)

        if not result.success:
            logger.warning(f"Workflow generation failed: {result.error}")
            return _generate_fallback_recommendation(session)

        # 转换为旧 API 格式（保持兼容）
        visual_pipeline = result.visual_pipeline

        # 注意: RuleBasedWorkflowGenerator 返回 "connections"，需要转换为 "edges"
        edges = []
        for conn in visual_pipeline.get("connections", []):
            edges.append(
                {
                    "id": conn["id"],
                    "source": conn["source"],
                    "target": conn["target"],
                    "type": conn.get("type", "smoothstep"),
                    "animated": conn.get("animated", True),
                }
            )

        title = session.get("metadata", {}).get("title") or session.get("id", "Chat Session")

        return {
            "session_id": session.get("id"),
            "suggested_name": visual_pipeline.get("name", title),
            "summary": result.explanation
            or f"识别到需求，已生成 {len(visual_pipeline['nodes'])} 个节点的推荐管道。",
            "confidence": round(result.confidence, 2),
            "nodes": visual_pipeline["nodes"],
            "edges": edges,
            "insights": result.detected_intents,
        }

    except ImportError as e:
        logger.error(f"Failed to import workflow generators: {e}")
        logger.warning("Falling back to simple recommendation")
        return _generate_fallback_recommendation(session)
    except Exception as e:
        logger.error(f"Workflow generation error: {e}", exc_info=True)
        return _generate_fallback_recommendation(session)


def _generate_fallback_recommendation(session: dict[str, Any]) -> dict[str, Any]:
    """生成简单的默认推荐（当 sage-libs 不可用时）"""
    return {
        "session_id": session.get("id"),
        "suggested_name": "Simple Workflow",
        "summary": "生成了一个简单的工作流模板",
        "confidence": 0.5,
        "nodes": [
            {
                "id": "node-input",
                "type": "custom",
                "position": {"x": 160, "y": 0},
                "data": {
                    "label": "Input",
                    "nodeId": "UserInput",
                    "description": "用户输入",
                    "status": "idle",
                    "config": {},
                },
            },
            {
                "id": "node-llm",
                "type": "custom",
                "position": {"x": 160, "y": 120},
                "data": {
                    "label": "LLM",
                    "nodeId": "OpenAIGenerator",
                    "description": "语言模型",
                    "status": "idle",
                    "config": {
                        "model_name": "gpt-3.5-turbo",
                        "temperature": 0.7,
                    },
                },
            },
            {
                "id": "node-output",
                "type": "custom",
                "position": {"x": 160, "y": 240},
                "data": {
                    "label": "Output",
                    "nodeId": "TerminalSink",
                    "description": "输出结果",
                    "status": "idle",
                    "config": {},
                },
            },
        ],
        "edges": [
            {
                "id": "e-0",
                "source": "node-input",
                "target": "node-llm",
                "type": "smoothstep",
                "animated": True,
            },
            {
                "id": "e-1",
                "source": "node-llm",
                "target": "node-output",
                "type": "smoothstep",
                "animated": True,
            },
        ],
        "insights": ["使用默认工作流模板"],
    }


__all__ = ["generate_pipeline_recommendation"]
