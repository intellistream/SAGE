import queue
import random
import threading
import time
from collections import deque


class FlowQueue:

    def __init__(self, name="FlowQueue", maxsize=0):
        self.name = name
        self.maxsize = maxsize
        self.queue = queue.Queue(maxsize)
        self.total_task = 0
        # self.task_per_minute = 0

        self.timestamps = deque()
        self.lock = threading.Lock()

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
        return self.queue.qsize() >= self.maxsize

    def is_empty(self):
        """
        队列是否为空
        """
        return self.queue.qsize() == 0

    def put(self, item):
        self.queue.put(item)
        now = time.time()
        self.total_task = self.total_task + 1
        with self.lock:
            self.timestamps.append(now)
            self._trim_old(now, 60.0)

    def get(self):
        """
        从队列中取数据；如果队列为空，会阻塞
        """
        return self.queue.get()

    def metrics(self):
        """
        返回 JSON 风格的实时状态信息：
        - 当前队列长度
        - 是否满/空
        - 不同时间窗口内的吞吐量（0.1s、1s、60s）
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
                "throughput_60s": len(self.timestamps)
            }


def _test():
    def producer(_queue: FlowQueue):
        for i in range(100):
            _queue.put(f"data-{i}")
            print(f"[Producer] Sent: data-{i}")
            time.sleep(random.uniform(0.01, 0.05))

    def consumer(_queue: FlowQueue, name: str):
        while True:
            item = _queue.get()
            print(f"[{name}] Got: {item}")
            time.sleep(random.uniform(0.05, 0.1))

    def monitor(_queue: FlowQueue):
        while True:
            count = _queue.get_throughput()
            print(f"[Monitor] Tasks in last 60s: {count}")
            time.sleep(0.5)

    # 启动线程
    q = FlowQueue(maxsize=1000)

    threading.Thread(target=producer, args=(q,), daemon=True).start()
    threading.Thread(target=consumer, args=(q, "Worker-1"), daemon=True).start()
    threading.Thread(target=consumer, args=(q, "Worker-2"), daemon=True).start()
    threading.Thread(target=monitor, args=(q,), daemon=True).start()

    # 主线程保持运行
    while True:
        time.sleep(1)


if __name__ == '__main__':
    _test()
