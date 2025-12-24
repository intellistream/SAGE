"""SCM Three-Way Decision (drop / summary / raw)

实现 SCM4LLMs 的 post_retrieval 三元决策：
- 在历史预算内优先保留原文 raw
- 超预算时，对每条候选用判题 prompt 判断是否必要；必要则尝试摘要 summary，否则直接丢弃 drop
- 上一轮对话（最近一轮）原样直拼，独立预算限制

兼容性说明：
- 若没有真实时间戳，使用 metadata.turn_index 近似时间顺序；无此字段则保留原始顺序
- 若检索结果不含预插阶段保存的 summary/original_text，摘要回退为简单压缩（截断）
- 计数方式支持 char/word/tiktoken（默认 char）

调试输出：
- 统计 LLM 是否被调用、调用次数、模型名与 base_url；为每条记忆记录决策（raw/summary/drop）
"""

from __future__ import annotations

from typing import Any, Optional

from ..base import (
    BasePostRetrievalAction,
    MemoryItem,
    PostRetrievalInput,
    PostRetrievalOutput,
)


class SCMThreeWayMergeAction(BasePostRetrievalAction):
    """SCM 三元决策合并策略"""

    def _init_action(self) -> None:
        # 预算与计数配置
        self.max_history_tokens = int(self.config.get("max_history_tokens", 2500))
        self.max_pre_turn_tokens = int(self.config.get("max_pre_turn_tokens", 500))
        self.token_counter = str(self.config.get("token_counter", "char")).lower()
        # 判题与格式化 prompt
        self.judge_prompt = self.config.get("judge_prompt", "")
        # Tokenizer 初始化（仅当需要 tiktoken）
        self._tokenizer = None
        if self.token_counter == "tiktoken":
            try:
                import tiktoken  # type: ignore

                # 使用常见编码；如需定制可扩展配置
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self._tokenizer = None
                self.token_counter = "char"  # 回退

        # LLM 生成器占位
        self._llm_generator = None

    # Operator 会在构造后尝试注入 LLM/Embedding 生成器
    def set_llm_generator(self, llm_generator: Any) -> None:
        self._llm_generator = llm_generator

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Optional[Any] = None,
    ) -> PostRetrievalOutput:
        # 读取检索结果
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(
                memory_items=[],
                metadata={"action": "scm_three_way", "note": "empty memory_data"},
            )

        question = input_data.data.get("question") or input_data.data.get("query") or ""

        # 按 turn_index 近似时间排序，并识别“上一轮”
        def get_turn_index(it: MemoryItem) -> int:
            try:
                ti = it.metadata.get("turn_index")
                return int(ti) if ti is not None else -1
            except Exception:
                return -1

        # 找到最大 turn_index（视为上一轮）
        max_turn = max([get_turn_index(it) for it in items]) if items else -1
        pre_turn_items = [it for it in items if get_turn_index(it) == max_turn and max_turn >= 0]
        history_candidates = [it for it in items if get_turn_index(it) != max_turn or max_turn < 0]

        # 历史候选按时间升序；若无 turn_index，保持现有顺序
        if any(get_turn_index(it) >= 0 for it in history_candidates):
            history_candidates.sort(key=lambda x: (get_turn_index(x), x.original_index))

        # 预算计数
        used_history_tokens = 0
        used_pre_tokens = 0

        result_items: list[MemoryItem] = []
        decisions = {"raw": 0, "summary": 0, "drop": 0}

        # LLM 调用统计
        llm_called = False
        llm_calls = 0
        llm_model = None
        llm_base_url = None
        try:
            if self._llm_generator is not None:
                llm_model = getattr(self._llm_generator, "model_name", None)
                llm_base_url = (
                    str(getattr(getattr(self._llm_generator, "client", object()), "base_url", ""))
                    or None
                )
        except Exception:
            pass

        # 逐条候选执行三元决策
        for item in history_candidates:
            raw_text = item.metadata.get("original_text") or item.text or ""
            summary_text = item.metadata.get("summary") or self._simple_summary(raw_text)

            raw_tokens = self._count_tokens(raw_text)
            # 尝试 raw（优先）
            if used_history_tokens + raw_tokens <= self.max_history_tokens:
                result_items.append(self._clone_item_with_text(item, raw_text, decision="raw"))
                used_history_tokens += raw_tokens
                decisions["raw"] += 1
                continue

            # 触发预算溢出：调用判题判断必要性
            is_necessary = False
            if self.judge_prompt:
                judge_prompt = self._format_judge_prompt(
                    self.judge_prompt, content=raw_text, query=question
                )
                try:
                    if self._llm_generator is not None:
                        llm_called = True
                        llm_calls += 1
                        judge_output = self._llm_generator.generate(judge_prompt, temperature=0)
                    elif llm is not None:
                        # 兼容 Operator 传入 llm 参数
                        llm_called = True
                        llm_calls += 1
                        judge_output = llm.generate(judge_prompt, temperature=0)
                    else:
                        judge_output = ""
                    is_necessary = self._parse_judge_output(judge_output)
                except Exception:
                    is_necessary = False
            # 不必要 → 直接丢弃
            if not is_necessary:
                decisions["drop"] += 1
                continue

            # 必要 → 尝试摘要
            summary_tokens = self._count_tokens(summary_text)
            if used_history_tokens + summary_tokens <= self.max_history_tokens:
                result_items.append(
                    self._clone_item_with_text(item, summary_text, decision="summary")
                )
                used_history_tokens += summary_tokens
                decisions["summary"] += 1
            else:
                # 摘要仍超预算 → 丢弃
                decisions["drop"] += 1

        # 追加“上一轮”原文（独立预算）
        if pre_turn_items:
            # 若存在多条（异常情况），合并为单条文本
            pre_text = "\n".join(
                [it.metadata.get("original_text") or it.text or "" for it in pre_turn_items]
            ).strip()
            # 截断到独立预算
            pre_text = self._truncate_to_budget(pre_text, self.max_pre_turn_tokens)
            used_pre_tokens = self._count_tokens(pre_text)
            # 以第一条的 metadata 为基准
            base_item = pre_turn_items[0]
            result_items.append(
                self._clone_item_with_text(
                    base_item,
                    pre_text,
                    decision="raw",
                    extra_meta={"is_last_turn": True},
                )
            )

        # 汇总元数据
        meta = {
            "action": "scm_three_way",
            "token_counter": self.token_counter,
            "max_history_tokens": self.max_history_tokens,
            "used_history_tokens": used_history_tokens,
            "max_pre_turn_tokens": self.max_pre_turn_tokens,
            "used_pre_turn_tokens": used_pre_tokens,
            "decisions": decisions,
            # LLM 调试信息
            "llm_called": llm_called,
            "llm_calls": llm_calls,
            "llm_model": llm_model,
            "llm_base_url": llm_base_url,
        }

        # 控制台简要调试输出
        try:
            print(
                f"[DEBUG SCM Three-Way] history_used={used_history_tokens}/{self.max_history_tokens} "
                f"pre_used={used_pre_tokens}/{self.max_pre_turn_tokens} decisions={decisions} "
                f"llm_called={llm_called} calls={llm_calls} model={(llm_model or '-')} base={(llm_base_url or '-')}"
            )
        except Exception:
            pass

        return PostRetrievalOutput(memory_items=result_items, metadata=meta)

    # ----------------------------------------
    # 辅助方法
    # ----------------------------------------
    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.token_counter == "char":
            return len(text)
        if self.token_counter == "word":
            return len(text.split())
        if self.token_counter == "tiktoken" and self._tokenizer is not None:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                return max(1, len(text) // 4)
        # 默认近似
        return len(text)

    def _truncate_to_budget(self, text: str, max_tokens: int) -> str:
        # 近似按字符/词/真实 token 截断
        if self.token_counter == "char":
            return text[:max_tokens]
        if self.token_counter == "word":
            words = text.split()
            return " ".join(words[:max_tokens])
        if self.token_counter == "tiktoken" and self._tokenizer is not None:
            try:
                tokens = self._tokenizer.encode(text)
                tokens = tokens[:max_tokens]
                # 无法完美 decode，做保守回退
                return text if len(tokens) >= len(text) else text[: max_tokens * 4]
            except Exception:
                return text[: max_tokens * 4]
        return text[:max_tokens]

    def _simple_summary(self, text: str) -> str:
        # 无 LLm/无预存摘要时的保守摘要：取前 30% 长度
        if not text:
            return ""
        cut = max(1, int(len(text) * 0.3))
        return text[:cut]

    def _format_judge_prompt(self, prompt: str, *, content: str, query: str) -> str:
        p = prompt
        if "{content}" in p:
            p = p.replace("{content}", content)
        if "{query}" in p:
            p = p.replace("{query}", query)
        # 兼容其它变量名
        if "{input}" in p:
            p = p.replace("{input}", content)
        return p

    def _parse_judge_output(self, text: str) -> bool:
        """解析判题输出，返回是否必要

        允许如下形式（论文风格）：
        - "[Answer]: The final answer is: (A) Yes"
        - "(B) No" 等变体
        """
        if not text:
            return False
        t = text.strip().lower()
        return "(a) yes" in t or "the final answer is: (a) yes" in t

    def _clone_item_with_text(
        self,
        item: MemoryItem,
        new_text: str,
        *,
        decision: str,
        extra_meta: Optional[dict[str, Any]] = None,
    ) -> MemoryItem:
        meta = dict(item.metadata or {})
        if extra_meta:
            meta.update(extra_meta)
        # 记录三元决策结果
        meta["scm_decision"] = decision
        return MemoryItem(
            text=new_text, score=item.score, metadata=meta, original_index=item.original_index
        )
