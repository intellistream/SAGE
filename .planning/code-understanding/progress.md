# 进度
- 已完成 README/pyproject/DEVELOPER 与主要源代码交叉阅读。
- 已核对高层构图、两条执行路径、FlowNet lightweight 默认行为、原生 DSL 边界、缓存、serving、CLI、edge、workload。
- 已运行 4 个核心测试文件：24 passed / 4 failed（缺 cloudpickle）/ 1 skipped。
- 完整导览保存到同目录 findings.md；本次只新增分析记录，没有修改产品代码。

# 第二阶段：缓存接入与重构
- 使用已有 /home/shuhao/miniconda3/bin/python（Python 3.13，已有 cloudpickle/pytest）完成基线验证；基线 23 passed / 1 failed，复现 round-robin 在线程执行时选择副本导致不稳定。
- 新增 backend-neutral 不可变 topology plan，共享 CompiledPlanCache，compile 每次重新绑定 actor/函数/参数。支持自定义缓存与 bypass。
- 修复真实线性拓扑检测、按边执行顺序、DAG/streaming 无用 actor 构造、批处理重复函数构造、轮询提交顺序、flatmap/None 语义、服务 context 路径。
- 修复 batch/streaming sink 收尾、等待在途 actor 调用后清理、流式失败状态及 single-flight interruption 唤醒。
- 针对性回归：68 passed；正在跑完整 src/tests。
- 最终复核发现 local actor 同副本可被线程池重入，已加 replica 共用锁，补 Local/FlowNet 两种后端的有状态副本回归。
- 最终全量 src/tests：190 passed, 1 skipped, 7 deprecation warnings（5.15s）。Ruff lint/format、发布边界、diff 检查全部通过。
- 本轮完成；改动留在工作区，未提交、未推送。无硬件/外部服务动作，也未宣称性能加速。
