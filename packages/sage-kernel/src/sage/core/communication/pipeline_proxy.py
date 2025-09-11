from concurrent.futures import ThreadPoolExecutor, Future
import logging
import queue
import threading
import time
from typing import Dict, Optional, Any, TYPE_CHECKING
import uuid
from sage.core.communication.packet import Packet
from sage.kernel.runtime.communication.queue_descriptor.python_queue_descriptor import PythonQueueDescriptor

if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment


class AsyncPipelineCallProxy:
    """异步服务调用代理，返回 Future 对象"""

    def __init__(self, env: 'BaseEnvironment'):
        # 请求结果管理
        # 这些不可序列化对象都要__post_init__去初始化
        self._result_lock = threading.RLock()
        self._request_results: Dict[str, Packet] = {}
        self._pending_requests: Dict[str, threading.Event] = {}
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="ServiceCall")
        self._shutdown = threading.Event()
        self._listener_thread = threading.Thread(target=self._response_listener, name="ServiceResponseListener")
        self._listener_thread.start()
        self.pipeline_input_qd = env.input_qd
        self.pipeline_sink_qd = env.sink_qd  # 在connect方法中，把它传进去
        self.response_queue = PythonQueueDescriptor(maxsize=10000)
        self.client_uuid = str(uuid.uuid4())
        self.connected = False

    def connect(self):
        try:
            request_packet = Packet(payload = None, client_uuid=self.client_uuid, request_id=None, client_queue=self.response_queue)
            self.pipeline_sink_qd.put(request_packet, timeout=5.0)
            self.connected = True
        except Exception as e:
            print(f"[ASYNC_PROXY] Error connecting: {e}")

    def async_call(self, *args, **kwargs):

        def async_method_call():
            """异步方法调用，返回 Future 对象"""
            print(f"[ASYNC_PROXY] Starting async call")

            # 使用 ServiceManager 的 call_async 方法返回 Future
            future = self._executor.submit(self.__call__, *args, **kwargs)

            print(f"[ASYNC_PROXY] Future created")
            return future

        return async_method_call

    def __call__(self, *args, **kwargs) -> Any:
        if not self.connected:
            self.connect()

        request_id = str(uuid.uuid4())
        call_start_time = time.time()

        # 创建等待事件
        event = threading.Event()
        with self._result_lock:
            self._pending_requests[request_id] = event

        try:
            packet = Packet(payload=(args, kwargs), client_uuid=self.client_uuid, request_id=request_id)

            queue_send_start = time.time()
            self.pipeline_input_qd.put(packet, timeout=5.0)
            queue_send_time = time.time() - queue_send_start

            print(f"[SERVICE_CALL] Request sent successfully in {queue_send_time:.3f}s (request_id: {request_id})")

            if not event.wait(timeout=5):
                raise TimeoutError(f"Service call timeout after {5}s")


            # 获取结果
            with self._result_lock:
                if request_id not in self._request_results:
                    print(f"[SERVICE_CALL] Result not found for request_id: {request_id}")
                    raise RuntimeError(f"Service call result not found: {request_id}")

                response = self._request_results.pop(request_id)
                return response.payload

        except Exception as e:
            # 清理等待状态
            with self._result_lock:
                self._pending_requests.pop(request_id, None)
                self._request_results.pop(request_id, None)
            raise

    def _response_listener(self):
        """
        响应监听线程 - 从响应队列接收响应并分发
        """
        print("Service response listener started")

        while not self._shutdown.is_set():
            try:
                # 从响应队列获取响应（阻塞等待1秒）
                try:
                    response_packet = self.response_queue.get(timeout=1.0)
                    # TODO: 把这些队列的结果和异常，封装进QD里边去
                except Exception as queue_error:
                    # 检查具体的队列异常类型
                    error_type = type(queue_error).__name__

                    # 处理标准Python队列超时异常（queue.Empty）
                    if isinstance(queue_error, queue.Empty):
                        # 这是正常的超时，继续循环而不记录任何消息
                        continue

                    # 处理其他可能的超时异常
                    error_str = str(queue_error).lower()
                    if error_type == 'Empty' or 'empty' in error_type.lower():
                        # 其他类型的Empty异常
                        continue
                    elif "timed out" in error_str or "timeout" in error_str:
                        # 其他类型的超时异常
                        continue
                    elif "closed" in error_str or "queue is closed" in error_str:
                        # 队列关闭
                        print(f"Queue operation result: {queue_error}")
                        continue
                    else:
                        # 其他未知的队列异常
                        if error_str.strip():  # 如果错误消息不为空
                            print(f"Queue operation issue ({error_type}): {queue_error}")
                        else:  # 如果错误消息为空，提供更多上下文
                            print(f"Queue operation ({error_type}): Empty message from queue.get() - likely timeout")
                        continue  # 继续运行，不要因为队列问题停止

                print(f"[SERVICE_RESPONSE] Received raw response data: {response_packet}")
                if response_packet is None:
                    print("[SERVICE_RESPONSE] Received None from queue, continuing")
                    continue
                request_id = response_packet.request_id

                with self._result_lock:
                    # 存储结果
                    self._request_results[request_id] = response_packet
                    print(
                        f"[SERVICE_RESPONSE] Stored result for request_id: {response_packet}, content: {response_packet.payload}"
                    )
                    # 唤醒等待的线程
                    event = self._pending_requests.pop(request_id, None)
                    if event is None:
                        raise RuntimeError(f"[SERVICE_RESPONSE] No waiting event found for request_id: {request_id}")
                    event.set()

            except Exception as e:
                # 检查是否是队列关闭导致的错误
                error_str = str(e).lower()
                if "closed" in error_str or "queue is closed" in error_str:
                    print("Response queue closed, stopping listener")
                    break
                else:
                    raise RuntimeError(f"Error in response listener: {e}")
