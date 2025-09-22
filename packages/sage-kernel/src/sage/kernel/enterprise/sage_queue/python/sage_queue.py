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
import logging
import atexit
import getpass
import threading
from typing import Any, Optional, List, Dict
from queue import Queue, Empty, Full
from ctypes import Structure, c_uint64, c_uint32, c_char, POINTER, c_void_p, c_int, c_bool

# 配置日志
logger = logging.getLogger(__name__)

# 全局队列注册表和锁
_global_queue_registry = {}
_registry_lock = threading.Lock()


def _get_user_prefix():
    """
    获取用户前缀，用于多租户隔离
    优先级：环境变量 > getpass.getuser() > 进程ID
    """
    import os
    import getpass
    
    # 1. 首先检查环境变量
    user = os.environ.get('SAGE_USER')
    if user:
        return user
    
    # 2. 尝试使用getpass获取用户名
    try:
        user = getpass.getuser()
        if user and user != 'unknown':
            return user
    except Exception:
        pass
    
    # 3. 如果都失败，使用进程ID作为fallback
    return f"proc_{os.getpid()}"

def _get_namespaced_queue_name(name: str, namespace: Optional[str] = None) -> str:
    """
    获取带命名空间的队列名称
    格式: {user_prefix}_{namespace}_{name} 或 {user_prefix}_{name}
    注意：移除了 PID 以支持跨进程共享
    """
    user_prefix = _get_user_prefix()
    
    if namespace:
        return f"{user_prefix}_{namespace}_{name}"
    else:
        return f"{user_prefix}_{name}"

def _extract_queue_info(namespaced_name: str) -> tuple:
    """从带命名空间的名称中提取信息"""
    try:
        parts = namespaced_name.split('_', 2)
        if len(parts) == 3:
            namespace = parts[0]
            pid_str = parts[1]
            original_name = parts[2]
            
            # 尝试解析PID
            try:
                pid = int(pid_str)
                return namespace, pid, original_name
            except ValueError:
                # PID解析失败，可能是老式命名或其他格式
                return namespace, None, '_'.join(parts[1:])
                
        # 如果不是标准的多租户格式，直接返回原名
        return None, None, namespaced_name
    except Exception:
        return None, None, namespaced_name

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
        queue = SageQueue("shared_queue_name")
        
        # 在不同进程中通过相同名称连接到同一队列
        def worker(queue_name):
            queue = SageQueue(queue_name)
            queue.put("data")
            queue.close()
        
        process = multiprocessing.Process(target=worker, args=["shared_queue_name"])
    """
    
    def __init__(self, name: str, maxsize: int = 1024 * 1024, auto_cleanup: bool = True, namespace: Optional[str] = None, enable_multi_tenant: bool = True):
        """
        初始化队列
        
        Args:
            name: 队列名称（用于跨进程共享）
            maxsize: 队列最大容量（字节）
            auto_cleanup: 是否自动清理共享内存
            namespace: 命名空间，默认使用用户名
            enable_multi_tenant: 是否启用多租户支持
        """
        self.original_name = name
        self.namespace = namespace
        self.enable_multi_tenant = enable_multi_tenant
        
        if enable_multi_tenant:
            self.name = _get_namespaced_queue_name(name, namespace)
        else:
            self.name = name
            
        self.maxsize = maxsize  # 使用传入的maxsize参数
        self.auto_cleanup = auto_cleanup
        
        # 加载C库
        self._lib = self._load_library()
        
        # 设置函数签名
        self._setup_function_signatures()
        
        # 创建或打开环形缓冲区
        self.name_bytes = self.name.encode('utf-8')  # 使用命名空间化的名称
        
        # 使用命名队列创建函数，支持真正的共享
        self._rb = self._lib.ring_buffer_create_named(self.name_bytes, self.maxsize)

        if not self._rb:
            # 如果创建失败，尝试打开现有的
            try:
                self._rb = self._lib.ring_buffer_open(self.name_bytes)
                if not self._rb:
                    import os
                    current_user = os.getenv('USER', 'unknown')
                    error_msg = f"""Failed to open existing ring buffer: {name}
                    
这可能是因为：
1. 共享内存文件属于其他用户，当前用户({current_user})没有访问权限
2. 共享内存文件已损坏
3. 系统资源不足

