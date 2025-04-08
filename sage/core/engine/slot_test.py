from sage.core.engine.slot import Slot
import time
import threading
import logging
from concurrent.futures import Future


class TestTask:
    """模拟任务类"""

    def __init__(self, name, duration=0):
        self.name = name
        self.duration = duration
        self.stop_called = False
        self.stop_event = threading.Event()
    def run(self):
        cnt=0
        while not self.stop_event.is_set():
            time.sleep(self.duration)
            if cnt%5 == 0 :
                print(f"{self.name} loop {cnt} times")
            cnt+=1

    def stop(self):
        self.stop_event.set()


class TestSlot():
    def __init__(self):
        self.slot = Slot("test_slot", max_threads=2)
        self.task1 = TestTask("task1", duration=0.1)
        self.task2 = TestTask("task2", duration=0.2)
        self.task3 = TestTask("task3", duration=0.3)

    def tearDown(self):
        self.slot.shutdown()

    def test_submit_task_within_capacity(self):
        # 测试正常提交任务
        self.slot.submit_task(self.task1)
        if not self.slot.current_load == 1 :
            raise RuntimeError("current load not equal to 1")
        self.slot.submit_task(self.task2)
        if not self.slot.current_load == 2 :
            raise RuntimeError("current load not equal to 2")
        time.sleep(3)
        self.slot.shutdown()
        if not self.slot.current_load == 0 :
            raise RuntimeError("current load not equal to 0")

    def test_submit_task_exceed_capacity(self):
        # 测试超过容量时提交失败
        self.slot.submit_task(self.task1)
        self.slot.submit_task(self.task2)
        self.slot.submit_task(self.task3)
        if not self.slot.current_load == 2 :
            raise RuntimeError("current load not equal to 2")
        time.sleep(3)
        self.slot.shutdown()

    def test_stop_running_task(self):
        # 测试停止正在运行的任务
        self.slot.submit_task(self.task3)  # 0.3秒任务
        time.sleep(3)  # 确保任务已经开始

        future = self.slot.task_to_future[self.task3]
        if future.running():
            print("task is running")
        self.slot.stop(self.task3)
        future.result()
        if future.done() :
            print("task is done")

    def test_stop_pending_task(self):
        # 测试取消未开始的任务
        self.slot.submit_task(self.task1)
        self.slot.submit_task(self.task2)
        self.slot.submit_task(self.task3)  # 会被拒绝，因为容量为2





