"""
ACEBench/ToolACE Data Loader

Provides utilities to load and convert ToolACE dataset from HuggingFace
to SAGE benchmark format for tool selection evaluation.

Dataset: https://huggingface.co/datasets/Team-ACE/ToolACE

The ToolACE format uses:
- system: Contains tool definitions in JSON format within the prompt
- conversations: List of user/assistant/tool exchanges

We convert this to SAGE's tool_selection format:
- sample_id: Unique identifier
- instruction: User query
- candidate_tools: List of tool IDs extracted from system prompt
- ground_truth: Expected tool calls from assistant response
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Parsed tool definition from ToolACE."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolDefinition:
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
        )


@dataclass
class ACEBenchSample:
    """A single ToolACE sample converted to SAGE format."""

    sample_id: str
    instruction: str
    system_prompt: str
    tools: list[ToolDefinition]
    expected_tool_calls: list[str]  # Tool names that should be called
    expected_arguments: list[dict[str, Any]]  # Arguments for each call
    full_conversation: list[dict[str, str]]

    def to_sage_format(self) -> dict[str, Any]:
        """Convert to SAGE benchmark format."""
        return {
            "sample_id": self.sample_id,
            "task_type": "tool_selection",
            "instruction": self.instruction,
            "context": self.system_prompt,
            "candidate_tools": [t.name for t in self.tools],
            "ground_truth": {
                "top_k": self.expected_tool_calls,
                "arguments": self.expected_arguments,
                "explanation": "Converted from ToolACE dataset",
            },
            "metadata": {
                "source": "ToolACE",
                "difficulty": self._estimate_difficulty(),
                "tags": ["tool_selection", "acebench"],
            },
        }

    def _estimate_difficulty(self) -> str:
        """Estimate task difficulty based on number of tool calls."""
        n_calls = len(self.expected_tool_calls)
        if n_calls == 0:
            return "easy"  # No tool needed
        elif n_calls == 1:
            return "easy"
        elif n_calls <= 3:
            return "medium"
        else:
            return "hard"


class ToolACEParser:
    """Parser for ToolACE dataset format."""

    # Regex to extract tool calls like: [ToolName(arg1="val1", arg2=val2)]
    TOOL_CALL_PATTERN = re.compile(r"\[([a-zA-Z_][a-zA-Z0-9_\s/\-]*)\((.*?)\)\]", re.DOTALL)

    @classmethod
    def parse_system_prompt(cls, system: str) -> list[ToolDefinition]:
        """Extract tool definitions from system prompt."""
        tools = []

        # Find JSON array of tools in system prompt
        # Look for patterns like: [...] containing tool definitions
        json_matches = re.findall(r"\[\{.*?\}\]", system, re.DOTALL)

        for match in json_matches:
            try:
                tool_list = json.loads(match)
                for tool_dict in tool_list:
                    if isinstance(tool_dict, dict) and "name" in tool_dict:
                        tools.append(ToolDefinition.from_dict(tool_dict))
            except json.JSONDecodeError:
                continue

        # If regex didn't work, try parsing the whole thing
        if not tools:
            try:
                # Sometimes the whole system is a JSON array
                start_idx = system.find("[{")
                if start_idx >= 0:
                    end_idx = system.rfind("}]") + 2
                    if end_idx > start_idx:
                        tool_list = json.loads(system[start_idx:end_idx])
                        for tool_dict in tool_list:
                            if isinstance(tool_dict, dict) and "name" in tool_dict:
                                tools.append(ToolDefinition.from_dict(tool_dict))
            except json.JSONDecodeError:
                pass

        return tools

    @classmethod
    def parse_tool_call(cls, response: str) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Parse tool calls from assistant response.

        Returns:
            Tuple of (tool_names, arguments_list)
        """
        tool_names = []
        arguments_list = []

        matches = cls.TOOL_CALL_PATTERN.findall(response)
        for tool_name, args_str in matches:
            tool_name = tool_name.strip()
            tool_names.append(tool_name)

            # Parse arguments
            args = {}
            if args_str.strip():
                # Parse key=value pairs
                for part in cls._split_args(args_str):
                    if "=" in part:
                        key, value = part.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip("\"'")
                        args[key] = value
            arguments_list.append(args)

        return tool_names, arguments_list

    @classmethod
    def _split_args(cls, args_str: str) -> list[str]:
        """Split arguments string handling nested quotes."""
        parts = []
        current = []
        in_quotes = False
        quote_char = None

        for char in args_str:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current.append(char)
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current.append(char)
            elif char == "," and not in_quotes:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            parts.append("".join(current).strip())

        return [p for p in parts if p]


