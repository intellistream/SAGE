# SAGE 配置目录

本目录保存仓库跟踪的配置样例与静态配置资源。当前主入口文件是 `config/config.yaml`。

## 文件

| 文件           | 作用                                                             |
| -------------- | ---------------------------------------------------------------- |
| `config.yaml`  | 统一配置样例，包含集群、远程环境、模型、gateway 和 studio 等设置 |
| `cluster.yaml` | 集群相关补充配置样例                                             |
| `models.json`  | 模型清单或静态模型元数据                                         |

## 快速查看

```bash
# 编辑配置样例
vi config/config.yaml

# 查看当前本地状态
sage status

# 查看运行时可见节点
sage runtime nodes

# 查看 gateway 集成契约
sage serve gateway --json
```

## config.yaml 当前主要配置段

- `cluster_name`: 集群标识
- `auth`: SSH 与连接相关参数
- `provider`: 头节点、工作节点与 provider 类型
- `remote`: 远程 Python、Conda、SAGE 根路径等设置
- `llm`: 模型、端口和推理相关参数
- `embedding`: 向量模型与服务端口
- `gateway`: OpenAI-compatible gateway 与 memory backend 设置
- `studio`: Studio 前后端端口
- `max_workers`: 本地或远程 worker 数量上限

当前 `config.yaml` 中仍包含部分历史分布式运行时字段，例如 `ray` 段。是否继续保留、迁移或收敛，应以当前代码读取路径和迁移计划为准；不要把未验证字段直接当作新的推荐配置面。

## 使用原则

- 以当前代码和 CLI 行为为准更新配置说明
- 不在文档中引入新的 venv 工作流
- 端口策略应优先遵循仓库当前统一端口约定
- 若用户文档需要扩展解释，请更新独立的 `sage-docs`，不要在主仓重复维护长篇说明

## 相关命令

```bash
./quickstart.sh --doctor
sage status
sage runtime nodes
sage serve gateway --probe --json
```
