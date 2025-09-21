#!/usr/bin/env python3
"""
import logging
简化的Ray Actor测试，避免使用ray.util.queue
"""

import os
import warnings

import ray
from sage.kernel.utils.ray.ray import ensure_ray_initialized

# 抑制Ray的ResourceWarning
warnings.filterwarnings("ignore", category=ResourceWarning)
os.environ["PYTHONWARNINGS"] = "ignore::ResourceWarning"


@ray.remote
class SimpleActor:
    def __init__(self):
        self.messages = []

    def add_message(self, msg):
        self.messages.append(msg)
        return f"Added: {msg}"

    def get_messages(self):
        return self.messages.copy()

    def get_message_count(self):
        return len(self.messages)


def test_simple_actor():
    """测试简单的Ray Actor通信"""
    logging.info("Testing simple Ray Actor communication...")

    # 强制关闭现有Ray会话并重新初始化以确保使用正确的输出目录
    import ray

    if ray.is_initialized():
        ray.shutdown()

    # 确保Ray初始化
    ensure_ray_initialized()

    # 创建Actor
    actor = SimpleActor.remote()

    # 测试添加消息
    result1 = ray.get(actor.add_message.remote("Hello"))
    logging.info(f"Result 1: {result1}")

    result2 = ray.get(actor.add_message.remote("World"))
    logging.info(f"Result 2: {result2}")

    # 测试获取消息
    messages = ray.get(actor.get_messages.remote())
    logging.info(f"Messages: {messages}")

    count = ray.get(actor.get_message_count.remote())
    logging.info(f"Message count: {count}")

    assert messages == ["Hello", "World"]
    assert count == 2

    logging.info("Simple Ray Actor test passed!")


if __name__ == "__main__":
    test_simple_actor()
