# 腰椎MRI医疗诊断Agent

基于SAGE框架构建的医疗诊断智能助手，专注于腰椎MRI影像分析和诊断报告生成。

## 📋 功能特性

### 1. 多模态数据处理
- **影像分析**: 处理T2加权矢状位MRI图像
- **报告解析**: 提取医疗报告中的关键信息
- **知识库构建**: 构建疾病-影像-诊断知识图谱

### 2. 智能诊断流程
- **影像特征提取**: 自动识别椎体和椎间盘区域
- **病变检测**: 检测退行性变化、椎间盘突出等
- **诊断建议生成**: 基于影像和病史生成诊断报告
- **相似病例检索**: 检索相似病例辅助诊断

### 3. RAG增强诊断
- **医学知识库**: 腰椎疾病诊断标准和治疗指南
- **病例库**: 历史病例和诊断报告
- **混合检索**: 结合影像相似度和文本语义检索

## 🏗️ 系统架构

```
medical_diagnosis/
├── agents/                    # Agent定义
│   ├── diagnostic_agent.py   # 主诊断Agent
│   ├── image_analyzer.py     # 影像分析Agent
│   └── report_generator.py   # 报告生成Agent
├── config/                    # 配置文件
│   ├── agent_config.yaml     # Agent配置
│   ├── pipeline_config.yaml  # Pipeline配置
│   └── model_config.yaml     # 模型配置
├── tools/                     # 工具函数
│   ├── image_processor.py    # 图像预处理
│   ├── feature_extractor.py  # 特征提取
│   └── knowledge_base.py     # 知识库管理
├── pipelines/                 # Pipeline定义
│   ├── indexing_pipeline.py  # 数据索引Pipeline
│   └── diagnosis_pipeline.py # 诊断Pipeline
└── run_diagnosis.py          # 主运行脚本
```

## 🚀 快速开始

### 1. 自动设置数据集（推荐）

运行自动设置脚本，它会：
- 检查并安装依赖
- 自动下载腰椎MRI数据集
- 预处理数据并生成训练/测试集
- 验证数据完整性

```bash
cd examples/medical_diagnosis
./setup_data.sh
```

### 2. 手动设置数据集（可选）

如果你想手动控制每个步骤：

```bash
# 2.1 下载数据集
python scripts/download_lumbar_dataset.py

# 2.2 预处理数据
python examples/medical_diagnosis/scripts/prepare_data.py

# 2.3 探索数据集
python examples/medical_diagnosis/scripts/explore_dataset.py
```

### 3. 运行诊断测试

```bash
# 单病例诊断测试
python examples/medical_diagnosis/test_diagnosis.py --mode single

# 批量诊断测试
python examples/medical_diagnosis/test_diagnosis.py --mode batch
```

### 4. 使用诊断应用

```bash
# 单病例诊断
python examples/medical_diagnosis/run_diagnosis.py \
  --image path/to/mri.jpg \
  --age 45 \
  --gender 男 \
  --symptoms "腰痛伴下肢放射痛"

# 批量诊断
python examples/medical_diagnosis/run_diagnosis.py \
  --batch data/test_cases/ \
  --output results/

# 交互式模式
python examples/medical_diagnosis/run_diagnosis.py --interactive
```

## 📊 数据集信息

**数据集**: UniDataPro/lumbar-spine-mri

**内容**:
- 腰椎MRI影像（T2加权矢状位）
- 医疗诊断报告
- 疾病标注（退行性病变、椎间盘突出等）

**应用场景**:
- 腰椎退行性疾病诊断
- 椎间盘突出检测
- 脊柱管狭窄评估

## 🔧 技术栈

- **SAGE框架**: 底层Pipeline和Agent框架
- **多模态Embedding**: 图像+文本联合嵌入
- **VLLMService**: 高性能LLM推理
- **SageDB**: 向量数据库（存储影像特征和病例）
- **Vision-Language Model**: 医疗影像理解模型

## 📖 使用示例

### 交互式诊断
```python
from medical_diagnosis.agents.diagnostic_agent import DiagnosticAgent

# 初始化诊断Agent
agent = DiagnosticAgent(config_path="config/agent_config.yaml")

# 提交诊断请求
result = agent.diagnose(
    image_path="data/test/mri_001.dcm",
    patient_info={
        "age": 45,
        "gender": "male",
        "symptoms": "下背部疼痛，左腿麻木"
    }
)

print(result.diagnosis_report)
print(result.similar_cases)
```

### Pipeline批量处理
```python
from medical_diagnosis.pipelines.diagnosis_pipeline import DiagnosisPipeline

# 批量处理多个病例
pipeline = DiagnosisPipeline()
results = pipeline.batch_process(
    image_dir="data/medical/batch_cases/",
    output_dir="output/diagnoses/"
)
```

## 🎯 核心能力

### 1. 影像分析
- 椎体分割和识别（L1-L5）
- 椎间盘定位（L1/L2 - L5/S1）
- 病变区域检测
- 影像质量评估

### 2. 诊断推理
- 基于影像特征的初步诊断
- 结合病史和症状的综合分析
- 检索相似病例辅助决策
- 多Agent协作诊断

### 3. 报告生成
- 结构化诊断报告
- 影像描述和发现
- 诊断结论和建议
- 治疗方案推荐

## ⚠️ 免责声明

**本系统仅用于学习和研究目的，不能替代专业医生的诊断。**

所有诊断结果需要经过专业医师审核和确认。本系统不承担任何医疗责任。

## 📝 许可证

遵循SAGE项目许可证。

## 🤝 贡献

欢迎提交问题和改进建议！
