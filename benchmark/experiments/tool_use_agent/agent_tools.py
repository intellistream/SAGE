"""
Tool Definitions for Tool Use Agent Pipeline
=============================================

Defines tools that can be called by the agent:
- BaseTool: Abstract base class for all tools
- ToolRegistry: Registry for managing available tools
- VectorSearchTool: RAG retrieval using vector_db service
- WebSearchTool: Simulated web search
- CalculatorTool: Mathematical calculations
- MemorySearchTool: Search conversation history
- EmailSearchTool: Simulated email search

Tools follow MCP (Model Context Protocol) style with:
- name: Unique identifier
- description: What the tool does
- input_schema: JSON schema for arguments
- call(): Execute the tool
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class BaseTool(ABC):
    """
    Base class for all tools - MCP style.

    Tools can optionally receive service references for accessing
    pipeline services like vector_db, memory_service, etc.
    """

    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}

    def __init__(self, services: dict[str, Any] | None = None, service_caller: Any = None):
        """
        Initialize tool with optional service references.

        Args:
            services: Dict mapping service names to service instances (legacy)
            service_caller: Callable to call service methods via pipeline
        """
        self.services = services or {}
        self._service_caller = service_caller

    def get_service(self, name: str) -> Any:
        """Get a service by name (legacy method)"""
        return self.services.get(name)

    def call_service(self, service_name: str, method: str, **kwargs) -> Any:
        """Call a service method via pipeline callback"""
        if self._service_caller:
            try:
                return self._service_caller(service_name, method=method, **kwargs)
            except Exception as e:
                print(f"[{self.name}] Service call error: {e}")
        return None

    @abstractmethod
    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool with given arguments.

        Args:
            arguments: Tool arguments matching input_schema

        Returns:
            Dict with 'success' bool and result/error
        """
        pass


class VectorSearchTool(BaseTool):
    """
    Vector search tool for RAG retrieval.

    Uses vector_db service for semantic similarity search.
    Falls back to keyword matching if service unavailable.
    """

    name = "vector_search"
    description = "Search the SAGE knowledge base for relevant documentation and information using semantic similarity."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant documents",
            },
            "top_k": {
                "type": "integer",
                "default": 3,
                "description": "Number of results to return",
            },
        },
        "required": ["query"],
    }

    # Fallback knowledge base when vector_db service unavailable
    KNOWLEDGE_BASE = [
        {
            "id": "doc1",
            "title": "SAGE Framework Overview",
            "content": "SAGE is a Python framework for building AI/LLM data processing pipelines with declarative dataflow. It consists of 5 layers: L1-Common (foundation), L2-Platform (services), L3-Kernel/Libs (core algorithms), L4-Middleware (operators), L5-CLI/Tools (interface).",
            "tags": ["overview", "architecture", "layers"],
        },
        {
            "id": "doc2",
            "title": "SAGE Installation Guide",
            "content": "To install SAGE, run ./quickstart.sh --dev --yes for development setup. Prerequisites: Python 3.10+, Git, build-essential, cmake, pkg-config, libopenblas-dev, liblapack-dev. The installation takes 10-25 minutes.",
            "tags": ["installation", "setup", "quickstart"],
        },
        {
            "id": "doc3",
            "title": "Pipeline Architecture",
            "content": "SAGE pipelines use SourceFunction, MapFunction, and SinkFunction operators connected via LocalEnvironment. Data flows from Source through Map operators to Sink. Services can be registered with env.register_service() and accessed via self.call_service().",
            "tags": ["pipeline", "operators", "dataflow"],
        },
        {
            "id": "doc4",
            "title": "Memory Services",
            "content": "sage-mem provides HierarchicalMemoryService with three tiers: STM (short-term), MTM (medium-term), LTM (long-term). Use MemoryServiceFactory.create_instance() to create services. Services support insert(), retrieve(), and delete() operations.",
            "tags": ["memory", "sage-mem", "hierarchical"],
        },
        {
            "id": "doc5",
            "title": "Context Compression",
            "content": "sage-refiner provides ContextService for automatic context compression. Use manage_context() to compress long conversations. Supports multiple algorithms: simple, llmlingua2, provence, reform. Configure with max_context_length and auto_compress settings.",
            "tags": ["refiner", "compression", "context"],
        },
    ]

    def _get_embedding(self, text: str) -> list[float] | None:
        """Convert text to embedding vector using UnifiedInferenceClient"""
        try:
            from sage.common.components.sage_llm import UnifiedInferenceClient

            client = UnifiedInferenceClient.create()
            # embed() 返回 list[list[float]]，取第一
            embeddings = client.embed([text])
            if isinstance(embeddings, list) and len(embeddings) > 0:
                return embeddings[0]
        except Exception as e:
            print(f"[VectorSearchTool] Embedding error: {e}")
        return None

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 3)

        # Try to use vector_db service with embedding
        try:
            # Step 1: Convert query text to embedding vector
            query_embedding = self._get_embedding(query)

            if query_embedding is not None:
                # Step 2: Search using vector
                import numpy as np

                query_vec = np.array(query_embedding, dtype=np.float32)
                results = self.call_service("vector_db", method="search", query=query_vec, k=top_k)

                if results is not None:
                    # Format results with metadata
                    formatted = []
                    for r in results:
                        meta = r.get("metadata", {})
                        formatted.append(
                            {
                                "id": r.get("id"),
                                "title": meta.get("title", ""),
                                "content": meta.get("text", meta.get("content", "")),
                                "score": r.get("score", 0),
                            }
                        )
                    return {
                        "success": True,
                        "documents": formatted,
                        "source": "vector_db",
                        "query": query,
                    }
        except Exception as e:
            print(f"[VectorSearchTool] Service error: {e}, using fallback")

        # Fallback: keyword-based search
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_docs = []
        for doc in self.KNOWLEDGE_BASE:
            content_lower = doc["content"].lower()
            title_lower = doc["title"].lower()

            # Score based on word overlap
            score = 0
            for word in query_words:
                if len(word) > 2:
                    if word in content_lower:
                        score += 2
                    if word in title_lower:
                        score += 3
                    for tag in doc["tags"]:
                        if word in tag:
                            score += 2

            if score > 0:
                scored_docs.append(
                    {
                        "id": doc["id"],
                        "title": doc["title"],
                        "content": doc["content"],
                        "score": score,
                    }
                )

        # Sort by score and take top_k
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        results = scored_docs[:top_k]

        return {
            "success": True,
            "documents": results,
            "source": "fallback_keyword",
            "query": query,
        }


