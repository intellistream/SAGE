# SAGE 项目人员分配

> 最后更新：2026-01-04

## 分配原则

- **SAGE 主项目**：数据流处理系统框架（国家优青项目）
- **sageLLM 项目**：推理引擎方向（科技部重大专项）
- **NeuroMem 项目**：类脑记忆系统（教育部先导项目）
- **每人最多出现在两处**：可同时参与一个主项目 + 一个子项目

## SAGE 主项目（按 package/submodule 归属）

> **资助信息**：国家自然科学基金优秀青年科学基金项目

| 姓名        | SAGE 归属 package/submodule                            | 备注                                    |
| ----------- | ------------------------------------------------------ | --------------------------------------- |
| 王子澳      | `sage-middleware` → `sageFlow`（向量流）               | 24 届硕士，申请 2026 国家面上基金       |
| 朱鑫材      | `sage-middleware` → `sageFlow`（向量流）               | 25 届硕士，申请 2026 国家面上基金       |
| 陈德斌      | `sage-middleware` → `sageTSDB`（时序数据库）           | 26 届硕士，湖北省科技厅重大项目（达梦） |
| 高鸿儒      | `sage-libs` → `anns`（Graph-based ANNS 内存访问优化）  | 20 届博士                               |
| Xinyi Li    | `sage-benchmark` → 大模型记忆细粒度基准（数据集/评测） |                                         |
| Yutong Zhou | `sage-libs` → 时序敏感 RAG                             |                                         |
| Yuyue Guo   | `sage-libs` → 智能体工具规划                           |                                         |

> **说明**：
>
> - 上述同学如同时参与 sageLLM/NeuroMem 项目，请在对应表中补充
> - 其余未列入的成员/贡献者，默认归属 SAGE 主项目，按 issue/PR 协作

## sageLLM 项目（推理引擎方向）

> **注意**：sageLLM 已独立为私有仓库 `intellistream/sageLLM`
>
> **资助信息**：科技部重大专项项目
>
> 详细任务分配和进度请查看：`sageLLM/docs/TEAM_ASSIGNMENT.md`

| 姓名     | sageLLM 任务                           | 备注                  |
| -------- | -------------------------------------- | --------------------- |
| 程序员 A | Task0 协作 + Task1 通信层（1.1-1.5）   | 全职（Q1 入职，3 年） |
| 程序员 B | Task0 协作 + Task2/Task3 调度与加速层  | 全职（Q1 入职，3 年） |
| 王明琪   | 2.1 前缀复用                           | 25 届硕士             |
| 高西岭   | 2.1 前缀复用（协作）                   | 26 届硕士             |
| 刘沛林   | 2.2 KV 池化与分层                      | 26 届硕士             |
| 陈彦博   | 2.2 KV 池化与分层（协作：KV 压缩路径） | 25 届硕士             |
| 张睿诚   | 2.3 淘汰策略                           | 24 届硕士             |
| 徐天翊   | 2.5 生命周期预测                       | 26 届硕士             |
| 张澹潇   | 3.2 稀疏化                             | 26 届硕士             |
| 杨锦昀   | 1.4 计算通信重叠                       | 24 届硕士             |
| 刘俊     | 2.4 调度 IR                            | 25 届博士             |
| 张森磊   | 3.3 投机解码                           | 25 届硕士             |
| 李昶吾   | 3.5 CoT 加速                           | 25 届博士             |

## NeuroMem 项目（类脑记忆系统）

> **资助信息**：
>
> - 教育部先导项目
> - 华为盘古横向合作项目
>
> **项目简介**：NeuroMem 是受大脑记忆机制启发的智能记忆系统，已独立为 PyPI 包 `isage-neuromem`

| 姓名   | NeuroMem 任务 | 备注      |
| ------ | ------------- | --------- |
| 张睿诚 | 核心架构      | 24 届硕士 |
| 徐天翊 | 存储优化      | 26 届硕士 |
| 张澹潇 | 检索算法      | 26 届硕士 |

> **说明**：上述成员同时参与 sageLLM 项目，具体任务分配见 sageLLM 表

## 独立项目状态

### 已独立的公开仓库

- ✅ **sage-benchmark**：`intellistream/sage-benchmark`（评测框架，PyPI: `isage-benchmark`）
- ✅ **sage-pypi-publisher**：`intellistream/sage-pypi-publisher`（PyPI 发布工具）
- ✅ **sageDB**：`intellistream/sageDB`（向量数据库，PyPI: `isagedb`）
- ✅ **sageFlow**：`intellistream/sageFlow`（向量流处理引擎，PyPI: `isage-flow`） - **申请 2026 国家面上基金（王子澳、朱鑫材）**
- ✅ **sageRefiner**：`intellistream/sageRefiner`（RAG 上下文压缩，PyPI: `isage-refiner`）
- ✅ **sageTSDB**：`intellistream/sageTSDB`（时序数据库，PyPI: `isage-tsdb`） - **湖北省科技厅重大项目（达梦牵头，陈德斌参与）**
- ✅ **NeuroMem**：`intellistream/NeuroMem`（类脑记忆系统，PyPI: `isage-neuromem`） - **教育部先导项目 + 华为盘古横向合作**

### 已独立的私有仓库

- ✅ **sageLLM**：`intellistream/sageLLM`（推理引擎） - **科技部重大专项项目**

### 保留在 SAGE 主项目的组件

> **资助信息**：国家自然科学基金优秀青年科学基金项目

- `sage-common`（L1 基础）
- `sage-llm-core`（L1 控制面与客户端，不包括 sageLLM 引擎）
- `sage-platform`（L2 平台）
- `sage-kernel`（L3 核心）
- `sage-libs`（L3 算法库）
- `sage-middleware`（L4 中间件，通过 PyPI 依赖上述独立组件）
- `sage-apps`（L5 应用）
- `sage-gateway`、`sage-llm-gateway`、`sage-edge`（L6 接口）
- `sage-cli`、`sage-studio`、`sage-tools`（L6 工具）

## 福利政策

### sageLLM 项目成员额外补贴

参与 sageLLM 项目的成员可获得额外研究补贴，具体金额根据学历和贡献度确定。

**汇报义务**：定期汇报项目进度（具体频率由项目负责人确定）

### 全员福利（sageLLM / SAGE 项目成员均可申请）

- 报销 GitHub Copilot Pro 订阅费用
- 其他课题组福利（按课题组规定申请）

> **说明**：具体福利政策以课题组最新通知为准

## 变更记录

- 2026-01-04：添加基金信息，调整文档结构（SAGE → sageLLM → NeuroMem）
- 2026-01-04：从 `team-management.md` 提取人员分配部分，独立文档
- 2026-01-03：原 `team-management.md` 创建，明确项目孵化/独立口径
