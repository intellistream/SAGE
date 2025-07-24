"""
SAGE High-Performance Memory-Mapped Queue

基于mmap和C实现的高性能进程间环形队列，提供与Python标准Queue兼容的接口
支持跨Actor通信，零拷贝操作，以及引用传递
"""

import ctypes
import pickle
import struct
import time
import threading
import os
from typing import Any, Optional, List, Dict
from queue import Empty, Full
from ctypes import Structure, c_uint64, c_uint32, c_char, POINTER, c_void_p, c_int, c_bool

# C结构体映射
class RingBufferStruct(Structure):
    _fields_ = [
        ("magic", c_uint64),
        ("version", c_uint32),
        ("buffer_size", c_uint32),
        ("head", c_uint64),
        ("tail", c_uint64),
        ("readers", c_uint32),
        ("writers", c_uint32),
        ("ref_count", c_uint32),
        ("process_count", c_uint32),
        # 跳过pthread_mutex_t，它在Python中不直接使用
        ("name", c_char * 64),
        ("creator_pid", c_int),
        ("total_bytes_written", c_uint64),
        ("total_bytes_read", c_uint64),
        ("padding", c_char * 24),  # 调整padding以匹配C结构
    ]

class RingBufferRef(Structure):
    _fields_ = [
        ("name", c_char * 64),
        ("size", c_uint32),
        ("auto_cleanup", c_bool),
        ("creator_pid", c_int),
    ]

class RingBufferStats(Structure):
    _fields_ = [
        ("buffer_size", c_uint32),
        ("available_read", c_uint32),
        ("available_write", c_uint32),
        ("readers", c_uint32),
        ("writers", c_uint32),
        ("ref_count", c_uint32),
        ("total_bytes_written", c_uint64),
        ("total_bytes_read", c_uint64),
        ("utilization", ctypes.c_double),
    ]


