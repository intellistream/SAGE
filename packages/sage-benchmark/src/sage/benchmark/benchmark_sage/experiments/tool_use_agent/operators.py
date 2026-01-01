"""
Pipeline Operators for Tool Use Agent
======================================

Defines the pipeline operators (functions) that process data:
- UserQuerySource: Receives queries, creates AgentState
- ToolSelector: ReAct-style reasoning to select tools
- ToolExecutor: Executes selected tools
- ResponseGenerator: Generates final response with reflection
- ResponseSink: Outputs response

All operators can access services via self.call_service().
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import TYPE_CHECKING

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.runtime.communication.packet import StopSignal

if TYPE_CHECKING:
    from .agent_tools import ToolRegistry

try:
    from .models import AgentState, ToolCallRequest, ToolCallResult
except ImportError:
    from models import AgentState, ToolCallRequest, ToolCallResult
#  AgentState, ToolCallRequest, ToolCallResult


class UserQuerySource(SourceFunction):
    """
    Source operator that receives user queries and creates AgentState.

    In batch mode, processes a list of predefined queries.
    Can be extended for interactive/streaming input.
    """

    def __init__(self, queries: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.queries = queries or [
            "What is SAGE framework and how to install it?",
            "Calculate 15 * 23 + 47",
            "Search for information about memory services in SAGE",
        ]
        self.current_index = 0

    def execute(self, data=None) -> AgentState | StopSignal | None:
        """Generate next query as AgentState"""
        if self.current_index >= len(self.queries):
            # Signal end of input
            return StopSignal("All queries processed")

        query = self.queries[self.current_index]
        self.current_index += 1

        print(f"\n{'=' * 70}")
        print(f"[UserQuerySource] Query {self.current_index}: {query}")
        print("=" * 70)

        return AgentState(
            query=query,
            metadata={
                "query_id": self.current_index,
                "timestamp": time.time(),
            },
        )


class ToolSelector(MapFunction):
    """
    Tool selection operator using ReAct-style reasoning.

    Implements:
    1. Thought: Analyze the query and context
    2. Action: Select appropriate tool(s)
    3. Uses memory_service to retrieve relevant history
    4. Uses context_service to compress context if needed

    Falls back to keyword-based selection if LLM unavailable.
    """

    def __init__(self, tool_registry: ToolRegistry | None = None, **kwargs):
        super().__init__(**kwargs)
        self.tool_registry = tool_registry
        self._llm_client = None

    def _get_llm_client(self):
        """Lazy initialization of LLM client"""
        if self._llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create()
            except Exception as e:
                print(f"[ToolSelector] LLM client unavailable: {e}")
                self._llm_client = None
        return self._llm_client

    def _retrieve_memory_context(self, state: AgentState) -> list[dict]:
        """Retrieve relevant context from memory service"""
        try:
            # 使用 method 参数直接调用服务方法
            results = self.call_service(
                "memory_service",
                method="retrieve",
                query=state.query,
                top_k=3,
            )
            return results if results else []
        except Exception as e:
            print(f"[ToolSelector] Memory service error: {e}")
        return []

    def _compress_context(self, state: AgentState) -> str:
        """Compress context using context service"""
        try:
            history = [
                {"role": "system", "content": m.get("content", "")}
                for m in state.memory_context[:5]
            ]
            # 使用 参数直接 method
            result = self.call_service(
                "context_service",
                method="manage_context",
                query=state.query,
                history=history,
            )
            if result and "compressed_context" in result:
                parts = result["compressed_context"]
                return "\n".join(p.get("content", "") for p in parts)
        except Exception as e:
            print(f"[ToolSelector] Context service error: {e}")
        return ""

    def _build_react_prompt(self, state: AgentState) -> str:
        """Build ReAct-style prompt for tool selection"""
        tools_desc = self.tool_registry.describe_tools_text() if self.tool_registry else ""

        context_str = ""
        if state.memory_context:
            context_str = "\nRelevant History:\n" + "\n".join(
                f"- {m.get('content', '')[:100]}..." for m in state.memory_context[:3]
            )

        return f"""You are an AI assistant that uses tools to answer questions.

Available Tools:
{tools_desc}

{context_str}

User Query: {state.query}

Think step by step using ReAct format:

Thought: [Analyze what the user needs and which tool(s) would help]
Action: [Select tool(s) to use]
Tool Selection: [Return JSON array of tool calls]

Example output:
Thought: The user wants to know about SAGE. I should search the knowledge base.
Action: Use vector_search to find relevant documentation.
Tool Selection: [{{"tool_name": "vector_search", "arguments": {{"query": "SAGE framework"}}, "reason": "Search knowledge base for SAGE info"}}]

