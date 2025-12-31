"""KeywordExtractAction - A-Mem Note 抽取实现（保留类名）

说明：
- 将原先 `AMemNoteExtractAction` 的能力迁移到 `KeywordExtractAction`，
  以便通过 `extract_type: "keyword"` 使用 A-Mem 的 Note 抽取（keywords/context/tags）。
- 支持 LLM 路径（优先），失败时回退到简易关键词抽取；保留调用检测元数据。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput

DEFAULT_ANALYSIS_PROMPT = (
    """
Generate a structured analysis of the following content by:
1. Identifying the most salient keywords (focus on nouns, verbs, and key concepts)
2. Extracting core themes and contextual elements
3. Creating relevant categorical tags

Format the response as a JSON object:
{
  "keywords": [
    // several specific, distinct keywords that capture key concepts and terminology
    // Order from most to least important
    // Don't include keywords that are the name of the speaker or time
    // At least three keywords, but don't be too redundant.
  ],
  "context":
    // one sentence summarizing:
    // - Main topic/domain
    // - Key arguments/points
    // - Intended audience/purpose
  ,
  "tags": [
    // several broad categories/themes for classification
    // Include domain, format, and type tags
    // At least three tags, but don't be too redundant.
  ]
}

Content for analysis:
{content}
"""
).strip()


class KeywordExtractAction(BasePreInsertAction):
    """A-Mem 的 Note 抽取（保留类名 KeywordExtractAction）

    优先使用 LLM 依据 analysis_prompt 产出 JSON：{keywords, context, tags}；
    如失败则回退到简易关键词抽取与空上下文/标签。
    """

    def _init_action(self) -> None:  # noqa: D401
        cfg = self.config or {}
        self.analysis_prompt: str = cfg.get("analysis_prompt", DEFAULT_ANALYSIS_PROMPT)
        self.max_keywords: int = int(cfg.get("max_keywords", 10))
        self.add_to_metadata: bool = bool(cfg.get("add_to_metadata", True))

        # 运行期由 PreInsert 主算子注入（llm/embedding 可选）
        self._llm_generator = None  # type: ignore[attr-defined]

    # 可被 PreInsert 主算子注入
    def set_llm_generator(self, generator) -> None:  # pragma: no cover - 按约定注入
        self._llm_generator = generator

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:  # noqa: D401
        # 1) 格式化对话
        dialogs = input_data.data.get("dialogs", [])
        dialogue_text = self._format_dialogue(dialogs)

        # 2) 抽取 note 结构
        keywords: list[str] = []
        context: str = ""
        tags: list[str] = []

        # 尝试 LLM 路径
        used_method = "llm"
        llm_called: bool = False
        llm_error: str | None = None
        llm_model: str | None = None
        llm_base_url: str | None = None
        try:
            if self._llm_generator is None:
                raise RuntimeError("LLM generator not set")

            # 使用安全填充，避免花括号导致的 KeyError
            prompt = self._fill_prompt(dialogue_text)

            # 记录可用的模型/端点信息（若可获取）
            try:
                llm_model = getattr(self._llm_generator, "model_name", None)
            except Exception:
                llm_model = None
            try:
                llm_base_url = getattr(
                    getattr(self._llm_generator, "client", object()), "base_url", None
                )
            except Exception:
                llm_base_url = None

            result_obj: Any = self._llm_generator.generate_json(prompt, default={})
            llm_called = True
            if isinstance(result_obj, str):
                try:
                    result_obj = json.loads(result_obj)
                except Exception:
                    result_obj = {}

            if isinstance(result_obj, dict):
                kws = result_obj.get("keywords") or []
                ctx = result_obj.get("context") or ""
                tgs = result_obj.get("tags") or []

                if isinstance(kws, list):
                    keywords = [str(k).strip() for k in kws if str(k).strip()]
                if isinstance(ctx, str):
                    context = ctx.strip()
                if isinstance(tgs, list):
                    tags = [str(t).strip() for t in tgs if str(t).strip()]

            # 约束关键词数量
            if self.max_keywords > 0 and len(keywords) > self.max_keywords:
                keywords = keywords[: self.max_keywords]

        except Exception as e:
            # 回退：基于词频的简单关键词抽取
            used_method = "simple"
            llm_called = False
            llm_error = f"{type(e).__name__}: {e}"
            keywords = self._extract_keywords_simple(dialogue_text, max_k=self.max_keywords)
            context = ""
            tags = []

        # 3) 组装 memory_entry
        entry = {
            "text": dialogue_text,
            "metadata": {
                "action": "extract.keyword",
                "method": used_method,
            },
        }
        entry = self._set_default_fields(entry)
        entry["insert_method"] = "note_insert"

        if self.add_to_metadata:
            note_meta = {
                "keywords": keywords,
                "context": context,
                "tags": tags,
            }
            entry["metadata"].setdefault("note", note_meta)

        # 标注 LLM 调用检测信息
        entry["metadata"]["llm_called"] = llm_called
        if llm_model is not None:
            entry["metadata"]["llm_model"] = llm_model
        if llm_base_url is not None:
            entry["metadata"]["llm_base_url"] = str(llm_base_url)
        if llm_error is not None:
            entry["metadata"]["llm_error"] = llm_error

        try:
            print(
                f"[DEBUG Keyword] LLM called={llm_called} method={used_method}"
                f" model={llm_model or '-'} base={llm_base_url or '-'}"
                f" keywords={len(keywords)}" + (f" error={llm_error}" if llm_error else "")
            )
        except Exception:
            pass

        return PreInsertOutput(
            memory_entries=[entry],
            metadata={
                "note_keywords": keywords,
                "note_context": context,
                "note_tags": tags,
                "preinsert_llm_called": llm_called,
                "preinsert_llm_model": llm_model,
                "preinsert_llm_base_url": llm_base_url,
                "preinsert_llm_error": llm_error,
            },
        )

    def _fill_prompt(self, dialogue_text: str) -> str:
        """安全地把对话文本填入 prompt，而不触发 str.format 的大括号解析。"""
        p = self.analysis_prompt
        if "{content}" in p:
            return p.replace("{content}", dialogue_text)
        if "{dialogue}" in p:
            return p.replace("{dialogue}", dialogue_text)
        if "{text}" in p:
            return p.replace("{text}", dialogue_text)
        return p + "\n\nContent:\n" + dialogue_text

    def _extract_keywords_simple(self, text: str, max_k: int = 10) -> list[str]:
        words = re.findall(r"\b\w+\b", (text or "").lower())
        stop = {
            "the",
            "is",
            "at",
            "which",
            "on",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "with",
            "to",
            "for",
            "of",
            "as",
            "by",
            "from",
            "that",
            "this",
            "it",
            "i",
        }
        tokens = [w for w in words if w not in stop and len(w) >= 2]
        freq = Counter(tokens)
        return [w for w, _ in freq.most_common(max_k or 10)]
