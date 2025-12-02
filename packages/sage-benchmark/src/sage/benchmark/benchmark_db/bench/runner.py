"""
Benchmark Runner

实现完整的测评流程执行器
基于 big-ann-benchmarks/neurips23/congestion/run.py 的设计
"""

import os
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .cache_profiler import CacheProfiler
from .maintenance import MaintenancePolicy, MaintenanceState
from .metrics import BenchmarkMetrics, generate_timestamps
from .worker import CongestionDropWorker


def store_timestamps_to_csv(
    filename: str,
    ids: np.ndarray,
    event_timestamps: np.ndarray,
    arrival_timestamps: np.ndarray,
    processed_timestamps: np.ndarray,
    counts: int,
):
    """
    将时间戳和 ID 保存到 CSV 文件

    Args:
        filename: 基础文件名
        ids: ID 数组
        event_timestamps: 事件时间戳
        arrival_timestamps: 到达时间戳
        processed_timestamps: 处理时间戳
        counts: 计数器（用于区分不同的批次）
    """
    df = pd.DataFrame(
        {
            "id": ids,
            "eventTime": event_timestamps,
            "arrivalTime": arrival_timestamps,
            "processedTime": processed_timestamps,
        }
    )

    head, tail = os.path.split(filename)
    if head and not os.path.isdir(head):
        os.makedirs(head)

    full_filename = f"{filename}_{counts}_timestamps.csv"
    df.to_csv(full_filename, index=False)
    print(f"Timestamps saved to {full_filename}")


def perform_controlled_rebuild(algo, ds, intervals: list[tuple[int, int]]) -> float:
    """
    执行受控的索引重建
    重置算法状态并重放给定区间的数据

    Args:
        algo: 算法实例
        ds: 数据集实例
        intervals: 要重建的区间列表 [(start, end), ...]

    Returns:
        维护延迟（微秒）
    """
    rebuild_start = time.time()
    was_running = getattr(algo, "_hpc_active", False)

    valid_intervals = [(s, e) for s, e in intervals if s < e]
    if not valid_intervals:
        return 0.0

    try:
        # 等待待处理的操作
        if hasattr(algo, "waitPendingOperations"):
            try:
                algo.waitPendingOperations()
            except Exception:
                pass

        # 停止 HPC 线程
        if was_running and hasattr(algo, "endHPC"):
            algo.endHPC()

        # 重置索引
        if not hasattr(algo, "reset_index"):
            raise RuntimeError("Algorithm does not expose reset_index for maintenance rebuild.")
        algo.reset_index()

        # 重启 HPC 线程
        if was_running and hasattr(algo, "startHPC"):
            algo.startHPC()

        # 重新加载数据
        for interval_start, interval_end in valid_intervals:
            ids = np.arange(interval_start, interval_end, dtype=np.uint32)
            if ids.size == 0:
                continue
            data = ds.get_data_in_range(interval_start, interval_end)
            if data.shape[0] != ids.shape[0]:
                raise RuntimeError("Mismatch between rebuild ids and dataset slice.")
            algo.initial_load(data, ids)
    finally:
        # 确保线程在后续步骤中运行
        if (
            was_running
            and hasattr(algo, "_hpc_active")
            and not algo._hpc_active
            and hasattr(algo, "startHPC")
        ):
            algo.startHPC()

    return (time.time() - rebuild_start) * 1e6


@dataclass
class RunbookEntry:
    """Runbook 操作条目"""

    operation: str  # 'initial_load', 'batch_insert', 'search', 'maintenance_rebuild', 'replace'
    params: dict  # 操作参数


