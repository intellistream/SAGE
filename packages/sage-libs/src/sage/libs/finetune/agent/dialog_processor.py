"""Agent dialog processing utilities for SFT/RL training."""

from __future__ import annotations

import json
import logging
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from datasets import Dataset

from sage.data.sources.agent_sft import AgentSFTDataLoader
from sage.data.sources.agent_sft.schemas import AgentSFTDialog
from sage.data.sources.agent_tools import AgentToolsDataLoader
from sage.libs.finetune.data import format_alpaca_sample, format_conversation_sample

from .data_formatter import AgentSFTFormatter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessedDialog:
    """Container for processed dialog samples."""

    dialog_id: str
    task_type: str
    text: str
    metadata: dict[str, Any]
    target_tools: list[str]
    split: str
    source: str = "agent_sft"

    def to_record(self) -> dict:
        """Convert to a dictionary suitable for HuggingFace datasets."""
        return {
            "dialog_id": self.dialog_id,
            "task_type": self.task_type,
            "text": self.text,
            "metadata": self.metadata,
            "target_tools": self.target_tools,
            "split": self.split,
            "source": self.source,
        }

    def to_json(self) -> str:
        """Serialize to JSON string for caching/debug."""
        return json.dumps(self.to_record(), ensure_ascii=False)


