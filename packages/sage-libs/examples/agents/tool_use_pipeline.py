#!/usr/bin/env python3
"""
Tool Use Agent Pipeline Demo
Agentic Workflow: User Query -> Select Tool(s) -> Use Tool(s) -> Generate Response

This example demonstrates how to build an Agent Pipeline with tool calling capabilities:
1. Receive user queries
2. LLM reasoning to select appropriate tools
3. Execute selected tools (Web Search, Vector Search, Calculator, etc.)
4. Generate final response based on tool execution results

Pipeline Architecture:
    UserQuerySource -> ToolSelector -> ToolExecutor -> ResponseGenerator -> ResponseSink

# test_tags: category=agent, timeout=180, requires_llm=true
"""

from __future__ import annotations

import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.api.local_environment import LocalEnvironment

# =============================================================================
# Data Models
# =============================================================================


@dataclass
class ToolCallRequest:
    """Tool call request"""

    tool_name: str
    arguments: dict[str, Any]


@dataclass
class ToolCallResult:
    """Tool call result"""

    tool_name: str
    success: bool
    result: Any
    error: str | None = None


@dataclass
class AgentState:
    """Agent state flowing through the pipeline"""

    query: str
    selected_tools: list[ToolCallRequest] = field(default_factory=list)
    tool_results: list[ToolCallResult] = field(default_factory=list)
    response: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Tool Definitions - MCP Style
# =============================================================================


class BaseTool(ABC):
    """Base tool class - MCP style"""

    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}

    @abstractmethod
    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool"""
        pass


class WebSearchTool(BaseTool):
    """Web search tool - simulates search engine"""

    name = "web_search"
    description = "Search the web for information. Returns relevant search results."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    }

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        mock_results = [
            {
                "title": f"Result {i + 1} for: {query}",
                "url": f"https://example.com/result{i + 1}",
                "snippet": f"This is a relevant snippet about {query}...",
            }
            for i in range(min(max_results, 5))
        ]
        return {"success": True, "results": mock_results, "query": query}


class VectorSearchTool(BaseTool):
    """Vector search tool - RAG retrieval"""

    name = "vector_search"
    description = "Search internal knowledge base using vector similarity."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "top_k": {"type": "integer", "default": 3},
        },
        "required": ["query"],
    }

    def __init__(self):
        self.knowledge_base = [
            {
                "id": "doc1",
                "content": "SAGE is a Python framework for building AI/LLM data processing pipelines.",
            },
            {
                "id": "doc2",
                "content": "The architecture consists of 5 layers: L1-Common to L5-Interface.",
            },
            {
                "id": "doc3",
                "content": "To install SAGE, run ./quickstart.sh --dev --yes for development setup.",
            },
        ]

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "").lower()
        top_k = arguments.get("top_k", 3)
        scored_docs = []
        for doc in self.knowledge_base:
            content_lower = doc["content"].lower()
            score = sum(1 for word in query.split() if word in content_lower)
            if score > 0:
                scored_docs.append({"doc": doc, "score": score})
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return {
            "success": True,
            "documents": [
                {"id": d["doc"]["id"], "content": d["doc"]["content"], "score": d["score"]}
                for d in scored_docs[:top_k]
            ],
            "query": query,
        }


class CalculatorTool(BaseTool):
    """Calculator tool"""

    name = "calculator"
    description = "Perform mathematical calculations."
    input_schema = {
        "type": "object",
        "properties": {"expression": {"type": "string", "description": "Math expression"}},
        "required": ["expression"],
    }

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        expression = arguments.get("expression", "")
        try:
            safe_expr = re.sub(r"[^0-9+\-*/(). ]", "", expression)
            if not safe_expr:
                return {"success": False, "error": "Invalid expression"}
            result = eval(safe_expr, {"__builtins__": {}}, {})
            return {"success": True, "expression": expression, "result": result}
        except Exception as e:
            return {"success": False, "expression": expression, "error": str(e)}


class EmailSearchTool(BaseTool):
    """Email search tool"""

    name = "email_search"
    description = "Search emails by sender, subject, or content."
    input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        mock_emails = [
            {
                "id": "email1",
                "from": "team@company.com",
                "subject": f"RE: {query}",
                "snippet": f"Info about {query}...",
            },
            {
                "id": "email2",
                "from": "support@example.com",
                "subject": f"Update on {query}",
                "snippet": f"Review of {query}...",
            },
        ]
        return {"success": True, "emails": mock_emails, "query": query}


class SlackSearchTool(BaseTool):
    """Slack message search tool"""

    name = "slack_search"
    description = "Search Slack messages and channels."
    input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}, "channel": {"type": "string"}},
        "required": ["query"],
    }

    def call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        channel = arguments.get("channel", "general")
        mock_messages = [
            {"channel": channel, "user": "alice", "message": f"Discussing {query} in the meeting."},
            {"channel": channel, "user": "bob", "message": f"Good point about {query}."},
        ]
        return {"success": True, "messages": mock_messages, "query": query}


# =============================================================================
# Tool Registry
# =============================================================================


class ToolRegistry:
    """Tool registry - manages all available tools"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def describe_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
            for tool in self._tools.values()
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found"}
        return tool.call(arguments)


