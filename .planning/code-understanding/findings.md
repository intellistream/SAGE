# SAGE 代码导览（当前本地 checkout）

## 定位与边界
SAGE（Streaming-Augmented Generative Execution）将工作流表示为显式数据流。根包 isage 使用 src 布局，Python >=3.11，基础依赖 cloudpickle、pyyaml。产品实现位于 src/sage；tools 主要负责安装、CI、维护；src/tests 是仓库测试。外部推理服务与可选 RAG、memory、intent、tool-use 不属于默认核心实现。

## 核心阅读地图
- foundation/__init__.py 与 foundation/core：用户函数 BaseFunction、Batch/Source/Map/Filter/FlatMap/Sink/KeyBy/Join/CoMap、Collector；另有配置、日志、模型资产工具。
- stream/datastream.py：链式构图；map/filter/flatmap/keyby/connect/sink/fill_future。Callable 经 wrap_lambda 包装。_apply 记录边并将 transformation 加入 env.pipeline。
- stream/transformations.py：保存函数类、构造参数、parallelism、上下游、输入编号，以及工厂。stream/connected_streams.py 提供多输入组合。
- runtime/base_environment.py：数据源入口、服务注册、pipeline 容器。from_batch 可接受函数类、集合或 iterable。
- runtime/environments.py：LocalEnvironment 与 FlowNetEnvironment 提交/停止入口。
- runtime/job_manager.py：本地单例作业管理，记录 UUID、状态、handle、错误。
- runtime/pipeline_compiler.py：将 transformation 转为 CompiledActorGraph，建立边表、actor wrapper 和方法引用；是高层运行时最重要的实现入口。
- runtime/local_backend.py：进程内 actor 副本与 ThreadPoolExecutor。
- runtime/flownet_backend.py：FlowNet adapter，默认 lightweight，本地 ActorAPI/LocalActorRegistry；cluster 模式初始化 session。create 仍注册 local actor，submit 外部 FlowDeclaration/URI 需要 cluster session。

## 两种高层执行路径
LocalEnvironment.submit → JobManager.submit_job → PipelineCompiler.compile(LocalRuntimeAdapter) → CompiledActorGraph.submit。
FlowNetEnvironment.submit → PipelineCompiler.compile(FlowNetRuntimeAdapter) → CompiledActorGraph.submit。

1. 线性 batch actor 路径：_can_execute_linear_actor_batch 判定后，先收集 source items，_execute_chain 按 stage 发起异步 actor method 调用并等待结果，再进入下一 stage。不要将这条批处理路径理解为逐条端到端流水执行。
2. 通用图路径：_build_instances 构造函数副本；Packet 携带 payload、partition_key、input_index；deque 驱动沿边传播。_process_packet 处理 keyed/filter/flatmap/join/comap/sink。streaming 模式每 source 一个线程，派发受 _dispatch_lock 保护。

parallelism：source 固定 1；下游副本暴露 ctx.parallel_index/parallelism。keyed 以 repr(key) 的 blake2b hash 稳定选副本；非 keyed 轮询。副本数量不能直接视为并发吞吐保证，需核对所走执行路径。
autostop=True 同步执行 batch；False 返回/记录后台 streaming handle。LocalEnvironment 返回 job UUID；FlowNetEnvironment 返回 compiled submit 的结果，二者返回值并不相同。

## FlowNet 原生层
与上面的高层 DataStream 编译器区分：runtime/flownet/api/declarations.py、decorators.py 提供 flow/actor/service/source 等声明；compiler/flow_compiler.py 将 DSL 编译为 core/FlowProgram。client 管理 session、bootstrap、endpoint、dataset job；runtime/runtime.py 的 V1RuntimeHost 组织执行循环、actor、通信、topic、backend container、shared state、endpoint 等。runtime/flowengine 与 operator_runtime 负责程序/算子执行。不能假设高层 Environment 会自动走完整原生集群提交链。

