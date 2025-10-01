#!/usr/bin/env python3
"""简单测试脚本：向 QA pipeline 服务发送测试问题"""

import sys
import time

# 模拟用户输入
test_question = "什么是人工智能？"

print(f"发送测试问题: {test_question}")
print(test_question)
print()

# 等待5秒看回复
time.sleep(5)

# 发送退出命令
print("bye bye")
