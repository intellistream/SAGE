"""
DFSDT (Depth-First Search-based Decision Tree) Tool Selector.

Implementation based on ToolLLM paper (Qin et al., 2023):
"ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs"

The DFSDT algorithm treats tool selection as a tree search problem where:
1. Each node represents a candidate tool evaluation state
2. LLM is used to score tool relevance at each node
3. DFS explores promising paths first based on scores
4. Diversity prompting encourages exploration of different tool combinations
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from .base import BaseToolSelector, SelectorResources
from .keyword_selector import KeywordSelector
from .schemas import (
    DFSDTSelectorConfig,
    KeywordSelectorConfig,
    SelectorConfig,
    ToolPrediction,
    ToolSelectionQuery,
)

logger = logging.getLogger(__name__)


# Prompt templates for LLM-based tool scoring
TOOL_RELEVANCE_PROMPT = """You are a tool selection expert. Given a user query and a candidate tool,
evaluate how relevant the tool is for completing the query.

User Query: {query}

Candidate Tool:
- Name: {tool_name}
- Description: {tool_description}
- Capabilities: {tool_capabilities}

Rate the relevance of this tool for the given query on a scale of 0 to 10, where:
- 0-2: Not relevant at all
- 3-4: Slightly relevant, might be useful indirectly
- 5-6: Moderately relevant, could help with part of the task
- 7-8: Highly relevant, directly addresses the query
- 9-10: Perfect match, exactly what's needed

Provide your rating as a single number. Only output the number, nothing else.

Rating:"""

DIVERSITY_PROMPT = """This is not the first time evaluating tools for this query.
Previous highly-rated tools were: {previous_tools}

Now evaluate a different tool that might provide a complementary or alternative approach.
Consider tools that:
1. Address different aspects of the query
2. Provide backup options if primary tools fail
3. Offer different methods to achieve the same goal

