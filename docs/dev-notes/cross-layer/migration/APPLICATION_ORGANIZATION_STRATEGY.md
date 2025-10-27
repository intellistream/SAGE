# SAGE应用组织策略

**Date**: 2024-09-28  
**Author**: SAGE Team  
**Summary**: 应用组织策略

---


## 背景

随着SAGE生态的发展,我们需要明确区分不同类型的代码:
- **Examples**: 教学示例和快速演示
- **Applications**: 完整的、生产就绪的应用
- **Templates**: 可复用的应用模板

## 分层组织策略

### Tier 1: Simple Examples (教学示例)
**位置**: `examples/`
**特点**:
- 单文件或简单目录结构
- 主要用于教学和文档
- 快速运行(<5分钟)
- 最少依赖

**示例**:
```
examples/
├── tutorials/
│   └── hello_world.py          # 单文件,30行代码
├── rag/
│   └── simple_rag.py           # 基础RAG,<100行
└── agents/
    └── basic_agent.py          # 简单Agent
```

### Tier 2: Complex Applications (完整应用)
**位置**: `packages/sage-libs/src/sage/libs/applications/`
**特点**:
- 多文件架构(Agents, Tools, Pipelines)
- 生产就绪代码
- 完整的测试和文档
- 独立安装: `pip install sage-libs[medical]`

**示例**:
```python
packages/sage-libs/src/sage/libs/applications/
├── __init__.py
├── medical_diagnosis/      # 你的医疗诊断应用
│   ├── __init__.py
│   ├── agents/
│   │   ├── diagnostic_agent.py
│   │   ├── image_analyzer.py
│   │   └── report_generator.py
│   ├── tools/
│   │   └── knowledge_base.py
│   ├── config/
│   │   └── agent_config.yaml
│   ├── data/               # gitignored
│   ├── scripts/
│   │   ├── setup_data.sh
│   │   ├── download_dataset.py
│   │   └── prepare_data.py
│   ├── tests/
│   │   └── test_diagnosis.py
│   ├── README.md
│   ├── requirements.txt
│   └── pyproject.toml      # 可选,如果需要独立发布
├── financial_analysis/     # 未来的金融分析应用
└── legal_assistant/        # 未来的法律助手应用
```

### Tier 3: Application Templates (应用模板)
**位置**: `packages/sage-tools/src/sage/tools/templates/`
**特点**:
- 可通过CLI工具使用
- 提供scaffolding功能
- 用于快速启动新应用

**使用方式**:
```bash
sage-tools create-app --template medical-diagnosis --name my-diagnosis-app
```

## 安装和使用

### 安装特定应用
```bash
# 安装医疗诊断应用
pip install sage-libs[medical]

# 或安装所有应用
pip install sage-libs[all-apps]
```

### 代码中使用
```python
# 从applications导入
from sage.libs.applications.medical_diagnosis import DiagnosticAgent

# 配置和运行
agent = DiagnosticAgent(config_path="config.yaml")
result = agent.diagnose(image_path="mri.jpg")
```

### 作为独立脚本运行
```bash
# 如果应用足够复杂,可以提供CLI入口
sage-medical-diagnosis --image mri.jpg --config config.yaml
```

## 判断标准

**什么时候放在 `examples/`?**
- ✅ 代码量 < 200行
- ✅ 单一文件或2-3个文件
- ✅ 主要用于教学
- ✅ 运行时间 < 5分钟
- ✅ 没有复杂的数据准备流程

**什么时候放在 `sage-libs/applications/`?**
- ✅ 代码量 > 200行
- ✅ 多文件架构(>5个文件)
- ✅ 生产就绪的质量
- ✅ 需要数据下载/预处理
- ✅ 有完整的测试覆盖
- ✅ 希望作为可安装包发布

**什么时候独立仓库?**
- ✅ 应用非常大(>10k行代码)
- ✅ 有独立的团队维护
- ✅ 有特殊的依赖冲突
- ✅ 需要独立的发布周期

## 医疗诊断应用的建议

你的医疗诊断应用应该:
1. **从 `examples/` 移动到 `packages/sage-libs/src/sage/libs/applications/medical_diagnosis/`**
2. **理由**:
   - 代码结构复杂(Agents, Tools, Scripts)
   - 需要数据下载和预处理
   - 生产级质量的代码
   - 有完整的文档和测试

## 迁移步骤

### 1. 创建新的应用目录
```bash
mkdir -p packages/sage-libs/src/sage/libs/applications/medical_diagnosis
```

### 2. 移动代码
```bash
mv examples/medical_diagnosis/* \
   packages/sage-libs/src/sage/libs/applications/medical_diagnosis/
```

### 3. 更新 pyproject.toml
```toml
# packages/sage-libs/pyproject.toml
[project.optional-dependencies]
medical = [
    "huggingface_hub>=0.19.0",
    "datasets>=2.14.0",
    "pillow>=10.0.0",
    "scikit-learn>=1.3.0",
]

all-apps = [
    "sage-libs[medical]",
    # 未来的其他应用
]
```

### 4. 在 examples/ 保留一个快速入口
```python
# examples/medical_diagnosis/quick_start.py
"""
医疗诊断应用快速入门

完整应用请参考: sage.libs.applications.medical_diagnosis
或访问: https://github.com/intellistream/SAGE/tree/main/packages/sage-libs/src/sage/libs/applications/medical_diagnosis
"""

from sage.libs.applications.medical_diagnosis import DiagnosticAgent

def quick_demo():
    """5分钟快速演示"""
    agent = DiagnosticAgent()

    # 使用模拟数据演示
    result = agent.diagnose(
        image_path="demo.jpg",  # 使用预置的demo数据
        patient_info={"age": 45, "gender": "male"}
    )

    print(result.report)

if __name__ == "__main__":
    quick_demo()
```

## 参考案例

### LangChain
- Examples: `cookbook/` (notebooks)
- Templates: `templates/`
- Apps: 独立仓库 + langchain-ai org

### HuggingFace Transformers  
- Examples: `examples/pytorch/` (按任务分类)
- Models: `src/transformers/models/` (核心代码)
- Applications: Hub上的Spaces

### SAGE (当前)
- Examples: `examples/` (简单示例)
- Libraries: `packages/sage-libs/` ✅ (应该放复杂应用的地方)
- Tools: `packages/sage-tools/` (开发工具和模板)

## 总结

**核心原则**:
1. **Simple → examples/**
2. **Complex → sage-libs/applications/**  
3. **Template → sage-tools/templates/**
4. **Mega-project → 独立仓库**

**医疗诊断应用建议**: 移动到 `sage-libs/applications/` ✅
