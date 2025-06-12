import pickle
import queue
import random
import threading
import time
from collections import deque
import sys


class MessageQueue:

    def __init__(self, name="MessageQueue", max_buffer_size=30000):
        self.max_buffer_size = max_buffer_size
        self.queue = queue.Queue(maxsize=10000)
        self.total_task = 0
        self.max_buffer_size = max_buffer_size  # 总内存限制（字节）
        self.current_buffer_usage = 0# 当前使用的内存（字节）
        self.memory_tracker = {}  # 跟踪每个项目的内存大小 {id(item): size}
        # self.task_per_minute = 0

        self.timestamps = deque()
        self.lock = threading.Lock()
        self.buffer_condition = threading.Condition(self.lock)  # 用于内存空间通知

    def _estimate_size(self, item):
        """估算项目的内存大小（字节）"""
        try:
            # 对于简单对象，直接使用getsizeof
            size = sys.getsizeof(item)
            # 对于复杂对象，可以尝试使用序列化方法估算
            if size < sys.getsizeof(object):
                return len(pickle.dumps(item))  # 使用pickle进行序列化
            return size
        except Exception as e:
            # 打印异常信息，避免静默失败
            print(f"错误: {e}")
            return 0

    def _trim_old(self, now, max_age):
        """清除超过 max_age 秒的历史时间戳"""
        while self.timestamps and (now - self.timestamps[0] > max_age):
            self.timestamps.popleft()

    def get_throughput(self, window_seconds=1.0):
        """
        返回指定时间窗口（秒）内的 put 次数（吞吐量）
        例如：window_seconds=0.1 获取最近 100ms 的吞吐量
        """
        now = time.time()
        with self.lock:
            self._trim_old(now, 60.0)  # 保留最多 60 秒
            return sum(1 for ts in self.timestamps if now - ts <= window_seconds)

    def qsize(self):
        """
        当前队列长度
        """
        return self.queue.qsize()

    def is_full(self):
        """
        队列是否满了
        """
        return self.current_buffer_usage >= self.max_buffer_size

    def is_empty(self):
        """
        队列是否为空
        """
        return self.queue.qsize() == 0

    def put(self, item, block=True, timeout=None):
        """
        将项目放入队列，并跟踪其内存使用情况
        如果超过内存限制，会根据block参数决定是否等待
        """
        # 估算项目大小
        item_size = self._estimate_size(item)

        if block:
            end_time = None if timeout is None else time.time() + timeout

            with self.buffer_condition:
                # 等待直到有足够的空间
                while self.current_buffer_usage + item_size > self.max_buffer_size:
                    if timeout is None:
                        self.buffer_condition.wait()
                    else:
                        remaining = end_time - time.time()
                        if remaining <= 0:
                            raise queue.Full("Memory limit exceeded - timeout")
                        self.buffer_condition.wait(remaining)

                # 更新内存使用量并添加项目
                self._do_put(item, item_size)
        else:
            with self.lock:
                # 立即检查是否可以添加
                if self.current_buffer_usage + item_size > self.max_buffer_size:
                    raise queue.Full("Memory limit exceeded")
                self._do_put(item, item_size)

    def _do_put(self, item, item_size):
        """内部方法：实际执行添加项目和更新内存追踪的操作"""
        now = time.time()

        # 将项目放入队列
        self.queue.put(item)

        # 更新内存追踪
        item_id = id(item)
        self.memory_tracker[item_id] = item_size
        self.current_buffer_usage += item_size

        # 更新统计数据
        self.total_task += 1
        self.timestamps.append(now)
        self._trim_old(now, 60.0)

    def get(self, block=True, timeout=0.1):
        """
        从队列中取数据；如果队列为空，会根据 block 和 timeout 参数决定是否阻塞
        """
        try:
            # 从队列中取出项目
            item = self.queue.get(block=block, timeout=timeout)
            # 更新内存追踪
            with self.buffer_condition:
                item_id = id(item)
                if item_id in self.memory_tracker:
                    # 减少当前内存使用量
                    self.current_buffer_usage -= self.memory_tracker[item_id]
                    # 从内存追踪器中移除该项目
                    del self.memory_tracker[item_id]
                    # 通知等待中的生产者有可用空间
                    self.buffer_condition.notify_all()

            return item
        except queue.Empty:
            return None
    def metrics(self):
        """
        返回 JSON 风格的实时状态信息：
        - 当前队列长度
        - 是否满/空
        - 不同时间窗口内的吞吐量（0.1s、1s、60s）
        - 内存使用情况
        """
        now = time.time()
        with self.lock:
            self._trim_old(now, 60.0)
            return {
                "queue_size": self.qsize(),
                "is_full": self.is_full(),
                "is_empty": self.is_empty(),
                "throughput_0.1s": sum(1 for ts in self.timestamps if now - ts <= 0.1),
                "throughput_1s": sum(1 for ts in self.timestamps if now - ts <= 1.0),
                "throughput_60s": len(self.timestamps),
                # 添加以下内存相关的指标
                "memory_usage_bytes": self.current_buffer_usage,
                "memory_usage_percent": (
                                                    self.current_buffer_usage / self.max_buffer_size) * 100 if self.max_buffer_size > 0 else 0,
                "memory_limit_bytes": self.max_buffer_size
            }


