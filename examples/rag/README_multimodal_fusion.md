# 多模态数据融合QA示例

## 概述

`qa_multimodal_fusion.py` 演示了如何在SAGE中使用多模态数据融合功能进行问答系统。该示例展示了：

- **多模态检索**：同时处理文本和图像数据
- **融合策略**：动态切换不同的数据融合算法
- **智能QA**：结合多模态信息生成准确答案

## 功能特性

### 🎯 多模态数据融合
- 支持文本+图像联合检索
- 可配置的融合权重（文本60% + 图像40%）
- 多种融合策略：加权平均、连接、注意力机制等

### 🔍 智能检索
- 基于相似度的多模态匹配
- 结构化元数据支持
- 位置和属性信息的联合查询

### 🤖 生成式问答
- 与OpenAI GPT模型集成
- 基于检索结果的上下文增强
- 结构化答案输出

## 使用方法

### 基本运行

```bash
cd /home/shuhao/SAGE
python examples/rag/qa_multimodal_fusion.py
```

### 测试模式

```bash
SAGE_EXAMPLES_MODE=test python examples/rag/qa_multimodal_fusion.py
```

## 示例输出

```
🎯 SAGE 多模态数据融合QA演示
==================================================
此演示展示如何使用多模态数据融合功能进行问答
支持文本+图像的联合检索和智能生成

📝 发送多模态问题 [1/5]: 埃菲尔铁塔在哪里？

🔍 执行多模态检索: 埃菲尔铁塔在哪里？
   📋 查询类型识别: 地标查询: 埃菲尔铁塔
   🔗 执行多模态嵌入融合
   📊 检索到 3 个相关结果:
   1. 埃菲尔铁塔 (相似度: 0.923, 类型: landmark)
   2. 悉尼歌剧院 (相似度: 0.756, 类型: landmark)
   3. 东京塔 (相似度: 0.689, 类型: landmark)

🤖 生成答案...
埃菲尔铁塔位于法国巴黎，是巴黎的标志性建筑...
```

## 配置说明

### 融合策略配置
```python
db_config = {
    "fusion_strategy": "weighted_average",  # 融合策略
    "text_weight": 0.6,                     # 文本权重
    "image_weight": 0.4,                    # 图像权重
    "dimension": 256                        # 嵌入维度
}
```

### 支持的融合策略
- `weighted_average`: 加权平均融合
- `concatenation`: 向量连接融合
- `attention_based`: 注意力机制融合
- `tensor_fusion`: 张量融合

## 知识库数据

示例包含4个著名地标的多模态数据：
- 埃菲尔铁塔（巴黎）
- 大本钟（伦敦）
- 东京塔（东京）
- 悉尼歌剧院（悉尼）

每个条目包含：
- 文本描述
- 图像嵌入向量（模拟）
- 结构化元数据

## 扩展使用

### 添加新的融合策略
```python
# 在fusion_strategies.h中定义新策略
class CustomFusion : public FusionStrategyInterface {
    Vector fuse(const std::unordered_map<ModalityType, Vector>& embeddings,
                const FusionParams& params) override {
        // 自定义融合逻辑
    }
};
```

### 集成真实的多模态数据库
```python
# 使用实际的MultimodalSageDB
from sage.db.multimodal import MultimodalSageDB

db = MultimodalSageDB.create_text_image_db({
    "dimension": 512,
    "fusion_strategy": "attention_based"
})
```

## 依赖要求

- Python 3.8+
- NumPy
- OpenAI API密钥（用于生成）
- SAGE核心库

## 相关文件

- `packages/sage-middleware/src/sage/middleware/components/sage_db/` - C++实现
- `examples/rag/qa_multimodal_fusion.py` - Python演示
- `packages/sage-middleware/src/sage/middleware/components/sage_db/examples/multimodal_demo.cpp` - C++演示