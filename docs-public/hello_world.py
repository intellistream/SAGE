#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE Framework Hello World 批处理示例

这是一个使用 SAGE Framework 的简单批处理示例，演示了：
1. 批处理数据源 (BatchFunction)
2. 数据转换 (MapFunction)
3. 数据输出 (SinkFunction)

Author: SAGE Team
"""

import time

from sage.kernel.api.function.batch_function import BatchFunction
from sage.kernel.api.function.map_function import MapFunction
from sage.kernel.api.function.sink_function import SinkFunction
from sage.kernel.api.local_environment import LocalEnvironment


class HelloBatch(BatchFunction):
    """
    批处理数据源函数，生成指定数量的 Hello, World! 消息

    该类继承自 BatchFunction，用于生成批处理数据。
    当计数器达到最大值时，返回 None 表示批处理完成。
    """

    def __init__(self, max_count=10, **kwargs):
        """
        初始化批处理数据源

        Args:
            max_count (int): 最大生成数据条数，默认为 10
            **kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = max_count

    def execute(self):
        """
        执行批处理数据生成

        Returns:
            str: 格式化的 Hello, World! 消息
            None: 当达到最大计数时返回 None，表示批处理完成
        """
        if self.counter >= self.max_count:
            return None  # 返回 None 表示批处理完成

        self.counter += 1
        return f"Hello, World! #{self.counter}"


class UpperCaseMap(MapFunction):
    """
    字符串大写转换函数

    该类继承自 MapFunction，用于将输入的字符串转换为大写形式。
    这是一个简单的数据转换示例。
    """

    def execute(self, data):
        """
        执行字符串大写转换

        Args:
            data (str): 输入的字符串数据

        Returns:
            str: 转换为大写的字符串
        """
        if data is None:
            return None
        return data.upper()


class PrintSink(SinkFunction):
    """
    控制台输出函数

    该类继承自 SinkFunction，用于将处理后的数据输出到控制台。
    这是数据流的最终输出端点。
    """

    def execute(self, data):
        """
        执行数据输出操作

        Args:
            data (str): 需要输出的数据

        Returns:
            str: 返回原始数据（便于链式操作）
        """
        if data is not None:
            print(f"[OUTPUT] {data}")
        return data


def main():
    """
    主函数：演示 SAGE Framework 批处理流程

    创建一个简单的数据处理流水线：
    1. HelloBatch 生成数据
    2. UpperCaseMap 转换数据为大写
    3. PrintSink 输出结果到控制台
    """
    # 创建本地执行环境
    env = LocalEnvironment("hello_world_batch_demo")

    # 构建数据处理流水线：批处理源 -> 映射转换 -> 输出
    print("构建数据处理流水线...")
    env.from_batch(HelloBatch).map(UpperCaseMap).sink(PrintSink)

    try:
        print("开始执行批处理任务...")
        env.submit()

        # 等待批处理完成
        time.sleep(2)  # 等待足够时间让批处理完成

    except KeyboardInterrupt:
        print("\n[INFO] 用户中断程序执行")
    except Exception as e:
        print(f"[ERROR] 程序执行出错: {e}")
    finally:
        print("[INFO] Hello World 批处理示例结束")


if __name__ == "__main__":
    """
    程序入口点

    禁用调试日志并启动主程序
    """
    # 禁用全局控制台调试信息，保持输出清洁
    # CustomLogger.disable_global_console_debug()  # Commented out due to import issue

    # 启动主程序
    main()
