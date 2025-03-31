import unittest
import threading
import random
import time
import queue
import sys
from .message_queue import MessageQueue


class TestMessageQueue(unittest.TestCase):
    """MessageQueue 组件的单元测试类"""

    def setUp(self):
        """每个测试前的初始化"""
        # 创建一个内存限制较小的队列 (5MB)，便于测试内存限制功能
        self.mq = MessageQueue(max_buffer_size=5 * 1024 * 1024)  # 5MB
        self.stop_event = threading.Event()
        self.test_results = {
            "put_counts": [],  # 每个生产者的put成功次数
            "get_counts": [],  # 每个消费者的get成功次数
            "blocked_counts": [],  # 每个生产者被阻塞次数
            "throughput_data": []  # 记录的吞吐量样本和实际值的比较
        }

    def producer(self, producer_id, stop_event, data_size_range, speed):
        """
        生产者函数 - 可配置数据大小和速度

        :param producer_id: 生产者ID
        :param stop_event: 停止事件
        :param data_size_range: (min_kb, max_kb) 数据大小范围
        :param speed: 每秒尝试放入数据的次数
        """
        count = 0
        blocked = 0
        min_kb, max_kb = data_size_range

        try:
            while not stop_event.is_set():
                size_kb = random.randint(min_kb, max_kb)
                data = "X" * (size_kb * 1024)

                try:
                    start_time = time.time()
                    # 尝试放入队列，使用阻塞模式，超时3秒
                    self.mq.put(data, timeout=3)
                    print(f"[生产者-{producer_id}] 成功放入 {size_kb}KB 数据")
                    count += 1

                    # 根据指定速度控制生产频率
                    elapsed = time.time() - start_time
                    sleep_time = max(0, 1.0 / speed - elapsed)
                    time.sleep(sleep_time)

                except queue.Full:
                    blocked += 1
                    print(f"[生产者-{producer_id}] 阻塞超时，队列仍满")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"[生产者-{producer_id}] 错误: {e}")
                    time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.test_results["put_counts"].append(count)
            self.test_results["blocked_counts"].append(blocked)
            print(f"[生产者-{producer_id}] 结束: 成功放入{count}个项目，被阻塞{blocked}次")

    def consumer(self, consumer_id, stop_event, speed):
        """
        消费者函数

        :param consumer_id: 消费者ID
        :param stop_event: 停止事件
        :param speed: 每秒尝试获取数据的最大次数
        """
        count = 0
        total_size = 0

        try:
            while not stop_event.is_set():
                try:
                    start_time = time.time()
                    item = self.mq.get()
                    size_kb = len(item) // 1024
                    count += 1
                    total_size += size_kb

                    print(f"[消费者-{consumer_id}] 获取第{count}个数据项，大小: {size_kb}KB")

                    # 控制消费速度
                    elapsed = time.time() - start_time
                    sleep_time = max(0, 1.0 / speed - elapsed)
                    time.sleep(sleep_time)

                except Exception as e:
                    print(f"[消费者-{consumer_id}] 错误: {e}")
                    time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.test_results["get_counts"].append(count)
            print(f"[消费者-{consumer_id}] 结束: 成功获取{count}个项目，总大小约{total_size / 1024:.2f}MB")

    def test_basic_functionality(self):
        """测试消息队列的基本功能"""
        # 测试初始状态
        self.assertEqual(self.mq.qsize(), 0)
        self.assertTrue(self.mq.is_empty())
        self.assertFalse(self.mq.is_full())

        # 测试简单的put和get
        test_data = "测试数据" * 1000
        self.mq.put(test_data)
        self.assertEqual(self.mq.qsize(), 1)
        self.assertFalse(self.mq.is_empty())

        retrieved_data = self.mq.get()
        self.assertEqual(retrieved_data, test_data)
        self.assertEqual(self.mq.qsize(), 0)

        # 测试吞吐量计算
        self.mq.put(test_data)
        throughput = self.mq.get_throughput(window_seconds=1.0)
        self.assertGreaterEqual(throughput, 1)

        # 测试内存估算
        size = self.mq._estimate_size(test_data)
        self.assertGreater(size, 0)

    def test_memory_limit_blocking(self):
        """测试内存限制和阻塞行为"""
        # 使用较小的内存限制进行测试
        small_queue = MessageQueue(max_buffer_size=1 * 1024 * 1024)  # 1MB

        # 生成一个接近但小于内存限制的数据项
        data1 = "X" * (900 * 1024)  # 900KB

        # 第一个项目应该能成功放入
        small_queue.put(data1, block=False)
        self.assertEqual(small_queue.qsize(), 1)

        # 尝试放入另一个接近限制的数据项，应该失败
        data2 = "Y" * (200 * 1024)  # 200KB
        with self.assertRaises(queue.Full):
            small_queue.put(data2, block=False)

        # 测试非阻塞行为
        def timed_put():
            try:
                small_queue.put(data2, timeout=0.5)
                return True
            except queue.Full:
                return False

        # 应该超时
        self.assertFalse(timed_put())

        # 移除第一个项目后，第二个应该能放入
        small_queue.get()
        self.assertTrue(timed_put())

    def test_metrics(self):
        """测试指标收集功能"""
        # 添加一些测试数据
        for i in range(5):
            self.mq.put(f"测试数据-{i}" * 1000)

        # 获取指标数据
        metrics = self.mq.metrics()

        # 验证指标数据的完整性
        self.assertEqual(metrics["queue_size"], 5)
        self.assertFalse(metrics["is_empty"])
        self.assertIn("throughput_1s", metrics)
        self.assertIn("memory_usage_bytes", metrics)
        self.assertIn("memory_usage_percent", metrics)

        # 验证吞吐量数据
        self.assertGreaterEqual(metrics["throughput_1s"], 5)

    def test_multi_producer_consumer(self):
        """测试多生产者消费者并发场景"""
        producer_configs = [
            (1, (100, 200), 10),  # ID=1, 小数据(100-200KB), 较快速度(10/秒)
            (2, (1000, 1500), 2),  # ID=2, 大数据(1-1.5MB), 较慢速度(2/秒)
            (3, (300, 700), 5)  # ID=3, 中等数据(300-700KB), 中等速度(5/秒)
        ]

        consumer_configs = [
            (1, 3),  # ID=1, 慢速(3/秒)
            (2, 8)  # ID=2, 快速(8/秒)
        ]

        threads = []
        for p_id, size_range, speed in producer_configs:
            t = threading.Thread(
                target=self.producer,
                args=(p_id, self.stop_event, size_range, speed),
                daemon=True
            )
            t.start()
            threads.append(t)

        for c_id, speed in consumer_configs:
            t = threading.Thread(
                target=self.consumer,
                args=(c_id, self.stop_event, speed),
                daemon=True
            )
            t.start()
            threads.append(t)

        # 运行30秒
        time.sleep(30)

        # 停止所有线程
        self.stop_event.set()
        for t in threads:
            t.join(timeout=2)

        # 测试结果分析
        total_produced = sum(self.test_results["put_counts"])
        total_consumed = sum(self.test_results["get_counts"])
        total_blocked = sum(self.test_results["blocked_counts"])

        # 检查生产者和消费者统计
        self.assertGreater(total_produced, 0, "生产者没有成功放入数据")
        self.assertGreater(total_consumed, 0, "消费者没有成功获取数据")
        self.assertLess(total_blocked, 10, "生产者被阻塞次数过多")

    def test_throughput_accuracy(self):
        """测试吞吐量计算的准确性"""

        def throughput_validator(stop_event, interval=0.3):
            while not stop_event.is_set():
                start_time = time.time()
                actual_count_during_window = [0]

                def count_put_operation():
                    actual_count_during_window[0] += 1

                original_do_put = self.mq._do_put

                def tracked_do_put(item, item_size):
                    original_do_put(item, item_size)
                    count_put_operation()

                self.mq._do_put = tracked_do_put

                time.sleep(interval)

                self.mq._do_put = original_do_put

                end_time = time.time()
                actual_elapsed = end_time - start_time
                reported_throughput = self.mq.get_throughput(window_seconds=interval)

                self.test_results["throughput_data"].append({
                    "timestamp": end_time,
                    "reported_throughput": reported_throughput,
                    "actual_count": actual_count_during_window[0],
                    "window": interval,
                    "actual_elapsed": actual_elapsed
                })

        # 启动吞吐量验证器线程
        throughput_thread = threading.Thread(target=throughput_validator, args=(self.stop_event,))
        throughput_thread.start()

        # 同时开始生产数据
        producer_thread = threading.Thread(
            target=self.producer,
            args=(1, self.stop_event, (50, 100), 20),  # 小数据，高频率
            daemon=True
        )
        producer_thread.start()

        # 消费线程
        consumer_thread = threading.Thread(
            target=self.consumer,
            args=(1, self.stop_event, 15),  # 快速消费
            daemon=True
        )
        consumer_thread.start()

        # 运行30秒
        time.sleep(30)

        # 停止线程
        self.stop_event.set()
        throughput_thread.join(timeout=2)
        producer_thread.join(timeout=2)
        consumer_thread.join(timeout=2)

        # 吞吐量验证
        throughput_samples = len(self.test_results["throughput_data"])
        self.assertGreater(throughput_samples, 0, "没有收集到有效的吞吐量数据")

        accuracy_errors = []
        for sample in self.test_results["throughput_data"]:
            if sample["actual_count"] > 0:
                error = abs(sample["reported_throughput"] - sample["actual_count"]) / sample["actual_count"] * 100
                accuracy_errors.append(error)

        if accuracy_errors:
            avg_error = sum(accuracy_errors) / len(accuracy_errors)
            self.assertLess(avg_error, 5.0, f"吞吐量计算的平均误差超过了5%（实际误差: {avg_error:.2f}%）")

    def test_memory_limit(self):
        """验证内存限制是否生效"""
        # 这个测试要在运行了多生产者消费者测试后进行
        self.test_multi_producer_consumer()

        total_blocked = sum(self.test_results["blocked_counts"])
        memory_limit_worked = total_blocked > 0
        self.assertTrue(memory_limit_worked, "内存限制未生效")

    def tearDown(self):
        """在每个测试之后清理资源"""
        print("测试已完成，清理资源...")


if __name__ == '__main__':
    unittest.main()