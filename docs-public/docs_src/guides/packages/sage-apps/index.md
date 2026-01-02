# sage-apps

Application layer packages showcasing SAGE's end-to-end capabilities.

**Layer**: L5 (Applications)

## Overview

`packages/sage-apps/src/sage/apps/` currently包含以下五个应用模块，每个模块都对应 `examples/apps/` 下的一个运行脚本：

| Application        | Module                         | Launcher                                  | Focus                     |
| ------------------ | ------------------------------ | ----------------------------------------- | ------------------------- |
| Article Monitoring | `sage.apps.article_monitoring` | `examples/apps/run_article_monitoring.py` | arXiv 数据摄取 + 多级筛选 |
| Auto-scaling Chat  | `sage.apps.auto_scaling_chat`  | `examples/apps/run_auto_scaling_chat.py`  | 弹性扩缩容策略演示        |
| Smart Home         | `sage.apps.smart_home`         | `examples/apps/run_smart_home.py`         | IoT 协同与事件驱动工作流  |
| Video Intelligence | `sage.apps.video`              | `examples/apps/run_video_intelligence.py` | 多模型视频理解            |
| Medical Diagnosis  | `sage.apps.medical_diagnosis`  | `examples/apps/run_medical_diagnosis.py`  | 多智能体医疗影像分析      |

每个模块都提供：

1. **Python API**（`run_*` 帮助函数/类）
1. **命令行入口**（`python -m sage.apps.<module>.pipeline`）
1. **示例脚本**（`examples/apps/run_*.py` 带参数解析与测试标记）

## 应用详情

### Article Monitoring

智能论文监控系统，持续从 arXiv 抓取文献并通过关键词 + 语义双重过滤输出推荐列表。

- **关键特性**：实时拉取、KeywordFilter + SemanticFilter、个性化排序、纯标准库依赖
- **代码位置**：`packages/sage-apps/src/sage/apps/article_monitoring/`
- **快速开始**：

```python
from sage.apps.article_monitoring import run_article_monitoring_pipeline

run_article_monitoring_pipeline(
    keywords=["machine learning", "deep learning"],
    interest_topics=["streaming ai"],
    category="cs.AI",
    max_articles=20,
)
```

CLI：`python -m sage.apps.article_monitoring.pipeline --keywords "transformer,attention"`

### Auto-scaling Chat

弹性扩缩容聊天系统，演示可配置的负载模式、自动扩缩容策略以及实时指标。

- **关键特性**：TrafficSource、AutoScaler、LoadBalancer 链式算子；ScalingEventsSink 输出；自定义阈值
- **代码位置**：`packages/sage-apps/src/sage/apps/auto_scaling_chat/`
- **快速开始**：

```python
from sage.apps.auto_scaling_chat import run_auto_scaling_demo

run_auto_scaling_demo(duration=60, base_rate=5, peak_rate=80, verbose=True)
```

CLI：`python -m sage.apps.auto_scaling_chat.pipeline --duration 60 --peak-rate 80`

### Smart Home

面向 IoT 的智能家居自动化工作流，协调机器人、传感器和家电完成洗衣等任务。

- **关键特性**：DeviceExecutor + EnvironmentMonitor 组合、工作流/事件日志双 sink、可自定义 cycles
- **代码位置**：`packages/sage-apps/src/sage/apps/smart_home/`
- **快速开始**：

```python
from sage.apps.smart_home import run_smart_home_demo

run_smart_home_demo(num_cycles=2, verbose=True)
```

CLI：`python -m sage.apps.smart_home.pipeline --cycles 3 --verbose`

### Video Intelligence

多模型视频理解管道，结合 CLIP、MobileNetV3 等模型进行帧级分析与事件检测。

- **关键特性**：帧抽取、感知/分析算子、可配置 sink 输出
- **代码位置**：`packages/sage-apps/src/sage/apps/video/`
- **快速开始**：

```python
from sage.kernel.api import LocalStreamEnvironment
from sage.apps.video import VideoIntelligencePipeline

env = LocalStreamEnvironment("video_analysis")
pipeline = VideoIntelligencePipeline(env)
pipeline.process("input.mp4")
```

### Medical Diagnosis

多智能体医疗影像分析系统，包括影像解析、知识库查询与报告生成。

- **关键特性**：DiagnosticAgent、ImageAnalyzer、ReportGenerator、可扩展知识库
- **代码位置**：`packages/sage-apps/src/sage/apps/medical_diagnosis/`
- **快速开始**：

```python
from sage.apps.medical_diagnosis import DiagnosticAgent

agent = DiagnosticAgent(config_path="config/agent_config.yaml")
result = agent.diagnose(image_path="data/case_001.npy", patient_info={"age": 45})
print(result.report)
```

## Launcher 脚本

所有应用都提供 `examples/apps/run_*.py` 入口，便于快速体验并带有 `@test_*` 元数据：

```bash
python examples/apps/run_article_monitoring.py --help
python examples/apps/run_auto_scaling_chat.py --duration 60 --peak-rate 80
python examples/apps/run_smart_home.py --cycles 2 --verbose
python examples/apps/run_video_intelligence.py --video sample.mp4
python examples/apps/run_medical_diagnosis.py --case-id demo_case
```

## 安装与测试

```bash
# 安装默认依赖（文章监控/Auto-scaling/Smart Home）
pip install -e packages/sage-apps

# 视频/医疗需要额外依赖
pip install -e packages/sage-apps[video]
pip install -e packages/sage-apps[medical]

# 运行全部测试
cd packages/sage-apps && pytest tests/ -v
```

## 开发指南

1. 在 `packages/sage-apps/src/sage/apps/<new_app>/` 创建模块（含 README、operators、pipeline 等）。
1. 提供 Python API + CLI + `examples/apps/run_<new_app>.py` 入口。
1. 在 `docs/dev-notes/l5-apps/README.md` 和 `docs-public` 中更新说明。
1. 添加对应测试：`packages/sage-apps/tests/<new_app>/`。

## 参考

- [Package Architecture](../../../concepts/architecture/package-structure.md)
- [Applications Guide](../../applications.md)
- [贡献指南](../../../community/community.md)
