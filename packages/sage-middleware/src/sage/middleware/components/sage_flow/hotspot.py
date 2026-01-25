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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.dim = dim
        self.similarity_threshold = similarity_threshold
        self.join_method = join_method
        self.parallelism = parallelism
        self.max_pairs_per_event = max_pairs_per_event

        self._lock = threading.Lock()
        self._initialized = False

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

        from sage_flow import SimpleStreamSource, StreamEnvironment

        self._env = StreamEnvironment()
        self._left_source = SimpleStreamSource("hotspot_left")
        self._right_source = SimpleStreamSource("hotspot_right")

        # 配置 join 参数（以 left 为 join 驱动）
        self._left_source.setJoinMethod(self.join_method)
        self._left_source.setJoinSimilarityThreshold(self.similarity_threshold)

        # join 回调：C++ 层完成相似度过滤；这里能拿到两侧 uid/ts/vec。
        # 我们在 join 回调里直接构造热点 pair 并入队；sink 仅用于完成 pipeline 拓扑。

        def on_join(l_uid, l_ts, _l_vec, r_uid, r_ts, _r_vec):
            left_uid = int(l_uid)
            right_uid = int(r_uid)
            ts = max(int(l_ts), int(r_ts))

            left_rec = self._records_left.get(left_uid)
            right_rec = self._records_right.get(right_uid)
            if left_rec is None or right_rec is None:
                return None

            left_vec2 = left_rec.get("_vec")
            right_vec2 = right_rec.get("_vec")
            if left_vec2 is None or right_vec2 is None:
                return None

            sim = float(
                np.dot(left_vec2, right_vec2)
                / (np.linalg.norm(left_vec2) * np.linalg.norm(right_vec2) + 1e-8)
            )

            self._pair_queue.put(
                {
                    "left": {k: v for k, v in left_rec.items() if k != "_vec"},
                    "right": {k: v for k, v in right_rec.items() if k != "_vec"},
                    "similarity": sim,
                    "event_time_ms": ts,
                }
            )

            # join 必须返回 (uid, ts, vec) 或 None。返回左向量占位即可。
            return (left_uid, ts, left_vec2)

        self._pipeline = self._left_source.join(
            self._right_source,
            on_join,
            dim=self.dim,
            parallelism=self.parallelism,
        )

        self._pipeline.writeSink("hotspot_pairs", lambda *args: None)

        self._env.addStream(self._left_source)
        self._env.addStream(self._right_source)

        self._initialized = True

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
            setattr(self, "_last_left_uid", uid)
            self._left_source.addRecord(uid, now_ms, vec)
            self._env.execute()

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
            self._right_source.addRecord(uid, now_ms, vec)
            self._env.execute()

        return self._drain_pairs()

    def _drain_pairs(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for _ in range(self.max_pairs_per_event):
            try:
                out.append(self._pair_queue.get_nowait())
            except queue.Empty:
                break
        return out

    def map0(self, data: Any) -> Any:
        if not isinstance(data, dict):
            return None
        # 以 list 输出让下游用 flatmap 扩散
        return self._push_left(data)

    def map1(self, data: Any) -> Any:
        if not isinstance(data, dict):
            return None
        return self._push_right(data)
