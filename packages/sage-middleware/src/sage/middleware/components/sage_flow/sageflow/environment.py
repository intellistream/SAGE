"""
Environment wrapper for SAGE Flow Python interface.
"""

from sageflow import Environment as CppEnvironment

from .stream import DataStream

class Environment:
    def __init__(self):
        self._env = CppEnvironment()

    def create_datastream(self):
        cpp_ds = self._env.create_datastream()
        return DataStream(cpp_ds)