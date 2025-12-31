"""FactExtractAction - 事实抽取策略（Mem0 风格）

从对话中抽取显著事实（salient facts），对齐 Mem0 的正确实现思路：
- 使用 LLM 提取事实列表（JSON 格式），失败时回退到简单启发式。
- 兼容无时间戳：使用 session_id 与 dialog_id 组合生成 session_round。
- 输出结构遵循 BasePreInsertAction 约定，字段包含 fact/text/embedding/metadata。

配置项（operators.pre_insert 下）：
- action: "extract"
- extract_type: "fact"
- method: "mem0_llm" | "simple"（默认 mem0_llm）
- keep_original: true/false（是否保留原始对话文本为一条记忆）
- add_to_metadata: true/false（是否把抽取的 facts 放进 metadata）
- mem0_llm_prompt: 自定义事实抽取提示词（可选）
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class FactExtractAction(BasePreInsertAction):
    """事实抽取 Action（Mem0 风格）"""

    def _init_action(self) -> None:
        self.method = self.config.get("method", "mem0_llm")
        self.keep_original = bool(self.config.get("keep_original", True))
        self.add_to_metadata = bool(self.config.get("add_to_metadata", True))

        # LLM 提示词：返回 {"facts": ["..."]}
        self.mem0_llm_prompt = self.config.get(
            "mem0_llm_prompt",
            (
                "You are an assistant that extracts salient facts from the given conversation. "
                "Return ONLY a compact JSON with the schema:\n"
                '{\n  "facts": ["..."]\n}\n'
                "Rules:\n"
                "- Each fact should be concise and self-contained.\n"
                "- Avoid duplicates; skip trivial greetings.\n"
                "- Do NOT include any explanation or extra keys.\n"
            ),
        )

        self.llm_generator = None

    def set_llm_generator(self, llm_generator):
        self.llm_generator = llm_generator

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        used_method = self.method
        llm_called: bool = False
        llm_error: str | None = None
        llm_model: str | None = None
        llm_base_url: str | None = None

        # 记录模型信息（可选）
        if self.llm_generator is not None:
            try:
                llm_model = getattr(self.llm_generator, "model_name", None)
            except Exception:
                llm_model = None
            try:
                llm_base_url = getattr(
                    getattr(self.llm_generator, "client", object()), "base_url", None
                )
            except Exception:
                llm_base_url = None

        # 抽取事实
        if self.method == "mem0_llm" and self.llm_generator is not None:
            try:
                prompt = self.mem0_llm_prompt + "\nText:\n" + text
                resp = self.llm_generator.generate(prompt)
                llm_called = True
                json_str = self._extract_json_block(resp)
                data = json.loads(json_str)
                facts: list[str] = [
                    self._clean_fact(f) for f in data.get("facts", []) if f and isinstance(f, str)
                ]
                facts = self._dedup_list(facts)
            except Exception as e:
                used_method = "simple"
                llm_called = False
                llm_error = f"{type(e).__name__}: {e}"
                facts = self._extract_simple_facts(text)
        else:
            facts = self._extract_simple_facts(text)

        # 元数据中的会话轮次（兼容无时间戳）
        session_id = input_data.data.get("session_id")
        dialog_id = input_data.data.get("dialog_id")
        session_round = (
            f"{session_id}:{dialog_id}"
            if session_id is not None and dialog_id is not None
            else None
        )

        entries: list[dict[str, Any]] = []

        # 可选：保留原始对话
        if self.keep_original:
            original_entry = {
                "text": text,
                "metadata": {
                    "action": "extract.fact",
                    "method": used_method,
                    "session_id": session_id,
                    "dialog_id": dialog_id,
                    "session_round": session_round,
                },
            }
            original_entry = self._set_default_fields(original_entry)
            original_entry["insert_method"] = "fact_insert_original"
            if self.add_to_metadata:
                original_entry["metadata"]["facts"] = facts
            original_entry["metadata"]["llm_called"] = llm_called
            if llm_model is not None:
                original_entry["metadata"]["llm_model"] = llm_model
            if llm_base_url is not None:
                original_entry["metadata"]["llm_base_url"] = str(llm_base_url)
            if llm_error is not None:
                original_entry["metadata"]["llm_error"] = llm_error
            entries.append(original_entry)

        # 为每条事实生成独立条目
        for idx, fact in enumerate(facts):
            entry = {
                "fact": fact,
                "text": fact,  # 兼容 MemoryInsert 侧统一字段
                "metadata": {
                    "action": "extract.fact",
                    "type": "fact",
                    "fact_index": idx,
                    "method": used_method,
                    "session_id": session_id,
                    "dialog_id": dialog_id,
                    "session_round": session_round,
                },
            }
            entry = self._set_default_fields(entry)
            entry["insert_method"] = "fact_insert_unit"
            entry["metadata"]["llm_called"] = llm_called
            if llm_model is not None:
                entry["metadata"]["llm_model"] = llm_model
            if llm_base_url is not None:
                entry["metadata"]["llm_base_url"] = str(llm_base_url)
            if llm_error is not None:
                entry["metadata"]["llm_error"] = llm_error
            entries.append(entry)

        # 调试输出：参考 KeywordExtractAction，打印 LLM 调用与事实数量
        try:
            print(
                f"[DEBUG Fact] LLM called={llm_called} method={used_method}"
                f" model={llm_model or '-'} base={llm_base_url or '-'}"
                f" facts={len(facts)}" + (f" error={llm_error}" if llm_error else "")
            )
        except Exception:
            pass

        return PreInsertOutput(
            memory_entries=entries,
            metadata={
                "facts": facts,
                "method": used_method,
                "preinsert_llm_called": llm_called,
                "preinsert_llm_model": llm_model,
                "preinsert_llm_base_url": llm_base_url,
                "preinsert_llm_error": llm_error,
            },
        )

    # -------------------- 简单回退抽取 --------------------
    def _extract_simple_facts(self, text: str) -> list[str]:
        """简单启发式事实抽取：
        - 基于句子分割
        - 过滤致意/无信息句子
        - 保留包含系动词/状态/拥有关系的短句
        """
        sentences = self._split_sentences(text)
        facts: list[str] = []
        for s in sentences:
            s_clean = self._clean_fact(s)
            if not s_clean:
                continue
            # 过滤寒暄
            if re.search(r"\b(hello|hi|thanks|thank you|bye)\b", s_clean, re.IGNORECASE):
                continue
            # 选择含有常见关系的句子
            if re.search(
                r"\b(is|are|was|were|has|have|lives|works|studies|born)\b", s_clean, re.IGNORECASE
            ):
                facts.append(s_clean)
        return self._dedup_list(facts)

    # -------------------- 工具方法 --------------------
    def _extract_json_block(self, text: str) -> str:
        """从返回文本中提取首个 JSON 对象字符串，可容忍前后噪声。

        优先提取三引号中的内容；若没有，则扫描提取首个平衡的大括号块。
        """
        text = text.strip()
        # 1) 先尝试 ```json ... ```
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            return m.group(1)

        # 2) 扫描提取首个平衡的大括号
        start = text.find("{")
        if start == -1:
            return text
        depth = 0
        end = start
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > start:
            return text[start:end]
        # 3) 回退：原样返回（交由 json.loads 报错后走简单抽取回退）
        return text

    def _split_sentences(self, text: str) -> list[str]:
        # 简单句子分割：按换行与句末标点
        parts = re.split(r"[\n\r]+|(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p and p.strip()]

    def _clean_fact(self, s: str) -> str:
        s = s.strip()
        # 去除前缀 role/speaker:
        s = re.sub(r"^(user|assistant|system|[A-Za-z]+):\s*", "", s)
        # 压缩空白
        s = re.sub(r"\s+", " ", s)
        return s

    def _dedup_list(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for it in items:
            if it not in seen:
                seen.add(it)
                out.append(it)
        return out