Your response:"""

    def _parse_tool_selection(self, response: str) -> list[ToolCallRequest]:
        """Parse LLM response to extract tool calls"""
        try:
            # Look for JSON array in response
            json_match = re.search(r"\[[\s\S]*?\]", response)
            if json_match:
                tools_data = json.loads(json_match.group())
                return [
                    ToolCallRequest(
                        tool_name=t.get("tool_name", t.get("name", "")),
                        arguments=t.get("arguments", {}),
                        reason=t.get("reason", ""),
                    )
                    for t in tools_data
                    if t.get("tool_name") or t.get("name")
                ]
        except Exception as e:
            print(f"[ToolSelector] Parse error: {e}")
        return []

    def _fallback_tool_selection(self, state: AgentState) -> list[ToolCallRequest]:
        """Keyword-based fallback tool selection"""
        query_lower = state.query.lower()
        selected = []

        # Check for calculation patterns
        if any(op in query_lower for op in ["+", "-", "*", "/", "calculate", "compute", "math"]):
            # Extract expression
            expr_match = re.search(r"[\d\s+\-*/().]+", state.query)
            expr = expr_match.group().strip() if expr_match else state.query
            selected.append(
                ToolCallRequest(
                    tool_name="calculator",
                    arguments={"expression": expr},
                    reason="Query contains math expression",
                )
            )

        # Check for email keywords
        elif any(word in query_lower for word in ["email", "mail", "message", "inbox"]):
            selected.append(
                ToolCallRequest(
                    tool_name="email_search",
                    arguments={"query": state.query},
                    reason="Query mentions email",
                )
            )

        # Check for memory/history keywords
        elif any(
            word in query_lower for word in ["remember", "earlier", "before", "previous", "history"]
        ):
            selected.append(
                ToolCallRequest(
                    tool_name="memory_search",
                    arguments={"query": state.query},
                    reason="Query asks about past context",
                )
            )

        # Check for SAGE/documentation keywords - use vector search
        elif any(
            word in query_lower
            for word in ["sage", "install", "how to", "what is", "explain", "documentation"]
        ):
            selected.append(
                ToolCallRequest(
                    tool_name="vector_search",
                    arguments={"query": state.query},
                    reason="Query about SAGE documentation",
                )
            )

        # Default to web search
        else:
            selected.append(
                ToolCallRequest(
                    tool_name="web_search",
                    arguments={"query": state.query},
                    reason="General information query",
                )
            )

        return selected

    def execute(self, data: AgentState) -> AgentState:
        """Execute tool selection with ReAct reasoning"""
        if not isinstance(data, AgentState):
            return data

        state = data
        print(f"\n[ToolSelector] Analyzing: {state.query[:50]}...")

        # Step 1: Retrieve memory context
        state.memory_context = self._retrieve_memory_context(state)
        if state.memory_context:
            print(f"[ToolSelector] Retrieved {len(state.memory_context)} memory entries")

        # Step 2: Compress context if needed
        state.compressed_context = self._compress_context(state)

        # Step 3: ReAct reasoning with LLM
        llm_client = self._get_llm_client()
        if llm_client:
            try:
                prompt = self._build_react_prompt(state)
                messages = [{"role": "user", "content": prompt}]
                response = llm_client.chat(messages)

                # Convert response to string if needed
                response_text = str(response) if not isinstance(response, str) else response

                # Extract thought from response
                thought_match = re.search(
                    r"Thought:\s*(.+?)(?=Action:|$)", response_text, re.DOTALL
                )
                if thought_match:
                    state.add_thought(thought_match.group(1).strip())

                # Extract action
                action_match = re.search(
                    r"Action:\s*(.+?)(?=Tool Selection:|$)", response_text, re.DOTALL
                )
                if action_match:
                    state.add_action(action_match.group(1).strip())

                # Parse tool selection
                selected_tools = self._parse_tool_selection(response_text)
                if selected_tools:
                    state.selected_tools = selected_tools
                    print(f"[ToolSelector] LLM selected: {[t.tool_name for t in selected_tools]}")
                    return state

            except Exception as e:
                print(f"[ToolSelector] LLM error: {e}")

        # Fallback to keyword matching
        print("[ToolSelector] Using fallback keyword matching...")
        state.add_thought("Analyzing query keywords to select appropriate tool")
        state.selected_tools = self._fallback_tool_selection(state)
        state.add_action(
            f"Selected tools via keyword matching: {[t.tool_name for t in state.selected_tools]}"
        )
        print(f"[ToolSelector] Fallback selected: {[t.tool_name for t in state.selected_tools]}")

        return state


class ToolExecutor(MapFunction):
    """
    Tool execution operator.

    Executes selected tools and collects results.
    Tools can access services like vector_db for RAG retrieval.
    """

    def __init__(self, tool_registry: ToolRegistry | None = None, **kwargs):
        super().__init__(**kwargs)
        self.tool_registry = tool_registry

    def _inject_services(self) -> None:
        """Inject service caller into tool registry"""
        if not self.tool_registry:
            return

        # 传递 call_service 回调给工具，让工具可以调用服务方法
        self.tool_registry.set_service_caller(self.call_service)

    def execute(self, data: AgentState) -> AgentState:
        """Execute all selected tools"""
        if not isinstance(data, AgentState):
            return data

        state = data

        if not state.selected_tools:
            print("[ToolExecutor] No tools selected")
            return state

        print(f"\n[ToolExecutor] Executing {len(state.selected_tools)} tool(s)...")

        # Inject services into tools
        self._inject_services()

        for tool_request in state.selected_tools:
            print(f"  -> {tool_request.tool_name}: {tool_request.arguments}")

            start_time = time.time()
            try:
                if self.tool_registry:
                    result = self.tool_registry.call_tool(
                        tool_request.tool_name,
                        tool_request.arguments,
                    )
                else:
                    result = {"success": False, "error": "No tool registry"}

                execution_time = time.time() - start_time

                tool_result = ToolCallResult(
                    tool_name=tool_request.tool_name,
                    success=result.get("success", True),
                    result=result,
                    execution_time=execution_time,
                )

                # Add observation to ReAct trace
                if result.get("success"):
                    obs_summary = self._summarize_result(result)
                    state.add_observation(f"{tool_request.tool_name}: {obs_summary}")
                    print(f"     Success ({execution_time:.2f}s)")
                else:
                    state.add_observation(
                        f"{tool_request.tool_name} failed: {result.get('error', 'Unknown error')}"
                    )
                    print(f"     Failed: {result.get('error')}")

            except Exception as e:
                execution_time = time.time() - start_time
                tool_result = ToolCallResult(
                    tool_name=tool_request.tool_name,
                    success=False,
                    result=None,
                    error=str(e),
                    execution_time=execution_time,
                )
                state.add_observation(f"{tool_request.tool_name} error: {e}")
                print(f"     Error: {e}")

            state.tool_results.append(tool_result)

        return state

    def _summarize_result(self, result: dict) -> str:
        """Create brief summary of tool result"""
        if "documents" in result:
            docs = result["documents"]
            return f"Found {len(docs)} document(s)"
        elif "results" in result:
            return f"Found {len(result['results'])} result(s)"
        elif "result" in result:
            return f"Result: {result['result']}"
        elif "emails" in result:
            return f"Found {len(result['emails'])} email(s)"
        elif "memories" in result:
            return f"Found {len(result['memories'])} memory entries"
        else:
            return "Completed"


class ResponseGenerator(MapFunction):
    """
    Response generation operator with reflection.

    Generates final response based on tool results.
    Includes ReAct reflection step for self-critique.
    Saves interaction to memory service.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._llm_client = None

    def _get_llm_client(self):
        """Lazy initialization of LLM client"""
        if self._llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create()
            except Exception:
                self._llm_client = None
        return self._llm_client

    def _build_response_prompt(self, state: AgentState) -> str:
        """Build prompt for response generation with reflection"""
        results_text = ""
        for tr in state.tool_results:
            results_text += f"\n### {tr.tool_name}:\n"
            if tr.success:
                result = tr.result
                if isinstance(result, dict):
                    if "documents" in result:
                        for doc in result["documents"][:3]:
                            results_text += (
                                f"- {doc.get('title', 'Doc')}: {doc.get('content', '')[:150]}...\n"
                            )
                    elif "result" in result:
                        results_text += f"Result: {result['result']}\n"
                    elif "emails" in result:
                        for email in result["emails"][:2]:
                            results_text += f"- {email.get('subject', 'Email')}\n"
                    else:
                        results_text += f"{json.dumps(result, ensure_ascii=False)[:300]}\n"
            else:
                results_text += f"Error: {tr.error}\n"

        react_trace = state.get_react_trace_str()

        return f"""Based on the tool results, generate a helpful response.

User Query: {state.query}

ReAct Reasoning Trace:
{react_trace}

Tool Results:
{results_text}

Now provide:
1. A clear, helpful response to the user
2. A brief reflection on whether the tools chosen were appropriate

Format:
Response: [Your response to the user]
Reflection: [Brief self-critique - were the right tools used? What could be improved?]

Your answer:"""

    def _generate_fallback_response(self, state: AgentState) -> str:
        """Generate response without LLM"""
        parts = [f"Query: {state.query}\n"]

        for tr in state.tool_results:
            parts.append(f"\n[{tr.tool_name}]:")
            if tr.success and isinstance(tr.result, dict):
                result = tr.result
                if "documents" in result:
                    for doc in result["documents"][:3]:
                        title = doc.get("title", "Document")
                        content = doc.get("content", "")[:150]
                        parts.append(f"  - {title}: {content}...")
                elif "result" in result:
                    parts.append(f"  Result: {result['result']}")
                elif "results" in result:
                    for r in result["results"][:3]:
                        parts.append(f"  - {r.get('title', r.get('snippet', str(r)[:50]))}")
                elif "emails" in result:
                    for email in result["emails"][:2]:
                        parts.append(f"  - {email.get('subject', 'Email')}")
                elif "memories" in result:
                    for mem in result["memories"][:2]:
                        parts.append(f"  - {str(mem)[:100]}...")
                else:
                    parts.append(f"  {json.dumps(result, ensure_ascii=False)[:200]}")
            elif not tr.success:
                parts.append(f"  Error: {tr.error}")

        return "\n".join(parts)

    def _save_to_memory(self, state: AgentState) -> None:
        """Save interaction to memory service"""
        try:
            entry = state.to_memory_entry()
            # 使用 method 参数直接调用服务方法
            self.call_service(
                "memory_service",
                method="insert",
                entry=json.dumps(entry),
                metadata={"session_id": state.session_id, "type": "interaction"},
            )
            print("[ResponseGenerator] Saved to memory")
        except Exception as e:
            print(f"[ResponseGenerator] Memory save error: {e}")

    def _update_context_history(self, state: AgentState) -> None:
        """Update context service history"""
        try:
            # 使用 method 参数直接调用服务方法
            self.call_service(
                "context_service",
                method="add_to_history",
                role="user",
                content=state.query,
            )
            self.call_service(
                "context_service",
                method="add_to_history",
                role="assistant",
                content=state.response[:500],
            )
        except Exception as e:
            print(f"[ResponseGenerator] Context history error: {e}")

    def execute(self, data: AgentState) -> AgentState:
        """Generate response with reflection"""
        if not isinstance(data, AgentState):
            return data

        state = data
        print("\n[ResponseGenerator] Generating response...")

        llm_client = self._get_llm_client()
        if llm_client and state.tool_results:
            try:
                prompt = self._build_response_prompt(state)
                messages = [{"role": "user", "content": prompt}]
                response = llm_client.chat(messages)

                # Convert response to string if needed
                response_text = str(response) if not isinstance(response, str) else response

                # Extract response part
                resp_match = re.search(
                    r"Response:\s*(.+?)(?=Reflection:|$)", response_text, re.DOTALL
                )
                if resp_match:
                    state.response = resp_match.group(1).strip()
                else:
                    state.response = response_text

                # Extract and add reflection
                refl_match = re.search(r"Reflection:\s*(.+?)$", response_text, re.DOTALL)
                if refl_match:
                    state.add_reflection(refl_match.group(1).strip())

                print("[ResponseGenerator] LLM response generated with reflection")

            except Exception as e:
                print(f"[ResponseGenerator] LLM error: {e}, using fallback")
                state.response = self._generate_fallback_response(state)
        else:
            print("[ResponseGenerator] Using fallback response generation")
            state.response = self._generate_fallback_response(state)
            state.add_reflection("Used fallback response generation (LLM unavailable)")

        # Save to memory and update context
        self._save_to_memory(state)
        self._update_context_history(state)

        return state


