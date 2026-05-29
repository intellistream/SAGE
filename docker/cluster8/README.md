# 8-Node Docker Cluster For Real SAGE Evaluation

这套配置把 SAGE 的分布式评测落到真实的 8 节点 Docker 集群里，不做 mock，不把当前代码推到 `main`，而是直接从当前容器把工作区同步到宿主机
`user@11.11.11.32`。

## 设计约束

- 控制面和数据面都是真实容器节点：1 个 head + 7 个 worker。
- 容器镜像里的 Miniconda 根目录固定为 `/root/miniconda3`。
- 运行时默认直接复用“当前实验容器”的真实状态作为集群镜像基底，因此比重新解环境更接近“同环境”。当前可执行实验环境是 `sagellm`（Python 3.11），而不是当前
  `base`。原因是本仓库现行代码和评测链路要求 Python 3.11，而本机 `base` 仍是 Python 3.8，直接照搬无法运行。
- 当前工作区代码通过 `rsync` 同步到宿主机，不需要推远端分支。
- 数据集、缓存、日志、结果全部走宿主机共享目录，便于复用和回收。
- ANN/FAISS 索引允许离线构建；评测脚本默认使用 `faiss_offline`，索引会落在统一结果目录的 run 子目录下。

## 宿主机目录布局

默认部署根目录：`/home/user/sage-docker-cluster`

- `workspace/`: 从当前容器同步过去的工作区副本
- `shared/datasets/`: 共享数据集目录
- `shared/results/`: 统一结果目录
- `shared/logs/`: 容器与 FlowNet 运行日志
- `shared/cache/`: Hugging Face / 其他缓存
- `shared/ssh/`: 容器间 SSH 控制密钥

统一结果根目录固定为：`/home/user/sage-docker-cluster/shared/results/langchain_rag_shared_workloads`

## 资源预算

默认资源配额按宿主机 `76 CPU / 251 GiB RAM` 保守划分：

- head: `8 CPU / 16 GiB`
- worker x7: `8 CPU / 12 GiB`
- 合计: `64 CPU / 100 GiB`

这给宿主机本身和其他进程留出了明显余量，不会把整机资源吃满。

## 使用方式

从当前容器直接部署到宿主机：

```bash
cd /root/SAGE/SAGE
bash docker/cluster8/scripts/deploy_from_container.sh
```

部署完成后，如果你在宿主机上继续操作：

```bash
cd /home/user/sage-docker-cluster/workspace/SAGE/docker/cluster8
bash scripts/host_cluster_ctl.sh status
bash scripts/host_cluster_ctl.sh langchain-rpc-up
bash scripts/host_cluster_ctl.sh run-rag-distributed --variants retrieval_only,full_rag --source-request-rate-qps 16
bash scripts/host_cluster_ctl.sh langchain-rpc-down
bash scripts/host_cluster_ctl.sh all-down
```

## 关键说明

- `scripts/deploy_from_container.sh` 会先把当前实验容器 commit 成宿主机上的集群基底镜像，再同步工作区到宿主机并启动集群。由于当前容器本身会被宿主机
  commit，这个脚本会把宿主机 `all-up` 放到后台任务里执行并轮询完成状态，避免同步 SSH 控制链路在 commit 过程中被打断。导出的 conda/pip 锁文件保留为回退路径。
- 当前 `sagellm` 环境里依赖的一组本地 editable `sagellm*` 仓库也会从 `/root/workspace`
  同步到宿主机共享工作区，并在容器启动时重新安装，避免镜像构建时错误回落到不可用的远端精确版本。
- `scripts/host_cluster_ctl.sh` 在宿主机上负责 `docker compose up/down`、FlowNet
  `cluster up/down/status`、LangChain RPC worker 起停，以及 RAG 评测命令。
- `run-rag-distributed` 会默认把 `sage` 切到 FlowNet `connect` 远端执行，并把 `langchain_rpc` 指向 8 个容器内
  worker，适合直接跑 8 节点真实分布式对比。
- 每个容器启动时都会把 `/workspace/SAGE` 和 `/workspace/llm-serving-workloads` 重新做一次 editable
  install，确保运行的就是共享工作区里的当前代码。
- 容器间 SSH 使用部署目录下自动生成的专用 ed25519 key；不会复用 GitHub SSH key。
