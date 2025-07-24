"""
服务队列通信测试

展示服务系统的高性能队列通信能力，包括：
1. 异步消息处理
2. 请求-响应模式
3. 批量处理和流式处理
4. 服务间通信
"""

import time
import threading
import uuid
from typing import List, Dict, Any
from sage_core.api.local_environment import LocalEnvironment
from sage_utils.mmap_queue.sage_queue import SageQueue


class MessageBrokerService:
    """
    消息代理服务
    支持发布-订阅模式和消息路由
    """
    
    def __init__(self, max_message_size: int = 1024*1024):
        self.max_message_size = max_message_size
        self.is_running = False
        self.subscribers = {}  # topic -> list of subscriber_ids
        self.message_count = 0
        self.ctx = None
        
        # 统计信息
        self.published_messages = 0
        self.delivered_messages = 0
    
    def start_running(self):
        self.is_running = True
        print(f"Message broker started (max_message_size: {self.max_message_size})")
    
    def terminate(self):
        self.is_running = False
        print(f"Message broker terminated. Published: {self.published_messages}, Delivered: {self.delivered_messages}")
    
    def subscribe(self, topic: str, subscriber_id: str) -> bool:
        """订阅主题"""
        if not self.is_running:
            return False
        
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        if subscriber_id not in self.subscribers[topic]:
            self.subscribers[topic].append(subscriber_id)
            print(f"Subscriber {subscriber_id} subscribed to topic '{topic}'")
            return True
        
        return False
    
    def unsubscribe(self, topic: str, subscriber_id: str) -> bool:
        """取消订阅"""
        if topic in self.subscribers and subscriber_id in self.subscribers[topic]:
            self.subscribers[topic].remove(subscriber_id)
            print(f"Subscriber {subscriber_id} unsubscribed from topic '{topic}'")
            return True
        return False
    
    def publish(self, topic: str, message: Dict[str, Any]) -> int:
        """发布消息到主题"""
        if not self.is_running:
            return 0
        
        if topic not in self.subscribers:
            return 0
        
        self.message_count += 1
        message_with_meta = {
            'id': self.message_count,
            'topic': topic,
            'timestamp': time.time(),
            'data': message
        }
        
        delivered = 0
        for subscriber_id in self.subscribers[topic]:
            try:
                # 模拟向订阅者发送消息
                self._deliver_to_subscriber(subscriber_id, message_with_meta)
                delivered += 1
            except Exception as e:
                print(f"Failed to deliver message to {subscriber_id}: {e}")
        
        self.published_messages += 1
        self.delivered_messages += delivered
        
        return delivered
    
    def _deliver_to_subscriber(self, subscriber_id: str, message: Dict[str, Any]):
        """向订阅者投递消息"""
        # 这里模拟消息投递
        print(f"  📨 Delivered message {message['id']} to {subscriber_id}")
    
    def get_topic_stats(self) -> Dict[str, Any]:
        """获取主题统计"""
        stats = {}
        for topic, subscribers in self.subscribers.items():
            stats[topic] = {
                'subscriber_count': len(subscribers),
                'subscribers': subscribers
            }
        return stats