class ToolACELoader:
    """Load ToolACE dataset from HuggingFace."""

    def __init__(
        self,
        split: str = "train",
        max_samples: Optional[int] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize loader.

        Args:
            split: Dataset split to load
            max_samples: Maximum number of samples to load (None for all)
            cache_dir: Directory to cache downloaded data
        """
        self.split = split
        self.max_samples = max_samples
        self.cache_dir = cache_dir

    def load(self) -> Iterator[ACEBenchSample]:
        """
        Load and parse ToolACE samples.

        Yields:
            ACEBenchSample objects
        """
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError("datasets library required. Install with: pip install datasets")

        logger.info(f"Loading ToolACE dataset (split={self.split})")

        # Load with streaming to avoid downloading entire dataset
        dataset = load_dataset(
            "Team-ACE/ToolACE",
            split=self.split,
            streaming=True,
            cache_dir=str(self.cache_dir) if self.cache_dir else None,
        )

        count = 0
        for idx, sample in enumerate(dataset):
            if self.max_samples and count >= self.max_samples:
                break

            parsed = self._parse_sample(sample, idx)
            if parsed is not None:
                count += 1
                yield parsed

        logger.info(f"Loaded {count} samples from ToolACE")

    def _parse_sample(self, sample: dict[str, Any], idx: int) -> Optional[ACEBenchSample]:
        """Parse a single ToolACE sample."""
        try:
            system = sample.get("system", "")
            conversations = sample.get("conversations", [])

            if not conversations:
                return None

            # Extract tools from system prompt
            tools = ToolACEParser.parse_system_prompt(system)
            if not tools:
                logger.debug(f"Sample {idx}: No tools found in system prompt")
                return None

            # Get user query (first message)
            user_msg = ""
            for conv in conversations:
                if conv.get("from") == "user":
                    user_msg = conv.get("value", "")
                    break

            if not user_msg:
                return None

            # Get assistant response (first assistant message)
            assistant_response = ""
            for conv in conversations:
                if conv.get("from") == "assistant":
                    assistant_response = conv.get("value", "")
                    break

            if not assistant_response:
                return None

            # Parse tool calls from assistant response
            tool_names, arguments = ToolACEParser.parse_tool_call(assistant_response)

            return ACEBenchSample(
                sample_id=f"ace_{idx:06d}",
                instruction=user_msg,
                system_prompt=system,
                tools=tools,
                expected_tool_calls=tool_names,
                expected_arguments=arguments,
                full_conversation=conversations,
            )

        except Exception as e:
            logger.warning(f"Failed to parse sample {idx}: {e}")
            return None


def load_acebench_samples(
    max_samples: int = 100,
    split: str = "train",
) -> list[dict[str, Any]]:
    """
    Convenience function to load ToolACE samples in SAGE format.

    Args:
        max_samples: Maximum number of samples
        split: Dataset split

    Returns:
        List of samples in SAGE benchmark format
    """
    loader = ToolACELoader(split=split, max_samples=max_samples)
    samples = []
    for sample in loader.load():
        samples.append(sample.to_sage_format())
    return samples


def save_acebench_to_jsonl(
    output_path: Path,
    max_samples: int = 1000,
    split: str = "train",
) -> int:
    """
    Load ToolACE samples and save to JSONL file.

    Args:
        output_path: Output file path
        max_samples: Maximum samples to save
        split: Dataset split

    Returns:
        Number of samples saved
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    loader = ToolACELoader(split=split, max_samples=max_samples)
    count = 0

    with open(output_path, "w", encoding="utf-8") as f:
        for sample in loader.load():
            sage_format = sample.to_sage_format()
            f.write(json.dumps(sage_format, ensure_ascii=False) + "\n")
            count += 1

    logger.info(f"Saved {count} samples to {output_path}")
    return count


if __name__ == "__main__":
    # Quick test

    logging.basicConfig(level=logging.INFO)

    print("Loading ToolACE samples...")
    samples = load_acebench_samples(max_samples=5)

    print(f"\nLoaded {len(samples)} samples:\n")
    for s in samples:
        print(f"ID: {s['sample_id']}")
        print(f"Instruction: {s['instruction'][:100]}...")
        print(f"Tools: {s['candidate_tools'][:5]}...")
        print(f"Expected: {s['ground_truth']['top_k']}")
        print()