class WebSearchTool(BaseTool):
    """
    Web search tool - simulates search engine results.

    In production, this would integrate with real search APIs.
    """

    name = "web_search"
    description = "Search the web for general information. Use for current events, external knowledge, or topics not in the knowledge base."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "default": 5,
                "description": "Maximum number of results",
            },
        },
        "required": ["query"],
    }

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)

        # Simulate web search results
        mock_results = [
            {
                "title": f"Result {i + 1} for: {query}",
                "url": f"https://example.com/result{i + 1}",
                "snippet": f"This is a simulated search result about {query}. In production, this would return real web search results.",
            }
            for i in range(min(max_results, 5))
        ]

        return {
            "success": True,
            "results": mock_results,
            "query": query,
            "note": "Simulated results - integrate with real search API for production",
        }


class CalculatorTool(BaseTool):
    """
    Calculator tool for mathematical expressions.

    Supports basic arithmetic, power, sqrt, and common math functions.
    """

    name = "calculator"
    description = "Perform mathematical calculations. Supports arithmetic (+, -, *, /, **), sqrt, abs, and basic math functions."
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate (e.g., '15 * 23 + 47', 'sqrt(16)', '2**10')",
            },
        },
        "required": ["expression"],
    }

    # Safe math functions
    SAFE_FUNCTIONS = {
        "sqrt": math.sqrt,
        "abs": abs,
        "pow": pow,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
        "round": round,
        "pi": math.pi,
        "e": math.e,
    }

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        expression = arguments.get("expression", "")

        try:
            # Sanitize: only allow safe characters and functions
            safe_expr = expression

            # Replace common function names
            for func_name in self.SAFE_FUNCTIONS:
                safe_expr = safe_expr.replace(func_name, f"__{func_name}__")

            # Check for unsafe patterns
            if re.search(r"[a-zA-Z_][a-zA-Z0-9_]*(?!_)", safe_expr.replace("__", "")):
                # Has identifiers that aren't our safe functions
                safe_expr = re.sub(r"[^0-9+\-*/(). \t]", "", expression)
            else:
                # Restore function names
                for func_name in self.SAFE_FUNCTIONS:
                    safe_expr = safe_expr.replace(f"__{func_name}__", func_name)

            if not safe_expr.strip():
                return {"success": False, "error": "Invalid expression"}

            # Evaluate with safe builtins
            result = eval(safe_expr, {"__builtins__": {}}, self.SAFE_FUNCTIONS)

            return {
                "success": True,
                "expression": expression,
                "result": result,
            }
        except Exception as e:
            return {
                "success": False,
                "expression": expression,
                "error": str(e),
            }