class TaskQueueService:
    """
    任务队列服务
    支持任务排队、优先级处理和结果回调
    """
    
    def __init__(self, max_workers: int = 4, queue_size: int = 1000):
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.is_running = False
        self.task_queue = []
        self.completed_tasks = {}
        self.processing_tasks = {}
        self.worker_threads = []
        self.ctx = None
        
        # 统计
        self.total_tasks = 0
        self.completed_count = 0
        self.failed_count = 0
    
    def start_running(self):
        self.is_running = True
        
        # 启动工作线程
        for i in range(self.max_workers):
            thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"TaskWorker_{i}"
            )
            thread.start()
            self.worker_threads.append(thread)
        
        print(f"Task queue service started with {self.max_workers} workers")
    
    def terminate(self):
        self.is_running = False
        print(f"Task queue terminated. Completed: {self.completed_count}, Failed: {self.failed_count}")
    
    def submit_task(self, task_id: str, task_type: str, payload: Dict[str, Any], priority: int = 5) -> bool:
        """提交任务"""
        if not self.is_running or len(self.task_queue) >= self.queue_size:
            return False
        
        task = {
            'id': task_id,
            'type': task_type,
            'payload': payload,
            'priority': priority,
            'submitted_at': time.time(),
            'status': 'queued'
        }
        
        # 按优先级插入（优先级数字越小越高）
        inserted = False
        for i, existing_task in enumerate(self.task_queue):
            if priority < existing_task['priority']:
                self.task_queue.insert(i, task)
                inserted = True
                break
        
        if not inserted:
            self.task_queue.append(task)
        
        self.total_tasks += 1
        print(f"📋 Task {task_id} ({task_type}) submitted with priority {priority}")
        return True
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        # 检查已完成任务
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        
        # 检查正在处理的任务
        if task_id in self.processing_tasks:
            return self.processing_tasks[task_id]
        
        # 检查队列中的任务
        for task in self.task_queue:
            if task['id'] == task_id:
                return task
        
        return {'status': 'not_found'}
    
    def _worker_loop(self):
        """工作线程循环"""
        thread_name = threading.current_thread().name
        
        while self.is_running:
            try:
                # 获取任务
                task = None
                if self.task_queue:
                    task = self.task_queue.pop(0)
                
                if task:
                    # 标记为处理中
                    task['status'] = 'processing'
                    task['worker'] = thread_name
                    task['started_at'] = time.time()
                    self.processing_tasks[task['id']] = task
                    
                    print(f"  ⚙️  {thread_name} processing task {task['id']}")
                    
                    # 执行任务
                    try:
                        result = self._execute_task(task)
                        task['status'] = 'completed'
                        task['result'] = result
                        task['completed_at'] = time.time()
                        self.completed_count += 1
                        
                    except Exception as e:
                        task['status'] = 'failed'
                        task['error'] = str(e)
                        task['failed_at'] = time.time()
                        self.failed_count += 1
                        print(f"  ❌ Task {task['id']} failed: {e}")
                    
                    # 移到已完成队列
                    self.processing_tasks.pop(task['id'], None)
                    self.completed_tasks[task['id']] = task
                    
                    print(f"  ✅ Task {task['id']} {task['status']}")
                
                else:
                    time.sleep(0.1)  # 没有任务时短暂休眠
                    
            except Exception as e:
                print(f"Worker {thread_name} error: {e}")
                time.sleep(1.0)
    
    def _execute_task(self, task: Dict[str, Any]) -> Any:
        """执行任务"""
        task_type = task['type']
        payload = task['payload']
        
        # 模拟不同类型的任务处理
        if task_type == 'calculation':
            # 模拟计算任务
            numbers = payload.get('numbers', [])
            operation = payload.get('operation', 'sum')
            
            time.sleep(0.2)  # 模拟计算时间
            
            if operation == 'sum':
                return sum(numbers)
            elif operation == 'product':
                result = 1
                for n in numbers:
                    result *= n
                return result
            else:
                return len(numbers)
        
        elif task_type == 'data_processing':
            # 模拟数据处理
            data = payload.get('data', [])
            processing_type = payload.get('type', 'count')
            
            time.sleep(0.3)  # 模拟处理时间
            
            if processing_type == 'count':
                return len(data)
            elif processing_type == 'unique':
                return len(set(data))
            else:
                return {'processed': True, 'items': len(data)}
        
        else:
            # 默认处理
            time.sleep(0.1)
            return {'task_type': task_type, 'processed': True}
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        return {
            'queued_tasks': len(self.task_queue),
            'processing_tasks': len(self.processing_tasks),
            'completed_tasks': len(self.completed_tasks),
            'total_submitted': self.total_tasks,
            'completed_count': self.completed_count,
            'failed_count': self.failed_count,
            'success_rate': self.completed_count / self.total_tasks if self.total_tasks > 0 else 0
        }


