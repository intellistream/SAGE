from __future__ import annotations

import time
from typing import Type, Union, Any, List, Optional
from enum import Enum
import sage_memory.api
from sage_core.function.base_function import BaseFunction
from sage_core.api.datastream import DataStream
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.source_transformation import SourceTransformation
from sage_core.transformation.future_transformation import FutureTransformation
from sage_utils.custom_logger import CustomLogger
from sage_utils.name_server import get_name
from sage_core.function.lambda_function import wrap_lambda
from sage_core.client import EngineClient
from sage_core.api.base_environment import BaseEnvironment

class LocalEnvironment(BaseEnvironment):
    """
    本地执行环境（不使用 Ray），用于开发调试或小规模测试。
    """

    def __init__(self, name: str = "local_environment", config: dict | None = None):
        super().__init__(name, config, platform="local")