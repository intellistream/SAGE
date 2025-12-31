"""EntityExtractAction - 实体抽取策略

从文本中抽取命名实体（人名、地名、组织等）。
适用于 Mem0, Mem0ᵍ 等需要实体识别的记忆体。

新增：mem0_llm 模式
- 参考 mem0 的正确实现（mem0/memory/graph_memory.py 的实体抽取流程），
    增加基于 LLM 的实体与类型抽取能力，并做规范化（全小写 + 空格转下划线）。
- 兼容原有 simple/spacy 方法；当 LLM 不可用或配置缺失时自动回退。

时间戳兼容：
- mem0 正确实现中有 created_at/updated_at；如果当前数据没有时间戳，
    这里使用 session_id 与 dialog_id 组合生成简易的会话轮次标记（session_round），
    并在 metadata 中统一记录，以保持上下游一致性。
"""

import json
import re

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class EntityExtractAction(BasePreInsertAction):
    """实体抽取 Action

    使用场景：
    - Mem0: 抽取实体建立知识图谱
    - Mem0ᵍ: 基于实体的记忆索引

    支持的抽取方法：
    - spacy: 使用 spaCy NER
    - simple: 简单的启发式方法
    - mem0_llm: 基于 LLM 的实体与类型抽取（参考 mem0 实现），并做名称规范化
    """

    def _init_action(self) -> None:
        """初始化实体抽取工具"""
        self.method = self.config.get("method", "simple")
        self.entity_types = self.config.get(
            "entity_types", ["PERSON", "ORG", "GPE", "LOC", "DATE", "TIME"]
        )

        # LLM 配置（用于 mem0_llm 模式）
        # 提示词可在 YAML 配置中覆盖：operators.pre_insert.mem0_llm_prompt
        self.mem0_llm_prompt = self.config.get(
            "mem0_llm_prompt",
            (
                "You are an assistant that extracts entities and their types from the given text. "
                "Return a compact JSON with the following schema: {\n"
                '  "entities": [ { "entity": "...", "entity_type": "..." } ]\n'
                "}. Do not include any explanation."
            ),
        )
        # 是否对实体名做规范化（小写 + 空格转下划线）
        self.normalize = bool(self.config.get("normalize", True))
        # 是否保留原始文本条目
        self.keep_original = bool(self.config.get("keep_original", True))

        # LLM 生成器（由上层注入，可选）
        self.llm_generator = None

        # 如果使用 spacy，加载模型
        if self.method == "spacy":
            try:
                import spacy

                model_name = self.config.get("spacy_model", "en_core_web_sm")
                self._nlp = spacy.load(model_name)
            except Exception:
                # 如果 spacy 不可用，回退到简单方法
                self.method = "simple"
                self._nlp = None
        else:
            self._nlp = None

    def set_llm_generator(self, llm_generator):
        """设置 LLM 生成器（与 TripleExtractAction 保持一致的注入方式）"""
        self.llm_generator = llm_generator

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行实体抽取

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含实体信息的记忆条目
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 抽取实体（根据模式选择具体方法），并记录 LLM 调用检测信息
        used_method = self.method
        llm_called: bool = False
        llm_error: str | None = None
        llm_model: str | None = None
        llm_base_url: str | None = None

        if self.method == "mem0_llm":
            # 优先走 LLM，失败则回退到 simple/spacy
            try:
                if not self.llm_generator:
                    raise RuntimeError("LLM generator not set")

                # 记录可能的模型/端点信息
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

                prompt = self.mem0_llm_prompt + "\nText:\n" + text
                resp = self.llm_generator.generate(prompt)
                llm_called = True

                json_str = self._extract_json_block(resp)
                data = json.loads(json_str)
                entities = []
                for item in data.get("entities", []):
                    ent_text = item.get("entity") or item.get("text") or ""
                    ent_type = item.get("entity_type") or item.get("type") or "UNKNOWN"
                    entities.append({"text": ent_text, "type": ent_type})
                entities = self._normalize_entities(entities)
            except Exception as e:
                # 回退：任意异常均视为 LLM 未成功运行
                used_method = "simple"
                llm_called = False
                llm_error = f"{type(e).__name__}: {e}"
                entities = self._extract_entities(text)
        else:
            entities = self._extract_entities(text)

        # 构建 metadata，兼容 mem0 的时间戳风格（用 session/dialog 代替）
        session_id = input_data.data.get("session_id")
        dialog_id = input_data.data.get("dialog_id")
        session_round = (
            f"{session_id}:{dialog_id}"
            if session_id is not None and dialog_id is not None
            else None
        )

        entries: list[dict[str, any]] = []

        if self.keep_original:
            # 保留原始文本作为一条记忆（便于下游与向量侧一致）
            original_entry = {
                "text": text,
                "entities": entities,
                "metadata": {
                    "action": "extract.entity",
                    "entity_count": len(entities),
                    "method": used_method,
                    "entity_types": self.entity_types,
                    "session_id": session_id,
                    "dialog_id": dialog_id,
                    "session_round": session_round,
                },
            }
            original_entry = self._set_default_fields(original_entry)
            original_entry["insert_method"] = "entity_insert_original"
            # 标注 LLM 调用检测信息（便于下游/日志快速判断是否真正走了大模型）
            original_entry["metadata"]["llm_called"] = llm_called
            if llm_model is not None:
                original_entry["metadata"]["llm_model"] = llm_model
            if llm_base_url is not None:
                original_entry["metadata"]["llm_base_url"] = str(llm_base_url)
            if llm_error is not None:
                original_entry["metadata"]["llm_error"] = llm_error
            entries.append(original_entry)

        # 可选：每个实体单独生成一条条目（便于后续按实体粒度索引/检索）
        for idx, ent in enumerate(entities):
            ent_text = ent.get("text") or ent.get("entity") or ""
            entry = {
                "text": ent_text,
                "entity": ent,
                "metadata": {
                    "action": "extract.entity",
                    "type": "entity",
                    "entity_index": idx,
                    "method": used_method,
                    "session_id": session_id,
                    "dialog_id": dialog_id,
                    "session_round": session_round,
                },
            }
            entry = self._set_default_fields(entry)
            entry["insert_method"] = "entity_insert_unit"
            # 同步 LLM 调用检测信息
            entry["metadata"]["llm_called"] = llm_called
            if llm_model is not None:
                entry["metadata"]["llm_model"] = llm_model
            if llm_base_url is not None:
                entry["metadata"]["llm_base_url"] = str(llm_base_url)
            if llm_error is not None:
                entry["metadata"]["llm_error"] = llm_error
            entries.append(entry)

        return PreInsertOutput(
            memory_entries=entries,
            metadata={
                "entities": entities,
                "method": used_method,
                "preinsert_llm_called": llm_called,
                "preinsert_llm_model": llm_model,
                "preinsert_llm_base_url": llm_base_url,
                "preinsert_llm_error": llm_error,
            },
        )

    def _extract_entities(self, text: str) -> list[dict[str, str]]:
        """抽取实体

        Args:
            text: 输入文本

        Returns:
            实体列表，每个实体包含 text, type, start, end
        """
        if self.method == "spacy" and self._nlp:
            return self._extract_by_spacy(text)
        else:
            return self._extract_simple(text)

    def _extract_by_spacy(self, text: str) -> list[dict[str, str]]:
        """使用 spaCy 抽取实体

        Args:
            text: 输入文本

        Returns:
            实体列表
        """
        doc = self._nlp(text)

        entities = []
        for ent in doc.ents:
            if ent.label_ in self.entity_types:
                entities.append(
                    {
                        "text": ent.text,
                        "type": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                    }
                )

        return entities

    def _extract_simple(self, text: str) -> list[dict[str, str]]:
        """简单的实体抽取（基于启发式规则）

        识别大写开头的词作为可能的实体。

        Args:
            text: 输入文本

        Returns:
            实体列表
        """
        import re

        # 匹配连续大写单词（可能是人名、地名等）
        pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
        matches = re.finditer(pattern, text)

        entities = []
        for match in matches:
            entities.append(
                {
                    "text": match.group(),
                    "type": "UNKNOWN",  # 简单方法无法判断类型
                    "start": match.start(),
                    "end": match.end(),
                }
            )

        # 去重
        seen = set()
        unique_entities = []
        for ent in entities:
            if ent["text"] not in seen:
                seen.add(ent["text"])
                unique_entities.append(ent)

        return self._normalize_entities(unique_entities)

    # -------------------- mem0_llm 抽取 --------------------
    def _extract_by_llm(self, text: str) -> list[dict[str, str]]:
        """使用 LLM 抽取实体与类型（参考 mem0 的实现思路）

        期望 LLM 返回 JSON：
        {
          "entities": [ { "entity": "alice", "entity_type": "person" }, ... ]
        }
        """
        # LLM 不可用则回退到简单方法
        if not self.llm_generator:
            return self._extract_simple(text)

        try:
            prompt = self.mem0_llm_prompt + "\nText:\n" + text
            response = self.llm_generator.generate(prompt)
            # 允许 LLM 返回包裹代码块的 JSON
            json_str = self._extract_json_block(response)
            data = json.loads(json_str)
            entities = []
            for item in data.get("entities", []):
                ent_text = item.get("entity") or item.get("text") or ""
                ent_type = item.get("entity_type") or item.get("type") or "UNKNOWN"
                entities.append({"text": ent_text, "type": ent_type})
            return self._normalize_entities(entities)
        except Exception:
            # 任意解析异常都回退到启发式
            return self._extract_simple(text)

    # -------------------- 工具方法 --------------------
    def _normalize_entities(self, entities: list[dict[str, str]]) -> list[dict[str, str]]:
        """将实体规范化为小写并将空格替换为下划线（与 mem0 保持一致的风格）"""
        if not self.normalize:
            return entities
        normalized = []
        for ent in entities:
            txt = (ent.get("text") or ent.get("entity") or "").strip()
            typ = (ent.get("type") or ent.get("entity_type") or "UNKNOWN").strip()
            txt_norm = re.sub(r"\s+", "_", txt.lower())
            typ_norm = re.sub(r"\s+", "_", typ.lower())
            normalized.append({"text": txt_norm, "type": typ_norm})
        return normalized

    def _extract_json_block(self, text: str) -> str:
        """从可能包含 ```json 代码块的文本中提取 JSON 内容"""
        text = text.strip()
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            return m.group(1)
        return text
