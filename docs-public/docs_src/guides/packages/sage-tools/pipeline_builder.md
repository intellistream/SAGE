- **知识库构建**：命令会在首次运行时扫描本地仓库并构建轻量级向量索引（内存缓存），无需额外安装 SageDB。若本地缺乏源码（如 `pip install isage` 场景），会自动从官方
  `SAGE-Pub` 仓库下载 `docs_src` 压缩包并缓存于 `~/.sage/cache/pipeline-builder/docs`。

# Pipeline Builder

`sage pipeline build` 通过与大语言模型（LLM）的多轮对话，快速生成可运行的 SAGE Pipeline 配置文件。v2
版本会在提示词中注入来自项目示例、组件目录以及自动检索到的知识片段，帮助模型了解可复用的 Source/Stage/Sink 组合，省去了用户查阅 API 文档的负担。

## 功能要点

- **自动上下文加载**：命令会解析 `examples/config/*.yaml` 中的示例 pipeline，并生成组件速查表提供给 LLM。
- **RAG 检索增强**：默认启用轻量级知识库，自动从 `docs-public/docs_src`、`examples/config`、`packages/sage-libs`
  等目录中检索与需求最相关的片段作为提示补充。
- **多轮优化**：交互过程中可以输入修改意见，LLM 会在上一轮基础上改写配置。
- **非交互模式**：通过 `--non-interactive` 结合 `--name` 与 `--goal`，一次性生成并输出配置。

## 快速开始

```bash
sage pipeline build --backend mock --name "QA Helper" --goal "构建一个问答流程"
```

Mock 后端无需真实 LLM 服务，可用于离线体验。当改用 OpenAI 兼容后端时，可指定：

```bash
sage pipeline build --backend openai --model qwen-max --api-key $OPENAI_API_KEY
```

### 运行生成的 Pipeline

构建完成后，可直接使用 `sage pipeline run` 命令加载 YAML 并提交到本地 JobManager：

```bash
sage pipeline run .sage/output/pipelines/qa-helper.yaml
```

- 默认会阻塞直到批处理任务结束（可通过 `--no-autostop` 关闭）。
- 若配置的 `pipeline.type` 为 `remote`，可配合 `--host`、`--port` 指定 JobManager 地址。
- 命令会自动解析 `services`、`stages`、`sink` 并完成动态导入。运行前请确保相关组件可在当前 Python 环境中导入。

## 重要选项

| 选项                  | 说明                                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| `--context-limit`     | 控制注入提示词的示例 pipeline 数量（默认 4）。                                                        |
| `--context-file/-c`   | 追加自定义上下文文件，内容将直接合并进提示。                                                          |
| `--show-contexts`     | 打印静态上下文（示例 + 自定义），便于调试。                                                           |
| `--knowledge-top-k`   | 检索知识库时返回的片段数量（默认 5）。                                                                |
| `--no-knowledge`      | 禁用知识库检索，只使用静态上下文。                                                                    |
| `--show-knowledge`    | 打印当前检索命中的知识片段。                                                                          |
| 环境变量              | `SAGE_PIPELINE_DOWNLOAD_DOCS=0` 可关闭自动下载；`SAGE_PIPELINE_DOCS_URL` 可指定自定义文档压缩包地址。 |
| `--requirements-path` | 从 JSON 文件读取需求输入，跳过交互式问答。                                                            |
| `--output`            | 指定生成的 YAML 文件路径或目录。                                                                      |
| `--overwrite`         | 允许覆盖已有文件。                                                                                    |

## 配置输出

生成的 YAML 会包含以下字段：

- `pipeline`: 基本元信息（名称、描述、版本、类型）。
- `source`: 数据源组件。
- `stages`: 顺序执行的算子列表，包含 `id`、`kind`、`class`、`params` 与 `summary`。
- `sink`: 输出组件。
- `services` / `monitors`: 运行依赖的扩展服务与监控器（可选）。
- `notes`: 备注信息。

## 常见问题

- **提示词过长**：调低 `--context-limit` 或 `--knowledge-top-k`，必要时禁用知识库检索。
- **组件未找到**：模型输出的类名需在本地 SAGE 环境中可导入。若缺少，可在反馈中要求替换为已存在的组件，并确保知识库已更新（可重新运行 `--no-knowledge` 以验证基线行为）。
- **生成失败**：确认 LLM 服务可用；若返回 JSON 解析错误，可通过反馈重新请求。|
