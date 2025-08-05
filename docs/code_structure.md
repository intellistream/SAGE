# SAGE 项目最终代码结构

> 本文档描述了经过讨论与微调后的 **SAGE** 项目目录与模块组织方案，遵循 Apache Flink 的分层思想，同时确保“开箱即用”。
>
> * **核心 (core)**：包含接口、调度运行时，以及最小可执行 **基础算子**（Source/Sink/Map）。
> * **扩展 (sage\_lib)**：承载非必需但常用的高级/领域算子和函数，实现与核心解耦。
> * **应用 (app)**：用户自己的管道与自定义函数。
> * **辅助 (tests / docs / examples / config / data)**：测试、文档、示例、配置与数据。

---

## 1. 顶层目录概览

```text
SAGE-Project/
├── sage/                     # 核心库包（接口 + 运行时 + 基础算子）
│   ├── api/                  # 对外 API 抽象（Function / Operator / Environment 等）
│   │   ├── execution/
│   │   ├── function/
│   │   ├── operator/
│   │   ├── memory/
│   │   ├── model/
│   │   └── query/
│   ├── core/                 # 运行时与内部实现
│   │   ├── compiler/
│   │   ├── dag/
│   │   ├── runtime/
│   │   ├── memory/
│   │   ├── model/
│   │   ├── io/
│   │   └── operators/        # **基础内置算子**（框架必备，保持最小集）
│   │       ├── operator_base.py  # Operator 抽象基类（框架级）
│   │       ├── source_operator.py
│   │       ├── sink_operator.py
│   │       ├── map_operator.py
│   │       └── __init__.py
│   ├── utils/
│   └── __init__.py
├── sage_lib/                 # 可选扩展库（高级/领域算子 & 函数）
│   ├── functions/
│   │   ├── stream/
│   │   ├── io/
│   │   ├── rag/
│   │   └── __init__.py
│   ├── operators/            # **高级/领域算子实现**（窗口、连接、RAG Chain 等）
│   │   ├── window_operator.py
│   │   ├── join_operator.py
│   │   ├── rag_chain_operator.py
│   │   └── __init__.py
│   └── __init__.py
├── app/                      # 用户代码区
│   ├── example/
│   │   └── qa_pipeline_flink.py
│   ├── user_functions/
│   └── __init__.py
├── tests/                    # 单元 & 集成测试
│   ├── core/
│   ├── api/
│   ├── sage_lib/
│   └── integration/
├── docs/                     # 项目文档
│   ├── final_code_structure.md  # ← 当前文件
│   ├── usage_guide.md
│   └── development_guide.md
├── examples/                 # 可运行示例程序
├── config/                   # 默认配置 & 环境变量
├── data/                     # 示例数据集
├── setup.py / pyproject.toml # 打包 & 依赖声明
├── requirements.txt
├── Dockerfile                # 容器化部署脚本
├── README.md
└── LICENSE
```

### 目录层级要点

| 层级                          | 主要职责       | 说明                                                                                      |
| --------------------------- | ---------- | --------------------------------------------------------------------------------------- |
| **sage.api**                | 抽象接口层      | 暴露稳定 API；无任何执行逻辑。                                                                       |
| **sage.core**               | 运行时 & 基础算子 | 包含编译器、DAG、调度器以及 **Source / Sink / Map** 三类最小必备算子。确保 `pip install sage` 后即可跑简单 Environment。 |
| **sage\_lib**               | 扩展组件       | 内置但可剥离的高级 Function / Operator；与业务耦合度较高，按需安装/引用。                                         |
| **app**                     | 用户项目区      | 托管用户自定义逻辑与管道脚本；与框架仓库分离，易于升级框架。                                                          |
| **tests & docs & examples** | 工程最佳实践     | 按工业惯例组织测试、文档与示例，保证可维护性。                                                                 |

---

## 2. Operator 分层设计

```mermaid
flowchart TD
    subgraph Core("sage.core")
        direction TB
        OB["operator_base.py\n(BaseOperator)"]
        OPS["operators/\nSource/Sink/Map"]
    end

    subgraph SageLib("sage_lib")
        direction TB
        O2["operators/\nWindow/Join/RAGChain"]
    end

    OB --> OPS
    OB -. extends .-> O2
```

* **BaseOperator**：核心框架级抽象，位于 `sage.core.operator_base`，声明生命周期方法 (`open/close`)、数据处理钩子 (`process_element`)、并行度等元信息。
* **核心算子** (`SourceOperator` / `SinkOperator` / `MapOperator`)：满足最小运行闭包，保证核心包安装即能跑；放在 `sage.core.operators`，依赖 runtime，但被 runtime 调用。
* **扩展算子**：如窗口、连接、RAG 专用链路算子等，位于 `sage_lib.operators`。它们同样继承 `BaseOperator`，但不被 core 引用，避免核心膨胀。

> 该分层等价于 Flink 将基础流算子放在 `flink-streaming-java`（依赖 runtime），而 runtime 对它们零依赖；只是在本项目中为方便使用，把“最小三算子”内收进 core。

---

## 3. 打包与依赖

* **核心依赖**：在 `install_requires` 中列出（PyYAML、Click、typing-extensions、ray 等）。
* **可选依赖**：`extras_require` 中声明，例如：

  * `rag`: 依赖 `sentence-transformers`, `openai`, `faiss-cpu` 等；
  * `window`: 依赖可能的高速滑动窗口库等。

用户可按需 `pip install sage[rag]` 来获得扩展算子与函数。

---

## 4. 部署与文档

* **Docker 支持**：仓库根目录提供 `Dockerfile`，默认安装核心包与示例依赖，可通过构建参数开启 extras。
* **文档构建**：推荐使用 **MkDocs + Material** 主题，配置放在 `mkdocs.yml`；CI 生成站点发布到 GitHub Pages。
* **CI/CD**：

  1. **pytest** 运行单元测试；
  2. **ruff / black** 进行静态检查；
  3. **build** 阶段生成 wheel 并上传 PyPI；
  4. **docker** 阶段构建并推送镜像至 registry。

---

## 5. 迁移与后续工作

1. **代码搬迁**

   * 将原 `sage/api/function`、`sage/api/operator` 的接口保留至 `sage/api/*`，删除实现细节。
   * 将原算子实现迁往:

     * 基础算子 ➜ `sage/core/operators`。
     * 其他算子 ➜ `sage_lib/operators`。
   * 将 Function 实现迁往 `sage_lib/functions`（保持原分类）。
2. **重构引用**

   * 修改核心 runtime/编译器引用的新路径。
   * 引入 `BaseOperator` 路径变更。
3. **完善测试**

   * `tests/core`：确保基础算子在 local/runtime 流程中可运行。
   * `tests/sage_lib`：使用 pytest 的 `mark.optional` 跳过未安装 extras 时的扩展测试。
4. **更新文档 & 示例**

   * README 给出最小示例（使用核心 Source/Map/Sink）。
   * examples 须同步新包路径。