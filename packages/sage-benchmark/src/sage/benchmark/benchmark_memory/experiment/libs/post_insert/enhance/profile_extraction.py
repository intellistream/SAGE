# -*- coding: utf-8 -*-
"""
Profile/Knowledge 提取（Profile Extraction）
在对话记忆插入后，从高热度Session中提取用户画像和知识，插入到LPM层。
使用并行LLM调用提升效率。
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

from sage.benchmark.benchmark_memory.experiment.libs.post_insert.base import BasePostInsertAction

logger = logging.getLogger(__name__)

# 用户画像提取提示词
USER_PROFILE_PROMPT = """你是一个用户画像分析专家。请根据以下对话记录，提取用户的个人信息和特征。

对话记录：
{conversation}

请以JSON格式返回用户画像：
{{
    "basic_info": {{
        "name": "用户姓名（如果提到）",
        "age": "年龄或年龄段",
        "gender": "性别",
        "location": "地理位置",
        "occupation": "职业"
    }},
    "interests": ["兴趣1", "兴趣2", "兴趣3"],
    "preferences": {{
        "communication_style": "沟通风格描述",
        "topics_of_interest": ["感兴趣的话题"],
        "values": ["价值观"]
    }},
    "personality_traits": ["性格特征1", "性格特征2"],
    "relationship_context": "与对话对象的关系背景",
    "goals_needs": ["目标或需求"],
    "confidence": 0.0-1.0
}}

只提取对话中明确提到或可推断的信息，不要编造。
"""

# 知识提取提示词
KNOWLEDGE_EXTRACTION_PROMPT = """你是一个知识提取专家。请从以下对话中提取有价值的知识信息。

对话记录：
{conversation}

请以JSON格式返回提取的知识：
{{
    "facts": [
        {{"type": "事实类型", "content": "事实内容", "confidence": 0.0-1.0}}
    ],
    "concepts": [
        {{"name": "概念名称", "definition": "定义", "context": "上下文"}}
    ],
    "relationships": [
        {{"entity1": "实体1", "relation": "关系", "entity2": "实体2"}}
    ],
    "events": [
        {{"event": "事件描述", "time": "时间", "participants": ["参与者"]}}
    ],
    "procedures": [
        {{"task": "任务名称", "steps": ["步骤1", "步骤2"]}}
    ],
    "opinions": [
        {{"topic": "话题", "opinion": "观点", "holder": "持有者"}}
    ]
}}

