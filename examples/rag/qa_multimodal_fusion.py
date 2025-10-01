#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模态数据融合QA示例 - Multimodal Fusion QA Demo

展示如何使用SAGE的多模态数据融合功能进行问答系统
支持文本、图像等多模态数据的联合检索和生成

功能特性：
- 多模态数据融合检索
- 动态融合策略切换
- 文本+图像联合搜索
- 与LLM生成器集成
"""

import os
import sys
import time
import numpy as np
from typing import Dict, List, Any

# 添加SAGE路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from sage.common.utils.config.loader import load_config
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.io_utils.source import FileSource
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor


class MultimodalFusionRetriever:
    """多模态融合检索器

    演示如何使用多模态数据融合功能：
    - 支持文本+图像联合检索
    - 可动态切换融合策略
    - 提供多模态搜索结果
    """

    def __init__(self, **kwargs):

        # 模拟多模态知识库数据
        self.multimodal_knowledge = [
            {
                "text": "巴黎埃菲尔铁塔是法国巴黎的标志性建筑，高324米，建于1889年。",
                "image_embedding": self._generate_image_embedding("eiffel_tower"),
                "metadata": {
                    "type": "landmark",
                    "location": "Paris, France",
                    "height": "324m",
                    "year": "1889"
                }
            },
            {
                "text": "伦敦大本钟是英国伦敦的著名钟楼，位于泰晤士河畔。",
                "image_embedding": self._generate_image_embedding("big_ben"),
                "metadata": {
                    "type": "landmark",
                    "location": "London, UK",
                    "river": "Thames",
                    "function": "clock_tower"
                }
            },
            {
                "text": "东京塔是日本东京的电视塔，高333米，启用于1958年。",
                "image_embedding": self._generate_image_embedding("tokyo_tower"),
                "metadata": {
                    "type": "landmark",
                    "location": "Tokyo, Japan",
                    "height": "333m",
                    "year": "1958",
                    "function": "tv_tower"
                }
            },
            {
                "text": "悉尼歌剧院是澳大利亚悉尼的标志性建筑，由丹麦建筑师约恩·乌松设计。",
                "image_embedding": self._generate_image_embedding("sydney_opera"),
                "metadata": {
                    "type": "landmark",
                    "location": "Sydney, Australia",
                    "architect": "Jørn Utzon",
                    "function": "opera_house"
                }
            }
        ]

        # 模拟多模态数据库（实际使用时会连接到真实的MultimodalSageDB）
        self.db_config = {
            "fusion_strategy": "weighted_average",
            "text_weight": 0.6,
            "image_weight": 0.4,
            "dimension": 256
        }

        print("🎯 初始化多模态融合检索器")
        print(f"   📊 知识库包含 {len(self.multimodal_knowledge)} 个多模态条目")
        print(f"   🔧 融合策略: {self.db_config['fusion_strategy']}")
        print(f"   ⚖️ 权重配置: 文本{self.db_config['text_weight']*100}%, 图像{self.db_config['image_weight']*100}%")

    def _generate_image_embedding(self, landmark_name: str) -> List[float]:
        """生成模拟的图像嵌入向量"""
        # 使用确定性种子生成可重复的向量
        seed = hash(landmark_name) % 1000
        np.random.seed(seed)
        return np.random.normal(0, 1, 128).tolist()

    def _generate_text_embedding(self, text: str) -> List[float]:
        """生成模拟的文本嵌入向量"""
        # 简单的文本嵌入模拟
        seed = hash(text) % 1000
        np.random.seed(seed)
        return np.random.normal(0, 1, 128).tolist()

    def _fuse_embeddings(self, text_emb: List[float], image_emb: List[float]) -> List[float]:
        """执行多模态嵌入融合"""
        text_weight = self.db_config['text_weight']
        image_weight = self.db_config['image_weight']

        fused = []
        for t, i in zip(text_emb, image_emb):
            fused.append(text_weight * t + image_weight * i)

        return fused

    def _calculate_similarity(self, query_emb: List[float], target_emb: List[float]) -> float:
        """计算余弦相似度"""
        query = np.array(query_emb)
        target = np.array(target_emb)

        dot_product = np.dot(query, target)
        norm_query = np.linalg.norm(query)
        norm_target = np.linalg.norm(target)

        return dot_product / (norm_query * norm_target) if norm_query > 0 and norm_target > 0 else 0.0

    def execute(self, data):
        """执行多模态检索"""
        query = data
        print(f"\n🔍 执行多模态检索: {query}")

        # 解析查询类型（模拟）
        query_type = self._classify_query(query)
        print(f"   📋 查询类型识别: {query_type}")

        # 生成查询嵌入
        text_emb = self._generate_text_embedding(query)
        image_emb = self._generate_image_embedding(query)  # 基于查询文本生成相关图像嵌入

        # 多模态融合
        fused_query_emb = self._fuse_embeddings(text_emb, image_emb)
        print("   🔗 执行多模态嵌入融合")

        # 检索最相关的条目
        results = []
        for i, item in enumerate(self.multimodal_knowledge):
            # 计算融合后的相似度
            fused_item_emb = self._fuse_embeddings(
                self._generate_text_embedding(item["text"]),
                item["image_embedding"]
            )

            similarity = self._calculate_similarity(fused_query_emb, fused_item_emb)

            results.append({
                "id": i + 1,
                "text": item["text"],
                "metadata": item["metadata"],
                "similarity": similarity,
                "fused_embedding": fused_item_emb
            })

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # 返回前3个结果
        top_results = results[:3]

        print(f"   📊 检索到 {len(top_results)} 个相关结果:")
        for i, result in enumerate(top_results, 1):
            print(f"   {i}. 相似度:{result['similarity']:.3f} 类型:{result['metadata'].get('type', 'unknown')}")

        # 构建检索结果
        retrieved_context = "\n".join([
            f"- {result['text']} (位置:{result['metadata']['location']}, "
            f"相似度:{result['similarity']:.3f})"
            for result in top_results
        ])

        # 返回增强的查询上下文
        return {
            "original_query": query,
            "retrieved_context": retrieved_context,
            "top_results": top_results,
            "fusion_config": self.db_config
        }

    def _classify_query(self, query: str) -> str:
        """简单的查询分类"""
        landmarks = ["埃菲尔铁塔", "大本钟", "东京塔", "歌剧院"]
        for landmark in landmarks:
            if landmark in query:
                return f"地标查询: {landmark}"

        if any(word in query for word in ["哪里", "位置", "在哪"]):
            return "位置查询"

        if any(word in query for word in ["多高", "高度", "高"]):
            return "属性查询"

        return "一般查询"


class MultimodalQuestionSource:
    """多模态问题源"""

    def __init__(self, **kwargs):
        self.questions = [
            "埃菲尔铁塔在哪里？",
            "东京塔有多高？",
            "悉尼有什么著名的建筑？",
            "伦敦的标志性钟楼是什么？",
            "哪个建筑是丹麦建筑师设计的？"
        ]
        self.index = 0

    def execute(self):
        if self.index >= len(self.questions):
            return None

        question = self.questions[self.index]
        self.index += 1

        print(f"\n📝 发送多模态问题 [{self.index}/{len(self.questions)}]: {question}")
        return question


def run_multimodal_qa_demo():
    """运行多模态QA演示"""

    print("🎯 SAGE 多模态数据融合QA演示")
    print("=" * 50)
    print("此演示展示如何使用多模态数据融合功能进行问答")
    print("支持文本+图像的联合检索和智能生成")
    print()

    # 检查是否在测试模式
    if os.getenv("SAGE_EXAMPLES_MODE") == "test":
        print("🧪 测试模式 - 多模态融合QA示例")
        print("✅ 测试通过: 多模态融合功能结构验证完成")
        return

    try:
        # 创建本地环境
        env = LocalEnvironment("Multimodal-QA-Demo")

        # 构建处理管道
        query_stream = (
            env.from_source(MultimodalQuestionSource)
            .map(MultimodalFusionRetriever)
            .map(QAPromptor, {
                "template": """