{base_prompt}"""


@dataclass
class SearchNode:
    """Node in the DFSDT search tree."""

    tool_id: str
    tool_name: str
    tool_description: str
    score: float = 0.0
    depth: int = 0
    parent: Optional["SearchNode"] = None
    children: list["SearchNode"] = field(default_factory=list)
    visited: bool = False
    pruned: bool = False

    def __hash__(self):
        return hash(self.tool_id)

    def __eq__(self, other):
        if isinstance(other, SearchNode):
            return self.tool_id == other.tool_id
        return False


class DFSDTSelector(BaseToolSelector):
    """
    DFSDT (Depth-First Search-based Decision Tree) tool selector.

    This selector implements the core idea from ToolLLM:
    1. Pre-filter candidates using fast keyword matching (optional)
    2. Build a search tree with candidate tools as nodes
    3. Use LLM to score each tool's relevance to the query
    4. DFS traversal prioritizes high-scoring branches
    5. Diversity prompting explores alternative tool combinations

    Key Features:
    - LLM-guided scoring for semantic understanding
    - Tree search for exploring multiple tool combinations
    - Diversity mechanism to avoid local optima
    - Keyword pre-filtering for efficiency with large tool sets
    """

    def __init__(self, config: DFSDTSelectorConfig, resources: SelectorResources):
        """
        Initialize DFSDT selector.

        Args:
            config: DFSDT selector configuration
            resources: Shared resources including tools loader
        """
        super().__init__(config, resources)
        self.config: DFSDTSelectorConfig = config

        # LLM client for scoring
        self._llm_client = None
        self._llm_initialized = False

        # Keyword selector for pre-filtering
        self._keyword_selector: Optional[KeywordSelector] = None
        if config.use_keyword_prefilter:
            keyword_config = KeywordSelectorConfig(
                name="keyword_prefilter",
                method="bm25",
                top_k=config.prefilter_k,
            )
            self._keyword_selector = KeywordSelector(keyword_config, resources)

        # Cache for tool metadata
        self._tool_cache: dict[str, dict] = {}
        self._preload_tools()

    @classmethod
    def from_config(cls, config: SelectorConfig, resources: SelectorResources) -> "DFSDTSelector":
        """Create DFSDT selector from config."""
        if not isinstance(config, DFSDTSelectorConfig):
            config = DFSDTSelectorConfig(
                name=config.name,
                top_k=config.top_k,
                min_score=config.min_score,
                cache_enabled=config.cache_enabled,
                params=config.params,
            )
        return cls(config, resources)

    def _preload_tools(self) -> None:
        """Preload tool metadata into cache."""
        try:
            tools_loader = self.resources.tools_loader
            for tool in tools_loader.iter_all():
                self._tool_cache[tool.tool_id] = {
                    "name": tool.name,
                    "description": getattr(tool, "description", "") or "",
                    "capabilities": getattr(tool, "capabilities", []) or [],
                    "category": getattr(tool, "category", "") or "",
                }
            self.logger.info(f"DFSDT: Preloaded {len(self._tool_cache)} tools")
        except Exception as e:
            self.logger.error(f"Error preloading tools: {e}")

    def _get_llm_client(self):
        """Lazy initialization of LLM client."""
        if not self._llm_initialized:
            try:
                from sage.llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create()
                self._llm_initialized = True
                self.logger.info("DFSDT: LLM client initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize LLM client: {e}")
                self._llm_client = None
                self._llm_initialized = True

        return self._llm_client

    def _select_impl(self, query: ToolSelectionQuery, top_k: int) -> list[ToolPrediction]:
        """
        Select tools using DFSDT algorithm.

        Args:
            query: Tool selection query
            top_k: Number of tools to select

        Returns:
            List of tool predictions with scores
        """
        # Step 1: Get candidate tools
        if query.candidate_tools:
            candidate_ids = set(query.candidate_tools)
        else:
            candidate_ids = set(self._tool_cache.keys())

        # Step 2: Pre-filter using keyword matching if enabled
        if self._keyword_selector and len(candidate_ids) > self.config.prefilter_k:
            prefilter_results = self._keyword_selector._select_impl(query, self.config.prefilter_k)
            candidate_ids = {p.tool_id for p in prefilter_results}
            self.logger.debug(f"DFSDT: Pre-filtered to {len(candidate_ids)} candidates")

        # Step 3: Build search tree and run DFSDT
        results = self._dfsdt_search(query, candidate_ids, top_k)

        return results

    def _dfsdt_search(
        self, query: ToolSelectionQuery, candidate_ids: set[str], top_k: int
    ) -> list[ToolPrediction]:
        """
        Run DFSDT search algorithm.

        Args:
            query: Tool selection query
            candidate_ids: Set of candidate tool IDs
            top_k: Number of tools to select

        Returns:
            List of tool predictions sorted by score
        """
        # Create root node
        root = SearchNode(
            tool_id="__root__",
            tool_name="root",
            tool_description="Search tree root",
            depth=0,
        )

        # Create child nodes for each candidate
        for tool_id in candidate_ids:
            if tool_id not in self._tool_cache:
                continue

            tool_info = self._tool_cache[tool_id]
            node = SearchNode(
                tool_id=tool_id,
                tool_name=tool_info["name"],
                tool_description=tool_info["description"],
                depth=1,
                parent=root,
            )
            root.children.append(node)

        # Score all nodes using LLM or fallback
        scored_nodes: list[SearchNode] = []
        visited_tools: list[str] = []

        for node in root.children:
            score = self._score_tool(query, node, visited_tools)
            node.score = score

            if score >= self.config.score_threshold:
                scored_nodes.append(node)
                visited_tools.append(node.tool_name)

        # Sort by score (DFS prioritizes high scores)
        scored_nodes.sort(key=lambda n: n.score, reverse=True)

        # Take top-k results
        predictions = []
        for node in scored_nodes[:top_k]:
            predictions.append(
                ToolPrediction(
                    tool_id=node.tool_id,
                    score=min(node.score, 1.0),  # Normalize to [0, 1]
                    metadata={
                        "method": "dfsdt",
                        "tool_name": node.tool_name,
                        "depth": node.depth,
                    },
                )
            )

        return predictions

    def _score_tool(
        self,
        query: ToolSelectionQuery,
        node: SearchNode,
        visited_tools: list[str],
    ) -> float:
        """
        Score a tool's relevance using LLM.

        Args:
            query: Tool selection query
            node: Search node representing the tool
            visited_tools: List of already scored tool names (for diversity)

        Returns:
            Relevance score (0-1)
        """
        llm_client = self._get_llm_client()

        if llm_client is None:
            # Fallback to simple keyword-based scoring
            return self._fallback_score(query, node)

        try:
            # Build prompt
            tool_info = self._tool_cache.get(node.tool_id, {})
            capabilities = tool_info.get("capabilities", [])
            cap_str = ", ".join(capabilities) if capabilities else "N/A"

            base_prompt = TOOL_RELEVANCE_PROMPT.format(
                query=query.instruction,
                tool_name=node.tool_name,
                tool_description=node.tool_description or "No description",
                tool_capabilities=cap_str,
            )

            # Add diversity prompt if enabled and there are visited tools
            if self.config.use_diversity_prompt and visited_tools:
                prompt = DIVERSITY_PROMPT.format(
                    previous_tools=", ".join(visited_tools[-3:]),  # Last 3 tools
                    base_prompt=base_prompt,
                )
            else:
                prompt = base_prompt

            # Call LLM
            response = llm_client.chat(
                [{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
            )

            # Parse score from response
            score = self._parse_score(response)
            return score / 10.0  # Normalize to 0-1

        except Exception as e:
            self.logger.warning(f"LLM scoring failed for {node.tool_id}: {e}")
            return self._fallback_score(query, node)

    def _fallback_score(self, query: ToolSelectionQuery, node: SearchNode) -> float:
        """
        Fallback scoring using keyword matching when LLM is unavailable.

        Args:
            query: Tool selection query
            node: Search node representing the tool

        Returns:
            Relevance score (0-1)
        """
        query_lower = query.instruction.lower()
        tool_text = f"{node.tool_name} {node.tool_description}".lower()

        # Simple keyword overlap
        query_words = set(query_lower.split())
        tool_words = set(tool_text.split())

        if not query_words or not tool_words:
            return 0.0

        overlap = len(query_words & tool_words)
        score = overlap / len(query_words)

        return min(score, 1.0)

    def _parse_score(self, response: str) -> float:
        """
        Parse numeric score from LLM response.

        Args:
            response: LLM response string

        Returns:
            Parsed score (0-10)
        """
        import re

        # Try to extract first number from response
        numbers = re.findall(r"(\d+(?:\.\d+)?)", response.strip())
        if numbers:
            score = float(numbers[0])
            return min(max(score, 0.0), 10.0)  # Clamp to 0-10

        # If no number found, try to infer from keywords
        response_lower = response.lower()
        if any(word in response_lower for word in ["perfect", "excellent", "exactly"]):
            return 9.0
        elif any(word in response_lower for word in ["highly", "very relevant", "good"]):
            return 7.0
        elif any(word in response_lower for word in ["moderate", "somewhat", "partial"]):
            return 5.0
        elif any(word in response_lower for word in ["slight", "minimal", "limited"]):
            return 3.0
        else:
            return 1.0

    def get_stats(self) -> dict:
        """Get selector statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "llm_initialized": self._llm_initialized,
                "tool_cache_size": len(self._tool_cache),
                "has_keyword_prefilter": self._keyword_selector is not None,
            }
        )
        return stats
