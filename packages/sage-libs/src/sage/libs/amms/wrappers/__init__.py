"""Python wrappers for AMM algorithm implementations.

This module provides Python wrappers around C++ AMM implementations,
making them accessible through the unified AmmIndex interface.
"""

from . import PyAMM

CPPAlgo = PyAMM.CPPAlgo
MatrixLoader = PyAMM.MatrixLoader
ConfigMap = PyAMM.ConfigMap
createAMM = PyAMM.createAMM
createMatrixLoader = PyAMM.createMatrixLoader
configMapToDict = PyAMM.configMapToDict
dictToConfigMap = PyAMM.dictToConfigMap

__all__ = [
    "CPPAlgo",
    "MatrixLoader",
    "ConfigMap",
    "createAMM",
    "createMatrixLoader",
    "configMapToDict",
    "dictToConfigMap",
]
