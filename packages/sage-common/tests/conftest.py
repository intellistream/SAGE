"""
pytest 配置文件
"""
import sys
import os

# 添加 sage-common 源码路径到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))