class BenchmarkRunner:
    """
    测评流程执行器

    负责执行 runbook 中定义的各种操作，包括：
    - initial_load: 初始数据加载
    - startHPC: 启动工作线程
    - enableScenario: 启用场景（随机污染/丢弃/乱序）
    - batch_insert: 批量插入（支持流式模拟和连续查询）
    - insert: 简单插入
    - delete: 删除
    - search: 搜索性能测试
    - maintenance_rebuild: 索引重建维护
    - waitPending: 等待待处理操作
    - endHPC: 结束工作线程
    """

    def __init__(
        self,
        algorithm,
        dataset,
        k: int = 10,
        num_workers: int = 1,
        maintenance_policy: Optional[MaintenancePolicy] = None,
        save_timestamps: bool = True,
        output_dir: str = "results",
        use_worker: bool = True,
        enable_cache_profiling: bool = False,
    ):
        """
        Args:
            algorithm: 算法实例
            dataset: 数据集实例
            k: kNN 查询的 k 值
            num_workers: 并行工作线程数
            maintenance_policy: 维护策略
            save_timestamps: 是否保存时间戳数据
            output_dir: 输出目录
            use_worker: 是否使用 CongestionDropWorker（启用队列和拥塞丢弃）
            enable_cache_profiling: 是否启用 cache miss 监测
        """
        self.base_algo = algorithm  # 保存原始算法
        self.dataset = dataset
        self.k = k
        self.num_workers = num_workers
        self.save_timestamps = save_timestamps
        self.output_dir = output_dir
        self.use_worker = use_worker
        self.enable_cache_profiling = enable_cache_profiling

        # Cache profiler（需要在创建worker之前初始化）
        self.cache_profiler = None
        if enable_cache_profiling:
            self.cache_profiler = CacheProfiler()
            # 在启动时检查可用性
            if not self.cache_profiler.is_available():
                print("  ⚠️  Cache profiling 不可用，将禁用该功能")
                self.cache_profiler = None
                self.enable_cache_profiling = False

        # 如果使用 worker，则包装算法
        if use_worker:
            self.worker = CongestionDropWorker(algorithm, cache_profiler=self.cache_profiler)
            self.algo = self.worker  # 通过 worker 访问算法
            self._hpc_active = False
        else:
            self.worker = None
            self.algo = algorithm

        # 维护状态
        self.maintenance_state = MaintenanceState()
        self.maintenance_policy = maintenance_policy or MaintenancePolicy()

        # 性能指标
        self.metrics = BenchmarkMetrics()
        self.metrics.algorithm_name = getattr(
            self.base_algo, "name", self.base_algo.__class__.__name__
        )
        self.metrics.dataset_name = dataset.short_name()
        self.metrics.distance = dataset.distance()
        self.metrics.search_type = dataset.search_type()
        self.metrics.count = k

        # 运行状态
        self.all_results: list[np.ndarray] = []  # 正式查询结果 (search operation)
        self.all_results_continuous: list[np.ndarray] = []  # 周期性查询结果 (batch_insert)
        self.result_map: dict[int, int] = {}  # {search_index: step}

        # 属性字典（用于保存详细信息）
        self.attrs = {
            "name": self.metrics.algorithm_name,
            "pendingWrite": 0,
            "totalTime": 0,
            "continuousQueryLatencies": [],
            "continuousQueryResults": [],
            "latencyInsert": [],
            "latencyQuery": [],
            "latencyDelete": [],
            "updateMemoryFootPrint": 0,
            "searchMemoryFootPrint": 0,
            "querySize": dataset.nq,
            "insertThroughput": [],
            "batchLatency": [],
            "batchThroughput": [],
            "batchinsertThroughtput": [],
            "maintenanceLatency": 0.0,
            "maintenanceRebuilds": 0,
            "maintenanceBudgetUs": getattr(self.maintenance_policy, "budget_us", 0.0) or 0.0,
            "maintenanceBudgetUsed": 0.0,
            "maintenancePolicyEnabled": getattr(self.maintenance_policy, "enable", True),
            "maintenanceDeletionRatioTrigger": getattr(
                self.maintenance_policy, "deletion_ratio_trigger", 0.0
            )
            or 0.0,
            "maintenanceEvents": [],
        }

        # 计数器
        self.counts = {
            "initial": 0,
            "batch_insert": 0,
            "insert": 0,
            "delete": 0,
            "search": 0,
            "maintenance_rebuild": 0,
        }

    def run_runbook(self, runbook: dict, dataset_name: str = None) -> BenchmarkMetrics:
        """
        执行 runbook 定义的测评流程

        Args:
            runbook: runbook 字典，格式如下：
                {
                    'dataset_name': {
                        'max_pts': 1000000,
                        1: {'operation': 'startHPC'},
                        2: {'operation': 'initial', 'start': 0, 'end': 50000},
                        3: {'operation': 'batch_insert', 'start': 50000, 'end': 100000,
                            'batchSize': 2500, 'eventRate': 10000},
                        4: {'operation': 'search'},
                        5: {'operation': 'endHPC'},
                    }
                }
            dataset_name: 数据集名称（用于从 runbook 中选择配置）

        Returns:
            BenchmarkMetrics: 测评指标
        """
        # 如果没有指定数据集名称，使用当前数据集的名称
        if dataset_name is None:
            dataset_name = self.dataset.short_name()

        # 从数据集配置中提取操作
        if dataset_name not in runbook:
            raise ValueError(f"Dataset '{dataset_name}' not found in runbook configuration")

        dataset_config = runbook[dataset_name]
        max_pts = dataset_config.get("max_pts")

        # 按数字键排序提取操作
        operations = []
        i = 1
        while i in dataset_config:
            op = dataset_config[i]
            operations.append(op)
            i += 1

        print(f"\n{'=' * 60}")
        print(
            f"Running {self.metrics.algorithm_name} on {self.metrics.dataset_name} dataset with {len(operations)} operations"
        )

        # 记录 runbook 开始时间
        runbook_start_time = time.time()

        # 初始化算法（调用setup）
        if hasattr(self.algo, "setup"):
            dtype = self.dataset.dtype if hasattr(self.dataset, "dtype") else "float32"
            # max_pts = max_pts if max_pts else 1000000
            ndim = self.dataset.d
            self.algo.setup(dtype, max_pts, ndim)
            print(f"✓ 算法初始化完成: dtype={dtype}, max_pts={max_pts}, ndim={ndim}\n")

        for idx, op in enumerate(operations):
            op_type = op.get("operation")
            print(f"\n[{idx + 1}/{len(operations)}] 执行操作: {op_type}")

            if op_type == "initial":
                self._execute_initial(op)
            elif op_type == "startHPC":
                self._start_workers()
            elif op_type == "enableScenario":
                self._enable_scenario(op)
            elif op_type == "batch_insert":
                self._execute_batch_insert(op)
            elif op_type == "insert":
                self._execute_insert(op)
            elif op_type == "delete":
                self._execute_delete(op)
            elif op_type == "search":
                self._execute_search(op)
            elif op_type == "maintenance_rebuild":
                self._execute_maintenance_rebuild(op)
            elif op_type == "waitPending":
                self._wait_pending()
            elif op_type == "endHPC":
                self._stop_workers()
            else:
                print(f"  ⚠️  未知操作类型: {op_type}")

        # 完成测评，汇总指标
        runbook_elapsed = time.time() - runbook_start_time
        self.attrs["totalTime"] = runbook_elapsed
        self._finalize_metrics()

        print(f"\n{'=' * 60}")
        print("Runbook 执行完成")
        print(f"总用时: {runbook_elapsed:.2f}s")
        print(f"{'=' * 60}\n")

        # 结果保存由 run_benchmark.py 的 store_results 统一处理
        # 这里不再重复保存，避免生成重复文件

        return self.metrics

    def _execute_initial(self, op: dict):
        """执行初始数据加载"""
        # 支持两种参数格式：
        # 1. data_size: 直接指定数据量
        # 2. start, end: 指定数据范围
        if "start" in op and "end" in op:
            start_idx = op["start"]
            end_idx = op["end"]
            data_size = end_idx - start_idx
        else:
            data_size = op.get("data_size", self.dataset.nb)
            start_idx = 0
            end_idx = data_size

        print(f"  加载初始数据: {data_size:,} 条 (索引 {start_idx} 到 {end_idx})")

        # 使用辅助方法加载数据
        X = self._load_data_range(start_idx, end_idx)

        # 对于流式索引使用 insert 方法，而不是 fit
        # 流式算法应该通过 insert 一条条添加数据
        ids = np.arange(start_idx, end_idx, dtype=np.uint32)

        # start_time = time.time()
        self.algo.insert(X, ids)
        # elapsed = time.time() - start_time
        self.counts["initial"] = data_size
        self.maintenance_state.live_points = data_size

        print(f"  ✓ 初始加载完成: {data_size:,} 条数据")

    def _load_data_range(self, start_idx: int, end_idx: int) -> np.ndarray:
        """
        加载指定范围的数据

        Args:
            start_idx: 起始索引
            end_idx: 结束索引（不包含）

        Returns:
            数据数组
        """
        # 策略选择：根据数据集大小决定加载方式
        # 1. 小数据集（< 1000万）：直接使用 get_data_in_range（内部加载全部数据）
        # 2. 大数据集（>= 1000万）：使用迭代器方式（避免内存溢出）

        LARGE_DATASET_THRESHOLD = 10_000_000  # 1000万条

        if self.dataset.nb < LARGE_DATASET_THRESHOLD:
            # 小数据集：直接切片，性能最优
            return self.dataset.get_data_in_range(start_idx, end_idx)
        else:
            # 大数据集：使用迭代器，内存友好
            X_list = []
            for i, batch in enumerate(self.dataset.get_dataset_iterator(bs=10000)):
                batch_start = i * 10000
                batch_end = min((i + 1) * 10000, self.dataset.nb)

                # 计算当前批次与目标范围的交集
                if batch_end <= start_idx:
                    continue  # 还没到目标范围
                if batch_start >= end_idx:
                    break  # 已超过目标范围

                # 提取交集部分
                local_start = max(0, start_idx - batch_start)
                local_end = min(len(batch), end_idx - batch_start)
                X_list.append(batch[local_start:local_end])

                if batch_end >= end_idx:
                    break

            if X_list:
                return np.vstack(X_list)
            else:
                return np.array([]).reshape(0, self.dataset.d)

    def _start_workers(self):
        """启动工作线程（如果使用 Worker）"""
        if self.use_worker and self.worker:
            print("  启动 Worker 线程")
            self.worker.startHPC()
            self._hpc_active = True

        print("  ✓ 工作线程启动完成")

    def _enable_scenario(self, op: dict):
        """启用场景（随机丢弃/污染/乱序）"""
        if not self.use_worker or not self.worker:
            print("  ⚠️  未使用 Worker，场景配置将被忽略")
            return

        # 支持两种格式：
        # 1. 旧格式: {'type': 'random_drop', 'prob': 0.05}
        # 2. 新格式: {'randomDrop': 1, 'randomDropProb': 0.05}

        scenario_type = op.get("type", "none")

        # 拥塞丢弃始终启用（worker 默认为 True），不提供关闭选项
        # 只通过 useBackpressureLogic 控制丢弃策略

        # 背压逻辑配置
        if "useBackpressureLogic" in op:
            use_backpressure = bool(op["useBackpressureLogic"])
            self.worker.setBackpressureLogic(use_backpressure)
            mode = "队列满丢弃" if use_backpressure else "非空即丢弃"
            print(f"  拥塞丢弃策略: {mode}")

        # 随机丢弃
        random_drop = False
        random_drop_prob = 0.0
        if "randomDrop" in op and op.get("randomDrop"):
            random_drop = True
            random_drop_prob = op.get("randomDropProb", 0.05)
        elif scenario_type == "random_drop":
            random_drop = True
            random_drop_prob = op.get("prob", 0.05)

        # 随机污染
        random_contamination = False
        random_contamination_prob = 0.0
        if "randomContamination" in op and op.get("randomContamination"):
            random_contamination = True
            random_contamination_prob = op.get("randomContaminationProb", 0.1)
        elif scenario_type == "random_contamination":
            random_contamination = True
            random_contamination_prob = op.get("prob", 0.1)

        # 乱序处理
        out_of_order = False
        if "outOfOrder" in op and op.get("outOfOrder"):
            out_of_order = True
        elif scenario_type == "out_of_order":
            out_of_order = True

        # 应用配置到 worker
        self.worker.enableScenario(
            random_contamination=random_contamination,
            random_contamination_prob=random_contamination_prob,
            random_drop=random_drop,
            random_drop_prob=random_drop_prob,
            out_of_order=out_of_order,
        )

        if random_drop:
            print(f"  ✓ 启用随机丢弃: {random_drop_prob * 100:.1f}%")
        if random_contamination:
            print(f"  ✓ 启用随机污染: {random_contamination_prob * 100:.1f}%")
        if out_of_order:
            print("  ✓ 启用乱序处理")

    def _execute_batch_insert(self, op: dict):
        """
        执行批量插入操作（支持流式模拟和连续查询）

        连续查询规则（参考 big-ann-benchmarks/neurips23/congestion）：
        - 每插入总数据量的 1/100 就执行一次查询
        - 即对于 10000 条数据，每 100 条插入后查询一次

        参数:
            start, end: 数据范围
            或 count: 插入数据量
            batchSize: 每批次大小（默认全部一次插入）
            eventRate: 插入速率 ops/s（0=不限速）
            continuousQuery: 是否启用连续查询（默认 True）
        """
        # 准备数据 - 必须指定 start, end, batchSize, eventRate
        if "start" not in op or "end" not in op:
            raise ValueError("batch_insert operation requires 'start' and 'end' parameters")
        if "batchSize" not in op or "eventRate" not in op:
            raise ValueError(
                "batch_insert operation requires 'batchSize' and 'eventRate' parameters"
            )

        start_idx = op["start"]
        end_idx = op["end"]
        count = end_idx - start_idx

        batch_size = op["batchSize"]
        event_rate = op["eventRate"]
        enable_continuous_query = op.get("continuousQuery", True)  # 默认启用连续查询

        # 连续查询间隔：每插入总数据量的 1/100 查询一次
        continuous_query_interval = count // 100 if enable_continuous_query else 0

        # 准备查询数据（如果需要连续查询）
        queries = None
        if continuous_query_interval > 0:
            queries = self.dataset.get_queries()

        # 生成事件时间戳（根据 eventRate 生成理想到达时间）
        event_timestamps = (
            generate_timestamps(count, event_rate) if event_rate > 0 else np.zeros(count)
        )
        arrival_timestamps = np.zeros(count, dtype=np.float64)
        processed_timestamps = np.zeros(count, dtype=np.float64)

        batch_latencies = []
        continuous_query_latencies = []
        continuous_query_results = []  # 存储查询返回的邻居 ID
        inserted_count = 0

        # 记录初始丢弃计数
        initial_drop_count = self.worker.drop_count_total if self.use_worker and self.worker else 0

        # 设置 worker 的基准开始时间（用于计算相对时间戳）
        start_time = time.time()
        if self.use_worker and self.worker:
            self.worker.benchmark_start_time = start_time
            self.worker.batch_timestamps = []  # 清空之前的记录

        # 按批次插入
        num_batches = (count + batch_size - 1) // batch_size
        start_time = time.time()

        # Cache profiling 统计
        # batch_cache_stats = []  # 存储每个批次的 cache miss 统计

        for batch_idx in range(num_batches):
            batch_start = batch_idx * batch_size
            batch_end = min((batch_idx + 1) * batch_size, count)
            batch_len = batch_end - batch_start

            # 按需加载当前批次的数据（避免一次性加载全部数据导致内存溢出）
            batch_data = self._load_data_range(start_idx + batch_start, start_idx + batch_end)
            batch_ids = np.arange(start_idx + batch_start, start_idx + batch_end, dtype=np.uint32)

            # 限速：使用 busy waiting 等待批次到达时间（精确到微秒）
            if event_rate > 0:
                tNow = (time.time() - start_time) * 1e6
                tExpectedArrival = event_timestamps[batch_end - 1]  # 批次最后一个元素的期望到达时间
                while tNow < tExpectedArrival:
                    # busy waiting for a batch to arrive
                    tNow = (time.time() - start_time) * 1e6
                # 记录到达时间戳（整个批次使用相同的到达时间）
                arrival_timestamps[batch_start:batch_end] = tExpectedArrival

            # 执行批量插入（通过 worker 队列）
            # 注意：这里只是将数据放入队列，真实的处理延迟由 worker 记录
            # 传递到达时间戳给 worker 用于延迟追踪
            # Cache profiling 现在在 worker 层执行，更精确地测量索引操作
            if event_rate > 0:
                self.algo.insert(batch_data, batch_ids, arrival_time=tExpectedArrival)
            else:
                self.algo.insert(batch_data, batch_ids)

            # 记录处理完成时间戳
            batch_processed_time = (time.time() - start_time) * 1e6
            processed_timestamps[batch_start:batch_end] = batch_processed_time

            inserted_count += batch_len

            # 显示队列状态（如果使用 worker）
            # if self.use_worker and self.worker and batch_idx % 10 == 0:
            #     insert_queue_size = self.worker.insert_queue.size()
            #     if insert_queue_size > 0:
            #         print(f"    [{batch_idx}] 队列状态: insert={insert_queue_size}/{self.worker.insert_queue_capacity}")

            # 连续查询（每插入总数据量的 1/100 执行一次）
            if (
                continuous_query_interval > 0
                and inserted_count % continuous_query_interval < batch_size
            ):
                # 等待 worker 处理完队列中的数据（确保索引状态最新）
                # if self.use_worker and self.worker:
                #     self.worker.waitPendingOperations()

                # 输出进度信息（类似 big-ann-benchmarks 风格）
                current_range_start = start_idx + batch_start
                current_range_end = start_idx + batch_end
                progress_pct = (inserted_count / count) * 100
                print(
                    f"    [{batch_idx}] {current_range_start}~{current_range_end} querying all {len(queries)} queries (进度: {progress_pct:.1f}%)"
                )

                # 执行全量查询：一次性传入所有查询向量
                # Cache profiling 在 worker.query() 中进行
                cq_start = time.time()

                try:
                    results = self.algo.query(queries, self.k)

                    # 处理返回值格式
                    if isinstance(results, tuple):
                        results = results[0]  # (neighbors, distances) -> neighbors

                    cq_latency = time.time() - cq_start
                    continuous_query_latencies.append(cq_latency)

                    # 保存查询结果的邻居 ID（不计算召回率，与 big-ann-benchmarks 一致）
                    # 处理 None 或空结果的情况
                    if results is not None and len(results) > 0:
                        # results shape: (nq, k) - 每个查询的k个邻居
                        for i in range(len(results)):
                            self.all_results_continuous.append(results[i])
                            continuous_query_results.append(results[i])
                    else:
                        # 索引为空或查询失败，记录空结果
                        print("       ⚠️  查询返回空结果")
                        for i in range(len(queries)):
                            empty_result = np.full(self.k, -1, dtype=np.int32)
                            self.all_results_continuous.append(empty_result)
                            continuous_query_results.append(empty_result)

                except Exception as e:
                    # 发生异常时仍然记录延迟（即使查询失败）
                    cq_latency = time.time() - cq_start
                    continuous_query_latencies.append(cq_latency)

                    print(f"       ❌ 查询异常: {type(e).__name__}: {str(e)}")
                    # 发生异常时记录空结果
                    for i in range(len(queries)):
                        empty_result = np.full(self.k, -1, dtype=np.int32)
                        self.all_results_continuous.append(empty_result)
                        continuous_query_results.append(empty_result)

                # 输出这一轮查询的统计信息
                # avg_latency_per_query = (cq_latency * 1000) / len(queries)  # 毫秒
                # print(f"       全量查询完成: 总耗时={cq_latency*1000:.2f}ms, 平均每query={avg_latency_per_query:.4f}ms")

        elapsed = time.time() - start_time
        throughput = count / elapsed

        # 计算丢弃统计
        final_drop_count = self.worker.drop_count_total if self.use_worker and self.worker else 0
        batch_drop_count = final_drop_count - initial_drop_count
        drop_rate = batch_drop_count / count if count > 0 else 0

        # 从 worker 获取真实的处理延迟和cache统计（如果启用 worker）
        batch_latencies = []
        insert_latencies = []
        queue_wait_times = []
        batch_insert_throughputs = []  # 从 worker 计算每个批次的插入吞吐量

        if self.use_worker and self.worker and hasattr(self.worker, "batch_timestamps"):
            for ts in self.worker.batch_timestamps:
                batch_latencies.append(ts["end_to_end_latency"])  # 端到端延迟
                insert_latencies.append(ts["insert_latency"])  # 纯索引延迟
                queue_wait_times.append(ts["queue_wait_time"])  # 队列等待时间

                # 计算吞吐量：batch_size / insert_latency（秒）
                # insert_latency 是微秒，需要转换为秒
                insert_time_seconds = ts["insert_latency"] / 1e6
                if insert_time_seconds > 0:
                    batch_throughput = batch_size / insert_time_seconds
                    batch_insert_throughputs.append(batch_throughput)

            if batch_latencies:
                avg_e2e = np.mean(batch_latencies) / 1000  # 转换为毫秒
                p99_e2e = np.percentile(batch_latencies, 99) / 1000
                avg_insert = np.mean(insert_latencies) / 1000
                avg_queue = np.mean(queue_wait_times) / 1000

                print("    批次延迟统计:")
                print(f"      端到端: 平均={avg_e2e:.2f}ms, P99={p99_e2e:.2f}ms")
                print(f"      索引插入: 平均={avg_insert:.2f}ms")
                print(f"      队列等待: 平均={avg_queue:.2f}ms")

        # 更新状态
        self.counts["batch_insert"] += count
        self.maintenance_state.live_points += count
        # 保存真实的批次延迟（微秒）
        if batch_latencies:
            self.attrs["batchLatency"].extend(batch_latencies)
        self.attrs["continuousQueryLatencies"].extend(continuous_query_latencies)
        self.attrs["continuousQueryResults"].extend(continuous_query_results)
        # 保存每个批次的插入吞吐量（从 worker 的真实插入时间计算）
        if batch_insert_throughputs:
            self.attrs["batchinsertThroughtput"].extend(batch_insert_throughputs)

        # 从 worker 获取 cache miss 统计数据（插入和查询）
        if self.use_worker and self.worker:
            # 获取插入的cache统计（只收集新增的部分）
            insert_cache_stats_all = getattr(self.worker, "cache_stats_list", [])
            last_insert_count = getattr(self, "_last_collected_insert_cache_count", 0)
            insert_cache_stats = insert_cache_stats_all[last_insert_count:]

            if insert_cache_stats:
                for cache_stat in insert_cache_stats:
                    self.metrics.cache_miss_per_batch.append(cache_stat.cache_misses)
                    self.metrics.cache_references_per_batch.append(cache_stat.cache_references)
                    self.metrics.cache_miss_rate_per_batch.append(cache_stat.cache_miss_rate)

                # 更新已收集计数
                self._last_collected_insert_cache_count = len(insert_cache_stats_all)

                avg_cache_miss = np.mean([s.cache_misses for s in insert_cache_stats])
                avg_cache_miss_rate = np.mean([s.cache_miss_rate for s in insert_cache_stats])
                print("    插入 Cache miss 统计:")
                print(f"      {len(insert_cache_stats)} 个批次")
                print(f"      平均 cache misses: {avg_cache_miss:,.0f}")
                print(f"      平均 cache miss 率: {avg_cache_miss_rate:.2%}")

            # 获取查询的cache统计（只收集新增的部分）
            query_cache_stats_all = getattr(self.worker, "query_cache_stats_list", [])
            last_query_count = getattr(self, "_last_collected_query_cache_count", 0)
            query_cache_stats = query_cache_stats_all[last_query_count:]

            if query_cache_stats:
                for cache_stat in query_cache_stats:
                    self.metrics.query_cache_miss_per_batch.append(cache_stat.cache_misses)
                    self.metrics.query_cache_references_per_batch.append(
                        cache_stat.cache_references
                    )
                    self.metrics.query_cache_miss_rate_per_batch.append(cache_stat.cache_miss_rate)

                # 更新已收集计数
                self._last_collected_query_cache_count = len(query_cache_stats_all)

                avg_query_cache_miss = np.mean([s.cache_misses for s in query_cache_stats])
                avg_query_cache_miss_rate = np.mean([s.cache_miss_rate for s in query_cache_stats])
                print("    连续查询 Cache miss 统计:")
                print(f"      {len(query_cache_stats)} 次查询")
                print(f"      平均 cache misses: {avg_query_cache_miss:,.0f}")
                print(f"      平均 cache miss 率: {avg_query_cache_miss_rate:.2%}")

        # 记录丢弃统计
        if "dropCount" not in self.attrs:
            self.attrs["dropCount"] = 0
        self.attrs["dropCount"] += batch_drop_count

        print(f"  ✓ 批量插入完成: {elapsed:.2f}s, {throughput:.0f} ops/s, {num_batches} 个批次")
        if batch_drop_count > 0:
            print(f"    ⚠️  丢弃: {batch_drop_count:,} 条 ({drop_rate * 100:.1f}%)")
        if continuous_query_latencies:
            avg_cq_lat = np.mean(continuous_query_latencies) * 1000
            print(
                f"    连续查询: {len(continuous_query_latencies)} 次, 平均延迟: {avg_cq_lat:.2f}ms"
            )

        # 保存时间戳数据（如果启用）
        if self.save_timestamps:
            timestamp_file = op.get("timestampFile", f"{self.output_dir}/batch_insert_timestamps")
            batch_insert_count = self.counts["batch_insert"]
            store_timestamps_to_csv(
                timestamp_file,
                np.arange(start_idx, end_idx, dtype=np.uint32),
                event_timestamps,
                arrival_timestamps,
                processed_timestamps,
                batch_insert_count,
            )

    def _execute_insert(self, op: dict):
        """执行简单插入操作"""
        count = op.get("count", 100)
        print(f"  插入: {count:,} 条数据")

        start_idx = self.counts["initial"] + self.counts["batch_insert"] + self.counts["insert"]
        end_idx = start_idx + count
        X_insert = self._load_data_range(start_idx, end_idx)

        start_time = time.time()
        insert_latencies = []

        for i in range(count):
            point = X_insert[i : i + 1]
            point_id = start_idx + i

            insert_start = time.time()
            if hasattr(self.algo, "batch_add"):
                self.algo.batch_add(point, [point_id])
            else:
                self.algo.add(point[0], point_id)
            insert_latencies.append(time.time() - insert_start)

        elapsed = time.time() - start_time
        throughput = count / elapsed

        self.counts["insert"] += count
        self.maintenance_state.live_points += count
        self.attrs["latencyInsert"].extend(insert_latencies)

        print(f"  ✓ 插入完成: {elapsed:.2f}s, {throughput:.0f} ops/s")

    def _execute_delete(self, op: dict):
        """执行删除操作"""
        count = op.get("count", 100)
        print(f"  删除: {count:,} 条数据")

        # 从已有数据中选择要删除的 ID
        total_points = self.counts["initial"] + self.counts["batch_insert"] + self.counts["insert"]
        if count > total_points:
            count = total_points
            print(f"  ⚠️  删除数量超过现有数据量，调整为 {count}")

        # 随机选择要删除的 ID
        delete_ids = np.random.choice(total_points, size=count, replace=False)

        start_time = time.time()
        delete_latencies = []

        for del_id in delete_ids:
            del_start = time.time()
            if hasattr(self.algo, "batch_delete"):
                self.algo.batch_delete([int(del_id)])
            elif hasattr(self.algo, "delete"):
                self.algo.delete(int(del_id))
            delete_latencies.append(time.time() - del_start)

        elapsed = time.time() - start_time
        throughput = count / elapsed

        self.counts["delete"] += count
        self.maintenance_state.deleted_points += count
        self.maintenance_state.live_points -= count
        self.attrs["latencyDelete"].extend(delete_latencies)

        # 检查是否需要触发维护
        deletion_ratio = self.maintenance_state.get_deletion_ratio()
        print(f"  ✓ 删除完成: {elapsed:.2f}s, {throughput:.0f} ops/s")
        print(f"    删除比例: {deletion_ratio:.2%}")

        if self.maintenance_policy.should_rebuild(self.maintenance_state):
            print(f"  ⚠️  达到维护触发阈值 ({self.maintenance_policy.deletion_ratio_trigger:.1%})")

    def _execute_search(self, op: dict):
        """
        执行搜索性能测试

        注意：在流式场景下，不依赖静态GT文件
        GT文件应该预先计算并存储在 raw_data/{dataset}/{max_pts}/{runbook}/ 目录下
        如果需要计算recall，应该在后处理阶段进行

        实现方式：
        1. 一次性批量查询所有查询向量（类似 batch_insert 中的连续查询）
        2. 只记录一次总延迟（整个批次的查询时间）
        3. P50/P95/P99 延迟是基于 batch_insert 过程中的周期性查询计算的
        """
        count = op.get("count", self.dataset.nq)
        queries = self.dataset.get_queries()

        if count > len(queries):
            count = len(queries)
        elif count < len(queries):
            queries = queries[:count]

        print(f"  执行查询: {count:,} 次（批量）")

        start_time = time.time()

        # 一次性批量查询所有向量
        # Cache profiling 在 worker.query() 中进行
        try:
            results = self.algo.query(queries, self.k)

            # 处理返回值格式
            if isinstance(results, tuple):
                results = results[0]
            else:
                pass

            query_latency = time.time() - start_time

            # 存储结果用于后处理
            if results is not None and len(results) > 0:
                for i in range(len(results)):
                    self.all_results.append(results[i])
                    self.result_map[i] = self.counts["search"]
            else:
                # 索引为空或查询失败，记录空结果
                print("    ⚠️  查询返回空结果")
                for i in range(count):
                    empty_result = np.full(self.k, -1, dtype=np.int32)
                    self.all_results.append(empty_result)
                    self.result_map[i] = self.counts["search"]

        except Exception as e:
            print(f"    ❌ 查询异常: {type(e).__name__}: {str(e)}")
            query_latency = time.time() - start_time
            # 发生异常时记录空结果
            for i in range(count):
                empty_result = np.full(self.k, -1, dtype=np.int32)
                self.all_results.append(empty_result)
                self.result_map[i] = self.counts["search"]

        throughput = count / query_latency if query_latency > 0 else 0

        self.counts["search"] += count
        # 记录一次批量查询的总延迟（秒）
        self.attrs["latencyQuery"].append(query_latency)

        # 收集查询的cache统计（如果有worker且启用了cache profiling）
        # search操作的cache统计也追加到query_cache_miss_per_batch（与连续查询合并）
        if self.use_worker and self.worker and hasattr(self.worker, "query_cache_stats_list"):
            # 获取从上次收集后新增的cache统计
            current_count = len(self.worker.query_cache_stats_list)
            last_collected_count = getattr(self, "_last_collected_query_cache_count", 0)

            if current_count > last_collected_count:
                # 只收集新增的统计
                new_stats = self.worker.query_cache_stats_list[last_collected_count:]
                for cache_stat in new_stats:
                    self.metrics.query_cache_miss_per_batch.append(cache_stat.cache_misses)
                    self.metrics.query_cache_references_per_batch.append(
                        cache_stat.cache_references
                    )
                    self.metrics.query_cache_miss_rate_per_batch.append(cache_stat.cache_miss_rate)

                # 更新已收集计数
                self._last_collected_query_cache_count = current_count

                # 输出最新一次的cache统计
                if new_stats:
                    latest_cache_stat = new_stats[-1]
                    print(
                        f"    查询 Cache miss: {latest_cache_stat.cache_misses:,.0f}, "
                        f"miss率: {latest_cache_stat.cache_miss_rate:.2%}"
                    )

        # 输出统计信息
        avg_latency_per_query = (query_latency * 1000) / count  # 每个查询的平均延迟（毫秒）

        print(f"  ✓ 查询完成: {query_latency:.2f}s, {throughput:.0f} qps")
        print(
            f"    总延迟: {query_latency * 1000:.2f}ms, 平均每query: {avg_latency_per_query:.4f}ms"
        )

    def _execute_maintenance_rebuild(self, op: dict):
        """执行索引重建维护"""
        print("  执行索引重建")

        budget_us = op.get("budget_us", self.maintenance_policy.budget_us)
        if budget_us:
            print(f"    维护预算: {budget_us / 1e6:.2f}s")

        rebuild_start = time.time()

        # 使用辅助函数执行重建
        success = perform_controlled_rebuild(self.algo, self.dataset, self.counts, budget_us)

        rebuild_elapsed = time.time() - rebuild_start

        if success:
            # 更新维护状态
            self.maintenance_state.deleted_points = 0
            self.maintenance_state.last_rebuild_time = time.time()
            self.maintenance_state.rebuild_count += 1

            self.counts["maintenance_rebuild"] += 1
            self.attrs["maintenanceLatency"] = rebuild_elapsed
            self.attrs["maintenanceRebuilds"] += 1
            self.attrs["maintenanceBudgetUsed"] += rebuild_elapsed * 1e6

            event = {
                "time": time.time(),
                "duration_us": rebuild_elapsed * 1e6,
                "deletion_ratio": self.maintenance_state.get_deletion_ratio(),
                "live_points": self.maintenance_state.live_points,
            }
            self.attrs["maintenanceEvents"].append(event)

            print(f"  ✓ 重建完成: {rebuild_elapsed:.2f}s")
        else:
            print("  ✗ 重建失败或超预算")

    def _wait_pending(self):
        """等待待处理操作完成（用于工作线程模式）"""
        if self.use_worker and self.worker:
            print("  等待 Worker 处理待处理操作...")
            self.worker.waitPendingOperations()
            print("  ✓ 待处理操作完成")
        else:
            print("  ✓ 无待处理操作（未使用 Worker）")

    def _stop_workers(self):
        """停止工作线程"""
        if self.use_worker and self.worker and self._hpc_active:
            print("  停止 Worker 线程...")
            self.worker.endHPC()
            self.worker.join_thread()
            self._hpc_active = False

            # 输出丢弃统计
            if hasattr(self.worker, "drop_count_total") and self.worker.drop_count_total > 0:
                print(f"  ⚠️  总丢弃数据: {self.worker.drop_count_total:,} 条")
        print("  ✓ 工作线程已停止")

    def _calculate_recall(self, results: np.ndarray, groundtruth: np.ndarray) -> float:
        """计算召回率"""
        correct = len(set(results) & set(groundtruth))
        return correct / len(groundtruth)

    def _finalize_metrics(self):
        """汇总最终指标"""
        self.attrs["totalTime"] = sum(
            [
                np.sum(self.attrs["latencyInsert"]) if self.attrs["latencyInsert"] else 0,
                np.sum(self.attrs["latencyQuery"]) if self.attrs["latencyQuery"] else 0,
                np.sum(self.attrs["latencyDelete"]) if self.attrs["latencyDelete"] else 0,
                self.attrs["maintenanceLatency"],
            ]
        )

        # 更新 metrics - 填充关键字段以便计算指标
        self.metrics.attrs = self.attrs.copy()
        self.metrics.best_search_time = (
            np.mean(self.attrs["latencyQuery"]) if self.attrs["latencyQuery"] else 0
        )
        self.metrics.insert_time = (
            np.mean(self.attrs["latencyInsert"]) if self.attrs["latencyInsert"] else 0
        )
        self.metrics.query_argument_groups = []
        self.metrics.run_count = 1

        # 填充 latency_query 列表（转换为微秒）
        # 注意：latencyQuery 现在存储的是批量查询的总延迟（秒）
        if self.attrs["latencyQuery"]:
            self.metrics.latency_query = [lat * 1e6 for lat in self.attrs["latencyQuery"]]

        # 填充 continuous_query_latencies（周期性查询延迟，秒）
        # 用于计算 P50/P95/P99 延迟
        if "continuousQueryLatencies" in self.attrs and self.attrs["continuousQueryLatencies"]:
            self.metrics.continuous_query_latencies = [self.attrs["continuousQueryLatencies"]]
            # 设置每次批量查询的查询数量（用于计算单个查询的延迟）
            self.metrics.queries_per_continuous_query = self.dataset.nq

        # 填充 latency_insert 列表（转换为微秒）
        if self.attrs["latencyInsert"]:
            self.metrics.latency_insert = [lat * 1e6 for lat in self.attrs["latencyInsert"]]

        # 填充 insert_throughput（优先使用 batchinsertThroughtput）
        if "batchinsertThroughtput" in self.attrs and self.attrs["batchinsertThroughtput"]:
            self.metrics.insert_throughput = self.attrs["batchinsertThroughtput"]
        elif "insertThroughput" in self.attrs and self.attrs["insertThroughput"]:
            self.metrics.insert_throughput = self.attrs["insertThroughput"]

        # 填充 total_time（微秒）
        self.metrics.total_time = self.attrs["totalTime"]

        # 填充 num_searches
        self.metrics.num_searches = self.counts.get("search", 0)

    # ========== 向后兼容的旧版 API ==========

    def run(self, runbook: dict) -> BenchmarkMetrics:
        """
        向后兼容的运行接口，委托给 run_runbook

        Args:
            runbook: 操作定义字典

        Returns:
            BenchmarkMetrics: 测评指标
        """
        return self.run_runbook(runbook)

    def run_streaming_benchmark(
        self,
        initial_size: int,
        batch_size: int,
        num_batches: int,
        query_interval: int = 1000,
        enable_maintenance: bool = True,
    ) -> BenchmarkMetrics:
        """
        运行流式插入测评（向后兼容接口）

        Args:
            initial_size: 初始数据量
            batch_size: 每批次插入数据量
            num_batches: 批次数量
            query_interval: 查询间隔（每插入多少条数据执行一次查询）
            enable_maintenance: 是否启用维护

        Returns:
            BenchmarkMetrics: 测评指标
        """
        runbook = {
            "operations": [
                {"operation": "initial", "data_size": initial_size},
            ]
        }

        # 添加批次插入
        for i in range(num_batches):
            runbook["operations"].append(
                {
                    "operation": "batch_insert",
                    "count": batch_size,
                    "continuous_query_interval": query_interval,
                    "timestamp_file": f"batch_{i}_timestamps.csv",
                }
            )

            # 添加搜索测试
            runbook["operations"].append({"operation": "search", "count": 100})

            # 添加维护（如果启用）
            if enable_maintenance and (i + 1) % 5 == 0:
                runbook["operations"].append({"operation": "maintenance_rebuild"})

        return self.run_runbook(runbook)
