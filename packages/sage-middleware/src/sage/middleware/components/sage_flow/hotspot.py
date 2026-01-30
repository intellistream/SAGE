from __future__ import annotations

import queue
import threading
import time
from typing import Any

import numpy as np

from sage.common.core.functions.comap_function import BaseCoMapFunction


class SageFlowHotspotPairCoMap(BaseCoMapFunction):
    """两个新闻流输入的热点 pair 生成器（基于 SageFlow join）。

    设计目标：
    - input stream0: 平台A新闻（doc流）
    - input stream1: 平台B新闻（doc流）
    - 输出：相似度 >= threshold 的跨平台新闻对（pair）

    输入数据格式（两边一致）：
    - id: int | str
    - embedding: list[float] | np.ndarray
    - text/title/url/...: 任意字段会透传到输出 pair 的 left/right 中

    输出数据格式：
    {
      "left": <原始左记录>,
      "right": <原始右记录>,
      "similarity": float,
      "event_time_ms": int
    }

    注意：
    - 这是一个 CoMapFunction，会被 SAGE runtime 的 CoMapOperator 根据 input_index 路由到 map0/map1。
    - 当前实现以“增量语义状态”为目标：持续把两侧 doc 写入 SageFlow 的两个 source，SageFlow runtime 维护索引/状态。
    """

    def __init__(
        self,
        dim: int,
        similarity_threshold: float = 0.85,
        join_method: str = "bruteforce_lazy",
        parallelism: int = 1,
        max_pairs_per_event: int = 128,
        window_size_ms: int = 10000,  # 窗口大小（毫秒），默认 10 秒
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.dim = dim
        self.similarity_threshold = similarity_threshold
        self.join_method = join_method
        self.parallelism = parallelism
        self.max_pairs_per_event = max_pairs_per_event
        self.window_size_ms = window_size_ms

        self._lock = threading.Lock()
        self._initialized = False
        self._executed = False  # 标记 sageflow 是否已启动执行

        self._env = None
        self._left_source = None
        self._right_source = None
        self._pipeline = None

        self._records_left: dict[int, dict[str, Any]] = {}
        self._records_right: dict[int, dict[str, Any]] = {}

        self._pair_queue: queue.Queue[dict[str, Any]] = queue.Queue()

    def _normalize_id(self, raw_id: Any, side: int) -> int:
        if raw_id is None:
            raw_id = 0
        if isinstance(raw_id, int):
            base = raw_id
        else:
            base = hash(str(raw_id)) % (2**31)
        # 避免左右两侧 id 冲突：做一个 side offset
        return base * 2 + side

    def _to_vec(self, embedding: Any) -> np.ndarray:
        if isinstance(embedding, np.ndarray):
            vec = embedding.astype(np.float32)
        else:
            vec = np.array(embedding, dtype=np.float32)
        return vec

    def _init_sageflow(self) -> None:
        if self._initialized:
            return

        from sage_flow import StreamEnvironment, StreamingSource

        self._env = StreamEnvironment()
        # 使用 StreamingSource 而非 SimpleStreamSource：
        # - SimpleStreamSource 是批处理源，execute() 后记录被一次性消费
        # - StreamingSource 支持动态流式输入，execute() 后可以持续 addRecord
        self._left_source = StreamingSource("hotspot_left", capacity=10000)
        self._right_source = StreamingSource("hotspot_right", capacity=10000)

        # join 回调：C++ 层完成相似度过滤（使用 exp(-alpha * L2_distance)）。
        # 回调只有满足阈值的 pair 才会被调用。
        # 我们在回调里构造热点 pair 并入队；sink 仅用于完成 pipeline 拓扑。
        #
        # 重要：C++ 和 Python 必须使用相同的相似度计算公式！
        # C++ 使用 sim = exp(-alpha * L2_distance)，alpha 默认为 0.1
        # 对于归一化向量，L2 距离范围是 [0, 2]，所以相似度范围是 [exp(-0.2), 1] ≈ [0.82, 1]
        # 使用更大的 alpha（如 5.0）可以获得更好的区分度

        # 与 C++ BruteForceBaseline 保持一致的相似度计算
        similarity_alpha = 5.0  # 与 bindings.cpp 中 JoinStrategyConfig 设置的 alpha 一致

        def compute_l2_similarity(
            vec_a: np.ndarray, vec_b: np.ndarray, alpha: float = 5.0
        ) -> float:
            """使用与 C++ 相同的公式计算相似度: sim = exp(-alpha * L2_distance)"""
            l2_dist = float(np.linalg.norm(vec_a - vec_b))
            return float(np.exp(-alpha * l2_dist))

        def on_join(l_uid, l_ts, l_vec, r_uid, r_ts, r_vec):
            left_uid = int(l_uid)
            right_uid = int(r_uid)
            ts = max(int(l_ts), int(r_ts))

            left_rec = self._records_left.get(left_uid)
            right_rec = self._records_right.get(right_uid)
            if left_rec is None or right_rec is None:
                return None

            # 使用与 C++ 相同的公式计算相似度
            l_vec_np = np.asarray(l_vec, dtype=np.float32)
            r_vec_np = np.asarray(r_vec, dtype=np.float32)
            similarity = compute_l2_similarity(l_vec_np, r_vec_np, similarity_alpha)

            self._pair_queue.put(
                {
                    "left": {k: v for k, v in left_rec.items() if k != "_vec"},
                    "right": {k: v for k, v in right_rec.items() if k != "_vec"},
                    "similarity": similarity,  # 使用与 C++ 一致的相似度
                    "event_time_ms": ts,
                }
            )

            # join 必须返回 (uid, ts, vec) 或 None。返回左向量占位即可。
            return (left_uid, ts, l_vec_np)

        # 使用完整的 7 参数版本 join()，包含 window_size_ms
        # 参数顺序：other, callback, dim, join_method, similarity_threshold, window_size_ms, parallelism
        self._pipeline = self._left_source.join(
            self._right_source,
            on_join,
            self.dim,  # dim
            self.join_method,  # join_method
            self.similarity_threshold,  # similarity_threshold
            self.window_size_ms,  # window_size_ms
            self.parallelism,  # parallelism
        )

        # pybind 签名：writeSink(sink_func, parallelism=1)
        # 不能额外传入 name 字符串参数
        self._pipeline.writeSink(lambda *args: None, parallelism=self.parallelism)

        self._env.addStream(self._left_source)
        self._env.addStream(self._right_source)

        self._initialized = True

    def _ensure_executing(self) -> None:
        """确保 sageflow 已启动执行（仅首次调用时启动）。"""
        if not self._executed:
            self._env.execute()
            self._executed = True

    def _push_left(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        emb = record.get("embedding")
        if emb is None:
            return []

        uid = self._normalize_id(record.get("id"), side=0)
        vec = self._to_vec(emb)

        now_ms = int(time.time() * 1000)
        with self._lock:
            self._init_sageflow()
            self._records_left[uid] = {**record, "id": uid, "_vec": vec}
            self._last_left_uid = uid
            print(f"[SageFlowHotspotPairCoMap] addRecord side=left uid={uid} ts_ms={now_ms}")
            self._ensure_executing()  # 确保已启动执行
            self._left_source.addRecord(uid, now_ms, vec)
            # 给 join 执行一点时间来处理
            time.sleep(0.01)

        return self._drain_pairs()

    def _push_right(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        emb = record.get("embedding")
        if emb is None:
            return []

        uid = self._normalize_id(record.get("id"), side=1)
        vec = self._to_vec(emb)

        now_ms = int(time.time() * 1000)
        with self._lock:
            self._init_sageflow()
            self._records_right[uid] = {**record, "id": uid, "_vec": vec}
            print(f"[SageFlowHotspotPairCoMap] addRecord side=right uid={uid} ts_ms={now_ms}")
            self._ensure_executing()  # 确保已启动执行
            self._right_source.addRecord(uid, now_ms, vec)
            # 给 join 执行一点时间来处理
            time.sleep(0.01)

        return self._drain_pairs()

    def _drain_pairs(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for _ in range(self.max_pairs_per_event):
            try:
                out.append(self._pair_queue.get_nowait())
            except queue.Empty:
                break
        return out

    def finish_and_drain_all(self) -> list[dict[str, Any]]:
        """结束 sageflow 流并等待所有 join 完成，收集全部剩余结果。"""
        if not self._initialized:
            return []

        with self._lock:
            # 标记两个流结束
            self._left_source.finish()
            self._right_source.finish()

        # 等待 sageflow 完成
        self._env.awaitTermination()

        # 收集所有剩余结果
        return self._drain_pairs()

    def map0(self, data: Any) -> Any:
        if not isinstance(data, dict):
            return None
        # 以 list 输出让下游用 flatmap 扩散
        return self._push_left(data)

    def map1(self, data: Any) -> Any:
        if not isinstance(data, dict):
            return None
        return self._push_right(data)