def create_default_registry() -> ToolRegistry:
    """Create default tool registry"""
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(VectorSearchTool())
    registry.register(CalculatorTool())
    registry.register(EmailSearchTool())
    registry.register(SlackSearchTool())
    return registry


# =============================================================================
# Pipeline Operators
# =============================================================================


class UserQuerySource(SourceFunction):
    """User query source - receives user queries and creates AgentState"""

    def __init__(self, queries: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.queries = queries or [
            "What is SAGE framework and how to install it?",
            "Calculate 15 * 23 + 47",
            "Search for recent emails about project update",
        ]
        self.current_index = 0

    def execute(self, data=None) -> AgentState | None:
        if self.current_index >= len(self.queries):
            from sage.kernel.runtime.communication.packet import StopSignal

            return StopSignal("All queries processed")

        query = self.queries[self.current_index]
        self.current_index += 1
        print(f"\n{'=' * 60}")
        print(f"[UserQuerySource] Query {self.current_index}: {query}")
        print("=" * 60)
        return AgentState(
            query=query, metadata={"query_id": self.current_index, "timestamp": time.time()}
        )


class ToolSelector(MapFunction):
    """Tool selector - uses LLM or fallback to select appropriate tools"""

    def __init__(self, tool_registry: ToolRegistry | None = None, **kwargs):
        super().__init__(**kwargs)
        self.tool_registry = tool_registry or create_default_registry()
        self._llm_client = None

    def _get_llm_client(self):
        if self._llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create()
            except Exception as e:
                print(f"[ToolSelector] Warning: Could not create LLM client: {e}")
                self._llm_client = None
        return self._llm_client

    def _build_tool_selection_prompt(self, query: str) -> str:
        tools_desc = self.tool_registry.describe_tools()
        tools_json = json.dumps(tools_desc, indent=2, ensure_ascii=False)
        return f"""You are an AI assistant that helps select the right tools.

Available Tools:
{tools_json}

User Query: {query}

Select appropriate tool(s). Return JSON array:
[{{"tool_name": "name", "arguments": {{"arg": "value"}}}}]

If no tools needed, return: []

Your response (JSON only):"""

    def _parse_tool_selection(self, response: str) -> list[ToolCallRequest]:
        try:
            json_match = re.search(r"\[[\s\S]*\]", response)
            if json_match:
                tools_data = json.loads(json_match.group())
                return [
                    ToolCallRequest(
                        tool_name=t.get("tool_name", t.get("name", "")),
                        arguments=t.get("arguments", {}),
                    )
                    for t in tools_data
                    if t.get("tool_name") or t.get("name")
                ]
        except Exception as e:
            print(f"[ToolSelector] Failed to parse response: {e}")
        return []

    def _fallback_tool_selection(self, query: str) -> list[ToolCallRequest]:
        query_lower = query.lower()
        selected_tools = []

        if any(word in query_lower for word in ["calculate", "math", "+", "-", "*", "/"]):
            expr_match = re.search(r"[\d\s+\-*/().]+", query)
            expr = expr_match.group().strip() if expr_match else query
            selected_tools.append(
                ToolCallRequest(tool_name="calculator", arguments={"expression": expr})
            )
        elif any(word in query_lower for word in ["email", "mail"]):
            selected_tools.append(
                ToolCallRequest(tool_name="email_search", arguments={"query": query})
            )
        elif any(word in query_lower for word in ["slack", "message"]):
            selected_tools.append(
                ToolCallRequest(tool_name="slack_search", arguments={"query": query})
            )
        elif any(word in query_lower for word in ["what is", "how to", "explain", "sage"]):
            selected_tools.append(
                ToolCallRequest(tool_name="vector_search", arguments={"query": query})
            )
        else:
            selected_tools.append(
                ToolCallRequest(tool_name="web_search", arguments={"query": query})
            )

        return selected_tools

    def execute(self, data: AgentState) -> AgentState:
        if not isinstance(data, AgentState):
            return data

        print(f"\n[ToolSelector] Analyzing query: {data.query}")

        llm_client = self._get_llm_client()
        if llm_client:
            try:
                prompt = self._build_tool_selection_prompt(data.query)
                response = llm_client.chat(prompt)
                selected_tools = self._parse_tool_selection(response)
                if selected_tools:
                    data.selected_tools = selected_tools
                    print(f"[ToolSelector] LLM selected: {[t.tool_name for t in selected_tools]}")
                    return data
            except Exception as e:
                print(f"[ToolSelector] LLM call failed: {e}")

        print("[ToolSelector] Using fallback keyword matching...")
        data.selected_tools = self._fallback_tool_selection(data.query)
        print(f"[ToolSelector] Fallback selected: {[t.tool_name for t in data.selected_tools]}")
        return data


class ToolExecutor(MapFunction):
    """Tool executor - executes selected tools and collects results"""

    def __init__(self, tool_registry: ToolRegistry | None = None, **kwargs):
        super().__init__(**kwargs)
        self.tool_registry = tool_registry or create_default_registry()

    def execute(self, data: AgentState) -> AgentState:
        if not isinstance(data, AgentState):
            return data

        print(f"\n[ToolExecutor] Executing {len(data.selected_tools)} tool(s)...")

        for tool_request in data.selected_tools:
            print(f"  -> Calling: {tool_request.tool_name}")
            print(f"     Arguments: {tool_request.arguments}")
            try:
                result = self.tool_registry.call_tool(
                    tool_request.tool_name, tool_request.arguments
                )
                tool_result = ToolCallResult(
                    tool_name=tool_request.tool_name,
                    success=result.get("success", True),
                    result=result,
                )
                print("     Result: Success")
            except Exception as e:
                tool_result = ToolCallResult(
                    tool_name=tool_request.tool_name, success=False, result=None, error=str(e)
                )
                print(f"     Result: Error - {e}")
            data.tool_results.append(tool_result)

        return data


class ResponseGenerator(MapFunction):
    """Response generator - generates final response based on tool results"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._llm_client = None

    def _get_llm_client(self):
        if self._llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create()
            except Exception:
                self._llm_client = None
        return self._llm_client

    def _build_response_prompt(self, state: AgentState) -> str:
        results_text = ""
        for tr in state.tool_results:
            if tr.success:
                results_text += f"\n### {tr.tool_name} Result:\n"
                results_text += json.dumps(tr.result, indent=2, ensure_ascii=False)
            else:
                results_text += f"\n### {tr.tool_name} Error:\n{tr.error}"
        return f"""Based on the tool results, generate a helpful response.

User Query: {state.query}

Tool Results:
{results_text}

Provide a clear, concise response:"""

    def _generate_fallback_response(self, state: AgentState) -> str:
        response_parts = [f"Query: {state.query}\n"]
        for tr in state.tool_results:
            response_parts.append(f"\n[{tr.tool_name}]:")
            if tr.success and isinstance(tr.result, dict):
                if "results" in tr.result:
                    for i, r in enumerate(tr.result["results"][:3], 1):
                        response_parts.append(f"  {i}. {r.get('title', str(r))}")
                elif "documents" in tr.result:
                    for doc in tr.result["documents"][:3]:
                        content = doc.get("content", "")[:100]
                        response_parts.append(f"  - {content}...")
                elif "result" in tr.result:
                    response_parts.append(f"  Result: {tr.result['result']}")
                elif "emails" in tr.result:
                    for email in tr.result["emails"][:2]:
                        response_parts.append(f"  - {email.get('subject', '')}")
                elif "messages" in tr.result:
                    for msg in tr.result["messages"][:2]:
                        response_parts.append(
                            f"  - @{msg.get('user', '')}: {msg.get('message', '')}"
                        )
                else:
                    response_parts.append(f"  {json.dumps(tr.result, ensure_ascii=False)[:200]}")
            elif not tr.success:
                response_parts.append(f"  Error: {tr.error}")
        return "\n".join(response_parts)

    def execute(self, data: AgentState) -> AgentState:
        if not isinstance(data, AgentState):
            return data

        print("\n[ResponseGenerator] Generating response...")

        llm_client = self._get_llm_client()
        if llm_client and data.tool_results:
            try:
                prompt = self._build_response_prompt(data)
                response = llm_client.chat(prompt)
                data.response = response
                print("[ResponseGenerator] LLM response generated.")
                return data
            except Exception as e:
                print(f"[ResponseGenerator] LLM call failed: {e}")

        print("[ResponseGenerator] Using fallback response generation...")
        data.response = self._generate_fallback_response(data)
        return data


class ResponseSink(SinkFunction):
    """Response output - outputs final response to console"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.test_mode = os.getenv("SAGE_TEST_MODE") == "true"

    def execute(self, data: AgentState) -> None:
        if not isinstance(data, AgentState):
            print(f"[ResponseSink] Received non-AgentState data: {type(data)}")
            return

        print("\n" + "=" * 60)
        print(f"[Final Response] Query: {data.query}")
        print("-" * 60)
        if data.selected_tools:
            print(f"Tools Used: {', '.join(t.tool_name for t in data.selected_tools)}")
            print("-" * 60)

        response = data.response
        if self.test_mode and len(response) > 500:
            response = response[:500] + "... (truncated)"
        print(response)
        print("=" * 60)


# =============================================================================
# Pipeline Build and Run
# =============================================================================


def run_tool_use_pipeline(queries: list[str] | None = None):
    """Run Tool Use Agent Pipeline"""
    print("""
========================================================
            Tool Use Agent Pipeline Demo
========================================================
  Pipeline: UserQuery -> ToolSelector -> ToolExecutor
            -> ResponseGenerator -> ResponseSink

  Available Tools:
    - web_search: Search the web
    - vector_search: Search knowledge base (RAG)
    - calculator: Mathematical calculations
    - email_search: Search emails
    - slack_search: Search Slack messages
========================================================
    """)

    tool_registry = create_default_registry()
    print(f"Registered tools: {tool_registry.list_tools()}\n")

    env = LocalEnvironment()
    (
        env.from_source(UserQuerySource, queries=queries)
        .map(ToolSelector, tool_registry=tool_registry)
        .map(ToolExecutor, tool_registry=tool_registry)
        .map(ResponseGenerator)
        .sink(ResponseSink)
    )

    start_time = time.time()
    env.submit(autostop=True)
    total_time = time.time() - start_time

    print(f"\nPipeline completed in {total_time:.2f} seconds")
    env.close()


def run_interactive_mode():
    """Interactive mode - user can input queries in real-time"""
    print("""
========================================================
         Tool Use Agent - Interactive Mode
  Type your query and press Enter.
  Type 'quit' or 'exit' to stop.
========================================================
    """)

    tool_registry = create_default_registry()
    print(f"Available tools: {tool_registry.list_tools()}\n")

    while True:
        try:
            query = input("\n> Your query: ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit"):
                print("Goodbye.")
                break

            state = AgentState(query=query)
            selector = ToolSelector(tool_registry=tool_registry)
            state = selector.execute(state)
            executor = ToolExecutor(tool_registry=tool_registry)
            state = executor.execute(state)
            generator = ResponseGenerator()
            state = generator.execute(state)
            sink = ResponseSink()
            sink.execute(state)
        except KeyboardInterrupt:
            print("\nInterrupted. Goodbye.")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main entry point"""
    import sys

    test_mode = os.getenv("SAGE_TEST_MODE") == "true"

    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            run_interactive_mode()
            return
        elif sys.argv[1] == "--query":
            queries = sys.argv[2:] if len(sys.argv) > 2 else None
            run_tool_use_pipeline(queries)
            return

    example_queries = [
        "What is SAGE framework and how to install it?",
        "Calculate 15 * 23 + 47",
        "Search for recent emails about project update",
    ]

    if test_mode:
        example_queries = example_queries[:1]

    run_tool_use_pipeline(example_queries)


if __name__ == "__main__":
    main()
