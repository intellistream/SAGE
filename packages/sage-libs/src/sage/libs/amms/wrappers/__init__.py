"""Python wrappers for AMM algorithm implementations (externalized).

The compiled bindings live in the external package `isage-amms`. Importing these
wrappers without installing that package will raise an ImportError with a clear
instruction.
"""

__all__ = [
    "CPPAlgo",
    "MatrixLoader",
    "ConfigMap",
    "createAMM",
    "createMatrixLoader",
    "configMapToDict",
    "dictToConfigMap",
]

try:  # ImportError is expected if external package is not installed
    from . import PyAMM

    CPPAlgo = PyAMM.CPPAlgo
    MatrixLoader = PyAMM.MatrixLoader
    ConfigMap = PyAMM.ConfigMap
    createAMM = PyAMM.createAMM
    createMatrixLoader = PyAMM.createMatrixLoader
    configMapToDict = PyAMM.configMapToDict
    dictToConfigMap = PyAMM.dictToConfigMap
except ImportError as exc:  # fail fast with guidance
    raise ImportError(
        "PyAMM bindings are now provided by the external package 'isage-amms'. "
        "Install it with `pip install isage-amms` to use AMM implementations."
    ) from exc