建议解决方案：
1. 清理无效的共享内存: sudo rm -f /dev/shm/sage_ringbuf_{name}
2. 或者使用不同的队列名称
3. 检查系统权限和资源限制"""
                    raise RuntimeError(error_msg)
            except Exception as e:
                logger.error(f"Failed to create or open ring buffer: {name}", exc_info=True)
                raise
            # 对于打开的现有缓冲区，需要增加引用计数
            try:
                ref_count = self._lib.ring_buffer_inc_ref(self._rb)
                if ref_count < 0:
                    raise RuntimeError(f"Failed to increment reference count for ring buffer: {name}")
            except Exception as e:
                logger.error(f"Failed to increment reference count for ring buffer: {name}", exc_info=True)
                raise
        else:
            # 对于新创建的缓冲区，不需要额外增加引用计数
            # 因为ring_buffer_create已经设置了初始引用计数为1
            pass
        # if CustomLogger.is_global_console_debug_enabled():
        #     print(self.get_stats())
        # 线程安全相关
        self._lock = threading.RLock()
        
        # 消息计数（用于qsize的近似值）
        self._message_count = 0
        self._message_lock = threading.Lock()
        
        # 标记是否已关闭
        self._closed = False
        
    
    def _load_library(self) -> ctypes.CDLL:
        """加载C动态库"""
        # 查找库文件的多种路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 可能的库文件路径（按优先级排序）
        lib_paths = [
            # 1. 开发环境：当前目录下的编译文件
            os.path.join(current_dir, "ring_buffer.so"),
            os.path.join(current_dir, "libring_buffer.so"),
            
            # 2. 父目录的构建目录（cmake构建）
            os.path.join(current_dir, "..", "build", "ring_buffer.so"),
            os.path.join(current_dir, "..", "build", "libring_buffer.so"),
            
            # 3. 父目录下的库文件（直接链接）
            os.path.join(current_dir, "..", "ring_buffer.so"),
            os.path.join(current_dir, "..", "libring_buffer.so"),
            
            # 4. 安装后的包内文件
            os.path.join(current_dir, "..", "..", "lib", "ring_buffer.so"),
            os.path.join(current_dir, "..", "..", "lib", "libring_buffer.so"),
            
            # 5. 系统库路径
            "ring_buffer.so",
            "libring_buffer.so",
            
            # 6. 相对路径查找
            "./ring_buffer.so",
            "./libring_buffer.so"
        ]
        
        # 尝试加载库
        for lib_path in lib_paths:
            if os.path.exists(lib_path):
                try:
                    # Debug output if needed
                    # print(f"Trying to load library from: {lib_path}")
                    return ctypes.CDLL(lib_path)
                except OSError as e:
                    print(f"Failed to load {lib_path}: {e}")
                    continue
        
        # 如果都找不到，尝试从环境变量或系统路径加载
        try:
            return ctypes.CDLL("libring_buffer.so")
        except OSError:
            pass    
        
        # 如果库不存在，尝试自动编译（仅在CI环境或开发环境中）
        if os.environ.get('CI') or os.path.exists(os.path.join(current_dir, 'ring_buffer.cpp')):
            print("Library not found, attempting auto-compilation...")
            try:
                import subprocess
                
                # 尝试使用auto_compile.sh脚本
                auto_compile_script = os.path.join(current_dir, 'auto_compile.sh')
                if os.path.exists(auto_compile_script):
                    result = subprocess.run(['bash', auto_compile_script], 
                                          cwd=current_dir, 
                                          capture_output=True, 
                                          text=True, 
                                          timeout=120)
                    if result.returncode == 0:
                        print("Auto-compilation successful!")
                        # 重新尝试加载库
                        for lib_path in lib_paths:
                            if os.path.exists(lib_path):
                                try:
                                    return ctypes.CDLL(lib_path)
                                except OSError:
                                    continue
                    else:
                        print(f"Auto-compilation failed: {result.stderr}")
                
                # 如果auto_compile.sh失败，尝试直接编译
                print("Trying direct compilation...")
                cpp_file = os.path.join(current_dir, 'ring_buffer.cpp')
                output_file = os.path.join(current_dir, 'libring_buffer.so')
                
                compile_cmd = [
                    'g++', '-std=c++11', '-fPIC', '-shared', '-O2',
                    '-I.', '-o', output_file, cpp_file
                ]
                
                result = subprocess.run(compile_cmd, 
                                      cwd=current_dir,
                                      capture_output=True, 
                                      text=True, 
                                      timeout=60)
                
                if result.returncode == 0:
                    # 创建兼容性符号链接
                    try:
                        symlink_path = os.path.join(current_dir, 'ring_buffer.so')
                        if os.path.exists(symlink_path):
                            os.unlink(symlink_path)
                        os.symlink('libring_buffer.so', symlink_path)
                    except OSError:
                        pass  # 在Windows上创建符号链接可能失败，但不影响功能
                    
                    print("Direct compilation successful!")
                    return ctypes.CDLL(output_file)
                else:
                    print(f"Direct compilation failed: {result.stderr}")
                    
            except Exception as e:
                print(f"Auto-compilation error: {e}")
        
        # 提供更详细的错误信息
        error_msg = f"""