def test_message_broker():
    """测试消息代理服务"""
    print("=== 消息代理服务测试 ===")
    
    # 创建环境
    env = LocalEnvironment("message_broker_env")
    env.register_service("message_broker", MessageBrokerService, max_message_size=2*1024*1024)
    
    # 创建服务
    task_factory = env.service_task_factories["message_broker"]
    service_task = task_factory.create_service_task()
    
    try:
        # 启动服务
        service_task.start_running()
        broker = service_task.service
        
        # 模拟订阅者
        topics = ["user_events", "system_alerts", "analytics"]
        subscribers = ["service_a", "service_b", "logger", "analytics_engine"]
        
        # 设置订阅关系
        print("\n设置订阅关系...")
        broker.subscribe("user_events", "service_a")
        broker.subscribe("user_events", "logger")
        broker.subscribe("system_alerts", "service_a")
        broker.subscribe("system_alerts", "service_b")
        broker.subscribe("system_alerts", "logger")
        broker.subscribe("analytics", "analytics_engine")
        broker.subscribe("analytics", "logger")
        
        # 发布消息
        print("\n发布消息...")
        
        # 用户事件
        for i in range(5):
            message = {
                "user_id": f"user_{i}",
                "action": "login" if i % 2 == 0 else "logout",
                "timestamp": time.time(),
                "ip": f"192.168.1.{100 + i}"
            }
            delivered = broker.publish("user_events", message)
            print(f"User event {i}: delivered to {delivered} subscribers")
            time.sleep(0.1)
        
        # 系统告警
        for i in range(3):
            message = {
                "level": "WARNING" if i < 2 else "ERROR",
                "message": f"System alert {i}",
                "component": f"component_{i}",
                "timestamp": time.time()
            }
            delivered = broker.publish("system_alerts", message)
            print(f"System alert {i}: delivered to {delivered} subscribers")
            time.sleep(0.1)
        
        # 分析数据
        for i in range(2):
            message = {
                "metric_name": f"cpu_usage_{i}",
                "value": 75.5 + i * 5,
                "tags": {"host": f"server_{i}"},
                "timestamp": time.time()
            }
            delivered = broker.publish("analytics", message)
            print(f"Analytics data {i}: delivered to {delivered} subscribers")
            time.sleep(0.1)
        
        # 显示统计
        print(f"\n=== 主题统计 ===")
        topic_stats = broker.get_topic_stats()
        for topic, stats in topic_stats.items():
            print(f"{topic}: {stats['subscriber_count']} subscribers - {stats['subscribers']}")
    
    finally:
        service_task.terminate()


def test_task_queue():
    """测试任务队列服务"""
    print("\n=== 任务队列服务测试 ===")
    
    # 创建环境
    env = LocalEnvironment("task_queue_env")
    env.register_service("task_queue", TaskQueueService, max_workers=3, queue_size=100)
    
    # 创建服务
    task_factory = env.service_task_factories["task_queue"]
    service_task = task_factory.create_service_task()
    
    try:
        # 启动服务
        service_task.start_running()
        queue = service_task.service
        
        # 提交各种类型的任务
        print("\n提交任务...")
        task_ids = []
        
        # 计算任务
        for i in range(5):
            task_id = f"calc_{i}"
            task_ids.append(task_id)
            queue.submit_task(
                task_id=task_id,
                task_type="calculation",
                payload={
                    "numbers": [i, i+1, i+2],
                    "operation": "sum" if i % 2 == 0 else "product"
                },
                priority=3
            )
        
        # 高优先级紧急任务
        urgent_task_id = "urgent_calc"
        task_ids.append(urgent_task_id)
        queue.submit_task(
            task_id=urgent_task_id,
            task_type="calculation",
            payload={"numbers": [100, 200, 300], "operation": "sum"},
            priority=1  # 高优先级
        )
        
        # 数据处理任务
        for i in range(3):
            task_id = f"data_proc_{i}"
            task_ids.append(task_id)
            queue.submit_task(
                task_id=task_id,
                task_type="data_processing",
                payload={
                    "data": [f"item_{j}" for j in range(i*10, (i+1)*10)],
                    "type": "count" if i % 2 == 0 else "unique"
                },
                priority=5
            )
        
        # 等待任务完成
        print("\n等待任务完成...")
        completed_count = 0
        max_wait_time = 10  # 最多等待10秒
        start_time = time.time()
        
        while completed_count < len(task_ids) and (time.time() - start_time) < max_wait_time:
            completed_count = 0
            for task_id in task_ids:
                status = queue.get_task_status(task_id)
                if status.get('status') in ['completed', 'failed']:
                    completed_count += 1
            
            if completed_count < len(task_ids):
                time.sleep(0.5)
                
                # 显示进度
                stats = queue.get_queue_stats()
                print(f"进度: {completed_count}/{len(task_ids)} 完成, "
                      f"队列中: {stats['queued_tasks']}, "
                      f"处理中: {stats['processing_tasks']}")
        
        # 显示结果
        print(f"\n=== 任务结果 ===")
        for task_id in task_ids:
            status = queue.get_task_status(task_id)
            if status.get('status') == 'completed':
                execution_time = status.get('completed_at', 0) - status.get('started_at', 0)
                print(f"{task_id}: ✅ {status.get('result')} (耗时: {execution_time:.3f}s)")
            elif status.get('status') == 'failed':
                print(f"{task_id}: ❌ {status.get('error')}")
            else:
                print(f"{task_id}: 🔄 {status.get('status', 'unknown')}")
        
        # 最终统计
        final_stats = queue.get_queue_stats()
        print(f"\n=== 队列统计 ===")
        for key, value in final_stats.items():
            print(f"{key}: {value}")
    
    finally:
        service_task.terminate()


if __name__ == "__main__":
    # 运行测试
    test_message_broker()
    test_task_queue()
    print("\n🎉 所有队列通信测试完成！")
