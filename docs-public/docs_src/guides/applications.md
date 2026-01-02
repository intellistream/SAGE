# 具体应用示例（L5 层）

SAGE 的应用层（L5）由 `examples/apps/` 入口脚本和 `packages/sage-apps/` 实现组成：

- `examples/tutorials/`：按照 L1-L6 重新编排的学习目录；其中 `L5-apps/` 目前提供文档占位。
- `examples/apps/*.py`：5 个运行脚本，用于解析参数、校验依赖，并调用 `sage.apps.*` 中的真实逻辑。
- `packages/sage-apps/`：应用实现所在的包（article_monitoring、auto_scaling_chat、smart_home、video、medical_diagnosis）。

> **数据与配置**：教程示例使用就近的 `data/`、`config/` 子目录；体积较大的语料和评测素材统一收敛到
> `packages/sage-benchmark/src/sage/data/`。历史上的 `examples/data/` 目录已移除，仅剩符号链接等待清理。

## 概览

| 应用入口脚本                              | 对应包路径                     | 功能概述                             |
| ----------------------------------------- | ------------------------------ | ------------------------------------ |
| `examples/apps/run_article_monitoring.py` | `sage.apps.article_monitoring` | arXiv 论文监控、关键词+语义筛选      |
| `examples/apps/run_auto_scaling_chat.py`  | `sage.apps.auto_scaling_chat`  | 弹性扩缩容的聊天会话流量模拟         |
| `examples/apps/run_smart_home.py`         | `sage.apps.smart_home`         | 多设备协作的智能家居自动化           |
| `examples/apps/run_video_intelligence.py` | `sage.apps.video`              | 多模型视频理解（CLIP + MobileNetV3） |
| `examples/apps/run_medical_diagnosis.py`  | `sage.apps.medical_diagnosis`  | 多智能体的医疗影像分析               |

## 应用列表

所有入口脚本都包含 `@test_*` 元数据，供 `sage-dev project test` 分类识别。涉及外部资源（视频、医疗数据等）的示例默认标记为
`@test_skip_ci: true` 以避免在 CI 中阻塞。

______________________________________________________________________

### 1. 文章监控系统（Article Monitoring）

智能监控 arXiv 最新论文，通过关键词和语义过滤为用户推荐相关文献。

**特点**：

- 实时数据流处理
- 多级筛选（关键词 + 语义）
- 个性化推荐

**快速开始**：

```bash
python examples/apps/run_article_monitoring.py --keywords "streaming ai" --max-articles 20
```

**详细文档**：[文章监控系统](article-monitoring.md)

______________________________________________________________________

### 2. 分布式智能家居系统（Smart Home）

展示 SAGE 的互联互通能力，通过 IoT 设备网络实现智能家居自动化。

**特点**：

- IoT 设备协调
- 自动化工作流
- 环境感知

**快速开始**：

```bash
python examples/apps/run_smart_home.py --cycles 3 --verbose
```

**详细文档**：[智能家居系统](smart-home.md)

______________________________________________________________________

### 3. 智能扩缩容聊天系统（Auto-scaling Chat）

展示 SAGE 的高资源利用能力，通过智能扩缩容实现弹性资源管理。

**特点**：

- 自动扩缩容
- 负载均衡
- 资源监控

**快速开始**：

```bash
python examples/apps/run_auto_scaling_chat.py --duration 60 --peak-rate 80
```

**详细文档**：[自动扩缩容系统](auto-scaling-chat.md)

______________________________________________________________________

### 4. 视频智能分析（Video Intelligence）

使用 CLIP 和 MobileNetV3 进行多模型视频内容分析。

**特点**：

- 多模型推理管道
- 场景理解
- 目标检测
- 时序分析

**快速开始**：

```bash
python examples/apps/run_video_intelligence.py --video path/to/video.mp4 --max-frames 100
```

**详细文档**：参见 [sage-apps 包文档](packages/sage-apps/index.md)

______________________________________________________________________

### 5. 医疗诊断系统（Medical Diagnosis）

AI 辅助的医疗影像分析系统，使用多智能体架构。

**特点**：

- 多智能体协作
- 医疗知识库
- 诊断报告生成

**快速开始**：

```bash
python examples/apps/run_medical_diagnosis.py --case-id demo_case
```

**详细文档**：参见 [sage-apps 包文档](packages/sage-apps/index.md)

______________________________________________________________________

## 安装

安装所有应用：

```bash
pip install -e packages/sage-apps[all]
```

安装特定应用：

```bash
# 仅安装文章监控 / Auto-scaling / Smart Home（共享默认 extra）
pip install -e packages/sage-apps

# 视频智能（额外的视觉推理依赖）
pip install -e packages/sage-apps[video]

# 医疗诊断（医学影像依赖）
pip install -e packages/sage-apps[medical]
```

## 技术架构

所有应用都基于 SAGE 框架的核心组件构建：

### SAGE 算子

- **BatchFunction**: 数据源（如 arXiv API、用户流量生成器）
- **MapFunction**: 数据转换（如过滤、处理、扩缩容决策）
- **SinkFunction**: 数据输出（如结果展示、指标收集）

### 示例管道

```python
from sage.kernel.api.local_environment import LocalEnvironment

env = LocalEnvironment("app_name")

pipeline = (
    env.from_batch(SourceOperator())
       .map(FilterOperator())
       .map(ProcessOperator())
       .sink(OutputOperator())
)

env.submit(autostop=True)
```

## 运行示例

所有示例都提供了命令行接口，上文命令即可直接运行。任意入口都支持 `--help` 查看完整参数与配置说明。

## 自定义应用

基于这些示例，您可以创建自己的 SAGE 应用：

1. **创建算子**: 继承 BatchFunction, MapFunction, SinkFunction
1. **构建管道**: 使用 SAGE Environment API
1. **运行测试**: 使用本地或分布式环境
1. **部署**: 集成到生产系统

参考示例代码：`packages/sage-apps/src/sage/apps/`

## 贡献

我们欢迎社区贡献新的应用示例！请参考：

- [贡献指南](../community/community.md)
- [开发文档](../developers/ci-cd.md)
- [包结构](../concepts/architecture/package-structure.md)

## 下一步

- 深入了解每个应用的详细文档（点击上方链接）
- 查看 [API 参考](../api-reference/index.md)
- 探索教程（查看导航栏教程章节）
- 加入 [社区讨论](../community/community.md)