class AgentDialogProcessor:
    """Preprocess agent dialogs into model-ready text samples."""

    SUPPORTED_SOURCES = {"agent_sft"}

    def __init__(
        self,
        formatter: Optional[AgentSFTFormatter] = None,
        tool_loader: Optional[AgentToolsDataLoader] = None,
        seed: int = 42,
    ) -> None:
        self.tool_loader = tool_loader or AgentToolsDataLoader()
        self.formatter = formatter or AgentSFTFormatter(
            output_format="chatml",
            tool_loader=self.tool_loader,
        )
        self._seed = seed
        self._rng = random.Random(seed)
        self._loaders: dict[str, AgentSFTDataLoader] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build_samples(
        self,
        data_uri: str,
        *,
        limit: Optional[int] = None,
        output_format: Optional[str] = None,
        task_weights: Optional[dict[str, float]] = None,
        shuffle: bool = True,
    ) -> list[ProcessedDialog]:
        """Build processed dialog samples from the requested split."""

        source, split = self._parse_data_uri(data_uri)
        dialogs = list(self._get_loader(source).iter_dialogs(split))
        if not dialogs:
            logger.warning("No dialogs found for %s", data_uri)
            return []

        logger.info("Loaded %d dialogs from %s:%s", len(dialogs), source, split)

        selected_dialogs = self._select_dialogs(
            dialogs,
            limit=limit,
            shuffle=shuffle,
            task_weights=task_weights,
        )

        fmt = output_format or self.formatter.output_format
        formatter = self._get_formatter(fmt)

        processed: list[ProcessedDialog] = []
        for dialog in selected_dialogs:
            try:
                sample = self._format_dialog(dialog, formatter, split, source)
                metrics = self._compute_dialog_metrics(sample)
                sample.metadata.update(metrics)
                processed.append(sample)
            except Exception as exc:  # pragma: no cover - safety net
                logger.warning(
                    "Failed to format dialog %s (%s): %s",
                    dialog.dialog_id,
                    split,
                    exc,
                )
                continue

        return processed

    def iter_texts(
        self,
        data_uri: str,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Iterate over processed dialog texts only."""

        for sample in self.build_samples(data_uri, **kwargs):
            yield sample.text

    def to_dataset(
        self,
        data_uri: str,
        *,
        limit: Optional[int] = None,
        output_format: Optional[str] = None,
        task_weights: Optional[dict[str, float]] = None,
        shuffle: bool = True,
    ) -> Dataset:
        """Return a HuggingFace dataset constructed from processed dialogs."""

        samples = self.build_samples(
            data_uri,
            limit=limit,
            output_format=output_format,
            task_weights=task_weights,
            shuffle=shuffle,
        )
        records = [sample.to_record() for sample in samples]
        return Dataset.from_list(records)

    def export_jsonl(
        self,
        data_uri: str,
        output_path: str | Path,
        **kwargs: Any,
    ) -> Path:
        """Export processed samples to a JSONL file for inspection/caching."""

        output_path = Path(output_path)
        samples = self.build_samples(data_uri, **kwargs)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fp:
            for sample in samples:
                fp.write(sample.to_json() + "\n")
        logger.info("Exported %d samples to %s", len(samples), output_path)
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _parse_data_uri(self, data_uri: str) -> tuple[str, str]:
        try:
            source, split = data_uri.split(":", 1)
        except ValueError as exc:
            raise ValueError(
                f"Invalid data uri '{data_uri}'. Expected format '<source>:<split>'"
            ) from exc

        source = source.strip()
        split = split.strip()

        if source not in self.SUPPORTED_SOURCES:
            raise ValueError(f"Unsupported data source '{source}'")
        if split not in {"train", "dev", "test"}:
            raise ValueError(f"Unsupported split '{split}'")
        return source, split

    def _get_loader(self, source: str) -> AgentSFTDataLoader:
        if source not in self._loaders:
            if source == "agent_sft":
                self._loaders[source] = AgentSFTDataLoader()
            else:  # pragma: no cover - future extensions
                raise ValueError(f"Unsupported data source '{source}'")
        return self._loaders[source]

    def _get_formatter(self, output_format: str) -> AgentSFTFormatter:
        if output_format == self.formatter.output_format:
            return self.formatter
        return AgentSFTFormatter(
            output_format=output_format,
            include_tool_descriptions=self.formatter.include_tool_descriptions,
            tool_loader=self.formatter.tool_loader,
            max_tools_in_prompt=self.formatter.max_tools_in_prompt,
        )

    def _select_dialogs(
        self,
        dialogs: list[AgentSFTDialog],
        *,
        limit: Optional[int],
        shuffle: bool,
        task_weights: Optional[dict[str, float]],
    ) -> list[AgentSFTDialog]:
        if shuffle:
            self._rng.shuffle(dialogs)

        if not task_weights:
            if limit is None:
                return dialogs
            return dialogs[:limit]

        weight_map = self._normalize_weights(task_weights, dialogs)
        ordered = self._weighted_shuffle(dialogs, weight_map)

        if limit is None:
            return ordered
        return ordered[:limit]

    def _normalize_weights(
        self,
        weights: dict[str, float],
        dialogs: Iterable[AgentSFTDialog],
    ) -> dict[str, float]:
        task_set: dict[str, float] = {}
        default_weight = 1.0

        for dialog in dialogs:
            task = self._get_task_type(dialog)
            if task not in task_set:
                task_set[task] = max(float(weights.get(task, default_weight)), 1e-3)

        total = sum(task_set.values())
        if not task_set or total == 0:
            return dict.fromkeys(task_set, 1.0)

        return {task: weight / total for task, weight in task_set.items()}

    def _weighted_shuffle(
        self,
        dialogs: list[AgentSFTDialog],
        weight_map: dict[str, float],
    ) -> list[AgentSFTDialog]:
        decorated: list[tuple[float, AgentSFTDialog]] = []
        for dialog in dialogs:
            task = self._get_task_type(dialog)
            weight = max(weight_map.get(task, 1.0), 1e-3)
            u = self._rng.random()
            key = u ** (1.0 / weight)
            decorated.append((key, dialog))

        decorated.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in decorated]

    def _format_dialog(
        self,
        dialog: AgentSFTDialog,
        formatter: AgentSFTFormatter,
        split: str,
        source: str,
    ) -> ProcessedDialog:
        formatted = formatter.format_dialog(dialog)
        text = self._render_text(formatted)
        task_type = self._get_task_type(dialog)

        return ProcessedDialog(
            dialog_id=dialog.dialog_id,
            task_type=task_type,
            text=text,
            metadata=dict(dialog.metadata),
            target_tools=list(dialog.target_tools),
            split=split,
            source=source,
        )

    # ------------------------------------------------------------------
    # Metrics for coreset / continual learning
    # ------------------------------------------------------------------
    def _compute_dialog_metrics(self, sample: ProcessedDialog) -> dict[str, float]:
        tokens = self._tokenize(sample.text)
        length = len(tokens)
        unique_tokens = len(set(tokens)) or 1
        lexical_diversity = unique_tokens / max(length, 1)

        entropy = 0.0
        if tokens:
            freq = Counter(tokens)
            total = float(length)
            entropy = -sum(
                (count / total) * math.log(count / total + 1e-9) for count in freq.values()
            )

        difficulty = length / 512.0 + entropy / 5.0
        difficulty = float(min(max(difficulty, 0.0), 5.0))

        if isinstance(sample.metadata.get("loss"), (int, float)):
            difficulty = float(sample.metadata["loss"])

        return {
            "loss": difficulty,
            "lexical_diversity": float(lexical_diversity),
            "token_length": float(length),
        }

    def _tokenize(self, text: str) -> list[str]:
        return [token for token in text.lower().split() if token]

    def _render_text(self, formatted: dict) -> str:
        if "text" in formatted:
            return formatted["text"]

        if {"instruction", "output"}.issubset(formatted.keys()):
            normalized = format_alpaca_sample(
                {
                    "instruction": formatted["instruction"],
                    "input": formatted.get("input", ""),
                    "output": formatted["output"],
                }
            )
            return normalized["text"]

        if "conversations" in formatted:
            conversations = []
            for message in formatted["conversations"]:
                role = message.get("role") or message.get("from", "user")
                value = message.get("content") or message.get("value", "")
                role = self._normalize_role(role)
                conversations.append({"role": role, "content": value})

            normalized = format_conversation_sample({"conversations": conversations})
            return normalized["text"]

        raise ValueError("Unsupported formatted sample structure")

    def _normalize_role(self, role: str) -> str:
        mapping = {
            "human": "user",
            "gpt": "assistant",
            "observation": "tool",
        }
        return mapping.get(role, role)

    def _get_task_type(self, dialog: AgentSFTDialog) -> str:
        metadata_type = dialog.metadata.get("task_type")
        if metadata_type:
            return metadata_type

        try:
            return self.formatter._classify_task(dialog)  # pylint: disable=protected-access
        except Exception:  # pragma: no cover
            return "tool_selection"
