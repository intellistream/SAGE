"""
Gorilla-style retrieval-augmented tool selector.

Implements the retrieval-augmented generation (RAG) approach from Gorilla paper
for tool selection. Uses embedding retrieval to find relevant API documentation,
then prompts LLM to make final selection based on retrieved context.

Reference:
    Patil et al. (2023) "Gorilla: Large Language Model Connected with Massive APIs"
    https://arxiv.org/abs/2305.15334
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import Field

from .base import BaseToolSelector, SelectorResources
from .schemas import SelectorConfig, ToolPrediction, ToolSelectionQuery

logger = logging.getLogger(__name__)


class GorillaSelectorConfig(SelectorConfig):
    """Configuration for Gorilla-style retrieval-augmented selector."""

    name: str = "gorilla"
    top_k_retrieve: int = Field(
        default=20, ge=1, description="Number of tools to retrieve in first stage"
    )
    top_k_select: int = Field(
        default=5, ge=1, description="Number of tools to select in final output"
    )
    embedding_model: str = Field(default="default", description="Embedding model for retrieval")
    llm_model: str = Field(
        default="auto", description="LLM model for selection (auto uses IntelligentLLMClient)"
    )
    similarity_metric: str = Field(
        default="cosine", description="Similarity metric: cosine, dot, euclidean"
    )
    temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="LLM temperature for selection"
    )
    use_detailed_docs: bool = Field(
        default=True, description="Include detailed parameter docs in context"
    )
    max_context_tools: int = Field(
        default=15, ge=1, description="Max tools to include in LLM context"
    )


@dataclass
class RetrievedToolDoc:
    """Retrieved tool documentation."""

    tool_id: str
    name: str
    description: str
    retrieval_score: float
    parameters: dict[str, Any] = field(default_factory=dict)
    category: str = ""


# Sentinel value to indicate auto-creation of LLM client
_AUTO_LLM = object()


class GorillaSelector(BaseToolSelector):
    """
    Gorilla-style retrieval-augmented tool selector.

    Two-stage approach:
    1. Retrieval: Use embedding similarity to retrieve top-k candidate tools
    2. Selection: Use LLM to analyze retrieved tool docs and select best matches

    This approach leverages the strengths of both embedding-based retrieval
    (efficient large-scale search) and LLM reasoning (understanding nuanced
    requirements and API semantics).

    Attributes:
        config: Gorilla selector configuration
        resources: Shared resources (tools_loader, embedding_client)
        llm_client: LLM client for selection stage
        _embedding_selector: Internal embedding selector for retrieval
    """

    def __init__(
        self,
        config: GorillaSelectorConfig,
        resources: SelectorResources,
        llm_client: Any = _AUTO_LLM,
    ):
        """
        Initialize Gorilla selector.

        Args:
            config: Selector configuration
            resources: Shared resources including embedding_client
            llm_client: LLM client for selection. Pass None to disable LLM and use
                retrieval-only mode. Omit or pass _AUTO_LLM for auto-creation.

        Raises:
            ValueError: If embedding_client is not provided
        """
        super().__init__(config, resources)
        self.config: GorillaSelectorConfig = config

        # Validate embedding client
        if not resources.embedding_client:
            raise ValueError(
                "GorillaSelector requires embedding_client in SelectorResources. "
                "Please provide an EmbeddingService instance."
            )

        self.embedding_client = resources.embedding_client

        # Initialize LLM client:
        # - llm_client=None: explicitly disable LLM, use retrieval-only mode
        # - llm_client=_AUTO_LLM (default): auto-create LLM client
        # - llm_client=<client>: use provided client
        if llm_client is None:
            self.llm_client = None
        elif llm_client is _AUTO_LLM:
            self.llm_client = self._create_llm_client()
        else:
            self.llm_client = llm_client

        # Build tool index and cache tool metadata
        self._tool_docs: dict[str, RetrievedToolDoc] = {}
        self._tool_embeddings: Optional[Any] = None
        self._tool_ids: list[str] = []
        self._preprocess_tools()

    def _create_llm_client(self) -> Any:
        """Create LLM client for selection stage."""
        try:
            from sage.llm import UnifiedInferenceClient

            # Always use create() for automatic local-first detection
            return UnifiedInferenceClient.create()
        except ImportError:
            logger.warning(
                "UnifiedInferenceClient not available. GorillaSelector will use "
                "embedding-only mode (no LLM reranking)."
            )
            return None
        except Exception as e:
            logger.warning(f"Failed to create LLM client: {e}. Using retrieval-only mode.")
            return None

    @classmethod
    def from_config(cls, config: SelectorConfig, resources: SelectorResources) -> "GorillaSelector":
        """Create Gorilla selector from config."""
        if not isinstance(config, GorillaSelectorConfig):
            # Convert generic config to GorillaSelectorConfig
            config = GorillaSelectorConfig(**config.model_dump())
        return cls(config, resources)

    def _preprocess_tools(self) -> None:
        """Preprocess all tools and build embeddings index."""
        import numpy as np

        try:
            tools_loader = self.resources.tools_loader

            # Collect tool metadata
            tool_texts = []

            for tool in tools_loader.iter_all():
                doc = RetrievedToolDoc(
                    tool_id=tool.tool_id,
                    name=tool.name,
                    description=getattr(tool, "description", ""),
                    retrieval_score=0.0,
                    parameters=getattr(tool, "parameters", {}),
                    category=getattr(tool, "category", ""),
                )
                self._tool_docs[tool.tool_id] = doc
                self._tool_ids.append(tool.tool_id)

                # Build searchable text
                text = self._build_tool_text(doc)
                tool_texts.append(text)

            if not tool_texts:
                self.logger.warning("No tools found to preprocess")
                return

            self.logger.info(f"Embedding {len(tool_texts)} tools for Gorilla retrieval...")

            # Embed all tools
            embeddings = self.embedding_client.embed(
                texts=tool_texts,
                model=self.config.embedding_model
                if self.config.embedding_model != "default"
                else None,
            )

            self._tool_embeddings = np.asarray(embeddings)
            if self._tool_embeddings.ndim == 1:
                self._tool_embeddings = self._tool_embeddings.reshape(1, -1)

            self.logger.info(
                f"Built Gorilla index with {len(self._tool_ids)} tools "
                f"(dim={self._tool_embeddings.shape[1]})"
            )

        except Exception as e:
            self.logger.error(f"Error preprocessing tools for Gorilla: {e}")
            raise

    def _build_tool_text(self, doc: RetrievedToolDoc) -> str:
        """Build searchable text from tool documentation."""
        parts = [doc.name]

        if doc.description:
            parts.append(doc.description)

        if doc.category:
            parts.append(f"Category: {doc.category}")

        if self.config.use_detailed_docs and doc.parameters:
            param_desc = []
            for param_name, param_info in doc.parameters.items():
                if isinstance(param_info, dict) and "description" in param_info:
                    param_desc.append(f"{param_name}: {param_info['description']}")
            if param_desc:
                parts.append("Parameters: " + "; ".join(param_desc))

        return " ".join(parts)

    def _retrieve_candidates(
        self, query: str, candidate_ids: Optional[set[str]], top_k: int
    ) -> list[RetrievedToolDoc]:
        """
        Retrieve candidate tools using embedding similarity.

        Args:
            query: User instruction
            candidate_ids: Optional set of valid candidate tool IDs
            top_k: Number of candidates to retrieve

        Returns:
            List of retrieved tool docs with scores
        """
        import numpy as np

        if self._tool_embeddings is None:
            return []

        # Embed query
        query_embedding = self.embedding_client.embed(
            texts=[query],
            model=self.config.embedding_model if self.config.embedding_model != "default" else None,
        )
        query_vector = np.asarray(query_embedding)[0]

        # Compute similarities
        if self.config.similarity_metric == "cosine":
            # Normalize for cosine similarity
            query_norm = query_vector / (np.linalg.norm(query_vector) + 1e-8)
            tool_norms = self._tool_embeddings / (
                np.linalg.norm(self._tool_embeddings, axis=1, keepdims=True) + 1e-8
            )
            scores = np.dot(tool_norms, query_norm)
        elif self.config.similarity_metric == "dot":
            scores = np.dot(self._tool_embeddings, query_vector)
        else:  # euclidean
            distances = np.linalg.norm(self._tool_embeddings - query_vector, axis=1)
            scores = 1.0 / (1.0 + distances)

        # Filter by candidate_ids if specified
        if candidate_ids:
            valid_indices = [i for i, tid in enumerate(self._tool_ids) if tid in candidate_ids]
            if not valid_indices:
                return []
            filtered_scores = [(i, scores[i]) for i in valid_indices]
        else:
            filtered_scores = list(enumerate(scores))

        # Sort by score and take top-k
        filtered_scores.sort(key=lambda x: x[1], reverse=True)
        top_results = filtered_scores[:top_k]

        # Build retrieved docs
        retrieved = []
        for idx, score in top_results:
            tool_id = self._tool_ids[idx]
            doc = self._tool_docs[tool_id]
            doc.retrieval_score = float(score)
            retrieved.append(doc)

        return retrieved

    def _build_llm_prompt(
        self, query: str, retrieved_docs: list[RetrievedToolDoc], top_k: int
    ) -> str:
        """Build prompt for LLM selection."""
        # Limit context size
        docs_for_context = retrieved_docs[: self.config.max_context_tools]

        # Build tool documentation string
        tool_docs_str = []
        for i, doc in enumerate(docs_for_context, 1):
            doc_str = f"{i}. **{doc.name}** (ID: `{doc.tool_id}`)\n"
            doc_str += f"   Description: {doc.description}\n"
            if doc.category:
                doc_str += f"   Category: {doc.category}\n"
            if doc.parameters and self.config.use_detailed_docs:
                params = []
                for pname, pinfo in list(doc.parameters.items())[:5]:  # Limit params
                    if isinstance(pinfo, dict):
                        ptype = pinfo.get("type", "any")
                        pdesc = pinfo.get("description", "")[:100]
                        params.append(f"{pname} ({ptype}): {pdesc}")
                if params:
                    doc_str += f"   Parameters: {'; '.join(params)}\n"
            tool_docs_str.append(doc_str)

        tools_text = "\n".join(tool_docs_str)

        prompt = f"""You are an expert API selector. Given a user task and a list of available APIs/tools,