class MemorySearchTool(BaseTool):
    """
    Memory search tool for retrieving conversation history.

    Uses memory_service to search past interactions.
    """

    name = "memory_search"
    description = "Search past conversations and interactions. Use to recall previous discussions, decisions, or context from earlier in the session."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for in conversation history",
            },
            "top_k": {
                "type": "integer",
                "default": 5,
                "description": "Number of results to return",
            },
        },
        "required": ["query"],
    }

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 5)

        # Try to use memory service
        memory_service = self.get_service("memory_service")
        if memory_service is not None:
            try:
                results = memory_service.retrieve(query=query, topk=top_k)
                return {
                    "success": True,
                    "memories": results,
                    "source": "memory_service",
                    "query": query,
                }
            except Exception as e:
                print(f"[MemorySearchTool] Service error: {e}")

        # Fallback: no memories available
        return {
            "success": True,
            "memories": [],
            "source": "fallback",
            "query": query,
            "note": "Memory service not available or empty",
        }


class EmailSearchTool(BaseTool):
    """
    Email search tool - simulated for demo purposes.
    """

    name = "email_search"
    description = "Search emails by sender, subject, or content. Use when the user asks about emails or messages."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for emails",
            },
            "sender": {
                "type": "string",
                "description": "Filter by sender email (optional)",
            },
        },
        "required": ["query"],
    }

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        sender = arguments.get("sender", "")

        # Simulate email search results
        mock_emails = [
            {
                "id": "email1",
                "from": sender or "team@sage-project.com",
                "subject": f"RE: {query}",
                "snippet": f"Information about {query}. This is a simulated email result.",
                "date": "2024-12-20",
            },
            {
                "id": "email2",
                "from": sender or "dev@sage-project.com",
                "subject": f"Update on {query}",
                "snippet": f"Latest updates regarding {query}. Please review.",
                "date": "2024-12-19",
            },
        ]

        return {
            "success": True,
            "emails": mock_emails,
            "query": query,
            "note": "Simulated results - integrate with email API for production",
        }


class ToolRegistry:
    """
    Registry for managing available tools.

    Supports:
    - Registering tools
    - Listing available tools
    - Getting tool descriptions (for LLM prompt)
    - Calling tools by name
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._services: dict[str, Any] = {}
        self._service_caller: Any = None

    def set_services(self, services: dict[str, Any]) -> None:
        """Set service references for all tools (legacy)"""
        self._services = services
        # Update existing tools
        for tool in self._tools.values():
            tool.services = services

    def set_service_caller(self, caller: Any) -> None:
        """Set service caller callback for all tools"""
        self._service_caller = caller
        for tool in self._tools.values():
            tool._service_caller = caller

    def register(self, tool: BaseTool) -> None:
        """Register a tool"""
        tool.services = self._services
        tool._service_caller = self._service_caller
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name"""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names"""
        return list(self._tools.keys())

    def describe_tools(self) -> list[dict[str, Any]]:
        """Get tool descriptions for LLM prompt"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def describe_tools_text(self) -> str:
        """Get tool descriptions as formatted text"""
        lines = []
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
            if tool.input_schema.get("properties"):
                for prop, spec in tool.input_schema["properties"].items():
                    required = prop in tool.input_schema.get("required", [])
                    req_str = " (required)" if required else ""
                    lines.append(f"    - {prop}: {spec.get('description', '')}{req_str}")
        return "\n".join(lines)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool by name with arguments"""
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found"}
        return tool.call(arguments)


def create_default_registry(services: dict[str, Any] | None = None) -> ToolRegistry:
    """
    Create registry with default tools.

    Args:
        services: Optional dict of service references

    Returns:
        ToolRegistry with default tools registered
    """
    registry = ToolRegistry()

    if services:
        registry.set_services(services)

    # Register default tools
    registry.register(VectorSearchTool(services))
    registry.register(WebSearchTool(services))
    registry.register(CalculatorTool(services))
    registry.register(MemorySearchTool(services))
    registry.register(EmailSearchTool(services))

    return registry
