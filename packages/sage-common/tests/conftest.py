"""
pytest 配置文件
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC_COMMON = ROOT / "src"

# 添加 sage-common 源码路径到 Python 路径
if str(SRC_COMMON) not in sys.path:
    sys.path.insert(0, str(SRC_COMMON))