class SageQueue:
    """
    与Python标准queue.Queue兼容的跨进程队列实现
    基于高性能mmap环形缓冲区，支持跨Actor通信
    
    多进程使用方法:
        # 创建队列
        queue = SageQueue("shared_queue_name", maxsize=64*1024)
        
        # 在不同进程中通过相同名称连接到同一队列
        def worker(queue_name):
            queue = SageQueue(queue_name)
            queue.put("data")
            queue.close()
        
        process = multiprocessing.Process(target=worker, args=["shared_queue_name"])
    """
    
    def __init__(self, name: str, auto_cleanup : bool = False):
        """
        初始化队列
        
        Args:
            name: 队列名称（用于跨进程共享）
            maxsize: 最大队列大小，0表示使用默认大小
            auto_cleanup: 是否自动清理共享内存
        """
        self.name = name
        self.maxsize =  1024 * 1024  # 默认1MB
        self.auto_cleanup = auto_cleanup
        
        # 加载C库
        self._lib = self._load_library()
        
        # 设置函数签名
        self._setup_function_signatures()
        
        # 创建或打开环形缓冲区
        self.name_bytes = name.encode('utf-8')
        
        # 首先尝试创建新的缓冲区
        self._rb = self._lib.ring_buffer_create(self.name_bytes, self.maxsize)
        
        if not self._rb:
            # 如果创建失败，尝试打开现有的
            try:
                self._rb = self._lib.ring_buffer_open(self.name_bytes)
            except Exception as e:
                self.logger.error(f"Failed to create or open ring buffer: {name}", exc_info=True)
                raise
            # 对于打开的现有缓冲区，需要增加引用计数
            try:
                ref_count = self._lib.ring_buffer_inc_ref(self._rb)
            except Exception as e:
                self.logger.error(f"Failed to increment reference count for ring buffer: {name}", exc_info=True)
                raise
        else:
            # 对于新创建的缓冲区，也需要增加引用计数（因为构造函数算一个引用）
            ref_count = self._lib.ring_buffer_inc_ref(self._rb)
            if ref_count < 0:
                self.logger.error(f"Failed to increment reference count for ring buffer: {name}", excinfo=True)
                raise
        
        # 线程安全相关
        self._lock = threading.RLock()
        
        # 消息计数（用于qsize的近似值）
        self._message_count = 0
        self._message_lock = threading.Lock()
        
        # 标记是否已关闭
        self._closed = False
    
    def _load_library(self) -> ctypes.CDLL:
        """加载C动态库"""
        # 查找库文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        lib_paths = [
            os.path.join(current_dir, "ring_buffer.so"),
            os.path.join(current_dir, "libring_buffer.so"),
            "ring_buffer.so",
            "libring_buffer.so"
        ]
        
        for lib_path in lib_paths:
            if os.path.exists(lib_path):
                try:
                    return ctypes.CDLL(lib_path)
                except OSError:
                    continue
        
        raise RuntimeError("Could not load ring_buffer library. Please compile it first.")
    
    def _setup_function_signatures(self):
        """设置C库函数签名"""
        # 基础操作
        self._lib.ring_buffer_create.argtypes = [ctypes.c_char_p, c_uint32]
        self._lib.ring_buffer_create.restype = POINTER(RingBufferStruct)
        
        self._lib.ring_buffer_open.argtypes = [ctypes.c_char_p]
        self._lib.ring_buffer_open.restype = POINTER(RingBufferStruct)
        
        self._lib.ring_buffer_close.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_close.restype = None
        
        self._lib.ring_buffer_destroy.argtypes = [ctypes.c_char_p]
        self._lib.ring_buffer_destroy.restype = None
        
        # 读写操作
        self._lib.ring_buffer_write.argtypes = [POINTER(RingBufferStruct), c_void_p, c_uint32]
        self._lib.ring_buffer_write.restype = c_int
        
        self._lib.ring_buffer_read.argtypes = [POINTER(RingBufferStruct), c_void_p, c_uint32]
        self._lib.ring_buffer_read.restype = c_int
        
        self._lib.ring_buffer_peek.argtypes = [POINTER(RingBufferStruct), c_void_p, c_uint32]
        self._lib.ring_buffer_peek.restype = c_int
        
        # 状态查询
        self._lib.ring_buffer_available_read.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_available_read.restype = c_uint32
        
        self._lib.ring_buffer_available_write.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_available_write.restype = c_uint32
        
        self._lib.ring_buffer_is_empty.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_is_empty.restype = c_bool
        
        self._lib.ring_buffer_is_full.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_is_full.restype = c_bool
        
        # 引用管理
        self._lib.ring_buffer_get_ref.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_get_ref.restype = POINTER(RingBufferRef)
        
        self._lib.ring_buffer_from_ref.argtypes = [POINTER(RingBufferRef)]
        self._lib.ring_buffer_from_ref.restype = POINTER(RingBufferStruct)
        
        self._lib.ring_buffer_release_ref.argtypes = [POINTER(RingBufferRef)]
        self._lib.ring_buffer_release_ref.restype = None
        
        self._lib.ring_buffer_inc_ref.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_inc_ref.restype = c_int
        
        self._lib.ring_buffer_dec_ref.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_dec_ref.restype = c_int
        
        # 统计信息
        self._lib.ring_buffer_get_stats.argtypes = [POINTER(RingBufferStruct), POINTER(RingBufferStats)]
        self._lib.ring_buffer_get_stats.restype = None
        
        self._lib.ring_buffer_reset_stats.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_reset_stats.restype = None
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """
        向队列添加元素
        
        Args:
            item: 要添加的元素
            block: 是否阻塞等待
            timeout: 超时时间（秒）
        
        Raises:
            Full: 当队列满且不阻塞时
        """
        if self._closed:
            raise RuntimeError("Queue is closed")
            
        # 序列化数据
        try:
            data = pickle.dumps(item, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            raise ValueError(f"Failed to serialize item: {e}")
        
        # 添加长度前缀（4字节）
        data_with_len = struct.pack('<I', len(data)) + data
        
        start_time = time.time()
        
        while True:
            with self._lock:
                # 检查是否有足够空间
                available = self._lib.ring_buffer_available_write(self._rb)
                if available >= len(data_with_len):
                    result = self._lib.ring_buffer_write(
                        self._rb,
                        ctypes.c_char_p(data_with_len),
                        len(data_with_len)
                    )
                    if result > 0:
                        with self._message_lock:
                            self._message_count += 1
                        return
            
            # 如果不阻塞，直接抛出异常
            if not block:
                raise Full("Queue is full")
            
            # 检查超时
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise Full("Put operation timed out")
                remaining = timeout - elapsed
                time.sleep(min(0.001, remaining))
            else:
                time.sleep(0.001)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        从队列获取元素
        
        Args:
            block: 是否阻塞等待
            timeout: 超时时间（秒）
        
        Returns:
            队列中的元素
            
        Raises:
            Empty: 当队列空且不阻塞时
        """
        if self._closed:
            raise RuntimeError("Queue is closed")
            
        start_time = time.time()
        
        while True:
            with self._lock:
                # 检查是否有数据可读
                available = self._lib.ring_buffer_available_read(self._rb)
                if available >= 4:  # 至少有长度前缀
                    # 先peek长度前缀
                    len_buffer = ctypes.create_string_buffer(4)
                    result = self._lib.ring_buffer_peek(self._rb, len_buffer, 4)
                    
                    if result == 4:
                        data_len = struct.unpack('<I', len_buffer.raw)[0]
                        total_len = 4 + data_len
                        
                        # 检查是否有完整的数据
                        if available >= total_len:
                            # 读取完整消息（长度前缀 + 数据）
                            full_buffer = ctypes.create_string_buffer(total_len)
                            result = self._lib.ring_buffer_read(self._rb, full_buffer, total_len)
                            
                            if result == total_len:
                                # 跳过长度前缀，反序列化数据
                                data = full_buffer.raw[4:4+data_len]
                                try:
                                    item = pickle.loads(data)
                                    with self._message_lock:
                                        self._message_count = max(0, self._message_count - 1)
                                    return item
                                except Exception as e:
                                    raise ValueError(f"Failed to deserialize item: {e}")
            
            # 如果不阻塞，直接抛出异常
            if not block:
                raise Empty("Queue is empty")
            
            # 检查超时
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise Empty("Get operation timed out")
                remaining = timeout - elapsed
                time.sleep(min(0.001, remaining))
            else:
                time.sleep(0.001)
    
    def put_nowait(self, item: Any) -> None:
        """非阻塞添加元素"""
        self.put(item, block=False)
    
    def get_nowait(self) -> Any:
        """非阻塞获取元素"""
        return self.get(block=False)
    
    def qsize(self) -> int:
        """返回队列中的元素个数（近似值）"""
        with self._message_lock:
            return self._message_count
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        with self._lock:
            return self._lib.ring_buffer_is_empty(self._rb)
    
    def full(self) -> bool:
        """检查队列是否已满"""
        with self._lock:
            return self._lib.ring_buffer_is_full(self._rb)
    
    def get_reference(self) -> 'SageQueueRef':
        """获取队列引用（用于内部统计和监控）"""
        ref_ptr = self._lib.ring_buffer_get_ref(self._rb)
        if not ref_ptr:
            raise RuntimeError("Failed to get queue reference")
        
        return SageQueueRef(ref_ptr.contents, self._lib)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        stats = RingBufferStats()
        self._lib.ring_buffer_get_stats(self._rb, ctypes.byref(stats))
        
        return {
            'buffer_size': stats.buffer_size,
            'available_read': stats.available_read,
            'available_write': stats.available_write,
            'readers': stats.readers,
            'writers': stats.writers,
            'ref_count': stats.ref_count,
            'total_bytes_written': stats.total_bytes_written,
            'total_bytes_read': stats.total_bytes_read,
            'utilization': stats.utilization,
            'message_count': self._message_count
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self._lib.ring_buffer_reset_stats(self._rb)
        with self._message_lock:
            self._message_count = 0
    
    def close(self):
        """关闭队列"""
        if self._closed:
            return
            
        self._closed = True
        
        if self._rb:
            # 减少引用计数
            try:
                self._lib.ring_buffer_dec_ref(self._rb)
            except:
                pass  # 忽略减少引用计数时的错误
            
            # 关闭缓冲区
            self._lib.ring_buffer_close(self._rb)
            self._rb = None
    
    def destroy(self):
        """销毁队列（删除共享内存）"""
        if self.name_bytes:
            self._lib.ring_buffer_destroy(self.name_bytes)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __getstate__(self):
        """
        支持pickle序列化 - 只保存重建队列连接所需的基本信息
        """
        return {
            'name': self.name,
            'maxsize': self.maxsize,
            'auto_cleanup': self.auto_cleanup
        }
    
    def __setstate__(self, state):
        """
        支持pickle反序列化 - 在新进程中重新连接到共享内存队列
        """
        self.__init__(state['name'], state['maxsize'], state['auto_cleanup'])
    
    def __del__(self):
        """析构函数"""
        try:
            self.close()
        except:
            pass


class SageQueueRef:
    """
    队列引用对象，用于内部统计和监控
    """
    
    def __init__(self, ref_struct: RingBufferRef, lib=None):
        self.name = ref_struct.name.decode('utf-8')
        self.size = ref_struct.size
        self.auto_cleanup = bool(ref_struct.auto_cleanup)
        self.creator_pid = ref_struct.creator_pid
        self._ref_ptr = None
        self._lib = lib
    
    def get_queue(self) -> SageQueue:
        """从引用创建队列实例（内部使用）"""
        # 直接使用名称打开现有队列
        return SageQueue(self.name, self.size, self.auto_cleanup)
    
    def __getstate__(self):
        """支持pickle序列化"""
        return {
            'name': self.name,
            'size': self.size,
            'auto_cleanup': self.auto_cleanup,
            'creator_pid': self.creator_pid
        }
    
    def __setstate__(self, state):
        """支持pickle反序列化"""
        self.name = state['name']
        self.size = state['size']
        self.auto_cleanup = state['auto_cleanup']
        self.creator_pid = state['creator_pid']
        self._ref_ptr = None
        self._lib = None
    
    def __repr__(self):
        return f"SageQueueRef(name='{self.name}', size={self.size}, creator_pid={self.creator_pid})"


# 便利函数
def create_queue(name: str, maxsize: int = 0) -> SageQueue:
    """创建一个新的SageQueue"""
    return SageQueue(name, maxsize)

def open_queue(name: str) -> SageQueue:
    """打开一个已存在的SageQueue"""
    return SageQueue(name, maxsize=0)

def destroy_queue(name: str):
    """销毁指定名称的队列"""
    name_bytes = name.encode('utf-8')
    # 这里需要加载库来调用destroy函数
    import ctypes
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        lib = ctypes.CDLL(os.path.join(current_dir, "ring_buffer.so"))
        lib.ring_buffer_destroy.argtypes = [ctypes.c_char_p]
        lib.ring_buffer_destroy.restype = None
        lib.ring_buffer_destroy(name_bytes)
    except:
        pass  # 忽略错误
