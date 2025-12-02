"""
Worker Thread for Congestion Drop Logic

实现工作线程，处理索引的插入、删除、查询操作
基于 big-ann-benchmarks/neurips23/congestion/base.py 的设计
"""

import random
import time
from threading import Lock, Thread
from typing import Optional

import numpy as np

# 尝试导入 PyCANDY 的工具类，如果失败则使用备用实现
try:
    from PyCANDYAlgo.utils import IdxQueue, NumpyIdxPair, NumpyIdxQueue  # type: ignore

    PYCANDY_AVAILABLE = True
except (ModuleNotFoundError, ImportError):
    PYCANDY_AVAILABLE = False
    import collections

    class NumpyIdxPair:
        """向量和索引对"""

        def __init__(self, vectors, idx):
            self.vectors = vectors
            self.idx = idx

    class _BaseQueue:
        """基础队列实现"""

        def __init__(self, cap: int = 10):
            self._dq = collections.deque()
            self._cap = int(cap)

        def capacity(self) -> int:
            return self._cap

        def size(self) -> int:
            return len(self._dq)

        def empty(self) -> bool:
            return not self._dq

        def front(self):
            return self._dq[0]

        def pop(self):
            self._dq.popleft()

        def push(self, item):
            self._dq.append(item)

    class NumpyIdxQueue(_BaseQueue):
        """向量队列"""

        pass

    class IdxQueue(_BaseQueue):
        """索引队列"""

        pass


def bind_to_core(core_id: int) -> int:
    """
    绑定线程到指定 CPU 核心

    Args:
        core_id: 核心 ID，-1 表示使用操作系统调度

    Returns:
        绑定的核心 ID，-1 表示未绑定
    """
    if core_id == -1:
        return -1

    try:
        import os

        max_cpus = os.cpu_count()
        if max_cpus is None:
            return -1
        cpu_id = core_id % max_cpus
        os.sched_setaffinity(os.getpid(), {cpu_id})
        return cpu_id
    except (AttributeError, ImportError, OSError):
        # sched_setaffinity 不可用或权限不足
        return -1


class AbstractThread:
    """
    线程基类和抽象
    """

    def __init__(self):
        self.thread: Optional[Thread] = None

    def inline_main(self):
        """主循环，子类需要实现"""
        pass

    def start_thread(self):
        """启动线程"""
        self.thread = Thread(target=self.inline_main)
        self.thread.start()

    def join_thread(self):
        """等待线程结束"""
        if self.thread:
            self.thread.join()