select the {top_k} most relevant tools that can help complete the task.

## User Task
{query}

## Available Tools
{tools_text}

## Instructions
1. Analyze the user's task requirements carefully
2. Consider which tools have the capabilities to fulfill the requirements
3. Select exactly {top_k} tools, ordered by relevance (most relevant first)
4. Return ONLY a JSON array of tool IDs, no explanation needed

## Output Format
Return a JSON array of tool IDs:
["tool_id_1", "tool_id_2", ...]

## Your Selection (JSON array only):"""

        return prompt

    def _parse_llm_response(
        self, response: str, retrieved_docs: list[RetrievedToolDoc]
    ) -> list[str]:
        """Parse LLM response to extract selected tool IDs."""
        # Get valid tool IDs from retrieved docs
        valid_ids = {doc.tool_id for doc in retrieved_docs}

        # Try to parse JSON array
        response = response.strip()

        # Remove markdown code block if present
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            response = response.strip()

        try:
            selected = json.loads(response)
            if isinstance(selected, list):
                # Filter to only valid IDs
                return [tid for tid in selected if tid in valid_ids]
        except json.JSONDecodeError:
            pass

        # Fallback: try to extract tool IDs from text
        extracted = []
        for doc in retrieved_docs:
            if doc.tool_id in response or doc.name in response:
                extracted.append(doc.tool_id)

        return extracted

    def _select_impl(self, query: ToolSelectionQuery, top_k: int) -> list[ToolPrediction]:
        """
        Select tools using Gorilla retrieval-augmented approach.

        Args:
            query: Tool selection query
            top_k: Number of tools to select

        Returns:
            List of tool predictions
        """
        # Filter candidates if specified
        candidate_ids = set(query.candidate_tools) if query.candidate_tools else None

        # Stage 1: Retrieve candidates using embedding
        retrieve_k = max(self.config.top_k_retrieve, top_k * 3)
        retrieved_docs = self._retrieve_candidates(query.instruction, candidate_ids, retrieve_k)

        if not retrieved_docs:
            self.logger.warning(f"No tools retrieved for query {query.sample_id}")
            return []

        # If no LLM client, fall back to retrieval-only
        if self.llm_client is None:
            return self._retrieval_only_select(retrieved_docs, top_k)

        # Stage 2: LLM selection from retrieved candidates
        try:
            prompt = self._build_llm_prompt(query.instruction, retrieved_docs, top_k)

            response = self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
            )

            selected_ids = self._parse_llm_response(response, retrieved_docs)

            # Build predictions with scores
            predictions = []
            retrieval_scores = {doc.tool_id: doc.retrieval_score for doc in retrieved_docs}

            for rank, tool_id in enumerate(selected_ids[:top_k]):
                # Score = combination of LLM rank and retrieval score
                llm_score = 1.0 - (rank / top_k) * 0.5  # 1.0 -> 0.5 based on rank
                retrieval_score = max(0.0, min(1.0, retrieval_scores.get(tool_id, 0.0)))
                combined_score = max(0.0, min(1.0, 0.6 * llm_score + 0.4 * retrieval_score))

                predictions.append(
                    ToolPrediction(
                        tool_id=tool_id,
                        score=combined_score,
                        explanation=f"LLM rank: {rank + 1}, retrieval score: {retrieval_score:.3f}",
                        metadata={
                            "method": "gorilla",
                            "llm_rank": rank + 1,
                            "retrieval_score": retrieval_score,
                        },
                    )
                )

            # If LLM didn't return enough, supplement with retrieval results
            if len(predictions) < top_k:
                existing_ids = {p.tool_id for p in predictions}
                for doc in retrieved_docs:
                    if doc.tool_id not in existing_ids and len(predictions) < top_k:
                        # Clamp score to [0, 1] range
                        score = max(0.0, min(1.0, doc.retrieval_score * 0.8))
                        predictions.append(
                            ToolPrediction(
                                tool_id=doc.tool_id,
                                score=score,
                                metadata={
                                    "method": "gorilla_fallback",
                                    "retrieval_score": doc.retrieval_score,
                                },
                            )
                        )

            return predictions

        except Exception as e:
            self.logger.warning(f"LLM selection failed, falling back to retrieval: {e}")
            return self._retrieval_only_select(retrieved_docs, top_k)

    def _retrieval_only_select(
        self, retrieved_docs: list[RetrievedToolDoc], top_k: int
    ) -> list[ToolPrediction]:
        """Fallback to retrieval-only selection when LLM unavailable."""
        predictions = []
        for doc in retrieved_docs[:top_k]:
            # Clamp score to [0, 1] range (cosine similarity can be negative)
            score = max(0.0, min(1.0, doc.retrieval_score))
            predictions.append(
                ToolPrediction(
                    tool_id=doc.tool_id,
                    score=score,
                    metadata={
                        "method": "gorilla_retrieval_only",
                        "retrieval_score": doc.retrieval_score,
                    },
                )
            )
        return predictions

    def get_stats(self) -> dict:
        """Get selector statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "num_tools": len(self._tool_ids),
                "embedding_model": self.config.embedding_model,
                "llm_model": self.config.llm_model,
                "top_k_retrieve": self.config.top_k_retrieve,
                "has_llm_client": self.llm_client is not None,
            }
        )
        return stats
