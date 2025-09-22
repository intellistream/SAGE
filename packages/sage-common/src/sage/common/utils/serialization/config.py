"""
序列化配置和常量定义
"""
import threading
import io


# 不可序列化类型黑名单
BLACKLIST = [
    threading.Thread,  # 线程
    io.TextIOWrapper,  # 文件句柄类型
    type(threading.Lock()),    # 锁
    type(threading.RLock()),   # 递归锁
    threading.Event,   # 事件
    threading.Condition,  # 条件变量
]

# 序列化时需要排除的属性名
ATTRIBUTE_BLACKLIST = {
    'logger',          # 日志对象
    '_logger',         # 私有日志对象
    'server_socket',   # socket对象
    'server_thread',   # 线程对象
    '_server_thread',  # 私有线程对象
    'client_socket',   # socket对象
    '__weakref__',     # 弱引用
    'runtime_context', # 运行时上下文
    # 'memory_collection', # 内存集合（通常是Ray Actor句柄）
    'env',             # 环境引用（避免循环引用）
    # '_dag_node_factory',  # 工厂对象
    # '_operator_factory',  # 工厂对象
    # '_function_factory',  # 工厂对象
}

# 哨兵值，表示应该跳过的值
SKIP_VALUE = object()


# Ray相关的专用排除列表
RAY_TRANSFORMATION_EXCLUDE_ATTRS = [
    'logger', '_logger',           # 日志对象
    'env',                         # 环境引用（避免循环引用）
    'runtime_context',             # 运行时上下文
    '_dag_node_factory',           # 懒加载工厂
    '_operator_factory',           # 懒加载工厂  
    '_function_factory',           # 懒加载工厂
    'server_socket',               # socket对象
    'server_thread', '_server_thread',  # 线程对象
]

RAY_OPERATOR_EXCLUDE_ATTRS = [
    'logger', '_logger',
    'runtime_context',
    'emit_context',
    'server_socket', 'client_socket',
    'server_thread', '_server_thread',
    # 注意：__weakref__ 是内置属性，不能简单移除，所以不包含在这里
]