class ResponseSink(SinkFunction):
    """
    Output sink for displaying the final response.

    Formats and prints the response along with ReAct trace.
    """

    def __init__(self, verbose: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.verbose = verbose
        self.test_mode = os.getenv("SAGE_TEST_MODE") == "true"

    def execute(self, data: AgentState) -> None:
        """Output the final response"""
        if not isinstance(data, AgentState):
            print(f"[ResponseSink] Unexpected data type: {type(data)}")
            return

        state = data

        print("\n" + "=" * 70)
        print(f"[Response] Session: {state.session_id}")
        print("-" * 70)
        print(f"Query: {state.query}")
        print("-" * 70)

        if state.selected_tools:
            tools_str = ", ".join(t.tool_name for t in state.selected_tools)
            print(f"Tools Used: {tools_str}")
            print("-" * 70)

        # Print response (truncate in test mode)
        response = state.response
        if self.test_mode and len(response) > 500:
            response = response[:500] + "... (truncated)"
        print(f"\n{response}\n")

        # Print ReAct trace if verbose
        if self.verbose and state.react_trace:
            print("-" * 70)
            print("ReAct Trace:")
            for step in state.react_trace:
                prefix = step.phase.value.capitalize()
                content = step.content[:100] + "..." if len(step.content) > 100 else step.content
                print(f"  [{prefix}] {content}")

        print("=" * 70)
