"""
Metronome - 全局同步锁机制
用于控制Pipeline中数据的逐个处理节奏
"""
import threading
import time
from typing import Optional
from sage.common.utils.logging.custom_logger import CustomLogger


class Metronome:
    """
    全局节拍器，用于控制数据流的同步处理
    
    工作原理：
    1. 初始状态为锁定
    2. BatchFunction在输出数据前等待锁释放
    3. 输出一个数据后自动重新锁定
    4. SinkFunction处理完数据后释放锁
    """
    
    def __init__(self, name: str = "global_metronome"):
        self.name = name
        self.logger = CustomLogger()
        self._lock = threading.RLock()  # 使用可重入锁
        self._is_locked = True  # 初始状态为锁定
        self._condition = threading.Condition(self._lock)
        self._waiting_count = 0  # 等待的线程数量
        
        self.logger.debug(f"Metronome '{self.name}' initialized (locked={self._is_locked})")
    
    def wait_for_release(self, timeout: Optional[float] = None) -> bool:
        """
        等待锁被释放
        
        Args:
            timeout: 超时时间（秒），None表示无限等待
            
        Returns:
            bool: True表示锁被释放，False表示超时
        """
        with self._condition:
            self._waiting_count += 1
            try:
                self.logger.debug(f"Metronome '{self.name}': Thread waiting for release (waiting_count={self._waiting_count})")
                
                while self._is_locked:
                    if not self._condition.wait(timeout=timeout):
                        self.logger.warning(f"Metronome '{self.name}': Wait timeout")
                        return False
                
                self.logger.debug(f"Metronome '{self.name}': Thread got release signal")
                return True
            finally:
                self._waiting_count -= 1
    
    def release_once(self):
        """
        释放锁一次，允许一个等待的线程继续执行
        不会自动重新锁定
        """
        with self._condition:
            if self._is_locked:
                self.logger.debug(f"Metronome '{self.name}': Releasing lock (waiting_count={self._waiting_count})")
                self._is_locked = False
                self._condition.notify(1)  # 只唤醒一个等待的线程
            else:
                self.logger.debug(f"Metronome '{self.name}': Already released, skipping")
    
    def lock_after_send(self):
        """
        在发送数据后立即锁定，等待Sink处理完成
        """
        with self._condition:
            if not self._is_locked:
                self.logger.debug(f"Metronome '{self.name}': Locking after send")
                self._is_locked = True
            else:
                self.logger.debug(f"Metronome '{self.name}': Already locked")
    
    def _auto_lock(self):
        """自动重新锁定"""
        with self._condition:
            if not self._is_locked:
                self._is_locked = True
                self.logger.debug(f"Metronome '{self.name}': Auto-locked")
    
    def force_release(self):
        """强制释放锁，不会自动重新锁定"""
        with self._condition:
            self.logger.info(f"Metronome '{self.name}': Force releasing lock")
            self._is_locked = False
            self._condition.notify_all()
    
    def is_locked(self) -> bool:
        """检查当前是否被锁定"""
        with self._lock:
            return self._is_locked
    
    def reset(self):
        """重置为初始锁定状态"""
        with self._condition:
            self.logger.info(f"Metronome '{self.name}': Resetting to locked state")
            self._is_locked = True
    
    def get_status(self) -> dict:
        """获取当前状态信息"""
        with self._lock:
            return {
                "name": self.name,
                "is_locked": self._is_locked,
                "waiting_count": self._waiting_count
            }


# 全局单例实例
_global_metronome = None
_metronome_lock = threading.Lock()


def get_global_metronome() -> Metronome:
    """获取全局metronome实例"""
    global _global_metronome
    with _metronome_lock:
        if _global_metronome is None:
            _global_metronome = Metronome("global")
        return _global_metronome


def create_metronome(name: str) -> Metronome:
    """创建一个新的metronome实例"""
    return Metronome(name)