Could not load ring_buffer library. Tried the following paths:
{chr(10).join(f"  - {path} {'(exists)' if os.path.exists(path) else '(not found)'}" for path in lib_paths)}

Please ensure the C library is compiled. You can:
1. Run 'make' in {current_dir}
2. Run 'bash build.sh' in {current_dir}
3. Run 'bash auto_compile.sh' in {current_dir}
4. Compile manually: g++ -std=c++11 -fPIC -shared -O2 -I. -o libring_buffer.so ring_buffer.cpp
        """
        raise RuntimeError(error_msg)
    
    def _setup_function_signatures(self):
        """设置C库函数签名"""
        # 基础操作
        self._lib.ring_buffer_create.argtypes = [c_uint32]
        self._lib.ring_buffer_create.restype = POINTER(RingBufferStruct)
        
        # 新增：命名队列创建函数
        self._lib.ring_buffer_create_named.argtypes = [ctypes.c_char_p, c_uint32]
        self._lib.ring_buffer_create_named.restype = POINTER(RingBufferStruct)

        self._lib.ring_buffer_open.argtypes = [ctypes.c_char_p]
        self._lib.ring_buffer_open.restype = POINTER(RingBufferStruct)
        
        self._lib.ring_buffer_close.argtypes = [POINTER(RingBufferStruct)]
        self._lib.ring_buffer_close.restype = None
        
        # 销毁函数（按名称销毁共享内存）
        self._lib.ring_buffer_destroy_named.argtypes = [ctypes.c_char_p]
        self._lib.ring_buffer_destroy_named.restype = None
        
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
                # 简化的实现：直接尝试读取一个较大的缓冲区
                # 假设单个消息不会超过64KB
                max_msg_size = 64 * 1024
                buffer = ctypes.create_string_buffer(max_msg_size)
                result = self._lib.ring_buffer_read(self._rb, buffer, max_msg_size)

                if result > 0:
                    # 成功读取数据
                    try:
                        # 解析长度前缀
                        if result >= 4:
                            data_len = struct.unpack('<I', buffer.raw[:4])[0]
                            if result >= 4 + data_len:
                                # 提取实际数据
                                data = buffer.raw[4:4+data_len]
                                item = pickle.loads(data)
                                with self._message_lock:
                                    self._message_count = max(0, self._message_count - 1)
                                return item
                    except Exception as e:
                        # 如果反序列化失败，继续尝试
                        pass

            # 如果不阻塞，直接抛出异常
            if not block:
                raise Empty("Queue is empty")
            
            # 检查超时
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise Empty("Get operation timed out")
                time.sleep(0.001)
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
        }
    
    def reset_stats(self):
        """重置统计��息"""
        self._lib.ring_buffer_reset_stats(self._rb)
        with self._message_lock:
            self._message_count = 0
    
    def close(self):
        """关闭队列，正确处理引用计数"""
        if getattr(self, '_closed', False):
            return
            
        self._closed = True
        
        # 从全局注册表移除（使用超���避免死锁）
        try:
            if _registry_lock.acquire(timeout=0.1):
                try:
                    _global_queue_registry.pop(self.name, None)
                finally:
                    _registry_lock.release()
        except Exception:
            pass  # 忽略注册表操作失败
        
        if self._rb:
            try:
                # 减少引用计数
                ref_count = self._lib.ring_buffer_dec_ref(self._rb)
                logger.debug(f"Decreased ref count for {self.name}, new count: {ref_count}")
                
                # 如果引用计数达到0，C层会自动清理共享内存
                # 这时我们不应该再调用ring_buffer_close，因为结构体可能已被释放
                if ref_count > 0:
                    # 只有引用计数大于0时才调用close
                    self._lib.ring_buffer_close(self._rb)
                    logger.debug(f"Closed ring buffer for {self.name}")
                else:
                    logger.debug(f"Ring buffer for {self.name} auto-cleaned by C layer")
                    
            except Exception as e:
                logger.warning(f"Error decrementing ref count for {self.name}: {e}")
                # 如果dec_ref失败，仍然尝试关闭
                try:
                    self._lib.ring_buffer_close(self._rb)
                except Exception:
                    pass
            finally:
                self._rb = None
    
    def destroy(self):
        """销毁队列（删除共享内存）"""
        if self.name:
            name_bytes = self.name.encode('utf-8')
            self._lib.ring_buffer_destroy_named(name_bytes)
            logger.info(f"Destroyed shared memory for queue: {self.name}")
    
    def get_shared_memory_info(self) -> Dict[str, Any]:
        """获取共享内存信息"""
        return {
            'original_name': self.original_name,
            'namespaced_name': self.name,
            'namespace': self.namespace,
            'multi_tenant_enabled': self.enable_multi_tenant,
            'auto_cleanup': self.auto_cleanup,
            'shm_path': f'/dev/shm/sage_ringbuf_{self.name}',
        }
    
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
        """析构函数 - 确保正确清理资源，不阻塞进程退出"""
        try:
            if (hasattr(self, '_rb') and self._rb and 
                not getattr(self, '_closed', False)):
                # 只做最基本的清理，避免阻塞
                try:
                    if hasattr(self, '_lib') and self._lib:
                        self._lib.ring_buffer_close(self._rb)
                except Exception:
                    pass  # 忽略所有异常
                self._rb = None
                self._closed = True
        except Exception:
            pass  # 析构函数绝不能抛出异常
        finally:
            # 确保资源被释放
            if hasattr(self, '_rb'):
                self._rb = None


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

        # 添加测试代码期望的属性
        self.queue_name = self.name  # 队列名称的别名
        self.maxsize = self.size     # 队列大小的别名
        self.create_if_not_exists = True  # 默认创建不存在的队列

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
            'creator_pid': self.creator_pid,
            'queue_name': self.queue_name,
            'maxsize': self.maxsize,
            'create_if_not_exists': self.create_if_not_exists
        }
    
    def __setstate__(self, state):
        """支持pickle反序列化"""
        self.name = state['name']
        self.size = state['size']
        self.auto_cleanup = state['auto_cleanup']
        self.creator_pid = state['creator_pid']
        self.queue_name = state.get('queue_name', self.name)
        self.maxsize = state.get('maxsize', self.size)
        self.create_if_not_exists = state.get('create_if_not_exists', True)
        self._ref_ptr = None
        self._lib = None
    
    def __repr__(self):
        return f"SageQueueRef(name='{self.name}', size={self.size}, creator_pid={self.creator_pid})"



def destroy_queue(name: str):
    """销毁指定名称的队列"""
    # 注意：ring_buffer_destroy需要RingBuffer指针，不是队列名称
    # 这个函数主要用于清理共享内存文件，不直接调用C++的destroy��数
    import os

    # 清理可能的共享内存文件
    shm_paths = [
        f"/dev/shm/sage_ringbuf_{name}",
        f"/tmp/sage_ringbuf_{name}"
    ]

    for path in shm_paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except (OSError, FileNotFoundError):
            pass  # 忽略删除失败的情况


def cleanup_invalid_queues():
    """清理无效的共享内存队列"""
    import subprocess
    import os
    
    try:
        # 获���当前用户拥有的共享内存文件
        result = subprocess.run(['ls', '-la', '/dev/shm/'],
                              capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return
            
        current_user = os.getenv('USER', 'unknown')
        current_pid = os.getpid()
        lines = result.stdout.split('\n')
        
        for line in lines:
            if 'sage_ringbuf_' in line:
                parts = line.split()
                if len(parts) >= 9:
                    owner = parts[2]
                    filename = parts[-1]
                    if filename.startswith('sage_ringbuf_'):
                        queue_name = filename[13:]  # 移除 "sage_ringbuf_" 前缀
                        
                        # 检查是��属于当前用户
                        if owner != current_user:
                            print(f"发现其他用户({owner})的共享内存文件: {filename}")
                            continue
                        
                        # 检查是否是当前用户的但属于已死进程的队列
                        namespace, pid, original_name = _extract_queue_info(queue_name)
                        if pid and pid != current_pid:
                            # 检查进程是否还存在
                            try:
                                os.kill(pid, 0)  # 不发送信号，只检查进程存在
                            except OSError:
                                # 进��不存在，可以清理
                                shm_path = f'/dev/shm/{filename}'
                                try:
                                    os.remove(shm_path)
                                    print(f"清理了死进程({pid})的共享内存: {filename}")
                                except OSError as e:
                                    print(f"无法清理共享内存 {filename}: {e}")
                        
    except Exception as e:
        print(f"清理共享内存时出错: {e}")
        pass


def cleanup_user_queues(user: Optional[str] = None, force: bool = False):
    """清理指定用户的所有SAGE队列
    
    Args:
        user: 用户名，默认为当前用户
        force: 是否强制清理（即使进程还在运行）
    """
    import subprocess
    import os
    
    if user is None:
        user = getpass.getuser()
    
    try:
        result = subprocess.run(['ls', '-la', '/dev/shm/'], 
                              capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return
            
        lines = result.stdout.split('\n')
        current_pid = os.getpid()
        
        for line in lines:
            if 'sage_ringbuf_' in line and user in line:
                parts = line.split()
                if len(parts) >= 9:
                    owner = parts[2]
                    filename = parts[-1]
                    
                    if owner == user and filename.startswith('sage_ringbuf_'):
                        queue_name = filename[13:]  # 移除 "sage_ringbuf_" 前缀
                        namespace, pid, original_name = _extract_queue_info(queue_name)
                        
                        should_clean = force
                        if not force and pid and pid != current_pid:
                            # 检查进程是否还存在
                            try:
                                os.kill(pid, 0)
                            except OSError:
                                should_clean = True
                        
                        if should_clean:
                            shm_path = f'/dev/shm/{filename}'
                            try:
                                os.remove(shm_path)
                                print(f"清理了队列: {filename} (原名: {original_name})")
                            except OSError as e:
                                print(f"无法清理 {filename}: {e}")
                        else:
                            print(f"跳过活跃进程的队列: {filename}")
                        
    except Exception as e:
        print(f"清理用户队列时出错: {e}")


def list_all_sage_queues():
    """列出所有SAGE队列的信息"""
    import subprocess
    import os
    
    try:
        result = subprocess.run(['ls', '-la', '/dev/shm/'], 
                              capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("无法访问 /dev/shm/")
            return
            
        lines = result.stdout.split('\n')
        queues = []
        
        for line in lines:
            if 'sage_ringbuf_' in line:
                parts = line.split()
                if len(parts) >= 9:
                    permissions = parts[0]
                    owner = parts[2]
                    group = parts[3]
                    size = parts[4]
                    date = ' '.join(parts[5:8])
                    filename = parts[-1]
                    
                    if filename.startswith('sage_ringbuf_'):
                        queue_name = filename[13:]
                        namespace, pid, original_name = _extract_queue_info(queue_name)
                        
                        # 检查进程状态
                        process_status = "Unknown"
                        if pid:
                            try:
                                os.kill(pid, 0)
                                process_status = "Running"
                            except OSError:
                                process_status = "Dead"
                        
                        queues.append({
                            'filename': filename,
                            'original_name': original_name,
                            'namespace': namespace,
                            'pid': pid,
                            'owner': owner,
                            'group': group,
                            'size': size,
                            'date': date,
                            'permissions': permissions,
                            'process_status': process_status,
                        })
        
        if queues:
            print(f"{'原始名称':<20} {'命名空间':<15} {'PID':<8} {'所有者':<10} {'大小':<10} {'进程状态':<10} {'文件名'}")
            print("-" * 100)
            for q in queues:
                print(f"{q['original_name']:<20} {q['namespace'] or 'N/A':<15} {q['pid'] or 'N/A':<8} {q['owner']:<10} {q['size']:<10} {q['process_status']:<10} {q['filename']}")
        else:
            print("没有找到SAGE队列")
            
    except Exception as e:
        print(f"列出队列时出错: {e}")