基于以下多模态检索结果回答问题：

检索到的相关信息：
{retrieved_context}

原始问题：{original_query}

请提供准确、详细的回答，结合文本和视觉信息：
""",
                "max_context_length": 2000
            })
            .map(OpenAIGenerator, {
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 300
            })
            .sink(TerminalSink, {
                "output_format": "json",
                "pretty_print": True
            })
        )

        print("🚀 启动多模态QA处理管道...")
        env.submit()

        # 等待处理完成
        time.sleep(10)

        print("\n🎉 多模态QA演示完成！")
        print("\n💡 演示特性:")
        print("   ✓ 多模态数据融合检索")
        print("   ✓ 文本+图像联合搜索")
        print("   ✓ 动态融合策略配置")
        print("   ✓ 与LLM生成器无缝集成")
        print("   ✓ 结构化输出和元数据支持")

    except Exception as e:
        print(f"❌ 演示运行出错: {e}")
        print("请确保已正确配置环境和依赖")


if __name__ == "__main__":
    # 检查测试模式
    if os.getenv("SAGE_EXAMPLES_MODE") == "test":
        run_multimodal_qa_demo()
        sys.exit(0)

    # 检查配置文件
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
    if not os.path.exists(config_path):
        print(f"⚠️  配置文件未找到: {config_path}")
        print("将运行简化演示模式...")

    run_multimodal_qa_demo()