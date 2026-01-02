"""
pytest 配置文件
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC_COMMON = ROOT / "src"
SRC_LLM_CORE = ROOT.parent / "sage-llm-core" / "src"

# 添加 sage-common 源码路径到 Python 路径
for p in (SRC_COMMON, SRC_LLM_CORE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