class CongestionDropWorker(AbstractThread):
    """
    并行索引工作线程，一次处理一个批次的插入、查询和删除
    支持拥塞丢弃逻辑
    """

    def __init__(self, my_index_algo, cache_profiler=None):
        """
        Args:
            my_index_algo: 底层索引算法实例
            cache_profiler: CacheProfiler实例（可选）
        """
        super().__init__()

        # 操作队列
        self.insert_queue = NumpyIdxQueue(10)
        self.initial_load_queue = NumpyIdxQueue(10)
        self.delete_queue = NumpyIdxQueue(10)
        self.query_queue = NumpyIdxQueue(10)
        self.cmd_queue = IdxQueue(10)

        # Worker 标识和配置
        self.my_id = 0
        self.vec_dim = 0
        self.congestion_drop = True
        self.ingested_vectors = 0
        self.single_worker_opt = True

        # 互斥锁
        self.m_mut = Lock()

        # 底层索引算法
        self.my_index_algo = my_index_algo

        # 场景控制
        self.random_contamination = False
        self.random_drop = False
        self.random_drop_prob = 0.0
        self.random_contamination_prob = 0.0
        self.out_of_order = False

        # 统计
        self.drop_count_total = 0

        # 时间戳追踪（用于计算真实处理延迟）
        self.batch_timestamps = []  # 存储 (batch_id, arrival_time, processed_time)
        self.query_timestamps = []  # 存储查询时间：[{total_time, lock_wait_time, query_time}, ...]
        self.benchmark_start_time = None  # 基准开始时间
        self.pair_timestamps = {}  # 字典：pair 内存地址 -> (arrival_time, batch_id)

        # 队列容量
        self.insert_queue_capacity = self.insert_queue.capacity()
        self.initial_load_queue_capacity = self.initial_load_queue.capacity()
        self.delete_queue_capacity = self.delete_queue.capacity()
        self.query_queue_capacity = self.query_queue.capacity()
        self.cmd_queue_capacity = self.cmd_queue.capacity()

        # 背压逻辑开关
        self.use_backpressure_logic = False

        # Cache profiler（可选）
        self.cache_profiler = cache_profiler
        self.cache_stats_list = []  # 存储每个批次插入的cache统计
        self.query_cache_stats_list = []  # 存储每次查询的cache统计

    def setup(self, dtype: str, max_pts: int, ndim: int) -> None:
        """
        初始化索引

        Args:
            dtype: 数据类型
            max_pts: 最大点数
            ndim: 向量维度
        """
        self.vec_dim = ndim
        self.my_index_algo.setup(dtype, max_pts, ndim)

    def inline_main(self) -> None:
        """
        工作线程主循环
        处理四个阶段：初始加载、插入、删除、终止命令
        """
        print(f"Worker {self.my_id}: Starting main thread logic.")
        should_loop = True
        query_seq = 0
        bind_to_core(self.my_id)

        while should_loop:
            # 1. 初始加载阶段
            # 使用非阻塞获取锁，避免死锁
            while not self.m_mut.acquire(blocking=False):
                pass

            initial_vectors = []
            initial_ids = []
            while not self.initial_load_queue.empty():
                pair = self.initial_load_queue.front()
                self.initial_load_queue.pop()
                initial_vectors.append(pair.vectors)
                initial_ids.append(pair.idx)

            if len(initial_vectors) > 0:
                initial_vectors = np.vstack(initial_vectors)
                initial_ids = np.vstack(initial_ids)
                self.my_index_algo.insert(initial_vectors, initial_ids)

            # 初始化完成后释放锁
            self.m_mut.release()

            # 2. 插入阶段 - 插入前获取锁
            while not self.m_mut.acquire(blocking=False):
                pass

            while not self.insert_queue.empty():
                pair = self.insert_queue.front()
                self.insert_queue.pop()

                # 使用字典查找时间戳信息
                pair_id = id(pair)
                timestamp_info = self.pair_timestamps.pop(pair_id, None)

                if timestamp_info:
                    arrival_time, batch_id = timestamp_info
                else:
                    arrival_time = None
                    batch_id = None

                # 记录索引插入开始时间（用于测量纯索引操作时间）
                insert_start_time = None
                if arrival_time is not None and self.benchmark_start_time is not None:
                    insert_start_time = time.time()

                # 启动 cache profiling（如果启用）
                cache_profiler_started = False
                if self.cache_profiler:
                    cache_profiler_started = self.cache_profiler.start()

                # 执行真正的索引插入
                self.my_index_algo.insert(pair.vectors, np.array(pair.idx))
                self.ingested_vectors += pair.vectors.shape[0]

                # 停止 cache profiling 并记录统计数据
                if cache_profiler_started:
                    cache_stats = self.cache_profiler.stop()
                    if cache_stats:
                        self.cache_stats_list.append(cache_stats)
                    else:
                        # 如果获取失败，记录空统计
                        from .cache_profiler import CacheMissStats

                        self.cache_stats_list.append(CacheMissStats())

                # 记录处理完成时间（如果有到达时间戳）
                if arrival_time is not None and self.benchmark_start_time is not None:
                    processed_time = (time.time() - self.benchmark_start_time) * 1e6  # 微秒
                    insert_duration = (
                        time.time() - insert_start_time
                    ) * 1e6  # 纯索引插入时间（微秒）

                    self.batch_timestamps.append(
                        {
                            "batch_id": batch_id,
                            "arrival_time": arrival_time,
                            "processed_time": processed_time,
                            "end_to_end_latency": processed_time
                            - arrival_time,  # 端到端延迟（含队列等待）
                            "insert_latency": insert_duration,  # 纯索引操作延迟
                            "queue_wait_time": (processed_time - arrival_time)
                            - insert_duration,  # 队列等待时间
                        }
                    )

            # 3. 删除阶段（继续持有锁）
            while not self.delete_queue.empty():
                pair = self.delete_queue.front()
                self.delete_queue.pop()
                self.my_index_algo.delete(np.array(pair.idx))

            # 删除完成后释放锁
            self.m_mut.release()

            # 4. 终止命令
            while not self.cmd_queue.empty():
                cmd = self.cmd_queue.front()
                self.cmd_queue.pop()
                if cmd == -1:
                    should_loop = False
                    print(f"parallel worker {self.my_id} terminates")
                    return

    def startHPC(self) -> bool:
        """启动高性能计算线程"""
        self.start_thread()
        return True

    def endHPC(self) -> bool:
        """结束高性能计算线程"""
        self.cmd_queue.push(-1)
        return False

    def set_id(self, id: int):
        """设置 worker ID"""
        self.my_id = id

    def waitPendingOperations(self) -> bool:
        """
        等待所有待处理的操作完成
        通过获取和释放锁来确保队列被处理
        """
        while not self.m_mut.acquire(blocking=False):
            pass
        self.m_mut.release()
        return True

    def reset_state(self, dtype: str, max_pts: int, ndim: int):
        """
        重置 worker 状态
        用于维护重建场景
        """
        self.insert_queue = NumpyIdxQueue(self.insert_queue_capacity)
        self.initial_load_queue = NumpyIdxQueue(self.initial_load_queue_capacity)
        self.delete_queue = NumpyIdxQueue(self.delete_queue_capacity)
        self.query_queue = NumpyIdxQueue(self.query_queue_capacity)
        self.cmd_queue = IdxQueue(self.cmd_queue_capacity)
        self.ingested_vectors = 0
        self.drop_count_total = 0
        self.vec_dim = ndim
        self.my_index_algo.setup(dtype, max_pts, ndim)

    def initial_load(self, X: np.ndarray, ids: np.ndarray):
        """
        初始数据加载
        在流式处理之前加载若干行数据

        Args:
            X: 向量数据 (n, d)
            ids: 向量 ID (n,)
        """
        if self.single_worker_opt:
            # 单 worker 优化：直接加载
            while not self.m_mut.acquire(blocking=False):
                pass
            self.my_index_algo.insert(X, ids)
            self.m_mut.release()

    def insert(self, X: np.ndarray, ids: np.ndarray, arrival_time: Optional[float] = None):
        """
        插入数据
        根据拥塞丢弃、随机丢弃、随机污染、乱序等策略处理数据

        Args:
            X: 向量数据
            ids: 向量 ID
            arrival_time: 到达时间（微秒），用于时间戳追踪

        注意：arrival_time 会被存储到 pair 中，在 worker 线程处理时记录 processed_time
        """

        def _record_drop(ids_arr):
            try:
                dropped = len(ids_arr)
            except TypeError:
                dropped = 1
            self.drop_count_total += dropped

        # 1. 随机丢弃检查（最先执行）
        if self.random_drop and random.random() < self.random_drop_prob:
            _record_drop(ids)
            print(f"RANDOM DROPPING DATA {ids[0]}:{ids[-1]}")
            return

        # 2. 随机污染：将向量数据替换为随机值
        if self.random_contamination and random.random() < self.random_contamination_prob:
            print(f"RANDOM CONTAMINATION DATA {ids[0]}:{ids[-1]}")
            X = np.random.randn(*X.shape).astype(X.dtype)

        # 3. 拥塞丢弃检查
        if self.use_backpressure_logic:
            # 背压逻辑：基于队列容量
            queue_full = self.insert_queue.size() >= self.insert_queue_capacity
            if self.congestion_drop and queue_full:
                _record_drop(ids)
                print(f"DROPPING DATA {ids[0]}:{ids[-1]} (queue full)")
                return
        else:
            # 正常逻辑：仅在队列为空时接受
            if not self.insert_queue.empty() and self.congestion_drop:
                _record_drop(ids)
                print(f"DROPPING DATA {ids[0]}:{ids[-1]}")
                return

        # 4. 乱序处理：打乱数据和ID的顺序
        if self.out_of_order:
            length = X.shape[0]
            order = np.random.permutation(length)
            X = X[order]
            ids = ids[order]

        # 5. 创建 pair 并插入队列，使用字典存储时间戳信息
        pair = NumpyIdxPair(X, ids)
        if arrival_time is not None:
            batch_id = f"{ids[0]}-{ids[-1]}"
            # 使用 pair 的内存地址作为键存储时间戳
            self.pair_timestamps[id(pair)] = (arrival_time, batch_id)
        self.insert_queue.push(pair)

    def delete(self, ids: np.ndarray):
        """
        删除数据

        Args:
            ids: 要删除的向量 ID
        """
        if self.use_backpressure_logic:
            queue_full = self.delete_queue.size() >= self.delete_queue_capacity
            if self.congestion_drop and queue_full:
                print("Failed to process deletion! (queue full)")
                return
            self.delete_queue.push(NumpyIdxPair(np.array([0.0]), ids))
            return

        else:
            if self.delete_queue.empty() or (not self.congestion_drop):
                self.delete_queue.push(NumpyIdxPair(np.array([0.0]), ids))
            else:
                print("Failed to process deletion!")
            return

    def query(self, X: np.ndarray, k: int):
        """
        执行查询
        需要获取锁以避免与插入/删除操作冲突

        Args:
            X: 查询向量
            k: 返回的最近邻数量

        Returns:
            查询结果 (neighbors_ids, distances) 或 neighbors_ids
        """
        # 记录查询开始时间（包括锁等待）
        query_start = time.time()

        # 获取锁，确保查询时索引状态一致
        lock_acquire_start = time.time()
        while not self.m_mut.acquire(blocking=False):
            pass
        lock_wait_time = (time.time() - lock_acquire_start) * 1e6  # 微秒

        try:
            # 启动 cache profiling（如果启用）
            cache_profiler_started = False
            if self.cache_profiler:
                cache_profiler_started = self.cache_profiler.start()

            # 执行真正的查询
            query_exec_start = time.time()
            result = self.my_index_algo.query(X, k)
            query_exec_time = (time.time() - query_exec_start) * 1e6  # 微秒

            # 停止 cache profiling 并记录统计数据
            if cache_profiler_started:
                cache_stats = self.cache_profiler.stop()
                if cache_stats:
                    self.query_cache_stats_list.append(cache_stats)
                else:
                    # 如果获取失败，记录空统计
                    from .cache_profiler import CacheMissStats

                    self.query_cache_stats_list.append(CacheMissStats())

            self.res = self.my_index_algo.res

            # 记录查询时间统计
            total_time = (time.time() - query_start) * 1e6  # 微秒
            self.query_timestamps.append(
                {
                    "total_time": total_time,  # 总时间（包括锁等待）
                    "lock_wait_time": lock_wait_time,  # 锁等待时间
                    "query_time": query_exec_time,  # 纯查询时间
                }
            )

            return result  # 返回查询结果
        finally:
            self.m_mut.release()

    def enableScenario(
        self,
        random_contamination: bool = False,
        random_contamination_prob: float = 0.0,
        random_drop: bool = False,
        random_drop_prob: float = 0.0,
        out_of_order: bool = False,
    ):
        """
        启用特殊场景

        Args:
            random_contamination: 是否启用随机污染
            random_contamination_prob: 随机污染概率
            random_drop: 是否启用随机丢弃
            random_drop_prob: 随机丢弃概率
            out_of_order: 是否启用乱序摄入
        """
        self.random_drop_prob = random_drop_prob
        if random_drop_prob:
            print("Enabling random dropping!")
        self.random_drop = random_drop
        print(f"worker random drop prob {self.random_drop_prob}")

        self.random_contamination = random_contamination
        if random_contamination:
            print("Enabling random contamination!")
        self.random_contamination_prob = random_contamination_prob
        print(f"worker contamination prob {self.random_contamination_prob}")

        if out_of_order:
            print("Enabling outta order ingestion!")
        self.out_of_order = out_of_order

    def setBackpressureLogic(self, use_backpressure: bool = True):
        """
        设置背压逻辑

        Args:
            use_backpressure: True 使用队列容量判断，False 仅在队列为空时接受
        """
        self.use_backpressure_logic = use_backpressure
        if use_backpressure:
            print(f"Worker {self.my_id}: Using backpressure logic (queue capacity-based)")
        else:
            print(f"Worker {self.my_id}: Using normal logic (empty queue only)")
