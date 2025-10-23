"""
Self-RAG Pipeline Implementation

Based on the Self-RAG paper (https://arxiv.org/abs/2310.11511)
Uses pre-retrieved documents from the dataset to generate answers.

This implementation uses the Self-RAG dataset format where each item contains:
- question: The question to answer
- answers: Ground truth answers
- ctxs: Pre-retrieved documents with title and text
"""

import json
from typing import Any, Dict, List

from sage.kernel.api.function.map_function import MapFunction
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.io.sink import FileSink
from sage.libs.io.source import FileSource


class SelfRAGRetriever(MapFunction):
    """
    Self-RAG Retriever - extracts pre-retrieved documents from dataset.

    Unlike traditional retrievers that perform retrieval, this simply
    extracts the pre-computed retrieved documents from the Self-RAG dataset.
    """

    def __init__(self, config: dict):
        self.top_k = config.get("top_k", 5)

    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pre-retrieved documents from the data item."""
        question = item["question"]
        ctxs = item.get("ctxs", [])

        # Extract top-k documents
        retrieved_docs = []
        for i, ctx in enumerate(ctxs[: self.top_k]):
            if "text" in ctx and ctx["text"].strip():
                doc = {
                    "rank": i + 1,
                    "title": ctx.get("title", ""),
                    "text": ctx["text"],
                    "score": ctx.get("score", 1.0),
                }
                retrieved_docs.append(doc)

        return {
            "question": question,
            "retrieved_docs": retrieved_docs,
            "ground_truth": item.get("answers", []),
            "id": item.get("id", ""),
        }


class SelfRAGPromptor(MapFunction):
    """
    Self-RAG Promptor - builds prompts with retrieved evidence.

    Constructs prompts in the Self-RAG format with numbered evidence paragraphs.
    """

    def __init__(self, config: dict):
        self.model_name = config.get("model_name", "mistral")
        self.use_context = config.get("use_context", True)

    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Build prompt with evidence paragraphs."""
        question = item["question"]
        retrieved_docs = item.get("retrieved_docs", [])

        # Build evidence context
        context = None
        if self.use_context and retrieved_docs:
            evidences = []
            for doc in retrieved_docs:
                rank = doc["rank"]
                title = doc["title"]
                text = doc["text"]
                evidence = f"[{rank}] {title}\n{text}"
                evidences.append(evidence)
            context = "\n".join(evidences)

        # Build prompt based on model type
        if self.use_context and context:
            if "llama" in self.model_name.lower():
                prompt = f"[INST]{context}\n{question}[/INST]"
            else:
                prompt = f"<s>[INST]{context}\n{question}[/INST]"
        else:
            if "llama" in self.model_name.lower():
                prompt = f"[INST]{question}[/INST]"
            else:
                prompt = f"### Instruction:\n{question}\n\n### Response:\n"

        item["prompt"] = prompt
        item["context"] = context
        return item


class SelfRAGGenerator(MapFunction):
    """
    Self-RAG Generator - generates answers using VLLM.

    Uses vLLM for efficient batch inference.
    """

    def __init__(self, config: dict):
        self.model_name = config.get("model_name", "mistralai/Mistral-7B-Instruct-v0.1")

        from vllm import LLM, SamplingParams

        self.llm = LLM(
            model=self.model_name,
            gpu_memory_utilization=config.get("gpu_memory_utilization", 0.8),
        )
        self.sampling_params = SamplingParams(
            temperature=config.get("temperature", 0),
            max_tokens=config.get("max_tokens", 100),
        )

    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Generate answer for the question."""
        prompt = item["prompt"]

        # Generate using vLLM
        outputs = self.llm.generate([prompt], self.sampling_params)
        response = outputs[0].outputs[0].text

        # Post-process output
        response = self._postprocess(response)

        item["model_output"] = response
        return item

    def _postprocess(self, text: str) -> str:
        """Clean up model output."""
        # Take first paragraph
        text = text.split("\n\n")[0]
        # Remove end tokens
        text = text.replace("</s>", "")
        # Remove leading space
        if text and text[0] == " ":
            text = text[1:]
        return text


def process_item(item: Dict[str, Any], config: dict) -> Dict[str, Any]:
    """
    Process a single item through the Self-RAG pipeline.

    This is a simplified interface for benchmark runner integration.

    Args:
        item: Data item with keys: question, answers, ctxs
        config: Pipeline configuration

    Returns:
        Result dictionary with: id, question, prediction, ground_truth
    """
    # Initialize components
    retriever = SelfRAGRetriever(config)
    promptor = SelfRAGPromptor(config)
    generator = SelfRAGGenerator(config)

    # Process through pipeline
    retrieved = retriever.execute(item)
    prompted = promptor.execute(retrieved)
    result = generator.execute(prompted)

    # Format output
    return {
        "id": item.get("id", "unknown"),
        "question": item["question"],
        "prediction": result["prediction"],
        "ground_truth": item.get("answers", []),
        "retrieved_docs": result.get("retrieved_docs", []),
    }


def run_selfrag_pipeline(config_path: str):
    """
    Run Self-RAG pipeline.

    Args:
        config_path: Path to configuration YAML file
    """
    import yaml

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    env = LocalEnvironment("selfrag_pipeline")

    (
        env.from_source(FileSource, {"file_path": config["data_path"]})
        .map(SelfRAGRetriever, config["retriever"])
        .map(SelfRAGPromptor, config["promptor"])
        .map(SelfRAGGenerator, config["generator"])
        .sink(FileSink, {"output_path": config["output_path"]})
    )

    env.submit()
    env.close()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Default config path
    config_dir = Path(__file__).parent.parent.parent / "config"
    config_path = config_dir / "config_selfrag.yaml"

    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    print(f"🚀 Running Self-RAG Pipeline")
    print(f"📝 Config: {config_path}")

    run_selfrag_pipeline(str(config_path))

    print("✅ Self-RAG pipeline completed!")