只提取对话中明确提到的知识，保持客观准确。
"""


class ProfileExtractionAction(BasePostInsertAction):
    """Profile和Knowledge提取动作类"""

    def _init_action(self) -> None:
        """
        初始化Profile提取动作

        从 self.config 中读取：
            - heat_threshold: Session热度阈值
            - max_workers: 并行工作线程数
            - extract_profile: 是否提取用户画像
            - extract_knowledge: 是否提取知识
            - min_conversation_length: 最小对话长度
        """
        self.heat_threshold = self.config.get("heat_threshold", 10)
        self.max_workers = self.config.get("max_workers", 3)
        self.extract_profile = self.config.get("extract_profile", True)
        self.extract_knowledge = self.config.get("extract_knowledge", True)
        self.min_conversation_length = self.config.get("min_conversation_length", 5)

        logger.info(
            f"ProfileExtractionAction initialized: heat_threshold={self.heat_threshold}, "
            f"max_workers={self.max_workers}, "
            f"extract_profile={self.extract_profile}, "
            f"extract_knowledge={self.extract_knowledge}"
        )

    def execute(
        self, memory_service: Any, llm_generator: Any, embedding_generator: Any, **kwargs
    ) -> dict[str, Any]:
        """
        执行Profile和Knowledge提取流程

        Args:
            memory_service: 记忆服务
            llm_generator: LLM生成器
            embedding_generator: 嵌入生成器
            **kwargs: 其他参数

        Returns:
            包含提取结果的字典
        """
        start_time = time.time()
        result = {
            "processed_sessions": 0,
            "extracted_profiles": 0,
            "extracted_knowledge": 0,
            "inserted_to_lpm": 0,
            "errors": [],
        }

        try:
            # 1. 查找热Session
            hot_sessions = self._find_hot_sessions(memory_service)
            logger.info(f"Found {len(hot_sessions)} hot sessions (threshold={self.heat_threshold})")

            if not hot_sessions:
                return result

            # 2. 并行提取Profile和Knowledge
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self._parallel_extract, session, memory_service, llm_generator
                    ): session
                    for session in hot_sessions
                }

                for future in as_completed(futures):
                    session = futures[future]
                    try:
                        profile, knowledge = future.result()

                        # 3. 插入到LPM
                        if profile or knowledge:
                            inserted = self._insert_to_lpm(
                                session["session_id"],
                                profile,
                                knowledge,
                                memory_service,
                                embedding_generator,
                            )

                            if inserted:
                                result["inserted_to_lpm"] += 1

                                # 4. 重置Session热度
                                self._reset_session_heat(session["session_id"], memory_service)

                        if profile:
                            result["extracted_profiles"] += 1
                        if knowledge:
                            result["extracted_knowledge"] += 1

                        result["processed_sessions"] += 1

                    except Exception as e:
                        error_msg = f"Session {session['session_id']} extraction failed: {e}"
                        logger.error(error_msg)
                        result["errors"].append(error_msg)

            execution_time = time.time() - start_time
            logger.info(
                f"ProfileExtraction completed in {execution_time:.3f}s: "
                f"processed={result['processed_sessions']}, "
                f"profiles={result['extracted_profiles']}, "
                f"knowledge={result['extracted_knowledge']}, "
                f"inserted={result['inserted_to_lpm']}"
            )

        except Exception as e:
            logger.error(f"Error in profile extraction: {e}", exc_info=True)
            result["errors"].append(str(e))

        return result

    def _find_hot_sessions(self, memory_service: Any) -> list[dict[str, Any]]:
        """查找高热度Session"""
        try:
            # 从STM获取所有Session的统计信息
            stm_stats = memory_service.get_stm_statistics()

            hot_sessions = []
            for session_id, stats in stm_stats.items():
                heat = stats.get("heat", 0)
                conversation_count = stats.get("conversation_count", 0)

                # 检查热度和对话数量
                if (
                    heat >= self.heat_threshold
                    and conversation_count >= self.min_conversation_length
                ):
                    hot_sessions.append(
                        {
                            "session_id": session_id,
                            "heat": heat,
                            "conversation_count": conversation_count,
                        }
                    )

            # 按热度降序排序
            hot_sessions.sort(key=lambda x: x["heat"], reverse=True)

            return hot_sessions

        except Exception as e:
            logger.error(f"Failed to find hot sessions: {e}")
            return []

    def _parallel_extract(
        self, session: dict[str, Any], memory_service: Any, llm_generator: Any
    ) -> tuple[Optional[dict], Optional[dict]]:
        """并行提取Profile和Knowledge"""
        session_id = session["session_id"]

        # 获取Session的所有对话
        conversation = memory_service.get_session_conversation(session_id)

        if not conversation:
            logger.warning(f"No conversation found for session {session_id}")
            return None, None

        # 格式化对话文本
        conversation_text = self._format_conversation(conversation)

        profile = None
        knowledge = None

        # 并行提取（使用线程池内的并行）
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []

            if self.extract_profile:
                futures.append(
                    executor.submit(self._extract_user_profile, conversation_text, llm_generator)
                )
            else:
                futures.append(None)

            if self.extract_knowledge:
                futures.append(
                    executor.submit(self._extract_knowledge, conversation_text, llm_generator)
                )
            else:
                futures.append(None)

            # 收集结果
            if futures[0]:
                profile = futures[0].result()
            if futures[1]:
                knowledge = futures[1].result()

        logger.info(
            f"Extracted from session {session_id}: "
            f"profile={'Yes' if profile else 'No'}, "
            f"knowledge={'Yes' if knowledge else 'No'}"
        )

        return profile, knowledge

    def _extract_user_profile(
        self, conversation: str, llm_generator: Any
    ) -> Optional[dict[str, Any]]:
        """提取用户画像"""
        try:
            prompt = USER_PROFILE_PROMPT.format(conversation=conversation)
            response = llm_generator.generate(prompt)
            profile = json.loads(response)

            # 验证置信度
            if profile.get("confidence", 0) < 0.5:
                logger.warning("Low confidence profile, skipping")
                return None

            return profile

        except Exception as e:
            logger.error(f"Failed to extract user profile: {e}")
            return None

    def _extract_knowledge(self, conversation: str, llm_generator: Any) -> Optional[dict[str, Any]]:
        """提取知识"""
        try:
            prompt = KNOWLEDGE_EXTRACTION_PROMPT.format(conversation=conversation)
            response = llm_generator.generate(prompt)
            knowledge = json.loads(response)

            # 检查是否有有效知识
            has_content = any(
                [
                    knowledge.get("facts"),
                    knowledge.get("concepts"),
                    knowledge.get("relationships"),
                    knowledge.get("events"),
                    knowledge.get("procedures"),
                    knowledge.get("opinions"),
                ]
            )

            if not has_content:
                logger.debug("No knowledge extracted")
                return None

            return knowledge

        except Exception as e:
            logger.error(f"Failed to extract knowledge: {e}")
            return None

    def _insert_to_lpm(
        self,
        session_id: str,
        profile: Optional[dict[str, Any]],
        knowledge: Optional[dict[str, Any]],
        memory_service: Any,
        embedding_generator: Any,
    ) -> bool:
        """插入Profile和Knowledge到LPM"""
        try:
            inserted_count = 0

            # 插入用户画像
            if profile:
                profile_text = json.dumps(profile, ensure_ascii=False)
                profile_embedding = embedding_generator.generate(profile_text)

                memory_service.insert_to_lpm(
                    content=profile_text,
                    embedding=profile_embedding,
                    metadata={
                        "type": "user_profile",
                        "session_id": session_id,
                        "timestamp": time.time(),
                    },
                )
                inserted_count += 1

            # 插入知识（分条插入）
            if knowledge:
                # Facts
                for fact in knowledge.get("facts", []):
                    fact_text = json.dumps(fact, ensure_ascii=False)
                    fact_embedding = embedding_generator.generate(fact_text)

                    memory_service.insert_to_lpm(
                        content=fact_text,
                        embedding=fact_embedding,
                        metadata={
                            "type": "knowledge_fact",
                            "session_id": session_id,
                            "timestamp": time.time(),
                        },
                    )
                    inserted_count += 1

                # Concepts
                for concept in knowledge.get("concepts", []):
                    concept_text = json.dumps(concept, ensure_ascii=False)
                    concept_embedding = embedding_generator.generate(concept_text)

                    memory_service.insert_to_lpm(
                        content=concept_text,
                        embedding=concept_embedding,
                        metadata={
                            "type": "knowledge_concept",
                            "session_id": session_id,
                            "timestamp": time.time(),
                        },
                    )
                    inserted_count += 1

                # 其他类型类似处理...

            logger.info(f"Inserted {inserted_count} items to LPM for session {session_id}")
            return inserted_count > 0

        except Exception as e:
            logger.error(f"Failed to insert to LPM: {e}")
            return False

    def _reset_session_heat(self, session_id: str, memory_service: Any) -> None:
        """重置Session热度"""
        try:
            memory_service.reset_session_heat(session_id)
            logger.info(f"Reset heat for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to reset session heat: {e}")

    def _format_conversation(self, conversation: list[dict[str, Any]]) -> str:
        """格式化对话记录为文本"""
        lines = []
        for dialog in conversation:
            timestamp = dialog.get("timestamp", "")
            content = dialog.get("content", "")

            if isinstance(content, list):
                for msg in content:
                    role = msg.get("role", "unknown")
                    text = msg.get("content", "")
                    lines.append(f"[{timestamp}] {role}: {text}")
            else:
                lines.append(f"[{timestamp}] {content}")

        return "\n".join(lines)