## 编译缓存
runtime/compiled_plan_cache.py：结构化 fingerprint（DAG/schema/policy/capabilities/retrieval/resource/compiler version）→ SHA256；LRU 容量、TTL、并发 single-flight、短期失败缓存。bind_compiled_plan 把请求态交给 binder，避免请求状态污染结构缓存。FlowDeclaration.compile_reusable/bind_reusable 有集成测试；高层 PipelineCompiler 并未自动使用这个缓存。

## Serving 与应用
- serving/gateway.py 生成外部 sagellm gateway 的命令、环境和地址，提供健康探测；不实现模型推理。
- serving/integrations/contracts.py、registry.py：工作流适配器的 import/submit/poll/collect 协议及响应校验。
- serving/integrations/policy.py：deadline class、负载压力、max_tokens cap、优先级和派发决策；registry 可在提交前应用并记录 policy_decision。
- cli/main.py：argparse 路由；verify 仅检查核心 import。serve gateway 默认打印启动契约，--probe 才调用健康检查，不直接启动服务。
- edge/app.py：可选 FastAPI shell 与 /healthz、/readyz，显式注入 llm_app 后挂载。
- workloads/large_scale_analysis.py：合成事件→分片 map→incident reducer→评分报告；支持 deterministic/stub/OpenAI completion 等 reducer。run_large_scale_analysis_workload 本身使用 Python 列表遍历 map，不自动证明分布式执行或真实 LLM 调用。

## 验证
执行：python3 -m pytest src/tests/test_runtime_local_consolidation.py src/tests/test_runtime_parallelism_contract.py src/tests/test_compiled_plan_cache.py src/tests/test_cli_main.py -q
结果：24 passed, 4 failed, 1 skipped（1.22 秒）。4 个失败均在 FlowNet 启动导入时缺少 cloudpickle；不是执行断言失败。跳过的是 CI-only sagellm 检查。未修改环境依赖、未启动外部服务、未运行设备实验。
已验证的是本地执行、部分 parallelism、缓存和 CLI 用例；不是整个项目测试通过或跨机器验证。

## 推荐阅读顺序
先看 test_runtime_local_consolidation.py 的 NumberBatchSource/DoubleValue/CollectSink 和相关用例，再读 DataStream._apply → BaseTransformation.add_upstream → Environment.submit → PipelineCompiler.compile → CompiledActorGraph.submit。随后读 parallelism 测试，再进入 FlowNet 原生声明/编译/运行时；需要做服务调度时读 serving/integrations。

## 缓存重构设计（进行中）
- 不能缓存 CompiledActorGraph：其包含当前 env、输入、实例、actor handle、服务和停止状态。
- 拟缓存不可变的算子种类、并行度、以索引编码的边和线性调度顺序，每次 compile 重新绑定用户函数及参数。
- 发现线性 batch 判定只看算子类型，不检查拓扑，分支图可能被串行错误执行；需回归测试。
- 发现 streaming finally 枚举全进程 source 线程，包含自身，因此无法可靠关闭 sink；异常仅记录日志，作业可能被标为成功结束。
- 发现缓存 compiler 抛 BaseException 时未唤醒 single-flight 等待者。

## 第二阶段最终状态（覆盖前文基线描述）
PipelineCompiler 现在默认接入共享 CompiledPlanCache；新增 frozen topology artifact 和 compile/bind 分离。缓存不持有函数类、参数、env、输入、actor、服务实例。可自定义缓存或 use_cache=False；compiled_plan 暴露 fingerprint 和共享 artifact，执行图单次使用。
高层 Environment 自动使用缓存并传入 autostop 避免流式无用 actor 构造。修复拓扑分支判定、按真实边排列线性执行、服务 context、重复实例构造、None/flatmap 语义、sink 收尾和流式失败状态。Local actor 同一副本串行、不同副本可并发；两个 adapter 都在提交时确定 round-robin 目标。
测试最终为 190 passed / 1 skipped，Ruff 与 release/tools 边界及 diff 检查通过。DEVELOPER.md、CHANGELOG.md 已更新；没有推送或提交。
